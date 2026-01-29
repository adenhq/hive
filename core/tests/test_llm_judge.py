"""
Unit tests for the LLMJudge with configurable LLM provider.

Tests cover:
- Backward compatibility (no provider, uses Anthropic fallback)
- Custom LLM provider injection
- Response parsing (JSON, markdown, mixed text)
- Error handling and robustness
"""

from unittest.mock import MagicMock, patch

import pytest

from framework.llm.provider import LLMProvider, LLMResponse
from framework.testing.llm_judge import LLMJudge


# ============================================================================
# Mock LLM Provider
# ============================================================================


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response_content='{"passes": true, "explanation": "Test passed"}'):
        self.response_content = response_content
        self.complete_calls = []

    def complete(
        self,
        messages,
        system="",
        tools=None,
        max_tokens=1024,
        response_format=None,
        json_mode=False,
    ):
        self.complete_calls.append(
            {
                "messages": messages,
                "system": system,
                "max_tokens": max_tokens,
                "json_mode": json_mode,
            }
        )
        return LLMResponse(
            content=self.response_content,
            model="mock-model",
            input_tokens=100,
            output_tokens=50,
        )

    def complete_with_tools(self, *args, **kwargs):
        raise NotImplementedError("Tool use not supported for LLMJudge tests")


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def default_provider():
    return MockLLMProvider()


@pytest.fixture
def judge(default_provider):
    return LLMJudge(llm_provider=default_provider)


@pytest.fixture
def base_inputs():
    return {
        "constraint": "test-constraint",
        "source_document": "Source text",
        "summary": "Summary text",
        "criteria": "Test criteria",
    }


# ============================================================================
# Provider Injection Tests
# ============================================================================


def test_init_with_provider(default_provider):
    judge = LLMJudge(llm_provider=default_provider)
    assert judge._provider is default_provider
    assert judge._client is None


def test_evaluate_uses_provider(judge, base_inputs):
    result = judge.evaluate(**base_inputs)

    assert result["passes"] is True
    assert result["explanation"] == "Test passed"
    assert len(judge._provider.complete_calls) == 1


def test_evaluate_passes_correct_arguments(judge, base_inputs):
    judge.evaluate(**base_inputs)

    call = judge._provider.complete_calls[0]
    assert call["max_tokens"] == 500
    assert call["json_mode"] is True
    assert call["system"] == ""
    assert call["messages"][0]["role"] == "user"

    prompt = call["messages"][0]["content"]
    for value in base_inputs.values():
        assert value in prompt


# ============================================================================
# Response Parsing Tests
# ============================================================================


@pytest.mark.parametrize(
    "response, expected_passes, expected_text",
    [
        ('{"passes": true, "explanation": "OK"}', True, "OK"),
        ('```json\n{"passes": false, "explanation": "Failed"}\n```', False, "Failed"),
        ('```\n{"passes": true, "explanation": "Passed"}\n```', True, "Passed"),
        (
            'Here is the result:\n{"passes": true, "explanation": "Looks good"}\nThanks!',
            True,
            "Looks good",
        ),
    ],
)
def test_response_parsing_variants(response, expected_passes, expected_text, base_inputs):
    provider = MockLLMProvider(response_content=response)
    judge = LLMJudge(llm_provider=provider)

    result = judge.evaluate(**base_inputs)

    assert result["passes"] is expected_passes
    assert expected_text in result["explanation"]


def test_default_explanation_when_missing(base_inputs):
    provider = MockLLMProvider(response_content='{"passes": true}')
    judge = LLMJudge(llm_provider=provider)

    result = judge.evaluate(**base_inputs)

    assert result["passes"] is True
    assert result["explanation"] == "No explanation provided"


def test_passes_coerced_to_bool(base_inputs):
    provider = MockLLMProvider(response_content='{"passes": "yes"}')
    judge = LLMJudge(llm_provider=provider)

    result = judge.evaluate(**base_inputs)

    assert result["passes"] is True


def test_passes_false_when_missing(base_inputs):
    provider = MockLLMProvider(response_content='{"explanation": "Missing pass key"}')
    judge = LLMJudge(llm_provider=provider)

    result = judge.evaluate(**base_inputs)

    assert result["passes"] is False


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_invalid_json_response(base_inputs):
    provider = MockLLMProvider(response_content="This is not JSON")
    judge = LLMJudge(llm_provider=provider)

    result = judge.evaluate(**base_inputs)

    assert result["passes"] is False
    assert result["explanation"].startswith("LLM judge error")


def test_provider_exception_propagation(base_inputs):
    provider = MockLLMProvider()
    provider.complete = MagicMock(side_effect=RuntimeError("API failure"))

    judge = LLMJudge(llm_provider=provider)
    result = judge.evaluate(**base_inputs)

    assert result["passes"] is False
    assert "API failure" in result["explanation"]


# ============================================================================
# Backward Compatibility (Anthropic Fallback)
# ============================================================================


def test_init_without_provider():
    judge = LLMJudge()
    assert judge._provider is None
    assert judge._client is None


def test_anthropic_fallback(base_inputs):
    judge = LLMJudge()

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text='{"passes": true, "explanation": "Anthropic response"}')
    ]
    mock_client.messages.create.return_value = mock_response
    judge._get_client = MagicMock(return_value=mock_client)

    result = judge.evaluate(**base_inputs)

    assert result["passes"] is True
    assert result["explanation"] == "Anthropic response"
    mock_client.messages.create.assert_called_once()


def test_anthropic_import_error():
    judge = LLMJudge()

    with patch.dict("sys.modules", {"anthropic": None}):
        with patch("builtins.__import__", side_effect=ImportError):
            with pytest.raises(RuntimeError, match="anthropic package required"):
                judge._get_client()


# ============================================================================
# Integration Usage Patterns
# ============================================================================


def test_multiple_evaluations_reuse_provider(default_provider, base_inputs):
    judge = LLMJudge(llm_provider=default_provider)

    for _ in range(3):
        judge.evaluate(**base_inputs)

    assert len(default_provider.complete_calls) == 3
