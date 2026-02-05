"""
Excel Tool - Read, write, and manipulate Excel files.

Provides functionality to work with Excel files (.xlsx, .xls) including:
- Reading data from Excel files with sheet selection
- Writing data to Excel files
- Appending data to existing Excel files
- Getting information about Excel file structure
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register Excel tools with the MCP server."""

    @mcp.tool()
    def excel_read(
        file_path: str,
        sheet_name: Optional[str] = None,
        sheet_index: Optional[int] = None,
        header: int = 0,
        usecols: Optional[Union[List[int], List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Read data from an Excel file.

        Args:
            file_path: Path to the Excel file (.xlsx or .xls)
            sheet_name: Name of the sheet to read (optional, defaults to first sheet)
            sheet_index: Index of the sheet to read (optional, defaults to first sheet)
            header: Row to use as column names (default 0)
            usecols: Columns to read (by index or name)

        Returns:
            Dict with 'data' containing the DataFrame as dict, 'sheet_names', and 'shape'
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"error": f"File does not exist: {file_path}"}

            # Get sheet names first
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            # Determine which sheet to read
            if sheet_name is not None:
                if sheet_name not in sheet_names:
                    return {"error": f"Sheet '{sheet_name}' not found. Available sheets: {sheet_names}"}
                sheet_to_read = sheet_name
            elif sheet_index is not None:
                if sheet_index >= len(sheet_names):
                    return {"error": f"Sheet index {sheet_index} out of range. Available indices: 0-{len(sheet_names)-1}"}
                sheet_to_read = sheet_names[sheet_index]
            else:
                # Default to first sheet
                sheet_to_read = sheet_names[0]

            # Read the specified sheet
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_to_read,
                header=header,
                usecols=usecols
            )

            # Convert DataFrame to dictionary for JSON serialization
            data_dict = df.to_dict(orient='records')

            return {
                "data": data_dict,
                "sheet_names": sheet_names,
                "selected_sheet": sheet_to_read,
                "shape": [len(data_dict), len(df.columns)],
                "columns": df.columns.tolist(),
            }

        except Exception as e:
            return {"error": f"Failed to read Excel file: {str(e)}"}

    @mcp.tool()
    def excel_write(
        data: List[Dict[str, Any]],
        file_path: str,
        sheet_name: str = "Sheet1",
        mode: str = "w",  # 'w' for write, 'a' for append
        start_row: int = 0,
        if_sheet_exists: str = "replace",  # For append mode
    ) -> Dict[str, Any]:
        """
        Write data to an Excel file.

        Args:
            data: List of dictionaries representing rows to write
            file_path: Path to the Excel file to create/write
            sheet_name: Name of the sheet to write to
            mode: 'w' to overwrite file, 'a' to append to existing file
            start_row: Starting row for writing (for append mode)
            if_sheet_exists: Action when sheet exists in append mode ('new', 'replace', 'overlay')

        Returns:
            Dict with success status and file information
        """
        try:
            file_path = Path(file_path)
            
            # Convert data to DataFrame
            if not data:
                df = pd.DataFrame()
            else:
                df = pd.DataFrame(data)

            # Handle directory creation
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to Excel file
            if mode == "w" or not file_path.exists():
                # Write mode - create new file or overwrite
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=start_row)
            else:
                # Append mode - add to existing file
                with pd.ExcelWriter(
                    file_path, 
                    engine='openpyxl',
                    mode='a',
                    if_sheet_exists=if_sheet_exists
                ) as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=start_row)

            return {
                "success": True,
                "file_path": str(file_path),
                "rows_written": len(df),
                "sheet_name": sheet_name,
            }

        except Exception as e:
            return {"error": f"Failed to write Excel file: {str(e)}"}

    @mcp.tool()
    def excel_append(
        data: List[Dict[str, Any]],
        file_path: str,
        sheet_name: str = "Sheet1",
    ) -> Dict[str, Any]:
        """
        Append data to an existing Excel file.

        Args:
            data: List of dictionaries representing rows to append
            file_path: Path to the existing Excel file
            sheet_name: Name of the sheet to append to

        Returns:
            Dict with success status and file information
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"error": f"File does not exist: {file_path}"}

            # Convert data to DataFrame
            if not data:
                return {"error": "No data provided to append"}

            df_new = pd.DataFrame(data)

            # Read existing data to determine where to append
            try:
                existing_df = pd.read_excel(file_path, sheet_name=sheet_name)
                start_row = len(existing_df) + 1  # +1 for header
            except ValueError:
                # Sheet doesn't exist, start at row 0
                start_row = 1  # Start after header row

            # Append to Excel file
            with pd.ExcelWriter(
                file_path,
                engine='openpyxl',
                mode='a',
                if_sheet_exists='overlay'  # Overlay onto existing sheet
            ) as writer:
                df_new.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False,
                    startrow=start_row,
                    header=False  # Don't write header again
                )

            return {
                "success": True,
                "file_path": str(file_path),
                "rows_appended": len(df_new),
                "sheet_name": sheet_name,
                "start_row": start_row,
            }

        except Exception as e:
            return {"error": f"Failed to append to Excel file: {str(e)}"}

    @mcp.tool()
    def excel_info(file_path: str) -> Dict[str, Any]:
        """
        Get information about an Excel file structure.

        Args:
            file_path: Path to the Excel file

        Returns:
            Dict with file information including sheet names, dimensions, etc.
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"error": f"File does not exist: {file_path}"}

            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            info = {
                "file_path": str(file_path),
                "sheet_count": len(sheet_names),
                "sheet_names": sheet_names,
                "sheets_info": {}
            }

            # Get info for each sheet
            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=5)  # Read first 5 rows for sample
                    info["sheets_info"][sheet_name] = {
                        "rows": len(df),
                        "columns": len(df.columns),
                        "column_names": df.columns.tolist(),
                        "sample_data": df.head().to_dict(orient='records')
                    }
                except Exception as e:
                    info["sheets_info"][sheet_name] = {
                        "error": f"Could not read sheet: {str(e)}"
                    }

            return info

        except Exception as e:
            return {"error": f"Failed to get Excel file info: {str(e)}"}

    @mcp.tool()
    def excel_list_files(directory: str = ".") -> Dict[str, Any]:
        """
        List Excel files in a directory.

        Args:
            directory: Directory to search for Excel files (default current directory)

        Returns:
            Dict with list of Excel files found
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists() or not dir_path.is_dir():
                return {"error": f"Directory does not exist: {directory}"}

            excel_extensions = ['.xlsx', '.xls', '.xlsm', '.xlsb']
            excel_files = []

            for ext in excel_extensions:
                excel_files.extend(list(dir_path.glob(f"*{ext}")))
                excel_files.extend(list(dir_path.glob(f"**/*{ext}")))  # Recursive search

            # Convert to relative paths and sort
            excel_files = [str(f.relative_to(dir_path)) for f in excel_files]
            excel_files.sort()

            return {
                "directory": str(dir_path),
                "excel_files": excel_files,
                "count": len(excel_files)
            }

        except Exception as e:
            return {"error": f"Failed to list Excel files: {str(e)}"}