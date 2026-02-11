"""
Regression test for CancelledError handler missing end_run() call.

The execution_stream.py CancelledError handler calls start_run() (via
StreamRuntimeAdapter) but never called end_run(), causing observability
run data to be silently lost.  After the fix, end_run() is called so
the trace context is properly closed.

Covers issue #4515.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from framework.graph import Goal, NodeSpec, SuccessCriterion
from framework.graph.edge import GraphSpec
from framework.graph.executor import GraphExecutor
from framework.runtime.event_bus import EventBus
from framework.runtime.execution_stream import EntryPointSpec, ExecutionStream
from framework.runtime.outcome_aggregator import OutcomeAggregator
from framework.runtime.shared_state import SharedStateManager
from framework.storage.concurrent import ConcurrentStorage


@pytest.mark.asyncio
async def test_cancelled_execution_calls_end_run(tmp_path):
    """
    When an execution is cancelled, end_run() must be called on the
    runtime adapter so the trace context opened by start_run() is closed.

    Before the fix, the CancelledError handler did NOT call end_run(),
    causing run observability data to be silently lost.
    """
    goal = Goal(
        id="test-goal",
        name="Test Goal",
        description="Cancellation test",
        success_criteria=[
            SuccessCriterion(
                id="result",
                description="Result present",
                metric="output_contains",
                target="result",
            )
        ],
        constraints=[],
    )

    node = NodeSpec(
        id="slow",
        name="Slow",
        description="A slow node",
        node_type="llm_generate",
        input_keys=[],
        output_keys=["result"],
        system_prompt='Return JSON: {"result": "ok"}',
    )

    graph = GraphSpec(
        id="test-graph",
        goal_id=goal.id,
        version="1.0.0",
        entry_node="slow",
        entry_points={"start": "slow"},
        terminal_nodes=["slow"],
        pause_nodes=[],
        nodes=[node],
        edges=[],
        default_model="dummy",
        max_tokens=10,
    )

    storage = ConcurrentStorage(tmp_path)
    await storage.start()

    stream = ExecutionStream(
        stream_id="start",
        entry_spec=EntryPointSpec(
            id="start",
            name="Start",
            entry_node="slow",
            trigger_type="manual",
            isolation_level="shared",
        ),
        graph=graph,
        goal=goal,
        state_manager=SharedStateManager(),
        storage=storage,
        outcome_aggregator=OutcomeAggregator(goal, EventBus()),
        event_bus=None,
        llm=None,
        tools=[],
        tool_executor=None,
    )

    await stream.start()

    # Slow async coroutine that can be cancelled at the await point
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(30)

    # Track end_run calls on the StreamRuntime
    end_run_calls: list[dict] = []
    original_end_run = stream._runtime.end_run

    def tracking_end_run(**kwargs):
        end_run_calls.append(kwargs)
        return original_end_run(**kwargs)

    with (
        patch.object(GraphExecutor, "execute", side_effect=slow_execute),
        patch.object(stream._runtime, "end_run", side_effect=tracking_end_run),
    ):
        execution_id = await stream.execute({})

        # Give the execution a moment to start (so start_run is called)
        await asyncio.sleep(0.2)

        # Cancel the execution — this cancels the asyncio task,
        # interrupting slow_execute at its await point.
        cancelled = await stream.cancel_execution(execution_id)
        assert cancelled is True

    # After cancellation, end_run should have been called
    assert len(end_run_calls) >= 1, (
        "end_run() was never called after cancellation — run observability data was silently lost"
    )

    # The run should indicate failure (cancellation is not success)
    last_call = end_run_calls[-1]
    assert last_call.get("success") is False

    await stream.stop()
    await storage.stop()
