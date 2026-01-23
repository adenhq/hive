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


class TestGrepSearch:
    """Improved tests for grep_search with debugging output."""
    
    @pytest.fixture
    def grep_search_fn(self, mcp):
        """Register and return the grep_search tool function."""
        from aden_tools.tools.file_system_toolkits.grep_search import register_tools
        register_tools(mcp)
        return mcp._tool_manager._tools["grep_search"].fn

    def test_grep_search_directory_non_recursive_debug(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Searching directory non-recursively only searches immediate files - with debug output."""
        # Create files in root
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("pattern here")
        file2.write_text("no match here")

        # Create nested directory with file
        nested = tmp_path / "nested"
        nested.mkdir()
        nested_file = nested / "nested_file.txt"
        nested_file.write_text("pattern in nested")

        # Debug: Print what files exist
        print(f"\nFiles in {tmp_path}:")
        for item in tmp_path.iterdir():
            print(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
        
        # Debug: Print what the function will search
        print(f"\nSearching path='.' from tmp_path: {tmp_path}")
        
        result = grep_search_fn(
            path=".",
            pattern="pattern",
            recursive=False,
            **mock_workspace
        )

        # Debug output
        print(f"\nResult: {result}")
        if result.get("success"):
            print(f"Matches found: {result['total_matches']}")
            for match in result.get("matches", []):
                print(f"  - {match['file']} line {match['line_number']}: {match['line_content']}")

        assert result["success"] is True, f"Search failed: {result.get('error')}"
        
        # The key assertion
        assert result["total_matches"] == 1, \
            f"Expected 1 match (only file1.txt in root), got {result['total_matches']}. Matches: {result.get('matches')}"
        
        assert result["recursive"] is False
        
        # Verify the match is from file1.txt
        assert len(result["matches"]) == 1
        assert "file1.txt" in result["matches"][0]["file"]
        assert "pattern here" in result["matches"][0]["line_content"]

    def test_grep_search_edge_case_hidden_files(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Test that hidden files (starting with .) are handled correctly."""
        # Create regular and hidden files
        (tmp_path / "visible.txt").write_text("pattern here")
        (tmp_path / ".hidden.txt").write_text("pattern in hidden")
        
        result = grep_search_fn(
            path=".",
            pattern="pattern",
            recursive=False,
            **mock_workspace
        )
        
        assert result["success"] is True
        # Both files should be found (Python's os.listdir includes hidden files)
        assert result["total_matches"] == 2

    def test_grep_search_subdirectory_non_recursive(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Test non-recursive search starting from a subdirectory."""
        # Create a subdirectory with files
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file1.txt").write_text("pattern here")
        (subdir / "file2.txt").write_text("no match")  # Changed from "no pattern" to "no match"
        
        # Create a nested subdirectory (should not be searched)
        nested = subdir / "nested"
        nested.mkdir()
        (nested / "file3.txt").write_text("pattern in nested")
        
        result = grep_search_fn(
            path="subdir",
            pattern="pattern",
            recursive=False,
            **mock_workspace
        )
        
        assert result["success"] is True
        assert result["total_matches"] == 1, \
            f"Expected 1 match (only file1.txt), got {result['total_matches']}. Matches: {result.get('matches')}"
        assert "subdir/file1.txt" in result["matches"][0]["file"]

    def test_grep_search_symlinks(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Test handling of symbolic links (if supported by OS)."""
        import platform
        
        # Skip on Windows if symlinks not available
        if platform.system() == "Windows":
            pytest.skip("Symlink test skipped on Windows")
        
        # Create a file and a symlink to it
        real_file = tmp_path / "real.txt"
        real_file.write_text("pattern here")
        
        link_file = tmp_path / "link.txt"
        link_file.symlink_to(real_file)
        
        result = grep_search_fn(
            path=".",
            pattern="pattern",
            recursive=False,
            **mock_workspace
        )
        
        assert result["success"] is True
        # Should find pattern in both real file and symlink (2 matches)
        # OR just in real file (1 match) depending on implementation
        assert result["total_matches"] >= 1

    def test_grep_search_empty_directory(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Test searching an empty directory returns no matches."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        result = grep_search_fn(
            path="empty",
            pattern="anything",
            recursive=False,
            **mock_workspace
        )
        
        assert result["success"] is True
        assert result["total_matches"] == 0
        assert result["matches"] == []

    def test_grep_search_case_sensitive(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Test that search is case-sensitive by default."""
        test_file = tmp_path / "case.txt"
        test_file.write_text("Pattern PATTERN pattern")
        
        result = grep_search_fn(
            path="case.txt",
            pattern="pattern",
            recursive=False,
            **mock_workspace
        )
        
        assert result["success"] is True
        assert result["total_matches"] == 1  # Only lowercase "pattern"

    def test_grep_search_case_insensitive(self, grep_search_fn, mock_workspace, mock_secure_path, tmp_path):
        """Test case-insensitive search using regex flag."""
        test_file = tmp_path / "case.txt"
        test_file.write_text("Pattern PATTERN pattern")
        
        result = grep_search_fn(
            path="case.txt",
            pattern="(?i)pattern",  # Case-insensitive flag
            recursive=False,
            **mock_workspace
        )
        
        assert result["success"] is True
        assert result["total_matches"] == 1  # One line with all variants