"""Excel Tool - Read and manipulate Excel (.xlsx) files."""

import os
from typing import Any

from fastmcp import FastMCP

from ..file_system_toolkits.security import get_secure_path


def register_tools(mcp: FastMCP) -> None:
    """Register Excel tools with the MCP server."""

    @mcp.tool()
    def excel_read(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        sheet_name: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict:
        """
        Read an Excel file and return its contents.

        Use this when you need to extract data from Excel spreadsheets (.xlsx files).
        Supports reading specific sheets by name, pagination with limit/offset.

        Args:
            path: Path to the Excel file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier
            sheet_name: Name of the sheet to read (default: first sheet)
            limit: Maximum number of rows to return (None = all rows)
            offset: Number of rows to skip from the beginning (default: 0)

        Returns:
            dict with success status, data, and metadata including:
            - sheet_name: Name of the sheet read
            - columns: List of column headers
            - rows: List of row data as dictionaries
            - row_count: Number of rows returned
            - total_rows: Total rows in the sheet

        Examples:
            # Read all data from first sheet
            excel_read(path="data.xlsx", workspace_id="ws1", agent_id="agent1", session_id="sess1")

            # Read specific sheet
            excel_read(path="data.xlsx", sheet_name="Sales", ...)

            # Paginate results (skip 100 rows, return next 50)
            excel_read(path="data.xlsx", offset=100, limit=50, ...)
        """
        if offset < 0 or (limit is not None and limit < 0):
            return {"error": "offset and limit must be non-negative"}

        try:
            import openpyxl
        except ImportError:
            return {
                "error": (
                    "openpyxl not installed. Install with: "
                    "pip install openpyxl  or  pip install tools[excel]"
                )
            }

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)

            if not os.path.exists(secure_path):
                return {"error": f"File not found: {path}"}

            if not path.lower().endswith(".xlsx"):
                return {"error": "File must have .xlsx extension"}

            # Load workbook
            wb = openpyxl.load_workbook(secure_path, read_only=True, data_only=True)

            # Get sheet
            if sheet_name:
                if sheet_name not in wb.sheetnames:
                    return {
                        "error": f"Sheet '{sheet_name}' not found. "
                        f"Available sheets: {', '.join(wb.sheetnames)}"
                    }
                ws = wb[sheet_name]
            else:
                ws = wb.active
                sheet_name = ws.title

            # Get headers from first row
            rows_iter = ws.iter_rows(values_only=True)
            try:
                headers = next(rows_iter)
            except StopIteration:
                return {"error": "Excel file is empty or has no headers"}

            # Filter out None headers (can happen with empty columns)
            columns = [str(h) if h is not None else f"Column_{i}" for i, h in enumerate(headers)]

            # Apply offset and limit
            rows = []
            row_idx = 0
            for row_data in rows_iter:
                if row_idx < offset:
                    row_idx += 1
                    continue
                if limit is not None and len(rows) >= limit:
                    break

                # Create row dict, handling None values
                row_dict = {}
                for i, cell_value in enumerate(row_data):
                    if i < len(columns):
                        # Convert value to string for consistency
                        if cell_value is not None:
                            row_dict[columns[i]] = str(cell_value)
                        else:
                            row_dict[columns[i]] = ""

                # Only include rows that have at least one non-empty value
                if any(row_dict.values()):
                    rows.append(row_dict)

                row_idx += 1

            # Count total rows (approximate from iterator)
            total_rows = row_idx - offset + len(rows) if limit is None else row_idx

            wb.close()

            return {
                "success": True,
                "path": path,
                "sheet_name": sheet_name,
                "columns": columns,
                "column_count": len(columns),
                "rows": rows,
                "row_count": len(rows),
                "total_rows": total_rows,
                "offset": offset,
                "limit": limit,
            }

        except Exception as e:
            return {"error": f"Failed to read Excel: {str(e)}"}

    @mcp.tool()
    def excel_write(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        columns: list[str],
        rows: list[dict],
        sheet_name: str = "Sheet1",
    ) -> dict:
        """
        Write data to a new Excel (.xlsx) file.

        Use this when you need to create Excel spreadsheets from data.
        Creates a new .xlsx file with the specified columns and rows.

        Args:
            path: Path to the Excel file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier
            columns: List of column names for the header row
            rows: List of dictionaries, each representing a row
            sheet_name: Name for the sheet (default: "Sheet1")

        Returns:
            dict with success status and metadata including:
            - sheet_name: Name of the created sheet
            - columns: List of column headers
            - rows_written: Number of rows written

        Examples:
            # Create simple Excel file
            excel_write(
                path="output.xlsx",
                columns=["Name", "Age", "City"],
                rows=[
                    {"Name": "Alice", "Age": 30, "City": "NYC"},
                    {"Name": "Bob", "Age": 25, "City": "LA"}
                ],
                ...
            )

            # Create with custom sheet name
            excel_write(path="sales.xlsx", sheet_name="Q1 Sales", ...)
        """
        try:
            import openpyxl
        except ImportError:
            return {
                "error": (
                    "openpyxl not installed. Install with: "
                    "pip install openpyxl  or  pip install tools[excel]"
                )
            }

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)

            if not path.lower().endswith(".xlsx"):
                return {"error": "File must have .xlsx extension"}

            if not columns:
                return {"error": "columns cannot be empty"}

            # Create parent directories if needed
            parent_dir = os.path.dirname(secure_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            # Create workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = sheet_name

            # Write headers
            for col_idx, col_name in enumerate(columns, start=1):
                ws.cell(row=1, column=col_idx, value=col_name)

            # Write data rows
            for row_idx, row_data in enumerate(rows, start=2):
                for col_idx, col_name in enumerate(columns, start=1):
                    value = row_data.get(col_name, "")
                    # Handle different data types
                    if value is None:
                        cell_value = ""
                    elif isinstance(value, (int, float, bool)):
                        cell_value = value
                    else:
                        cell_value = str(value)
                    ws.cell(row=row_idx, column=col_idx, value=cell_value)

            # Save workbook
            wb.save(secure_path)
            wb.close()

            return {
                "success": True,
                "path": path,
                "sheet_name": sheet_name,
                "columns": columns,
                "column_count": len(columns),
                "rows_written": len(rows),
            }

        except Exception as e:
            return {"error": f"Failed to write Excel: {str(e)}"}

    @mcp.tool()
    def excel_info(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
    ) -> dict:
        """
        Get metadata about an Excel file without reading all data.

        Use this to check file structure, sheet names, and row/column counts
        before reading the full file.

        Args:
            path: Path to the Excel file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier

        Returns:
            dict with file metadata including:
            - sheet_names: List of all sheet names in the workbook
            - active_sheet: Name of the currently active sheet
            - columns: List of column headers from the active sheet
            - column_count: Number of columns
            - total_rows: Total number of data rows (approximate for large files)
            - file_size_bytes: Size of the file in bytes

        Examples:
            # Check file structure before reading
            excel_info(path="data.xlsx", ...)
            # Returns: sheet names, column headers, row counts
        """
        try:
            import openpyxl
        except ImportError:
            return {
                "error": (
                    "openpyxl not installed. Install with: "
                    "pip install openpyxl  or  pip install tools[excel]"
                )
            }

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)

            if not os.path.exists(secure_path):
                return {"error": f"File not found: {path}"}

            if not path.lower().endswith(".xlsx"):
                return {"error": "File must have .xlsx extension"}

            # Get file size
            file_size = os.path.getsize(secure_path)

            # Load workbook in read-only mode for efficiency
            wb = openpyxl.load_workbook(secure_path, read_only=True, data_only=True)

            sheet_names = wb.sheetnames
            active_sheet = wb.active.title

            # Get headers and count rows from active sheet
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)

            try:
                headers = next(rows_iter)
                columns = [
                    str(h) if h is not None else f"Column_{i}" for i, h in enumerate(headers)
                ]
            except StopIteration:
                columns = []

            # Count total rows (approximate)
            total_rows = sum(1 for _ in rows_iter)

            wb.close()

            return {
                "success": True,
                "path": path,
                "sheet_names": sheet_names,
                "active_sheet": active_sheet,
                "columns": columns,
                "column_count": len(columns),
                "total_rows": total_rows,
                "file_size_bytes": file_size,
            }

        except Exception as e:
            return {"error": f"Failed to get Excel info: {str(e)}"}
