# Excel Tool

The Excel tool provides functionality to read, write, and manipulate Excel files (.xlsx, .xls) within the Hive framework.

## Functions

### `excel_read`
Read data from an Excel file with options for sheet selection and column filtering.

**Parameters:**
- `file_path`: Path to the Excel file (.xlsx or .xls)
- `sheet_name`: Name of the sheet to read (optional, defaults to first sheet)
- `sheet_index`: Index of the sheet to read (optional, defaults to first sheet)
- `header`: Row to use as column names (default 0)
- `usecols`: Columns to read (by index or name)

**Returns:**
- `data`: The Excel data as a list of dictionaries
- `sheet_names`: List of all sheet names in the file
- `selected_sheet`: The sheet that was read
- `shape`: Dimensions of the data [rows, columns]
- `columns`: Column names

### `excel_write`
Write data to an Excel file, with options for overwrite or append modes.

**Parameters:**
- `data`: List of dictionaries representing rows to write
- `file_path`: Path to the Excel file to create/write
- `sheet_name`: Name of the sheet to write to
- `mode`: 'w' to overwrite file, 'a' to append to existing file
- `start_row`: Starting row for writing (for append mode)
- `if_sheet_exists`: Action when sheet exists in append mode ('new', 'replace', 'overlay')

**Returns:**
- `success`: Boolean indicating success
- `file_path`: Path to the created/written file
- `rows_written`: Number of rows written
- `sheet_name`: Name of the sheet written to

### `excel_append`
Append data to an existing Excel file.

**Parameters:**
- `data`: List of dictionaries representing rows to append
- `file_path`: Path to the existing Excel file
- `sheet_name`: Name of the sheet to append to

**Returns:**
- `success`: Boolean indicating success
- `file_path`: Path to the file
- `rows_appended`: Number of rows appended
- `sheet_name`: Name of the sheet appended to
- `start_row`: Row where appending started

### `excel_info`
Get information about an Excel file structure.

**Parameters:**
- `file_path`: Path to the Excel file

**Returns:**
- `file_path`: Path to the file
- `sheet_count`: Number of sheets in the file
- `sheet_names`: List of all sheet names
- `sheets_info`: Information about each sheet including dimensions and sample data

### `excel_list_files`
List Excel files in a directory.

**Parameters:**
- `directory`: Directory to search for Excel files (default current directory)

**Returns:**
- `directory`: The directory searched
- `excel_files`: List of Excel files found
- `count`: Number of Excel files found

## Usage Examples

### Reading an Excel file
```python
result = excel_read(file_path="data.xlsx", sheet_name="Sheet1")
if "error" not in result:
    print(f"Found {result['shape'][0]} rows in {result['selected_sheet']}")
    print(result['data'][:5])  # Print first 5 rows
```

### Writing to an Excel file
```python
data = [
    {"Name": "John", "Age": 30, "City": "New York"},
    {"Name": "Jane", "Age": 25, "City": "Boston"}
]
result = excel_write(data=data, file_path="output.xlsx", sheet_name="People")
if result.get("success"):
    print(f"Wrote {result['rows_written']} rows to {result['file_path']}")
```

### Getting Excel file information
```python
info = excel_info(file_path="data.xlsx")
if "error" not in info:
    print(f"File has {info['sheet_count']} sheets: {info['sheet_names']}")
    for sheet_name, sheet_info in info['sheets_info'].items():
        print(f"{sheet_name}: {sheet_info['rows']} rows, {sheet_info['columns']} columns")
```