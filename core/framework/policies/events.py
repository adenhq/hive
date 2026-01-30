"""Policy event types for the guardrails system.

Events represent actions that policies evaluate. Each event captures
the context needed to make a policy decision.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid


class PolicyEventType(Enum):
    """Types of events that policies can evaluate."""

    LLM_REQUEST = "llm_request"
    """Before an LLM call - evaluate prompt, context, sensitive data."""

    LLM_RESPONSE = "llm_response"
    """After an LLM call - evaluate output for unsafe intent, data exfil."""

    TOOL_CALL = "tool_call"
    """Before a tool call - evaluate tool name, args, permissions."""

    TOOL_RESULT = "tool_result"
    """After a tool call - evaluate output for injection, provenance."""

    SIDE_EFFECT = "side_effect"
    """Before external side effects - send, write, mutate, post."""

    RUN_CONTROL = "run_control"
    """Runtime control events - budget, retry loops, execution limits."""


@dataclass
class PolicyEvent:
    """An event submitted to the policy engine for evaluation.

    Events are the primary input to policies. Each event captures:
    - What type of action is being attempted
    - Context about the execution (IDs, timing)
    - Payload with action-specific details

    Attributes:
        event_type: The category of event (tool call, LLM request, etc.)
        timestamp: ISO-formatted timestamp of when the event occurred
        execution_id: Unique identifier for the current execution/run
        payload: Event-specific data (tool name, args, etc.)
        stream_id: Optional identifier for the agent stream
        correlation_id: Optional ID for tracking related events
        event_id: Unique identifier for this specific event
    """

    event_type: PolicyEventType
    timestamp: str
    execution_id: str
    payload: dict[str, Any]
    stream_id: Optional[str] = None
    correlation_id: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def create(
        cls,
        event_type: PolicyEventType,
        payload: dict[str, Any],
        execution_id: str,
        stream_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> "PolicyEvent":
        """Factory method to create an event with automatic timestamp.

        Args:
            event_type: The type of event
            payload: Event-specific data
            execution_id: The current execution ID
            stream_id: Optional stream identifier
            correlation_id: Optional correlation ID

        Returns:
            A new PolicyEvent instance
        """
        return cls(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_id=execution_id,
            payload=payload,
            stream_id=stream_id,
            correlation_id=correlation_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a dictionary.

        Returns:
            Dictionary representation suitable for logging/storage
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "execution_id": self.execution_id,
            "stream_id": self.stream_id,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        }
