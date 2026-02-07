"""
Run Schema - A complete execution of an agent graph.

A Run contains all the decisions made during execution, along with
summaries and metrics that Builder needs to understand what happened.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, computed_field

from framework.schemas.runtime.decision import Decision, Outcome


class RunStatus(StrEnum):
    """Status of a run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STUCK = "stuck"
    CANCELLED = "cancelled"


class Problem(BaseModel):
    """A problem that occurred during the run."""

    id: str
    severity: str = Field(description="critical, warning, or minor")
    description: str
    root_cause: str | None = None
    decision_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    suggested_fix: str | None = None
    model_config = {"extra": "allow"}


class RunMetrics(BaseModel):
    """Quantitative metrics about a run."""

    total_decisions: int = 0
    successful_decisions: int = 0
    failed_decisions: int = 0
    total_tokens: int = 0
    total_latency_ms: int = 0
    nodes_executed: list[str] = Field(default_factory=list)
    edges_traversed: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def success_rate(self) -> float:
        if self.total_decisions == 0:
            return 0.0
        return self.successful_decisions / self.total_decisions

    model_config = {"extra": "allow"}


class Run(BaseModel):
    """A complete execution of an agent graph."""

    id: str
    goal_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    status: RunStatus = RunStatus.RUNNING
    completed_at: datetime | None = None
    decisions: list[Decision] = Field(default_factory=list)
    problems: list[Problem] = Field(default_factory=list)
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    narrative: str = ""
    goal_description: str = ""
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "allow"}

    @computed_field
    @property
    def duration_ms(self) -> int:
        if self.completed_at is None:
            return 0
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds() * 1000)

    def add_decision(self, decision: Decision) -> None:
        self.decisions.append(decision)
        self.metrics.total_decisions += 1
        if decision.node_id not in self.metrics.nodes_executed:
            self.metrics.nodes_executed.append(decision.node_id)

    def record_outcome(self, decision_id: str, outcome: Outcome) -> None:
        for dec in self.decisions:
            if dec.id == decision_id:
                dec.outcome = outcome
                if outcome.success:
                    self.metrics.successful_decisions += 1
                else:
                    self.metrics.failed_decisions += 1
                self.metrics.total_tokens += outcome.tokens_used
                self.metrics.total_latency_ms += outcome.latency_ms
                break

    def add_problem(
        self,
        severity: str,
        description: str,
        decision_id: str | None = None,
        root_cause: str | None = None,
        suggested_fix: str | None = None,
    ) -> str:
        problem_id = f"prob_{len(self.problems)}"
        problem = Problem(
            id=problem_id,
            severity=severity,
            description=description,
            decision_id=decision_id,
            root_cause=root_cause,
            suggested_fix=suggested_fix,
        )
        self.problems.append(problem)
        return problem_id

    def complete(self, status: RunStatus, narrative: str = "") -> None:
        self.status = status
        self.completed_at = datetime.now()
        self.narrative = narrative or self._generate_narrative()

    def _generate_narrative(self) -> str:
        parts = []
        status_text = "completed successfully" if self.status == RunStatus.COMPLETED else "failed"
        parts.append(f"Run {status_text}.")
        parts.append(
            f"Made {self.metrics.total_decisions} decisions: "
            f"{self.metrics.successful_decisions} succeeded, "
            f"{self.metrics.failed_decisions} failed."
        )
        if self.problems:
            critical = [p for p in self.problems if p.severity == "critical"]
            warnings = [p for p in self.problems if p.severity == "warning"]
            if critical:
                parts.append(f"Critical issues: {', '.join(p.description for p in critical)}")
            if warnings:
                parts.append(f"Warnings: {', '.join(p.description for p in warnings)}")
        failed_decisions = [d for d in self.decisions if not d.was_successful]
        if failed_decisions:
            parts.append(f"Failed on: {', '.join(d.intent for d in failed_decisions[:3])}")
        return " ".join(parts)


class RunSummary(BaseModel):
    """A condensed view of a run for Builder to quickly scan."""

    run_id: str
    goal_id: str
    status: RunStatus
    duration_ms: int
    decision_count: int
    success_rate: float
    problem_count: int
    narrative: str
    key_decisions: list[str] = Field(default_factory=list)
    critical_problems: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    successes: list[str] = Field(default_factory=list)
    model_config = {"extra": "allow"}

    @classmethod
    def from_run(cls, run: Run) -> "RunSummary":
        key_decisions = []
        for d in run.decisions:
            if not d.was_successful:
                key_decisions.append(d.summary_for_builder())
            elif d.evaluation and d.evaluation.outcome_quality > 0.8:
                key_decisions.append(d.summary_for_builder())
        key_decisions = key_decisions[:5]
        critical = [p.description for p in run.problems if p.severity == "critical"]
        warnings = [p.description for p in run.problems if p.severity == "warning"]
        successes = []
        for d in run.decisions:
            if d.was_successful and d.outcome and d.outcome.summary:
                successes.append(d.outcome.summary)
        successes = successes[:3]
        return cls(
            run_id=run.id,
            goal_id=run.goal_id,
            status=run.status,
            duration_ms=run.duration_ms,
            decision_count=run.metrics.total_decisions,
            success_rate=run.metrics.success_rate,
            problem_count=len(run.problems),
            narrative=run.narrative,
            key_decisions=key_decisions,
            critical_problems=critical,
            warnings=warnings,
            successes=successes,
        )
