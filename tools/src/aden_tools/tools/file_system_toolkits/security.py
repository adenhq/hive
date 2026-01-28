import os

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
        rel_path = path.lstrip("/\\")
        final_path = os.path.abspath(os.path.join(session_dir, rel_path))
    else:
        final_path = os.path.abspath(os.path.join(session_dir, path))

    # Security: Resolve real paths to prevent symlink / junction escapes
    real_session_dir = os.path.normcase(os.path.realpath(session_dir))
    real_final_path = os.path.normcase(os.path.realpath(final_path))

    # Verify path is within session_dir, even after resolving symlinks.
    # Any resolved path outside the sandbox must be blocked.
    try:
        common_prefix = os.path.commonpath([real_final_path, real_session_dir])
    except ValueError:
        # Can happen on Windows if drives logic differs
        raise ValueError(f"Access denied: Path '{path}' resolves outside the session sandbox. Debug: {real_final_path} not in {real_session_dir}")

    if common_prefix != real_session_dir:
        raise ValueError(f"Access denied: Path '{path}' resolves outside the session sandbox (symlink escape). Debug: {real_final_path} not in {real_session_dir}")

    return final_path
