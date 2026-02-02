"""Tests for csv_tool - Updated for Multi-file SQL Support."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.csv_tool.csv_tool import register_tools

duckdb_available = importlib.util.find_spec("duckdb") is not None

# Test IDs for sandbox
TEST_WORKSPACE_ID = "test-workspace"
TEST_AGENT_ID = "test-agent"
TEST_SESSION_ID = "test-session"


@pytest.fixture
def csv_tools(mcp: FastMCP, tmp_path: Path):
    """Register all CSV tools and return them as a dict."""
    with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
        register_tools(mcp)
        yield {
            "csv_read": mcp._tool_manager._tools["csv_read"].fn,
            "csv_write": mcp._tool_manager._tools["csv_write"].fn,
            "csv_append": mcp._tool_manager._tools["csv_append"].fn,
            "csv_info": mcp._tool_manager._tools["csv_info"].fn,
            "csv_sql": mcp._tool_manager._tools["csv_sql"].fn,
        }

@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    """Create and return the session directory within the sandbox."""
    session_path = tmp_path / TEST_WORKSPACE_ID / TEST_AGENT_ID / TEST_SESSION_ID
    session_path.mkdir(parents=True, exist_ok=True)
    return session_path

@pytest.fixture
def products_csv(session_dir: Path) -> Path:
    """Create a products CSV for SQL testing."""
    csv_file = session_dir / "products.csv"
    csv_file.write_text(
        "id,name,category,price\n"
        "1,iPhone,Electronics,999\n"
        "2,MacBook,Electronics,1999\n"
        "3,Coffee Mug,Kitchen,15\n"
    )
    return csv_file

@pytest.fixture
def categories_csv(session_dir: Path) -> Path:
    """Create a categories CSV for JOIN testing."""
    csv_file = session_dir / "categories.csv"
    csv_file.write_text(
        "category,manager\n"
        "Electronics,Alice\n"
        "Kitchen,Bob\n"
    )
    return csv_file


# --- Test CsvRead, Write, Append, Info kısımları aynı kalacak ---
# (Sadece csv_sql kısmındaki değişiklikleri ve yeni testleri aşağıya ekliyorum)

@pytest.mark.skipif(not duckdb_available, reason="duckdb not installed")
class TestCsvSql:
    """Tests for csv_sql function (Updated for Multi-file Support)."""

    def test_basic_select_single_file(self, csv_tools, products_csv, tmp_path):
        """Execute basic SELECT query using 'paths' as a string."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = csv_tools["csv_sql"](
                paths="products.csv",  # Tekil path desteği
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                query="SELECT * FROM data",
            )

        assert result["success"] is True
        assert result["row_count"] == 3
        assert result["rows"][0]["name"] == "iPhone"

    def test_multi_file_join(self, csv_tools, products_csv, categories_csv, tmp_path):
        """Execute JOIN query across multiple CSV files (The New Feature)."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = csv_tools["csv_sql"](
                paths=["products.csv", "categories.csv"], # Liste desteği
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                query="""
                    SELECT data0.name, data1.manager 
                    FROM data0 
                    JOIN data1 ON data0.category = data1.category 
                    WHERE data0.id = '1'
                """,
            )

        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["rows"][0]["name"] == "iPhone"
        assert result["rows"][0]["manager"] == "Alice"

    def test_alias_backward_compatibility(self, csv_tools, products_csv, tmp_path):
        """Ensure 'data' still works as an alias for 'data0'."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = csv_tools["csv_sql"](
                paths=["products.csv"],
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                query="SELECT name FROM data WHERE id = '2'",
            )
        assert result["success"] is True
        assert result["rows"][0]["name"] == "MacBook"

    def test_security_blocked_dml(self, csv_tools, products_csv, tmp_path):
        """Ensure non-SELECT queries are still blocked."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = csv_tools["csv_sql"](
                paths="products.csv",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                query="DELETE FROM data",
            )
        assert "error" in result
        assert "allowed" in result["error"].lower()

    def test_file_not_found_in_list(self, csv_tools, products_csv, tmp_path):
        """Return error if one of the files in the list is missing."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = csv_tools["csv_sql"](
                paths=["products.csv", "missing.csv"],
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                query="SELECT * FROM data0",
            )
        assert "error" in result
        assert "not found" in result["error"].lower()