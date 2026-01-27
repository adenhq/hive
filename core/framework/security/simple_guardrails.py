"""
Simple guardrail implementations.
"""
from typing import Optional, Any, List
from .guardrail import Guardrail, GuardrailResult, GuardrailAction

class KeywordGuardrail(Guardrail):
    """
    Blocks content containing specific forbidden keywords.
    Useful for preventing PII leakage (e.g., "password", "api_key") 
    or specific topic avoidance.
    """
    
    def __init__(self, forbidden_terms: List[str], name: str = "keyword-guardrail"):
        self._forbidden_terms = [term.lower() for term in forbidden_terms]
        self._name = name
        
    @property
    def name(self) -> str:
        return self._name
        
    def validate(self, content: str, context: Optional[dict[str, Any]] = None) -> GuardrailResult:
        content_lower = content.lower()
        
        for term in self._forbidden_terms:
            if term in content_lower:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=f"Content contains forbidden term: '{term}'"
                )
                
        return GuardrailResult(action=GuardrailAction.ALLOW)


class InputSizeGuardrail(Guardrail):
    """
    Prevents processing of excessively large inputs to avoid DoS or cost spikes.
    """
    
    def __init__(self, max_chars: int = 100000, name: str = "input-size-guardrail"):
        self.max_chars = max_chars
        self._name = name
        
    @property
    def name(self) -> str:
        return self._name
        
    def validate(self, content: str, context: Optional[dict[str, Any]] = None) -> GuardrailResult:
        if len(content) > self.max_chars:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"Input size ({len(content)}) exceeds maximum allowed ({self.max_chars})"
            )
            
        return GuardrailResult(action=GuardrailAction.ALLOW)
