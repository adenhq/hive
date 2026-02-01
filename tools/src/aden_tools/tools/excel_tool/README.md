# Excel Tool

Read and manipulate Excel files (.xlsx, .xlsm, .xls) for agents.

## Features

- Read Excel files with pagination and sheet selection
- Write new Excel workbooks
- Append rows to existing files
- Get file metadata (sheets, columns, row counts)
- List all sheets in a workbook
- Convert Excel sheets to CSV format

## Tools

### `excel_read`

Read an Excel file and return its contents.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `str` | Yes | Path to Excel file (relative to session sandbox) |
| `workspace_id` | `str` | Yes | Workspace identifier |
| `agent_id` | `str` | Yes | Agent identifier |
| `session_id` | `str` | Yes | Session identifier |
| `sheet_name` | `str` | No | Sheet to read (default: first sheet) |
| `limit` | `int` | No | Max rows to return (default: all) |
| `offset` | `int` | No | Rows to skip from beginning (default: 0) |

**Returns:**
```json
{
  "success": true,
  "path": "data/report.xlsx",
  "sheet_name": "Sales",
  "columns": ["Date", "Amount", "Customer"],
  "column_count": 3,
  "rows": [
    {"Date": "2024-01-01", "Amount": 100, "Customer": "Acme Corp"},
    {"Date": "2024-01-02", "Amount": 200, "Customer": "Tech Inc"}
  ],
  "row_count": 2,
  "total_rows": 100,
  "offset": 0,
  "limit": null
}
```

### `excel_write`

Write data to a new Excel file.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `str` | Yes | Path for new Excel file |
| `workspace_id` | `str` | Yes | Workspace identifier |
| `agent_id` | `str` | Yes | Agent identifier |
| `session_id` | `str` | Yes | Session identifier |
| `columns` | `list[str]` | Yes | Column names for header |
| `rows` | `list[dict]` | Yes | Data rows as dictionaries |
| `sheet_name` | `str` | No | Sheet name (default: "Sheet1") |

**Returns:**
```json
{
  "success": true,
  "path": "output/results.xlsx",
  "sheet_name": "Sheet1",
  "columns": ["Name", "Score"],
  "column_count": 2,
  "rows_written": 50
}
```

### `excel_append`

Append rows to an existing Excel file.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `str` | Yes | Path to existing Excel file |
| `workspace_id` | `str` | Yes | Workspace identifier |
| `agent_id` | `str` | Yes | Agent identifier |
| `session_id` | `str` | Yes | Session identifier |
| `rows` | `list[dict]` | Yes | Rows to append (keys match existing columns) |
| `sheet_name` | `str` | No | Sheet to append to (default: first sheet) |

**Returns:**
```json
{
  "success": true,
  "path": "data/sales.xlsx",
  "sheet_name": "Q1",
  "rows_appended": 10,
  "total_rows": 110
}
```

### `excel_info`

Get metadata about an Excel file without reading all data.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `str` | Yes | Path to Excel file |
| `workspace_id` | `str` | Yes | Workspace identifier |
| `agent_id` | `str` | Yes | Agent identifier |
| `session_id` | `str` | Yes | Session identifier |

**Returns:**
```json
{
  "success": true,
  "path": "data/report.xlsx",
  "file_size_bytes": 45678,
  "sheet_count": 3,
  "sheets": [
    {
      "sheet_name": "Sales",
      "columns": ["Date", "Amount"],
      "column_count": 2,
      "total_rows": 100
    },
    {
      "sheet_name": "Costs",
      "columns": ["Date", "Expense"],
      "column_count": 2,
      "total_rows": 75
    }
  ]
}
```

### `excel_sheet_list`

List all sheet names in an Excel workbook.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `str` | Yes | Path to Excel file |
| `workspace_id` | `str` | Yes | Workspace identifier |
| `agent_id` | `str` | Yes | Agent identifier |
| `session_id` | `str` | Yes | Session identifier |

**Returns:**
```json
{
  "success": true,
  "path": "data/report.xlsx",
  "sheets": ["Sales", "Costs", "Summary"],
  "sheet_count": 3
}
```

### `excel_to_csv`

Convert an Excel sheet to CSV format.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `str` | Yes | Path to Excel file |
| `workspace_id` | `str` | Yes | Workspace identifier |
| `agent_id` | `str` | Yes | Agent identifier |
| `session_id` | `str` | Yes | Session identifier |
| `output_path` | `str` | Yes | Path for output CSV file |
| `sheet_name` | `str` | No | Sheet to convert (default: first sheet) |

**Returns:**
```json
{
  "success": true,
  "input_path": "data/report.xlsx",
  "output_path": "data/report.csv",
  "sheet_name": "Sales",
  "rows_written": 100
}
```

## Dependencies

- `openpyxl` - For reading and writing .xlsx and .xlsm files

Install with:
```bash
pip install openpyxl
```

## Use Cases

- **Report Processing**: Read Excel reports from external systems
- **Data Export**: Generate Excel files for stakeholders
- **Workflow Automation**: Automate data entry involving spreadsheets
- **Format Conversion**: Convert between Excel and CSV formats
- **Multi-Sheet Operations**: Work with complex workbooks containing multiple sheets

## Error Handling

All tools return error dictionaries instead of raising exceptions:

```json
{
  "error": "File not found: data/missing.xlsx"
}
```

Common error cases:
- File not found
- Invalid file extension
- Missing openpyxl dependency
- Sheet not found in workbook
- Empty files or invalid data

## Security

All file paths are validated through `get_secure_path()` to ensure files are within the session sandbox and prevent path traversal attacks.

## Example Agent Usage

```python
# Read Excel data
result = excel_read(
    path="reports/sales_2024.xlsx",
    workspace_id="ws_123",
    agent_id="agent_456",
    session_id="session_789",
    sheet_name="Q1"
)

# Write processed data
excel_write(
    path="output/summary.xlsx",
    workspace_id="ws_123",
    agent_id="agent_456",
    session_id="session_789",
    columns=["Product", "Total"],
    rows=[
        {"Product": "Widget", "Total": 1000},
        {"Product": "Gadget", "Total": 1500}
    ]
)

# Convert to CSV for further processing
excel_to_csv(
    path="output/summary.xlsx",
    workspace_id="ws_123",
    agent_id="agent_456",
    session_id="session_789",
    output_path="output/summary.csv"
)
```
