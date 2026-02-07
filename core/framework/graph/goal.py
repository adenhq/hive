"""
Goal Schema - The source of truth for agent behavior.

Re-exports from framework.schemas.graph.goal for backward compatibility.
"""

from framework.schemas.graph.goal import Constraint, Goal, GoalStatus, SuccessCriterion

__all__ = [
    "Constraint",
    "Goal",
    "GoalStatus",
    "SuccessCriterion",
]
