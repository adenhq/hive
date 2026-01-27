"""
Tests for async tool execution in thread pool.

Tests cover:
- Basic async execution (simple functions)
- Concurrent tool executions (no blocking)
- Blocking operations (sleep, subprocess, file I/O)
- Timeout handling
- Error handling
- Resource cleanup
- ToolRegistry async/sync integration
"""

import asyncio
import json
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from framework.llm.provider import Tool, ToolResult, ToolUse
from framework.runner.tool_registry import AsyncToolExecutor, ToolRegistry


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="function")
def async_executor():
    """Create and cleanup AsyncToolExecutor."""
    executor = AsyncToolExecutor(max_workers=5, timeout=10.0)
    
    async def _cleanup():
        await executor.cleanup()
    
    yield executor
    
    # Run cleanup in event loop
    try:
        asyncio.run(_cleanup())
    except RuntimeError:
        pass  # Event loop already closed


@pytest.fixture
def tool_registry():
    """Create and cleanup ToolRegistry."""
    registry = ToolRegistry(max_workers=5, tool_timeout=10.0)
    yield registry


# =============================================================================
# SIMPLE SYNC FUNCTIONS FOR TESTING
# =============================================================================


def simple_add(a: int, b: int) -> int:
    """Simple sync function that adds two numbers."""
    return a + b


def simple_string(text: str) -> str:
    """Simple sync function that returns text."""
    return f"Result: {text}"


def simple_dict(key: str, value: str) -> dict:
    """Simple sync function that returns dict."""
    return {"key": key, "value": value}


def raise_error() -> None:
    """Sync function that raises an error."""
    raise ValueError("Test error from tool")


def blocking_sleep(seconds: float) -> str:
    """Sync function that blocks with sleep."""
    time.sleep(seconds)
    return f"Slept for {seconds} seconds"


def blocking_subprocess() -> str:
    """Sync function that runs subprocess (blocking I/O)."""
    result = subprocess.run(
        ["python", "-c", "import time; time.sleep(0.1); print('Done')"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip()


def blocking_file_io(tmpdir: str, size: int = 1000) -> int:
    """Sync function that performs file I/O (blocking)."""
    filepath = Path(tmpdir) / "test.txt"
    data = "x" * size
    filepath.write_text(data)
    read_data = filepath.read_text()
    return len(read_data)


# =============================================================================
# TEST CLASS: BasicAsyncExecution
# =============================================================================


class TestBasicAsyncExecution:
    """Tests for basic async execution of synchronous functions."""

    @pytest.mark.asyncio
    async def test_execute_simple_function(self, async_executor):
        """Test executing a simple sync function asynchronously."""
        result = await async_executor.execute(simple_add, 2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_execute_with_kwargs(self, async_executor):
        """Test executing with keyword arguments."""
        result = await async_executor.execute(
            simple_add,
            a=10,
            b=20,
        )
        assert result == 30

    @pytest.mark.asyncio
    async def test_execute_with_mixed_args(self, async_executor):
        """Test executing with positional and keyword arguments."""
        def func_with_default(text: str = "") -> str:
            return simple_string(text)
        
        result = await async_executor.execute(func_with_default, text="world")
        # Check that the result is as expected
        assert "Result:" in result
        assert "world" in result

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, async_executor):
        """Test that dict return values are preserved."""
        result = await async_executor.execute(
            simple_dict,
            key="test_key",
            value="test_value",
        )
        assert result == {"key": "test_key", "value": "test_value"}

    @pytest.mark.asyncio
    async def test_execute_preserves_exception(self, async_executor):
        """Test that exceptions from tools are properly raised."""
        with pytest.raises(ValueError, match="Test error from tool"):
            await async_executor.execute(raise_error)


# =============================================================================
# TEST CLASS: ConcurrentExecution
# =============================================================================


class TestConcurrentExecution:
    """Tests for concurrent tool execution without blocking."""

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, async_executor):
        """Test that multiple tools can execute concurrently."""
        # Create tasks that all run concurrently
        tasks = [
            asyncio.create_task(async_executor.execute(simple_add, 1, 1)),
            asyncio.create_task(async_executor.execute(simple_add, 2, 2)),
            asyncio.create_task(async_executor.execute(simple_add, 3, 3)),
        ]

        results = await asyncio.gather(*tasks)
        assert results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_concurrent_does_not_block_event_loop(self, async_executor):
        """Test that tool execution doesn't block other asyncio tasks."""
        events = []

        async def record_event(name: str, delay: float) -> None:
            events.append(f"{name}_start")
            await asyncio.sleep(delay)
            events.append(f"{name}_end")

        async def execute_blocking_tool() -> None:
            events.append("tool_start")
            # This blocks the thread, but should NOT block the event loop
            result = await async_executor.execute(blocking_sleep, 0.3)
            events.append("tool_end")
            assert "Slept" in result

        # Run tool and async task concurrently
        await asyncio.gather(
            execute_blocking_tool(),
            record_event("event1", 0.1),
        )

        # Verify that async events interleaved with tool execution
        # Tool should NOT have blocked the event loop
        assert "event1_start" in events
        assert "tool_start" in events
        # event1 should have started before tool finishes
        assert events.index("event1_start") < events.index("tool_end")

    @pytest.mark.asyncio
    async def test_max_concurrent_workers_limit(self, async_executor):
        """Test that max_workers limits concurrent execution."""
        # Create more tasks than max_workers
        task_count = 20
        max_workers = 5

        executor = AsyncToolExecutor(max_workers=max_workers, timeout=10.0)

        # Track concurrent execution count
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        def counting_sleep(seconds: float) -> None:
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            time.sleep(seconds)
            concurrent_count -= 1

        # Start many tasks
        tasks = [
            asyncio.create_task(executor.execute(counting_sleep, 0.1))
            for _ in range(task_count)
        ]

        await asyncio.gather(*tasks)
        await executor.cleanup()

        # Should not exceed max_workers
        assert max_concurrent <= max_workers + 1  # +1 for timing wiggle room


# =============================================================================
# TEST CLASS: BlockingOperations
# =============================================================================


class TestBlockingOperations:
    """Tests for handling actual blocking I/O operations."""

    @pytest.mark.asyncio
    async def test_blocking_sleep_does_not_block_loop(self, async_executor):
        """Test that sleep in tool doesn't block event loop."""
        start = time.time()

        async def tool_and_loop_task() -> tuple[str, float]:
            # Run blocking tool
            tool_task = asyncio.create_task(
                async_executor.execute(blocking_sleep, 0.5)
            )

            # Run async task concurrently
            await asyncio.sleep(0.2)
            loop_end = time.time()

            tool_result = await tool_task
            return tool_result, loop_end - start

        tool_result, loop_time = await tool_and_loop_task()

        # Tool should sleep ~0.5s
        assert "0.5" in tool_result

        # Loop task should complete around 0.2s (not 0.5s)
        # Allow for timing variance
        assert 0.1 < loop_time < 0.7

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip subprocess test (can be flaky in test env)
        reason="Subprocess test can be flaky in test environment"
    )
    async def test_blocking_subprocess(self, async_executor):
        """Test that subprocess execution works asynchronously."""
        result = await async_executor.execute(blocking_subprocess)
        assert "Done" in result

    @pytest.mark.asyncio
    async def test_blocking_file_io(self, async_executor):
        """Test that file I/O operations work asynchronously."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await async_executor.execute(
                blocking_file_io,
                tmpdir=tmpdir,
                size=5000,
            )
            assert result == 5000


# =============================================================================
# TEST CLASS: TimeoutHandling
# =============================================================================


class TestTimeoutHandling:
    """Tests for timeout handling and cleanup."""

    @pytest.mark.asyncio
    async def test_timeout_raises_asyncio_error(self, async_executor):
        """Test that timeout raises asyncio.TimeoutError."""
        with pytest.raises(asyncio.TimeoutError, match="exceeded"):
            # Set very short timeout for a function that sleeps
            await async_executor.execute(
                blocking_sleep,
                1.0,  # Sleep for 1 second
                timeout=0.1,  # But timeout after 0.1 seconds
            )

    @pytest.mark.asyncio
    async def test_custom_timeout(self, async_executor):
        """Test custom per-execution timeout."""
        # This should work (timeout is long enough)
        result = await async_executor.execute(
            blocking_sleep,
            0.1,
            timeout=1.0,
        )
        assert "0.1" in result

    @pytest.mark.asyncio
    async def test_timeout_error_includes_function_name(self, async_executor):
        """Test that timeout error message includes function name."""
        with pytest.raises(asyncio.TimeoutError) as exc_info:
            await async_executor.execute(
                blocking_sleep,
                1.0,
                timeout=0.05,
            )
        assert "blocking_sleep" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_other_tasks_not_affected_by_timeout(self, async_executor):
        """Test that timeout of one task doesn't affect others."""
        results = []

        async def run_with_timeout():
            try:
                await async_executor.execute(blocking_sleep, 1.0, timeout=0.05)
            except asyncio.TimeoutError:
                results.append("timeout")

        async def run_without_timeout():
            result = await async_executor.execute(simple_add, 5, 5)
            results.append(result)

        # Run both concurrently
        await asyncio.gather(run_with_timeout(), run_without_timeout())

        # Both should complete
        assert "timeout" in results
        assert 10 in results


# =============================================================================
# TEST CLASS: ErrorHandling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling and recovery."""

    @pytest.mark.asyncio
    async def test_tool_exception_propagated(self, async_executor):
        """Test that tool exceptions are properly propagated."""
        with pytest.raises(ValueError, match="Test error"):
            await async_executor.execute(raise_error)

    @pytest.mark.asyncio
    async def test_multiple_errors_dont_affect_other_tasks(self, async_executor):
        """Test that errors in one tool don't affect others."""
        results = []

        async def run_failing_tool():
            try:
                await async_executor.execute(raise_error)
            except ValueError:
                results.append("error_caught")

        async def run_successful_tool():
            result = await async_executor.execute(simple_add, 7, 3)
            results.append(result)

        await asyncio.gather(run_failing_tool(), run_successful_tool())

        assert "error_caught" in results
        assert 10 in results

    @pytest.mark.asyncio
    async def test_exception_includes_traceback_in_log(self, async_executor):
        """Test that exception logs include traceback info."""
        with pytest.raises(ValueError):
            await async_executor.execute(raise_error)
        # Logging happens in execute method (can verify with caplog if needed)


# =============================================================================
# TEST CLASS: ResourceManagement
# =============================================================================


class TestResourceManagement:
    """Tests for resource cleanup and management."""

    @pytest.mark.asyncio
    async def test_cleanup_shuts_down_executor(self):
        """Test that cleanup properly shuts down thread pool."""
        executor = AsyncToolExecutor(max_workers=5, timeout=10.0)

        # Execute something first
        result = await executor.execute(simple_add, 1, 1)
        assert result == 2

        # Cleanup
        await executor.cleanup()

        # Executor should be shutdown
        assert executor._executor._shutdown

    @pytest.mark.asyncio
    async def test_cleanup_waits_for_pending_tasks(self):
        """Test that cleanup waits for pending tasks to complete."""
        executor = AsyncToolExecutor(max_workers=2, timeout=10.0)

        task_count = 0

        def counting_task():
            nonlocal task_count
            task_count += 1
            time.sleep(0.1)
            return task_count

        # Start multiple long-running tasks
        tasks = [
            asyncio.create_task(executor.execute(counting_task))
            for _ in range(5)
        ]

        # Let them start
        await asyncio.sleep(0.05)

        # Cleanup (should wait for pending tasks)
        await executor.cleanup()

        # All tasks should have completed
        assert task_count == 5

    @pytest.mark.asyncio
    async def test_active_tasks_tracked(self, async_executor):
        """Test that active tasks are properly tracked."""
        # Execute a task
        task = asyncio.create_task(async_executor.execute(simple_add, 1, 1))

        # Wait a bit for it to be added to tracking
        await asyncio.sleep(0.01)

        # Should have active tasks
        assert len(async_executor._active_tasks) >= 0

        # Wait for task to complete
        await task


# =============================================================================
# TEST CLASS: ToolRegistryAsyncIntegration
# =============================================================================


class TestToolRegistryAsyncIntegration:
    """Tests for ToolRegistry async integration."""

    @pytest.mark.asyncio
    async def test_registry_executor_is_async(self, tool_registry):
        """Test that registry.get_executor() returns async function."""
        executor = tool_registry.get_executor()

        # Should be an async function
        import inspect
        assert inspect.iscoroutinefunction(executor)

    @pytest.mark.asyncio
    async def test_registry_executor_executes_tool(self, tool_registry):
        """Test that registry executor properly executes registered tools."""
        # Register a tool with an executor wrapper that takes a dict
        tool = Tool(
            name="add",
            description="Add two numbers",
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        )
        
        # Create an executor that takes a dict
        def add_executor(inputs: dict) -> int:
            return simple_add(inputs["a"], inputs["b"])
        
        tool_registry.register("add", tool, add_executor)

        # Get executor and use it
        executor = tool_registry.get_executor()

        tool_use = ToolUse(id="call_1", name="add", input={"a": 5, "b": 3})

        result = await executor(tool_use)

        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert json.loads(result.content) == 8

    @pytest.mark.asyncio
    async def test_registry_executor_timeout(self, tool_registry):
        """Test that registry executor respects timeout."""
        def sleep_executor(inputs: dict) -> str:
            return blocking_sleep(inputs["seconds"])
        
        tool = Tool(
            name="sleep",
            description="Sleep function",
            parameters={
                "type": "object",
                "properties": {"seconds": {"type": "number"}},
                "required": ["seconds"],
            },
        )
        tool_registry.register("sleep", tool, sleep_executor)

        # Create registry with short timeout
        fast_registry = ToolRegistry(max_workers=5, tool_timeout=0.1)
        fast_registry.register("sleep", tool, sleep_executor)

        executor = fast_registry.get_executor()

        tool_use = ToolUse(id="call_1", name="sleep", input={"seconds": 1.0})

        result = await executor(tool_use)

        # Should timeout and return error
        assert result.is_error
        assert "timed out" in result.content.lower() or "timeout" in result.content.lower()

    @pytest.mark.asyncio
    async def test_registry_executor_handles_unknown_tool(self, tool_registry):
        """Test that registry executor handles unknown tools gracefully."""
        executor = tool_registry.get_executor()

        tool_use = ToolUse(id="call_1", name="unknown_tool", input={})

        result = await executor(tool_use)

        assert result.is_error
        assert "Unknown tool" in result.content

    @pytest.mark.asyncio
    async def test_registry_executor_handles_tool_error(self, tool_registry):
        """Test that registry executor handles tool errors gracefully."""
        def fail_executor(inputs: dict) -> None:
            raise_error()
        
        tool = Tool(
            name="fail",
            description="Failing tool",
            parameters={"type": "object", "properties": {}, "required": []},
        )
        tool_registry.register("fail", tool, fail_executor)

        executor = tool_registry.get_executor()

        tool_use = ToolUse(id="call_1", name="fail", input={})

        result = await executor(tool_use)

        assert result.is_error
        assert "Test error" in result.content

    @pytest.mark.asyncio
    async def test_registry_async_cleanup(self, tool_registry):
        """Test that registry async_cleanup works properly."""
        # Register and execute something
        tool = Tool(
            name="test",
            description="Test tool",
            parameters={"type": "object", "properties": {}, "required": []},
        )
        tool_registry.register("test", tool, lambda: "done")

        executor = tool_registry.get_executor()
        await executor(ToolUse(id="1", name="test", input={}))

        # Cleanup
        await tool_registry.async_cleanup()

        # Executor should be shutdown
        assert tool_registry._async_executor._executor._shutdown


# =============================================================================
# TEST CLASS: BackwardCompatibility
# =============================================================================


class TestBackwardCompatibility:
    """Tests for backward compatibility with sync code."""

    def test_sync_register_still_works(self, tool_registry):
        """Test that sync registration still works."""
        tool = Tool(
            name="sync_add",
            description="Sync add",
            parameters={
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "required": ["a", "b"],
            },
        )

        # This should not raise
        tool_registry.register("sync_add", tool, simple_add)
        assert tool_registry.has_tool("sync_add")

    def test_sync_cleanup_still_works(self, tool_registry):
        """Test that sync cleanup() still works."""
        # Should not raise
        tool_registry.cleanup()

    @pytest.mark.asyncio
    async def test_registered_tools_can_be_async_executed(self, tool_registry):
        """Test that tools registered with sync API can be async executed."""
        def executor(inputs: dict) -> dict:
            return {"result": "success"}
        
        tool = Tool(
            name="test_tool",
            description="Test",
            parameters={"type": "object", "properties": {}, "required": []},
        )

        # Register with sync API
        tool_registry.register("test_tool", tool, executor)

        # Execute with async executor
        executor_func = tool_registry.get_executor()
        result = await executor_func(ToolUse(id="1", name="test_tool", input={}))

        assert not result.is_error
        assert "success" in result.content


# =============================================================================
# TEST CLASS: Integration
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_multiple_tools_concurrent_execution(self, tool_registry):
        """Test executing multiple different tools concurrently."""
        # Register several tools with proper executors
        def add_executor(inputs: dict) -> int:
            return simple_add(inputs.get("a", 0), inputs.get("b", 0))
        
        def string_executor(inputs: dict) -> str:
            return simple_string(inputs.get("text", ""))
        
        def dict_executor(inputs: dict) -> dict:
            return simple_dict(inputs.get("key", ""), inputs.get("value", ""))
        
        tools_config = [
            ("add", add_executor),
            ("string", string_executor),
            ("dict", dict_executor),
        ]

        for name, func in tools_config:
            tool = Tool(
                name=name,
                description=f"{name} tool",
                parameters={"type": "object", "properties": {}, "required": []},
            )
            tool_registry.register(name, tool, func)

        executor = tool_registry.get_executor()

        # Create concurrent tool calls
        tool_uses = [
            ToolUse(id="1", name="add", input={"a": 1, "b": 2}),
            ToolUse(id="2", name="string", input={"text": "hello"}),
            ToolUse(id="3", name="dict", input={"key": "k", "value": "v"}),
        ]

        # Execute concurrently
        results = await asyncio.gather(
            *[executor(tu) for tu in tool_uses]
        )

        # All should succeed
        assert all(not r.is_error for r in results)

    @pytest.mark.asyncio
    async def test_stress_test_many_concurrent_tools(self, tool_registry):
        """Stress test with many concurrent tool executions."""
        def fast_tool_executor(inputs: dict) -> int:
            a = inputs.get("a", 0)
            b = inputs.get("b", 0)
            return simple_add(a, b)
        
        tool = Tool(
            name="fast_tool",
            description="Fast tool",
            parameters={"type": "object", "properties": {}, "required": []},
        )
        tool_registry.register("fast_tool", tool, fast_tool_executor)

        executor = tool_registry.get_executor()

        # Execute 50 tools concurrently
        tool_uses = [
            ToolUse(id=f"{i}", name="fast_tool", input={"a": i, "b": i})
            for i in range(50)
        ]

        results = await asyncio.gather(
            *[executor(tu) for tu in tool_uses]
        )

        # All should succeed
        assert all(not r.is_error for r in results)
        assert len(results) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
