"""
Tests for core GraphExecutor execution paths.
Focused on minimal success and failure scenarios.
"""

import pytest

from framework.graph.edge import GraphSpec
from framework.graph.executor import GraphExecutor
from framework.graph.goal import Goal
from framework.graph.node import NodeResult, NodeSpec


# ---- Dummy runtime (no real logging) ----
class DummyRuntime:
    def start_run(self, **kwargs):
        return "run-1"

    def end_run(self, **kwargs):
        pass

    def report_problem(self, **kwargs):
        pass


# ---- Fake node that always succeeds ----
class SuccessNode:
    def validate_input(self, ctx):
        return []

    async def execute(self, ctx):
        return NodeResult(
            success=True,
            output={"result": 123},
            tokens_used=1,
            latency_ms=1,
        )


@pytest.mark.asyncio
async def test_executor_single_node_success():
    runtime = DummyRuntime()

    graph = GraphSpec(
        id="graph-1",
        goal_id="g1",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="test node",
                node_type="llm_generate",
                input_keys=[],
                output_keys=["result"],
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    executor = GraphExecutor(
        runtime=runtime,
        node_registry={"n1": SuccessNode()},
    )

    goal = Goal(
        id="g1",
        name="test-goal",
        description="simple test",
    )

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is True
    assert result.path == ["n1"]
    assert result.steps_executed == 1


# ---- Fake node that always fails ----
class FailingNode:
    def validate_input(self, ctx):
        return []

    async def execute(self, ctx):
        return NodeResult(
            success=False,
            error="boom",
            output={},
            tokens_used=0,
            latency_ms=0,
        )


@pytest.mark.asyncio
async def test_executor_single_node_failure():
    runtime = DummyRuntime()

    graph = GraphSpec(
        id="graph-2",
        goal_id="g2",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="failing node",
                node_type="llm_generate",
                input_keys=[],
                output_keys=["result"],
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    executor = GraphExecutor(
        runtime=runtime,
        node_registry={"n1": FailingNode()},
    )

    goal = Goal(
        id="g2",
        name="fail-goal",
        description="failure test",
    )

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is False
    assert result.error is not None
    assert result.path == ["n1"]


# ---- Fake node with configurable output ----
class ConfigurableOutputNode:
    """Node that returns configurable output."""

    def __init__(self, output: dict):
        self._output = output

    def validate_input(self, ctx):
        return []

    async def execute(self, ctx):
        return NodeResult(
            success=True,
            output=self._output,
            tokens_used=1,
            latency_ms=1,
        )


# ---- Tests for nullable_keys derived from output_schema ----


@pytest.mark.asyncio
async def test_executor_nullable_output_schema_passes_validation():
    """Node with output_schema marking a key as not required should accept None values."""
    graph = GraphSpec(
        id="graph-nullable",
        goal_id="g1",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="node with optional output",
                node_type="llm_generate",
                input_keys=[],
                output_keys=["answer", "clarification_reason"],
                output_schema={
                    "answer": {"type": "string", "required": True},
                    "clarification_reason": {"type": "string", "required": False},
                },
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    node = ConfigurableOutputNode({"answer": "hello", "clarification_reason": None})
    executor = GraphExecutor(
        runtime=DummyRuntime(),
        node_registry={"n1": node},
    )
    goal = Goal(id="g1", name="test", description="test")

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is True
    assert result.path == ["n1"]


@pytest.mark.asyncio
async def test_executor_required_output_key_none_fails_validation():
    """Node with output_schema marking a key as required should reject None values."""
    graph = GraphSpec(
        id="graph-required",
        goal_id="g2",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="node with required output",
                node_type="llm_generate",
                input_keys=[],
                output_keys=["answer", "clarification_reason"],
                output_schema={
                    "answer": {"type": "string", "required": True},
                    "clarification_reason": {"type": "string", "required": True},
                },
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    node = ConfigurableOutputNode({"answer": "hello", "clarification_reason": None})
    executor = GraphExecutor(
        runtime=DummyRuntime(),
        node_registry={"n1": node},
    )
    goal = Goal(id="g2", name="test", description="test")

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is False
    assert result.error is not None
    assert "Output validation failed" in result.error


@pytest.mark.asyncio
async def test_executor_no_output_schema_none_fails_validation():
    """Without output_schema, None values should fail validation."""
    graph = GraphSpec(
        id="graph-no-schema",
        goal_id="g3",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="node without output schema",
                node_type="llm_generate",
                input_keys=[],
                output_keys=["answer", "optional_field"],
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    node = ConfigurableOutputNode({"answer": "hello", "optional_field": None})
    executor = GraphExecutor(
        runtime=DummyRuntime(),
        node_registry={"n1": node},
    )
    goal = Goal(id="g3", name="test", description="test")

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is False
    assert result.error is not None and "Output validation failed" in result.error


@pytest.mark.asyncio
async def test_executor_mixed_required_and_optional_keys():
    """Only keys with required=False in output_schema should be nullable."""
    graph = GraphSpec(
        id="graph-mixed",
        goal_id="g4",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="mixed required and optional",
                node_type="llm_generate",
                input_keys=[],
                output_keys=["a", "b", "c"],
                output_schema={
                    "a": {"type": "string", "required": True},
                    "b": {"type": "string", "required": False},
                    "c": {"type": "string", "required": False},
                },
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    node = ConfigurableOutputNode({"a": "value", "b": None, "c": None})
    executor = GraphExecutor(
        runtime=DummyRuntime(),
        node_registry={"n1": node},
    )
    goal = Goal(id="g4", name="test", description="test")

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is True


@pytest.mark.asyncio
async def test_executor_required_key_none_fails_with_mixed_schema():
    """Required key returning None should still fail even if other keys are nullable."""
    graph = GraphSpec(
        id="graph-mixed-fail",
        goal_id="g5",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="mixed with required None",
                node_type="llm_generate",
                input_keys=[],
                output_keys=["a", "b"],
                output_schema={
                    "a": {"type": "string", "required": True},
                    "b": {"type": "string", "required": False},
                },
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    node = ConfigurableOutputNode({"a": None, "b": None})
    executor = GraphExecutor(
        runtime=DummyRuntime(),
        node_registry={"n1": node},
    )
    goal = Goal(id="g5", name="test", description="test")

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is False
    assert result.error is not None
    assert "Output validation failed" in result.error
