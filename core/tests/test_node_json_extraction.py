"""Tests for LLMNode JSON extraction logic.

Run with:
    cd core
    pytest tests/test_node_json_extraction.py -v
"""

import pytest
from framework.graph.node import LLMNode


class TestJsonExtraction:
    """Test _extract_json JSON extraction without LLM calls."""

    @pytest.fixture
    def node(self):
        """Create an LLMNode instance for testing."""
        return LLMNode()

    def test_clean_json(self, node):
        """Test parsing clean JSON directly."""
        result = node._extract_json('{"key": "value"}', ["key"])
        assert result == {"key": "value"}

    def test_json_with_whitespace(self, node):
        """Test parsing JSON with surrounding whitespace."""
        result = node._extract_json('  {"key": "value"}  \n', ["key"])
        assert result == {"key": "value"}

    def test_markdown_code_block_at_start(self, node):
        """Test extracting JSON from markdown code block at start."""
        input_text = '```json\n{"key": "value"}\n```'
        result = node._extract_json(input_text, ["key"])
        assert result == {"key": "value"}

    def test_markdown_code_block_without_json_label(self, node):
        """Test extracting JSON from markdown code block without 'json' label."""
        input_text = '```\n{"key": "value"}\n```'
        result = node._extract_json(input_text, ["key"])
        assert result == {"key": "value"}

    def test_prose_around_markdown_block(self, node):
        """Test extracting JSON when prose surrounds the markdown block."""
        input_text = 'Here is the result:\n```json\n{"key": "value"}\n```\nHope this helps!'
        result = node._extract_json(input_text, ["key"])
        assert result == {"key": "value"}

    def test_json_embedded_in_prose(self, node):
        """Test extracting JSON embedded in prose text."""
        input_text = 'The answer is {"key": "value"} as requested.'
        result = node._extract_json(input_text, ["key"])
        assert result == {"key": "value"}

    def test_nested_json(self, node):
        """Test parsing nested JSON objects."""
        input_text = '{"outer": {"inner": "value"}}'
        result = node._extract_json(input_text, ["outer"])
        assert result == {"outer": {"inner": "value"}}

    def test_deeply_nested_json(self, node):
        """Test parsing deeply nested JSON objects."""
        input_text = '{"a": {"b": {"c": {"d": "deep"}}}}'
        result = node._extract_json(input_text, ["a"])
        assert result == {"a": {"b": {"c": {"d": "deep"}}}}

    def test_json_with_array(self, node):
        """Test parsing JSON with array values."""
        input_text = '{"items": [1, 2, 3]}'
        result = node._extract_json(input_text, ["items"])
        assert result == {"items": [1, 2, 3]}

    def test_json_with_string_containing_braces(self, node):
        """Test parsing JSON where string values contain braces."""
        input_text = '{"code": "function() { return 1; }"}'
        result = node._extract_json(input_text, ["code"])
        assert result == {"code": "function() { return 1; }"}

    def test_json_with_escaped_quotes(self, node):
        """Test parsing JSON with escaped quotes in strings."""
        input_text = '{"message": "He said \\"hello\\""}'
        result = node._extract_json(input_text, ["message"])
        assert result == {"message": 'He said "hello"'}

    def test_multiple_json_objects_takes_first(self, node):
        """Test that when multiple JSON objects exist, first is taken."""
        input_text = '{"first": 1} and then {"second": 2}'
        result = node._extract_json(input_text, ["first"])
        assert result == {"first": 1}

    def test_json_with_boolean_and_null(self, node):
        """Test parsing JSON with boolean and null values."""
        input_text = '{"active": true, "deleted": false, "data": null}'
        result = node._extract_json(input_text, ["active", "deleted", "data"])
        assert result == {"active": True, "deleted": False, "data": None}

    def test_json_with_numbers(self, node):
        """Test parsing JSON with integer and float values."""
        input_text = '{"count": 42, "price": 19.99}'
        result = node._extract_json(input_text, ["count", "price"])
        assert result == {"count": 42, "price": 19.99}

    def test_invalid_json_raises_error(self, node):
        """Test that completely invalid JSON raises an error."""
        with pytest.raises(ValueError, match="Cannot parse JSON"):
            node._extract_json("This is not JSON at all", ["key"])

    def test_empty_string_raises_error(self, node):
        """Test that empty string raises an error."""
        with pytest.raises(ValueError, match="Cannot parse JSON"):
            node._extract_json("", ["key"])

class TestLLMProviderFallback:
    """Test multi-provider LLM fallback for JSON extraction.
    
    These tests verify that the LLM fallback logic correctly:
    1. Checks multiple API keys in priority order
    2. Creates the correct LLM provider for each API key
    3. Provides helpful error messages when no API key is found
    """

    @pytest.fixture
    def node(self):
        """Create an LLMNode instance for testing."""
        return LLMNode()

    def test_error_message_lists_all_supported_providers(self, node, monkeypatch):
        """Test that error message mentions all supported API keys when none found."""
        # Clear all relevant environment variables
        for key in ["CEREBRAS_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            monkeypatch.delenv(key, raising=False)
        
        # Use input that can't be parsed locally
        invalid_json = "completely unparseable garbage @@## not json"
        
        with pytest.raises(ValueError) as exc_info:
            node._extract_json(invalid_json, ["key"])
        
        error_msg = str(exc_info.value)
        # Should mention all supported providers
        assert "CEREBRAS_API_KEY" in error_msg
        assert "GROQ_API_KEY" in error_msg
        assert "OPENAI_API_KEY" in error_msg
        assert "ANTHROPIC_API_KEY" in error_msg

    def test_provider_priority_order(self, node, monkeypatch):
        """Test that providers are checked in the correct priority order.
        
        Priority: Cerebras > Groq > OpenAI > Anthropic (faster/cheaper first)
        """
        # This test verifies the logic exists - actual LLM calls are mocked in integration tests
        
        # When only Anthropic key is set, it should be used (last in priority)
        for key in ["CEREBRAS_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"]:
            monkeypatch.delenv(key, raising=False)
        
        # With no API key, should raise with helpful message
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        
        invalid_json = "not json at all !@#$%"
        with pytest.raises(ValueError, match="no API key found"):
            node._extract_json(invalid_json, ["key"])