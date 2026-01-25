"""
Tests for execution error model and classification.

Tests cover:
- ExecutionErrorType enum
- ExecutionError creation and properties
- Exception classification
- Error retriability logic
"""

import pytest
from framework.graph.execution_errors import (
    ExecutionError,
    ExecutionErrorType,
    is_retriable,
    classify_exception,
    create_execution_error,
    from_exception,
)


class TestExecutionErrorType:
    """Tests for ExecutionErrorType enum."""

    def test_retriable_types(self):
        """Test that retriable types are correctly identified."""
        assert is_retriable(ExecutionErrorType.RETRIABLE_TRANSIENT) is True
        assert is_retriable(ExecutionErrorType.RETRIABLE_VALIDATION) is True

    def test_fatal_types(self):
        """Test that fatal types are correctly identified."""
        assert is_retriable(ExecutionErrorType.FATAL_CONFIGURATION) is False
        assert is_retriable(ExecutionErrorType.FATAL_SECURITY) is False
        assert is_retriable(ExecutionErrorType.FATAL_EXCEPTION) is False


class TestExecutionError:
    """Tests for ExecutionError class."""

    def test_creation(self):
        """Test creating an ExecutionError."""
        error = ExecutionError(
            error_type=ExecutionErrorType.RETRIABLE_TRANSIENT,
            message="Rate limit exceeded",
            source="test",
        )
        assert error.error_type == ExecutionErrorType.RETRIABLE_TRANSIENT
        assert error.message == "Rate limit exceeded"
        assert error.source == "test"
        assert error.retriable is True

    def test_retriable_property(self):
        """Test retriable property."""
        retriable_error = ExecutionError(
            error_type=ExecutionErrorType.RETRIABLE_TRANSIENT,
            message="Timeout",
        )
        assert retriable_error.retriable is True

        fatal_error = ExecutionError(
            error_type=ExecutionErrorType.FATAL_CONFIGURATION,
            message="Missing tool",
        )
        assert fatal_error.retriable is False

    def test_str_representation(self):
        """Test string representation."""
        error = ExecutionError(
            error_type=ExecutionErrorType.RETRIABLE_TRANSIENT,
            message="Connection timeout",
            source="worker_node",
        )
        error_str = str(error)
        assert "retriable_transient" in error_str
        assert "worker_node" in error_str
        assert "Connection timeout" in error_str

    def test_to_dict(self):
        """Test dictionary serialization."""
        error = ExecutionError(
            error_type=ExecutionErrorType.FATAL_SECURITY,
            message="Permission denied",
            source="sandbox",
            details={"file": "/etc/passwd"},
        )
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "fatal_security"
        assert error_dict["message"] == "Permission denied"
        assert error_dict["source"] == "sandbox"
        assert error_dict["retriable"] is False
        assert error_dict["details"]["file"] == "/etc/passwd"


class TestClassifyException:
    """Tests for exception classification."""

    def test_timeout_error(self):
        """Test that timeout errors are classified as retriable transient."""
        error_type = classify_exception(TimeoutError("Connection timeout"))
        assert error_type == ExecutionErrorType.RETRIABLE_TRANSIENT

    def test_rate_limit_error(self):
        """Test that rate limit errors are classified as retriable transient."""
        error = Exception("Rate limit exceeded, please retry")
        error_type = classify_exception(error)
        assert error_type == ExecutionErrorType.RETRIABLE_TRANSIENT

    def test_network_error(self):
        """Test that network errors are classified as retriable transient."""
        error = Exception("Connection refused")
        error_type = classify_exception(error)
        assert error_type == ExecutionErrorType.RETRIABLE_TRANSIENT

    def test_validation_error(self):
        """Test that validation errors are classified as retriable validation."""
        error = ValueError("Invalid input format")
        error_type = classify_exception(error)
        assert error_type == ExecutionErrorType.RETRIABLE_VALIDATION

    def test_json_decode_error(self):
        """Test that JSON errors are classified as retriable validation."""
        error = Exception("JSON decode error: unexpected token")
        error_type = classify_exception(error)
        assert error_type == ExecutionErrorType.RETRIABLE_VALIDATION

    def test_configuration_error(self):
        """Test that configuration errors are classified as fatal."""
        error = Exception("Tool 'send_email' not found")
        error_type = classify_exception(error)
        assert error_type == ExecutionErrorType.FATAL_CONFIGURATION

    def test_permission_error(self):
        """Test that permission errors are classified as fatal security."""
        error = PermissionError("Access denied")
        error_type = classify_exception(error)
        assert error_type == ExecutionErrorType.FATAL_SECURITY

    def test_import_error(self):
        """Test that import errors are classified as fatal configuration."""
        error = ImportError("No module named 'foo'")
        error_type = classify_exception(error)
        assert error_type == ExecutionErrorType.FATAL_CONFIGURATION

    def test_generic_exception(self):
        """Test that generic exceptions are classified as fatal."""
        error = Exception("Something went wrong")
        error_type = classify_exception(error)
        assert error_type == ExecutionErrorType.FATAL_EXCEPTION


class TestCreateExecutionError:
    """Tests for create_execution_error helper."""

    def test_create_with_enum(self):
        """Test creating error with enum type."""
        error = create_execution_error(
            ExecutionErrorType.RETRIABLE_TRANSIENT,
            "Timeout",
            source="test",
        )
        assert error.error_type == ExecutionErrorType.RETRIABLE_TRANSIENT
        assert error.message == "Timeout"

    def test_create_with_string(self):
        """Test creating error with string type."""
        error = create_execution_error(
            "retriable_transient",
            "Timeout",
            source="test",
        )
        assert error.error_type == ExecutionErrorType.RETRIABLE_TRANSIENT

    def test_create_with_details(self):
        """Test creating error with details."""
        error = create_execution_error(
            ExecutionErrorType.FATAL_CONFIGURATION,
            "Missing tool",
            details={"tool_name": "send_email"},
        )
        assert error.details["tool_name"] == "send_email"

    def test_create_with_exception(self):
        """Test creating error with original exception."""
        original = ValueError("Bad value")
        error = create_execution_error(
            ExecutionErrorType.RETRIABLE_VALIDATION,
            "Validation failed",
            exception=original,
        )
        assert error.original_exception is original


class TestFromException:
    """Tests for from_exception helper."""

    def test_from_timeout(self):
        """Test creating error from timeout exception."""
        exception = TimeoutError("Connection timeout")
        error = from_exception(exception, source="worker")
        assert error.error_type == ExecutionErrorType.RETRIABLE_TRANSIENT
        assert error.message == "Connection timeout"
        assert error.source == "worker"
        assert error.original_exception is exception

    def test_from_value_error(self):
        """Test creating error from value error."""
        exception = ValueError("Invalid format")
        error = from_exception(exception)
        assert error.error_type == ExecutionErrorType.RETRIABLE_VALIDATION
        assert error.retriable is True

    def test_from_permission_error(self):
        """Test creating error from permission error."""
        exception = PermissionError("Access denied")
        error = from_exception(exception)
        assert error.error_type == ExecutionErrorType.FATAL_SECURITY
        assert error.retriable is False

    def test_with_details(self):
        """Test creating error with additional details."""
        exception = Exception("Tool not found")
        error = from_exception(
            exception,
            source="worker",
            details={"tool_name": "missing_tool"},
        )
        assert error.details["tool_name"] == "missing_tool"


class TestErrorRetriability:
    """Integration tests for error retriability logic."""

    def test_retriable_errors_should_retry(self):
        """Test that retriable errors are marked for retry."""
        errors = [
            create_execution_error(
                ExecutionErrorType.RETRIABLE_TRANSIENT,
                "Rate limit",
            ),
            create_execution_error(
                ExecutionErrorType.RETRIABLE_VALIDATION,
                "Invalid format",
            ),
        ]
        for error in errors:
            assert error.retriable is True

    def test_fatal_errors_should_not_retry(self):
        """Test that fatal errors are not marked for retry."""
        errors = [
            create_execution_error(
                ExecutionErrorType.FATAL_CONFIGURATION,
                "Missing tool",
            ),
            create_execution_error(
                ExecutionErrorType.FATAL_SECURITY,
                "Permission denied",
            ),
            create_execution_error(
                ExecutionErrorType.FATAL_EXCEPTION,
                "Unexpected error",
            ),
        ]
        for error in errors:
            assert error.retriable is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
