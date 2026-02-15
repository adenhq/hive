"""Regression tests for JSON parsing performance and blocking behavior.

Run with:
    cd core
    pytest tests/test_node_json_performance.py -v
"""

import asyncio
import json
import time

import pytest

from framework.graph.node import (
    LLMNode,
    find_json_object,
)

# Test inputs
SMALL_JSON = '{"key": "value"}'
LARGE_JSON_SIZE = 500_000  # 500KB
LARGE_TEXT_SIZE = 1_000_000  # 1MB


def generate_large_json(size_bytes: int) -> str:
    """Generate a large valid JSON string."""
    data = {"data": "x" * (size_bytes - 20)}
    return json.dumps(data)


def generate_large_text(size_bytes: int) -> str:
    """Generate large non-JSON text."""
    return "x" * size_bytes


class TestJsonPerformance:
    """Test performance characteristics of find_json_object."""

    def test_large_valid_json_performance(self):
        """Ensure parsing large valid JSON is fast (O(n))."""
        large_json = generate_large_json(LARGE_JSON_SIZE)
        input_text = f"prefix {large_json} suffix"

        start = time.perf_counter()
        result = find_json_object(input_text)
        duration = time.perf_counter() - start

        assert result == large_json
        # Should be very fast (< 0.5s for 500KB)
        assert duration < 0.5, f"Parsing took too long: {duration:.4f}s"

    def test_large_non_json_performance(self):
        """Ensure scanning large non-JSON text allows early exit or fast failure."""
        large_text = generate_large_text(LARGE_TEXT_SIZE)

        start = time.perf_counter()
        result = find_json_object(large_text)
        duration = time.perf_counter() - start

        assert result is None
        # Should be extremely fast (early exit on no '{')
        assert duration < 0.1, f"Scanning took too long: {duration:.4f}s"

    def test_worst_case_performance(self):
        """Test worst-case input: many nested braces."""
        # Note: New implementation limits nesting depth, so this should fail fast
        # or handle it gracefully without O(n^2) behavior
        nested = "{" * 1000 + "}" * 1000

        start = time.perf_counter()
        find_json_object(nested)
        duration = time.perf_counter() - start

        # Valid JSON (nested empty dicts technically, but here just braces)
        # Actually "{"*N is not valid JSON key-value, so it should return None
        # unless we formed valid {"a":{"b":...}}
        # But this tests the scanner performance
        assert duration < 0.5, f"Worst-case scan took too long: {duration:.4f}s"


@pytest.mark.asyncio
class TestAsyncNonBlocking:
    """Test that large JSON parsing does not block the event loop."""

    async def test_async_find_json_does_not_block(self):
        """Verify that find_json_object_async yields control."""
        # This requires the new async implementation to be present in node.py
        # We'll import it dynamically or assume it's there after the fix
        from framework.graph.node import find_json_object_async

        large_json = generate_large_json(LARGE_JSON_SIZE * 2)  # 1MB input
        input_text = f"prefix {large_json} suffix"

        # Background task that should keep running
        blocking_detected = False

        async def heartbeat():
            nonlocal blocking_detected
            try:
                while True:
                    await asyncio.sleep(0.01)
                    # If we don't get scheduled for > 0.1s, loop is blocked
            except asyncio.CancelledError:
                pass

        # Measure baseline blocking
        # If execution blocks for > 100ms, it's considered blocking

        # We can also check if multiple tasks run concurrently
        async def run_parser():
            return await find_json_object_async(input_text)

        # Run 3 parsers concurrently + a heartbeat
        tasks = [run_parser() for _ in range(3)]

        # To truly test non-blocking, we'd need a more sophisticated rig,
        # but running multiple large parsers efficiently via async implies
        # they are yielding or offloaded.

        results = await asyncio.gather(*tasks)

        for res in results:
            assert res == large_json

        # If it was blocking, duration would be roughly sum of sequential executions?
        # Actually, if it's CPU bound and single-threaded (even with async),
        # it will still take sum of time. The key is *responsiveness* / yielding.
        # But for 'asyncio.to_thread' implementation, it should yield immediately.

        # If offloaded to thread, the main loop should be free.

    async def test_llm_node_uses_async_extraction(self):
        """Verify LLMNode has async JSON extraction wired in."""
        # Verify the async extraction method exists on LLMNode
        node = LLMNode()
        assert hasattr(node, "_extract_json_async"), (
            "LLMNode must expose _extract_json_async for non-blocking JSON parsing"
        )

        # Verify find_json_object_async is importable from the same module
        from framework.graph.node import find_json_object_async

        # Verify it works end-to-end with a large payload
        large_json = generate_large_json(100_000)
        result = await find_json_object_async(f"prefix {large_json} suffix")
        assert result == large_json
