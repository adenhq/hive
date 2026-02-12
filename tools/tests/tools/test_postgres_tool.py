"""
Tests for PostgreSQL MCP tools.

Goals of this test suite:
- Validate the MCP tool contract (inputs / outputs / error handling)
- Ensure tools work WITHOUT a real PostgreSQL database
- Keep tests schema-agnostic and environment-independent
- Verify read-only behavior and safe failure modes

Key principles:
- No real DB connections
- psycopg connections are fully mocked
- Tests focus on return structure, not actual data
"""

import psycopg
import pytest
from fastmcp import FastMCP

from aden_tools.tools.postgres_tool import register_tools


@pytest.fixture
def mcp():
    """
    Create an isolated FastMCP instance per test.

    Each test registers tools into a fresh MCP instance to avoid
    cross-test pollution.
    """
    return FastMCP("test-server")


@pytest.fixture
def pg_query_fn(mcp: FastMCP, monkeypatch):
    """
    Register pg_query tool and return its callable function.

    Database access is mocked before tool registration so that
    the tool binds to the mocked connection.
    """
    _mock_db(monkeypatch)
    register_tools(mcp)
    return mcp._tool_manager._tools["pg_query"].fn


@pytest.fixture
def pg_list_schemas_fn(mcp: FastMCP, monkeypatch):
    """Return pg_list_schemas tool function with mocked DB."""
    _mock_db(monkeypatch)
    register_tools(mcp)
    return mcp._tool_manager._tools["pg_list_schemas"].fn


@pytest.fixture
def pg_list_tables_fn(mcp: FastMCP, monkeypatch):
    """Return pg_list_tables tool function with mocked DB."""
    _mock_db(monkeypatch)
    register_tools(mcp)
    return mcp._tool_manager._tools["pg_list_tables"].fn


@pytest.fixture
def pg_describe_table_fn(mcp: FastMCP, monkeypatch):
    """Return pg_describe_table tool function with mocked DB."""
    _mock_db(monkeypatch)
    register_tools(mcp)
    return mcp._tool_manager._tools["pg_describe_table"].fn


@pytest.fixture
def pg_explain_fn(mcp: FastMCP, monkeypatch):
    """Return pg_explain tool function with mocked DB."""
    _mock_db(monkeypatch)
    register_tools(mcp)
    return mcp._tool_manager._tools["pg_explain"].fn


# ============================================================================
# Database Mocking
# ============================================================================

def _mock_db(monkeypatch):
    """
    Mock psycopg database connection and cursor.

    This prevents:
    - Any real network/database access
    - Environment-specific failures
    - Flaky tests due to DB state

    The mock implements only the minimal surface area required
    by the PostgreSQL MCP tools.
    """

    class FakeCursor:
        """
        Minimal psycopg-like cursor implementation.

        - `description` mimics cursor.description for SELECT queries
        - `fetchmany` returns a fixed row set
        - `fetchall` is reused by schema/table listing tools
        """
        description = [type("D", (), {"name": "col"})]

        def execute(self, *args, **kwargs):
            pass

        def fetchmany(self, n):
            return [["value"]]

        def fetchall(self):
            return [
                ("public",),
                ("example_schema",),
            ]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeConn:
        """
        Minimal psycopg-like connection.

        Supports context manager usage and cursor creation.
        """
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        "aden_tools.tools.postgres_tool.db.connection.get_connection",
        lambda: FakeConn(),
    )

class TestPgQuery:
    """Tests for the pg_query MCP tool."""

    def test_simple_select(self, pg_query_fn):
        """
        Basic SELECT query should succeed and return rows + columns.
        """
        result = pg_query_fn(sql="SELECT 1")

        assert result["success"] is True
        assert result["row_count"] == 1
        assert isinstance(result["columns"], list)
        assert isinstance(result["rows"], list)

    def test_invalid_sql_returns_error(self, pg_query_fn, monkeypatch):
        """
        SQL rejected by the validator should return a safe error response.
        """
        monkeypatch.setattr(
            "aden_tools.tools.postgres_tool.security.sql_guard.validate_sql",
            lambda _: (_ for _ in ()).throw(ValueError("Invalid SQL")),
        )

        result = pg_query_fn(sql="DROP TABLE x")

        assert result["success"] is False
        assert "error" in result

    def test_query_timeout(self, pg_query_fn, monkeypatch):
        """
        psycopg QueryCanceled exception should be converted
        into a user-friendly timeout error.
        """

        class TimeoutCursor:
            def execute(self, *args, **kwargs):
                raise psycopg.errors.QueryCanceled()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        class TimeoutConn:
            def cursor(self):
                return TimeoutCursor()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(
            "aden_tools.tools.postgres_tool.db.connection.get_connection",
            lambda: TimeoutConn(),
        )

        result = pg_query_fn(sql="SELECT pg_sleep(10)")

        assert result["success"] is False
        assert "timed out" in result["error"].lower()

class TestPgListSchemas:
    """Tests for pg_list_schemas MCP tool."""

    def test_list_schemas_success(self, pg_list_schemas_fn):
        result = pg_list_schemas_fn()

        assert result["success"] is True
        assert isinstance(result["result"], list)
        assert all(isinstance(x, str) for x in result["result"])

class TestPgListTables:
    """Tests for pg_list_tables MCP tool."""

    def test_list_tables_all(self, pg_list_tables_fn):
        result = pg_list_tables_fn()

        assert result["success"] is True
        assert isinstance(result["result"], list)

    def test_list_tables_with_schema(self, pg_list_tables_fn):
        result = pg_list_tables_fn(schema="any_schema")

        assert result["success"] is True
        assert isinstance(result["result"], list)

class TestPgDescribeTable:
    """Tests for pg_describe_table MCP tool."""

    def test_describe_table_success(self, pg_describe_table_fn, monkeypatch):
        """
        Describe table should return structured column metadata
        regardless of actual schema/table name.
        """

        class DescribeCursor:
            def execute(self, *args, **kwargs):
                pass

            def fetchall(self):
                return [
                    ("col_a", "bigint", False, None),
                    ("col_b", "text", True, "default"),
                ]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        class DescribeConn:
            def cursor(self):
                return DescribeCursor()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(
            "aden_tools.tools.postgres_tool.postgres_tool.get_connection",
            lambda: DescribeConn(),
        )

        result = pg_describe_table_fn(
            schema="any_schema",
            table="any_table",
        )

        assert result["success"] is True
        assert isinstance(result["result"], list)
        assert len(result["result"]) == 2

        column = result["result"][0]
        assert set(column.keys()) == {"column", "type", "nullable", "default"}
        assert isinstance(column["column"], str)
        assert isinstance(column["type"], str)
        assert isinstance(column["nullable"], bool)


class TestPgExplain:
    """Tests for pg_explain MCP tool."""

    def test_explain_success(self, pg_explain_fn):
        result = pg_explain_fn(sql="SELECT 1")

        assert result["success"] is True
        assert isinstance(result["result"], list)

    def test_explain_invalid_sql(self, pg_explain_fn, monkeypatch):
        """
        Invalid SQL should be rejected before EXPLAIN execution.
        """
        monkeypatch.setattr(
            "aden_tools.tools.postgres_tool.security.sql_guard.validate_sql",
            lambda _: (_ for _ in ()).throw(ValueError("Invalid SQL")),
        )

        result = pg_explain_fn(sql="DELETE FROM x")

        assert result["success"] is False
        assert "error" in result
