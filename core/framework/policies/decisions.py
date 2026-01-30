"""Policy decision types for the guardrails system.

Decisions represent the outcome of policy evaluation. Each decision
indicates what action to take and provides context for that action.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid


class PolicyAction(Enum):
    """Actions that a policy can return."""

    ALLOW = "allow"
    """Proceed normally - no policy concerns."""

    SUGGEST = "suggest"
    """Proceed but attach guidance (e.g., prefer read-only tool)."""

    REQUIRE_CONFIRM = "require_confirm"
    """Pause execution for human-in-the-loop confirmation."""

    BLOCK = "block"
    """Stop execution with a structured exception."""


class Severity(Enum):
    """Severity levels for policy decisions."""

    LOW = "low"
    """Minor concern, informational."""

    MEDIUM = "medium"
    """Moderate concern, should be reviewed."""

    HIGH = "high"
    """Significant concern, requires attention."""

    CRITICAL = "critical"
    """Critical concern, immediate action required."""


@dataclass
class PolicyDecision:
    """The result of evaluating a policy against an event.

    A decision captures:
    - What action to take (allow, suggest, require_confirm, block)
    - Why this decision was made
    - Metadata for logging, auditing, and handling

    Attributes:
        action: The action to take
        reason: Human-readable explanation for the decision
        policy_id: Identifier of the policy that made this decision
        severity: How severe the concern is
        tags: Categorization tags for filtering/analysis
        suggested_patch: Optional modifications to make the action safe
        requires_human: Whether human review is required
        metadata: Additional context for logging/debugging
        decision_id: Unique identifier for this decision
        timestamp: When the decision was made
    """

    action: PolicyAction
    reason: str
    policy_id: str
    severity: Severity = Severity.MEDIUM
    tags: list[str] = field(default_factory=list)
    suggested_patch: Optional[dict[str, Any]] = None
    requires_human: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        """Set requires_human based on action if not explicitly set."""
        if self.action == PolicyAction.REQUIRE_CONFIRM:
            self.requires_human = True

    @classmethod
    def allow(
        cls,
        policy_id: str,
        reason: str = "No policy concerns",
        **kwargs: Any,
    ) -> "PolicyDecision":
        """Create an ALLOW decision.

        Args:
            policy_id: The policy making this decision
            reason: Why the action is allowed
            **kwargs: Additional decision attributes

        Returns:
            A PolicyDecision with ALLOW action
        """
        return cls(
            action=PolicyAction.ALLOW,
            reason=reason,
            policy_id=policy_id,
            severity=Severity.LOW,
            **kwargs,
        )

    @classmethod
    def suggest(
        cls,
        policy_id: str,
        reason: str,
        suggested_patch: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "PolicyDecision":
        """Create a SUGGEST decision.

        Args:
            policy_id: The policy making this decision
            reason: Why a suggestion is being made
            suggested_patch: Recommended modifications
            **kwargs: Additional decision attributes

        Returns:
            A PolicyDecision with SUGGEST action
        """
        return cls(
            action=PolicyAction.SUGGEST,
            reason=reason,
            policy_id=policy_id,
            severity=kwargs.pop("severity", Severity.LOW),
            suggested_patch=suggested_patch,
            **kwargs,
        )

    @classmethod
    def require_confirm(
        cls,
        policy_id: str,
        reason: str,
        severity: Severity = Severity.HIGH,
        **kwargs: Any,
    ) -> "PolicyDecision":
        """Create a REQUIRE_CONFIRM decision.

        Args:
            policy_id: The policy making this decision
            reason: Why confirmation is required
            severity: Severity level (default HIGH)
            **kwargs: Additional decision attributes

        Returns:
            A PolicyDecision with REQUIRE_CONFIRM action
        """
        return cls(
            action=PolicyAction.REQUIRE_CONFIRM,
            reason=reason,
            policy_id=policy_id,
            severity=severity,
            requires_human=True,
            **kwargs,
        )

    @classmethod
    def block(
        cls,
        policy_id: str,
        reason: str,
        severity: Severity = Severity.CRITICAL,
        **kwargs: Any,
    ) -> "PolicyDecision":
        """Create a BLOCK decision.

        Args:
            policy_id: The policy making this decision
            reason: Why the action is blocked
            severity: Severity level (default CRITICAL)
            **kwargs: Additional decision attributes

        Returns:
            A PolicyDecision with BLOCK action
        """
        return cls(
            action=PolicyAction.BLOCK,
            reason=reason,
            policy_id=policy_id,
            severity=severity,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the decision to a dictionary.

        Returns:
            Dictionary representation suitable for logging/storage
        """
        return {
            "decision_id": self.decision_id,
            "action": self.action.value,
            "reason": self.reason,
            "policy_id": self.policy_id,
            "severity": self.severity.value,
            "tags": self.tags,
            "suggested_patch": self.suggested_patch,
            "requires_human": self.requires_human,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
