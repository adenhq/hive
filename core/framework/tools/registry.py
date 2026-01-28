"""Tool discovery and registration for Aden Hive."""

import importlib.util
import inspect
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from framework.llm.provider import Tool, ToolResult, ToolUse

logger = logging.getLogger(__name__)


@dataclass
class RegisteredTool:
    """A tool with its executor function."""

    tool: Tool
    executor: Callable[[dict], Any]


class ToolRegistry:
    """
    Manages tool discovery and registration in the core backbone.

    Tool Discovery Order:
    1. Built-in tools
    2. Dynamic tools from file/module
    3. MCP servers
    4. Manually registered tools
    """

    def __init__(self):
        self._tools: dict[str, RegisteredTool] = {}
        self._mcp_configs: list[dict[str, Any]] = []
        self._session_context: dict[str, Any] = {}

    def register(
        self,
        name: str,
        tool: Tool,
        executor: Callable[[dict], Any],
    ) -> None:
        """Register a single tool with its executor."""
        self._tools[name] = RegisteredTool(tool=tool, executor=executor)

    def register_function(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Register a function as a tool, auto-generating the Tool definition."""
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or f"Execute {tool_name}"

        # Generate parameters from function signature
        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = "string"  # Default
            if param.annotation != inspect.Parameter.empty:
                if param.annotation is int:
                    param_type = "integer"
                elif param.annotation is float:
                    param_type = "number"
                elif param.annotation is bool:
                    param_type = "boolean"
                elif param.annotation is dict:
                    param_type = "object"
                elif param.annotation is list:
                    param_type = "array"

            properties[param_name] = {"type": param_type}

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        tool = Tool(
            name=tool_name,
            description=tool_desc,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )

        def executor(inputs: dict) -> Any:
            return func(**inputs)

        self.register(tool_name, tool, executor)

    def discover_from_module(self, module_path: Path) -> int:
        """Load tools from a Python module file."""
        if not module_path.exists():
            return 0

        spec = importlib.util.spec_from_file_location("dynamic_tools", module_path)
        if spec is None or spec.loader is None:
            return 0

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        count = 0
        
        # 1. Check for TOOLS dict and tool_executor
        if hasattr(module, "TOOLS"):
            tools_dict = module.TOOLS
            executor_func = getattr(module, "tool_executor", None)

            for name, tool in tools_dict.items():
                if executor_func:
                    def make_executor(tool_name: str):
                        def executor(inputs: dict) -> Any:
                            tool_use = ToolUse(id=f"call_{tool_name}", name=tool_name, input=inputs)
                            result = executor_func(tool_use)
                            if isinstance(result, ToolResult):
                                return json.loads(result.content) if result.content else {}
                            return result
                        return executor
                    self.register(name, tool, make_executor(name))
                else:
                    self.register(name, tool, lambda inputs: {"mock": True, "inputs": inputs})
                count += 1

        # 2. Check for functions decorated with @tool (if using the decorator)
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and hasattr(obj, "_tool_metadata"):
                metadata = obj._tool_metadata
                self.register_function(
                    obj,
                    name=metadata.get("name", name),
                    description=metadata.get("description"),
                )
                count += 1

        return count

    def get_tools(self) -> dict[str, Tool]:
        """Get all registered Tool objects."""
        return {name: rt.tool for name, rt in self._tools.items()}

    def get_registered_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def get_tool(self, name: str) -> RegisteredTool | None:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def set_session_context(self, **context) -> None:
        """Set session context to auto-inject into tool calls."""
        self._session_context.update(context)
