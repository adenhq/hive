"""Tests for parquet_tool - Read and query Parquet files."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.parquet_tool.parquet_tool import register_tools

duckdb_available = importlib.util.find_spec("duckdb") is not None

TEST_WORKSPACE_ID = "test-workspace"
TEST_AGENT_ID = "test-agent"
TEST_SESSION_ID = "test-session"


@pytest.fixture
def parquet_tools(mcp: FastMCP, tmp_path: Path):
    """Register all Parquet tools and return them as a dict."""
    with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
        register_tools(mcp)
        yield {
            "parquet_info": mcp._tool_manager._tools["parquet_info"].fn,
            "parquet_preview": mcp._tool_manager._tools["parquet_preview"].fn,
            "parquet_query": mcp._tool_manager._tools["parquet_query"].fn,
        }


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    """Create and return the session directory within the sandbox."""
    session_path = tmp_path / TEST_WORKSPACE_ID / TEST_AGENT_ID / TEST_SESSION_ID
    session_path.mkdir(parents=True, exist_ok=True)
    return session_path


@pytest.fixture
def basic_parquet(session_dir: Path) -> Path:
    """Create a basic Parquet file for testing."""
    if not duckdb_available:
        pytest.skip("duckdb not installed")
    
    import duckdb
    
    parquet_file = session_dir / "basic.parquet"
    con = duckdb.connect(":memory:")
    con.execute(
        "COPY (SELECT * FROM (VALUES "
        "('Alice', 30, 'NYC'), "
        "('Bob', 25, 'LA'), "
        "('Charlie', 35, 'Chicago')) AS t(name, age, city)) "
        f"TO '{parquet_file}' (FORMAT PARQUET)"
    )
    con.close()
    return parquet_file


@pytest.fixture
def products_parquet(session_dir: Path) -> Path:
    """Create a products Parquet file for testing."""
    if not duckdb_available:
        pytest.skip("duckdb not installed")
    
    import duckdb
    
    parquet_file = session_dir / "products.parquet"
    con = duckdb.connect(":memory:")
    con.execute(
        "COPY (SELECT * FROM (VALUES "
        "(1, 'iPhone', 'Electronics', 999, 50), "
        "(2, 'MacBook', 'Electronics', 1999, 30), "
        "(3, 'Coffee Mug', 'Kitchen', 15, 200), "
        "(4, 'Headphones', 'Electronics', 299, 75), "
        "(5, 'Water Bottle', 'Kitchen', 25, 150)) "
        "AS t(id, name, category, price, stock)) "
        f"TO '{parquet_file}' (FORMAT PARQUET)"
    )
    con.close()
    return parquet_file


@pytest.fixture
def partitioned_parquet(session_dir: Path) -> Path:
    """Create a partitioned Parquet dataset (folder with multiple files)."""
    if not duckdb_available:
        pytest.skip("duckdb not installed")
    
    import duckdb
    
    folder = session_dir / "partitioned"
    folder.mkdir()
    
    con = duckdb.connect(":memory:")
    
    # Create part 1
    con.execute(
        "COPY (SELECT * FROM (VALUES "
        "(1, 'A', 100), (2, 'B', 200)) AS t(id, name, value)) "
        f"TO '{folder / 'part1.parquet'}' (FORMAT PARQUET)"
    )
    
    # Create part 2
    con.execute(
        "COPY (SELECT * FROM (VALUES "
        "(3, 'C', 300), (4, 'D', 400)) AS t(id, name, value)) "
        f"TO '{folder / 'part2.parquet'}' (FORMAT PARQUET)"
    )
    
    con.close()
    return folder


@pytest.mark.skipif(not duckdb_available, reason="duckdb not installed")
class TestParquetInfo:
    """Tests for parquet_info function."""

    def test_info_basic_parquet(self, parquet_tools, basic_parquet, tmp_path):
        """Get info about a basic Parquet file."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_info"](
                path="basic.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
            )

        assert result["success"] is True
        assert result["column_count"] == 3
        assert result["row_count"] == 3
        assert result["file_count"] == 1
        assert len(result["columns"]) == 3
        assert result["columns"][0]["name"] == "name"

    def test_info_partitioned_dataset(self, parquet_tools, partitioned_parquet, tmp_path):
        """Get info about a partitioned Parquet dataset."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_info"](
                path="partitioned",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
            )

        assert result["success"] is True
        assert result["file_count"] == 2
        assert result["row_count"] == 4

    def test_info_file_not_found(self, parquet_tools, session_dir, tmp_path):
        """Return error for non-existent file."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_info"](
                path="nonexistent.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
            )

        assert "error" in result
        assert "not found" in result["error"].lower()


@pytest.mark.skipif(not duckdb_available, reason="duckdb not installed")
class TestParquetPreview:
    """Tests for parquet_preview function."""

    def test_preview_basic(self, parquet_tools, basic_parquet, tmp_path):
        """Preview a basic Parquet file."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_preview"](
                path="basic.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
            )

        assert result["success"] is True
        assert result["row_count"] == 3
        assert len(result["rows"]) == 3
        assert result["rows"][0]["name"] == "Alice"

    def test_preview_with_limit(self, parquet_tools, basic_parquet, tmp_path):
        """Preview with row limit."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_preview"](
                path="basic.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                limit=2,
            )

        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["limit"] == 2

    def test_preview_with_columns(self, parquet_tools, basic_parquet, tmp_path):
        """Preview with column selection."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_preview"](
                path="basic.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                columns=["name", "age"],
            )

        assert result["success"] is True
        assert result["columns"] == ["name", "age"]
        assert "city" not in result["rows"][0]

    def test_preview_with_where(self, parquet_tools, basic_parquet, tmp_path):
        """Preview with WHERE clause filtering."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_preview"](
                path="basic.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                where="age > 25",
            )

        assert result["success"] is True
        assert result["row_count"] == 2
        names = [row["name"] for row in result["rows"]]
        assert "Alice" in names
        assert "Charlie" in names
        assert "Bob" not in names

    def test_preview_limit_enforcement(self, parquet_tools, basic_parquet, tmp_path):
        """Enforce maximum limit."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_preview"](
                path="basic.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                limit=1000,  
            )

        assert result["success"] is True
        assert result["limit"] == 20 

    def test_preview_file_not_found(self, parquet_tools, session_dir, tmp_path):
        """Return error for non-existent file."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_preview"](
                path="nonexistent.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
            )

        assert "error" in result
        assert "not found" in result["error"].lower()


@pytest.mark.skipif(not duckdb_available, reason="duckdb not installed")
class TestParquetQuery:
    """Tests for parquet_query function."""

    def test_query_basic_select(self, parquet_tools, products_parquet, tmp_path):
        """Execute basic SELECT query."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="SELECT * FROM data",
            )

        assert result["success"] is True
        assert result["row_count"] == 5
        assert "id" in result["columns"]

    def test_query_with_where(self, parquet_tools, products_parquet, tmp_path):
        """Query with WHERE clause."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="SELECT name, price FROM data WHERE price > 500",
            )

        assert result["success"] is True
        assert result["row_count"] == 2
        names = [row["name"] for row in result["rows"]]
        assert "iPhone" in names
        assert "MacBook" in names

    def test_query_aggregate(self, parquet_tools, products_parquet, tmp_path):
        """Query with aggregate functions."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="SELECT category, COUNT(*) as count FROM data GROUP BY category",
            )

        assert result["success"] is True
        assert result["row_count"] == 2

    def test_query_order_by(self, parquet_tools, products_parquet, tmp_path):
        """Query with ORDER BY."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="SELECT name FROM data ORDER BY price DESC LIMIT 2",
            )

        assert result["success"] is True
        assert result["rows"][0]["name"] == "MacBook"
        assert result["rows"][1]["name"] == "iPhone"

    def test_query_empty_sql_error(self, parquet_tools, products_parquet, tmp_path):
        """Return error for empty SQL."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="",
            )

        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_query_non_select_blocked(self, parquet_tools, products_parquet, tmp_path):
        """Block non-SELECT queries."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="DELETE FROM data WHERE id = 1",
            )

        assert "error" in result
        assert "select" in result["error"].lower()

    def test_query_insert_blocked(self, parquet_tools, products_parquet, tmp_path):
        """Block INSERT statements."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="INSERT INTO data VALUES (6, 'Test', 'Test', 10, 10)",
            )

        assert "error" in result

    def test_query_drop_blocked(self, parquet_tools, products_parquet, tmp_path):
        """Block DROP statements."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="DROP TABLE data",
            )

        assert "error" in result

    def test_query_limit_enforcement(self, parquet_tools, products_parquet, tmp_path):
        """Enforce maximum row limit."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="products.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="SELECT * FROM data",
                limit=2,
            )

        assert result["success"] is True
        assert result["row_count"] <= 2

    def test_query_file_not_found(self, parquet_tools, session_dir, tmp_path):
        """Return error for non-existent file."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_query"](
                path="nonexistent.parquet",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
                sql="SELECT * FROM data",
            )

        assert "error" in result
        assert "not found" in result["error"].lower()


@pytest.mark.skipif(not duckdb_available, reason="duckdb not installed")
class TestParquetSecurity:
    """Security tests for Parquet tools."""

    def test_path_traversal_blocked(self, parquet_tools, session_dir, tmp_path):
        """Prevent path traversal attacks."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_info"](
                path="../../../etc/passwd",
                workspace_id=TEST_WORKSPACE_ID,
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
            )

        assert "error" in result

    def test_missing_workspace_id(self, parquet_tools, basic_parquet, tmp_path):
        """Return error when workspace_id is missing."""
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
            result = parquet_tools["parquet_info"](
                path="basic.parquet",
                workspace_id="",
                agent_id=TEST_AGENT_ID,
                session_id=TEST_SESSION_ID,
            )

        assert "error" in result
