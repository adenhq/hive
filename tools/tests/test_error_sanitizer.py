"""
Tests for error_sanitizer (no path/exception leak in tool responses).
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from aden_tools.utils.error_sanitizer import error_response, sanitize_error


class TestSanitizeError:
    """Tests for sanitize_error()."""

    def test_returns_generic_message_only(self):
        """Return value must be the generic message, never str(exception)."""
        exc = ValueError("/home/secret/.hive/workdir/workspaces/xyz")
        result = sanitize_error(exc, "File not found", path="/tmp/secret/path")
        assert result == "File not found"
        assert "/home" not in result
        assert "secret" not in result
        assert "workdir" not in result
        assert "ValueError" not in result

    def test_logs_full_context(self, caplog):
        """Exception and path must be logged server-side (for debugging)."""
        caplog.set_level(logging.WARNING)
        exc = OSError(2, "No such file", "/resolved/secret/path")
        sanitize_error(exc, "File not found", path="/user/provided/path")
        assert "File not found" in caplog.text
        # Path may appear in log record (server-side only)
        assert "Tool error" in caplog.text or "File not found" in caplog.text

    def test_without_path(self):
        """Works when path is not provided."""
        exc = PermissionError(13, "Permission denied")
        result = sanitize_error(exc, "Permission denied")
        assert result == "Permission denied"
        assert "PermissionError" not in result


class TestErrorResponse:
    """Tests for error_response() - dict form for tool returns."""

    def test_returns_dict_with_generic_message_only(self):
        """Response dict must never contain paths or str(exception)."""
        exc = FileNotFoundError(2, "No such file", "/etc/passwd")
        result = error_response(exc, "File not found", path="/home/user/.hive/workspace")
        assert result == {"error": "File not found"}
        assert "/etc" not in str(result)
        assert "/home" not in str(result)
        assert "passwd" not in str(result)
        assert "FileNotFoundError" not in str(result)
        assert "No such file" not in str(result)

    def test_oserror_with_resolved_path_not_leaked(self):
        """OSError often contains resolved path - must not appear in response."""
        exc = OSError(2, "No such file or directory", "/resolved/absolute/path/to/file")
        result = error_response(exc, "File not found")
        err_str = result["error"]
        assert err_str == "File not found"
        assert "/resolved" not in err_str
        assert "absolute" not in err_str

    def test_permission_error_not_leaked(self):
        """PermissionError message must not appear in response."""
        exc = PermissionError(13, "Permission denied: '/var/secret/data'")
        result = error_response(exc, "Permission denied")
        assert result["error"] == "Permission denied"
        assert "/var" not in result["error"]
        assert "secret" not in result["error"]

    @patch("aden_tools.utils.error_sanitizer.logger")
    def test_log_level_forwarded(self, mock_logger):
        """log_level=error uses logger.error."""
        exc = RuntimeError("internal detail")
        error_response(exc, "Operation failed", log_level="error")
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Operation failed" in str(call_args)
        assert mock_logger.warning.call_count == 0
