"""Cross-platform path security module for Hive agent sandboxing.

This module provides secure path resolution that works identically on
Windows, Linux, and macOS by using pathlib exclusively.
"""
from pathlib import Path

# Use user home directory for workspaces
WORKSPACES_DIR = Path.home() / ".hive" / "workdir" / "workspaces"


def get_secure_path(path: str, workspace_id: str, agent_id: str, session_id: str) -> str:
    """Resolve and verify a path within a 3-layer sandbox (workspace/agent/session).
    
    This function is cross-platform compatible using pathlib:
    - Handles both '/' (Unix) and '\\' (Windows) path separators automatically
    - Treats absolute paths as relative to session root for security
    - Prevents path traversal attacks (../)
    - Uses Path.is_relative_to() for robust sandbox validation
    
    Args:
        path: The path to resolve (can be absolute or relative)
        workspace_id: The workspace identifier
        agent_id: The agent identifier
        session_id: The session identifier
        
    Returns:
        The resolved absolute path as a string
        
    Raises:
        ValueError: If IDs are missing or path escapes the sandbox
    """
    if not workspace_id or not agent_id or not session_id:
        raise ValueError("workspace_id, agent_id, and session_id are all required")

    # Ensure session directory exists using pathlib
    session_dir = WORKSPACES_DIR / workspace_id / agent_id / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert input to Path object for cross-platform handling
    input_path = Path(path)
    
    # Normalize the path: strip leading slashes to make it relative
    # This handles both Unix (/etc/passwd) and Windows (C:\foo) style paths
    path_str = path.lstrip('/\\')
    
    # Handle Windows drive letters (e.g., "C:" -> strip the colon too)
    if len(path_str) >= 2 and path_str[1] == ':':
        path_str = path_str[2:].lstrip('/\\')
    
    # Join with session directory and resolve to absolute path
    final_path = (session_dir / path_str).resolve()
    
    # Security check: verify path is within session_dir using is_relative_to()
    # This is the recommended cross-platform way to check path containment
    try:
        if not final_path.is_relative_to(session_dir.resolve()):
            raise ValueError(f"Access denied: Path '{path}' is outside the session sandbox.")
    except ValueError:
        # is_relative_to raises ValueError if not relative, re-raise with clear message
        raise ValueError(f"Access denied: Path '{path}' is outside the session sandbox.")
        
    return str(final_path)
