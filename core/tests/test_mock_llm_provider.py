"""Tests for MockLLMProvider streaming functionality."""

import asyncio
import pytest

from framework.llm.mock import MockLLMProvider
from framework.llm.provider import Tool, ToolResult, ToolUse
from framework.llm.stream_events import (
    FinishEvent,
    TextDeltaEvent,
    TextEndEvent,
)


class TestMockLLMProviderStreaming:
    """Tests for MockLLMProvider.stream() method."""

    @pytest.mark.asyncio
    async def test_stream_yields_text_delta_events(self):
        """Test that stream() yields TextDeltaEvents for each word."""
        provider = MockLLMProvider()

        events = []
        async for event in provider.stream(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful.",
        ):
            events.append(event)

        text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
        assert len(text_deltas) > 0, "Should yield at least one TextDeltaEvent"

    @pytest.mark.asyncio
    async def test_stream_yields_text_end_event(self):
        """Test that stream() yields a TextEndEvent at the end."""
        provider = MockLLMProvider()

        events = []
        async for event in provider.stream(
            messages=[{"role": "user", "content": "test"}],
        ):
            events.append(event)

        text_end_events = [e for e in events if isinstance(e, TextEndEvent)]
        assert len(text_end_events) == 1
        assert len(text_end_events[0].full_text) > 0

    @pytest.mark.asyncio
    async def test_stream_yields_finish_event(self):
        """Test that stream() yields a FinishEvent at the end."""
        provider = MockLLMProvider(model="test-model")

        events = []
        async for event in provider.stream(
            messages=[{"role": "user", "content": "test"}],
        ):
            events.append(event)

        finish_events = [e for e in events if isinstance(e, FinishEvent)]
        assert len(finish_events) == 1
        assert finish_events[0].stop_reason == "mock_complete"
        assert finish_events[0].model == "test-model"

    @pytest.mark.asyncio
    async def test_stream_accumulates_text_correctly(self):
        """Test that TextDeltaEvent snapshots accumulate correctly."""
        provider = MockLLMProvider()

        events = []
        async for event in provider.stream(
            messages=[{"role": "user", "content": "test"}],
        ):
            events.append(event)

        text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]

        if len(text_deltas) > 1:
            for i in range(1, len(text_deltas)):
                assert len(text_deltas[i].snapshot) > len(text_deltas[i - 1].snapshot)

    @pytest.mark.asyncio
    async def test_stream_with_tools_ignores_tools(self):
        """Test that stream() ignores tools in mock mode."""
        provider = MockLLMProvider()

        tools = [
            Tool(
                name="test_tool",
                description="A test tool",
                parameters={"properties": {"arg": {"type": "string"}}, "required": ["arg"]},
            )
        ]

        events = []
        async for event in provider.stream(
            messages=[{"role": "user", "content": "test"}],
            tools=tools,
        ):
            events.append(event)

        assert len(events) > 0
        text_end = [e for e in events if isinstance(e, TextEndEvent)]
        assert len(text_end) == 1

    @pytest.mark.asyncio
    async def test_stream_with_system_prompt(self):
        """Test that stream() uses system prompt for mock response."""
        provider = MockLLMProvider()

        events = []
        async for event in provider.stream(
            messages=[{"role": "user", "content": "test"}],
            system="You are a helpful assistant.",
        ):
            events.append(event)

        assert len(events) > 0


class TestMockLLMProviderComplete:
    """Tests for MockLLMProvider.complete() method."""

    def test_complete_returns_mock_response(self):
        """Test complete() returns a mock response."""
        provider = MockLLMProvider()

        response = provider.complete(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are helpful.",
        )

        assert response.content
        assert response.model == "mock-model"
        assert response.stop_reason == "mock_complete"
        assert response.input_tokens == 0
        assert response.output_tokens == 0

    def test_complete_json_mode_extracts_keys(self):
        """Test JSON mode extracts keys from system prompt."""
        provider = MockLLMProvider()

        response = provider.complete(
            messages=[{"role": "user", "content": "Generate data"}],
            system="output_keys: [name, email, age]",
            json_mode=True,
        )

        import json

        data = json.loads(response.content)
        assert "name" in data
        assert "email" in data
        assert "age" in data

    def test_complete_json_mode_with_keys_pattern(self):
        """Test JSON mode extracts keys from 'keys:' pattern."""
        provider = MockLLMProvider()

        response = provider.complete(
            messages=[{"role": "user", "content": "test"}],
            system="Generate JSON with keys: foo, bar",
            json_mode=True,
        )

        import json

        data = json.loads(response.content)
        assert "foo" in data
        assert "bar" in data

    def test_complete_json_mode_fallback(self):
        """Test JSON mode fallback when no keys found."""
        provider = MockLLMProvider()

        response = provider.complete(
            messages=[{"role": "user", "content": "test"}],
            system="Just respond",
            json_mode=True,
        )

        import json

        data = json.loads(response.content)
        assert "result" in data

    def test_complete_ignores_max_tokens(self):
        """Test that max_tokens is ignored in mock mode."""
        provider = MockLLMProvider()

        response = provider.complete(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10,
        )

        assert response.content


class TestMockLLMProviderCompleteWithTools:
    """Tests for MockLLMProvider.complete_with_tools() method."""

    def test_complete_with_tools_skips_tool_execution(self):
        """Test that tools are not executed in mock mode."""
        provider = MockLLMProvider()

        tools = [
            Tool(
                name="test_tool",
                description="Test",
                parameters={},
            )
        ]

        executed = []

        def tool_executor(tool_use: ToolUse) -> ToolResult:
            executed.append(tool_use.name)
            return ToolResult(tool_use_id=tool_use.id, content="result")

        response = provider.complete_with_tools(
            messages=[{"role": "user", "content": "test"}],
            system="Use the tool",
            tools=tools,
            tool_executor=tool_executor,
        )

        assert len(executed) == 0, "Tools should not be executed in mock mode"
        assert response.content

    def test_complete_with_tools_detects_json_in_system(self):
        """Test that JSON mode is auto-detected from system prompt."""
        provider = MockLLMProvider()

        tools = [Tool(name="t", description="Test", parameters={})]

        response = provider.complete_with_tools(
            messages=[{"role": "user", "content": "test"}],
            system="Return JSON output",
            tools=tools,
            tool_executor=lambda t: ToolResult(tool_use_id=t.id, content=""),
        )

        import json

        try:
            json.loads(response.content)
            is_json = True
        except json.JSONDecodeError:
            is_json = False

        assert is_json, "Should return JSON when system prompt mentions JSON"


class TestMockLLMProviderAsync:
    """Tests for MockLLMProvider async methods."""

    @pytest.mark.asyncio
    async def test_acomplete_returns_immediately(self):
        """Test acomplete() returns without blocking."""
        provider = MockLLMProvider()

        response = await provider.acomplete(
            messages=[{"role": "user", "content": "test"}],
        )

        assert response.content
        assert response.model == "mock-model"

    @pytest.mark.asyncio
    async def test_acomplete_with_tools_returns_immediately(self):
        """Test acomplete_with_tools() returns without blocking."""
        provider = MockLLMProvider()

        tools = [Tool(name="t", description="Test", parameters={})]

        response = await provider.acomplete_with_tools(
            messages=[{"role": "user", "content": "test"}],
            system="Test",
            tools=tools,
            tool_executor=lambda t: ToolResult(tool_use_id=t.id, content=""),
        )

        assert response.content

    @pytest.mark.asyncio
    async def test_async_methods_dont_block_event_loop(self):
        """Test that async methods don't block the event loop."""
        provider = MockLLMProvider()
        ticks = []

        async def heartbeat():
            for _ in range(5):
                ticks.append(1)
                await asyncio.sleep(0.01)

        async def run_complete():
            return await provider.acomplete(
                messages=[{"role": "user", "content": "test"}],
            )

        results = await asyncio.gather(heartbeat(), run_complete())

        assert len(ticks) == 5
        assert results[1].content


class TestMockLLMProviderExtractOutputKeys:
    """Tests for _extract_output_keys method."""

    def test_extract_output_keys_bracket_format(self):
        """Test extracting keys from 'output_keys: [key1, key2]' format."""
        provider = MockLLMProvider()

        keys = provider._extract_output_keys("output_keys: [name, email, phone]")

        assert keys == ["name", "email", "phone"]

    def test_extract_output_keys_quoted_values(self):
        """Test extracting quoted keys from bracket format."""
        provider = MockLLMProvider()

        keys = provider._extract_output_keys('output_keys: ["name", "email"]')

        assert keys == ["name", "email"]

    def test_extract_output_keys_with_keys_pattern(self):
        """Test extracting keys from 'keys: key1, key2' format."""
        provider = MockLLMProvider()

        keys = provider._extract_output_keys("Generate JSON with keys: foo, bar, baz")

        assert keys == ["foo", "bar", "baz"]

    def test_extract_output_keys_json_schema(self):
        """Test extracting keys from JSON schema in prompt."""
        provider = MockLLMProvider()

        keys = provider._extract_output_keys('Return JSON like: {"name": "", "age": 0}')

        assert "name" in keys
        assert "age" in keys

    def test_extract_output_keys_empty_when_no_pattern(self):
        """Test returns empty list when no pattern matches."""
        provider = MockLLMProvider()

        keys = provider._extract_output_keys("Just respond normally")

        assert keys == []
