import json
import pytest
import httpx
from unittest.mock import MagicMock, patch
from aden_tools.tools.n8n_tool import N8NClient

@pytest.fixture
def mock_credentials():
    return {
        "api_key": "test_api_key",
        "host": "https://n8n.example.com"
    }

@pytest.fixture
def n8n_client(mock_credentials):
    return N8NClient(mock_credentials["api_key"], mock_credentials["host"])

def test_client_init(mock_credentials):
    client = N8NClient(mock_credentials["api_key"], mock_credentials["host"])
    assert client.api_key == "test_api_key"
    assert client.host == "https://n8n.example.com"
    assert client.base_url == "https://n8n.example.com/api/v1"
    assert client.headers["X-N8N-API-KEY"] == "test_api_key"

@patch("httpx.Client.request")
def test_list_workflows_success(mock_request, n8n_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "1", "name": "Workflow 1", "active": True},
            {"id": "2", "name": "Workflow 2", "active": False}
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    workflows = n8n_client.list_workflows()
    
    assert len(workflows) == 2
    assert workflows[0]["name"] == "Workflow 1"
    mock_request.assert_called_once_with(
        method="GET",
        url="https://n8n.example.com/api/v1/workflows",
        headers=n8n_client.headers,
        params=None,
        json=None
    )

@patch("httpx.Client.request")
def test_trigger_workflow_success(mock_request, n8n_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"executionId": "exec_123", "status": "started"}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    payload = {"data": "test"}
    result = n8n_client.trigger_workflow("wf_1", payload)
    
    assert result["executionId"] == "exec_123"
    mock_request.assert_called_once_with(
        method="POST",
        url="https://n8n.example.com/api/v1/workflows/wf_1/run",
        headers=n8n_client.headers,
        params=None,
        json=payload
    )

@patch("httpx.Client.request")
def test_get_execution_status_success(mock_request, n8n_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "exec_123", "status": "success"}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    result = n8n_client.get_execution_status("exec_123")
    
    assert result["status"] == "success"
    mock_request.assert_called_once_with(
        method="GET",
        url="https://n8n.example.com/api/v1/executions/exec_123",
        headers=n8n_client.headers,
        params=None,
        json=None
    )

@patch("httpx.Client.request")
def test_api_error_handling(mock_request, n8n_client):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    
    # Create the HTTPStatusError with required arguments
    error = httpx.HTTPStatusError("401 Unauthorized", request=MagicMock(), response=mock_response)
    mock_request.side_effect = error

    with pytest.raises(ValueError, match="n8n API error: 401 - Unauthorized"):
        n8n_client.list_workflows()

@patch("httpx.Client.request")
def test_network_error_handling(mock_request, n8n_client):
    mock_request.side_effect = Exception("Connection timeout")

    with pytest.raises(RuntimeError, match="n8n request failed: Connection timeout"):
        n8n_client.list_workflows()

@patch("aden_tools.tools.n8n_tool.N8NClient")
def test_mcp_tool_list_workflows(mock_client_class):
    from aden_tools.tools.n8n_tool import register_tools
    
    mock_client = mock_client_class.return_value
    mock_client.list_workflows.return_value = [{"id": "1", "name": "WF1", "active": True}]
    
    # Mock MCP
    mock_mcp = MagicMock()
    # Mock the @mcp.tool() decorator
    # This is tricky because it's used as @mcp.tool()
    mock_tool_decorator = MagicMock()
    mock_mcp.tool.return_value = mock_tool_decorator
    
    mock_creds = MagicMock()
    mock_creds.get.side_effect = lambda x: "test_val"
    
    register_tools(mock_mcp, credentials=mock_creds)
    
    # The register_tools function should have called mcp.tool() 3 times
    assert mock_mcp.tool.call_count == 3
    
    # Find the list_workflows function
    # It's one of the calls to mock_tool_decorator
    list_wf_func = None
    for call in mock_tool_decorator.call_args_list:
        func = call.args[0]
        if func.__name__ == "n8n_list_workflows":
            list_wf_func = func
            break
            
    assert list_wf_func is not None
    result_json = list_wf_func()
    result = json.loads(result_json)
    assert result[0]["name"] == "WF1"

@patch("aden_tools.tools.n8n_tool.N8NClient")
def test_mcp_tool_trigger_workflow_error(mock_client_class):
    from aden_tools.tools.n8n_tool import register_tools
    
    mock_client = mock_client_class.return_value
    mock_client.trigger_workflow.side_effect = Exception("Workflow not found")
    
    mock_mcp = MagicMock()
    mock_tool_decorator = MagicMock()
    mock_mcp.tool.return_value = mock_tool_decorator
    
    mock_creds = MagicMock()
    mock_creds.get.side_effect = lambda x: "test_val"
    register_tools(mock_mcp, credentials=mock_creds)
    
    trigger_func = None
    for call in mock_tool_decorator.call_args_list:
        func = call.args[0]
        if func.__name__ == "n8n_trigger_workflow":
            trigger_func = func
            break
            
    assert trigger_func is not None
    result = trigger_func("bad_id", {})
    assert "Error triggering workflow" in result
    assert "Workflow not found" in result
