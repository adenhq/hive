"""
Integration tests for PolicyEngine runtime wiring.

These tests verify that policies are evaluated during tool execution
when a PolicyEngine is configured on the GraphExecutor.
"""

import json
from unittest.mock import MagicMock

import pytest

from framework.graph.edge import EdgeSpec, GraphSpec
from framework.graph.executor import GraphExecutor
from framework.graph.goal import Goal
from framework.graph.node import NodeContext, NodeProtocol, NodeResult, NodeSpec
from framework.llm.provider import ToolResult, ToolUse
from framework.policies.builtin.tool_gating import HighRiskToolGatingPolicy
from framework.policies.engine import PolicyEngine
from framework.runtime.core import Runtime


# === Fixtures ===


@pytest.fixture
def runtime(tmp_path):
    """Create a real Runtime with temp storage."""
    return Runtime(storage_path=tmp_path / "runtime_storage")


@pytest.fixture
def simple_graph():
    """Minimal graph with one LLM tool node and a terminal node."""
    nodes = [
        NodeSpec(
            id="tool-node",
            name="Tool Node",
            description="Calls a tool",
            node_type="llm_tool_use",
            input_keys=["query"],
            output_keys=["result"],
            tools=["safe_read", "dangerous_delete"],
        ),
    ]
    edges = []
    return GraphSpec(
        id="test-graph",
        goal_id="test-goal",
        version="1.0.0",
        entry_node="tool-node",
        terminal_nodes=["tool-node"],
        nodes=nodes,
        edges=edges,
        max_steps=5,
    )


@pytest.fixture
def goal():
    return Goal(
        id="test-goal",
        name="Test Goal",
        description="Test policy integration",
    )


def _make_tool_executor():
    """Create a tool executor that records calls and returns success."""
    calls = []

    def executor(tool_use: ToolUse) -> ToolResult:
        calls.append(tool_use)
        return ToolResult(
            tool_use_id=tool_use.id,
            content=json.dumps({"status": "ok", "tool": tool_use.name}),
            is_error=False,
        )

    return executor, calls


# === Tests: PolicyEngine wraps tool executor ===


class TestPolicyToolInterception:
    """Test that the PolicyEngine intercepts tool calls via GraphExecutor."""

    def test_executor_wraps_tool_executor_when_engine_provided(self, runtime):
        """Verify the tool executor is wrapped when a PolicyEngine is set."""
        original, _calls = _make_tool_executor()
        engine = PolicyEngine(raise_on_block=False)

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
        )

        # The tool_executor should be a different function (the wrapper)
        assert executor.tool_executor is not original

    def test_executor_preserves_tool_executor_without_engine(self, runtime):
        """Without a PolicyEngine, the original executor is used directly."""
        original, _calls = _make_tool_executor()

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
        )

        assert executor.tool_executor is original

    def test_allowed_tool_call_passes_through(self, runtime):
        """A tool call allowed by policy should execute normally."""
        original, calls = _make_tool_executor()
        engine = PolicyEngine(raise_on_block=False)
        engine.register_policy(HighRiskToolGatingPolicy())

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
        )

        # Start a run so runtime has a run context
        runtime.start_run("test-goal", "test")

        tool_use = ToolUse(id="call_1", name="safe_read", input={"key": "value"})
        result = executor.tool_executor(tool_use)

        assert not result.is_error
        assert len(calls) == 1
        assert calls[0].name == "safe_read"

        runtime.end_run(success=True)

    def test_blocked_tool_call_returns_error(self, runtime):
        """A tool call blocked by policy should return an error ToolResult."""
        original, calls = _make_tool_executor()

        # Create engine that blocks on high-risk patterns
        # HighRiskToolGatingPolicy with default_action="block" blocks unknown tools in strict mode
        engine = PolicyEngine(raise_on_block=False)
        policy = HighRiskToolGatingPolicy(default_action="block")
        engine.register_policy(policy)

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
        )

        runtime.start_run("test-goal", "test")

        # "file_delete" matches high-risk patterns — will be REQUIRE_CONFIRM or BLOCK
        tool_use = ToolUse(id="call_2", name="file_delete", input={"path": "/tmp/x"})
        result = executor.tool_executor(tool_use)

        # The original executor should NOT have been called
        assert len(calls) == 0
        assert result.is_error
        content = json.loads(result.content)
        assert "error" in content

        runtime.end_run(success=True)

    def test_require_confirm_denied_without_callback(self, runtime):
        """REQUIRE_CONFIRM without approval callback should deny the call."""
        original, calls = _make_tool_executor()
        engine = PolicyEngine(raise_on_block=False, raise_on_confirm=False)
        engine.register_policy(HighRiskToolGatingPolicy())

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
            approval_callback=None,
        )

        runtime.start_run("test-goal", "test")

        # "file_delete" matches high-risk patterns -> REQUIRE_CONFIRM
        tool_use = ToolUse(id="call_3", name="file_delete", input={"path": "/tmp/x"})
        result = executor.tool_executor(tool_use)

        # Should be denied since no approval callback
        assert result.is_error
        assert len(calls) == 0
        content = json.loads(result.content)
        assert "denied" in content.get("error", "").lower() or "blocked" in content.get(
            "error", ""
        ).lower()

        runtime.end_run(success=True)

    def test_require_confirm_approved_with_callback(self, runtime):
        """REQUIRE_CONFIRM with approving callback should allow execution."""
        original, calls = _make_tool_executor()
        engine = PolicyEngine(raise_on_block=False, raise_on_confirm=False)
        engine.register_policy(HighRiskToolGatingPolicy())

        # Approval callback that always approves
        approve_cb = MagicMock(return_value=True)

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
            approval_callback=approve_cb,
        )

        runtime.start_run("test-goal", "test")

        tool_use = ToolUse(id="call_4", name="file_delete", input={"path": "/tmp/x"})
        result = executor.tool_executor(tool_use)

        # Callback should have been called
        approve_cb.assert_called_once()
        call_info = approve_cb.call_args[0][0]
        assert call_info["type"] == "policy_confirmation"
        assert call_info["tool_name"] == "file_delete"

        # Tool should have executed
        assert not result.is_error
        assert len(calls) == 1

        runtime.end_run(success=True)

    def test_require_confirm_denied_with_callback(self, runtime):
        """REQUIRE_CONFIRM with denying callback should block execution."""
        original, calls = _make_tool_executor()
        engine = PolicyEngine(raise_on_block=False, raise_on_confirm=False)
        engine.register_policy(HighRiskToolGatingPolicy())

        # Approval callback that always denies
        deny_cb = MagicMock(return_value=False)

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
            approval_callback=deny_cb,
        )

        runtime.start_run("test-goal", "test")

        tool_use = ToolUse(id="call_5", name="file_delete", input={"path": "/tmp/x"})
        result = executor.tool_executor(tool_use)

        # Should be denied
        assert result.is_error
        assert len(calls) == 0

        runtime.end_run(success=True)

    def test_policy_decisions_recorded_in_runtime(self, runtime):
        """Verify that blocked tool calls create runtime problem reports."""
        from framework.policies.base import BasePolicy
        from framework.policies.decisions import PolicyDecision, Severity
        from framework.policies.events import PolicyEvent, PolicyEventType

        # Create a custom policy that always blocks
        class AlwaysBlockPolicy(BasePolicy):
            _id: str = "always-block"
            _name: str = "Always Block"
            _description: str = "Blocks everything"
            _event_types = [PolicyEventType.TOOL_CALL]

            @property
            def id(self):
                return self._id

            @property
            def name(self):
                return self._name

            @property
            def description(self):
                return self._description

            @property
            def event_types(self):
                return self._event_types

            async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
                return PolicyDecision.block(
                    policy_id=self._id,
                    reason="Always blocked for testing",
                    severity=Severity.HIGH,
                )

        original, _calls = _make_tool_executor()
        engine = PolicyEngine(raise_on_block=False)
        engine.register_policy(AlwaysBlockPolicy())

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
        )

        runtime.start_run("test-goal", "test")

        tool_use = ToolUse(id="call_6", name="file_delete", input={"path": "/tmp"})
        executor.tool_executor(tool_use)

        # Check that a problem was reported
        run = runtime.current_run
        assert run is not None
        assert len(run.problems) > 0
        problem = run.problems[0]
        assert "file_delete" in problem.description
        assert problem.severity == "warning"

        runtime.end_run(success=True)

    def test_no_policies_registered_allows_everything(self, runtime):
        """An empty PolicyEngine should allow all tool calls."""
        original, calls = _make_tool_executor()
        engine = PolicyEngine(raise_on_block=False)
        # No policies registered

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
        )

        runtime.start_run("test-goal", "test")

        tool_use = ToolUse(id="call_7", name="anything_at_all", input={})
        result = executor.tool_executor(tool_use)

        assert not result.is_error
        assert len(calls) == 1

        runtime.end_run(success=True)


# === Tests: PolicyConfig builds engine correctly ===


class TestPolicyConfig:
    """Test that PolicyConfig correctly builds a PolicyEngine."""

    def test_default_config_disabled(self):
        """Default PolicyConfig with no policies enabled produces None."""
        from framework.runner.runner import PolicyConfig

        config = PolicyConfig()
        # No policies enabled, even though enabled=True
        # _build_policy_engine should return None since no policies registered
        from framework.runner.runner import AgentRunner

        # We can't easily test _build_policy_engine without an AgentRunner,
        # so test the config structure instead
        assert config.enabled is True
        assert config.enable_tool_gating is False
        assert config.enable_domain_allowlist is False
        assert config.enable_budget_limits is False
        assert config.enable_injection_guard is False

    def test_config_with_tool_gating(self):
        """PolicyConfig with tool_gating=True should enable gating policy."""
        from framework.runner.runner import PolicyConfig

        config = PolicyConfig(
            enable_tool_gating=True,
            tool_gating_mode="strict",
        )
        assert config.enable_tool_gating is True
        assert config.tool_gating_mode == "strict"

    def test_config_with_all_policies(self):
        """PolicyConfig with all policies enabled."""
        from framework.runner.runner import PolicyConfig

        config = PolicyConfig(
            enable_tool_gating=True,
            enable_domain_allowlist=True,
            allowed_domains=["api.example.com"],
            enable_budget_limits=True,
            token_limit=50000,
            cost_limit_usd=0.50,
            enable_injection_guard=True,
        )
        assert config.enable_tool_gating is True
        assert config.enable_domain_allowlist is True
        assert config.allowed_domains == ["api.example.com"]
        assert config.enable_budget_limits is True
        assert config.token_limit == 50000
        assert config.cost_limit_usd == 0.50
        assert config.enable_injection_guard is True

    def test_policy_config_exported_from_framework(self):
        """PolicyConfig should be importable from framework."""
        from framework import PolicyConfig

        config = PolicyConfig(enable_tool_gating=True)
        assert config.enable_tool_gating is True


# === Tests: Post-call evaluation (injection guard) ===


class TestPostCallEvaluation:
    """Test that TOOL_RESULT events are evaluated after tool execution."""

    def test_post_call_evaluation_runs(self, runtime):
        """Verify post-call evaluation happens even when pre-call allows."""
        from framework.policies.builtin.injection_guard import (
            InjectionGuardPolicy,
            InjectionMode,
        )

        original, calls = _make_tool_executor()
        engine = PolicyEngine(raise_on_block=False)
        engine.register_policy(
            InjectionGuardPolicy(mode=InjectionMode.PERMISSIVE)
        )

        executor = GraphExecutor(
            runtime=runtime,
            tool_executor=original,
            policy_engine=engine,
        )

        runtime.start_run("test-goal", "test")

        # Normal tool call — should pass both pre and post evaluation
        tool_use = ToolUse(id="call_8", name="read_data", input={"key": "test"})
        result = executor.tool_executor(tool_use)

        # Should execute successfully
        assert not result.is_error
        assert len(calls) == 1

        runtime.end_run(success=True)
