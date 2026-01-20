"""Tool discovery and registration for agent runner."""

import importlib.util
import inspect
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from framework.llm.provider import Tool, ToolUse, ToolResult


@dataclass
class RegisteredTool:
    """A tool with its executor function."""

    tool: Tool
    executor: Callable[[dict], Any]


class ToolRegistry:
    """
    Manages tool discovery and registration.

    Tool Discovery Order:
    1. Built-in tools (if any)
    2. tools.py in agent folder
    3. Manually registered tools
    """

    def __init__(self):
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        tool: Tool,
        executor: Callable[[dict], Any],
    ) -> None:
        """
        Register a single tool with its executor.

        Args:
            name: Tool name (must match tool.name)
            tool: Tool definition
            executor: Function that takes tool input dict and returns result
        """
        self._tools[name] = RegisteredTool(tool=tool, executor=executor)

    def register_function(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """
        Register a function as a tool, auto-generating the Tool definition.

        Args:
            func: Function to register
            name: Tool name (defaults to function name)
            description: Tool description (defaults to docstring)
        """
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
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == dict:
                    param_type = "object"
                elif param.annotation == list:
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
        """
        Load tools from a Python module file.

        Looks for:
        - TOOLS: dict[str, Tool] - tool definitions
        - tool_executor(tool_use: ToolUse) -> ToolResult - unified executor
        - Functions decorated with @tool

        Args:
            module_path: Path to tools.py file

        Returns:
            Number of tools discovered
        """
        if not module_path.exists():
            return 0

        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("agent_tools", module_path)
        if spec is None or spec.loader is None:
            return 0

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        count = 0

        # Check for TOOLS dict
        if hasattr(module, "TOOLS"):
            tools_dict = getattr(module, "TOOLS")
            executor_func = getattr(module, "tool_executor", None)

            for name, tool in tools_dict.items():
                if executor_func:
                    # Use unified executor
                    def make_executor(tool_name: str):
                        def executor(inputs: dict) -> Any:
                            tool_use = ToolUse(
                                id=f"call_{tool_name}",
                                name=tool_name,
                                input=inputs,
                            )
                            result = executor_func(tool_use)
                            if isinstance(result, ToolResult):
                                return json.loads(result.content) if result.content else {}
                            return result

                        return executor

                    self.register(name, tool, make_executor(name))
                else:
                    # Register tool without executor (will use mock)
                    self.register(name, tool, lambda inputs: {"mock": True, "inputs": inputs})
                count += 1

        # Check for @tool decorated functions
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

    def get_executor(self) -> Callable[[ToolUse], ToolResult]:
        """
        Get unified tool executor function.

        Returns a function that dispatches to the appropriate tool executor.
        """

        def executor(tool_use: ToolUse) -> ToolResult:
            if tool_use.name not in self._tools:
                return ToolResult(
                    tool_use_id=tool_use.id,
                    content=json.dumps({"error": f"Unknown tool: {tool_use.name}"}),
                    is_error=True,
                )

            registered = self._tools[tool_use.name]
            try:
                result = registered.executor(tool_use.input)
                if isinstance(result, ToolResult):
                    return result
                return ToolResult(
                    tool_use_id=tool_use.id,
                    content=json.dumps(result) if not isinstance(result, str) else result,
                    is_error=False,
                )
            except Exception as e:
                return ToolResult(
                    tool_use_id=tool_use.id,
                    content=json.dumps({"error": str(e)}),
                    is_error=True,
                )

        return executor

    def get_registered_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools


def tool(
    description: str | None = None,
    name: str | None = None,
) -> Callable:
    """
    Decorator to mark a function as a tool.

    Usage:
        @tool(description="Fetch lead from GTM table")
        def gtm_fetch_lead(lead_id: str) -> dict:
            return {"lead_data": {...}}
    """

    def decorator(func: Callable) -> Callable:
        func._tool_metadata = {
            "name": name or func.__name__,
            "description": description or func.__doc__,
        }
        return func

    return decorator
