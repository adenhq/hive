"""
Tool Access Layer - Unified interface for tool access in nodes.

Provides:
- Tool discovery and metadata
- Secure tool execution
- Tool permissions and scoping
- Observability and monitoring
- Tool composition utilities
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from framework.llm.provider import Tool, ToolResult, ToolUse
from framework.runtime.core import Runtime

logger = logging.getLogger(__name__)


class ToolPermission(str, Enum):
    """Tool access permissions."""
    READ_ONLY = "read_only"  # Can query tool metadata but not execute
    EXECUTE = "execute"  # Can execute the tool
    ADMIN = "admin"  # Can execute and modify tool configuration


@dataclass
class ToolMetadata:
    """Metadata about a tool."""
    name: str
    description: str
    parameters: dict[str, Any]
    required_params: list[str]
    examples: list[dict[str, Any]] = field(default_factory=list)
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    cost_estimate: float | None = None  # Estimated cost per call
    latency_estimate_ms: int | None = None  # Estimated latency


@dataclass
class ToolExecutionResult:
    """Result of tool execution with metadata."""
    success: bool
    result: Any
    error: str | None = None
    execution_time_ms: int = 0
    tokens_used: int = 0
    cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolAccessLayer:
    """
    Unified tool access layer for nodes.

    Provides a consistent API for:
    - Discovering available tools
    - Accessing tool metadata
    - Executing tools with permissions
    - Monitoring tool usage

    Example:
        layer = ToolAccessLayer(
            tools=tool_registry.get_tools(),
            tool_executor=tool_registry.get_executor(),
            runtime=runtime,
            node_id="analyze_node",
            allowed_tools=["web_search", "file_read"],  # Optional: restrict access
        )

        # Discover tools
        available = layer.list_tools()

        # Get metadata
        metadata = layer.get_tool_metadata("web_search")

        # Execute tool
        result = await layer.execute_tool(
            name="web_search",
            params={"query": "Python async"},
        )
    """

    def __init__(
        self,
        tools: dict[str, Tool],
        tool_executor: Callable[[ToolUse], ToolResult],
        runtime: Runtime,
        node_id: str,
        allowed_tools: list[str] | None = None,
        permission_level: ToolPermission = ToolPermission.EXECUTE,
    ):
        """
        Initialize the tool access layer.

        Args:
            tools: Dictionary of available tools {name: Tool}
            tool_executor: Function to execute tools
            runtime: Runtime for decision logging
            node_id: ID of the node using this layer
            allowed_tools: Optional list of tool names this node can access
            permission_level: Permission level for tool access
        """
        self._all_tools = tools
        self._tool_executor = tool_executor
        self._runtime = runtime
        self._node_id = node_id
        self._permission_level = permission_level

        # Filter tools based on allowed_tools if specified
        if allowed_tools:
            self._tools = {
                name: tool
                for name, tool in tools.items()
                if name in allowed_tools
            }
        else:
            self._tools = tools

        # Track tool usage for observability
        self._usage_stats: dict[str, dict[str, Any]] = {}

    # === TOOL DISCOVERY ===

    def list_tools(self, category: str | None = None) -> list[str]:
        """
        List available tool names.

        Args:
            category: Optional category filter

        Returns:
            List of tool names
        """
        if category:
            return [
                name for name, tool in self._tools.items()
                if self._get_tool_category(tool) == category
            ]
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is available."""
        return name in self._tools

    def get_tool_metadata(self, name: str) -> ToolMetadata | None:
        """
        Get metadata for a tool.

        Args:
            name: Tool name

        Returns:
            ToolMetadata or None if tool not found
        """
        if name not in self._tools:
            return None

        tool = self._tools[name]
        params = tool.parameters.get("properties", {})
        required = tool.parameters.get("required", [])

        return ToolMetadata(
            name=name,
            description=tool.description,
            parameters=params,
            required_params=required,
            category=self._get_tool_category(tool),
        )

    def search_tools(
        self,
        query: str,
        by_description: bool = True,
        by_tags: bool = True,
    ) -> list[str]:
        """
        Search for tools by query string.

        Args:
            query: Search query
            by_description: Search in descriptions
            by_tags: Search in tags

        Returns:
            List of matching tool names
        """
        query_lower = query.lower()
        matches = []

        for name, tool in self._tools.items():
            if by_description and query_lower in tool.description.lower():
                matches.append(name)
                continue

            if by_tags:
                metadata = self.get_tool_metadata(name)
                if metadata and any(query_lower in tag.lower() for tag in metadata.tags):
                    matches.append(name)

        return matches

    # === TOOL EXECUTION ===

    async def execute_tool(
        self,
        name: str,
        params: dict[str, Any],
        timeout_seconds: float | None = None,
    ) -> ToolExecutionResult:
        """
        Execute a tool with proper error handling and observability.

        Args:
            name: Tool name
            params: Tool parameters
            timeout_seconds: Optional timeout

        Returns:
            ToolExecutionResult with execution details
        """
        # Check permissions
        if self._permission_level == ToolPermission.READ_ONLY:
            return ToolExecutionResult(
                success=False,
                result=None,
                error=f"Node '{self._node_id}' has read-only permission for tools",
            )

        # Check if tool exists
        if not self.has_tool(name):
            return ToolExecutionResult(
                success=False,
                result=None,
                error=f"Tool '{name}' not available to node '{self._node_id}'",
            )

        # Get tool metadata for validation
        metadata = self.get_tool_metadata(name)
        if metadata:
            # Validate required parameters
            missing = [p for p in metadata.required_params if p not in params]
            if missing:
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error=f"Missing required parameters: {', '.join(missing)}",
                )

        # Record decision
        decision_id = self._runtime.decide(
            intent=f"Execute tool '{name}'",
            options=[{
                "id": f"tool_{name}",
                "description": f"Execute {name} with provided parameters",
                "action_type": "tool_execution",
            }],
            chosen=f"tool_{name}",
            reasoning=f"Node {self._node_id} executing tool {name}",
            context={"tool": name, "params": params},
        )

        start_time = time.time()

        try:
            # Execute tool
            tool_use = ToolUse(
                id=f"{self._node_id}_{name}_{int(start_time)}",
                name=name,
                input=params,
            )

            result = self._tool_executor(tool_use)
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Parse result
            if result.is_error:
                self._runtime.record_outcome(
                    decision_id=decision_id,
                    success=False,
                    error=result.content,
                )

                # Update usage stats
                self._update_usage_stats(name, False, execution_time_ms)

                return ToolExecutionResult(
                    success=False,
                    result=None,
                    error=result.content,
                    execution_time_ms=execution_time_ms,
                )

            # Parse JSON result if possible
            try:
                if isinstance(result.content, str):
                    parsed_result = json.loads(result.content)
                else:
                    parsed_result = result.content
            except (json.JSONDecodeError, TypeError):
                parsed_result = result.content

            # Record successful outcome
            self._runtime.record_outcome(
                decision_id=decision_id,
                success=True,
                result=parsed_result,
            )

            # Update usage stats
            self._update_usage_stats(name, True, execution_time_ms)

            return ToolExecutionResult(
                success=True,
                result=parsed_result,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            self._runtime.record_outcome(
                decision_id=decision_id,
                success=False,
                error=str(e),
            )

            self._update_usage_stats(name, False, execution_time_ms)

            return ToolExecutionResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

    # === TOOL COMPOSITION ===

    async def execute_tool_chain(
        self,
        tool_calls: list[dict[str, Any]],
        stop_on_error: bool = True,
    ) -> list[ToolExecutionResult]:
        """
        Execute multiple tools in sequence.

        Args:
            tool_calls: List of {"name": str, "params": dict}
            stop_on_error: Stop execution if a tool fails

        Returns:
            List of execution results
        """
        results = []

        for call in tool_calls:
            result = await self.execute_tool(
                name=call["name"],
                params=call.get("params", {}),
            )
            results.append(result)

            if not result.success and stop_on_error:
                break

        return results

    # === OBSERVABILITY ===

    def get_usage_stats(self, tool_name: str | None = None) -> dict[str, Any]:
        """
        Get usage statistics for tools.

        Args:
            tool_name: Optional tool name to get stats for specific tool

        Returns:
            Usage statistics dictionary
        """
        if tool_name:
            return self._usage_stats.get(tool_name, {})
        return self._usage_stats.copy()

    def _update_usage_stats(
        self,
        tool_name: str,
        success: bool,
        execution_time_ms: int,
    ) -> None:
        """Update internal usage statistics."""
        if tool_name not in self._usage_stats:
            self._usage_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_time_ms": 0,
                "avg_time_ms": 0,
            }

        stats = self._usage_stats[tool_name]
        stats["total_calls"] += 1
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1

        stats["total_time_ms"] += execution_time_ms
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["total_calls"]

    def _get_tool_category(self, tool: Tool) -> str:
        """Infer tool category from name or description."""
        name_lower = tool.name.lower()

        if any(word in name_lower for word in ["file", "read", "write", "list"]):
            return "file_system"
        elif any(word in name_lower for word in ["web", "search", "scrape", "http"]):
            return "web"
        elif any(word in name_lower for word in ["db", "database", "query", "sql"]):
            return "database"
        elif any(word in name_lower for word in ["email", "send", "mail"]):
            return "communication"
        else:
            return "general"

