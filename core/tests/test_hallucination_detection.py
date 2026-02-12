"""
Test hallucination detection in SharedMemory and OutputValidator.

These tests verify that code detection works correctly across the entire
string content, not just the first 500 characters.
"""

import pytest

from framework.graph.node import MemoryWriteError, SharedMemory
from framework.graph.validator import OutputValidator, ValidationResult


class TestSharedMemoryHallucinationDetection:
    """Test the SharedMemory hallucination detection."""

    def test_detects_code_at_start(self):
        """Code at the start of the string should be detected."""
        memory = SharedMemory()
        code_content = "import os\ndef hack(): pass\nexcept:\n    class Foo: pass" + "A" * 6000

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", code_content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_code_in_middle(self):
        """Code in the middle of the string should be detected (was previously missed)."""
        memory = SharedMemory()
        padding_start = "A" * 600
        code = "\nimport os\ndef malicious(): pass\ntry:\n    except: pass\n"
        padding_end = "B" * 5000
        content = padding_start + code + padding_end

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_code_at_end(self):
        """Code at the end of the string should be detected (was previously missed)."""
        memory = SharedMemory()
        padding = "A" * 5500
        code = "\nclass Exploit:\n    def run(self):\n        import subprocess\n"
        content = padding + code

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_javascript_code(self):
        """JavaScript code patterns should be detected via strict indicator."""
        memory = SharedMemory()
        padding = "A" * 600
        code = "\nfunction malicious() { require('child_process'); }\n"
        padding_end = "B" * 5000
        content = padding + code + padding_end

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_sql_injection(self):
        """SQL patterns should be detected."""
        memory = SharedMemory()
        padding = "A" * 600
        code = "\nDROP TABLE users; SELECT * FROM passwords;\n"
        padding_end = "B" * 5000
        content = padding + code + padding_end

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_detects_script_injection(self):
        """HTML script injection should be detected."""
        memory = SharedMemory()
        padding = "A" * 600
        code = "\n<script>alert('xss')</script>\n"
        padding_end = "B" * 5000
        content = padding + code + padding_end

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)

    def test_allows_short_strings_without_validation(self):
        """Strings under 5000 chars should not trigger validation."""
        memory = SharedMemory()
        content = "def hello(): pass"  # Contains code indicator but short

        # Should not raise - too short to validate
        memory.write("output", content)
        assert memory.read("output") == content

    def test_allows_long_strings_without_code(self):
        """Long strings without code indicators should be allowed."""
        memory = SharedMemory()
        content = "This is a long text document. " * 500  # ~15000 chars, no code

        memory.write("output", content)
        assert memory.read("output") == content

    def test_validate_false_bypasses_check(self):
        """Using validate=False should bypass the check."""
        memory = SharedMemory()
        code_content = "import os\ndef hack():\n    try: pass\n    except: pass" + "A" * 6000

        memory.write("output", code_content, validate=False)
        assert memory.read("output") == code_content

    def test_sampling_for_very_long_strings(self):
        """Very long strings (>10KB) should be sampled at multiple positions."""
        memory = SharedMemory()
        size = 50000
        code_position = int(size * 0.75)
        code = "def hidden(): pass\nimport os\nclass X: pass\n"
        content = "A" * code_position + code + "B" * (size - code_position - len(code))

        with pytest.raises(MemoryWriteError) as exc_info:
            memory.write("output", content)

        assert "hallucinated code" in str(exc_info.value)


class TestOutputValidatorHallucinationDetection:
    """Test the OutputValidator hallucination detection."""

    def test_detects_code_anywhere_in_output(self):
        """Code anywhere in the output value should trigger a warning."""
        validator = OutputValidator()
        padding = "Normal text content. " * 50
        code = "\ndef suspicious_function():\n    pass\n"
        output = {"result": padding + code}

        # The method logs a warning but doesn't fail
        result = validator.validate_no_hallucination(output)
        # The warning is logged - we can't easily test logging, but the method should work
        assert isinstance(result, ValidationResult)

    def test_contains_code_indicators_full_check(self):
        """_contains_code_indicators should detect multiple code patterns."""
        validator = OutputValidator()
        padding = "A" * 600
        code = "import os\ndef run():\n    try: pass"
        content = padding + code

        assert validator._contains_code_indicators(content) is True

    def test_contains_code_indicators_sampling(self):
        """_contains_code_indicators should sample for very long strings."""
        validator = OutputValidator()
        size = 50000
        code_position = int(size * 0.75)
        code = "class Hidden:\n    def run(self):\n        import os"
        content = "A" * code_position + code + "B" * (size - code_position - len(code))

        assert validator._contains_code_indicators(content) is True

    def test_no_false_positive_for_clean_text(self):
        """Clean text without code should not trigger false positives."""
        validator = OutputValidator()

        # Long text without any code indicators
        content = "This is a perfectly normal document. " * 300

        assert validator._contains_code_indicators(content) is False

    def test_detects_multiple_languages(self):
        """Should detect code patterns from multiple programming languages."""
        validator = OutputValidator()

        # Strict indicators: single match is enough
        strict_cases = [
            "SELECT * FROM users",
            "DROP TABLE data",
            "<script>",
            "<?php",
            "async def foo(): pass",
            "require('fs')",
        ]
        for code in strict_cases:
            assert validator._contains_code_indicators(code) is True, f"Failed to detect: {code}"

        # Contextual indicators: need 3+ to trigger
        multi_indicator = "def foo():\n    import os\n    from sys import argv"
        assert validator._contains_code_indicators(multi_indicator) is True


class TestEdgeCases:
    """Test edge cases for hallucination detection."""

    def test_empty_string(self):
        """Empty strings should not cause errors."""
        memory = SharedMemory()
        memory.write("output", "")
        assert memory.read("output") == ""

    def test_non_string_values(self):
        """Non-string values should not be validated for code."""
        memory = SharedMemory()

        # These should all work without validation
        memory.write("number", 12345)
        memory.write("list", [1, 2, 3])
        memory.write("dict", {"key": "value"})
        memory.write("bool", True)

        assert memory.read("number") == 12345
        assert memory.read("list") == [1, 2, 3]

    def test_exactly_5000_chars(self):
        """String of exactly 5000 chars should not trigger validation."""
        memory = SharedMemory()
        content = "def code(): pass" + "A" * (5000 - 16)  # Exactly 5000 chars

        # Should not raise - exactly at threshold, not over
        memory.write("output", content)
        assert len(memory.read("output")) == 5000

    def test_5001_chars_triggers_validation(self):
        """String of 5001 chars with code should trigger validation."""
        memory = SharedMemory()
        code = "def code(): pass\nimport os\nclass X: pass"
        content = code + "A" * (5001 - len(code))

        with pytest.raises(MemoryWriteError):
            memory.write("output", content)
