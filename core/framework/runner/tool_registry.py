"""Tool discovery and registration for agent runner."""

import asyncio
import importlib.util
import inspect
import json
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ExecutorTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from framework.llm.provider import Tool, ToolUse, ToolResult

logger = logging.getLogger(__name__)


class AsyncToolExecutor:
    """
    Executes synchronous tool functions asynchronously in a thread pool.

    Prevents blocking the asyncio event loop when tools perform blocking I/O
    (subprocess.run, file operations, network calls, sleep, etc.).

    Configuration:
        max_workers: Maximum concurrent tool executions (default: 10)
        timeout: Default timeout per tool execution in seconds (default: 30)

    Example:
        async_executor = AsyncToolExecutor(max_workers=10, timeout=30.0)
        result = await async_executor.execute(blocking_func, arg1, arg2)
        await async_executor.cleanup()
    """

    def __init__(
        self,
        max_workers: int = 10,
        timeout: float = 30.0,
    ):
        """
        Initialize async tool executor.

        Args:
            max_workers: Maximum number of concurrent tool executions
            timeout: Default timeout in seconds for each tool execution
        """
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="aden-tool-",
        )
        self._timeout = timeout
        self._active_tasks: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
        logger.debug(
            f"Initialized AsyncToolExecutor with {max_workers} workers, "
            f"{timeout}s timeout"
        )

    async def execute(
        self,
        func: Callable,
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a synchronous function in the thread pool.

        Args:
            func: Synchronous function to execute
            *args: Positional arguments for func
            timeout: Timeout in seconds (uses default if None)
            **kwargs: Keyword arguments for func

        Returns:
            Return value of func

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
            Exception: Any exception raised by func
        """
        timeout = timeout or self._timeout

        try:
            # Get the current event loop and run function in executor
            loop = asyncio.get_event_loop()

            # Create a task for tracking
            task = asyncio.create_task(
                asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor,
                        self._safe_call,
                        func,
                        args,
                        kwargs,
                    ),
                    timeout=timeout,
                )
            )

            # Track active task
            async with self._lock:
                self._active_tasks.add(task)
                task.add_done_callback(
                    lambda t: self._active_tasks.discard(t)
                )

            # Execute and return result
            result = await task
            return result

        except asyncio.TimeoutError:
            logger.warning(
                f"Tool execution timeout after {timeout}s: {func.__name__}"
            )
            raise asyncio.TimeoutError(
                f"Tool '{func.__name__}' exceeded {timeout}s timeout"
            ) from None
        except Exception as e:
            logger.error(
                f"Tool execution error in {func.__name__}: {e}",
                exc_info=True,
            )
            raise

    @staticmethod
    def _safe_call(
        func: Callable,
        args: tuple,
        kwargs: dict,
    ) -> Any:
        """
        Safely call function with arguments. Used in executor.
        
        Handles both:
        - Functions called with **kwargs unpacking: func(**input_dict)
        - Functions called with positional args: func(arg1, arg2)
        """
        # If we have kwargs but no args, unpack kwargs
        if kwargs and not args:
            return func(**kwargs)
        # If we have both args and kwargs, pass both (common case)
        elif args and kwargs:
            return func(*args, **kwargs)
        # If we only have args, pass them positionally
        elif args:
            return func(*args)
        # If nothing, call with no arguments
        else:
            return func()

    async def cleanup(self) -> None:
        """
        Cleanup: wait for pending tasks and shutdown executor.

        Should be called before process exit to allow graceful shutdown.
        """
        # Wait for active tasks with timeout
        if self._active_tasks:
            logger.debug(f"Waiting for {len(self._active_tasks)} active tasks...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"Cleanup timeout: {len(self._active_tasks)} tasks still running"
                )

        # Shutdown executor
        self._executor.shutdown(wait=False)
        logger.debug("AsyncToolExecutor cleaned up")


@dataclass
class RegisteredTool:
    """A tool with its executor function."""

    tool: Tool
    executor: Callable[[dict], Any]
    is_async: bool = False  # True if executor is async


class ToolRegistry:
    """
    Manages tool discovery and registration.

    Tool Discovery Order:
    1. Built-in tools (if any)
    2. tools.py in agent folder
    3. MCP servers
    4. Manually registered tools
    """

    def __init__(
        self,
        max_workers: int = 10,
        tool_timeout: float = 30.0,
    ):
        """
        Initialize tool registry.

        Args:
            max_workers: Maximum concurrent tool executions in thread pool
            tool_timeout: Default timeout in seconds for tool execution
        """
        self._tools: dict[str, RegisteredTool] = {}
        self._mcp_clients: list[Any] = []  # List of MCPClient instances
        self._session_context: dict[str, Any] = {}  # Auto-injected context for tools
        self._async_executor = AsyncToolExecutor(
            max_workers=max_workers,
            timeout=tool_timeout,
        )
        logger.debug(
            f"ToolRegistry initialized with async executor: "
            f"{max_workers} workers, {tool_timeout}s timeout"
        )

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
        This executor is ASYNC - it must be awaited.

        The executor:
        1. Routes to the correct tool executor (sync)
        2. Runs it in a thread pool to avoid blocking the event loop
        3. Returns ToolResult with output or error

        Example:
            executor = registry.get_executor()
            result = await executor(tool_use)  # NOTE: Must await!
        """

        async def async_executor(tool_use: ToolUse) -> ToolResult:
            """Async executor that wraps sync execution in thread pool."""
            if tool_use.name not in self._tools:
                return ToolResult(
                    tool_use_id=tool_use.id,
                    content=json.dumps({"error": f"Unknown tool: {tool_use.name}"}),
                    is_error=True,
                )

            registered = self._tools[tool_use.name]
            try:
                # Run the sync executor in thread pool
                # The registered.executor expects to be called with a dict as input
                # For tool executors, we pass the dict as a positional argument
                # For other executors, they can be called directly
                
                # Create a wrapper that calls the executor with the input dict
                def executor_wrapper():
                    return registered.executor(tool_use.input)
                
                result = await self._async_executor.execute(executor_wrapper)

                # Handle different result types
                if isinstance(result, ToolResult):
                    return result

                return ToolResult(
                    tool_use_id=tool_use.id,
                    content=json.dumps(result) if not isinstance(result, str) else result,
                    is_error=False,
                )

            except asyncio.TimeoutError:
                logger.warning(f"Tool '{tool_use.name}' execution timed out")
                return ToolResult(
                    tool_use_id=tool_use.id,
                    content=json.dumps({"error": f"Tool execution timed out"}),
                    is_error=True,
                )
            except Exception as e:
                logger.error(f"Tool '{tool_use.name}' execution failed: {e}")
                return ToolResult(
                    tool_use_id=tool_use.id,
                    content=json.dumps({"error": str(e)}),
                    is_error=True,
                )

        return async_executor

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

    async def async_cleanup(self) -> None:
        """
        Async cleanup: disconnect MCP clients and shutdown async executor.

        Should be called before process exit to allow graceful shutdown.
        """
        # Disconnect MCP clients
        for client in self._mcp_clients:
            try:
                client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting MCP client: {e}")
        self._mcp_clients.clear()

        # Shutdown async executor
        await self._async_executor.cleanup()
        logger.debug("ToolRegistry cleaned up")

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
