"""
Guardrail Engine - Runtime policy enforcement for agent decisions.

The GuardrailEngine validates decisions before and after execution,
preventing common failure modes and enforcing safety policies.

Integration points:
- Runtime.decide() → check_before_decision()
- Runtime.record_outcome() → check_after_decision()
- Violations are recorded to Run.problems

Example:
    engine = GuardrailEngine(config)

    # Before executing a decision
    plan = DecisionPlan(node_id="search", tool_name="web_search", ...)
    result = engine.check_before_decision(plan, run_context)

    if result.blocked:
        # Don't execute, report violation
        for violation in result.violations:
            runtime.report_problem(...)
    else:
        # Proceed with execution
        ...

    # After execution
    result = engine.check_after_decision(decision, outcome, run_context)
    for violation in result.violations:
        runtime.report_problem(...)
"""

import logging
import uuid
from typing import Any

from framework.schemas.guardrails import (
    DecisionPlan,
    GuardrailAction,
    GuardrailConfig,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailViolation,
    RunContext,
)

logger = logging.getLogger(__name__)


class GuardrailEngine:
    """
    Engine for evaluating and enforcing guardrails.

    Provides methods to check decisions before and after execution,
    returning results that indicate whether to proceed, warn, or block.
    """

    def __init__(self, config: GuardrailConfig | None = None):
        """
        Initialize the guardrail engine.

        Args:
            config: Guardrail configuration. If None, uses permissive defaults.
        """
        self.config = config or GuardrailConfig()
        self._violation_counter = 0

    def _generate_violation_id(self) -> str:
        """Generate a unique violation ID."""
        self._violation_counter += 1
        return f"guardrail_violation_{self._violation_counter}_{uuid.uuid4().hex[:6]}"

    def check_before_decision(
        self,
        plan: DecisionPlan,
        context: RunContext,
    ) -> GuardrailResult:
        """
        Check guardrails before a decision is executed.

        This is called BEFORE the decision runs, allowing us to
        prevent problematic decisions from executing.

        Args:
            plan: The proposed decision plan
            context: Current run context with cumulative stats

        Returns:
            GuardrailResult indicating whether to proceed
        """
        if not self.config.enabled:
            return GuardrailResult(action=GuardrailAction.ALLOW, allowed=True)

        violations: list[GuardrailViolation] = []
        warnings: list[str] = []

        # Check tool-related guardrails
        if plan.tool_name:
            tool_violations = self._check_tool_before(plan.tool_name, context)
            violations.extend(tool_violations)

        # Check token budget (estimated)
        if plan.estimated_tokens > 0:
            token_violations = self._check_tokens_before(plan.estimated_tokens, context)
            violations.extend(token_violations)

        # Check retry limits
        retry_violations = self._check_retries_before(plan.node_id, context)
        violations.extend(retry_violations)

        # Determine overall action
        action = self._determine_action(violations)
        allowed = action != GuardrailAction.BLOCK

        # Generate warnings for non-blocking violations
        for v in violations:
            if v.action == GuardrailAction.WARN:
                warnings.append(f"[{v.guardrail_type}] {v.description}")

        if violations:
            logger.info(
                f"Guardrail check: {len(violations)} violation(s), action={action.value}"
            )

        return GuardrailResult(
            action=action,
            allowed=allowed,
            violations=violations,
            warnings=warnings,
        )

    def check_after_decision(
        self,
        outcome_success: bool,
        outcome_tokens: int,
        outcome_latency_ms: int,
        tool_name: str | None,
        node_id: str,
        context: RunContext,
    ) -> GuardrailResult:
        """
        Check guardrails after a decision has executed.

        This is called AFTER the decision runs, allowing us to
        evaluate the outcome and update tracking.

        Args:
            outcome_success: Whether the decision succeeded
            outcome_tokens: Tokens used by the decision
            outcome_latency_ms: Latency in milliseconds
            tool_name: Name of tool called (if any)
            node_id: Node that made the decision
            context: Current run context (will be updated)

        Returns:
            GuardrailResult with any violations detected
        """
        if not self.config.enabled:
            return GuardrailResult(action=GuardrailAction.ALLOW, allowed=True)

        violations: list[GuardrailViolation] = []
        warnings: list[str] = []

        # Update context with actual usage
        context.total_tokens_used += outcome_tokens
        context.total_decisions += 1

        # Check token budget (actual)
        token_violations = self._check_tokens_after(outcome_tokens, context)
        violations.extend(token_violations)

        # Check latency
        latency_violations = self._check_latency(outcome_latency_ms)
        violations.extend(latency_violations)

        # Update tool tracking
        if tool_name:
            context.increment_tool_call(tool_name)
            if outcome_success:
                context.reset_tool_failure_streak(tool_name)
            else:
                streak = context.record_tool_failure(tool_name)
                # Check for tool loop
                loop_violations = self._check_tool_loop(tool_name, streak)
                violations.extend(loop_violations)

        # Update retry tracking for failures
        if not outcome_success:
            retry_count = context.increment_node_retry(node_id)
            # Check if we're exceeding retry limits
            retry_violations = self._check_retries_after(node_id, retry_count, context)
            violations.extend(retry_violations)

        # Determine overall action (for post-decision, this is mostly informational)
        action = self._determine_action(violations)

        for v in violations:
            warnings.append(f"[{v.guardrail_type}] {v.description}")

        return GuardrailResult(
            action=action,
            allowed=True,  # Post-decision checks don't block (already executed)
            violations=violations,
            warnings=warnings,
        )

    def _check_tool_before(
        self,
        tool_name: str,
        context: RunContext,
    ) -> list[GuardrailViolation]:
        """Check tool-related guardrails before execution."""
        violations = []

        # Check if tool is forbidden
        is_forbidden, reason = self.config.is_tool_forbidden(tool_name)
        if is_forbidden:
            violations.append(
                GuardrailViolation(
                    id=self._generate_violation_id(),
                    guardrail_type="tool_forbidden",
                    action=GuardrailAction.BLOCK,
                    severity=GuardrailSeverity.CRITICAL,
                    description=reason,
                    details={"tool_name": tool_name},
                    suggested_fix=(
                        f"Remove call to forbidden tool '{tool_name}' "
                        "or update guardrail config"
                    ),
                )
            )
            return violations

        # Check call count limits
        tool_config = self.config.get_tool_config(tool_name)
        if tool_config and tool_config.max_calls_per_run:
            current_calls = context.tool_call_counts.get(tool_name, 0)
            if current_calls >= tool_config.max_calls_per_run:
                violations.append(
                    GuardrailViolation(
                        id=self._generate_violation_id(),
                        guardrail_type="tool_limit",
                        action=GuardrailAction.BLOCK,
                        severity=GuardrailSeverity.WARNING,
                        description=(
                            f"Tool '{tool_name}' has reached max calls "
                            f"({current_calls}/{tool_config.max_calls_per_run})"
                        ),
                        details={
                            "tool_name": tool_name,
                            "current_calls": current_calls,
                            "max_calls": tool_config.max_calls_per_run,
                        },
                        suggested_fix="Consider alternative approaches or increase limit",
                    )
                )

        # Check for potential loop (consecutive failures)
        tool_config = self.config.get_tool_config(tool_name)
        max_failures = (
            tool_config.max_consecutive_failures
            if tool_config
            else 3  # Default
        )
        current_streak = context.tool_failure_streaks.get(tool_name, 0)
        if current_streak >= max_failures:
            violations.append(
                GuardrailViolation(
                    id=self._generate_violation_id(),
                    guardrail_type="tool_loop",
                    action=GuardrailAction.BLOCK,
                    severity=GuardrailSeverity.CRITICAL,
                    description=(
                        f"Tool '{tool_name}' has failed {current_streak} consecutive times - "
                        "possible infinite loop detected"
                    ),
                    details={
                        "tool_name": tool_name,
                        "consecutive_failures": current_streak,
                        "max_allowed": max_failures,
                    },
                    suggested_fix="Break the loop by trying a different approach or tool",
                )
            )

        return violations

    def _check_tool_loop(
        self,
        tool_name: str,
        failure_streak: int,
    ) -> list[GuardrailViolation]:
        """Check for tool loop after a failure."""
        violations = []

        tool_config = self.config.get_tool_config(tool_name)
        max_failures = (
            tool_config.max_consecutive_failures
            if tool_config
            else 3
        )

        # Warn when approaching limit
        if failure_streak == max_failures - 1:
            violations.append(
                GuardrailViolation(
                    id=self._generate_violation_id(),
                    guardrail_type="tool_loop_warning",
                    action=GuardrailAction.WARN,
                    severity=GuardrailSeverity.WARNING,
                    description=(
                        f"Tool '{tool_name}' approaching failure limit "
                        f"({failure_streak}/{max_failures})"
                    ),
                    details={
                        "tool_name": tool_name,
                        "consecutive_failures": failure_streak,
                    },
                    suggested_fix="Consider trying a different approach",
                )
            )

        return violations

    def _check_tokens_before(
        self,
        estimated_tokens: int,
        context: RunContext,
    ) -> list[GuardrailViolation]:
        """Check token budget before execution."""
        violations = []

        if not self.config.tokens:
            return violations

        # Check per-decision limit
        if self.config.tokens.max_tokens_per_decision:
            if estimated_tokens > self.config.tokens.max_tokens_per_decision:
                violations.append(
                    GuardrailViolation(
                        id=self._generate_violation_id(),
                        guardrail_type="token_decision_limit",
                        action=GuardrailAction.WARN,
                        severity=GuardrailSeverity.WARNING,
                        description=(
                            f"Estimated tokens ({estimated_tokens}) exceeds "
                            f"per-decision limit ({self.config.tokens.max_tokens_per_decision})"
                        ),
                        details={
                            "estimated_tokens": estimated_tokens,
                            "limit": self.config.tokens.max_tokens_per_decision,
                        },
                        suggested_fix="Reduce prompt size or use a more efficient model",
                    )
                )

        # Check run budget
        if self.config.tokens.max_tokens_per_run:
            projected_total = context.total_tokens_used + estimated_tokens
            if projected_total > self.config.tokens.max_tokens_per_run:
                violations.append(
                    GuardrailViolation(
                        id=self._generate_violation_id(),
                        guardrail_type="token_run_limit",
                        action=GuardrailAction.BLOCK,
                        severity=GuardrailSeverity.CRITICAL,
                        description=(
                            f"Projected tokens ({projected_total}) would exceed "
                            f"run budget ({self.config.tokens.max_tokens_per_run})"
                        ),
                        details={
                            "current_tokens": context.total_tokens_used,
                            "estimated_additional": estimated_tokens,
                            "projected_total": projected_total,
                            "limit": self.config.tokens.max_tokens_per_run,
                        },
                        suggested_fix="Reduce token usage or increase budget",
                    )
                )
            # Warn when approaching limit
            elif self.config.tokens.warn_threshold_percent:
                threshold = (
                    self.config.tokens.max_tokens_per_run
                    * self.config.tokens.warn_threshold_percent
                )
                if projected_total > threshold:
                    pct_used = projected_total / self.config.tokens.max_tokens_per_run
                    violations.append(
                        GuardrailViolation(
                            id=self._generate_violation_id(),
                            guardrail_type="token_budget_warning",
                            action=GuardrailAction.WARN,
                            severity=GuardrailSeverity.WARNING,
                            description=(
                                f"Approaching token budget "
                                f"({int(pct_used * 100)}% used)"
                            ),
                            details={
                                "current_tokens": context.total_tokens_used,
                                "budget": self.config.tokens.max_tokens_per_run,
                                "percent_used": pct_used,
                            },
                        )
                    )

        return violations

    def _check_tokens_after(
        self,
        actual_tokens: int,
        context: RunContext,
    ) -> list[GuardrailViolation]:
        """Check token usage after execution."""
        violations = []

        if not self.config.tokens:
            return violations

        # Check per-decision limit
        if self.config.tokens.max_tokens_per_decision:
            if actual_tokens > self.config.tokens.max_tokens_per_decision:
                violations.append(
                    GuardrailViolation(
                        id=self._generate_violation_id(),
                        guardrail_type="token_decision_exceeded",
                        action=GuardrailAction.WARN,
                        severity=GuardrailSeverity.WARNING,
                        description=(
                            f"Decision used {actual_tokens} tokens, "
                            f"exceeding limit of {self.config.tokens.max_tokens_per_decision}"
                        ),
                        details={
                            "actual_tokens": actual_tokens,
                            "limit": self.config.tokens.max_tokens_per_decision,
                        },
                    )
                )

        # Check run budget
        if self.config.tokens.max_tokens_per_run:
            if context.total_tokens_used > self.config.tokens.max_tokens_per_run:
                violations.append(
                    GuardrailViolation(
                        id=self._generate_violation_id(),
                        guardrail_type="token_run_exceeded",
                        action=GuardrailAction.WARN,
                        severity=GuardrailSeverity.CRITICAL,
                        description=(
                            f"Run has used {context.total_tokens_used} tokens, "
                            f"exceeding budget of {self.config.tokens.max_tokens_per_run}"
                        ),
                        details={
                            "total_tokens": context.total_tokens_used,
                            "budget": self.config.tokens.max_tokens_per_run,
                        },
                        suggested_fix="Consider ending the run or reducing token usage",
                    )
                )

        return violations

    def _check_retries_before(
        self,
        node_id: str,
        context: RunContext,
    ) -> list[GuardrailViolation]:
        """Check retry limits before execution."""
        violations = []

        if not self.config.retries:
            return violations

        # Check node retry limit
        node_retries = context.node_retry_counts.get(node_id, 0)
        if node_retries >= self.config.retries.max_retries_per_node:
            violations.append(
                GuardrailViolation(
                    id=self._generate_violation_id(),
                    guardrail_type="retry_node_limit",
                    action=GuardrailAction.BLOCK,
                    severity=GuardrailSeverity.CRITICAL,
                    description=(
                        f"Node '{node_id}' has reached max retries "
                        f"({node_retries}/{self.config.retries.max_retries_per_node})"
                    ),
                    details={
                        "node_id": node_id,
                        "retries": node_retries,
                        "max_retries": self.config.retries.max_retries_per_node,
                    },
                    suggested_fix="Investigate why this node keeps failing",
                )
            )

        # Check run retry limit
        if context.total_retries >= self.config.retries.max_retries_per_run:
            violations.append(
                GuardrailViolation(
                    id=self._generate_violation_id(),
                    guardrail_type="retry_run_limit",
                    action=GuardrailAction.BLOCK,
                    severity=GuardrailSeverity.CRITICAL,
                    description=(
                        f"Run has reached max total retries "
                        f"({context.total_retries}/{self.config.retries.max_retries_per_run})"
                    ),
                    details={
                        "total_retries": context.total_retries,
                        "max_retries": self.config.retries.max_retries_per_run,
                    },
                    suggested_fix="This run is experiencing too many failures",
                )
            )

        return violations

    def _check_retries_after(
        self,
        node_id: str,
        retry_count: int,
        context: RunContext,
    ) -> list[GuardrailViolation]:
        """Check retry status after a failure."""
        violations = []

        if not self.config.retries:
            return violations

        # Warn when approaching node limit
        if retry_count == self.config.retries.max_retries_per_node - 1:
            violations.append(
                GuardrailViolation(
                    id=self._generate_violation_id(),
                    guardrail_type="retry_node_warning",
                    action=GuardrailAction.WARN,
                    severity=GuardrailSeverity.WARNING,
                    description=(
                        f"Node '{node_id}' approaching retry limit "
                        f"({retry_count}/{self.config.retries.max_retries_per_node})"
                    ),
                    details={
                        "node_id": node_id,
                        "retries": retry_count,
                    },
                )
            )

        return violations

    def _check_latency(self, latency_ms: int) -> list[GuardrailViolation]:
        """Check latency guardrails."""
        violations = []

        if not self.config.latency:
            return violations

        if self.config.latency.max_latency_ms:
            if latency_ms > self.config.latency.max_latency_ms:
                violations.append(
                    GuardrailViolation(
                        id=self._generate_violation_id(),
                        guardrail_type="latency_exceeded",
                        action=GuardrailAction.WARN,
                        severity=GuardrailSeverity.WARNING,
                        description=(
                            f"Decision took {latency_ms}ms, "
                            f"exceeding max latency of {self.config.latency.max_latency_ms}ms"
                        ),
                        details={
                            "latency_ms": latency_ms,
                            "max_latency_ms": self.config.latency.max_latency_ms,
                        },
                    )
                )
        elif latency_ms > self.config.latency.warn_latency_ms:
            violations.append(
                GuardrailViolation(
                    id=self._generate_violation_id(),
                    guardrail_type="latency_warning",
                    action=GuardrailAction.WARN,
                    severity=GuardrailSeverity.MINOR,
                    description=(
                        f"Decision took {latency_ms}ms, "
                        f"above warning threshold of {self.config.latency.warn_latency_ms}ms"
                    ),
                    details={
                        "latency_ms": latency_ms,
                        "warn_threshold_ms": self.config.latency.warn_latency_ms,
                    },
                )
            )

        return violations

    def _determine_action(
        self,
        violations: list[GuardrailViolation],
    ) -> GuardrailAction:
        """Determine the overall action based on all violations."""
        if not violations:
            return GuardrailAction.ALLOW

        # If any violation is BLOCK, the overall action is BLOCK
        for v in violations:
            if v.action == GuardrailAction.BLOCK:
                return GuardrailAction.BLOCK

        # If any violation is WARN, the overall action is WARN
        for v in violations:
            if v.action == GuardrailAction.WARN:
                return GuardrailAction.WARN

        return GuardrailAction.ALLOW

    def create_problem_from_violation(
        self,
        violation: GuardrailViolation,
    ) -> dict[str, Any]:
        """
        Convert a violation to a Problem dict for Run.add_problem().

        Returns:
            Dict suitable for passing to Run.add_problem()
        """
        return {
            "severity": violation.severity.value,
            "description": f"[Guardrail: {violation.guardrail_type}] {violation.description}",
            "root_cause": f"Guardrail violation: {violation.guardrail_type}",
            "suggested_fix": violation.suggested_fix,
        }


def create_default_guardrails() -> GuardrailConfig:
    """
    Create a sensible default guardrail configuration.

    This provides reasonable defaults that prevent common issues
    without being overly restrictive.
    """
    return GuardrailConfig(
        enabled=True,
        tokens=None,  # No token limits by default
        retries=None,  # Use defaults
        latency=None,  # Use defaults
        default_action=GuardrailAction.WARN,
    )


def create_strict_guardrails(
    max_tokens_per_run: int = 100000,
    max_tokens_per_decision: int = 10000,
    forbidden_tools: list[str] | None = None,
) -> GuardrailConfig:
    """
    Create a strict guardrail configuration for production.

    Args:
        max_tokens_per_run: Maximum tokens for the entire run
        max_tokens_per_decision: Maximum tokens per decision
        forbidden_tools: List of forbidden tool names
    """
    from framework.schemas.guardrails import (
        LatencyGuardConfig,
        RetryGuardConfig,
        TokenGuardConfig,
    )

    return GuardrailConfig(
        enabled=True,
        tokens=TokenGuardConfig(
            max_tokens_per_run=max_tokens_per_run,
            max_tokens_per_decision=max_tokens_per_decision,
            warn_threshold_percent=0.8,
        ),
        retries=RetryGuardConfig(
            max_retries_per_node=3,
            max_retries_per_run=10,
        ),
        latency=LatencyGuardConfig(
            warn_latency_ms=30000,
            max_latency_ms=60000,
        ),
        forbidden_tools=forbidden_tools or [],
        default_action=GuardrailAction.WARN,
    )
