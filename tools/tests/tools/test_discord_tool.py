"""
Tests for Discord tool.

Covers:
- _DiscordClient methods (list_guilds, list_channels, send_message, get_messages)
- Error handling (401, 403, 404, timeout)
- Credential retrieval (CredentialStoreAdapter vs env var)
- All 4 MCP tool functions
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aden_tools.tools.discord_tool.discord_tool import (
    DISCORD_API_BASE,
    _DiscordClient,
    register_tools,
)

# --- _DiscordClient tests ---


class TestDiscordClient:
    def setup_method(self):
        self.client = _DiscordClient("test-bot-token")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bot test-bot-token"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": "123", "username": "test-bot"}
        assert self.client._handle_response(response) == {"id": "123", "username": "test-bot"}

    def test_handle_response_204(self):
        response = MagicMock()
        response.status_code = 204
        result = self.client._handle_response(response)
        assert result == {"success": True}

    @pytest.mark.parametrize(
        "status_code",
        [401, 403, 404, 500],
    )
    def test_handle_response_errors(self, status_code):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = {"message": "Test error"}
        response.text = "Test error"
        result = self.client._handle_response(response)
        assert "error" in result
        assert str(status_code) in result["error"]

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.get")
    def test_list_guilds(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                    {"id": "g1", "name": "Test Server"},
                    {"id": "g2", "name": "Another Server"},
                ]
            ),
        )
        result = self.client.list_guilds()
        mock_get.assert_called_once_with(
            f"{DISCORD_API_BASE}/users/@me/guilds",
            headers=self.client._headers,
            timeout=30.0,
        )
        assert len(result) == 2
        assert result[0]["name"] == "Test Server"

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.get")
    def test_list_channels(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                    {"id": "c1", "name": "general", "type": 0},
                    {"id": "c2", "name": "incidents", "type": 0},
                ]
            ),
        )
        result = self.client.list_channels("guild-123")
        mock_get.assert_called_once_with(
            f"{DISCORD_API_BASE}/guilds/guild-123/channels",
            headers=self.client._headers,
            timeout=30.0,
        )
        assert len(result) == 2
        assert result[0]["name"] == "general"

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.post")
    def test_send_message(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "id": "m123",
                    "channel_id": "c1",
                    "content": "Hello world",
                }
            ),
        )
        result = self.client.send_message("c1", "Hello world")
        mock_post.assert_called_once_with(
            f"{DISCORD_API_BASE}/channels/c1/messages",
            headers=self.client._headers,
            json={"content": "Hello world", "tts": False},
            timeout=30.0,
        )
        assert result["content"] == "Hello world"
        assert result["channel_id"] == "c1"

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.get")
    def test_get_messages(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                    {"id": "m1", "content": "First"},
                    {"id": "m2", "content": "Second"},
                ]
            ),
        )
        result = self.client.get_messages("c1", limit=10)
        mock_get.assert_called_once_with(
            f"{DISCORD_API_BASE}/channels/c1/messages",
            headers=self.client._headers,
            params={"limit": 10},
            timeout=30.0,
        )
        assert len(result) == 2
        assert result[0]["content"] == "First"


# --- Tool registration tests ---


class TestDiscordListGuildsTool:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "test-token"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.get")
    def test_list_guilds_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value=[{"id": "g1", "name": "Test Server"}]),
        )
        result = self._fn("discord_list_guilds")()
        assert result["success"] is True
        assert len(result["guilds"]) == 1
        assert result["guilds"][0]["name"] == "Test Server"

    def test_list_guilds_no_credentials(self):
        mcp = MagicMock()
        fns = []
        mcp.tool.return_value = lambda fn: fns.append(fn) or fn
        register_tools(mcp, credentials=None)
        with patch.dict("os.environ", {"DISCORD_BOT_TOKEN": ""}, clear=False):
            result = next(f for f in fns if f.__name__ == "discord_list_guilds")()
        assert "error" in result
        assert "not configured" in result["error"]


class TestDiscordListChannelsTool:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "test-token"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.get")
    def test_list_channels_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                    {"id": "c1", "name": "general", "type": 0},
                ]
            ),
        )
        result = self._fn("discord_list_channels")("guild-123")
        assert result["success"] is True
        assert len(result["channels"]) == 1
        assert result["channels"][0]["name"] == "general"

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.get")
    def test_list_channels_error(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=404,
            json=MagicMock(return_value={"message": "Unknown Guild"}),
            text="Unknown Guild",
        )
        result = self._fn("discord_list_channels")("bad-guild")
        assert "error" in result
        assert "404" in result["error"]


class TestDiscordSendMessageTool:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "test-token"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.post")
    def test_send_message_success(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "id": "m123",
                    "channel_id": "c1",
                    "content": "Incident resolved",
                }
            ),
        )
        result = self._fn("discord_send_message")("c1", "Incident resolved")
        assert result["success"] is True
        assert result["message"]["content"] == "Incident resolved"


class TestDiscordGetMessagesTool:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "test-token"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.discord_tool.discord_tool.httpx.get")
    def test_get_messages_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                    {"id": "m1", "content": "First message"},
                ]
            ),
        )
        result = self._fn("discord_get_messages")("c1", limit=10)
        assert result["success"] is True
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "First message"


# --- Credential spec tests ---


class TestCredentialSpec:
    def test_discord_credential_spec_exists(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        assert "discord" in CREDENTIAL_SPECS

    def test_discord_spec_env_var(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        spec = CREDENTIAL_SPECS["discord"]
        assert spec.env_var == "DISCORD_BOT_TOKEN"

    def test_discord_spec_tools(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        spec = CREDENTIAL_SPECS["discord"]
        assert "discord_list_guilds" in spec.tools
        assert "discord_list_channels" in spec.tools
        assert "discord_send_message" in spec.tools
        assert "discord_get_messages" in spec.tools
        assert len(spec.tools) == 4
