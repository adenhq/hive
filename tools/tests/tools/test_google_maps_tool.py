import json
import pytest
import httpx
from unittest.mock import MagicMock, patch, ANY
from aden_tools.tools.google_maps_tool.google_maps_tool import _GoogleMapsClient, register_tools

@pytest.fixture
def mock_credentials():
    mock = MagicMock()
    mock.get.side_effect = lambda x: "test_key" if x == "google_maps" else None
    return mock

@pytest.fixture
def client():
    return _GoogleMapsClient("test_key")

def test_client_init(client):
    assert client.api_key == "test_key"
    assert "geocode" in client.base_urls

@patch("httpx.Client.get")
def test_geocode_success(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "OK", "results": [{"formatted_address": "Test Address"}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = client.geocode("123 Test St")
    assert result["status"] == "OK"
    assert result["results"][0]["formatted_address"] == "Test Address"
    
    # Verify params
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["address"] == "123 Test St"
    assert kwargs["params"]["key"] == "test_key"

@patch("httpx.Client.get")
def test_api_error_limit_exceeded(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "OVER_QUERY_LIMIT", "error_message": "Quota exceeded"}
    mock_get.return_value = mock_response

    with pytest.raises(RuntimeError, match="Google Maps API limit exceeded"):
        client.geocode("123 Test St")

@patch("httpx.Client.get")
def test_api_error_request_denied(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "REQUEST_DENIED", "error_message": "Invalid key"}
    mock_get.return_value = mock_response

    with pytest.raises(PermissionError, match="Google Maps API denied"):
        client.geocode("123 Test St")

@patch("httpx.Client.get")
def test_directions_success(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "OK", "routes": []}
    mock_get.return_value = mock_response

    client.directions("Origin", "Dest", mode="walking")
    
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["origin"] == "Origin"
    assert kwargs["params"]["destination"] == "Dest"
    assert kwargs["params"]["mode"] == "walking"

@patch("aden_tools.tools.google_maps_tool.google_maps_tool._GoogleMapsClient")
def test_mcp_tool_geocode(mock_client_class, mock_credentials):
    mock_client = mock_client_class.return_value
    mock_client.geocode.return_value = {"status": "OK", "results": []}

    mock_mcp = MagicMock()
    mock_tool_distributor = MagicMock()
    mock_mcp.tool.return_value = mock_tool_distributor
    
    register_tools(mock_mcp, credentials=mock_credentials)
    
    # Find maps_geocode
    geocode_tool = None
    for call in mock_tool_distributor.call_args_list:
        func = call.args[0]
        if func.__name__ == "maps_geocode":
            geocode_tool = func
            break
    
    assert geocode_tool is not None
    
    # Call tool
    res = geocode_tool("Test St")
    assert "status" in res

@patch("aden_tools.tools.google_maps_tool.google_maps_tool._GoogleMapsClient")
def test_mcp_tool_distance_matrix(mock_client_class, mock_credentials):
    mock_client = mock_client_class.return_value
    mock_client.distance_matrix.return_value = {"status": "OK", "rows": []}

    mock_mcp = MagicMock()
    mock_tool_distributor = MagicMock()
    mock_mcp.tool.return_value = mock_tool_distributor
    
    register_tools(mock_mcp, credentials=mock_credentials)
    
    # Find tool
    dm_tool = None
    for call in mock_tool_distributor.call_args_list:
        func = call.args[0]
        if func.__name__ == "maps_distance_matrix":
            dm_tool = func
            break
            
    assert dm_tool is not None
    
    dm_tool(["A", "B"], ["C", "D"], mode="driving")
    mock_client.distance_matrix.assert_called_with(["A", "B"], ["C", "D"], mode="driving")
