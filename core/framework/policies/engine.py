"""Policy engine for orchestrating policy evaluation.

The PolicyEngine is the central component that:
- Registers and manages policies
- Routes events to appropriate policies
- Evaluates policies with short-circuit logic
- Aggregates decisions and handles conflicts
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from framework.policies.base import Policy
from framework.policies.decisions import PolicyAction, PolicyDecision, Severity
from framework.policies.events import PolicyEvent, PolicyEventType
from framework.policies.exceptions import (
    ConfirmationRequiredError,
    PolicyRegistrationError,
    PolicyViolationError,
)

logger = logging.getLogger(__name__)


@dataclass
class AggregatedDecision:
    """Aggregated result from evaluating multiple policies.

    When multiple policies evaluate an event, their decisions
    are aggregated into a single result following these rules:
    - BLOCK wins (short-circuits evaluation)
    - REQUIRE_CONFIRM is next priority
    - SUGGEST decisions are collected
    - ALLOW only if all policies allow

    Attributes:
        final_action: The resulting action to take
        decisions: All individual policy decisions
        blocking_decision: The decision that caused a BLOCK (if any)
        confirmation_decision: The decision requiring confirmation (if any)
        suggestions: List of SUGGEST decisions
    """

    final_action: PolicyAction
    decisions: list[PolicyDecision]
    blocking_decision: Optional[PolicyDecision] = None
    confirmation_decision: Optional[PolicyDecision] = None
    suggestions: list[PolicyDecision] = field(default_factory=list)

    @property
    def is_allowed(self) -> bool:
        """Check if the action is allowed to proceed."""
        return self.final_action in (PolicyAction.ALLOW, PolicyAction.SUGGEST)

    @property
    def requires_confirmation(self) -> bool:
        """Check if human confirmation is required."""
        return self.final_action == PolicyAction.REQUIRE_CONFIRM

    @property
    def is_blocked(self) -> bool:
        """Check if the action is blocked."""
        return self.final_action == PolicyAction.BLOCK

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "final_action": self.final_action.value,
            "decision_count": len(self.decisions),
            "blocking_decision": (
                self.blocking_decision.to_dict()
                if self.blocking_decision
                else None
            ),
            "confirmation_decision": (
                self.confirmation_decision.to_dict()
                if self.confirmation_decision
                else None
            ),
            "suggestion_count": len(self.suggestions),
        }


DecisionCallback = Callable[[PolicyDecision, PolicyEvent], None]


class PolicyEngine:
    """Orchestrates policy evaluation for events.

    The engine manages a collection of policies and evaluates them
    against events. It supports:
    - Policy registration by event type
    - Ordered evaluation with short-circuit on BLOCK
    - Decision aggregation and conflict resolution
    - Callbacks for observability

    Example:
        engine = PolicyEngine()
        engine.register_policy(HighRiskToolGatingPolicy())

        event = PolicyEvent.create(
            event_type=PolicyEventType.TOOL_CALL,
            payload={"tool_name": "file_delete", "args": {"path": "/tmp/x"}},
            execution_id="exec-123",
        )

        result = await engine.evaluate(event)
        if result.is_blocked:
            raise PolicyViolationError(result.blocking_decision, event)
    """

    def __init__(
        self,
        *,
        raise_on_block: bool = True,
        raise_on_confirm: bool = False,
    ) -> None:
        """Initialize the PolicyEngine.

        Args:
            raise_on_block: Raise PolicyViolationError on BLOCK decisions
            raise_on_confirm: Raise ConfirmationRequiredError on REQUIRE_CONFIRM
        """
        self._policies: dict[str, Policy] = {}
        self._policies_by_event_type: dict[PolicyEventType, list[Policy]] = {
            event_type: [] for event_type in PolicyEventType
        }
        self._decision_callbacks: list[DecisionCallback] = []
        self._raise_on_block = raise_on_block
        self._raise_on_confirm = raise_on_confirm

    @property
    def policies(self) -> dict[str, Policy]:
        """Get all registered policies by ID."""
        return self._policies.copy()

    def register_policy(self, policy: Policy) -> None:
        """Register a policy with the engine.

        Args:
            policy: The policy to register

        Raises:
            PolicyRegistrationError: If policy ID is already registered
        """
        if policy.id in self._policies:
            raise PolicyRegistrationError(
                f"Policy with ID '{policy.id}' is already registered"
            )

        self._policies[policy.id] = policy
        for event_type in policy.event_types:
            self._policies_by_event_type[event_type].append(policy)

        logger.info(
            "Registered policy",
            extra={
                "policy_id": policy.id,
                "policy_name": policy.name,
                "event_types": [et.value for et in policy.event_types],
            },
        )

    def unregister_policy(self, policy_id: str) -> None:
        """Unregister a policy from the engine.

        Args:
            policy_id: The ID of the policy to unregister

        Raises:
            KeyError: If policy ID is not registered
        """
        if policy_id not in self._policies:
            raise KeyError(f"Policy '{policy_id}' is not registered")

        policy = self._policies.pop(policy_id)
        for event_type in policy.event_types:
            self._policies_by_event_type[event_type].remove(policy)

        logger.info(
            "Unregistered policy",
            extra={"policy_id": policy_id},
        )

    def add_decision_callback(self, callback: DecisionCallback) -> None:
        """Add a callback to be invoked for each decision.

        Callbacks receive the decision and event for logging,
        metrics, or other observability purposes.

        Args:
            callback: Function to call with (decision, event)
        """
        self._decision_callbacks.append(callback)

    def get_policies_for_event(
        self, event_type: PolicyEventType
    ) -> list[Policy]:
        """Get all policies that handle a given event type.

        Args:
            event_type: The event type to look up

        Returns:
            List of policies that handle this event type
        """
        return self._policies_by_event_type[event_type].copy()

    async def evaluate(self, event: PolicyEvent) -> AggregatedDecision:
        """Evaluate all applicable policies against an event.

        Policies are evaluated in registration order. Evaluation
        short-circuits on BLOCK decisions.

        Args:
            event: The event to evaluate

        Returns:
            AggregatedDecision with the combined result

        Raises:
            PolicyViolationError: If raise_on_block=True and BLOCK decision
            ConfirmationRequiredError: If raise_on_confirm=True and REQUIRE_CONFIRM
        """
        policies = self._policies_by_event_type.get(event.event_type, [])

        if not policies:
            # No policies for this event type - allow by default
            return AggregatedDecision(
                final_action=PolicyAction.ALLOW,
                decisions=[],
            )

        decisions: list[PolicyDecision] = []
        suggestions: list[PolicyDecision] = []
        blocking_decision: Optional[PolicyDecision] = None
        confirmation_decision: Optional[PolicyDecision] = None

        for policy in policies:
            try:
                decision = await policy.evaluate(event)
            except Exception as e:
                logger.error(
                    "Policy evaluation failed",
                    extra={
                        "policy_id": policy.id,
                        "event_id": event.event_id,
                        "error": str(e),
                    },
                )
                # Policy errors result in a BLOCK for safety
                decision = PolicyDecision.block(
                    policy_id=policy.id,
                    reason=f"Policy evaluation error: {e}",
                    severity=Severity.CRITICAL,
                    metadata={"error": str(e)},
                )

            decisions.append(decision)
            self._notify_callbacks(decision, event)

            # Handle decision by action type
            if decision.action == PolicyAction.BLOCK:
                blocking_decision = decision
                # Short-circuit on BLOCK
                break
            elif decision.action == PolicyAction.REQUIRE_CONFIRM:
                if confirmation_decision is None:
                    confirmation_decision = decision
            elif decision.action == PolicyAction.SUGGEST:
                suggestions.append(decision)

        # Determine final action (priority: BLOCK > REQUIRE_CONFIRM > SUGGEST > ALLOW)
        if blocking_decision:
            final_action = PolicyAction.BLOCK
        elif confirmation_decision:
            final_action = PolicyAction.REQUIRE_CONFIRM
        elif suggestions:
            final_action = PolicyAction.SUGGEST
        else:
            final_action = PolicyAction.ALLOW

        result = AggregatedDecision(
            final_action=final_action,
            decisions=decisions,
            blocking_decision=blocking_decision,
            confirmation_decision=confirmation_decision,
            suggestions=suggestions,
        )

        logger.debug(
            "Policy evaluation complete",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "final_action": final_action.value,
                "policy_count": len(policies),
                "decision_count": len(decisions),
            },
        )

        # Raise exceptions if configured
        if self._raise_on_block and result.is_blocked:
            assert blocking_decision is not None
            raise PolicyViolationError(blocking_decision, event)

        if self._raise_on_confirm and result.requires_confirmation:
            assert confirmation_decision is not None
            raise ConfirmationRequiredError(confirmation_decision, event)

        return result

    async def evaluate_many(
        self, events: list[PolicyEvent]
    ) -> list[AggregatedDecision]:
        """Evaluate multiple events concurrently.

        Args:
            events: List of events to evaluate

        Returns:
            List of AggregatedDecision results in same order
        """
        return await asyncio.gather(
            *[self.evaluate(event) for event in events]
        )

    def _notify_callbacks(
        self, decision: PolicyDecision, event: PolicyEvent
    ) -> None:
        """Notify all registered callbacks of a decision."""
        for callback in self._decision_callbacks:
            try:
                callback(decision, event)
            except Exception as e:
                logger.warning(
                    "Decision callback failed",
                    extra={"error": str(e)},
                )
