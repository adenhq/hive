import os

WORKSPACES_DIR = os.path.expanduser("~/.hive/workdir/workspaces")


def get_secure_path(path: str, workspace_id: str, agent_id: str, session_id: str) -> str:
    """Resolve and verify a path within a 3-layer sandbox (workspace/agent/session)."""

    if not workspace_id or not agent_id or not session_id:
        raise ValueError("workspace_id, agent_id, and session_id are all required")

    session_dir = os.path.abspath(
        os.path.join(WORKSPACES_DIR, workspace_id, agent_id, session_id)
    )
    os.makedirs(session_dir, exist_ok=True)

    # ✅ Treat ALL absolute paths as relative
    if os.path.isabs(path):
        path = path.lstrip("/\\")  # remove leading slash or backslash

    final_path = os.path.abspath(os.path.join(session_dir, path))

    # ✅ Strong sandbox enforcement
    if os.path.commonpath([final_path, session_dir]) != session_dir:
        raise ValueError(f"Access denied: Path '{path}' is outside the session sandbox.")

    return final_path
