"""
Unit tests for Security Guardrails.
"""
import pytest
from ..simple_guardrails import KeywordGuardrail
from ..guarded_provider import GuardedLLMProvider, GuardrailException

# Mock classes to avoid importing full framework
class MockResponse:
    def __init__(self, content):
        self.content = content

class MockProvider:
    def complete(self, messages, **kwargs):
        # Return a response based on input for testing output guardrails
        if "politics" in messages[0]["content"]:
            return MockResponse("Politics is the subject.")
        return MockResponse("Safe response.")

    def complete_with_tools(self, *args, **kwargs):
        pass

def test_keyword_guardrail_blocks_forbidden_term():
    guardrail = KeywordGuardrail(forbidden_terms=["badword"], name="test-guardrail")
    result = guardrail.validate("This string contains a badword.")
    assert result.is_blocked
    assert "badword" in result.reason

def test_keyword_guardrail_allows_safe_content():
    guardrail = KeywordGuardrail(forbidden_terms=["badword"], name="test-guardrail")
    result = guardrail.validate("This string is clean.")
    assert not result.is_blocked

def test_guarded_provider_blocks_input():
    provider = MockProvider()
    guardrail = KeywordGuardrail(forbidden_terms=["secret"], name="input-checker")
    guarded = GuardedLLMProvider(base_provider=provider, input_guardrails=[guardrail])
    
    with pytest.raises(GuardrailException) as excinfo:
        guarded.complete(messages=[{"role": "user", "content": "My secret is 123"}])
    
    assert "secret" in str(excinfo.value)

def test_guarded_provider_blocks_output():
    provider = MockProvider()
    guardrail = KeywordGuardrail(forbidden_terms=["Politics"], name="output-checker")
    guarded = GuardedLLMProvider(base_provider=provider, output_guardrails=[guardrail])
    
    # Provider mock returns "Politics..." when input contains "politics"
    with pytest.raises(GuardrailException) as excinfo:
        guarded.complete(messages=[{"role": "user", "content": "Tell me about politics"}])
        
    assert "Politics" in str(excinfo.value)
