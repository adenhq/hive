import json
import pytest
import httpx
from unittest.mock import MagicMock, patch
from aden_tools.tools.discord_tool import DiscordClient, register_tools

@pytest.fixture
def mock_credentials():
    mock = MagicMock()
    mock.get.side_effect = lambda x: "test_bot_token" if x == "discord" else None
    return mock

@pytest.fixture
def client():
    return DiscordClient("test_bot_token")

def test_client_init(client):
    assert client.bot_token == "test_bot_token"
    assert "Authorization" in client.headers
    assert client.headers["Authorization"] == "Bot test_bot_token"

@patch("httpx.Client.request")
def test_list_channels_success(mock_request, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": "1", "name": "general", "type": 0},
        {"id": "2", "name": "voice", "type": 2}
    ]
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    channels = client.list_channels("guild_123")
    assert len(channels) == 2
    assert channels[0]["name"] == "general"
    
    mock_request.assert_called_with(
        method="GET",
        url="https://discord.com/api/v10/guilds/guild_123/channels",
        headers=client.headers,
        params=None,
        json=None
    )

@patch("httpx.Client.request")
def test_send_message_success(mock_request, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "msg_1", "content": "Hello"}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    result = client.send_message("chan_123", "Hello")
    assert result["id"] == "msg_1"
    
    mock_request.assert_called_with(
        method="POST",
        url="https://discord.com/api/v10/channels/chan_123/messages",
        headers=client.headers,
        params=None,
        json={"content": "Hello"}
    )

@patch("httpx.Client.request")
def test_get_recent_messages_success(mock_request, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": "m1", "content": "hi"}]
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    msgs = client.get_recent_messages("chan_123", limit=5)
    assert len(msgs) == 1
    
    mock_request.assert_called_with(
        method="GET",
        url="https://discord.com/api/v10/channels/chan_123/messages",
        headers=client.headers,
        params={"limit": 5},
        json=None
    )

@patch("httpx.Client.request")
def test_api_error_handling(mock_request, client):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    error = httpx.HTTPStatusError("401 Unauthorized", request=MagicMock(), response=mock_response)
    mock_request.side_effect = error

    with pytest.raises(ValueError, match="Discord API error: 401 - Unauthorized"):
        client.list_channels("guild_1")

@patch("aden_tools.tools.discord_tool.DiscordClient")
def test_mcp_tool_list_channels(mock_client_class, mock_credentials):
    mock_client = mock_client_class.return_value
    mock_client.list_channels.return_value = [{"id": "1", "name": "gen", "type": 0}]

    mock_mcp = MagicMock()
    mock_tool_distributor = MagicMock()
    mock_mcp.tool.return_value = mock_tool_distributor
    
    register_tools(mock_mcp, credentials=mock_credentials)
    
    # Find tool
    tool_func = None
    for call in mock_tool_distributor.call_args_list:
        func = call.args[0]
        if func.__name__ == "discord_list_channels":
            tool_func = func
            break
            
    assert tool_func is not None
    res = tool_func("g1")
    assert "gen" in res

@patch("aden_tools.tools.discord_tool.DiscordClient")
def test_mcp_tool_send_message_error(mock_client_class, mock_credentials):
    mock_client = mock_client_class.return_value
    mock_client.send_message.side_effect = Exception("Network error")

    mock_mcp = MagicMock()
    mock_tool_distributor = MagicMock()
    mock_mcp.tool.return_value = mock_tool_distributor
    
    register_tools(mock_mcp, credentials=mock_credentials)
    
    tool_func = None
    for call in mock_tool_distributor.call_args_list:
        func = call.args[0]
        if func.__name__ == "discord_send_message":
            tool_func = func
            break
            
    res = tool_func("c1", "msg")
    assert "Error sending message" in res
    assert "Network error" in res
