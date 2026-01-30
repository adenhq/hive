# Excel Tool

Read and manipulate Excel files (.xlsx, .xlsm) within the Aden agent framework.

## Installation

The Excel tool requires `openpyxl`. Install it with:

```bash
pip install openpyxl
# or
pip install tools[excel]
```

## Available Functions

### `excel_read`

Read data from an Excel file.

**Parameters:**
- `path` (str): Path to the Excel file (relative to session sandbox)
- `workspace_id` (str): Workspace identifier
- `agent_id` (str): Agent identifier
- `session_id` (str): Session identifier
- `sheet` (str, optional): Sheet name to read (default: active sheet)
- `limit` (int, optional): Maximum number of rows to return
- `offset` (int, optional): Number of rows to skip from the beginning

**Returns:**
```python
{
    "success": True,
    "path": "data.xlsx",
    "sheet_name": "Sheet1",
    "columns": ["name", "age", "city"],
    "column_count": 3,
    "rows": [
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25, "city": "LA"}
    ],
    "row_count": 2,
    "total_rows": 2,
    "offset": 0,
    "limit": None
}
```

**Example:**
```python
# Read all data from the active sheet
result = excel_read(
    path="employees.xlsx",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789"
)

# Read specific sheet with pagination
result = excel_read(
    path="data.xlsx",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789",
    sheet="Q4 Sales",
    limit=100,
    offset=50
)
```

### `excel_write`

Write data to a new Excel file.

**Parameters:**
- `path` (str): Path to the Excel file
- `workspace_id` (str): Workspace identifier
- `agent_id` (str): Agent identifier
- `session_id` (str): Session identifier
- `columns` (list[str]): List of column names for the header
- `rows` (list[dict]): List of dictionaries, each representing a row
- `sheet` (str, optional): Sheet name (default: "Sheet1")

**Returns:**
```python
{
    "success": True,
    "path": "output.xlsx",
    "sheet_name": "Sheet1",
    "columns": ["name", "age"],
    "column_count": 2,
    "rows_written": 3
}
```

**Example:**
```python
result = excel_write(
    path="output.xlsx",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789",
    columns=["name", "age", "department"],
    rows=[
        {"name": "Alice", "age": 30, "department": "Engineering"},
        {"name": "Bob", "age": 25, "department": "Marketing"}
    ],
    sheet="Employees"
)
```

### `excel_append`

Append rows to an existing Excel file.

**Parameters:**
- `path` (str): Path to the Excel file
- `workspace_id` (str): Workspace identifier
- `agent_id` (str): Agent identifier
- `session_id` (str): Session identifier
- `rows` (list[dict]): List of dictionaries to append
- `sheet` (str, optional): Sheet name to append to (default: active sheet)

**Returns:**
```python
{
    "success": True,
    "path": "data.xlsx",
    "sheet_name": "Sheet1",
    "rows_appended": 2,
    "total_rows": 10
}
```

**Example:**
```python
result = excel_append(
    path="employees.xlsx",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789",
    rows=[
        {"name": "Charlie", "age": 35, "department": "Sales"},
        {"name": "Diana", "age": 28, "department": "HR"}
    ]
)
```

### `excel_info`

Get metadata about an Excel file without reading all data.

**Parameters:**
- `path` (str): Path to the Excel file
- `workspace_id` (str): Workspace identifier
- `agent_id` (str): Agent identifier
- `session_id` (str): Session identifier

**Returns:**
```python
{
    "success": True,
    "path": "data.xlsx",
    "file_size_bytes": 12345,
    "sheet_count": 3,
    "sheet_names": ["Employees", "Products", "Summary"],
    "sheets": [
        {
            "name": "Employees",
            "columns": ["id", "name", "department"],
            "column_count": 3,
            "row_count": 100
        },
        ...
    ]
}
```

**Example:**
```python
result = excel_info(
    path="report.xlsx",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789"
)

print(f"File has {result['sheet_count']} sheets")
for sheet in result['sheets']:
    print(f"  - {sheet['name']}: {sheet['row_count']} rows")
```

### `excel_sheet_list`

List all sheet names in an Excel file.

**Parameters:**
- `path` (str): Path to the Excel file
- `workspace_id` (str): Workspace identifier
- `agent_id` (str): Agent identifier
- `session_id` (str): Session identifier

**Returns:**
```python
{
    "success": True,
    "path": "data.xlsx",
    "sheet_names": ["Sheet1", "Sheet2", "Summary"],
    "sheet_count": 3
}
```

**Example:**
```python
result = excel_sheet_list(
    path="workbook.xlsx",
    workspace_id="ws-123",
    agent_id="agent-456",
    session_id="session-789"
)

for sheet in result['sheet_names']:
    print(f"Found sheet: {sheet}")
```

## Error Handling

All functions return a dict with an `error` key if something goes wrong:

```python
{
    "error": "File not found: missing.xlsx"
}
```

Common errors:
- File not found
- Invalid file extension (must be .xlsx or .xlsm)
- Sheet not found (when specifying a sheet that doesn't exist)
- Empty columns (when writing)
- Path traversal attempt (security)

## Security

- All file operations are sandboxed within the session directory
- Path traversal attacks are blocked
- Files are validated for correct extension before processing

## Supported Formats

- `.xlsx` - Excel 2007+ format (recommended)
- `.xlsm` - Excel 2007+ with macros

Note: The tool uses `openpyxl` which does not support the older `.xls` format. Convert legacy files to `.xlsx` before use.
