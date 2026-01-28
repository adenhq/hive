"""Tests for security.py - get_secure_path() function."""
import os
import pytest
from unittest.mock import patch


class TestGetSecurePath:
    """Tests for get_secure_path() function."""

    @pytest.fixture(autouse=True)
    def setup_workspaces_dir(self, tmp_path):
        """Patch WORKSPACES_DIR to use temp directory."""
        self.workspaces_dir = tmp_path / "workspaces"
        self.workspaces_dir.mkdir()
        with patch(
            "aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR",
            str(self.workspaces_dir.resolve()),
        ):
            yield

    @pytest.fixture
    def ids(self):
        """Standard workspace, agent, and session IDs."""
        return {
            "workspace_id": "test-workspace",
            "agent_id": "test-agent",
            "session_id": "test-session",
        }

    def test_creates_session_directory(self, ids):
        """Session directory is created if it doesn't exist."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path("file.txt", **ids)

        session_dir = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session"
        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_relative_path_resolved(self, ids):
        """Relative paths are resolved within session directory."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path("subdir/file.txt", **ids)

        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session" / "subdir" / "file.txt"
        assert result == str(expected)

    def test_absolute_path_treated_as_relative(self, ids):
        """Absolute paths are treated as relative to session root (logic verification)."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        # We assume the logic strips leading / or \
        # We mock realpath to just be abspath to avoid tempdir quirks
        with patch("os.path.realpath", side_effect=os.path.abspath):
            result = get_secure_path("/data/file.txt", **ids)
        
        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session" / "data" / "file.txt"
        assert result == str(expected)

    def test_path_traversal_blocked(self, ids):
        """Path traversal attempts are blocked."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        with pytest.raises(ValueError, match="outside the session sandbox"):
            get_secure_path("../../../etc/passwd", **ids)

    def test_path_traversal_with_nested_dotdot(self, ids):
        """Nested path traversal with valid prefix is blocked."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        with pytest.raises(ValueError, match="outside the session sandbox"):
            get_secure_path("valid/../../..", **ids)

    def test_path_traversal_absolute_with_dotdot(self, ids):
        """Absolute path with traversal is blocked."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        with pytest.raises(ValueError, match="outside the session sandbox"):
            get_secure_path("/foo/../../../etc/passwd", **ids)

    def test_missing_workspace_id_raises(self, ids):
        """Missing workspace_id raises ValueError."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        with pytest.raises(ValueError, match="workspace_id.*required"):
            get_secure_path("file.txt", workspace_id="", agent_id=ids["agent_id"], session_id=ids["session_id"])

    def test_missing_agent_id_raises(self, ids):
        """Missing agent_id raises ValueError."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        with pytest.raises(ValueError, match="agent_id.*required"):
            get_secure_path("file.txt", workspace_id=ids["workspace_id"], agent_id="", session_id=ids["session_id"])

    def test_missing_session_id_raises(self, ids):
        """Missing session_id raises ValueError."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        with pytest.raises(ValueError, match="session_id.*required"):
            get_secure_path("file.txt", workspace_id=ids["workspace_id"], agent_id=ids["agent_id"], session_id="")

    def test_none_ids_raise(self):
        """None values for IDs raise ValueError."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        with pytest.raises(ValueError):
            get_secure_path("file.txt", workspace_id=None, agent_id="agent", session_id="session")

    def test_simple_filename(self, ids):
        """Simple filename resolves correctly."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path("file.txt", **ids)

        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session" / "file.txt"
        assert result == str(expected)

    def test_current_dir_path(self, ids):
        """Current directory path (.) resolves to session dir."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path(".", **ids)

        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session"
        assert result == str(expected)

    def test_dot_slash_path(self, ids):
        """Dot-slash paths resolve correctly."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path("./subdir/file.txt", **ids)

        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session" / "subdir" / "file.txt"
        assert result == str(expected)

    def test_deeply_nested_path(self, ids):
        """Deeply nested paths work correctly."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path("a/b/c/d/e/file.txt", **ids)

        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session" / "a" / "b" / "c" / "d" / "e" / "file.txt"
        assert result == str(expected)

    def test_path_with_spaces(self, ids):
        """Paths with spaces work correctly."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path("my folder/my file.txt", **ids)

        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session" / "my folder" / "my file.txt"
        assert result == str(expected)

    def test_path_with_special_characters(self, ids):
        """Paths with special characters work correctly."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path("file-name_v2.0.txt", **ids)

        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session" / "file-name_v2.0.txt"
        assert result == str(expected)

    def test_empty_path(self, ids):
        """Empty string path resolves to session directory."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        result = get_secure_path("", **ids)

        expected = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session"
        assert result == str(expected)

    def test_symlink_within_sandbox_works(self, ids):
        """Symlinks that stay within the sandbox are allowed."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        session_dir = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session"
        # We don't need to create real symlinks, just ensure the logic allows it if realpath is inside.
        
        # We need to rely on the actual behavior for non-symlinks, so we wrap the original realpath
        original_realpath = os.path.realpath
        
        def side_effect(path, *args, **kwargs):
            # If checking the specific symlink, pretend it resolves to a file inside the sandbox
            path_str = str(path)
            if "link_to_target" in path_str:
                return str(session_dir / "target.txt")
            return original_realpath(path, *args, **kwargs)

        with patch("os.path.realpath", side_effect=side_effect):
            # The path passed to realpath will be the abspath of the link
            result = get_secure_path("link_to_target", **ids)
            # It should return the absolute path of the link (not the resolved target, unless we changed that? 
            # Wait, the implementation returns `final_path` which IS the abspath of the input, 
            # BUT checked against the realpath. 
            # Actually, `os.path.abspath` resolves symlinks? No.
            
            expected = session_dir / "link_to_target"
            assert result == str(expected)

    def test_symlink_escape_blocked(self, ids):
        """Symlinks pointing outside sandbox must be blocked."""
        from aden_tools.tools.file_system_toolkits.security import get_secure_path

        session_dir = self.workspaces_dir / "test-workspace" / "test-agent" / "test-session"

        # Logic: 
        # 1. get_secure_path computes final_path = abspath(session_dir/input) -> /.../escape_link
        # 2. calls realpath(/.../escape_link) -> MOCKED to return /.../outside_file.txt
        # 3. checks commonpath -> fails -> raises ValueError

        original_realpath = os.path.realpath
        
        def side_effect(path, *args, **kwargs):
            path_str = str(path)
            if "escape_link" in path_str:
                return str(self.workspaces_dir / "outside_file.txt")
            return original_realpath(path, *args, **kwargs)

        with patch("os.path.realpath", side_effect=side_effect):
            with pytest.raises(ValueError, match="resolves outside the session sandbox"):
                 get_secure_path("escape_link", **ids)
