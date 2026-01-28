"""Unified tool execution service."""

import json
import logging
import time
from typing import Any

from framework.llm.provider import ToolResult, ToolUse
from framework.runtime.core import Runtime
from framework.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Service for executing tools and recording outcomes.

    Provides:
    - Unified dispatching to registered tools
    - Automatic outcome recording to Runtime
    - Performance tracking (latency)
    - Error handling and normalization
    """

    def __init__(self, registry: ToolRegistry, runtime: Runtime | None = None):
        """
        Initialize tool executor.

        Args:
            registry: Tool registry to look up tools
            runtime: Runtime for recording outcomes (optional)
        """
        self.registry = registry
        self.runtime = runtime

    async def execute(
        self,
        tool_use: ToolUse,
        decision_id: str | None = None,
        node_id: str | None = None,
    ) -> ToolResult:
        """
        Execute a tool and record the outcome.

        Args:
            tool_use: The tool call request
            decision_id: ID of the decision that triggered this call (for outcome recording)
            node_id: ID of the node making the call

        Returns:
            ToolResult with content and status
        """
        registered = self.registry.get_tool(tool_use.name)
        if not registered:
            error_msg = f"Unknown tool: {tool_use.name}"
            return self._handle_error(tool_use, error_msg, decision_id)

        start = time.time()
        try:
            # Execute tool
            # We support both sync and async executors (check if awaitable)
            import inspect

            executor = registered.executor
            
            # Inject session context if needed (handled by registry during registration usually)
            # But we can also do it here if we want dynamic injection
            
            if inspect.iscoroutinefunction(executor):
                result = await executor(tool_use.input)
            else:
                result = executor(tool_use.input)

            latency_ms = int((time.time() - start) * 1000)

            # Normalize result to ToolResult
            if isinstance(result, ToolResult):
                tool_result = result
            else:
                content = json.dumps(result) if not isinstance(result, str) else result
                tool_result = ToolResult(
                    tool_use_id=tool_use.id,
                    content=content,
                    is_error=False,
                )

            # Record outcome if runtime and decision_id are provided
            if self.runtime and decision_id:
                self.runtime.record_outcome(
                    decision_id=decision_id,
                    success=not tool_result.is_error,
                    result=result,
                    summary=f"Executed tool {tool_use.name}",
                    latency_ms=latency_ms,
                )

            return tool_result

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            error_msg = str(e)
            logger.error(f"Tool execution failed: {tool_use.name} - {error_msg}")
            
            return self._handle_error(tool_use, error_msg, decision_id, latency_ms)

    def _handle_error(
        self,
        tool_use: ToolUse,
        error: str,
        decision_id: str | None = None,
        latency_ms: int = 0,
    ) -> ToolResult:
        """Handle execution error and record failed outcome."""
        result = ToolResult(
            tool_use_id=tool_use.id,
            content=json.dumps({"error": error}),
            is_error=True,
        )

        if self.runtime and decision_id:
            self.runtime.record_outcome(
                decision_id=decision_id,
                success=False,
                error=error,
                latency_ms=latency_ms,
            )

        return result
