"""CSV Tool - Read and manipulate CSV files with SQL support."""

import csv
import os
from typing import List, Dict, Union, Optional

from fastmcp import FastMCP

from ..file_system_toolkits.security import get_secure_path


def register_tools(mcp: FastMCP) -> None:
    """Register CSV tools with the MCP server."""

    @mcp.tool()
    def csv_read(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> dict:
        """
        Read a CSV file and return its contents.

        Args:
            path: Path to the CSV file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier
            limit: Maximum number of rows to return (None = all rows)
            offset: Number of rows to skip from the beginning
        """
        if offset < 0 or (limit is not None and limit < 0):
            return {"error": "offset and limit must be non-negative"}
        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)

            if not os.path.exists(secure_path):
                return {"error": f"File not found: {path}"}

            if not path.lower().endswith(".csv"):
                return {"error": "File must have .csv extension"}

            with open(secure_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    return {"error": "CSV file is empty or has no headers"}

                columns = list(reader.fieldnames)
                rows = []
                for i, row in enumerate(reader):
                    if i < offset:
                        continue
                    if limit is not None and len(rows) >= limit:
                        break
                    rows.append(row)

            return {
                "success": True,
                "path": path,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }
        except Exception as e:
            return {"error": f"Failed to read CSV: {str(e)}"}

    @mcp.tool()
    def csv_write(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        columns: List[str],
        rows: List[dict],
    ) -> dict:
        """Write data to a new CSV file."""
        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)
            if not path.lower().endswith(".csv"):
                return {"error": "File must have .csv extension"}
            if not columns:
                return {"error": "columns cannot be empty"}

            parent_dir = os.path.dirname(secure_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(secure_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for row in rows:
                    filtered_row = {k: v for k, v in row.items() if k in columns}
                    writer.writerow(filtered_row)

            return {"success": True, "path": path, "rows_written": len(rows)}
        except Exception as e:
            return {"error": f"Failed to write CSV: {str(e)}"}

    @mcp.tool()
    def csv_append(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        rows: List[dict],
    ) -> dict:
        """Append rows to an existing CSV file."""
        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)
            if not os.path.exists(secure_path):
                return {"error": f"File not found: {path}"}

            with open(secure_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                columns = list(reader.fieldnames) if reader.fieldnames else []

            with open(secure_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                for row in rows:
                    filtered_row = {k: v for k, v in row.items() if k in columns}
                    writer.writerow(filtered_row)

            return {"success": True, "rows_appended": len(rows)}
        except Exception as e:
            return {"error": f"Failed to append to CSV: {str(e)}"}

    @mcp.tool()
    def csv_info(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
    ) -> dict:
        """Get metadata (columns, row count) about a CSV file."""
        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)
            file_size = os.path.getsize(secure_path)
            with open(secure_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                columns = list(reader.fieldnames) if reader.fieldnames else []
                total_rows = sum(1 for _ in reader)

            return {
                "success": True,
                "columns": columns,
                "total_rows": total_rows,
                "file_size_bytes": file_size
            }
        except Exception as e:
            return {"error": f"Failed to get info: {str(e)}"}

    @mcp.tool()
    def csv_sql(
        paths: Union[List[str], str],
        workspace_id: str,
        agent_id: str,
        session_id: str,
        query: str,
    ) -> dict:
        """
        Query one or multiple CSV files using SQL (DuckDB).
        Tables are available as 'data0', 'data1', etc. 'data' aliases 'data0'.
        """
        try:
            import duckdb
        except ImportError:
            return {"error": "DuckDB not installed. Run: pip install duckdb"}

        if isinstance(paths, str):
            paths = [paths]

        try:
            if not query or not query.strip():
                return {"error": "query cannot be empty"}

            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                return {"error": "Only SELECT queries are allowed"}

            disallowed = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
            if any(keyword in query_upper for keyword in disallowed):
                return {"error": "DML/DDL commands are not allowed"}

            con = duckdb.connect(":memory:")
            try:
                for i, path in enumerate(paths):
                    secure_path = get_secure_path(path, workspace_id, agent_id, session_id)
                    if not os.path.exists(secure_path):
                        return {"error": f"File not found: {path}"}
                    
                    # Performance: Use VIEW to avoid copying data to RAM
                    table_name = f"data{i}"
                    con.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_csv_auto('{secure_path}')")
                    if i == 0:
                        con.execute(f"CREATE VIEW data AS SELECT * FROM {table_name}")

                result = con.execute(query)
                columns = [desc[0] for desc in result.description]
                rows = result.fetchall()
                rows_as_dicts = [dict(zip(columns, row)) for row in rows]

                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows_as_dicts,
                    "row_count": len(rows_as_dicts),
                    "query": query
                }
            finally:
                con.close()
        except Exception as e:
            return {"error": f"SQL Query failed: {str(e)}"}