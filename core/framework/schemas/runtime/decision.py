"""
Decision Schema - The atomic unit of agent behavior that Builder cares about.

A Decision captures a moment where the agent chose between options.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class DecisionType(StrEnum):
    """Types of decisions an agent can make."""

    TOOL_SELECTION = "tool_selection"
    PARAMETER_CHOICE = "parameter_choice"
    PATH_CHOICE = "path_choice"
    OUTPUT_FORMAT = "output_format"
    RETRY_STRATEGY = "retry_strategy"
    DELEGATION = "delegation"
    TERMINATION = "termination"
    CUSTOM = "custom"


class Option(BaseModel):
    """One possible choice the agent could make."""

    id: str
    description: str
    action_type: str
    action_params: dict[str, Any] = Field(default_factory=dict)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    model_config = {"extra": "allow"}


class Outcome(BaseModel):
    """What actually happened when a decision was executed."""

    success: bool
    result: Any = None
    error: str | None = None
    state_changes: dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: int = 0
    summary: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    model_config = {"extra": "allow"}


class DecisionEvaluation(BaseModel):
    """Post-hoc evaluation of whether a decision was good."""

    goal_aligned: bool = True
    alignment_score: float = Field(default=1.0, ge=0.0, le=1.0)
    better_option_existed: bool = False
    better_option_id: str | None = None
    why_better: str | None = None
    outcome_quality: float = Field(default=1.0, ge=0.0, le=1.0)
    contributed_to_success: bool | None = None
    explanation: str = ""
    model_config = {"extra": "allow"}


class Decision(BaseModel):
    """The atomic unit of agent behavior that Builder analyzes."""

    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    node_id: str
    intent: str = Field(description="What the agent was trying to do")
    decision_type: DecisionType = DecisionType.CUSTOM
    options: list[Option] = Field(default_factory=list)
    chosen_option_id: str = ""
    reasoning: str = ""
    active_constraints: list[str] = Field(default_factory=list)
    input_context: dict[str, Any] = Field(default_factory=dict)
    outcome: Outcome | None = None
    evaluation: DecisionEvaluation | None = None
    model_config = {"extra": "allow"}

    @computed_field
    @property
    def chosen_option(self) -> Option | None:
        for opt in self.options:
            if opt.id == self.chosen_option_id:
                return opt
        return None

    @computed_field
    @property
    def was_successful(self) -> bool:
        return self.outcome is not None and self.outcome.success

    @computed_field
    @property
    def was_good_decision(self) -> bool:
        if self.evaluation is None:
            return self.was_successful
        return self.evaluation.goal_aligned and self.evaluation.outcome_quality > 0.5

    def summary_for_builder(self) -> str:
        status = "✓" if self.was_successful else "✗"
        quality = ""
        if self.evaluation:
            quality = f" [quality: {self.evaluation.outcome_quality:.1f}]"
        chosen = self.chosen_option
        action = chosen.description if chosen else "unknown action"
        return f"{status} [{self.node_id}] {self.intent} → {action}{quality}"
