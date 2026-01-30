"""Exceptions for the guardrails system.

Structured exceptions allow the runtime to handle policy violations
deterministically (retry, escalate to HITL, degrade model, etc.).
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from framework.policies.decisions import PolicyDecision
    from framework.policies.events import PolicyEvent


class GuardrailsError(Exception):
    """Base exception for all guardrails errors."""

    pass


class PolicyViolationError(GuardrailsError):
    """Raised when a policy blocks an action.

    This exception carries the full context of the violation,
    allowing the runtime to:
    - Log the violation with full details
    - Escalate to human-in-the-loop if configured
    - Retry with modified parameters
    - Degrade to a safer model/approach

    Attributes:
        decision: The PolicyDecision that caused the block
        event: The PolicyEvent that was evaluated
        message: Human-readable error message

    Example:
        try:
            await engine.evaluate(event)
        except PolicyViolationError as e:
            logger.error(
                "Policy violation",
                policy_id=e.decision.policy_id,
                reason=e.decision.reason,
                event_type=e.event.event_type.value,
            )
            if e.decision.requires_human:
                await escalate_to_human(e)
    """

    def __init__(
        self,
        decision: "PolicyDecision",
        event: "PolicyEvent",
        message: Optional[str] = None,
    ) -> None:
        """Initialize the PolicyViolationError.

        Args:
            decision: The decision that blocked the action
            event: The event that was evaluated
            message: Optional custom message (defaults to decision reason)
        """
        self.decision = decision
        self.event = event
        super().__init__(message or decision.reason)

    def to_dict(self) -> dict:
        """Serialize the error for logging/storage.

        Returns:
            Dictionary with decision and event details
        """
        return {
            "error_type": "PolicyViolationError",
            "message": str(self),
            "decision": self.decision.to_dict(),
            "event": self.event.to_dict(),
        }


class PolicyConfigurationError(GuardrailsError):
    """Raised when a policy is misconfigured.

    This can happen when:
    - Required configuration is missing
    - Configuration values are invalid
    - Policy dependencies are not met
    """

    pass


class PolicyRegistrationError(GuardrailsError):
    """Raised when policy registration fails.

    This can happen when:
    - A policy with the same ID is already registered
    - The policy doesn't implement the required interface
    - The policy's event types are invalid
    """

    pass


class ConfirmationRequiredError(GuardrailsError):
    """Raised when human confirmation is required to proceed.

    This is a non-blocking indication that the action requires
    human approval before continuing. The runtime should pause
    and request confirmation.

    Attributes:
        decision: The PolicyDecision requiring confirmation
        event: The PolicyEvent that was evaluated
    """

    def __init__(
        self,
        decision: "PolicyDecision",
        event: "PolicyEvent",
        message: Optional[str] = None,
    ) -> None:
        """Initialize the ConfirmationRequiredError.

        Args:
            decision: The decision requiring confirmation
            event: The event that was evaluated
            message: Optional custom message
        """
        self.decision = decision
        self.event = event
        super().__init__(
            message or f"Confirmation required: {decision.reason}"
        )

    def to_dict(self) -> dict:
        """Serialize the error for logging/storage.

        Returns:
            Dictionary with decision and event details
        """
        return {
            "error_type": "ConfirmationRequiredError",
            "message": str(self),
            "decision": self.decision.to_dict(),
            "event": self.event.to_dict(),
        }
