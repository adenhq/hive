"""Tests for salesforce_tool."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.salesforce_tool.salesforce_tool import register_tools


@pytest.fixture
def mcp():
    """Create a FastMCP instance."""
    mcp = FastMCP("test-server")
    register_tools(mcp)
    return mcp


@pytest.fixture
def tool_manager(mcp):
    """Retrieve the tool manager from the MCP server."""
    # FastMCP stores tools in its internal _tool_manager._tools dictionary
    return mcp._tool_manager


@pytest.fixture
def mock_httpx_client():
    """Mock request call."""
    with patch("httpx.get") as mock_get, \
         patch("httpx.post") as mock_post, \
         patch("httpx.patch") as mock_patch, \
         patch("httpx.delete") as mock_delete:
        yield {
            "get": mock_get,
            "post": mock_post,
            "patch": mock_patch,
            "delete": mock_delete,
        }


def test_missing_credentials_error(tool_manager):
    """Test error when credentials are missing."""
    tool = tool_manager._tools["salesforce_soql_query"].fn
    result = tool(query="SELECT Id FROM Account")
    assert "Salesforce Access Token is required" in result


def test_salesforce_soql_query(tool_manager, mock_httpx_client):
    """Test SOQL query execution."""
    tool = tool_manager._tools["salesforce_soql_query"].fn
    mock_get = mock_httpx_client["get"]

    # Mock successful response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "totalSize": 1,
        "done": True,
        "records": [
            {
                "attributes": {"type": "Account", "url": "/..."},
                "Id": "001...",
                "Name": "Test Account"
            }
        ]
    }
    mock_get.return_value = mock_response

    result = tool(
        query="SELECT Id, Name FROM Account",
        access_token="fake_token",
        instance_url="https://test.salesforce.com"
    )

    # Verify call arguments
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "https://test.salesforce.com/services/data/v60.0/query" in args[0]
    assert kwargs["params"]["q"] == "SELECT Id, Name FROM Account"

    # Verify result logic (stripping attributes)
    assert "Found 1 records" in result
    assert "Test Account" in result
    assert "attributes" not in result


def test_salesforce_soql_query_error(tool_manager, mock_httpx_client):
    """Test SOQL query with API error."""
    tool = tool_manager._tools["salesforce_soql_query"].fn
    mock_get = mock_httpx_client["get"]

    # Mock error response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.json.return_value = [{"message": "Invalid query", "errorCode": "MALFORMED_QUERY"}]
    mock_get.return_value = mock_response

    result = tool(
        query="SELECT Invalid FROM Account",
        access_token="fake_token",
        instance_url="https://test.salesforce.com"
    )

    assert "Error executing query" in result
    assert "Invalid query" in result


def test_salesforce_get_record(tool_manager, mock_httpx_client):
    """Test getting a record."""
    tool = tool_manager._tools["salesforce_get_record"].fn
    mock_get = mock_httpx_client["get"]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "attributes": {"type": "Account", "url": "..."},
        "Id": "001...",
        "Name": "Test Account"
    }
    mock_get.return_value = mock_response

    result = tool(
        sobject="Account",
        record_id="001...",
        access_token="fake_token",
        instance_url="https://test.salesforce.com"
    )

    assert "Test Account" in result
    assert "attributes" not in result


def test_salesforce_create_record(tool_manager, mock_httpx_client):
    """Test creating a record."""
    tool = tool_manager._tools["salesforce_create_record"].fn
    mock_post = mock_httpx_client["post"]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "001...", "success": True, "errors": []}
    mock_post.return_value = mock_response

    result = tool(
        sobject="Account",
        data={"Name": "New Account"},
        access_token="fake_token",
        instance_url="https://test.salesforce.com"
    )

    assert "Successfully created record" in result
    assert "001..." in result


def test_salesforce_update_record(tool_manager, mock_httpx_client):
    """Test updating a record."""
    tool = tool_manager._tools["salesforce_update_record"].fn
    mock_patch = mock_httpx_client["patch"]

    # 204 No Content is typical for update success
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_patch.return_value = mock_response

    result = tool(
        sobject="Account",
        record_id="001...",
        data={"Name": "Updated Name"},
        access_token="fake_token",
        instance_url="https://test.salesforce.com"
    )

    assert "Successfully updated record" in result


def test_salesforce_get_limits(tool_manager, mock_httpx_client):
    """Test fetching API limits."""
    tool = tool_manager._tools["salesforce_get_limits"].fn
    mock_get = mock_httpx_client["get"]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "DailyApiRequests": {"Max": 15000, "Remaining": 14999}
    }
    mock_get.return_value = mock_response

    result = tool(
        access_token="fake_token",
        instance_url="https://test.salesforce.com"
    )

    assert "API Usage" in result
    assert "Remaining': 14999" in result
