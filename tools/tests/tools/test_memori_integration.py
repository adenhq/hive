"""
Integration test for Memori tool registration within the Hive toolkit.
"""

from fastmcp import FastMCP
from aden_tools.tools import register_all_tools
from aden_tools.credentials import CredentialManager

def test_memori_integration_in_toolkit():
    """Verify Memori tools are globally registered in register_all_tools."""
    mcp = FastMCP("hive-toolkit")
    creds = CredentialManager.for_testing({
        "memori": "token-789"
    })
    
    # Register all tools like the real runtime does
    register_all_tools(mcp, credentials=creds)
    
    # FastMCP internal access to verify registration
    tool_names = mcp._tool_manager._tools.keys()
    
    # Check all 4 memori tools
    assert "memori_add" in tool_names
    assert "memori_recall" in tool_names
    assert "memori_delete" in tool_names
    assert "memori_health_check" in tool_names
    
    # Verify description keyword
    add_tool = mcp._tool_manager._tools["memori_add"]
    assert "persistent memory" in add_tool.description

if __name__ == "__main__":
    test_memori_integration_in_toolkit()
    print("Memori Integration check passed!")
