import os
from pathlib import Path
from typing import IO

# Use user home directory for workspaces
WORKSPACES_DIR = os.path.expanduser("~/.hive/workdir/workspaces")


def get_secure_path(path: str, workspace_id: str, agent_id: str, session_id: str) -> str:
    """Resolve and verify a path within a 3-layer sandbox (workspace/agent/session)."""
    if not workspace_id or not agent_id or not session_id:
        raise ValueError("workspace_id, agent_id, and session_id are all required")

    # Ensure session directory exists: runtime/workspace_id/agent_id/session_id
    session_dir = os.path.join(WORKSPACES_DIR, workspace_id, agent_id, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # Resolve absolute path
    if os.path.isabs(path):
        # Treat absolute paths as relative to the session root if they start with /
        rel_path = path.lstrip(os.sep)
        final_path = os.path.abspath(os.path.join(session_dir, rel_path))
    else:
        final_path = os.path.abspath(os.path.join(session_dir, path))

    # Verify path is within session_dir
    common_prefix = os.path.commonpath([final_path, session_dir])
    if common_prefix != session_dir:
        raise ValueError(f"Access denied: Path '{path}' is outside the session sandbox.")

    return final_path


def _is_under_session_root(session_dir: Path, path: Path) -> bool:
    """Validate that a real path stays under the session root."""
    try:
        real = path.resolve(strict=True)
        root = session_dir.resolve(strict=True)
    except FileNotFoundError:
        return False

    try:
        real.relative_to(root)
        return True
    except ValueError:
        return False


def safe_open_in_sandbox(
    path: str,
    workspace_id: str,
    agent_id: str,
    session_id: str,
    mode: str = "r",
    encoding: str = "utf-8",
) -> IO[str]:
    """
    Atomically resolve and open a file within the session sandbox.

    This mitigates TOCTOU issues where a checked path is swapped for a
    symlink pointing outside the sandbox between validation and open().
    """
    # Resolve lexical path and ensure session dir exists
    secure_path_str = get_secure_path(path, workspace_id, agent_id, session_id)
    secure_path = Path(secure_path_str)
    session_dir = Path(WORKSPACES_DIR) / workspace_id / agent_id / session_id

    # Open first, then validate the real path is still under session_dir
    f = open(secure_path, mode, encoding=encoding)
    if not _is_under_session_root(session_dir, secure_path):
        f.close()
        raise PermissionError("Path escaped session sandbox via TOCTOU/symlink")

    return f
