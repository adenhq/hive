"""
Tests for OutputValidator nullable_keys functionality.

Verifies that optional output keys can be None without failing validation
when specified in the nullable_keys parameter.
"""

from framework.graph.validator import OutputValidator


class TestValidateOutputKeysNullableKeys:
    """Tests for nullable_keys parameter in validate_output_keys."""

    def setup_method(self):
        self.validator = OutputValidator()

    def test_none_value_fails_without_nullable_keys(self):
        """None values should fail validation when nullable_keys is not specified."""
        output = {"name": "test", "description": None}
        expected_keys = ["name", "description"]

        result = self.validator.validate_output_keys(output, expected_keys)

        assert result.success is False
        assert "Output key 'description' is None" in result.errors

    def test_none_value_passes_with_nullable_keys(self):
        """None values should pass validation when key is in nullable_keys."""
        output = {"name": "test", "description": None}
        expected_keys = ["name", "description"]
        nullable_keys = ["description"]

        result = self.validator.validate_output_keys(
            output, expected_keys, nullable_keys=nullable_keys
        )

        assert result.success is True
        assert result.errors == []

    def test_multiple_nullable_keys(self):
        """Multiple keys can be nullable."""
        output = {"name": "test", "description": None, "clarification_reason": None}
        expected_keys = ["name", "description", "clarification_reason"]
        nullable_keys = ["description", "clarification_reason"]

        result = self.validator.validate_output_keys(
            output, expected_keys, nullable_keys=nullable_keys
        )

        assert result.success is True
        assert result.errors == []

    def test_missing_key_still_fails_even_if_nullable(self):
        """Missing keys should still fail validation even if they are nullable."""
        output = {"name": "test"}
        expected_keys = ["name", "description"]
        nullable_keys = ["description"]

        result = self.validator.validate_output_keys(
            output, expected_keys, nullable_keys=nullable_keys
        )

        assert result.success is False
        assert "Missing required output key: 'description'" in result.errors

    def test_non_nullable_key_with_none_still_fails(self):
        """Non-nullable keys with None values should still fail."""
        output = {"name": None, "description": None}
        expected_keys = ["name", "description"]
        nullable_keys = ["description"]

        result = self.validator.validate_output_keys(
            output, expected_keys, nullable_keys=nullable_keys
        )

        assert result.success is False
        assert "Output key 'name' is None" in result.errors
        assert "Output key 'description' is None" not in result.errors

    def test_empty_nullable_keys_list(self):
        """Empty nullable_keys list should behave like no nullable_keys."""
        output = {"name": "test", "description": None}
        expected_keys = ["name", "description"]
        nullable_keys = []

        result = self.validator.validate_output_keys(
            output, expected_keys, nullable_keys=nullable_keys
        )

        assert result.success is False
        assert "Output key 'description' is None" in result.errors


class TestValidateAllNullableKeys:
    """Tests for nullable_keys parameter in validate_all."""

    def setup_method(self):
        self.validator = OutputValidator()

    def test_validate_all_passes_nullable_keys(self):
        """validate_all should pass nullable_keys to validate_output_keys."""
        output = {"name": "test", "optional_field": None}
        expected_keys = ["name", "optional_field"]
        nullable_keys = ["optional_field"]

        result = self.validator.validate_all(
            output,
            expected_keys=expected_keys,
            nullable_keys=nullable_keys,
            check_hallucination=False,
        )

        assert result.success is True
        assert result.errors == []

    def test_validate_all_fails_without_nullable_keys(self):
        """validate_all should fail for None values when nullable_keys not specified."""
        output = {"name": "test", "optional_field": None}
        expected_keys = ["name", "optional_field"]

        result = self.validator.validate_all(
            output,
            expected_keys=expected_keys,
            check_hallucination=False,
        )

        assert result.success is False
        assert "Output key 'optional_field' is None" in result.errors
