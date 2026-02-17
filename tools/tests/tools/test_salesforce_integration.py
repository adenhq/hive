"""
Integration-style tests for the Salesforce tool.
Verifies tool registration, credential handling, and end-to-end flow.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools import register_all_tools
from aden_tools.credentials import CredentialStoreAdapter


@pytest.fixture
def mcp():
    return FastMCP("test-hive")


@pytest.fixture
def mock_credentials():
    adapter = MagicMock(spec=CredentialStoreAdapter)
    adapter.get.side_effect = lambda k: {
        "salesforce_instance_url": "https://test.salesforce.com",
        "salesforce_access_token": "test-integration-token",
    }.get(k)
    return adapter


def test_salesforce_registration_integrated(mcp, mock_credentials):
    """Test that Salesforce tools are correctly registered via register_all_tools."""
    register_all_tools(mcp, credentials=mock_credentials)
    
    # Check for a few key Salesforce tools
    tool_names = [t.name for t in mcp._tool_manager._tools.values()]
    assert "salesforce_query" in tool_names
    assert "salesforce_search_leads" in tool_names


@patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.get")
def test_full_query_flow(mock_get, mcp, mock_credentials):
    """Test the full flow from tool call to API request."""
    register_all_tools(mcp, credentials=mock_credentials)
    
    # Access tool via tool manager
    func = mcp._tool_manager._tools["salesforce_query"].fn
    
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"records": [{"Id": "rec1", "Name": "Integrated Test"}]}
    )
    
    result = func(soql_query="SELECT Id FROM Lead")
    
    # Verify results
    assert len(result["records"]) == 1
    assert result["records"][0]["Name"] == "Integrated Test"
    
    # Verify request details
    args, kwargs = mock_get.call_args
    assert "https://test.salesforce.com/services/data/v60.0/query" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer test-integration-token"
    assert kwargs["params"]["q"] == "SELECT Id FROM Lead"


def test_salesforce_missing_credentials(mcp):
    """Test that the tool returns a helpful error when credentials are missing."""
    # Ensure env vars are not set
    with patch.dict("os.environ", {}, clear=True):
        register_all_tools(mcp, credentials=None)
        
        func = mcp._tool_manager._tools["salesforce_query"].fn
        result = func(soql_query="SELECT Id FROM Lead")
        
        assert "error" in result
        assert "Salesforce credentials not configured" in result["error"]
        assert "SALESFORCE_ACCESS_TOKEN" in result["help"]
