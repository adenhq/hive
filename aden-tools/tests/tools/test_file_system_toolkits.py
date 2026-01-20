"""Tests for file_system_toolkits tools (FastMCP)."""
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from fastmcp import FastMCP


@pytest.fixture
def mcp():
    """Create a FastMCP instance."""
    return FastMCP("test-server")


@pytest.fixture
def mock_workspace():
    """Mock workspace, agent, and session IDs."""
    return {
        "workspace_id": "test-workspace",
        "agent_id": "test-agent",
        "session_id": "test-session"
    }


@pytest.fixture
def mock_secure_path(tmp_path):
    """Mock get_secure_path to return temp directory paths."""
    def _get_secure_path(path, workspace_id, agent_id, session_id):
        return os.path.join(tmp_path, path)
    
    with patch("aden_tools.tools.file_system_toolkits.view_file.view_file.get_secure_path", side_effect=_get_secure_path):
        with patch("aden_tools.tools.file_system_toolkits.write_to_file.write_to_file.get_secure_path", side_effect=_get_secure_path):
            with patch("aden_tools.tools.file_system_toolkits.list_dir.list_dir.get_secure_path", side_effect=_get_secure_path):
                with patch("aden_tools.tools.file_system_toolkits.replace_file_content.replace_file_content.get_secure_path", side_effect=_get_secure_path):
                    with patch("aden_tools.tools.file_system_toolkits.apply_diff.apply_diff.get_secure_path", side_effect=_get_secure_path):
                        with patch("aden_tools.tools.file_system_toolkits.apply_patch.apply_patch.get_secure_path", side_effect=_get_secure_path):
                            with patch("aden_tools.tools.file_system_toolkits.grep_search.grep_search.get_secure_path", side_effect=_get_secure_path):
                                with patch("aden_tools.tools.file_system_toolkits.grep_search.grep_search.WORKSPACES_DIR", str(tmp_path)):
                                    with patch("aden_tools.tools.file_system_toolkits.execute_command_tool.execute_command_tool.get_secure_path", side_effect=_get_secure_path):
                                        with patch("aden_tools.tools.file_system_toolkits.execute_command_tool.execute_command_tool.WORKSPACES_DIR", str(tmp_path)):
                                            yield


class TestViewFileTool:
    """Tests for view_file tool."""

    @pytest.fixture
    def view_file_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.view_file import register_tools
        register_tools(mcp)
        return mcp._tool_manager._tools["view_file"].fn

    def test_view_existing_file(self, view_file_fn, mock_workspace, mock_secure_path, tmp_path):
        """Viewing an existing file returns content and metadata."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        result = view_file_fn(path="test.txt", **mock_workspace)

        assert result["success"] is True
        assert result["content"] == "Hello, World!"
        assert result["size_bytes"] == len("Hello, World!".encode("utf-8"))
        assert result["lines"] == 1

    def test_view_nonexistent_file(self, view_file_fn, mock_workspace, mock_secure_path):
        """Viewing a non-existent file returns an error."""
        result = view_file_fn(path="nonexistent.txt", **mock_workspace)

        assert "error" in result
        assert "not found" in result["error"].lower()


class TestWriteToFileTool:
    """Tests for write_to_file tool."""

    @pytest.fixture
    def write_to_file_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.write_to_file import register_tools
        register_tools(mcp)
        return mcp._tool_manager._tools["write_to_file"].fn

    def test_write_new_file(self, write_to_file_fn, mock_workspace, mock_secure_path, tmp_path):
        """Writing to a new file creates it successfully."""
        result = write_to_file_fn(
            path="new_file.txt",
            content="Test content",
            **mock_workspace
        )

        assert result["success"] is True
        assert result["mode"] == "written"
        assert result["bytes_written"] > 0

        # Verify file was created
        created_file = tmp_path / "new_file.txt"
        assert created_file.exists()
        assert created_file.read_text() == "Test content"

    def test_write_append_mode(self, write_to_file_fn, mock_workspace, mock_secure_path, tmp_path):
        """Writing with append=True appends to existing file."""
        test_file = tmp_path / "append_test.txt"
        test_file.write_text("Line 1\n")

        result = write_to_file_fn(
            path="append_test.txt",
            content="Line 2\n",
            append=True,
            **mock_workspace
        )

        assert result["success"] is True
        assert result["mode"] == "appended"
        assert test_file.read_text() == "Line 1\nLine 2\n"


class TestListDirTool:
    """Tests for list_dir tool."""

    @pytest.fixture
    def list_dir_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.list_dir import register_tools
        register_tools(mcp)
        return mcp._tool_manager._tools["list_dir"].fn

    def test_list_directory(self, list_dir_fn, mock_workspace, mock_secure_path, tmp_path):
        """Listing a directory returns all entries."""
        # Create test files and directories
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")
        (tmp_path / "subdir").mkdir()

        result = list_dir_fn(path=".", **mock_workspace)

        assert result["success"] is True
        assert result["total_count"] == 3
        assert len(result["entries"]) == 3

        # Check that entries have correct structure
        for entry in result["entries"]:
            assert "name" in entry
            assert "type" in entry
            assert entry["type"] in ["file", "directory"]

    def test_list_empty_directory(self, list_dir_fn, mock_workspace, mock_secure_path, tmp_path):
        """Listing an empty directory returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = list_dir_fn(path="empty", **mock_workspace)

        assert result["success"] is True
        assert result["total_count"] == 0
        assert result["entries"] == []


class TestReplaceFileContentTool:
    """Tests for replace_file_content tool."""

    @pytest.fixture
    def replace_file_content_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.replace_file_content import register_tools
        register_tools(mcp)
        return mcp._tool_manager._tools["replace_file_content"].fn

    def test_replace_content(self, replace_file_content_fn, mock_workspace, mock_secure_path, tmp_path):
        """Replacing content in a file works correctly."""
        test_file = tmp_path / "replace_test.txt"
        test_file.write_text("Hello World! Hello again!")

        result = replace_file_content_fn(
            path="replace_test.txt",
            target="Hello",
            replacement="Hi",
            **mock_workspace
        )

        assert result["success"] is True
        assert result["occurrences_replaced"] == 2
        assert test_file.read_text() == "Hi World! Hi again!"

    def test_replace_target_not_found(self, replace_file_content_fn, mock_workspace, mock_secure_path, tmp_path):
        """Replacing non-existent target returns error."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        result = replace_file_content_fn(
            path="test.txt",
            target="nonexistent",
            replacement="new",
            **mock_workspace
        )

        assert "error" in result
        assert "not found" in result["error"].lower()


class TestGrepSearchTool:
    """Tests for grep_search tool."""

    @pytest.fixture
    def grep_search_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.grep_search import register_tools
        register_tools(mcp)
        return mcp._tool_manager._tools["grep_search"].fn

    def test_grep_search_single_file(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Searching a single file returns matches."""
        test_file = tmp_path / "search_test.txt"
        test_file.write_text("Line 1\nLine 2 with pattern\nLine 3")

        result = grep_search_fn(
            path="search_test.txt",
            pattern="pattern",
            **mock_workspace
        )

        assert result["success"] is True
        assert result["total_matches"] == 1
        assert len(result["matches"]) == 1
        assert result["matches"][0]["line_number"] == 2
        assert "pattern" in result["matches"][0]["line_content"]

    def test_grep_search_no_matches(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Searching with no matches returns empty list."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        result = grep_search_fn(
            path="test.txt",
            pattern="nonexistent",
            **mock_workspace
        )

        assert result["success"] is True
        assert result["total_matches"] == 0
        assert result["matches"] == []


class TestExecuteCommandTool:
    """Tests for execute_command_tool."""

    @pytest.fixture
    def execute_command_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.execute_command_tool import register_tools
        register_tools(mcp)
        return mcp._tool_manager._tools["execute_command_tool"].fn

    def test_execute_simple_command(self, execute_command_fn, mock_workspace, mock_secure_path):
        """Executing a simple command returns output."""
        result = execute_command_fn(
            command="echo 'Hello World'",
            **mock_workspace
        )

        assert result["success"] is True
        assert result["return_code"] == 0
        assert "Hello World" in result["stdout"]

    def test_execute_failing_command(self, execute_command_fn, mock_workspace, mock_secure_path):
        """Executing a failing command returns non-zero exit code."""
        result = execute_command_fn(
            command="exit 1",
            **mock_workspace
        )

        assert result["success"] is True
        assert result["return_code"] == 1


class TestApplyDiffTool:
    """Tests for apply_diff tool."""

    @pytest.fixture
    def apply_diff_fn(self, mcp):
        from aden_tools.tools.file_system_toolkits.apply_diff import register_tools
        register_tools(mcp)
        return mcp._tool_manager._tools["apply_diff"].fn

    def test_apply_diff_file_not_found(self, apply_diff_fn, mock_workspace, mock_secure_path):
        """Applying diff to non-existent file returns error."""
        result = apply_diff_fn(
            path="nonexistent.txt",
            diff_text="some diff",
            **mock_workspace
        )

        assert "error" in result
        assert "not found" in result["error"].lower()
