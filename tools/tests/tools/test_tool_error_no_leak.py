"""
Tests that MCP tool error responses never leak paths or exception text.

check: error["error"] must not contain:
- Resolved filesystem paths (e.g. /home/user/.hive/...)
- str(exception) or exception messages that may contain paths
"""

from __future__ import annotations

import os
import re
from unittest.mock import patch

import pytest
from fastmcp import FastMCP


@pytest.fixture
def mock_workspace():
    """Mock workspace, agent, and session IDs."""
    return {
        "workspace_id": "test-workspace",
        "agent_id": "test-agent",
        "session_id": "test-session",
    }


@pytest.fixture
def mock_secure_path(tmp_path):
    """Mock get_secure_path to return temp directory paths."""

    def _get_secure_path(path, workspace_id, agent_id, session_id):
        return os.path.join(tmp_path, path)

    with patch(
        "aden_tools.tools.file_system_toolkits.view_file.view_file.get_secure_path",
        side_effect=_get_secure_path,
    ):
        with patch(
            "aden_tools.tools.file_system_toolkits.list_dir.list_dir.get_secure_path",
            side_effect=_get_secure_path,
        ):
            with patch(
                "aden_tools.tools.file_system_toolkits.replace_file_content.replace_file_content.get_secure_path",
                side_effect=_get_secure_path,
            ):
                yield


# Patterns that must NOT appear in user-facing tool error messages
PATH_PATTERN = re.compile(
    r"(?:^|[\s/])"
    r"(?:/[\w.-]+)+"  # absolute path-like
    r"|"
    r"(?:\.\.?/[\w.-]+)+"  # relative with ..
    r"|"
    r"(?:[A-Za-z]:\\)[\w.\\-]+"  # Windows path
)
# Exception type names or traceback fragments that must never appear in user-facing errors
# (We do use generic "Permission denied" / "File not found" - those are OK)
LEAK_PATTERNS = (
    "FileNotFoundError",
    "PermissionError",
    "OSError",
    "IsADirectoryError",
    "NotADirectoryError",
    "No such file or directory",  # OSError message
    "errno",
    "Traceback",
    "  File \"",
    ".py\", line",
)


def _assert_error_sanitized(result: dict) -> None:
    """Assert result['error'] does not contain paths or exception leak."""
    assert "error" in result, "Expected error response"
    err = result["error"]
    assert isinstance(err, str), "error must be string"
    # No path-like substrings
    if PATH_PATTERN.search(err):
        raise AssertionError(f"Error message must not contain path-like content: {err!r}")
    # No exception type names or traceback fragments
    err_lower = err.lower()
    for bad in LEAK_PATTERNS:
        if bad.lower() in err_lower:
            raise AssertionError(f"Error message must not contain {bad!r}: {err!r}")


class TestViewFileErrorNoLeak:
    """view_file error responses must be sanitized."""

    @pytest.fixture
    def view_file_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.view_file import register_tools

        register_tools(mcp)
        return mcp._tool_manager._tools["view_file"].fn

    def test_nonexistent_file_error_sanitized(self, view_file_fn, mock_workspace, mock_secure_path):
        """Non-existent file returns generic error without path."""
        result = view_file_fn(path="nonexistent.txt", **mock_workspace)
        _assert_error_sanitized(result)
        assert "not found" in result["error"].lower()

    def test_exception_path_not_leaked(self, view_file_fn, mock_workspace, mock_secure_path, tmp_path):
        """When open() raises, response must not contain path or exception text."""
        (tmp_path / "dir_not_file").mkdir(exist_ok=True)
        # Pass a path that is a directory - open() will fail; response must be sanitized
        result = view_file_fn(path="dir_not_file", **mock_workspace)
        # Either "Path is not a file" (validation) or "Failed to read file" (exception)
        _assert_error_sanitized(result)
        assert "error" in result


class TestListDirErrorNoLeak:
    """list_dir error responses must be sanitized."""

    @pytest.fixture
    def list_dir_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.list_dir import register_tools

        register_tools(mcp)
        return mcp._tool_manager._tools["list_dir"].fn

    def test_nonexistent_dir_error_sanitized(self, list_dir_fn, mock_workspace, mock_secure_path):
        """Non-existent directory returns generic error without path."""
        result = list_dir_fn(path="nonexistent_dir", **mock_workspace)
        _assert_error_sanitized(result)
        assert "not found" in result["error"].lower() or "directory" in result["error"].lower()


class TestCsvToolErrorNoLeak:
    """CSV tool error responses must be sanitized."""

    @pytest.fixture
    def csv_tools(self, mcp, tmp_path):
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            from aden_tools.tools.csv_tool.csv_tool import register_tools

            register_tools(mcp)
            yield {
                "csv_read": mcp._tool_manager._tools["csv_read"].fn,
                "csv_sql": mcp._tool_manager._tools["csv_sql"].fn,
            }

    def test_csv_read_file_not_found_sanitized(self, csv_tools, tmp_path):
        """csv_read file not found must not contain path."""
        session_dir = tmp_path / "test-workspace" / "test-agent" / "test-session"
        session_dir.mkdir(parents=True)
        result = csv_tools["csv_read"](
            path="missing.csv",
            workspace_id="test-workspace",
            agent_id="test-agent",
            session_id="test-session",
        )
        _assert_error_sanitized(result)
        assert "not found" in result["error"].lower()

    def test_csv_sql_query_failed_sanitized(self, csv_tools, tmp_path):
        """csv_sql on invalid query must not leak exception text."""
        session_dir = tmp_path / "test-workspace" / "test-agent" / "test-session"
        session_dir.mkdir(parents=True)
        csv_file = session_dir / "data.csv"
        csv_file.write_text("a,b\n1,2\n")
        result = csv_tools["csv_sql"](
            path="data.csv",
            workspace_id="test-workspace",
            agent_id="test-agent",
            session_id="test-session",
            query="SELEKT * FORM data",  # typo to trigger DuckDB error
        )
        _assert_error_sanitized(result)
        assert "error" in result


class TestPdfReadErrorNoLeak:
    """pdf_read error responses must be sanitized."""

    @pytest.fixture
    def pdf_read_fn(self, mcp):
        from aden_tools.tools.pdf_read_tool import register_tools

        register_tools(mcp)
        return mcp._tool_manager._tools["pdf_read"].fn

    def test_pdf_file_not_found_sanitized(self, pdf_read_fn, tmp_path):
        """PDF not found must not contain file_path in error."""
        result = pdf_read_fn(file_path=str(tmp_path / "missing.pdf"))
        _assert_error_sanitized(result)
        assert "not found" in result["error"].lower()


class TestReplaceFileContentErrorNoLeak:
    """replace_file_content error responses must be sanitized."""

    @pytest.fixture
    def replace_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.replace_file_content import register_tools

        register_tools(mcp)
        return mcp._tool_manager._tools["replace_file_content"].fn

    def test_file_not_found_sanitized(self, replace_fn, mock_workspace, mock_secure_path):
        """File not found must not contain path."""
        result = replace_fn(
            path="nonexistent.txt",
            target="x",
            replacement="y",
            **mock_workspace,
        )
        _assert_error_sanitized(result)
        assert "not found" in result["error"].lower()
