from framework.graph.node import NodeResult
from framework.llm.provider import LLMProvider
from dataclasses import dataclass
from typing import Any

# Mock LLM Provider
class MockLLM(LLMProvider):
    def complete(self, messages, max_tokens=None, **kwargs):
        # Return a mock response object
        @dataclass
        class MockResponse:
            content: str
        return MockResponse(content="Mocked Summary of the Output")

    def complete_with_tools(self, messages, system, tools, tool_executor, max_iterations=10):
        # Not used by to_summary, but required by abstract base class
        pass

def test_summary_refactor():
    print("Testing NodeResult.to_summary refactor...")
    
    # 1. Create a NodeResult with some output
    result = NodeResult(
        success=True,
        output={"key1": "value1", "key2": "value2"},
        tokens_used=10,
        latency_ms=100
    )
    
    # 2. Test fallback (no provider) - Should mimic old key-value behavior (without Anthropic key)
    print("\n[Test 1] No LLM Provider (Fallback)")
    summary_fallback = result.to_summary()
    print(f"Summary: {summary_fallback}")
    assert "Completed with 2 outputs" in summary_fallback
    assert "key1" in summary_fallback
    
    # 3. Test with Mock Provider - Should use provider's complete method
    print("\n[Test 2] With Mock LLM Provider")
    mock_llm = MockLLM()
    summary_llm = result.to_summary(llm_provider=mock_llm)
    print(f"Summary: {summary_llm}")
    
    if "Mocked Summary" in summary_llm:
        print("[SUCCESS] Used LLM provider for summary!")
    else:
        print("[FAILURE] Did not use LLM provider.")
        return False

    return True

if __name__ == "__main__":
    if test_summary_refactor():
        print("\nAll tests passed!")
    else:
        print("\nTest failed.")
        exit(1)
