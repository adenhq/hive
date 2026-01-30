"""Excel Tool - Read and manipulate Excel files (.xlsx, .xlsm)."""

import os
from datetime import datetime
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
        sheet: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict:
        """
        Read an Excel file and return its contents.

        Args:
            path: Path to the Excel file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier
            sheet: Sheet name to read (default: active sheet)
            limit: Maximum number of rows to return (None = all rows)
            offset: Number of rows to skip from the beginning (after header)

        Returns:
            dict with success status, data, and metadata
        """
        try:
            from openpyxl import load_workbook
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

            if not path.lower().endswith((".xlsx", ".xlsm")):
                return {"error": "File must have .xlsx or .xlsm extension"}

            # Load workbook in read-only mode for better performance
            wb = load_workbook(secure_path, read_only=True, data_only=True)

            try:
                # Get the specified sheet or active sheet
                if sheet:
                    if sheet not in wb.sheetnames:
                        return {
                            "error": f"Sheet '{sheet}' not found. Available sheets: {wb.sheetnames}"
                        }
                    ws = wb[sheet]
                else:
                    ws = wb.active

                if ws is None:
                    return {"error": "Workbook has no active sheet"}

                # Read all rows
                all_rows = []
                for row in ws.iter_rows(values_only=True):
                    # Convert cell values to serializable format
                    converted_row = [_convert_cell_value(cell) for cell in row]
                    all_rows.append(converted_row)

                if not all_rows:
                    return {
                        "success": True,
                        "path": path,
                        "sheet_name": ws.title,
                        "columns": [],
                        "column_count": 0,
                        "rows": [],
                        "row_count": 0,
                        "total_rows": 0,
                        "offset": offset,
                        "limit": limit,
                    }

                # First row as headers
                columns = all_rows[0] if all_rows else []
                data_rows = all_rows[1:]  # Rows without header

                # Apply offset and limit to data rows
                total_rows = len(data_rows)
                if offset > 0:
                    data_rows = data_rows[offset:]
                if limit is not None:
                    data_rows = data_rows[:limit]

                # Convert rows to list of dicts with column names as keys
                rows_as_dicts = []
                for row in data_rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i] if i < len(columns) and columns[i] else f"Column_{i+1}"
                        row_dict[str(col_name)] = value
                    rows_as_dicts.append(row_dict)

                return {
                    "success": True,
                    "path": path,
                    "sheet_name": ws.title,
                    "columns": [str(c) if c is not None else f"Column_{i+1}" for i, c in enumerate(columns)],
                    "column_count": len(columns),
                    "rows": rows_as_dicts,
                    "row_count": len(rows_as_dicts),
                    "total_rows": total_rows,
                    "offset": offset,
                    "limit": limit,
                }

            finally:
                wb.close()

        except Exception as e:
            return {"error": f"Failed to read Excel file: {str(e)}"}

    @mcp.tool()
    def excel_write(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        columns: list[str],
        rows: list[dict],
        sheet: str = "Sheet1",
    ) -> dict:
        """
        Write data to a new Excel file.

        Args:
            path: Path to the Excel file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier
            columns: List of column names for the header
            rows: List of dictionaries, each representing a row
            sheet: Name for the sheet (default: "Sheet1")

        Returns:
            dict with success status and metadata
        """
        try:
            from openpyxl import Workbook
        except ImportError:
            return {
                "error": (
                    "openpyxl not installed. Install with: "
                    "pip install openpyxl  or  pip install tools[excel]"
                )
            }

        try:
            secure_path = get_secure_path(path, workspace_id, agent_id, session_id)

            if not path.lower().endswith((".xlsx", ".xlsm")):
                return {"error": "File must have .xlsx or .xlsm extension"}

            if not columns:
                return {"error": "columns cannot be empty"}

            # Create parent directories if needed
            parent_dir = os.path.dirname(secure_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            # Create new workbook
            wb = Workbook()
            ws = wb.active
            if ws is None:
                return {"error": "Failed to create worksheet"}

            ws.title = sheet

            # Write header row
            for col_idx, col_name in enumerate(columns, start=1):
                ws.cell(row=1, column=col_idx, value=col_name)

            # Write data rows
            for row_idx, row_data in enumerate(rows, start=2):
                for col_idx, col_name in enumerate(columns, start=1):
                    value = row_data.get(col_name, "")
                    ws.cell(row=row_idx, column=col_idx, value=value)

            # Save workbook
            wb.save(secure_path)
            wb.close()

            return {
                "success": True,
                "path": path,
                "sheet_name": sheet,
                "columns": columns,
                "column_count": len(columns),
                "rows_written": len(rows),
            }

        except Exception as e:
            return {"error": f"Failed to write Excel file: {str(e)}"}

    @mcp.tool()
    def excel_append(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
        rows: list[dict],
        sheet: str | None = None,
    ) -> dict:
        """
        Append rows to an existing Excel file.

        Args:
            path: Path to the Excel file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier
            rows: List of dictionaries to append, keys should match existing columns
            sheet: Sheet name to append to (default: active sheet)

        Returns:
            dict with success status and metadata
        """
        try:
            from openpyxl import load_workbook
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
                return {"error": f"File not found: {path}. Use excel_write to create a new file."}

            if not path.lower().endswith((".xlsx", ".xlsm")):
                return {"error": "File must have .xlsx or .xlsm extension"}

            if not rows:
                return {"error": "rows cannot be empty"}

            # Load existing workbook
            wb = load_workbook(secure_path)

            # Get the specified sheet or active sheet
            if sheet:
                if sheet not in wb.sheetnames:
                    return {
                        "error": f"Sheet '{sheet}' not found. Available sheets: {wb.sheetnames}"
                    }
                ws = wb[sheet]
            else:
                ws = wb.active

            if ws is None:
                return {"error": "Workbook has no active sheet"}

            # Get existing columns from first row
            columns = []
            for cell in ws[1]:
                columns.append(str(cell.value) if cell.value is not None else "")

            if not columns or all(c == "" for c in columns):
                wb.close()
                return {"error": "Excel file has no headers in the first row"}

            # Find the next empty row
            next_row = ws.max_row + 1

            # Append rows
            for row_data in rows:
                for col_idx, col_name in enumerate(columns, start=1):
                    value = row_data.get(col_name, "")
                    ws.cell(row=next_row, column=col_idx, value=value)
                next_row += 1

            # Save workbook
            wb.save(secure_path)
            wb.close()

            # Get new total row count (excluding header)
            total_rows = next_row - 2  # -1 for header, -1 because next_row was incremented

            return {
                "success": True,
                "path": path,
                "sheet_name": ws.title,
                "rows_appended": len(rows),
                "total_rows": total_rows,
            }

        except Exception as e:
            return {"error": f"Failed to append to Excel file: {str(e)}"}

    @mcp.tool()
    def excel_info(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
    ) -> dict:
        """
        Get metadata about an Excel file without reading all data.

        Args:
            path: Path to the Excel file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier

        Returns:
            dict with file metadata (sheets, columns per sheet, row counts, file size)
        """
        try:
            from openpyxl import load_workbook
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

            if not path.lower().endswith((".xlsx", ".xlsm")):
                return {"error": "File must have .xlsx or .xlsm extension"}

            # Get file size
            file_size = os.path.getsize(secure_path)

            # Load workbook in read-only mode
            wb = load_workbook(secure_path, read_only=True, data_only=True)

            try:
                sheets_info = []
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]

                    # Get columns from first row
                    columns = []
                    first_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
                    if first_row:
                        columns = [str(c) if c is not None else f"Column_{i+1}" for i, c in enumerate(first_row)]

                    # Count rows (excluding header)
                    row_count = 0
                    for _ in ws.iter_rows(min_row=2, values_only=True):
                        row_count += 1

                    sheets_info.append({
                        "name": sheet_name,
                        "columns": columns,
                        "column_count": len(columns),
                        "row_count": row_count,
                    })

                return {
                    "success": True,
                    "path": path,
                    "file_size_bytes": file_size,
                    "sheet_count": len(wb.sheetnames),
                    "sheet_names": wb.sheetnames,
                    "sheets": sheets_info,
                }

            finally:
                wb.close()

        except Exception as e:
            return {"error": f"Failed to get Excel info: {str(e)}"}

    @mcp.tool()
    def excel_sheet_list(
        path: str,
        workspace_id: str,
        agent_id: str,
        session_id: str,
    ) -> dict:
        """
        List all sheet names in an Excel file.

        Args:
            path: Path to the Excel file (relative to session sandbox)
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            session_id: Session identifier

        Returns:
            dict with list of sheet names
        """
        try:
            from openpyxl import load_workbook
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

            if not path.lower().endswith((".xlsx", ".xlsm")):
                return {"error": "File must have .xlsx or .xlsm extension"}

            # Load workbook in read-only mode (minimal memory usage)
            wb = load_workbook(secure_path, read_only=True)

            try:
                return {
                    "success": True,
                    "path": path,
                    "sheet_names": wb.sheetnames,
                    "sheet_count": len(wb.sheetnames),
                }
            finally:
                wb.close()

        except Exception as e:
            return {"error": f"Failed to list sheets: {str(e)}"}


def _convert_cell_value(value: Any) -> Any:
    """Convert Excel cell values to JSON-serializable types."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float, str, bool)):
        return value
    # For any other type, convert to string
    return str(value)
