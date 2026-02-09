"""
Goal Schema - The source of truth for agent behavior.

A Goal defines WHAT the agent should achieve, not HOW.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GoalStatus(StrEnum):
    """Lifecycle status of a goal."""

    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"


class SuccessCriterion(BaseModel):
    """A measurable condition that defines success."""

    id: str
    description: str = Field(description="Human-readable description of what success looks like")
    metric: str = Field(
        description="How to measure: 'output_contains', 'output_equals', 'llm_judge', 'custom'"
    )
    target: Any = Field(description="The target value or condition")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relative importance (0-1)")
    met: bool = False
    model_config = {"extra": "allow"}


class Constraint(BaseModel):
    """A boundary the agent must respect."""

    id: str
    description: str
    constraint_type: str = Field(
        description="Type: 'hard' (must not violate) or 'soft' (prefer not to violate)"
    )
    category: str = Field(
        default="general", description="Category: 'time', 'cost', 'safety', 'scope', 'quality'"
    )
    check: str = Field(
        default="", description="How to check: expression, function name, or 'llm_judge'"
    )
    model_config = {"extra": "allow"}


class Goal(BaseModel):
    """The source of truth for agent behavior."""

    id: str
    name: str
    description: str
    status: GoalStatus = GoalStatus.DRAFT
    success_criteria: list[SuccessCriterion] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context: domain knowledge, user preferences, etc.",
    )
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="What the agent needs: 'llm', 'web_search', 'code_execution', etc.",
    )
    input_schema: dict[str, Any] = Field(default_factory=dict, description="Expected input format")
    output_schema: dict[str, Any] = Field(
        default_factory=dict, description="Expected output format"
    )
    version: str = "1.0.0"
    parent_version: str | None = None
    evolution_reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    model_config = {"extra": "allow"}

    def is_success(self) -> bool:
        if not self.success_criteria:
            return False
        total_weight = sum(c.weight for c in self.success_criteria)
        met_weight = sum(c.weight for c in self.success_criteria if c.met)
        return met_weight >= total_weight * 0.9

    def check_constraint(self, constraint_id: str, value: Any) -> bool:
        for c in self.constraints:
            if c.id == constraint_id:
                return True
        return True

    def to_prompt_context(self) -> str:
        lines = [
            f"# Goal: {self.name}",
            f"{self.description}",
            "",
            "## Success Criteria:",
        ]
        for sc in self.success_criteria:
            lines.append(f"- {sc.description}")
        if self.constraints:
            lines.append("")
            lines.append("## Constraints:")
            for c in self.constraints:
                severity = "MUST" if c.constraint_type == "hard" else "SHOULD"
                lines.append(f"- [{severity}] {c.description}")
        if self.context:
            lines.append("")
            lines.append("## Context:")
            for key, value in self.context.items():
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)
