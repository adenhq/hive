import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from framework.runtime.stream_runtime import StreamRuntime
from framework.schemas.decision import DecisionType
from framework.schemas.run import RunStatus


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.save_run = AsyncMock()
    return storage


@pytest.fixture
def mock_aggregator():
    aggregator = MagicMock()
    aggregator.record_decision = MagicMock()
    aggregator.record_outcome = MagicMock()
    return aggregator


@pytest.fixture
def runtime(mock_storage, mock_aggregator):
    return StreamRuntime(
        stream_id="test_stream", storage=mock_storage, outcome_aggregator=mock_aggregator
    )


@pytest.mark.asyncio
async def test_stream_runtime_workflow(runtime):
    """Test full lifecycle of a run within StreamRuntime."""
    # 1. Start Run
    run_id = runtime.start_run(
        execution_id="exec_1", goal_id="goal_1", goal_description="Test Goal"
    )
    assert run_id.startswith("run_test_stream_")
    assert "exec_1" in runtime._runs

    # 2. Make Decision
    decision_id = runtime.decide(
        execution_id="exec_1",
        intent="Test Intent",
        options=[{"id": "opt1", "description": "Option 1"}],
        chosen="opt1",
        reasoning="Because",
        decision_type=DecisionType.TOOL_SELECTION,
    )
    assert decision_id == "dec_0"

    # Verify decision recorded
    run = runtime.get_run("exec_1")
    assert len(run.decisions) == 1
    assert run.decisions[0].id == "dec_0"

    # 3. Record Outcome
    runtime.record_outcome(
        execution_id="exec_1", decision_id=decision_id, success=True, result="Success"
    )
    assert run.decisions[0].outcome.success is True

    # 4. End Run
    runtime.end_run(execution_id="exec_1", success=True, narrative="Done")

    # Verify cleanup and persistence
    assert run.status == RunStatus.COMPLETED
    # Wait for async save
    await asyncio.sleep(0.1)
    runtime._storage.save_run.assert_called_once()
    assert "exec_1" not in runtime._runs


def test_decide_no_run(runtime):
    """Test decide stops if no run exists."""
    decision_id = runtime.decide(
        execution_id="missing_exec", intent="intent", options=[], chosen="opt", reasoning="reason"
    )
    assert decision_id == ""


def test_end_run_no_run(runtime):
    """Test end_run handles missing run gracefully."""
    # Should simply return/log without error
    runtime.end_run("missing_exec", True)


def test_quick_decision(runtime):
    """Test simple quick_decision wrapper."""
    runtime.start_run("exec_2", "goal_2")
    decision_id = runtime.quick_decision(
        execution_id="exec_2", intent="intent", action="action", reasoning="reason"
    )
    assert decision_id == "dec_0"
    run = runtime.get_run("exec_2")
    assert run.decisions[0].options[0].id == "action"
