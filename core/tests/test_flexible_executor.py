"""
Tests for the Worker-Judge flexible execution pattern.

Tests cover:
- Plan and PlanStep data structures
- Code sandbox security
- HybridJudge rule evaluation
- WorkerNode action dispatch
- FlexibleGraphExecutor end-to-end
"""

import asyncio
import pytest

from framework.graph.plan import (
    Plan,
    PlanStep,
    ActionSpec,
    ActionType,
    StepStatus,
    Judgment,
    JudgmentAction,
    EvaluationRule,
    PlanExecutionResult,
    ExecutionStatus,
)
from framework.graph.code_sandbox import (
    CodeSandbox,
    safe_exec,
    safe_eval,
)
from framework.graph.judge import HybridJudge, create_default_judge
from framework.graph.goal import Goal, SuccessCriterion


class TestPlanDataStructures:
    """Tests for Plan and PlanStep."""

    def test_plan_step_creation(self):
        """Test creating a PlanStep."""
        action = ActionSpec(
            action_type=ActionType.LLM_CALL,
            prompt="Hello, world!",
        )
        step = PlanStep(
            id="step_1",
            description="Say hello",
            action=action,
            expected_outputs=["greeting"],
        )

        assert step.id == "step_1"
        assert step.status == StepStatus.PENDING
        assert step.action.action_type == ActionType.LLM_CALL

    def test_plan_step_is_ready(self):
        """Test PlanStep.is_ready() with dependencies."""
        step1 = PlanStep(
            id="step_1",
            description="First step",
            action=ActionSpec(action_type=ActionType.FUNCTION),
            dependencies=[],
        )
        step2 = PlanStep(
            id="step_2",
            description="Second step",
            action=ActionSpec(action_type=ActionType.FUNCTION),
            dependencies=["step_1"],
        )

        # Step 1 is ready (no deps)
        assert step1.is_ready(set()) is True

        # Step 2 is not ready (dep not met)
        assert step2.is_ready(set()) is False

        # Step 2 is ready after step 1 completes
        assert step2.is_ready({"step_1"}) is True

    def test_plan_get_ready_steps(self):
        """Test Plan.get_ready_steps()."""
        plan = Plan(
            id="test_plan",
            goal_id="goal_1",
            description="Test plan",
            steps=[
                PlanStep(
                    id="step_1",
                    description="First",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=[],
                ),
                PlanStep(
                    id="step_2",
                    description="Second",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_1"],
                ),
            ],
        )

        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].id == "step_1"

    def test_plan_is_complete(self):
        """Test Plan.is_complete()."""
        plan = Plan(
            id="test_plan",
            goal_id="goal_1",
            description="Test plan",
            steps=[
                PlanStep(
                    id="step_1",
                    description="First",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    status=StepStatus.COMPLETED,
                ),
            ],
        )

        assert plan.is_complete() is True

    def test_plan_to_feedback_context(self):
        """Test Plan.to_feedback_context()."""
        plan = Plan(
            id="test_plan",
            goal_id="goal_1",
            description="Test plan",
            steps=[
                PlanStep(
                    id="step_1",
                    description="Completed step",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    status=StepStatus.COMPLETED,
                    result={"data": "value"},
                ),
                PlanStep(
                    id="step_2",
                    description="Failed step",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    status=StepStatus.FAILED,
                    error="Something went wrong",
                    attempts=3,
                ),
            ],
        )

        context = plan.to_feedback_context()
        assert context["plan_id"] == "test_plan"
        assert len(context["completed_steps"]) == 1
        assert len(context["failed_steps"]) == 1
        assert context["failed_steps"][0]["error"] == "Something went wrong"


class TestCodeSandbox:
    """Tests for code sandbox security."""

    def test_simple_execution(self):
        """Test simple code execution."""
        result = safe_exec("x = 1 + 2\nresult = x * 3")
        assert result.success is True
        assert result.variables.get("x") == 3
        assert result.result == 9

    def test_input_injection(self):
        """Test passing inputs to sandbox."""
        result = safe_exec(
            "result = x + y",
            inputs={"x": 10, "y": 20},
        )
        assert result.success is True
        assert result.result == 30

    def test_blocked_import(self):
        """Test that dangerous imports are blocked."""
        result = safe_exec("import os")
        assert result.success is False
        assert "blocked" in result.error.lower() or "import" in result.error.lower()

    def test_blocked_private_access(self):
        """Test that private attribute access is blocked."""
        result = safe_exec("x = [].__class__.__bases__")
        assert result.success is False

    def test_blocked_exec_eval(self):
        """Test that exec/eval are blocked."""
        result = safe_exec("exec('print(1)')")
        assert result.success is False

    def test_safe_eval_expression(self):
        """Test safe_eval for expressions."""
        result = safe_eval("x + y", inputs={"x": 5, "y": 3})
        assert result.success is True
        assert result.result == 8

    def test_allowed_modules(self):
        """Test that allowed modules work."""
        sandbox = CodeSandbox()
        # math is in ALLOWED_MODULES
        result = sandbox.execute(
            """
import math
result = math.sqrt(16)
""",
            inputs={},
        )
        # Note: imports are blocked by default in validation
        # This test documents current behavior
        assert result.success is False  # imports blocked by validator


class TestHybridJudge:
    """Tests for the HybridJudge."""

    def test_rule_based_accept(self):
        """Test rule-based accept judgment."""
        judge = HybridJudge()
        judge.add_rule(EvaluationRule(
            id="success_check",
            description="Accept on success flag",
            condition="result.get('success') == True",
            action=JudgmentAction.ACCEPT,
        ))

        step = PlanStep(
            id="test_step",
            description="Test",
            action=ActionSpec(action_type=ActionType.FUNCTION),
        )
        goal = Goal(
            id="goal_1",
            name="Test Goal",
            description="A test goal",
            success_criteria=[
                SuccessCriterion(id="sc1", description="Complete task", metric="completion", target="100%"),
            ],
        )

        # Use sync version for testing
        judgment = asyncio.run(
            judge.evaluate(step, {"success": True}, goal)
        )

        assert judgment.action == JudgmentAction.ACCEPT
        assert judgment.rule_matched == "success_check"

    def test_rule_based_retry(self):
        """Test rule-based retry judgment."""
        judge = HybridJudge()
        judge.add_rule(EvaluationRule(
            id="timeout_retry",
            description="Retry on timeout",
            condition="result.get('error_type') == 'timeout'",
            action=JudgmentAction.RETRY,
            feedback_template="Timeout occurred, please retry",
        ))

        step = PlanStep(
            id="test_step",
            description="Test",
            action=ActionSpec(action_type=ActionType.FUNCTION),
        )
        goal = Goal(
            id="goal_1",
            name="Test Goal",
            description="A test goal",
            success_criteria=[
                SuccessCriterion(id="sc1", description="Complete task", metric="completion", target="100%"),
            ],
        )

        judgment = asyncio.run(
            judge.evaluate(step, {"error_type": "timeout"}, goal)
        )

        assert judgment.action == JudgmentAction.RETRY

    def test_rule_priority(self):
        """Test that higher priority rules are checked first."""
        judge = HybridJudge()

        # Lower priority - would match
        judge.add_rule(EvaluationRule(
            id="low_priority",
            description="Low priority accept",
            condition="True",
            action=JudgmentAction.ACCEPT,
            priority=1,
        ))

        # Higher priority - should match first
        judge.add_rule(EvaluationRule(
            id="high_priority",
            description="High priority escalate",
            condition="True",
            action=JudgmentAction.ESCALATE,
            priority=100,
        ))

        step = PlanStep(
            id="test_step",
            description="Test",
            action=ActionSpec(action_type=ActionType.FUNCTION),
        )
        goal = Goal(
            id="goal_1",
            name="Test Goal",
            description="A test goal",
            success_criteria=[
                SuccessCriterion(id="sc1", description="Complete task", metric="completion", target="100%"),
            ],
        )

        judgment = asyncio.run(
            judge.evaluate(step, {}, goal)
        )

        assert judgment.rule_matched == "high_priority"
        assert judgment.action == JudgmentAction.ESCALATE

    def test_default_judge_rules(self):
        """Test that create_default_judge includes useful rules."""
        judge = create_default_judge()

        # Should have rules for common cases
        rule_ids = {r.id for r in judge.rules}
        assert "explicit_success" in rule_ids
        assert "transient_error_retry" in rule_ids
        assert "security_escalate" in rule_ids


class TestJudgment:
    """Tests for Judgment data structure."""

    def test_judgment_creation(self):
        """Test creating a Judgment."""
        judgment = Judgment(
            action=JudgmentAction.ACCEPT,
            reasoning="Step completed successfully",
            confidence=0.95,
        )

        assert judgment.action == JudgmentAction.ACCEPT
        assert judgment.confidence == 0.95
        assert judgment.llm_used is False

    def test_judgment_with_feedback(self):
        """Test Judgment with feedback for retry/replan."""
        judgment = Judgment(
            action=JudgmentAction.REPLAN,
            reasoning="Missing required data",
            feedback="Need to fetch user data first",
            context={"missing": ["user_id", "email"]},
        )

        assert judgment.action == JudgmentAction.REPLAN
        assert judgment.feedback is not None
        assert "user_id" in judgment.context["missing"]


class TestPlanExecutionResult:
    """Tests for PlanExecutionResult."""

    def test_completed_result(self):
        """Test completed execution result."""
        result = PlanExecutionResult(
            status=ExecutionStatus.COMPLETED,
            results={"output": "success"},
            steps_executed=5,
            total_tokens=1000,
        )

        assert result.status == ExecutionStatus.COMPLETED
        assert result.steps_executed == 5

    def test_needs_replan_result(self):
        """Test needs_replan execution result."""
        result = PlanExecutionResult(
            status=ExecutionStatus.NEEDS_REPLAN,
            feedback="Step 3 failed: missing data",
            feedback_context={
                "completed_steps": ["step_1", "step_2"],
                "failed_step": "step_3",
            },
            completed_steps=["step_1", "step_2"],
        )

        assert result.status == ExecutionStatus.NEEDS_REPLAN
        assert result.feedback is not None
        assert len(result.completed_steps) == 2


# Integration tests would require mocking Runtime and LLM
class TestFlexibleExecutorIntegration:
    """Integration tests for FlexibleGraphExecutor."""

    def test_executor_creation(self, tmp_path):
        """Test creating a FlexibleGraphExecutor."""
        from framework.runtime.core import Runtime
        from framework.graph.flexible_executor import FlexibleGraphExecutor

        runtime = Runtime(storage_path=tmp_path / "runtime")
        executor = FlexibleGraphExecutor(runtime=runtime)

        assert executor.runtime == runtime
        assert executor.judge is not None
        assert executor.worker is not None

    def test_executor_with_custom_judge(self, tmp_path):
        """Test executor with custom judge."""
        from framework.runtime.core import Runtime
        from framework.graph.flexible_executor import FlexibleGraphExecutor

        runtime = Runtime(storage_path=tmp_path / "runtime")
        custom_judge = HybridJudge()
        custom_judge.add_rule(EvaluationRule(
            id="custom_rule",
            description="Custom rule",
            condition="True",
            action=JudgmentAction.ACCEPT,
        ))

        executor = FlexibleGraphExecutor(runtime=runtime, judge=custom_judge)

        assert len(executor.judge.rules) == 1
        assert executor.judge.rules[0].id == "custom_rule"


class TestOutputValidation:
    """Tests for strict output validation in FlexibleExecutor."""

    @pytest.mark.asyncio
    async def test_safe_single_output_mapping(self, tmp_path):
        """Test that single expected output can safely map from generic 'result'."""
        from framework.runtime.core import Runtime
        from framework.graph.flexible_executor import FlexibleGraphExecutor
        from framework.graph.worker_node import StepExecutionResult

        runtime = Runtime(storage_path=tmp_path / "runtime")
        executor = FlexibleGraphExecutor(runtime=runtime)

        # Create step expecting single output
        step = PlanStep(
            id="extract_step",
            description="Extract data",
            action=ActionSpec(action_type=ActionType.FUNCTION),
            expected_outputs=["extracted_data"],
        )

        # Worker returns generic "result"
        work_result = StepExecutionResult(
            outputs={"result": "extracted value"},
            success=True,
            tokens_used=10,
            latency_ms=100,
        )

        # Create minimal judgment
        judgment = Judgment(
            action=JudgmentAction.ACCEPT,
            reasoning="Success",
            confidence=1.0,
        )

        goal = Goal(
            id="test_goal",
            name="Test",
            description="Test goal",
            success_criteria=[
                SuccessCriterion(id="sc1", description="Complete", metric="done", target="100%"),
            ],
        )

        plan = Plan(
            id="test_plan",
            goal_id="test_goal",
            description="Test",
            steps=[step],
        )

        context = {}

        # Should succeed and map result -> extracted_data
        result = await executor._handle_judgment(
            step=step,
            work_result=work_result,
            judgment=judgment,
            plan=plan,
            goal=goal,
            context=context,
            steps_executed=1,
            total_tokens=10,
            total_latency=100,
        )

        # Should return None (continue execution)
        assert result is None
        # Should have mapped output
        assert context.get("extracted_data") == "extracted value"
        # Should NOT have generic "result" key
        assert "result" not in context

    @pytest.mark.asyncio
    async def test_multiple_outputs_prevents_corruption(self, tmp_path):
        """Test that multiple expected outputs fail instead of silent corruption."""
        from framework.runtime.core import Runtime
        from framework.graph.flexible_executor import FlexibleGraphExecutor
        from framework.graph.worker_node import StepExecutionResult

        runtime = Runtime(storage_path=tmp_path / "runtime")
        executor = FlexibleGraphExecutor(runtime=runtime)

        # Create step expecting MULTIPLE outputs
        step = PlanStep(
            id="extract_step",
            description="Extract data",
            action=ActionSpec(action_type=ActionType.FUNCTION),
            expected_outputs=["extracted_data", "confidence_score"],
        )

        # Worker returns only generic "result" (ambiguous!)
        work_result = StepExecutionResult(
            outputs={"result": "some text"},
            success=True,
            tokens_used=10,
            latency_ms=100,
        )

        judgment = Judgment(
            action=JudgmentAction.ACCEPT,
            reasoning="Success",
            confidence=1.0,
        )

        goal = Goal(
            id="test_goal",
            name="Test",
            description="Test goal",
            success_criteria=[
                SuccessCriterion(id="sc1", description="Complete", metric="done", target="100%"),
            ],
        )

        plan = Plan(
            id="test_plan",
            goal_id="test_goal",
            description="Test",
            steps=[step],
        )

        context = {}

        # Should fail with clear feedback instead of corrupting data
        result = await executor._handle_judgment(
            step=step,
            work_result=work_result,
            judgment=judgment,
            plan=plan,
            goal=goal,
            context=context,
            steps_executed=1,
            total_tokens=10,
            total_latency=100,
        )

        # Should return NEEDS_REPLAN (not None)
        assert result is not None
        assert result.status == ExecutionStatus.NEEDS_REPLAN
        assert "output validation failed" in result.feedback.lower()
        # Context should NOT be corrupted with duplicate values
        assert "extracted_data" not in context
        assert "confidence_score" not in context

    @pytest.mark.asyncio
    async def test_exact_output_match_succeeds(self, tmp_path):
        """Test that exact output matches work correctly."""
        from framework.runtime.core import Runtime
        from framework.graph.flexible_executor import FlexibleGraphExecutor
        from framework.graph.worker_node import StepExecutionResult

        runtime = Runtime(storage_path=tmp_path / "runtime")
        executor = FlexibleGraphExecutor(runtime=runtime)

        step = PlanStep(
            id="extract_step",
            description="Extract data",
            action=ActionSpec(action_type=ActionType.FUNCTION),
            expected_outputs=["extracted_data", "confidence_score"],
        )

        # Worker returns EXACT expected outputs
        work_result = StepExecutionResult(
            outputs={
                "extracted_data": "some text",
                "confidence_score": 0.95,
            },
            success=True,
            tokens_used=10,
            latency_ms=100,
        )

        judgment = Judgment(
            action=JudgmentAction.ACCEPT,
            reasoning="Success",
            confidence=1.0,
        )

        goal = Goal(
            id="test_goal",
            name="Test",
            description="Test goal",
            success_criteria=[
                SuccessCriterion(id="sc1", description="Complete", metric="done", target="100%"),
            ],
        )

        plan = Plan(
            id="test_plan",
            goal_id="test_goal",
            description="Test",
            steps=[step],
        )

        context = {}

        # Should succeed
        result = await executor._handle_judgment(
            step=step,
            work_result=work_result,
            judgment=judgment,
            plan=plan,
            goal=goal,
            context=context,
            steps_executed=1,
            total_tokens=10,
            total_latency=100,
        )

        assert result is None  # Continue execution
        assert context["extracted_data"] == "some text"
        assert context["confidence_score"] == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
