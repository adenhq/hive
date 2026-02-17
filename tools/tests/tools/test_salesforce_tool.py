"""
Unit tests for the Salesforce tool.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.salesforce_tool.salesforce_tool import register_tools


@pytest.fixture
def mcp():
    mcp_mock = MagicMock()
    # Mock the tool decorator: @mcp.tool()
    # It should return a decorator that returns the function itself
    mcp_mock.tool.return_value = lambda fn: fn
    return mcp_mock


@pytest.fixture
def credentials():
    mock_creds = MagicMock()
    mock_creds.get.side_effect = lambda k: {
        "salesforce_instance_url": "https://test.salesforce.com",
        "salesforce_access_token": "test-token",
    }.get(k)
    return mock_creds


def test_registration(mcp, credentials):
    """Test that all Salesforce tools are registered."""
    register_tools(mcp, credentials=credentials)
    # Check how many times mcp.tool() was called
    assert mcp.tool.call_count == 8


@patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.get")
def test_salesforce_query(mock_get, mcp, credentials):
    """Test executing a SOQL query."""
    # Capture the registered functions
    registered_tools = {}

    def mock_tool_decorator(**kwargs):
        def decorator(fn):
            name = kwargs.get("name") or fn.__name__
            registered_tools[name] = fn
            return fn
        return decorator

    mcp.tool.side_effect = mock_tool_decorator
    register_tools(mcp, credentials=credentials)
    
    salesforce_query = registered_tools["salesforce_query"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"totalSize": 1, "done": True, "records": [{"Id": "00Q1"}]}
    mock_get.return_value = mock_response

    result = salesforce_query(soql_query="SELECT Id FROM Lead")

    assert result["totalSize"] == 1
    assert result["records"][0]["Id"] == "00Q1"
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "query" in args[0]
    assert kwargs["params"]["q"] == "SELECT Id FROM Lead"


@patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.post")
def test_salesforce_create_record(mock_post, mcp, credentials):
    """Test creating a record."""
    registered_tools = {}
    mcp.tool.side_effect = lambda **kwargs: lambda fn: registered_tools.update({kwargs.get("name") or fn.__name__: fn}) or fn
    register_tools(mcp, credentials=credentials)
    
    salesforce_create_record = registered_tools["salesforce_create_record"]

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "00Q123456789", "success": True}
    mock_post.return_value = mock_response

    result = salesforce_create_record(object_name="Lead", fields={"LastName": "Doe", "Company": "Acme"})

    assert result["id"] == "00Q123456789"
    assert result["success"] is True
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {"LastName": "Doe", "Company": "Acme"}


@patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.patch")
def test_salesforce_update_record(mock_patch, mcp, credentials):
    """Test updating a record."""
    registered_tools = {}
    mcp.tool.side_effect = lambda **kwargs: lambda fn: registered_tools.update({kwargs.get("name") or fn.__name__: fn}) or fn
    register_tools(mcp, credentials=credentials)
    
    salesforce_update_record = registered_tools["salesforce_update_record"]

    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_patch.return_value = mock_response

    result = salesforce_update_record(object_name="Lead", record_id="00Q1", fields={"Status": "Closed"})

    assert result["success"] is True
    mock_patch.assert_called_once()


@patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.get")
def test_salesforce_get_record(mock_get, mcp, credentials):
    """Test getting a record by ID."""
    registered_tools = {}
    mcp.tool.side_effect = lambda **kwargs: lambda fn: registered_tools.update({kwargs.get("name") or fn.__name__: fn}) or fn
    register_tools(mcp, credentials=credentials)
    
    salesforce_get_record = registered_tools["salesforce_get_record"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Id": "00Q1", "Name": "Test Lead"}
    mock_get.return_value = mock_response

    result = salesforce_get_record(object_name="Lead", record_id="00Q1")

    assert result["Id"] == "00Q1"
    assert result["Name"] == "Test Lead"
    mock_get.assert_called_once()
    assert "Lead/00Q1" in mock_get.call_args[0][0]


@patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.get")
def test_salesforce_describe_object(mock_get, mcp, credentials):
    """Test describing an object."""
    registered_tools = {}
    mcp.tool.side_effect = lambda **kwargs: lambda fn: registered_tools.update({kwargs.get("name") or fn.__name__: fn}) or fn
    register_tools(mcp, credentials=credentials)
    
    salesforce_describe_object = registered_tools["salesforce_describe_object"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"name": "Lead", "fields": []}
    mock_get.return_value = mock_response

    result = salesforce_describe_object(object_name="Lead")

    assert result["name"] == "Lead"
    mock_get.assert_called_once()
    assert "Lead/describe" in mock_get.call_args[0][0]


@patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.get")
def test_salesforce_search_leads(mock_get, mcp, credentials):
    """Test searching leads."""
    registered_tools = {}
    mcp.tool.side_effect = lambda **kwargs: lambda fn: registered_tools.update({kwargs.get("name") or fn.__name__: fn}) or fn
    register_tools(mcp, credentials=credentials)
    
    salesforce_search_leads = registered_tools["salesforce_search_leads"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"records": [{"Name": "Search Result"}]}
    mock_get.return_value = mock_response

    result = salesforce_search_leads(query="test")

    assert result["records"][0]["Name"] == "Search Result"
    mock_get.assert_called_once()
    soql = mock_get.call_args[1]["params"]["q"]
    assert "FROM Lead" in soql
    assert "LIKE '%test%'" in soql


def test_error_handling(mcp, credentials):
    """Test handling of API errors."""
    registered_tools = {}
    mcp.tool.side_effect = lambda **kwargs: lambda fn: registered_tools.update({kwargs.get("name") or fn.__name__: fn}) or fn
    register_tools(mcp, credentials=credentials)
    
    salesforce_query = registered_tools["salesforce_query"]

    with patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = salesforce_query(soql_query="SELECT Id FROM Lead")
        assert "error" in result
        assert "access token" in result["error"]

    with patch("aden_tools.tools.salesforce_tool.salesforce_tool.httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = salesforce_query(soql_query="SELECT Id FROM Lead")
        assert "error" in result
        assert "Resource not found" in result["error"]
