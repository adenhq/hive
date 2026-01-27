"""
Runtime Core - The interface agents use to record their behavior.

This is designed to make it EASY for agents to record decisions in a way
that Builder can analyze. The agent calls simple methods, and the runtime
handles all the structured logging.

Guardrails Integration:
    The runtime can optionally be configured with guardrails that validate
    decisions before and after execution. See GuardrailEngine for details.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from framework.schemas.decision import Decision, DecisionType, Option, Outcome
from framework.schemas.guardrails import (
    DecisionPlan,
    GuardrailConfig,
    GuardrailResult,
    RunContext,
)
from framework.schemas.run import Run, RunStatus
from framework.storage.backend import FileStorage

if TYPE_CHECKING:
    from framework.runtime.guardrail_engine import GuardrailEngine

logger = logging.getLogger(__name__)


class Runtime:
    """
    The runtime environment that agents execute within.

    Usage:
        runtime = Runtime("/path/to/storage")

        # Start a run
        run_id = runtime.start_run("goal_123", "Qualify sales leads")

        # Record a decision
        decision_id = runtime.decide(
            node_id="lead-qualifier",
            intent="Determine if lead has budget",
            options=[
                {"id": "ask", "description": "Ask the lead directly"},
                {"id": "infer", "description": "Infer from company size"},
            ],
            chosen="infer",
            reasoning="Company data is available, asking would be slower"
        )

        # Record the outcome
        runtime.record_outcome(
            decision_id=decision_id,
            success=True,
            result={"has_budget": True, "estimated": "$50k"},
            summary="Inferred budget of $50k from company revenue"
        )

        # End the run
        runtime.end_run(success=True, narrative="Qualified 10 leads successfully")

    With Guardrails:
        from framework.runtime.guardrail_engine import GuardrailEngine, create_strict_guardrails

        config = create_strict_guardrails(max_tokens_per_run=50000)
        runtime = Runtime("/path/to/storage", guardrail_config=config)

        # Guardrails automatically check decisions and record violations
    """

    def __init__(
        self,
        storage_path: str | Path,
        guardrail_config: GuardrailConfig | None = None,
    ):
        self.storage = FileStorage(storage_path)
        self._current_run: Run | None = None
        self._current_node: str = "unknown"

        # Guardrails support
        self._guardrail_config = guardrail_config
        self._guardrail_engine: GuardrailEngine | None = None
        self._run_context: RunContext | None = None

        if guardrail_config:
            from framework.runtime.guardrail_engine import GuardrailEngine
            self._guardrail_engine = GuardrailEngine(guardrail_config)

    @property
    def guardrails_enabled(self) -> bool:
        """Check if guardrails are enabled for this runtime."""
        return self._guardrail_engine is not None and self._guardrail_config is not None

    # === RUN LIFECYCLE ===

    def start_run(
        self,
        goal_id: str,
        goal_description: str = "",
        input_data: dict[str, Any] | None = None,
    ) -> str:
        """
        Start a new run.

        Args:
            goal_id: The ID of the goal being pursued
            goal_description: Human-readable description of the goal
            input_data: Initial input to the run

        Returns:
            The run ID
        """
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        self._current_run = Run(
            id=run_id,
            goal_id=goal_id,
            goal_description=goal_description,
            input_data=input_data or {},
        )

        # Initialize guardrail context for this run
        if self.guardrails_enabled:
            self._run_context = RunContext(
                run_id=run_id,
                goal_id=goal_id,
            )

        return run_id

    def end_run(
        self,
        success: bool,
        narrative: str = "",
        output_data: dict[str, Any] | None = None,
    ) -> None:
        """
        End the current run.

        Args:
            success: Whether the run achieved its goal
            narrative: Human-readable summary of what happened
            output_data: Final output of the run
        """
        if self._current_run is None:
            # Gracefully handle case where run was already ended or never started
            # This can happen during exception handling cascades
            logger.warning("end_run called but no run in progress (already ended or never started)")
            return

        status = RunStatus.COMPLETED if success else RunStatus.FAILED
        self._current_run.output_data = output_data or {}
        self._current_run.complete(status, narrative)

        # Save to storage
        self.storage.save_run(self._current_run)
        self._current_run = None

        # Clear guardrail context
        self._run_context = None

    def set_node(self, node_id: str) -> None:
        """Set the current node context for subsequent decisions."""
        self._current_node = node_id

    @property
    def current_run(self) -> Run | None:
        """Get the current run (for inspection)."""
        return self._current_run

    # === GUARDRAIL METHODS ===

    def check_guardrails_before(
        self,
        node_id: str,
        intent: str,
        tool_name: str | None = None,
        tool_params: dict[str, Any] | None = None,
        estimated_tokens: int = 0,
    ) -> GuardrailResult:
        """
        Check guardrails before executing a decision.

        Call this before decide() to check if the decision should proceed.
        If blocked, the decision should not be executed.

        Args:
            node_id: Node making the decision
            intent: What the decision aims to accomplish
            tool_name: Name of tool being called (if applicable)
            tool_params: Parameters for the tool call
            estimated_tokens: Estimated token usage

        Returns:
            GuardrailResult indicating whether to proceed
        """
        if not self.guardrails_enabled or self._run_context is None:
            return GuardrailResult()  # Allow by default

        plan = DecisionPlan(
            node_id=node_id,
            intent=intent,
            tool_name=tool_name,
            tool_params=tool_params or {},
            estimated_tokens=estimated_tokens,
        )

        result = self._guardrail_engine.check_before_decision(plan, self._run_context)

        # Record any violations as problems
        if result.has_violations and self._current_run:
            for violation in result.violations:
                problem_data = self._guardrail_engine.create_problem_from_violation(violation)
                self._current_run.add_problem(**problem_data)

        return result

    def check_guardrails_after(
        self,
        node_id: str,
        success: bool,
        tokens_used: int = 0,
        latency_ms: int = 0,
        tool_name: str | None = None,
    ) -> GuardrailResult:
        """
        Check guardrails after a decision has executed.

        Call this after record_outcome() to evaluate the result
        and update tracking for loop detection, etc.

        Args:
            node_id: Node that made the decision
            success: Whether the decision succeeded
            tokens_used: Actual tokens consumed
            latency_ms: Actual latency
            tool_name: Name of tool called (if any)

        Returns:
            GuardrailResult with any violations detected
        """
        if not self.guardrails_enabled or self._run_context is None:
            return GuardrailResult()

        result = self._guardrail_engine.check_after_decision(
            outcome_success=success,
            outcome_tokens=tokens_used,
            outcome_latency_ms=latency_ms,
            tool_name=tool_name,
            node_id=node_id,
            context=self._run_context,
        )

        # Record any violations as problems
        if result.has_violations and self._current_run:
            for violation in result.violations:
                problem_data = self._guardrail_engine.create_problem_from_violation(violation)
                self._current_run.add_problem(**problem_data)

        return result

    # === DECISION RECORDING ===

    def decide(
        self,
        intent: str,
        options: list[dict[str, Any]],
        chosen: str,
        reasoning: str,
        node_id: str | None = None,
        decision_type: DecisionType = DecisionType.CUSTOM,
        constraints: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Record a decision the agent made.

        This is the PRIMARY method agents should call. It captures:
        - What the agent was trying to do
        - What options it considered
        - What it chose and why

        Args:
            intent: What the agent was trying to accomplish
            options: List of options considered. Each should have:
                - id: Unique identifier
                - description: What this option does
                - action_type: "tool_call", "generate", "delegate", etc.
                - action_params: Parameters for the action (optional)
                - pros: Why this might be good (optional)
                - cons: Why this might be bad (optional)
                - confidence: How confident (0-1, optional)
            chosen: ID of the chosen option
            reasoning: Why the agent chose this option
            node_id: Which node made this decision (uses current if not set)
            decision_type: Type of decision
            constraints: Active constraints that influenced the decision
            context: Additional context available when deciding

        Returns:
            The decision ID (use to record outcome later), or empty string if no run
        """
        if self._current_run is None:
            # Gracefully handle case where run ended during exception handling
            logger.warning(f"decide called but no run in progress: {intent}")
            return ""

        # Build Option objects
        option_objects = []
        for opt in options:
            option_objects.append(
                Option(
                    id=opt["id"],
                    description=opt.get("description", ""),
                    action_type=opt.get("action_type", "unknown"),
                    action_params=opt.get("action_params", {}),
                    pros=opt.get("pros", []),
                    cons=opt.get("cons", []),
                    confidence=opt.get("confidence", 0.5),
                )
            )

        # Create decision
        decision_id = f"dec_{len(self._current_run.decisions)}"
        decision = Decision(
            id=decision_id,
            node_id=node_id or self._current_node,
            intent=intent,
            decision_type=decision_type,
            options=option_objects,
            chosen_option_id=chosen,
            reasoning=reasoning,
            active_constraints=constraints or [],
            input_context=context or {},
        )

        self._current_run.add_decision(decision)
        return decision_id

    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        result: Any = None,
        error: str | None = None,
        summary: str = "",
        state_changes: dict[str, Any] | None = None,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """
        Record the outcome of a decision.

        Call this AFTER executing the action to record what happened.

        Args:
            decision_id: ID returned from decide()
            success: Whether the action succeeded
            result: The actual result/output
            error: Error message if failed
            summary: Human-readable summary of what happened
            state_changes: What state changed as a result
            tokens_used: LLM tokens consumed
            latency_ms: Time taken in milliseconds
        """
        if self._current_run is None:
            # Gracefully handle case where run ended during exception handling
            # This can happen in cascading error scenarios
            logger.warning(
                f"record_outcome called but no run in progress (decision_id={decision_id})"
            )
            return

        outcome = Outcome(
            success=success,
            result=result,
            error=error,
            summary=summary,
            state_changes=state_changes or {},
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

        self._current_run.record_outcome(decision_id, outcome)

    # === PROBLEM RECORDING ===

    def report_problem(
        self,
        severity: str,
        description: str,
        decision_id: str | None = None,
        root_cause: str | None = None,
        suggested_fix: str | None = None,
    ) -> str:
        """
        Report a problem that occurred.

        Agents can self-report issues they notice. This helps Builder
        understand what's going wrong.

        Args:
            severity: "critical", "warning", or "minor"
            description: What went wrong
            decision_id: Which decision caused this (if known)
            root_cause: Why it went wrong (if known)
            suggested_fix: What might fix it (if known)

        Returns:
            The problem ID, or empty string if no run in progress
        """
        if self._current_run is None:
            # Gracefully handle case where run ended during exception handling
            # Log the problem since we can't store it, then return empty ID
            logger.warning(
                f"report_problem called but no run in progress: [{severity}] {description}"
            )
            return ""

        return self._current_run.add_problem(
            severity=severity,
            description=description,
            decision_id=decision_id,
            root_cause=root_cause,
            suggested_fix=suggested_fix,
        )

    # === CONVENIENCE METHODS ===

    def decide_and_execute(
        self,
        intent: str,
        options: list[dict[str, Any]],
        chosen: str,
        reasoning: str,
        executor: Callable,
        **kwargs,
    ) -> tuple[str, Any]:
        """
        Record a decision and immediately execute it.

        This is a convenience method that combines decide() and record_outcome().

        Args:
            intent: What the agent is trying to do
            options: Options considered
            chosen: ID of chosen option
            reasoning: Why this option
            executor: Function to call to execute the action
            **kwargs: Additional args for decide()

        Returns:
            Tuple of (decision_id, result)
        """
        import time

        decision_id = self.decide(
            intent=intent,
            options=options,
            chosen=chosen,
            reasoning=reasoning,
            **kwargs,
        )

        # Execute and measure
        start = time.time()
        try:
            result = executor()
            latency_ms = int((time.time() - start) * 1000)

            self.record_outcome(
                decision_id=decision_id,
                success=True,
                result=result,
                latency_ms=latency_ms,
            )
            return decision_id, result

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)

            self.record_outcome(
                decision_id=decision_id,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise

    def quick_decision(
        self,
        intent: str,
        action: str,
        reasoning: str,
        node_id: str | None = None,
    ) -> str:
        """
        Record a simple decision with a single action (no alternatives).

        Use this for straightforward decisions where there's really only
        one sensible option.

        Args:
            intent: What the agent is trying to do
            action: What it's doing
            reasoning: Why

        Returns:
            The decision ID
        """
        return self.decide(
            intent=intent,
            options=[
                {
                    "id": "action",
                    "description": action,
                    "action_type": "execute",
                }
            ],
            chosen="action",
            reasoning=reasoning,
            node_id=node_id,
        )
