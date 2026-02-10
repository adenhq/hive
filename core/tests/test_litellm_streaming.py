
import pytest
from unittest.mock import MagicMock, patch
from framework.llm.litellm import LiteLLMProvider
from framework.llm.stream_events import (
    TextDeltaEvent,
    TextEndEvent,
    ToolCallEvent,
    FinishEvent,
    StreamErrorEvent
)

# Helper to create mock chunks
def MockChunk(
    delta_content=None,
    tool_calls=None,
    finish_reason=None,
    input_tokens=0,
    output_tokens=0,
):
    chunk = MagicMock()
    chunk.choices = [MagicMock()]

    # Delta content
    chunk.choices[0].delta.content = delta_content

    # Delta tool calls
    if tool_calls is not None:
        chunk.choices[0].delta.tool_calls = tool_calls
    else:
        chunk.choices[0].delta.tool_calls = None

    # Finish reason
    chunk.choices[0].finish_reason = finish_reason

    # Usage
    if finish_reason:
        chunk.usage.prompt_tokens = input_tokens
        chunk.usage.completion_tokens = output_tokens
    else:
        if hasattr(chunk, "usage"):
            del chunk.usage

    return chunk

def MockToolCall(index=0, id=None, name=None, args=None):
    tc = MagicMock()
    tc.index = index
    tc.id = id
    tc.function.name = name
    tc.function.arguments = args
    return tc

async def async_iter(items):
    for item in items:
        yield item

class TestLiteLLMStreaming:

    @pytest.mark.asyncio
    async def test_text_streaming(self):
        """Text chunks yield TextDeltaEvent sequence with correct snapshots."""
        mock_chunks = [
            MockChunk(delta_content="Hello"),
            MockChunk(delta_content=" world"),
            MockChunk(finish_reason="stop", input_tokens=10, output_tokens=5),
        ]

        with patch("litellm.acompletion", return_value=async_iter(mock_chunks)):
            provider = LiteLLMProvider(model="gpt-4")
            events = []
            async for e in provider.stream(
                messages=[{"role": "user", "content": "Hi"}]
            ):
                events.append(e)

        # Check event sequence
        assert len(events) == 4

        # 1. TextDeltaEvent "Hello"
        assert isinstance(events[0], TextDeltaEvent)
        assert events[0].content == "Hello"
        assert events[0].snapshot == "Hello"

        # 2. TextDeltaEvent " world"
        assert isinstance(events[1], TextDeltaEvent)
        assert events[1].content == " world"
        assert events[1].snapshot == "Hello world"

        # 3. TextEndEvent
        assert isinstance(events[2], TextEndEvent)
        assert events[2].full_text == "Hello world"

        # 4. FinishEvent
        assert isinstance(events[3], FinishEvent)
        assert events[3].stop_reason == "stop"
        assert events[3].input_tokens == 10
        assert events[3].output_tokens == 5

    @pytest.mark.asyncio
    async def test_tool_call_accumulation(self):
        """Partial tool call JSON is accumulated into single ToolCallEvent."""
        mock_chunks = [
            # Chunk 1: "call_1", function name "search", arg start '{"qu'
            MockChunk(tool_calls=[MockToolCall(id="call_1", name="search", args='{"qu')]),
            # Chunk 2: arg mid 'ery":'
            MockChunk(tool_calls=[MockToolCall(id=None, name=None, args='ery":')]),
            # Chunk 3: arg end ' "test"}'
            MockChunk(tool_calls=[MockToolCall(id=None, name=None, args=' "test"}')]),
            # Chunk 4: finish
            MockChunk(finish_reason="tool_calls", input_tokens=20, output_tokens=10),
        ]

        with patch("litellm.acompletion", return_value=async_iter(mock_chunks)):
            provider = LiteLLMProvider(model="gpt-4")
            events = []
            async for e in provider.stream(
                messages=[{"role": "user", "content": "Search for test"}]
            ):
                events.append(e)

        assert len(events) == 2

        # 1. ToolCallEvent
        assert isinstance(events[0], ToolCallEvent)
        assert events[0].tool_use_id == "call_1"
        assert events[0].tool_name == "search"
        assert events[0].tool_input == {"query": "test"}

        # 2. FinishEvent
        assert isinstance(events[1], FinishEvent)
        assert events[1].stop_reason == "tool_calls"
        assert events[1].input_tokens == 20
        assert events[1].output_tokens == 10

    @pytest.mark.asyncio
    async def test_error_yields_stream_error_event(self):
        """Exception during streaming yields StreamErrorEvent."""
        async def failing_stream():
            yield MockChunk(delta_content="Part")
            raise ConnectionError("Connection reset")

        with patch("litellm.acompletion", return_value=failing_stream()):
            provider = LiteLLMProvider(model="gpt-4")
            events = []
            async for e in provider.stream(
                messages=[{"role": "user", "content": "Hi"}]
            ):
                events.append(e)

        assert len(events) == 2

        # 1. Partial TextDeltaEvent
        assert isinstance(events[0], TextDeltaEvent)
        assert events[0].content == "Part"
        assert events[0].snapshot == "Part"

        # 2. StreamErrorEvent
        assert isinstance(events[1], StreamErrorEvent)
        assert "Connection reset" in events[1].error
        assert events[1].recoverable is False
