import pytest
from framework.utils.json_parser import parse_json_from_text


class TestJsonParser:
    def test_standard_json(self):
        text = '{"key": "value", "num": 123}'
        parsed, cleaned = parse_json_from_text(text)
        assert parsed == {"key": "value", "num": 123}
        assert cleaned == text

    def test_markdown_json_block(self):
        text = 'Here is the result:\n```json\n{"key": "value"}\n```'
        parsed, cleaned = parse_json_from_text(text)
        assert parsed == {"key": "value"}
        assert '{"key": "value"}' in cleaned

    def test_markdown_no_lang_block(self):
        text = '```\n{"key": "value"}\n```'
        parsed, cleaned = parse_json_from_text(text)
        assert parsed == {"key": "value"}

    def test_python_syntax_booleans(self):
        # Case specific to Python stringification
        text = '{"valid": True, "invalid": False, "nothing": None}'
        parsed, cleaned = parse_json_from_text(text)
        assert parsed == {"valid": True, "invalid": False, "nothing": None}

    def test_single_quotes(self):
        # Case specific to Python dictionary string representation
        text = "{'key': 'value', 'nested': {'inner': 1}}"
        parsed, cleaned = parse_json_from_text(text)
        assert parsed == {"key": "value", "nested": {"inner": 1}}

    def test_embedded_json(self):
        text = 'Some prefix text {"key": "value"} some suffix text'
        parsed, cleaned = parse_json_from_text(text)
        assert parsed == {"key": "value"}
        assert '{"key": "value"}' in cleaned

    def test_malformed_json_fallback(self):
        # Truly broken JSON should return None
        text = '{"key": "value" broken'
        parsed, cleaned = parse_json_from_text(text)
        assert parsed is None

    def test_nested_brackets_trap(self):
        # Should not get confused by nested brackets
        text = '{"key": {"nested": "value"}}'
        parsed, cleaned = parse_json_from_text(text)
        assert parsed == {"key": {"nested": "value"}}

    def test_multiple_blocks_first_wins(self):
        # Logic is to take the first valid block
        text = '```json\n{"first": 1}\n```\n```json\n{"second": 2}\n```'
        parsed, cleaned = parse_json_from_text(text)
        assert parsed == {"first": 1}
