"""Tests for LiteLLM retry logic with transient errors."""

import pytest
from unittest.mock import patch, MagicMock
import litellm

from framework.llm.litellm import LiteLLMProvider, TRANSIENT_EXCEPTIONS


class TestLiteLLMRetry:
    """Test retry behavior for transient LLM errors."""

    def test_retries_on_rate_limit_error(self):
        """Should retry on rate limit errors."""
        provider = LiteLLMProvider(model="gpt-4o-mini", api_key="test-key")
        
        call_count = 0
        
        def mock_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise litellm.RateLimitError(
                    message="Rate limit exceeded",
                    llm_provider="openai",
                    model="gpt-4o-mini",
                )
            # Succeed on 3rd attempt
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Success"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.model = "gpt-4o-mini"
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            return mock_response
        
        with patch.object(litellm, 'completion', side_effect=mock_completion):
            result = provider.complete(
                messages=[{"role": "user", "content": "Hello"}],
            )
        
        assert call_count == 3
        assert result.content == "Success"

    def test_retries_on_timeout_error(self):
        """Should retry on timeout errors."""
        provider = LiteLLMProvider(model="gpt-4o-mini", api_key="test-key")
        
        call_count = 0
        
        def mock_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise litellm.Timeout(
                    message="Request timed out",
                    llm_provider="openai",
                    model="gpt-4o-mini",
                )
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Success"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.model = "gpt-4o-mini"
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            return mock_response
        
        with patch.object(litellm, 'completion', side_effect=mock_completion):
            result = provider.complete(
                messages=[{"role": "user", "content": "Hello"}],
            )
        
        assert call_count == 2
        assert result.content == "Success"

    def test_retries_on_connection_error(self):
        """Should retry on connection errors."""
        provider = LiteLLMProvider(model="gpt-4o-mini", api_key="test-key")
        
        call_count = 0
        
        def mock_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise litellm.APIConnectionError(
                    message="Connection failed",
                    llm_provider="openai",
                    model="gpt-4o-mini",
                )
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Success"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.model = "gpt-4o-mini"
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            return mock_response
        
        with patch.object(litellm, 'completion', side_effect=mock_completion):
            result = provider.complete(
                messages=[{"role": "user", "content": "Hello"}],
            )
        
        assert call_count == 2
        assert result.content == "Success"

    def test_does_not_retry_on_auth_error(self):
        """Should NOT retry on authentication errors (permanent)."""
        provider = LiteLLMProvider(model="gpt-4o-mini", api_key="invalid-key")
        
        call_count = 0
        
        def mock_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            raise litellm.AuthenticationError(
                message="Invalid API key",
                llm_provider="openai",
                model="gpt-4o-mini",
            )
        
        with patch.object(litellm, 'completion', side_effect=mock_completion):
            with pytest.raises(litellm.AuthenticationError):
                provider.complete(
                    messages=[{"role": "user", "content": "Hello"}],
                )
        
        # Should only try once - no retry on auth errors
        assert call_count == 1

    def test_gives_up_after_max_retries(self):
        """Should give up after 3 attempts."""
        provider = LiteLLMProvider(model="gpt-4o-mini", api_key="test-key")
        
        call_count = 0
        
        def mock_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            raise litellm.RateLimitError(
                message="Rate limit exceeded",
                llm_provider="openai",
                model="gpt-4o-mini",
            )
        
        with patch.object(litellm, 'completion', side_effect=mock_completion):
            with pytest.raises(litellm.RateLimitError):
                provider.complete(
                    messages=[{"role": "user", "content": "Hello"}],
                )
        
        # Should try 3 times then give up
        assert call_count == 3

    def test_transient_exceptions_tuple_defined(self):
        """Verify TRANSIENT_EXCEPTIONS contains expected error types."""
        assert litellm.RateLimitError in TRANSIENT_EXCEPTIONS
        assert litellm.Timeout in TRANSIENT_EXCEPTIONS
        assert litellm.APIConnectionError in TRANSIENT_EXCEPTIONS
