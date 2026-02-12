import os

WORKSPACES_DIR = os.path.expanduser("~/.hive/workdir/workspaces")


def get_secure_path(path: str, workspace_id: str, agent_id: str, session_id: str) -> str:
    """Resolve and verify a path within a 3-layer sandbox (workspace/agent/session)."""
    if not workspace_id or not agent_id or not session_id:
        raise ValueError("workspace_id, agent_id, and session_id are all required")

    session_dir = os.path.realpath(os.path.join(WORKSPACES_DIR, workspace_id, agent_id, session_id))
    os.makedirs(session_dir, exist_ok=True)

    path = path.strip()

    if os.path.isabs(path) or path.startswith(("/", "\\")):
        rel_path = path[1:] if path and path[0] in ("/", "\\") else path
        final_path = os.path.realpath(os.path.join(session_dir, rel_path))
    else:
        final_path = os.path.realpath(os.path.join(session_dir, path))

    try:
        common_prefix = os.path.commonpath([final_path, session_dir])
    except ValueError as err:
        raise ValueError(f"Access denied: Path '{path}' is outside the session sandbox.") from err

    if common_prefix != session_dir:
        raise ValueError(f"Access denied: Path '{path}' is outside the session sandbox.")

    return final_path

