''' parquet_tool - Tools for inspecting and querying Parquet files using DuckDB.
    Requires DuckDB to be installed in the environment: uv pip install duckdb
    
    supports: - parquet_info: Get schema and metadata about a Parquet file or folder
              - parquet_preview: Preview rows from a Parquet file with optional filtering
              - parquet_query: Execute SQL query on a Parquet file (powered by DuckDB)


'''

from __future__ import annotations

import os

from fastmcp import FastMCP

from ..file_system_toolkits.security import get_secure_path

MAX_PREVIEW_ROWS = 20
MAX_QUERY_ROWS = 200
MAX_CELL_LENGTH = 1000


def register_tools(mcp: FastMCP) -> None:
    """Register Parquet tools with the MCP server."""

    @mcp.tool()
    def parquet_info(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
    ) -> dict:
        """
        Get schema and metadata about a Parquet file or folder.

        Args:
            path: Path to Parquet file or folder (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier

        Returns:
            dict with schema (columns + types) and metadata
        """
        try:
            import duckdb
        except ImportError:
            return {"error": "DuckDB not installed. Install with: uv pip install duckdb"}

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)

            if not os.path.exists(secure_path):
                return {"error": f"File or folder not found: {path}"}

            con = duckdb.connect(":memory:")
            try:
                result = con.execute(
                    f"SELECT * FROM read_parquet('{secure_path}/**/*.parquet') LIMIT 0"
                ).description
                columns = [{"name": col[0], "type": str(col[1])} for col in result]

                try:
                    count_result = con.execute(
                        f"SELECT COUNT(*) FROM read_parquet('{secure_path}/**/*.parquet')"
                    ).fetchone()
                    row_count = count_result[0] if count_result else None
                except Exception:
                    row_count = None

                if os.path.isdir(secure_path):
                    file_count = sum(
                        1
                        for root, _, files in os.walk(secure_path)
                        for f in files
                        if f.endswith(".parquet")
                    )
                else:
                    file_count = 1

                return {
                    "success": True,
                    "path": path,
                    "columns": columns,
                    "column_count": len(columns),
                    "row_count": row_count,
                    "file_count": file_count,
                }
            finally:
                con.close()

        except Exception as e:
            return {"error": f"Failed to read Parquet info: {str(e)}"}

    @mcp.tool()
    def parquet_preview(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        limit: int = MAX_PREVIEW_ROWS,
        columns: list[str] | None = None,
        where: str | None = None,
    ) -> dict:
        """
        Preview rows from a Parquet file with optional filtering.

        Args:
            path: Path to Parquet file or folder (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier
            limit: Maximum rows to return (default 20, max 20)
            columns: List of column names to select (None = all columns)
            where: SQL WHERE clause for filtering (e.g., "price > 100")

        Returns:
            dict with preview data and metadata
        """
        try:
            import duckdb
        except ImportError:
            return {"error": "DuckDB not installed. Install with: uv pip install duckdb"}

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)

            if not os.path.exists(secure_path):
                return {"error": f"File or folder not found: {path}"}

            if limit < 1 or limit > MAX_PREVIEW_ROWS:
                limit = MAX_PREVIEW_ROWS

            con = duckdb.connect(":memory:")
            try:
                col_str = "*" if not columns else ", ".join(columns)
                query = f"SELECT {col_str} FROM read_parquet('{secure_path}/**/*.parquet')"
                if where:
                    query += f" WHERE {where}"
                query += f" LIMIT {limit}"

                result = con.execute(query)
                col_names = [desc[0] for desc in result.description]
                rows = result.fetchall()

                rows_as_dicts = []
                for row in rows:
                    row_dict = {}
                    for col, val in zip(col_names, row, strict=False):
                        if isinstance(val, str) and len(val) > MAX_CELL_LENGTH:
                            row_dict[col] = val[:MAX_CELL_LENGTH] + "..."
                        else:
                            row_dict[col] = val
                    rows_as_dicts.append(row_dict)

                return {
                    "success": True,
                    "path": path,
                    "columns": col_names,
                    "rows": rows_as_dicts,
                    "row_count": len(rows_as_dicts),
                    "limit": limit,
                }
            finally:
                con.close()

        except Exception as e:
            return {"error": f"Failed to preview Parquet: {str(e)}"}

    @mcp.tool()
    def parquet_query(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        sql: str,
        limit: int = MAX_QUERY_ROWS,
    ) -> dict:
        """
        Execute SQL query on a Parquet file (powered by DuckDB).

        The Parquet file is loaded as a table named 'data'. Use standard SQL syntax.

        Args:
            path: Path to Parquet file or folder (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier
            sql: SQL query to execute. The Parquet is available as table 'data'.
                 Example: "SELECT * FROM data WHERE price > 100 ORDER BY name LIMIT 10"
            limit: Maximum rows to return (default 200, max 200)

        Returns:
            dict with query results, columns, and row count
        """
        try:
            import duckdb
        except ImportError:
            return {"error": "DuckDB not installed. Install with: uv pip install duckdb"}

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)

            if not os.path.exists(secure_path):
                return {"error": f"File or folder not found: {path}"}

            if not sql or not sql.strip():
                return {"error": "sql cannot be empty"}

            sql_upper = sql.strip().upper()
            if not sql_upper.startswith("SELECT"):
                return {"error": "Only SELECT queries are allowed for security reasons"}

            disallowed = [
                "INSERT",
                "UPDATE",
                "DELETE",
                "DROP",
                "CREATE",
                "ALTER",
                "TRUNCATE",
                "EXEC",
                "EXECUTE",
            ]
            for keyword in disallowed:
                if keyword in sql_upper:
                    return {"error": f"'{keyword}' is not allowed in queries"}

            if limit < 1 or limit > MAX_QUERY_ROWS:
                limit = MAX_QUERY_ROWS

            con = duckdb.connect(":memory:")
            try:
                con.execute(
                    f"CREATE TABLE data AS SELECT * FROM read_parquet('{secure_path}/**/*.parquet')"
                )
                user_sql = sql.strip()
                if "LIMIT" not in sql_upper:
                    user_sql += f" LIMIT {limit}"
                else:
                    user_sql = sql 

                result = con.execute(user_sql)
                col_names = [desc[0] for desc in result.description]
                rows = result.fetchall()[:limit]

                rows_as_dicts = []
                for row in rows:
                    row_dict = {}
                    for col, val in zip(col_names, row, strict=False):
                        if isinstance(val, str) and len(val) > MAX_CELL_LENGTH:
                            row_dict[col] = val[:MAX_CELL_LENGTH] + "..."
                        else:
                            row_dict[col] = val
                    rows_as_dicts.append(row_dict)

                return {
                    "success": True,
                    "path": path,
                    "query": sql,
                    "columns": col_names,
                    "rows": rows_as_dicts,
                    "row_count": len(rows_as_dicts),
                    "limit": limit,
                }
            finally:
                con.close()

        except Exception as e:
            error_msg = str(e)
            if "Catalog Error" in error_msg:
                return {"error": f"SQL error: {error_msg}. Remember the table is named 'data'."}
            return {"error": f"Query failed: {error_msg}"}
