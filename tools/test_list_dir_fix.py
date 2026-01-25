#!/usr/bin/env python3
"""Test the list_dir fix for broken symlinks."""

import tempfile
from pathlib import Path
from fastmcp import FastMCP

# Test directly
def test_list_dir_symlinks():
    """Test that list_dir handles all symlink types."""
    from aden_tools.tools.file_system_toolkits.list_dir import register_tools
    from unittest.mock import patch
    
    mcp = FastMCP("test")
    register_tools(mcp)
    list_dir_fn = mcp._tool_manager._tools["list_dir"].fn
    
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        
        # Create test files
        (tmpdir / "normal_file.txt").write_text("content")
        (tmpdir / "subdir").mkdir()
        
        # Create valid symlink
        target = tmpdir / "target.txt"
        target.write_text("target content")
        (tmpdir / "good_link").symlink_to(target)
        
        # Create broken symlink
        (tmpdir / "broken_link").symlink_to(tmpdir / "nonexistent.txt")
        
        # Mock get_secure_path to return our temp dir
        with patch("aden_tools.tools.file_system_toolkits.list_dir.list_dir.get_secure_path", return_value=str(tmpdir)):
            result = list_dir_fn(
                path=".",
                workspace_id="test",
                agent_id="test",
                session_id="test"
            )
        
        print("Testing list_dir with symlinks...")
        print(f"\nResult: {result}")
        
        assert result["success"] is True, "Should succeed"
        assert result["total_count"] == 5, f"Should have 5 entries, got {result['total_count']}"
        
        # Check each entry type
        entries_by_name = {e["name"]: e for e in result["entries"]}
        
        # Normal file
        assert entries_by_name["normal_file.txt"]["type"] == "file"
        assert entries_by_name["normal_file.txt"]["size_bytes"] == 7
        print("✓ Normal file handled correctly")
        
        # Directory
        assert entries_by_name["subdir"]["type"] == "directory"
        assert entries_by_name["subdir"]["size_bytes"] is None
        print("✓ Directory handled correctly")
        
        # Target file
        assert entries_by_name["target.txt"]["type"] == "file"
        assert entries_by_name["target.txt"]["size_bytes"] == 14
        print("✓ Target file handled correctly")
        
        # Good symlink
        assert entries_by_name["good_link"]["type"] == "symlink"
        assert entries_by_name["good_link"]["size_bytes"] == 14
        assert entries_by_name["good_link"].get("broken") is None
        print("✓ Valid symlink handled correctly")
        
        # Broken symlink (the key test!)
        assert entries_by_name["broken_link"]["type"] == "symlink"
        assert entries_by_name["broken_link"]["size_bytes"] is None
        assert entries_by_name["broken_link"]["broken"] is True
        print("✓ Broken symlink handled correctly WITHOUT CRASH!")
        
        print("\n✅ All tests passed! list_dir now handles broken symlinks gracefully.")

if __name__ == "__main__":
    test_list_dir_symlinks()
