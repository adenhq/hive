"""Tests for excel_tool - Read and manipulate Excel files."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from fastmcp import FastMCP

from aden_tools.tools.excel_tool.excel_tool import register_tools

# Test IDs for sandbox
TEST_WORKSPACE_ID = "test-workspace"
TEST_AGENT_ID = "test-agent"
TEST_SESSION_ID = "test-session"


@pytest.fixture
def mcp():
    """Create FastMCP instance for testing."""
    return FastMCP("test-excel")


@pytest.fixture
def excel_tools(mcp: FastMCP, tmp_path: Path):
    """Register all Excel tools and return them as a dict."""
    with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", str(tmp_path)):
        register_tools(mcp)
        
        # Access tools safely to avoid IDE type checking errors
        tools = mcp._tool_manager._tools
        
        yield {
            "excel_read": getattr(tools["excel_read"], "fn"),
            "excel_write": getattr(tools["excel_write"], "fn"), 
            "excel_append": getattr(tools["excel_append"], "fn"),
            "excel_info": getattr(tools["excel_info"], "fn"),
            "excel_create_sheet": getattr(tools["excel_create_sheet"], "fn"),
        }


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    """Create and return the session directory within the sandbox."""
    session_path = tmp_path / TEST_WORKSPACE_ID / TEST_AGENT_ID / TEST_SESSION_ID
    session_path.mkdir(parents=True, exist_ok=True)
    return session_path


@pytest.fixture
def basic_excel(session_dir: Path) -> Path:
    """Create a basic Excel file for testing."""
    excel_path = session_dir / "test.xlsx"
    
    data = {
        "Name": ["Alice", "Bob", "Charlie"],
        "Age": [25, 30, 35],
        "City": ["New York", "London", "Tokyo"]
    }
    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False, sheet_name="Sheet1")
    
    return excel_path


class TestExcelRead:
    """Test excel_read functionality."""

    def test_read_basic_file(self, excel_tools, basic_excel):
        """Test reading a basic Excel file."""
        excel_read = excel_tools["excel_read"]
        
        result = excel_read(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID
        )
        
        assert result["success"] is True
        assert result["path"] == "test.xlsx"
        assert result["sheet"] == "Sheet1"
        assert result["row_count"] == 3
        assert result["column_count"] == 3
        assert result["total_rows"] == 3
        assert "Name" in result["columns"]
        assert "Age" in result["columns"]
        assert "City" in result["columns"]
        assert len(result["rows"]) == 3

    def test_read_nonexistent_file(self, excel_tools):
        """Test reading a non-existent file returns error."""
        excel_read = excel_tools["excel_read"]
        
        result = excel_read(
            path="nonexistent.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID
        )
        
        assert "error" in result
        assert "File not found" in result["error"]

    def test_read_invalid_extension(self, excel_tools):
        """Test reading file with invalid extension."""
        excel_read = excel_tools["excel_read"]
        
        result = excel_read(
            path="test.txt",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID
        )
        
        assert "error" in result
        assert "File must have .xlsx or .xls extension" in result["error"]

    def test_read_with_limit_offset(self, excel_tools, basic_excel):
        """Test reading with limit and offset."""
        excel_read = excel_tools["excel_read"]
        
        result = excel_read(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            limit=2,
            offset=1
        )
        
        assert result["success"] is True
        assert result["row_count"] == 2
        assert result["total_rows"] == 3
        assert result["offset"] == 1
        assert result["limit"] == 2

    def test_read_negative_params(self, excel_tools):
        """Test negative offset and limit return errors."""
        excel_read = excel_tools["excel_read"]
        
        # Test negative offset
        result = excel_read(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            offset=-1
        )
        assert "error" in result
        assert "offset and limit must be non-negative" in result["error"]
        
        # Test negative limit
        result = excel_read(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            limit=-1
        )
        assert "error" in result
        assert "offset and limit must be non-negative" in result["error"]


class TestExcelWrite:
    """Test excel_write functionality."""

    def test_write_basic_file(self, excel_tools, session_dir):
        """Test writing data to a new Excel file."""
        excel_write = excel_tools["excel_write"]
        
        columns = ["Product", "Price", "Stock"]
        rows = [
            {"Product": "Apple", "Price": 1.5, "Stock": 100},
            {"Product": "Banana", "Price": 0.8, "Stock": 200}
        ]
        
        result = excel_write(
            path="output.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            columns=columns,
            rows=rows,
            sheet_name="Products"
        )
        
        assert result["success"] is True
        assert result["path"] == "output.xlsx"
        assert result["sheet"] == "Products"
        assert result["rows_written"] == 2
        assert result["column_count"] == 3
        
        # Verify file was created and content is correct
        output_path = session_dir / "output.xlsx"
        assert output_path.exists()
        
        df = pd.read_excel(output_path, sheet_name="Products")
        assert len(df) == 2
        assert list(df.columns) == columns

    def test_write_empty_columns_error(self, excel_tools):
        """Test writing with empty columns returns error."""
        excel_write = excel_tools["excel_write"]
        
        result = excel_write(
            path="output.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            columns=[],
            rows=[]
        )
        
        assert "error" in result
        assert "columns cannot be empty" in result["error"]

    def test_write_invalid_extension(self, excel_tools):
        """Test writing with invalid extension."""
        excel_write = excel_tools["excel_write"]
        
        result = excel_write(
            path="output.txt",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            columns=["A"],
            rows=[{"A": 1}]
        )
        
        assert "error" in result
        assert "File must have .xlsx or .xls extension" in result["error"]


class TestExcelAppend:
    """Test excel_append functionality."""

    def test_append_to_existing_file(self, excel_tools, basic_excel):
        """Test appending rows to existing file."""
        excel_append = excel_tools["excel_append"]
        
        new_rows = [
            {"Name": "David", "Age": 40, "City": "Berlin"}
        ]
        
        result = excel_append(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            rows=new_rows
        )
        
        assert result["success"] is True
        assert result["path"] == "test.xlsx"
        assert result["sheet"] == "Sheet1"
        assert result["rows_appended"] == 1
        assert result["total_rows"] == 4  # 3 original + 1 new
        
        # Verify the data was appended
        df = pd.read_excel(basic_excel, sheet_name="Sheet1")
        assert len(df) == 4
        assert df.iloc[-1]["Name"] == "David"

    def test_append_nonexistent_file(self, excel_tools):
        """Test appending to non-existent file returns error."""
        excel_append = excel_tools["excel_append"]
        
        result = excel_append(
            path="nonexistent.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            rows=[{"A": 1}]
        )
        
        assert "error" in result
        assert "File not found" in result["error"]

    def test_append_empty_rows(self, excel_tools, basic_excel):
        """Test appending empty rows returns error."""
        excel_append = excel_tools["excel_append"]
        
        result = excel_append(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            rows=[]
        )
        
        assert "error" in result
        assert "rows cannot be empty" in result["error"]


class TestExcelInfo:
    """Test excel_info functionality."""

    def test_get_file_info(self, excel_tools, basic_excel):
        """Test getting file information."""
        excel_info = excel_tools["excel_info"]
        
        result = excel_info(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID
        )
        
        assert result["success"] is True
        assert result["path"] == "test.xlsx"
        assert result["sheet_count"] == 1
        assert "file_size" in result
        assert len(result["sheets"]) == 1
        
        sheet_info = result["sheets"][0]
        assert sheet_info["name"] == "Sheet1"
        assert sheet_info["row_count"] == 3
        assert sheet_info["column_count"] == 3
        assert "Name" in sheet_info["columns"]

    def test_info_nonexistent_file(self, excel_tools):
        """Test getting info for non-existent file."""
        excel_info = excel_tools["excel_info"]
        
        result = excel_info(
            path="nonexistent.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID
        )
        
        assert "error" in result
        assert "File not found" in result["error"]


class TestExcelCreateSheet:
    """Test excel_create_sheet functionality."""

    def test_create_sheet_new_file(self, excel_tools, session_dir):
        """Test creating a sheet in a new file."""
        excel_create_sheet = excel_tools["excel_create_sheet"]
        
        columns = ["ID", "Value"]
        rows = [{"ID": 1, "Value": "Test"}]
        
        result = excel_create_sheet(
            path="new_file.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            sheet_name="Data",
            columns=columns,
            rows=rows
        )
        
        assert result["success"] is True
        assert result["path"] == "new_file.xlsx"
        assert result["sheet"] == "Data"
        assert result["rows_written"] == 1
        assert result.get("file_created") is True
        
        # Verify file was created
        new_file = session_dir / "new_file.xlsx"
        assert new_file.exists()
        
        df = pd.read_excel(new_file, sheet_name="Data")
        assert len(df) == 1
        assert list(df.columns) == columns

    def test_create_sheet_existing_file(self, excel_tools, basic_excel):
        """Test adding a sheet to existing file."""
        excel_create_sheet = excel_tools["excel_create_sheet"]
        
        columns = ["X", "Y"]
        rows = [{"X": 10, "Y": 20}]
        
        result = excel_create_sheet(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            sheet_name="NewSheet",
            columns=columns,
            rows=rows
        )
        
        assert result["success"] is True
        assert result["sheet"] == "NewSheet"
        assert result["rows_written"] == 1
        assert "existing_sheets" in result
        
        # Verify both sheets exist
        with pd.ExcelFile(basic_excel) as xls:
            assert "Sheet1" in xls.sheet_names
            assert "NewSheet" in xls.sheet_names

    def test_create_sheet_empty_columns(self, excel_tools):
        """Test creating sheet with empty columns returns error."""
        excel_create_sheet = excel_tools["excel_create_sheet"]
        
        result = excel_create_sheet(
            path="new_file.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            sheet_name="Test",
            columns=[],
            rows=[]
        )
        
        assert "error" in result
        assert "columns cannot be empty" in result["error"]


class TestMultiSheetOperations:
    """Test multi-sheet Excel operations."""

    def test_read_specific_sheet(self, excel_tools, session_dir):
        """Test reading a specific sheet by name."""
        # Create multi-sheet Excel file
        excel_path = session_dir / "multi_sheet.xlsx"
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
            df2 = pd.DataFrame({"X": [5, 6], "Y": [7, 8]})
            df1.to_excel(writer, sheet_name='FirstSheet', index=False)
            df2.to_excel(writer, sheet_name='SecondSheet', index=False)
        
        excel_read = excel_tools["excel_read"]
        
        # Read specific sheet
        result = excel_read(
            path="multi_sheet.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            sheet_name="SecondSheet"
        )
        
        assert result["success"] is True
        assert result["sheet"] == "SecondSheet"
        assert result["columns"] == ["X", "Y"]
        assert result["row_count"] == 2

    def test_read_invalid_sheet(self, excel_tools, basic_excel):
        """Test reading invalid sheet name returns error."""
        excel_read = excel_tools["excel_read"]
        
        result = excel_read(
            path="test.xlsx",
            workspace_id=TEST_WORKSPACE_ID,
            agent_id=TEST_AGENT_ID,
            session_id=TEST_SESSION_ID,
            sheet_name="InvalidSheet"
        )
        
        assert "error" in result
        assert "Sheet 'InvalidSheet' not found" in result["error"]
