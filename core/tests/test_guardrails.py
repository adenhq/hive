"""
Tests for the Guardrails system.

Tests cover:
- GuardrailConfig model validation
- GuardrailEngine before/after decision checks
- Tool restrictions and loop detection
- Token budget enforcement
- Retry limit management
- Runtime integration
"""

from framework.runtime.guardrail_engine import (
    GuardrailEngine,
    create_default_guardrails,
    create_strict_guardrails,
)
from framework.schemas.guardrails import (
    DecisionPlan,
    GuardrailAction,
    GuardrailConfig,
    GuardrailSeverity,
    LatencyGuardConfig,
    RetryGuardConfig,
    RunContext,
    TokenGuardConfig,
    ToolGuardConfig,
)


class TestGuardrailConfig:
    """Tests for GuardrailConfig model."""

    def test_default_config(self):
        """Test default configuration is permissive."""
        config = GuardrailConfig()
        assert config.enabled is True
        assert config.tools == []
        assert config.tokens is None
        assert config.retries is None
        assert config.forbidden_tools == []

    def test_tool_forbidden_check_global_list(self):
        """Test forbidden tool detection via global list."""
        config = GuardrailConfig(forbidden_tools=["dangerous_tool", "rm_rf"])

        is_forbidden, reason = config.is_tool_forbidden("dangerous_tool")
        assert is_forbidden is True
        assert "dangerous_tool" in reason

        is_forbidden, reason = config.is_tool_forbidden("safe_tool")
        assert is_forbidden is False
        assert reason == ""

    def test_tool_forbidden_check_tool_config(self):
        """Test forbidden tool detection via ToolGuardConfig."""
        config = GuardrailConfig(
            tools=[
                ToolGuardConfig(
                    tool_name="exec_shell",
                    forbidden=True,
                    forbidden_reason="Shell execution is disabled",
                )
            ]
        )

        is_forbidden, reason = config.is_tool_forbidden("exec_shell")
        assert is_forbidden is True
        assert "disabled" in reason

    def test_get_tool_config(self):
        """Test retrieving tool-specific configuration."""
        config = GuardrailConfig(
            tools=[
                ToolGuardConfig(tool_name="web_search", max_calls_per_run=10),
                ToolGuardConfig(tool_name="api_call", max_calls_per_run=5),
            ]
        )

        search_config = config.get_tool_config("web_search")
        assert search_config is not None
        assert search_config.max_calls_per_run == 10

        unknown_config = config.get_tool_config("unknown_tool")
        assert unknown_config is None


class TestRunContext:
    """Tests for RunContext tracking."""

    def test_increment_tool_call(self):
        """Test tool call counting."""
        ctx = RunContext(run_id="test", goal_id="goal")

        count = ctx.increment_tool_call("search")
        assert count == 1
        count = ctx.increment_tool_call("search")
        assert count == 2
        count = ctx.increment_tool_call("other")
        assert count == 1

    def test_tool_failure_tracking(self):
        """Test consecutive failure tracking."""
        ctx = RunContext(run_id="test", goal_id="goal")

        streak = ctx.record_tool_failure("search")
        assert streak == 1
        streak = ctx.record_tool_failure("search")
        assert streak == 2

        # Reset on success
        ctx.reset_tool_failure_streak("search")
        assert ctx.tool_failure_streaks["search"] == 0

        # Next failure starts fresh
        streak = ctx.record_tool_failure("search")
        assert streak == 1

    def test_node_retry_tracking(self):
        """Test node retry counting."""
        ctx = RunContext(run_id="test", goal_id="goal")

        count = ctx.increment_node_retry("node_a")
        assert count == 1
        assert ctx.total_retries == 1

        count = ctx.increment_node_retry("node_a")
        assert count == 2
        assert ctx.total_retries == 2

        count = ctx.increment_node_retry("node_b")
        assert count == 1
        assert ctx.total_retries == 3


class TestGuardrailEngineForbiddenTools:
    """Tests for forbidden tool guardrails."""

    def test_forbidden_tool_blocks_decision(self):
        """Test that forbidden tools are blocked."""
        config = GuardrailConfig(forbidden_tools=["dangerous_tool"])
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        plan = DecisionPlan(
            node_id="node1",
            intent="Execute command",
            tool_name="dangerous_tool",
        )

        result = engine.check_before_decision(plan, ctx)

        assert result.blocked is True
        assert result.action == GuardrailAction.BLOCK
        assert len(result.violations) == 1
        assert result.violations[0].guardrail_type == "tool_forbidden"
        assert result.violations[0].severity == GuardrailSeverity.CRITICAL

    def test_allowed_tool_passes(self):
        """Test that allowed tools pass."""
        config = GuardrailConfig(forbidden_tools=["dangerous_tool"])
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        plan = DecisionPlan(
            node_id="node1",
            intent="Search web",
            tool_name="safe_tool",
        )

        result = engine.check_before_decision(plan, ctx)

        assert result.blocked is False
        assert result.action == GuardrailAction.ALLOW
        assert len(result.violations) == 0


class TestGuardrailEngineToolLoops:
    """Tests for tool loop detection."""

    def test_tool_loop_detection(self):
        """Test that consecutive failures trigger loop detection."""
        config = GuardrailConfig(
            tools=[
                ToolGuardConfig(
                    tool_name="flaky_tool",
                    max_consecutive_failures=3,
                )
            ]
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        # Simulate 3 consecutive failures
        ctx.record_tool_failure("flaky_tool")
        ctx.record_tool_failure("flaky_tool")
        ctx.record_tool_failure("flaky_tool")

        plan = DecisionPlan(
            node_id="node1",
            intent="Try again",
            tool_name="flaky_tool",
        )

        result = engine.check_before_decision(plan, ctx)

        assert result.blocked is True
        assert any(v.guardrail_type == "tool_loop" for v in result.violations)

    def test_tool_loop_reset_on_success(self):
        """Test that successful execution resets failure streak."""
        config = GuardrailConfig()
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        # Record failures
        ctx.record_tool_failure("tool")
        ctx.record_tool_failure("tool")

        # Simulate success - call triggers streak reset
        _result = engine.check_after_decision(
            outcome_success=True,
            outcome_tokens=100,
            outcome_latency_ms=500,
            tool_name="tool",
            node_id="node1",
            context=ctx,
        )
        assert _result.allowed  # Verify call worked

        # Streak should be reset
        assert ctx.tool_failure_streaks["tool"] == 0


class TestGuardrailEngineToolLimits:
    """Tests for tool call limits."""

    def test_tool_call_limit_blocks(self):
        """Test that exceeding max calls blocks."""
        config = GuardrailConfig(
            tools=[
                ToolGuardConfig(tool_name="limited_tool", max_calls_per_run=3)
            ]
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        # Simulate 3 previous calls
        ctx.tool_call_counts["limited_tool"] = 3

        plan = DecisionPlan(
            node_id="node1",
            intent="Call again",
            tool_name="limited_tool",
        )

        result = engine.check_before_decision(plan, ctx)

        assert result.blocked is True
        assert any(v.guardrail_type == "tool_limit" for v in result.violations)


class TestGuardrailEngineTokenBudget:
    """Tests for token budget enforcement."""

    def test_token_budget_warning(self):
        """Test warning when approaching token budget."""
        config = GuardrailConfig(
            tokens=TokenGuardConfig(
                max_tokens_per_run=10000,
                warn_threshold_percent=0.8,
            )
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal", total_tokens_used=7500)

        plan = DecisionPlan(
            node_id="node1",
            intent="Generate text",
            estimated_tokens=1000,
        )

        result = engine.check_before_decision(plan, ctx)

        # Should warn but not block
        assert result.blocked is False
        assert result.action == GuardrailAction.WARN
        assert any(v.guardrail_type == "token_budget_warning" for v in result.violations)

    def test_token_budget_blocks(self):
        """Test blocking when exceeding token budget."""
        config = GuardrailConfig(
            tokens=TokenGuardConfig(max_tokens_per_run=10000)
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal", total_tokens_used=9500)

        plan = DecisionPlan(
            node_id="node1",
            intent="Generate text",
            estimated_tokens=1000,
        )

        result = engine.check_before_decision(plan, ctx)

        assert result.blocked is True
        assert any(v.guardrail_type == "token_run_limit" for v in result.violations)

    def test_per_decision_token_warning(self):
        """Test warning for large single decisions."""
        config = GuardrailConfig(
            tokens=TokenGuardConfig(max_tokens_per_decision=5000)
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        plan = DecisionPlan(
            node_id="node1",
            intent="Generate large text",
            estimated_tokens=6000,
        )

        result = engine.check_before_decision(plan, ctx)

        # Should warn but not block by default
        assert result.action == GuardrailAction.WARN
        assert any(v.guardrail_type == "token_decision_limit" for v in result.violations)


class TestGuardrailEngineRetries:
    """Tests for retry limit enforcement."""

    def test_node_retry_limit_blocks(self):
        """Test blocking when node exceeds retry limit."""
        config = GuardrailConfig(
            retries=RetryGuardConfig(max_retries_per_node=3)
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")
        ctx.node_retry_counts["failing_node"] = 3

        plan = DecisionPlan(node_id="failing_node", intent="Try again")

        result = engine.check_before_decision(plan, ctx)

        assert result.blocked is True
        assert any(v.guardrail_type == "retry_node_limit" for v in result.violations)

    def test_run_retry_limit_blocks(self):
        """Test blocking when run exceeds total retry limit."""
        config = GuardrailConfig(
            retries=RetryGuardConfig(max_retries_per_run=10)
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal", total_retries=10)

        plan = DecisionPlan(node_id="node1", intent="Execute")

        result = engine.check_before_decision(plan, ctx)

        assert result.blocked is True
        assert any(v.guardrail_type == "retry_run_limit" for v in result.violations)


class TestGuardrailEngineLatency:
    """Tests for latency monitoring."""

    def test_latency_warning(self):
        """Test warning for slow decisions."""
        config = GuardrailConfig(
            latency=LatencyGuardConfig(warn_latency_ms=5000)
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        result = engine.check_after_decision(
            outcome_success=True,
            outcome_tokens=100,
            outcome_latency_ms=10000,
            tool_name=None,
            node_id="slow_node",
            context=ctx,
        )

        assert any(v.guardrail_type == "latency_warning" for v in result.violations)

    def test_latency_exceeded(self):
        """Test warning when max latency exceeded."""
        config = GuardrailConfig(
            latency=LatencyGuardConfig(max_latency_ms=30000)
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        result = engine.check_after_decision(
            outcome_success=True,
            outcome_tokens=100,
            outcome_latency_ms=45000,
            tool_name=None,
            node_id="very_slow_node",
            context=ctx,
        )

        assert any(v.guardrail_type == "latency_exceeded" for v in result.violations)


class TestGuardrailEngineDisabled:
    """Tests for disabled guardrails."""

    def test_disabled_guardrails_allow_all(self):
        """Test that disabled guardrails don't block anything."""
        config = GuardrailConfig(
            enabled=False,
            forbidden_tools=["dangerous"],
        )
        engine = GuardrailEngine(config)
        ctx = RunContext(run_id="test", goal_id="goal")

        plan = DecisionPlan(
            node_id="node1",
            intent="Use forbidden tool",
            tool_name="dangerous",
        )

        result = engine.check_before_decision(plan, ctx)

        assert result.blocked is False
        assert result.action == GuardrailAction.ALLOW
        assert len(result.violations) == 0


class TestConvenienceFactories:
    """Tests for convenience factory functions."""

    def test_create_default_guardrails(self):
        """Test default guardrails factory."""
        config = create_default_guardrails()
        assert config.enabled is True
        assert config.tokens is None  # No limits by default

    def test_create_strict_guardrails(self):
        """Test strict guardrails factory."""
        config = create_strict_guardrails(
            max_tokens_per_run=50000,
            max_tokens_per_decision=5000,
            forbidden_tools=["exec_command"],
        )

        assert config.enabled is True
        assert config.tokens is not None
        assert config.tokens.max_tokens_per_run == 50000
        assert config.tokens.max_tokens_per_decision == 5000
        assert "exec_command" in config.forbidden_tools
        assert config.retries is not None
        assert config.latency is not None


class TestViolationToProblem:
    """Tests for converting violations to problems."""

    def test_create_problem_from_violation(self):
        """Test conversion of violation to problem dict."""
        from framework.schemas.guardrails import GuardrailViolation

        violation = GuardrailViolation(
            id="v1",
            guardrail_type="token_exceeded",
            action=GuardrailAction.WARN,
            severity=GuardrailSeverity.WARNING,
            description="Token limit exceeded",
            suggested_fix="Reduce prompt size",
        )

        engine = GuardrailEngine(GuardrailConfig())
        problem = engine.create_problem_from_violation(violation)

        assert problem["severity"] == "warning"
        assert "token_exceeded" in problem["description"]
        assert problem["suggested_fix"] == "Reduce prompt size"
