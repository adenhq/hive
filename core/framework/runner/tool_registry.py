"""Tool discovery and registration for agent runner."""

import importlib.util
import inspect
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_type_hints

from framework.llm.provider import Tool, ToolResult, ToolUse

logger = logging.getLogger(__name__)


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
    3. MCP servers
    4. Manually registered tools
    """

    def __init__(self):
        self._tools: dict[str, RegisteredTool] = {}
        self._mcp_clients: list[Any] = []  # List of MCPClient instances
        self._session_context: dict[str, Any] = {}  # Auto-injected context for tools

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

    def _validate_and_bind_arguments(
        self,
        tool_name: str,
        func: Callable,
        sig: inspect.Signature,
        inputs: dict[str, Any],
    ) -> inspect.BoundArguments:
        """
        Validate and bind arguments for tool execution.

        Uses Python's signature.bind() for validation, then performs basic type checking.
        This ensures Python's binding rules (positional-only, keyword-only, etc.) are respected.

        Type checking policy:
        - int: only int
        - float: int or float (numeric widening allowed)
        - bool: only bool
        - str: only str
        - None values are allowed for optional parameters

        Args:
            tool_name: Name of the tool (for error messages)
            func: Function object (for type hint resolution)
            sig: Function signature to validate against
            inputs: Input dictionary from tool execution

        Returns:
            BoundArguments object with validated and bound arguments

        Raises:
            ValueError: If validation fails (missing required, unexpected params, type mismatch)
        """
        # Filter out 'self' and 'cls' from inputs if present
        filtered_inputs = {k: v for k, v in inputs.items() if k not in ("self", "cls")}

        # Use Python's bind() to validate arguments - this catches:
        # - Missing required parameters
        # - Extra unexpected parameters (unless **kwargs present)
        # - Positional-only parameters passed as keywords
        # - Keyword-only parameters passed positionally
        try:
            bound = sig.bind(**filtered_inputs)
            bound.apply_defaults()
        except TypeError as e:
            # Convert Python's TypeError to ValueError with clearer message
            error_msg = str(e)
            if "missing" in error_msg.lower() and "required" in error_msg.lower():
                raise ValueError(
                    f"Tool '{tool_name}' argument validation failed: {error_msg}"
                ) from e
            elif "unexpected keyword argument" in error_msg or "got an unexpected" in error_msg:
                raise ValueError(
                    f"Tool '{tool_name}' argument validation failed: {error_msg}"
                ) from e
            elif "positional only" in error_msg.lower():
                raise ValueError(
                    f"Tool '{tool_name}' argument validation failed: {error_msg}"
                ) from e
            else:
                raise ValueError(f"Tool '{tool_name}' argument binding failed: {error_msg}") from e

        # Type validation using proper type hint resolution
        try:
            type_hints = get_type_hints(func, include_extras=False)
        except Exception:
            # If type hints can't be resolved, skip type checking
            # This can happen with complex types or missing imports
            type_hints = {}

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls") or param_name not in bound.arguments:
                continue

            value = bound.arguments[param_name]

            # Skip type checking if value is None (for optional params)
            if value is None:
                continue

            # Get resolved type hint (handles string annotations properly)
            annotation = type_hints.get(param_name, inspect.Parameter.empty)
            if annotation == inspect.Parameter.empty:
                # Fallback to signature annotation if type_hints didn't resolve it
                annotation = param.annotation
                if isinstance(annotation, str):
                    # Last resort: try to resolve common string annotations
                    base_annotation = annotation.split("|", 1)[0].strip().strip("'\"")
                    if base_annotation == "int":
                        annotation = int
                    elif base_annotation == "float":
                        annotation = float
                    elif base_annotation == "bool":
                        annotation = bool
                    elif base_annotation == "str":
                        annotation = str
                    else:
                        # Can't resolve, skip type checking
                        continue

            # Handle Optional/Union types (e.g., int | None, Optional[int])
            # Python 3.10+ uses types.UnionType for `|` syntax (e.g., float | None)
            # typing.Union for older syntax
            if hasattr(annotation, "__args__"):
                args = annotation.__args__
                if type(None) in args:
                    # Optional type - extract the non-None type
                    non_none_types = [t for t in args if t is not type(None)]
                    if non_none_types:
                        annotation = non_none_types[0]
                    else:
                        continue
                else:
                    # Union of multiple non-None types - skip complex unions
                    continue

            # Skip if still can't resolve to a concrete type
            if annotation == inspect.Parameter.empty or not isinstance(annotation, type):
                continue

            # Basic type checking with pragmatic numeric widening
            if annotation is int:
                if not isinstance(value, int):
                    raise ValueError(
                        f"Tool '{tool_name}' parameter '{param_name}' must be int, "
                        f"got {type(value).__name__}"
                    )
            elif annotation is float:
                # Pragmatic: allow int → float conversion (numeric widening)
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Tool '{tool_name}' parameter '{param_name}' must be float, "
                        f"got {type(value).__name__}"
                    )
            elif annotation is bool:
                if not isinstance(value, bool):
                    raise ValueError(
                        f"Tool '{tool_name}' parameter '{param_name}' must be bool, "
                        f"got {type(value).__name__}"
                    )
            elif annotation is str:
                if not isinstance(value, str):
                    raise ValueError(
                        f"Tool '{tool_name}' parameter '{param_name}' must be str, "
                        f"got {type(value).__name__}"
                    )

        return bound

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
            """
            Execute the function with validated inputs.
            """
            bound = self._validate_and_bind_arguments(tool_name, func, sig, inputs)
            return func(**bound.arguments)

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
            tools_dict = module.TOOLS
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

    def set_session_context(self, **context) -> None:
        """
        Set session context to auto-inject into tool calls.

        Args:
            **context: Key-value pairs to inject (e.g., workspace_id, agent_id, session_id)
        """
        self._session_context.update(context)

    def register_mcp_server(
        self,
        server_config: dict[str, Any],
    ) -> int:
        """
        Register an MCP server and discover its tools.

        Args:
            server_config: MCP server configuration dict with keys:
                - name: Server name (required)
                - transport: "stdio" or "http" (required)
                - command: Command to run (for stdio)
                - args: Command arguments (for stdio)
                - env: Environment variables (for stdio)
                - cwd: Working directory (for stdio)
                - url: Server URL (for http)
                - headers: HTTP headers (for http)
                - description: Server description (optional)

        Returns:
            Number of tools registered from this server
        """
        try:
            from framework.runner.mcp_client import MCPClient, MCPServerConfig

            # Build config object
            config = MCPServerConfig(
                name=server_config["name"],
                transport=server_config["transport"],
                command=server_config.get("command"),
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
                cwd=server_config.get("cwd"),
                url=server_config.get("url"),
                headers=server_config.get("headers", {}),
                description=server_config.get("description", ""),
            )

            # Create and connect client
            client = MCPClient(config)
            client.connect()

            # Store client for cleanup
            self._mcp_clients.append(client)

            # Register each tool
            count = 0
            for mcp_tool in client.list_tools():
                # Convert MCP tool to framework Tool
                tool = self._convert_mcp_tool_to_framework_tool(mcp_tool)

                # Create executor that calls the MCP server
                def make_mcp_executor(client_ref: MCPClient, tool_name: str, registry_ref):
                    def executor(inputs: dict) -> Any:
                        try:
                            # Inject session context for tools that need it
                            merged_inputs = {**registry_ref._session_context, **inputs}
                            result = client_ref.call_tool(tool_name, merged_inputs)
                            # MCP tools return content array, extract the result
                            if isinstance(result, list) and len(result) > 0:
                                if isinstance(result[0], dict) and "text" in result[0]:
                                    return result[0]["text"]
                                return result[0]
                            return result
                        except Exception as e:
                            logger.error(f"MCP tool '{tool_name}' execution failed: {e}")
                            return {"error": str(e)}

                    return executor

                self.register(
                    mcp_tool.name,
                    tool,
                    make_mcp_executor(client, mcp_tool.name, self),
                )
                count += 1

            logger.info(f"Registered {count} tools from MCP server '{config.name}'")
            return count

        except Exception as e:
            logger.error(f"Failed to register MCP server: {e}")
            return 0

    def _convert_mcp_tool_to_framework_tool(self, mcp_tool: Any) -> Tool:
        """
        Convert an MCP tool to a framework Tool.

        Args:
            mcp_tool: MCPTool object

        Returns:
            Framework Tool object
        """
        # Extract parameters from MCP input schema
        input_schema = mcp_tool.input_schema
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        # Convert to framework Tool format
        tool = Tool(
            name=mcp_tool.name,
            description=mcp_tool.description,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )

        return tool

    def cleanup(self) -> None:
        """Clean up all MCP client connections."""
        for client in self._mcp_clients:
            try:
                client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting MCP client: {e}")
        self._mcp_clients.clear()

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


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
