"""
Plan Schema - Data structures for flexible execution.

Plans are created externally and executed by FlexibleGraphExecutor.
Schema includes enums, specs, and plan/step types with their behavior.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(StrEnum):
    """Types of actions a PlanStep can perform."""

    LLM_CALL = "llm_call"
    TOOL_USE = "tool_use"
    SUB_GRAPH = "sub_graph"
    FUNCTION = "function"
    CODE_EXECUTION = "code_execution"


class StepStatus(StrEnum):
    """Status of a plan step."""

    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    REJECTED = "rejected"

    def is_terminal(self) -> bool:
        """True if this status is a terminal (finished) state."""
        return self in (
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.SKIPPED,
            StepStatus.REJECTED,
        )

    def is_successful(self) -> bool:
        """True if this status is successful completion."""
        return self == StepStatus.COMPLETED


class ApprovalDecision(StrEnum):
    """Human decision on a step requiring approval."""

    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    ABORT = "abort"


class ApprovalRequest(BaseModel):
    """Request for human approval before executing a step."""

    step_id: str
    step_description: str
    action_type: str
    action_details: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    approval_message: str | None = None
    preview: str | None = None
    model_config = {"extra": "allow"}


class ApprovalResult(BaseModel):
    """Result of human approval decision."""

    decision: ApprovalDecision
    reason: str | None = None
    modifications: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "allow"}


class JudgmentAction(StrEnum):
    """Actions the judge can take after evaluating a step."""

    ACCEPT = "accept"
    RETRY = "retry"
    REPLAN = "replan"
    ESCALATE = "escalate"


class ActionSpec(BaseModel):
    """Specification for an action to be executed."""

    action_type: ActionType
    prompt: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    graph_id: str | None = None
    function_name: str | None = None
    function_args: dict[str, Any] = Field(default_factory=dict)
    code: str | None = None
    language: str = "python"
    model_config = {"extra": "allow"}


class PlanStep(BaseModel):
    """A single step in a plan."""

    id: str
    description: str
    action: ActionSpec
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    requires_approval: bool = Field(default=False)
    approval_message: str | None = None
    status: StepStatus = StepStatus.PENDING
    result: Any | None = None
    error: str | None = None
    attempts: int = 0
    max_retries: int = 3
    started_at: datetime | None = None
    completed_at: datetime | None = None
    model_config = {"extra": "allow"}

    def is_ready(self, terminal_step_ids: set[str]) -> bool:
        """True if all dependencies are in a terminal state and step is PENDING."""
        if self.status != StepStatus.PENDING:
            return False
        return all(dep in terminal_step_ids for dep in self.dependencies)


class Judgment(BaseModel):
    """Result of judging a step execution."""

    action: JudgmentAction
    reasoning: str
    feedback: str | None = None
    rule_matched: str | None = None
    confidence: float = 1.0
    llm_used: bool = False
    context: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "allow"}


class EvaluationRule(BaseModel):
    """Rule for HybridJudge to evaluate step results."""

    id: str
    description: str
    condition: str
    action: JudgmentAction
    feedback_template: str = ""
    priority: int = 0
    model_config = {"extra": "allow"}


class Plan(BaseModel):
    """Complete execution plan."""

    id: str
    goal_id: str
    description: str
    steps: list[PlanStep] = Field(default_factory=list)
    revision: int = 1
    current_step_idx: int = 0
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "external"
    previous_feedback: str | None = None
    model_config = {"extra": "allow"}

    @classmethod
    def from_json(cls, data: str | dict) -> "Plan":
        """Load a Plan from exported JSON (e.g. from export_graph())."""
        import json as json_module

        if isinstance(data, str):
            data = json_module.loads(data)
        if "plan" in data:
            data = data["plan"]
        steps = []
        for step_data in data.get("steps", []):
            action_data = step_data.get("action", {})
            action_type_str = action_data.get("action_type", "function")
            action_type = ActionType(action_type_str)
            action = ActionSpec(
                action_type=action_type,
                prompt=action_data.get("prompt"),
                system_prompt=action_data.get("system_prompt"),
                tool_name=action_data.get("tool_name"),
                tool_args=action_data.get("tool_args", {}),
                function_name=action_data.get("function_name"),
                function_args=action_data.get("function_args", {}),
                code=action_data.get("code"),
            )
            step = PlanStep(
                id=step_data["id"],
                description=step_data.get("description", ""),
                action=action,
                inputs=step_data.get("inputs", {}),
                expected_outputs=step_data.get("expected_outputs", []),
                dependencies=step_data.get("dependencies", []),
                requires_approval=step_data.get("requires_approval", False),
                approval_message=step_data.get("approval_message"),
            )
            steps.append(step)
        return cls(
            id=data.get("id", "plan"),
            goal_id=data.get("goal_id", ""),
            description=data.get("description", ""),
            steps=steps,
            context=data.get("context", {}),
            revision=data.get("revision", 1),
        )

    def get_step(self, step_id: str) -> PlanStep | None:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_ready_steps(self) -> list[PlanStep]:
        """Steps that are ready to execute (dependencies terminal)."""
        terminal_ids = {s.id for s in self.steps if s.status.is_terminal()}
        return [s for s in self.steps if s.is_ready(terminal_ids)]

    def get_completed_steps(self) -> list[PlanStep]:
        """All completed steps."""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    def is_complete(self) -> bool:
        """True when all steps are in a terminal state."""
        return all(s.status.is_terminal() for s in self.steps)

    def is_successful(self) -> bool:
        """True when all steps completed successfully."""
        return all(s.status == StepStatus.COMPLETED for s in self.steps)

    def has_failed_steps(self) -> bool:
        """True if any step failed, was skipped, or rejected."""
        return any(
            s.status in (StepStatus.FAILED, StepStatus.SKIPPED, StepStatus.REJECTED)
            for s in self.steps
        )

    def get_failed_steps(self) -> list[PlanStep]:
        """All steps that failed, were skipped, or rejected."""
        return [
            s
            for s in self.steps
            if s.status in (StepStatus.FAILED, StepStatus.SKIPPED, StepStatus.REJECTED)
        ]

    def to_feedback_context(self) -> dict[str, Any]:
        """Context dict for replanning."""
        return {
            "plan_id": self.id,
            "revision": self.revision,
            "completed_steps": [
                {"id": s.id, "description": s.description, "result": s.result}
                for s in self.get_completed_steps()
            ],
            "failed_steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "error": s.error,
                    "attempts": s.attempts,
                }
                for s in self.steps
                if s.status == StepStatus.FAILED
            ],
            "context": self.context,
        }


class ExecutionStatus(StrEnum):
    """Status of plan execution."""

    COMPLETED = "completed"
    AWAITING_APPROVAL = "awaiting_approval"
    NEEDS_REPLAN = "needs_replan"
    NEEDS_ESCALATION = "needs_escalation"
    REJECTED = "rejected"
    ABORTED = "aborted"
    FAILED = "failed"


class PlanExecutionResult(BaseModel):
    """Result of executing a plan."""

    status: ExecutionStatus
    results: dict[str, Any] = Field(default_factory=dict)
    feedback: str | None = None
    feedback_context: dict[str, Any] = Field(default_factory=dict)
    completed_steps: list[str] = Field(default_factory=list)
    steps_executed: int = 0
    total_tokens: int = 0
    total_latency_ms: int = 0
    error: str | None = None
    model_config = {"extra": "allow"}
