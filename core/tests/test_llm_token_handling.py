"""
Tests for LLM token exhaustion handling and error classification.

This test suite covers:
- Token limit error detection and conversion to TokenLimitExceeded
- Rate limit error classification
- Authentication error classification
- Model not found error classification
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from framework.llm.exceptions import (
    TokenLimitExceeded,
    RateLimitError,
    AuthenticationError,
    ModelNotFoundError,
)


@pytest.fixture
def mock_litellm():
    with patch("framework.llm.litellm.litellm") as mock:
        yield mock


@pytest.fixture
def provider(mock_litellm):
    """Create provider with mocked litellm."""
    from framework.llm.litellm import LiteLLMProvider
    return LiteLLMProvider(model="gpt-4o")


class TestTokenLimitDetection:
    """Test detection of token limit errors."""

    def test_context_length_exceeded(self, provider, mock_litellm):
        """Token limit error should raise TokenLimitExceeded."""
        mock_litellm.completion.side_effect = Exception(
            "Error code: 400 - context_length_exceeded"
        )

        with pytest.raises(TokenLimitExceeded) as exc_info:
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1024,
            )

        assert "Context length exceeded" in str(exc_info.value)
        assert exc_info.value.model == "gpt-4o"

    def test_max_tokens_exceeded(self, provider, mock_litellm):
        """Max tokens error should raise TokenLimitExceeded."""
        mock_litellm.completion.side_effect = Exception(
            "This request would exceed the max tokens"
        )

        with pytest.raises(TokenLimitExceeded):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1024,
            )

    def test_token_error_in_tool_use(self, provider, mock_litellm):
        """Token limit during tool use should raise TokenLimitExceeded."""
        mock_litellm.completion.side_effect = Exception(
            "context_length_exceeded"
        )

        with pytest.raises(TokenLimitExceeded):
            provider.complete_with_tools(
                messages=[{"role": "user", "content": "test"}],
                system="You are helpful",
                tools=[],
                tool_executor=lambda x: None,
            )

    def test_token_error_anthropic_model(self, mock_litellm):
        """Token error from Anthropic model."""
        from framework.llm.litellm import LiteLLMProvider
        provider = LiteLLMProvider(model="claude-3-sonnet")
        mock_litellm.completion.side_effect = Exception(
            "This model can process up to 200K tokens, but you requested more. context_length_exceeded"
        )

        with pytest.raises(TokenLimitExceeded):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )


class TestRateLimitDetection:
    """Test detection of rate limit errors."""

    def test_429_error(self, provider, mock_litellm):
        """429 status code should raise RateLimitError."""
        mock_litellm.completion.side_effect = Exception(
            "Error code: 429 - Rate limit exceeded"
        )

        with pytest.raises(RateLimitError):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )

    def test_rate_limit_string(self, provider, mock_litellm):
        """'rate_limit' in error should raise RateLimitError."""
        mock_litellm.completion.side_effect = Exception(
            "API rate_limit exceeded"
        )

        with pytest.raises(RateLimitError):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )


class TestAuthenticationDetection:
    """Test detection of authentication errors."""

    def test_401_error(self, provider, mock_litellm):
        """401 status code should raise AuthenticationError."""
        mock_litellm.completion.side_effect = Exception(
            "Error code: 401 - Unauthorized"
        )

        with pytest.raises(AuthenticationError):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )

    def test_authentication_string(self, provider, mock_litellm):
        """'authentication' in error should raise AuthenticationError."""
        mock_litellm.completion.side_effect = Exception(
            "Authentication required"
        )

        with pytest.raises(AuthenticationError):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )

    def test_unauthorized_string(self, provider, mock_litellm):
        """'unauthorized' in error should raise AuthenticationError."""
        mock_litellm.completion.side_effect = Exception(
            "API key is unauthorized"
        )

        with pytest.raises(AuthenticationError):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )


class TestModelNotFoundDetection:
    """Test detection of model not found errors."""

    def test_model_not_found(self, provider, mock_litellm):
        """'model not found' should raise ModelNotFoundError."""
        mock_litellm.completion.side_effect = Exception(
            "Model not found"
        )

        with pytest.raises(ModelNotFoundError):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )


class TestErrorMetadata:
    """Test exception metadata."""

    def test_token_error_stores_model(self, provider, mock_litellm):
        """TokenLimitExceeded should store model name."""
        mock_litellm.completion.side_effect = Exception(
            "context_length_exceeded"
        )

        with pytest.raises(TokenLimitExceeded) as exc_info:
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )

        assert exc_info.value.model == "gpt-4o"

    def test_error_message_includes_model(self, provider, mock_litellm):
        """Error message should include model name."""
        mock_litellm.completion.side_effect = Exception(
            "context_length_exceeded"
        )

        with pytest.raises(TokenLimitExceeded) as exc_info:
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )

        assert "gpt-4o" in str(exc_info.value)


class TestErrorDetectionWithSystemPrompt:
    """Test error handling with system prompts."""

    def test_token_error_with_system(self, provider, mock_litellm):
        """Token error with system prompt."""
        mock_litellm.completion.side_effect = Exception(
            "context_length_exceeded"
        )

        with pytest.raises(TokenLimitExceeded):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
                system="You are helpful",
                max_tokens=1024,
            )


class TestErrorDetectionWithTools:
    """Test error detection in tool-use loops."""

    def test_rate_limit_in_tool_loop(self, provider, mock_litellm):
        """Rate limit during tool use."""
        mock_litellm.completion.side_effect = Exception(
            "429 rate_limit_exceeded"
        )

        with pytest.raises(RateLimitError):
            provider.complete_with_tools(
                messages=[{"role": "user", "content": "test"}],
                system="You are helpful",
                tools=[],
                tool_executor=lambda x: None,
            )

    def test_auth_error_in_tool_loop(self, provider, mock_litellm):
        """Auth error during tool use."""
        mock_litellm.completion.side_effect = Exception(
            "401 unauthorized"
        )

        with pytest.raises(AuthenticationError):
            provider.complete_with_tools(
                messages=[{"role": "user", "content": "test"}],
                system="You are helpful",
                tools=[],
                tool_executor=lambda x: None,
            )


class TestErrorDetectionWithJsonMode:
    """Test error detection with JSON mode."""

    def test_token_error_json_mode(self, provider, mock_litellm):
        """Token error with JSON mode."""
        mock_litellm.completion.side_effect = Exception(
            "context_length_exceeded"
        )

        with pytest.raises(TokenLimitExceeded):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
                json_mode=True,
                max_tokens=512,
            )


class TestUnknownErrors:
    """Test handling of unknown errors."""

    def test_generic_error_re_raised(self, provider, mock_litellm):
        """Generic errors that don't match patterns are re-raised."""
        mock_litellm.completion.side_effect = ValueError(
            "Some unknown error"
        )

        with pytest.raises(ValueError):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )

    def test_error_with_special_characters(self, provider, mock_litellm):
        """Errors with special characters."""
        mock_litellm.completion.side_effect = Exception(
            "context_length_exceeded: [{'error': 'max tokens'}]"
        )

        with pytest.raises(TokenLimitExceeded):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )


class TestCaseInsensitiveMatching:
    """Test that error detection is case-insensitive."""

    def test_uppercase_context_length(self, provider, mock_litellm):
        """Case-insensitive detection of CONTEXT_LENGTH_EXCEEDED."""
        mock_litellm.completion.side_effect = Exception(
            "CONTEXT_LENGTH_EXCEEDED"
        )

        with pytest.raises(TokenLimitExceeded):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )

    def test_uppercase_rate_limit(self, provider, mock_litellm):
        """Case-insensitive detection of RATE_LIMIT."""
        mock_litellm.completion.side_effect = Exception(
            "RATE_LIMIT exceeded"
        )

        with pytest.raises(RateLimitError):
            provider.complete(
                messages=[{"role": "user", "content": "test"}],
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
