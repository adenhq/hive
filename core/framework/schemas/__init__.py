"""
Schema definitions - single entry point for framework schemas.

Subpackages:
- schemas.runtime  → decision.py, run.py (Decision, Run, RunStatus, etc.)
- schemas.graph   → goal.py, node.py, edge.py, plan.py (Goal, Plan, GraphSpec, etc.)

Import from here for "all schemas", or from framework.schemas.runtime / framework.schemas.graph
for a specific domain.
"""

from framework.schemas.graph import (
    ActionSpec,
    ActionType,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalResult,
    AsyncEntryPointSpec,
    Constraint,
    EdgeCondition,
    EdgeSpec,
    EvaluationRule,
    ExecutionStatus,
    Goal,
    GoalStatus,
    GraphSpec,
    Judgment,
    JudgmentAction,
    NodeSpec,
    Plan,
    PlanExecutionResult,
    PlanStep,
    StepStatus,
    SuccessCriterion,
)
from framework.schemas.runtime.decision import (
    Decision,
    DecisionEvaluation,
    DecisionType,
    Option,
    Outcome,
)
from framework.schemas.runtime.run import (
    Problem,
    Run,
    RunMetrics,
    RunStatus,
    RunSummary,
)

__all__ = [
    # Runtime
    "Decision",
    "DecisionEvaluation",
    "DecisionType",
    "Option",
    "Outcome",
    "Problem",
    "Run",
    "RunMetrics",
    "RunStatus",
    "RunSummary",
    # Graph
    "ActionSpec",
    "ActionType",
    "ApprovalDecision",
    "ApprovalRequest",
    "ApprovalResult",
    "AsyncEntryPointSpec",
    "Constraint",
    "EdgeCondition",
    "EdgeSpec",
    "EvaluationRule",
    "ExecutionStatus",
    "Goal",
    "GoalStatus",
    "GraphSpec",
    "Judgment",
    "JudgmentAction",
    "NodeSpec",
    "Plan",
    "PlanExecutionResult",
    "PlanStep",
    "StepStatus",
    "SuccessCriterion",
]
