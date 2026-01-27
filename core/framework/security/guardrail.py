"""
Base Guardrail protocol for the Aden Security System.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any


class GuardrailAction(Enum):
    """Action to take when a guardrail triggers."""
    ALLOW = "allow"     # Allow the content to pass
    FLAG = "flag"       # Allow but mark as suspicious
    BLOCK = "block"     # Block the content entirely
    MODIFY = "modify"   # Modify the content (sanitization)


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    action: GuardrailAction
    reason: Optional[str] = None
    modified_content: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @property
    def is_blocked(self) -> bool:
        return self.action == GuardrailAction.BLOCK


class Guardrail(ABC):
    """
    Abstract base class for all security guardrails.
    
    Guardrails can run on:
    - Inputs (before sending to LLM)
    - Outputs (before returning to Agent)
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the guardrail."""
        pass

    @abstractmethod
    def validate(self, content: str, context: Optional[dict[str, Any]] = None) -> GuardrailResult:
        """
        Validate the content against the guardrail.
        
        Args:
            content: The text content to check (prompt or response).
            context: Optional context (e.g., user_id, agent_id).
            
        Returns:
            GuardrailResult indicating the action to take.
        """
        pass
