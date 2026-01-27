import os
import pytest
from unittest.mock import MagicMock, patch
from framework.llm.litellm import LiteLLMProvider
from framework.llm.anthropic import AnthropicProvider

class TestStructuredOutputsOptimization:
    """Test optimized handling of JSON mode when response_format is provided."""

    @patch("litellm.completion")
    def test_json_mode_skip_prompt_if_format_exists(self, mock_completion):
        """Verify that JSON prompt instruction is skipped if response_format is provided."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_completion.return_value = mock_response

        provider = LiteLLMProvider(model="gpt-4o-mini", api_key="test-key")
        
        # Call with BOTH json_mode=True and a response_format
        provider.complete(
            messages=[{"role": "user", "content": "Return JSON"}],
            system="You are helpful.",
            json_mode=True,
            response_format={"type": "json_schema", "json_schema": {"name": "Test", "schema": {}}}
        )

        call_kwargs = mock_completion.call_args[1]
        assert "response_format" in call_kwargs
        
        messages = call_kwargs["messages"]
        system_msg = messages[0]["content"]
        
        # Key check: The legacy prompt instruction should NOT be present
        assert "Please respond with a valid JSON object" not in system_msg
        assert system_msg == "You are helpful."

    @patch("litellm.acompletion")
    @pytest.mark.asyncio
    async def test_streaming_json_mode_skip_prompt_if_format_exists(self, mock_acompletion):
        """Verify the same optimization for streaming."""
        
        # Mock async iterator for litellm.acompletion
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "{"
        mock_chunk.choices[0].finish_reason = None
        mock_chunk.model = "gpt-4o-mini"
        
        async def mock_stream():
            yield mock_chunk
            
        mock_acompletion.return_value = mock_stream()

        provider = LiteLLMProvider(model="gpt-4o-mini", api_key="test-key")
        
        # Call with BOTH json_mode=True and a response_format
        stream = provider.stream_complete(
            messages=[{"role": "user", "content": "Return JSON"}],
            system="You are helpful.",
            json_mode=True,
            response_format={"type": "json_schema", "json_schema": {"name": "Test", "schema": {}}}
        )

        # Collect one chunk to trigger the call
        async for _ in stream:
            break

        call_kwargs = mock_acompletion.call_args[1]
        assert "response_format" in call_kwargs
        
        messages = call_kwargs["messages"]
        system_msg = messages[0]["content"]
        
        # Key check: The legacy prompt instruction should NOT be present
        assert "Please respond with a valid JSON object" not in system_msg
        assert system_msg == "You are helpful."

if __name__ == "__main__":
    import asyncio
    pytest.main([__file__])
