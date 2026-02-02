"""Tests for database_tool - Read-only SQLite access."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.database_tool.database_tool import register_tools

TEST_WORKSPACE_ID = "test-workspace"
TEST_AGENT_ID = "test-agent"
TEST_SESSION_ID = "test-session"


@pytest.fixture
def db_tools(mcp: FastMCP, tmp_path: Path):
    with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
        register_tools(mcp)
        yield {
            "db_info": mcp._tool_manager._tools["db_info"].fn,
            "db_query": mcp._tool_manager._tools["db_query"].fn,
        }


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    session_path = tmp_path / TEST_WORKSPACE_ID / TEST_AGENT_ID / TEST_SESSION_ID
    session_path.mkdir(parents=True, exist_ok=True)
    return session_path


@pytest.fixture
def sample_db(session_dir: Path) -> Path:
    db_path = session_dir / "sample.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO users (name) VALUES ('Alice'), ('Bob')")
    conn.commit()
    conn.close()
    return db_path


def test_db_info_lists_tables(db_tools, sample_db, tmp_path):
    with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
        result = db_tools["db_info"](
            path="sample.db",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
        )

    assert result["success"] is True
    assert "users" in result["tables"]
    assert result["table_count"] == 1


def test_db_query_select(db_tools, sample_db, tmp_path):
    with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
        result = db_tools["db_query"](
            path="sample.db",
            query="SELECT name FROM users ORDER BY id",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
        )

    assert result["success"] is True
    assert result["row_count"] == 2
    assert result["rows"][0]["name"] == "Alice"


def test_db_query_rejects_non_select(db_tools, sample_db, tmp_path):
    with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
        result = db_tools["db_query"](
            path="sample.db",
            query="DELETE FROM users",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
        )

    assert "error" in result
    assert "select" in result["error"].lower()
