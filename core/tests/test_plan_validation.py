"""Tests for Plan validation logic."""
import pytest
from framework.graph.plan import Plan, PlanStep, ActionSpec, ActionType, StepStatus

class TestPlanValidation:
    """Tests for Plan.validate() method."""

    def test_validate_valid_linear_plan(self):
        """Validate a simple linear plan A -> B."""
        plan = Plan(
            id="test_plan",
            goal_id="goal_1",
            description="Linear plan",
            steps=[
                PlanStep(
                    id="step_A",
                    description="Step A",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=[],
                ),
                PlanStep(
                    id="step_B",
                    description="Step B",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_A"],
                ),
            ],
        )
        # Should not raise
        plan.validate()

    def test_validate_valid_fork_join_plan(self):
        """Validate a diamond shape plan (A -> B, A -> C, B -> D, C -> D)."""
        plan = Plan(
            id="test_plan",
            goal_id="goal_1",
            description="Diamond plan",
            steps=[
                PlanStep(
                    id="step_A",
                    description="Step A",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=[],
                ),
                PlanStep(
                    id="step_B",
                    description="Step B",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_A"],
                ),
                PlanStep(
                    id="step_C",
                    description="Step C",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_A"],
                ),
                PlanStep(
                    id="step_D",
                    description="Step D",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_B", "step_C"],
                ),
            ],
        )
        # Should not raise
        plan.validate()

    def test_validate_empty_plan(self):
        """Empty plan raises validation error."""
        plan = Plan(
            id="empty_plan",
            goal_id="goal_1",
            description="Empty",
            steps=[],
        )
        with pytest.raises(ValueError, match="Plan must contain at least one step"):
            plan.validate()

    def test_validate_missing_dependency(self):
        """Dependency on non-existent step raises validation error."""
        plan = Plan(
            id="missing_dep_plan",
            goal_id="goal_1",
            description="Missing Dep",
            steps=[
                PlanStep(
                    id="step_A",
                    description="Step A",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["missing_step"],
                ),
            ],
        )
        with pytest.raises(ValueError, match="depends on missing step"):
            plan.validate()

    def test_validate_self_cycle(self):
        """Self-referencing step raises validation error."""
        plan = Plan(
            id="self_cycle_plan",
            goal_id="goal_1",
            description="Self Cycle",
            steps=[
                PlanStep(
                    id="step_A",
                    description="Step A",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_A"],
                ),
            ],
        )
        with pytest.raises(ValueError, match="No valid start node"):
            plan.validate()

    def test_validate_cycle_two_nodes(self):
        """A -> B -> A cycle raises validation error."""
        plan = Plan(
            id="cycle_plan",
            goal_id="goal_1",
            description="Cycle",
            steps=[
                PlanStep(
                    id="step_A",
                    description="Step A",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_B"],
                ),
                PlanStep(
                    id="step_B",
                    description="Step B",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_A"],
                ),
            ],
        )
        with pytest.raises(ValueError, match="No valid start node"):
            plan.validate()

    def test_validate_unreachable_cycle(self):
        """Unreachable cycle (A valid, B <-> C) raises validation error."""
        plan = Plan(
            id="unreachable_cycle_plan",
            goal_id="goal_1",
            description="Unreachable Cycle",
            steps=[
                PlanStep(
                    id="step_A",
                    description="Step A",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=[],
                ),
                PlanStep(
                    id="step_B",
                    description="Step B",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_C"],
                ),
                PlanStep(
                    id="step_C",
                    description="Step C",
                    action=ActionSpec(action_type=ActionType.FUNCTION),
                    dependencies=["step_B"],
                ),
            ],
        )
        # Step A is a valid start node, but B and C form a cycle and are effectively unreachable/in-cycle.
        # Our implementation should catch this after processing A.
        with pytest.raises(ValueError, match="Cycle detected or unreachable nodes"):
            plan.validate()
