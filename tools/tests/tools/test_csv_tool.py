import pytest
import os
from fastmcp import FastMCP
from aden_tools.tools.csv_analysis_tool import register_tools

@pytest.fixture
def mcp():
    server = FastMCP("test")
    register_tools(server)
    return server

def test_inspect_csv(mcp, tmp_path):
    # Crear CSV temporal
    d = tmp_path / "data.csv"
    d.write_text("col1,col2\n10,20\n30,40")

    tool_fn = mcp._tool_manager._tools["inspect_csv"].fn
    result = tool_fn(file_path=str(d))

    assert result["rows"] == 2
    assert "col1" in result["columns"]
    assert result["sample_data"][0]["col1"] == 10