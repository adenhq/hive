# Excel Tool

Read and write Excel (.xlsx) spreadsheet files.

## Overview

The Excel tool provides functionality to read, write, and inspect Excel files within the agent sandbox. It supports:

- Reading data from specific sheets or the active sheet
- Writing data to new Excel files with custom columns
- Getting metadata about Excel files (sheet names, dimensions, etc.)
- Pagination support for large files

## Tools

### excel_read

Read an Excel file and return its contents.

**When to use:**
- Extracting data from Excel spreadsheets
- Processing tabular data in .xlsx format
- Reading specific sheets from multi-sheet workbooks

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Path to the Excel file (relative to session sandbox) |
| `workspace_id` | string | Yes | Workspace identifier |
| `agent_id` | string | Yes | Agent identifier |
| `session_id` | string | Yes | Session identifier |
| `sheet_name` | string | No | Name of the sheet to read (default: first/active sheet) |
| `limit` | integer | No | Maximum number of rows to return |
| `offset` | integer | No | Number of rows to skip from the beginning |

**Returns:**
- `success`: Boolean indicating if operation succeeded
- `sheet_name`: Name of the sheet that was read
- `columns`: List of column headers
- `rows`: List of row data as dictionaries
- `row_count`: Number of rows returned
- `total_rows`: Total rows in the sheet
- `error`: Error message if operation failed

**Example:**
```python
# Read all data from first sheet
result = excel_read(
    path="sales_data.xlsx",
    workspace_id="ws1",
    agent_id="agent1",
    session_id="sess1"
)

# Read specific sheet with pagination
result = excel_read(
    path="sales_data.xlsx",
    sheet_name="Q1 Sales",
    offset=100,
    limit=50,
    workspace_id="ws1",
    agent_id="agent1",
    session_id="sess1"
)
```

### excel_write

Write data to a new Excel (.xlsx) file.

**When to use:**
- Creating Excel reports from processed data
- Exporting data in spreadsheet format
- Generating multi-sheet workbooks

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Path to the Excel file (relative to session sandbox) |
| `workspace_id` | string | Yes | Workspace identifier |
| `agent_id` | string | Yes | Agent identifier |
| `session_id` | string | Yes | Session identifier |
| `columns` | list[string] | Yes | List of column names for the header row |
| `rows` | list[dict] | Yes | List of dictionaries, each representing a row |
| `sheet_name` | string | No | Name for the sheet (default: "Sheet1") |

**Returns:**
- `success`: Boolean indicating if operation succeeded
- `sheet_name`: Name of the created sheet
- `columns`: List of column headers
- `rows_written`: Number of rows written
- `error`: Error message if operation failed

**Example:**
```python
result = excel_write(
    path="output.xlsx",
    workspace_id="ws1",
    agent_id="agent1",
    session_id="sess1",
    columns=["Name", "Age", "City"],
    rows=[
        {"Name": "Alice", "Age": 30, "City": "NYC"},
        {"Name": "Bob", "Age": 25, "City": "LA"}
    ],
    sheet_name="Customers"
)
```

### excel_info

Get metadata about an Excel file without reading all data.

**When to use:**
- Checking file structure before processing
- Listing available sheets in a workbook
- Getting row/column counts for planning

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Path to the Excel file (relative to session sandbox) |
| `workspace_id` | string | Yes | Workspace identifier |
| `agent_id` | string | Yes | Agent identifier |
| `session_id` | string | Yes | Session identifier |

**Returns:**
- `success`: Boolean indicating if operation succeeded
- `sheet_names`: List of all sheet names in the workbook
- `active_sheet`: Name of the currently active sheet
- `columns`: List of column headers from the active sheet
- `column_count`: Number of columns
- `total_rows`: Total number of data rows
- `file_size_bytes`: Size of the file in bytes
- `error`: Error message if operation failed

**Example:**
```python
result = excel_info(
    path="data.xlsx",
    workspace_id="ws1",
    agent_id="agent1",
    session_id="sess1"
)
# Returns sheet names, column headers, and row counts
```

## Dependencies

This tool requires `openpyxl`:

```bash
pip install openpyxl
```

Or install with the excel extra:

```bash
pip install tools[excel]
```

## Error Handling

All tools return error dictionaries with descriptive messages:

- File not found errors
- Invalid file extensions (must be .xlsx)
- Missing required parameters
- Missing dependencies (openpyxl not installed)
- Sheet not found errors
- File access outside sandbox (security error)

## Security

- All file paths are resolved within the session sandbox
- Path traversal attempts are blocked
- Only .xlsx files are supported
- Files must be within the workspace/agent/session directory structure

## Limitations

- Only .xlsx format is supported (not .xls or .ods)
- Formula values are read as calculated results, not formulas
- Very large files (>100MB) may require increased memory
- Cell formatting is not preserved when writing
