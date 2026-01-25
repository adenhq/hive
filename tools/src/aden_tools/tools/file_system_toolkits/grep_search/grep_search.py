import os
import re
from mcp.server.fastmcp import FastMCP
from ..security import get_secure_path, WORKSPACES_DIR

# --- SMART FILTERING CONFIG ---
# Folders to completely ignore during recursive searches
IGNORED_DIRS = {
    'node_modules', '.git', '.idea', '.vscode', '__pycache__', 
    'venv', 'env', '.DS_Store', 'dist', 'build', 'coverage',
    'target', 'bin', 'obj' # Added common build folders
}

# File extensions to skip (prevent opening binaries as text)
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp',
    '.pdf', '.zip', '.tar', '.gz', '.7z', '.rar',
    '.exe', '.dll', '.so', '.dylib', '.bin',
    '.pyc', '.pyo', '.pyd', '.class', '.o', '.obj',
    '.db', '.sqlite', '.sqlite3', '.parquet'
}

MAX_MATCHES = 1000  # Safety cap to prevent context window crash

def register_tools(mcp: FastMCP) -> None:
    """Register grep search tools with the MCP server."""

    @mcp.tool()
    def grep_search(path: str, pattern: str, workspace_id: str, agent_id: str, session_id: str, recursive: bool = False) -> dict:
        """
        Search for a pattern in a file or directory within the session sandbox.

        Use this when you need to find specific content or patterns in files using regex.
        Set recursive=True to search through all subdirectories.

        Args:
            path: The path to search in (file or directory, relative to session root)
            pattern: The regex pattern to search for
            workspace_id: The ID of the workspace
            agent_id: The ID of the agent
            session_id: The ID of the current session
            recursive: Whether to search recursively in directories (default: False)

        Returns:
            Dict with search results and match details, or error dict
        """
        # 1. Early Regex Validation
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e.msg}"}

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)
            # Use session dir root for relative path calculations
            session_root = os.path.join(WORKSPACES_DIR, workspace_id, agent_id, session_id)

            matches = []
            
            # Helper to check if file should be processed
            def is_skippable(file_name):
                _, ext = os.path.splitext(file_name)
                return ext.lower() in BINARY_EXTENSIONS

            # Helper to search a single file
            def search_file(f_path):
                # Optimization: Stop if we already hit the limit
                if len(matches) >= MAX_MATCHES:
                    return

                # Calculate relative path for display
                display_path = os.path.relpath(f_path, session_root)
                
                try:
                    with open(f_path, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            if regex.search(line):
                                matches.append({
                                    "file": display_path,
                                    "line_number": i,
                                    "line_content": line.strip()[:300]  # Truncate extremely long lines
                                })
                                if len(matches) >= MAX_MATCHES:
                                    return
                except (UnicodeDecodeError, PermissionError):
                    # Skip files that aren't valid UTF-8 text or are locked
                    return

            # --- MAIN LOOP OPTIMIZATION ---
            
            if os.path.isfile(secure_path):
                search_file(secure_path)
            
            elif recursive:
                # Optimized Recursive Walk
                for root, dirs, filenames in os.walk(secure_path):
                    # 1. PRUNE IGNORED DIRECTORIES IN-PLACE
                    # This modifies the 'dirs' list used by os.walk, preventing it 
                    # from entering node_modules, .git, etc.
                    dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
                    
                    if len(matches) >= MAX_MATCHES:
                        break

                    for filename in filenames:
                        if not is_skippable(filename):
                            search_file(os.path.join(root, filename))
                            if len(matches) >= MAX_MATCHES:
                                break
            else:
                # Non-recursive directory list
                if os.path.isdir(secure_path):
                    for filename in os.listdir(secure_path):
                        full_path = os.path.join(secure_path, filename)
                        # Check if it is a file and not a binary
                        if os.path.isfile(full_path) and not is_skippable(filename):
                            search_file(full_path)
                            if len(matches) >= MAX_MATCHES:
                                break

            result = {
                "success": True,
                "pattern": pattern,
                "path": path,
                "recursive": recursive,
                "matches": matches,
                "total_matches": len(matches)
            }

            if len(matches) >= MAX_MATCHES:
                result["warning"] = f"Match limit reached ({MAX_MATCHES}). Please refine your search."

            return result

        except FileNotFoundError:
            return {"error": f"Directory or file not found: {path}"}
        except PermissionError:
            return {"error": f"Permission denied accessing: {path}"}
        except Exception as e:
            return {"error": f"Failed to perform grep search: {str(e)}"}