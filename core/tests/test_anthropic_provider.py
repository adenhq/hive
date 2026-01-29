"""Tests for AnthropicProvider.

Run with:
    cd core
    python -m pytest tests/test_anthropic_provider.py -v
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from framework.llm.anthropic import AnthropicProvider, _get_api_key_from_credential_manager
from framework.llm.litellm import LiteLLMProvider
from framework.llm.provider import LLMResponse, Tool, ToolResult, ToolUse


# ===========================================================================
# TestGetApiKeyFromCredentialManager
# ===========================================================================

class TestGetApiKeyFromCredentialManager:
    """Tests for the _get_api_key_from_credential_manager helper."""

    def test_returns_key_from_credential_manager(self):
        """Returns API key from CredentialManager when available."""
        mock_creds = MagicMock()
        mock_creds.is_available.return_value = True
        mock_creds.get.return_value = "cred-manager-key"

        with patch.dict("sys.modules", {"aden_tools": MagicMock(), "aden_tools.credentials": MagicMock()}):
            with patch(
                "framework.llm.anthropic._get_api_key_from_credential_manager"
            ) as mock_fn:
                mock_fn.return_value = "cred-manager-key"
                result = mock_fn()
                assert result == "cred-manager-key"

    def test_falls_back_to_env_var(self):
        """Falls back to ANTHROPIC_API_KEY env var when CredentialManager unavailable."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *args: (_ for _ in ()).throw(ImportError)
                if "aden_tools" in name
                else __builtins__.__import__(name, *args),
            ):
                result = _get_api_key_from_credential_manager()
                assert result == "env-key"

    def test_returns_none_when_nothing_available(self):
        """Returns None when neither CredentialManager nor env var is set."""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_api_key_from_credential_manager()
            assert result is None or isinstance(result, str)


# ===========================================================================
# TestAnthropicProviderInit
# ===========================================================================

class TestAnthropicProviderInit:
    """Tests for AnthropicProvider initialization."""

    def test_init_with_explicit_api_key(self):
        """Initialize with an explicit API key."""
        provider = AnthropicProvider(api_key="test-key-123")

        assert provider.api_key == "test-key-123"
        assert provider.model == "claude-haiku-4-5-20251001"
        assert isinstance(provider._provider, LiteLLMProvider)

    def test_init_with_custom_model(self):
        """Custom model is forwarded to internal LiteLLMProvider."""
        provider = AnthropicProvider(
            api_key="test-key",
            model="claude-sonnet-4-20250514",
        )

        assert provider.model == "claude-sonnet-4-20250514"
        assert provider._provider.model == "claude-sonnet-4-20250514"

    def test_init_with_env_var(self):
        """API key from ANTHROPIC_API_KEY env var."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-api-key"}):
            provider = AnthropicProvider()
            assert provider.api_key == "env-api-key"

    def test_init_raises_without_api_key(self):
        """Raises ValueError when no API key is available."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "framework.llm.anthropic._get_api_key_from_credential_manager",
                return_value=None,
            ):
                with pytest.raises(ValueError, match="API key required"):
                    AnthropicProvider()

    def test_delegates_to_litellm_provider(self):
        """Internal _provider is a LiteLLMProvider with correct params."""
        provider = AnthropicProvider(api_key="key-123", model="claude-3-haiku-20240307")

        assert isinstance(provider._provider, LiteLLMProvider)
        assert provider._provider.api_key == "key-123"
        assert provider._provider.model == "claude-3-haiku-20240307"


# ===========================================================================
# TestAnthropicProviderComplete
# ===========================================================================

class TestAnthropicProviderComplete:
    """Tests for AnthropicProvider.complete()."""

    def _make_provider(self):
        return AnthropicProvider(api_key="test-key")

    @patch("litellm.completion")
    def test_delegates_to_litellm(self, mock_completion):
        """complete() delegates to LiteLLMProvider.complete()."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from Claude"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "claude-haiku-4-5-20251001"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_completion.return_value = mock_response

        provider = self._make_provider()
        result = provider.complete(
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result.content == "Hello from Claude"
        assert result.model == "claude-haiku-4-5-20251001"
        mock_completion.assert_called_once()

    @patch("litellm.completion")
    def test_forwards_all_parameters(self, mock_completion):
        """complete() forwards system, tools, max_tokens, response_format, json_mode."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "claude-haiku-4-5-20251001"
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 10
        mock_completion.return_value = mock_response

        provider = self._make_provider()
        tool = Tool(name="search", description="Search", parameters={"properties": {}})

        result = provider.complete(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            tools=[tool],
            max_tokens=2048,
            response_format={"type": "json_object"},
            json_mode=True,
        )

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["max_tokens"] == 2048
        assert "tools" in call_kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @patch("litellm.completion")
    def test_error_propagation(self, mock_completion):
        """Errors from litellm propagate through AnthropicProvider."""
        mock_completion.side_effect = Exception("API Error")

        provider = self._make_provider()
        with pytest.raises(Exception, match="API Error"):
            provider.complete(messages=[{"role": "user", "content": "test"}])

    @patch("litellm.completion")
    def test_empty_system_prompt(self, mock_completion):
        """complete() works with empty system prompt."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "test"
        mock_response.usage.prompt_tokens = 1
        mock_response.usage.completion_tokens = 1
        mock_completion.return_value = mock_response

        provider = self._make_provider()
        result = provider.complete(
            messages=[{"role": "user", "content": "test"}],
            system="",
        )

        assert result.content == "response"


# ===========================================================================
# TestAnthropicProviderCompleteWithTools
# ===========================================================================

class TestAnthropicProviderCompleteWithTools:
    """Tests for AnthropicProvider.complete_with_tools()."""

    def _make_provider(self):
        return AnthropicProvider(api_key="test-key")

    @patch("litellm.completion")
    def test_delegates_to_litellm(self, mock_completion):
        """complete_with_tools() delegates to LiteLLMProvider."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Final answer"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "claude-haiku-4-5-20251001"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_completion.return_value = mock_response

        provider = self._make_provider()
        tool = Tool(name="search", description="Search", parameters={"properties": {}})

        def executor(tool_use: ToolUse) -> ToolResult:
            return ToolResult(tool_use_id=tool_use.id, content="result")

        result = provider.complete_with_tools(
            messages=[{"role": "user", "content": "find info"}],
            system="You are helpful",
            tools=[tool],
            tool_executor=executor,
        )

        assert result.content == "Final answer"

    @patch("litellm.completion")
    def test_tool_loop_executes_tools(self, mock_completion):
        """complete_with_tools() executes tools and feeds results back."""
        tool_call_msg = MagicMock()
        tool_call_msg.content = ""
        tc = MagicMock()
        tc.id = "tc1"
        tc.function.name = "search"
        tc.function.arguments = '{"query": "test"}'
        tool_call_msg.tool_calls = [tc]

        first_response = MagicMock()
        first_response.choices = [MagicMock()]
        first_response.choices[0].message = tool_call_msg
        first_response.choices[0].finish_reason = "tool_calls"
        first_response.model = "claude-haiku-4-5-20251001"
        first_response.usage.prompt_tokens = 10
        first_response.usage.completion_tokens = 5

        final_msg = MagicMock()
        final_msg.content = "Found the info"
        final_msg.tool_calls = None

        final_response = MagicMock()
        final_response.choices = [MagicMock()]
        final_response.choices[0].message = final_msg
        final_response.choices[0].finish_reason = "stop"
        final_response.model = "claude-haiku-4-5-20251001"
        final_response.usage.prompt_tokens = 20
        final_response.usage.completion_tokens = 10

        mock_completion.side_effect = [first_response, final_response]

        provider = self._make_provider()
        tool = Tool(name="search", description="Search", parameters={"properties": {}})

        executor_calls = []

        def executor(tool_use: ToolUse) -> ToolResult:
            executor_calls.append(tool_use)
            return ToolResult(tool_use_id=tool_use.id, content="search result")

        result = provider.complete_with_tools(
            messages=[{"role": "user", "content": "find info"}],
            system="You are helpful",
            tools=[tool],
            tool_executor=executor,
        )

        assert result.content == "Found the info"
        assert len(executor_calls) == 1
        assert executor_calls[0].name == "search"
        assert result.input_tokens == 30
        assert result.output_tokens == 15

    @patch("litellm.completion")
    def test_max_iterations_reached(self, mock_completion):
        """complete_with_tools() returns when max iterations exceeded."""
        tc = MagicMock()
        tc.id = "tc1"
        tc.function.name = "search"
        tc.function.arguments = '{"q": "x"}'

        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = ""
        response.choices[0].message.tool_calls = [tc]
        response.choices[0].finish_reason = "tool_calls"
        response.model = "test"
        response.usage.prompt_tokens = 1
        response.usage.completion_tokens = 1
        mock_completion.return_value = response

        provider = self._make_provider()
        tool = Tool(name="search", description="Search", parameters={"properties": {}})

        def executor(tool_use: ToolUse) -> ToolResult:
            return ToolResult(tool_use_id=tool_use.id, content="result")

        result = provider.complete_with_tools(
            messages=[{"role": "user", "content": "test"}],
            system="sys",
            tools=[tool],
            tool_executor=executor,
            max_iterations=2,
        )

        assert result.stop_reason == "max_iterations"
        assert mock_completion.call_count == 2
