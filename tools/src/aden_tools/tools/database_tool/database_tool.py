"""Database Tool - Secure read-only SQLite access."""

from __future__ import annotations

import os
import re
import sqlite3

from fastmcp import FastMCP

from ..file_system_toolkits.security import get_secure_path

FORBIDDEN_SQL = re.compile(
    r"\b(attach|detach|pragma|alter|insert|update|delete|drop|create|replace)\b",
    re.IGNORECASE,
)


def _is_read_only_query(query: str) -> bool:
    stripped = query.strip().strip(";")
    if not stripped:
        return False
    if FORBIDDEN_SQL.search(stripped):
        return False
    return stripped.lower().startswith("select") or stripped.lower().startswith("with")


def register_tools(mcp: FastMCP) -> None:
    """Register database tools with the MCP server."""

    @mcp.tool()
    def db_info(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
    ) -> dict:
        """Return table and column metadata for a SQLite database."""
        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)
            if not os.path.exists(secure_path):
                return {"error": f"File not found: {path}"}

            conn = sqlite3.connect(f"file:{secure_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            table_info = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info('{table}')")
                table_info[table] = [
                    {
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "default": col[4],
                        "primary_key": bool(col[5]),
                    }
                    for col in cursor.fetchall()
                ]

            return {
                "success": True,
                "path": path,
                "tables": tables,
                "table_count": len(tables),
                "schema": table_info,
            }
        except sqlite3.Error as exc:
            return {"error": f"Database error: {str(exc)}"}
        except Exception as exc:
            return {"error": f"Failed to inspect database: {str(exc)}"}

    @mcp.tool()
    def db_query(
        path: str,
        query: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        limit: int = 1000,
    ) -> dict:
        """Execute a read-only SQL query against a SQLite database."""
        if limit <= 0:
            return {"error": "limit must be greater than zero"}

        if not _is_read_only_query(query):
            return {"error": "Only SELECT queries are allowed"}

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)
            if not os.path.exists(secure_path):
                return {"error": f"File not found: {path}"}

            conn = sqlite3.connect(f"file:{secure_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            wrapped_query = f"SELECT * FROM ({query.strip().strip(';')}) LIMIT ?"
            cursor.execute(wrapped_query, (limit,))
            rows = [dict(row) for row in cursor.fetchall()]

            return {
                "success": True,
                "path": path,
                "row_count": len(rows),
                "rows": rows,
                "limit": limit,
            }
        except sqlite3.Error as exc:
            return {"error": f"Database error: {str(exc)}"}
        except Exception as exc:
            return {"error": f"Failed to execute query: {str(exc)}"}
