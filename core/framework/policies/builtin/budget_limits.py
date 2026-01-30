"""Budget limit policy for resource control.

This policy enforces budget limits on token usage, cost, time,
and execution counts, preventing runaway agent execution.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from framework.policies.base import BasePolicy
from framework.policies.decisions import PolicyDecision, Severity
from framework.policies.events import PolicyEvent, PolicyEventType


class BudgetMode(Enum):
    """Operating modes for budget enforcement."""

    PERMISSIVE = "permissive"
    """Warn at thresholds but don't block (SUGGEST only)."""

    BALANCED = "balanced"
    """Warn at soft limit, block at hard limit."""

    STRICT = "strict"
    """Block immediately at any limit."""


@dataclass
class BudgetConfig:
    """Configuration for a single budget limit.

    Attributes:
        soft_limit: Threshold for warnings (e.g., 80% of hard limit)
        hard_limit: Threshold for blocking
        current: Current usage (updated externally)
        unit: Unit of measurement for display
    """

    soft_limit: Optional[float] = None
    hard_limit: Optional[float] = None
    current: float = 0.0
    unit: str = ""

    @property
    def soft_limit_reached(self) -> bool:
        """Check if soft limit is reached."""
        if self.soft_limit is None:
            return False
        return self.current >= self.soft_limit

    @property
    def hard_limit_reached(self) -> bool:
        """Check if hard limit is reached."""
        if self.hard_limit is None:
            return False
        return self.current >= self.hard_limit

    @property
    def usage_percent(self) -> Optional[float]:
        """Get usage as percentage of hard limit."""
        if self.hard_limit is None or self.hard_limit == 0:
            return None
        return (self.current / self.hard_limit) * 100


@dataclass
class BudgetLimitPolicy(BasePolicy):
    """Policy that enforces resource budgets on agent execution.

    This policy tracks and enforces limits on:
    - Token usage (input + output tokens)
    - Cost (in dollars or credits)
    - Time (execution duration)
    - Tool calls (number of invocations)
    - LLM calls (number of requests)

    Operating modes:
    - permissive: Warn at thresholds but don't block
    - balanced: Warn at soft limit (80%), block at hard limit (100%)
    - strict: Block immediately at any limit

    The policy evaluates RUN_CONTROL events which should be emitted
    periodically by the runtime with current usage metrics.

    Attributes:
        mode: Operating mode (permissive, balanced, strict)
        token_budget: Token usage limits
        cost_budget: Cost limits (dollars/credits)
        time_budget: Execution time limits (seconds)
        tool_call_budget: Tool invocation limits
        llm_call_budget: LLM request limits

    Example:
        policy = BudgetLimitPolicy(
            mode=BudgetMode.BALANCED,
            token_budget=BudgetConfig(soft_limit=8000, hard_limit=10000, unit="tokens"),
            cost_budget=BudgetConfig(soft_limit=0.80, hard_limit=1.00, unit="USD"),
        )
        engine.register_policy(policy)

        # Runtime emits periodic updates
        event = PolicyEvent.create(
            event_type=PolicyEventType.RUN_CONTROL,
            payload={
                "tokens_used": 7500,
                "cost_usd": 0.75,
                "elapsed_seconds": 45,
            },
            execution_id="exec-123",
        )
    """

    mode: BudgetMode = BudgetMode.BALANCED
    token_budget: BudgetConfig = field(
        default_factory=lambda: BudgetConfig(
            soft_limit=80000, hard_limit=100000, unit="tokens"
        )
    )
    cost_budget: BudgetConfig = field(
        default_factory=lambda: BudgetConfig(
            soft_limit=0.80, hard_limit=1.00, unit="USD"
        )
    )
    time_budget: BudgetConfig = field(
        default_factory=lambda: BudgetConfig(
            soft_limit=240, hard_limit=300, unit="seconds"
        )
    )
    tool_call_budget: BudgetConfig = field(
        default_factory=lambda: BudgetConfig(
            soft_limit=80, hard_limit=100, unit="calls"
        )
    )
    llm_call_budget: BudgetConfig = field(
        default_factory=lambda: BudgetConfig(
            soft_limit=40, hard_limit=50, unit="calls"
        )
    )

    # Internal tracking
    _start_time: Optional[float] = field(default=None, repr=False)

    # Policy metadata
    _id: str = "budget-limits"
    _name: str = "Budget Limits"
    _description: str = (
        "Enforces resource budgets on token usage, cost, time, and "
        "execution counts to prevent runaway agent behavior."
    )

    def __post_init__(self) -> None:
        """Initialize start time for time tracking."""
        if self._start_time is None:
            self._start_time = time.time()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def event_types(self) -> list[PolicyEventType]:
        return [PolicyEventType.RUN_CONTROL, PolicyEventType.TOOL_CALL, PolicyEventType.LLM_REQUEST]

    def _update_from_payload(self, payload: dict) -> None:
        """Update budget tracking from event payload."""
        # Token usage
        if "tokens_used" in payload:
            self.token_budget.current = payload["tokens_used"]
        if "input_tokens" in payload and "output_tokens" in payload:
            self.token_budget.current = payload["input_tokens"] + payload["output_tokens"]

        # Cost
        if "cost_usd" in payload:
            self.cost_budget.current = payload["cost_usd"]
        if "cost" in payload:
            self.cost_budget.current = payload["cost"]

        # Time
        if "elapsed_seconds" in payload:
            self.time_budget.current = payload["elapsed_seconds"]
        elif self._start_time:
            self.time_budget.current = time.time() - self._start_time

        # Tool calls
        if "tool_call_count" in payload:
            self.tool_call_budget.current = payload["tool_call_count"]

        # LLM calls
        if "llm_call_count" in payload:
            self.llm_call_budget.current = payload["llm_call_count"]

    def _check_budgets(
        self,
    ) -> tuple[list[tuple[str, BudgetConfig]], list[tuple[str, BudgetConfig]]]:
        """Check all budgets and return (soft_breached, hard_breached) lists."""
        budgets = [
            ("tokens", self.token_budget),
            ("cost", self.cost_budget),
            ("time", self.time_budget),
            ("tool_calls", self.tool_call_budget),
            ("llm_calls", self.llm_call_budget),
        ]

        soft_breached = []
        hard_breached = []

        for name, budget in budgets:
            if budget.hard_limit_reached:
                hard_breached.append((name, budget))
            elif budget.soft_limit_reached:
                soft_breached.append((name, budget))

        return soft_breached, hard_breached

    def _format_budget_status(self, name: str, budget: BudgetConfig) -> str:
        """Format a budget status message."""
        percent = budget.usage_percent
        if percent is not None:
            return f"{name}: {budget.current:.1f}/{budget.hard_limit:.1f} {budget.unit} ({percent:.0f}%)"
        return f"{name}: {budget.current:.1f} {budget.unit}"

    async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
        """Evaluate resource usage against budget limits.

        Args:
            event: The event to evaluate (RUN_CONTROL, TOOL_CALL, or LLM_REQUEST)

        Returns:
            PolicyDecision based on budget status
        """
        # Increment counters for relevant events
        if event.event_type == PolicyEventType.TOOL_CALL:
            self.tool_call_budget.current += 1
        elif event.event_type == PolicyEventType.LLM_REQUEST:
            self.llm_call_budget.current += 1

        # Update from payload if present
        self._update_from_payload(event.payload)

        # Check all budgets
        soft_breached, hard_breached = self._check_budgets()

        # Build status messages
        breach_details = []
        for name, budget in hard_breached:
            breach_details.append(self._format_budget_status(name, budget))
        for name, budget in soft_breached:
            breach_details.append(self._format_budget_status(name, budget))

        metadata: dict[str, Any] = {
            "token_usage": self.token_budget.current,
            "cost_usage": self.cost_budget.current,
            "time_usage": self.time_budget.current,
            "tool_call_count": self.tool_call_budget.current,
            "llm_call_count": self.llm_call_budget.current,
        }

        # Handle hard limit breaches
        if hard_breached:
            names = [name for name, _ in hard_breached]

            if self.mode == BudgetMode.PERMISSIVE:
                # Even permissive mode warns on hard limits
                return PolicyDecision.suggest(
                    policy_id=self.id,
                    reason=f"Budget exceeded for: {', '.join(names)}. {'; '.join(breach_details)}",
                    severity=Severity.HIGH,
                    tags=["budget", "exceeded"] + names,
                    metadata=metadata,
                )
            else:
                return PolicyDecision.block(
                    policy_id=self.id,
                    reason=f"Budget limit reached for: {', '.join(names)}. {'; '.join(breach_details)}",
                    severity=Severity.CRITICAL,
                    tags=["budget", "limit-reached"] + names,
                    metadata=metadata,
                )

        # Handle soft limit breaches
        if soft_breached:
            names = [name for name, _ in soft_breached]

            if self.mode == BudgetMode.STRICT:
                return PolicyDecision.require_confirm(
                    policy_id=self.id,
                    reason=f"Approaching budget limit for: {', '.join(names)}. {'; '.join(breach_details)}",
                    severity=Severity.MEDIUM,
                    tags=["budget", "warning"] + names,
                    metadata=metadata,
                )
            else:
                return PolicyDecision.suggest(
                    policy_id=self.id,
                    reason=f"Approaching budget limit for: {', '.join(names)}. {'; '.join(breach_details)}",
                    severity=Severity.LOW,
                    tags=["budget", "warning"] + names,
                    metadata=metadata,
                )

        # All within limits
        return PolicyDecision.allow(
            policy_id=self.id,
            reason="All budgets within limits",
            metadata=metadata,
        )

    def reset(self) -> None:
        """Reset all budget counters."""
        self.token_budget.current = 0
        self.cost_budget.current = 0
        self.time_budget.current = 0
        self.tool_call_budget.current = 0
        self.llm_call_budget.current = 0
        self._start_time = time.time()

    def set_token_limit(
        self, hard_limit: float, soft_limit: Optional[float] = None
    ) -> None:
        """Set token budget limits."""
        self.token_budget.hard_limit = hard_limit
        self.token_budget.soft_limit = soft_limit or (hard_limit * 0.8)

    def set_cost_limit(
        self, hard_limit: float, soft_limit: Optional[float] = None
    ) -> None:
        """Set cost budget limits."""
        self.cost_budget.hard_limit = hard_limit
        self.cost_budget.soft_limit = soft_limit or (hard_limit * 0.8)

    def set_time_limit(
        self, hard_limit: float, soft_limit: Optional[float] = None
    ) -> None:
        """Set time budget limits (in seconds)."""
        self.time_budget.hard_limit = hard_limit
        self.time_budget.soft_limit = soft_limit or (hard_limit * 0.8)

    def get_usage_summary(self) -> dict[str, Any]:
        """Get a summary of current usage across all budgets."""
        return {
            "tokens": {
                "current": self.token_budget.current,
                "soft_limit": self.token_budget.soft_limit,
                "hard_limit": self.token_budget.hard_limit,
                "percent": self.token_budget.usage_percent,
            },
            "cost": {
                "current": self.cost_budget.current,
                "soft_limit": self.cost_budget.soft_limit,
                "hard_limit": self.cost_budget.hard_limit,
                "percent": self.cost_budget.usage_percent,
            },
            "time": {
                "current": self.time_budget.current,
                "soft_limit": self.time_budget.soft_limit,
                "hard_limit": self.time_budget.hard_limit,
                "percent": self.time_budget.usage_percent,
            },
            "tool_calls": {
                "current": self.tool_call_budget.current,
                "soft_limit": self.tool_call_budget.soft_limit,
                "hard_limit": self.tool_call_budget.hard_limit,
                "percent": self.tool_call_budget.usage_percent,
            },
            "llm_calls": {
                "current": self.llm_call_budget.current,
                "soft_limit": self.llm_call_budget.soft_limit,
                "hard_limit": self.llm_call_budget.hard_limit,
                "percent": self.llm_call_budget.usage_percent,
            },
        }
