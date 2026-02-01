"""Tests for Excel tool."""

import os
import tempfile
from pathlib import Path

import pytest
from fastmcp import FastMCP

from aden_tools.tools.excel_tool import register_tools


@pytest.fixture
def mcp():
    """Create a FastMCP instance with Excel tools registered."""
    server = FastMCP("test")
    register_tools(server)
    return server


@pytest.fixture
def test_workspace():
    """Create a temporary test workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up workspace structure
        workspace_id = "test_workspace"
        agent_id = "test_agent"
        session_id = "test_session"

        workspace_path = Path(tmpdir) / workspace_id / agent_id / session_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        yield {
            "tmpdir": tmpdir,
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "session_id": session_id,
        }


def test_excel_write_basic(mcp, test_workspace):
    """Test writing a basic Excel file."""
    tool_fn = mcp._tool_manager._tools["excel_write"].fn

    result = tool_fn(
        path="test.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=["Name", "Age", "City"],
        rows=[
            {"Name": "Alice", "Age": 30, "City": "NYC"},
            {"Name": "Bob", "Age": 25, "City": "LA"},
        ],
    )

    assert result["success"] is True
    assert result["rows_written"] == 2
    assert result["column_count"] == 3


def test_excel_read_basic(mcp, test_workspace):
    """Test reading an Excel file."""
    # First write a file
    write_fn = mcp._tool_manager._tools["excel_write"].fn
    write_fn(
        path="test_read.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=["Product", "Price"],
        rows=[
            {"Product": "Widget", "Price": 10},
            {"Product": "Gadget", "Price": 20},
            {"Product": "Gizmo", "Price": 30},
        ],
    )

    # Now read it
    read_fn = mcp._tool_manager._tools["excel_read"].fn
    result = read_fn(
        path="test_read.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
    )

    assert result["success"] is True
    assert result["row_count"] == 3
    assert len(result["columns"]) == 2
    assert result["rows"][0]["Product"] == "Widget"


def test_excel_read_with_limit_offset(mcp, test_workspace):
    """Test reading with pagination (limit and offset)."""
    # Write a file with multiple rows
    write_fn = mcp._tool_manager._tools["excel_write"].fn
    rows = [{"ID": i, "Value": f"Item{i}"} for i in range(10)]
    write_fn(
        path="test_pagination.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=["ID", "Value"],
        rows=rows,
    )

    # Read with offset=2 and limit=3
    read_fn = mcp._tool_manager._tools["excel_read"].fn
    result = read_fn(
        path="test_pagination.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        offset=2,
        limit=3,
    )

    assert result["success"] is True
    assert result["row_count"] == 3
    assert result["offset"] == 2
    assert result["rows"][0]["ID"] == 2


def test_excel_append(mcp, test_workspace):
    """Test appending rows to an existing file."""
    # Create initial file
    write_fn = mcp._tool_manager._tools["excel_write"].fn
    write_fn(
        path="test_append.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=["Name", "Score"],
        rows=[{"Name": "Alice", "Score": 95}],
    )

    # Append more rows
    append_fn = mcp._tool_manager._tools["excel_append"].fn
    result = append_fn(
        path="test_append.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        rows=[
            {"Name": "Bob", "Score": 87},
            {"Name": "Charlie", "Score": 92},
        ],
    )

    assert result["success"] is True
    assert result["rows_appended"] == 2
    assert result["total_rows"] == 3


def test_excel_info(mcp, test_workspace):
    """Test getting Excel file metadata."""
    # Create a file
    write_fn = mcp._tool_manager._tools["excel_write"].fn
    write_fn(
        path="test_info.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=["A", "B", "C"],
        rows=[{"A": 1, "B": 2, "C": 3}] * 5,
    )

    # Get info
    info_fn = mcp._tool_manager._tools["excel_info"].fn
    result = info_fn(
        path="test_info.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
    )

    assert result["success"] is True
    assert result["sheet_count"] == 1
    assert result["sheets"][0]["column_count"] == 3
    assert result["sheets"][0]["total_rows"] == 5


def test_excel_sheet_list(mcp, test_workspace):
    """Test listing sheets in a workbook."""
    # Create file with default sheet
    write_fn = mcp._tool_manager._tools["excel_write"].fn
    write_fn(
        path="test_sheets.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=["X"],
        rows=[{"X": 1}],
        sheet_name="CustomSheet",
    )

    # List sheets
    list_fn = mcp._tool_manager._tools["excel_sheet_list"].fn
    result = list_fn(
        path="test_sheets.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
    )

    assert result["success"] is True
    assert "CustomSheet" in result["sheets"]
    assert result["sheet_count"] == 1


def test_excel_to_csv(mcp, test_workspace):
    """Test converting Excel to CSV."""
    # Create Excel file
    write_fn = mcp._tool_manager._tools["excel_write"].fn
    write_fn(
        path="test_convert.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=["Name", "Value"],
        rows=[
            {"Name": "Item1", "Value": 100},
            {"Name": "Item2", "Value": 200},
        ],
    )

    # Convert to CSV
    convert_fn = mcp._tool_manager._tools["excel_to_csv"].fn
    result = convert_fn(
        path="test_convert.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        output_path="test_convert.csv",
    )

    assert result["success"] is True
    assert result["rows_written"] == 2


def test_excel_file_not_found(mcp, test_workspace):
    """Test error handling for non-existent file."""
    read_fn = mcp._tool_manager._tools["excel_read"].fn
    result = read_fn(
        path="nonexistent.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
    )

    assert "error" in result
    assert "not found" in result["error"].lower()


def test_excel_invalid_extension(mcp, test_workspace):
    """Test error handling for invalid file extension."""
    write_fn = mcp._tool_manager._tools["excel_write"].fn
    result = write_fn(
        path="test.txt",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=["A"],
        rows=[{"A": 1}],
    )

    assert "error" in result
    assert "extension" in result["error"].lower()


def test_excel_empty_columns(mcp, test_workspace):
    """Test error handling for empty columns."""
    write_fn = mcp._tool_manager._tools["excel_write"].fn
    result = write_fn(
        path="test_empty.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        columns=[],
        rows=[],
    )

    assert "error" in result
    assert "cannot be empty" in result["error"].lower()


def test_excel_negative_offset_limit(mcp, test_workspace):
    """Test error handling for negative offset/limit."""
    read_fn = mcp._tool_manager._tools["excel_read"].fn
    result = read_fn(
        path="test.xlsx",
        workspace_id=test_workspace["workspace_id"],
        agent_id=test_workspace["agent_id"],
        session_id=test_workspace["session_id"],
        offset=-1,
    )

    assert "error" in result
    assert "non-negative" in result["error"].lower()
