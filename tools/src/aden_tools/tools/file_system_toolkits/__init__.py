"""
File System Toolkits Package
============================
Collection of file system manipulation tools for the Hive agent framework.

This package provides tools for:
- Viewing and reading files
- Writing and creating files
- Applying diffs and patches
- Executing commands
- Searching with grep
- Listing directories
- Replacing file content

All tools follow MCP (Model Context Protocol) standards.
"""

from pathlib import Path

# Import all file system tools
def get_available_tools():
    """Return list of available file system toolkit names."""
    return [
        "view_file",
        "write_to_file", 
        "list_dir",
        "grep_search",
        "execute_command_tool",
        "apply_diff",
        "apply_patch",
        "replace_file_content"
    ]

__all__ = ["get_available_tools"]
