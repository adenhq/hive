"""
Integration test for Zendesk tool registration within the Hive toolkit.
"""

from fastmcp import FastMCP
from aden_tools.tools import register_all_tools
from aden_tools.credentials import CredentialManager

def test_zendesk_integration_in_toolkit():
    """Verify Zendesk tools are globally registered in register_all_tools."""
    mcp = FastMCP("hive-toolkit")
    creds = CredentialManager.for_testing({
        "zendesk": "token",
        "zendesk_subdomain": "sub",
        "zendesk_email": "email"
    })
    
    # Register all tools like the real runtime does
    register_all_tools(mcp, credentials=creds)
    
    # FastMCP internal access to verify registration
    tool_names = mcp._tool_manager._tools.keys()
    zendesk_tools = [name for name in tool_names if name.startswith("zendesk_")]
    
    assert len(zendesk_tools) == 4
    assert "zendesk_health_check" in zendesk_tools
    assert "zendesk_ticket_search" in zendesk_tools
    assert "zendesk_ticket_get" in zendesk_tools
    assert "zendesk_ticket_update" in zendesk_tools
    
    # Verify the tool description contains expected keywords
    search_tool = mcp._tool_manager._tools["zendesk_ticket_search"]
    assert "Search for tickets" in search_tool.description
    assert "status" in search_tool.description

if __name__ == "__main__":
    test_zendesk_integration_in_toolkit()
    print("Integration check passed!")
