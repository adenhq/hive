"""
Plan Data Structures for Flexible Execution.

Plans are created externally (by Claude Code or another LLM agent) and
executed internally by the FlexibleGraphExecutor with Worker-Judge loop.

Schema definitions live in framework.schemas.graph.plan. This module
re-exports them and adds load_export() for backward compatibility.
"""

from typing import Any

from framework.schemas.graph.plan import (
    ActionSpec,
    ActionType,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalResult,
    EvaluationRule,
    ExecutionStatus,
    Judgment,
    JudgmentAction,
    Plan,
    PlanExecutionResult,
    PlanStep,
    StepStatus,
)


def load_export(data: str | dict) -> tuple[Plan, Any]:
    """
    Load both Plan and Goal from export_graph() output.

    The export_graph() MCP tool returns both the plan and the goal that was
    defined and approved during the agent building process. This function
    loads both so you can use them with FlexibleGraphExecutor.

    Args:
        data: JSON string or dict from export_graph()

    Returns:
        Tuple of (Plan, Goal) ready for FlexibleGraphExecutor

    Example:
        # Load from export_graph() output
        exported = export_graph()
        plan, goal = load_export(exported)

        result = await executor.execute_plan(plan, goal, context)
    """
    import json as json_module

    from framework.graph.goal import Goal

    if isinstance(data, str):
        data = json_module.loads(data)

    plan = Plan.from_json(data)
    goal_data = data.get("goal", {})
    if goal_data:
        goal = Goal.model_validate(goal_data)
    else:
        goal = Goal(
            id=plan.goal_id,
            name=plan.goal_id,
            description=plan.description,
            success_criteria=[],
            constraints=[],
        )
    return plan, goal


__all__ = [
    "ActionSpec",
    "ActionType",
    "ApprovalDecision",
    "ApprovalRequest",
    "ApprovalResult",
    "EvaluationRule",
    "ExecutionStatus",
    "Judgment",
    "JudgmentAction",
    "Plan",
    "PlanExecutionResult",
    "PlanStep",
    "StepStatus",
    "load_export",
]
