"""Tests for messaging tool (FastMCP)."""
import pytest
from unittest.mock import patch, MagicMock

from fastmcp import FastMCP
from aden_tools.tools.messaging_tool import register_tools
from aden_tools.credentials import CredentialManager


@pytest.fixture
def mcp():
    """Create a FastMCP instance."""
    return FastMCP("test")


@pytest.fixture
def registered_mcp(mcp: FastMCP):
    """Create a FastMCP instance with messaging tools registered."""
    register_tools(mcp)
    return mcp


def get_tool_fn(mcp: FastMCP, name: str):
    """Get a tool function by name."""
    return mcp._tool_manager._tools[name].fn


class TestMessagingSend:
    """Tests for messaging_send tool."""

    def test_unknown_platform_returns_error(self, registered_mcp):
        """Unknown platform returns helpful error."""
        fn = get_tool_fn(registered_mcp, "messaging_send")
        result = fn(platform="telegram", message="hello")

        assert "error" in result
        assert "telegram" in result["error"].lower()
        assert "slack" in result["error"].lower() or "discord" in result["error"].lower()

    def test_empty_message_returns_error(self, registered_mcp):
        """Empty message returns error."""
        fn = get_tool_fn(registered_mcp, "messaging_send")
        result = fn(platform="slack", message="", channel="C123")

        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_slack_missing_token_returns_error(self, registered_mcp, monkeypatch):
        """Slack without token returns helpful error."""
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

        fn = get_tool_fn(registered_mcp, "messaging_send")
        result = fn(platform="slack", message="hello", channel="C123")

        assert "error" in result
        assert "SLACK_BOT_TOKEN" in result["error"]
        assert "help" in result

    def test_slack_missing_channel_returns_error(self, registered_mcp, monkeypatch):
        """Slack without channel returns error."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        fn = get_tool_fn(registered_mcp, "messaging_send")
        result = fn(platform="slack", message="hello", channel="")

        assert "error" in result
        assert "channel" in result["error"].lower()

    def test_discord_missing_webhook_returns_error(self, registered_mcp, monkeypatch):
        """Discord without webhook returns helpful error."""
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

        fn = get_tool_fn(registered_mcp, "messaging_send")
        result = fn(platform="discord", message="hello")

        assert "error" in result
        assert "DISCORD_WEBHOOK_URL" in result["error"]
        assert "help" in result

    @patch("httpx.Client")
    def test_slack_send_success(self, mock_client_class, registered_mcp, monkeypatch):
        """Successful Slack message send."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C123",
            "message": {"thread_ts": None},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        fn = get_tool_fn(registered_mcp, "messaging_send")
        result = fn(platform="slack", message="Hello!", channel="C123")

        assert result["success"] is True
        assert result["platform"] == "slack"
        assert result["message_id"] == "1234567890.123456"

    @patch("httpx.Client")
    def test_discord_send_success(self, mock_client_class, registered_mcp, monkeypatch):
        """Successful Discord webhook send."""
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "987654321",
            "channel_id": "456",
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        fn = get_tool_fn(registered_mcp, "messaging_send")
        result = fn(platform="discord", message="Hello!")

        assert result["success"] is True
        assert result["platform"] == "discord"
        assert result["message_id"] == "987654321"


class TestMessagingRead:
    """Tests for messaging_read tool."""

    def test_missing_token_returns_error(self, registered_mcp, monkeypatch):
        """Missing Slack token returns helpful error."""
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

        fn = get_tool_fn(registered_mcp, "messaging_read")
        result = fn(channel="C123")

        assert "error" in result
        assert "SLACK_BOT_TOKEN" in result["error"]

    def test_missing_channel_returns_error(self, registered_mcp, monkeypatch):
        """Missing channel returns error."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        fn = get_tool_fn(registered_mcp, "messaging_read")
        result = fn(channel="")

        assert "error" in result
        assert "channel" in result["error"].lower()

    @patch("httpx.Client")
    def test_read_success(self, mock_client_class, registered_mcp, monkeypatch):
        """Successful message read."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "messages": [
                {
                    "ts": "1234567890.123456",
                    "text": "Hello world",
                    "user": "U123",
                    "thread_ts": None,
                },
                {
                    "ts": "1234567890.123457",
                    "text": "Another message",
                    "user": "U456",
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        fn = get_tool_fn(registered_mcp, "messaging_read")
        result = fn(channel="C123", limit=10)

        assert result["success"] is True
        assert result["platform"] == "slack"
        assert result["count"] == 2
        assert len(result["messages"]) == 2


class TestMessagingReact:
    """Tests for messaging_react tool."""

    def test_missing_token_returns_error(self, registered_mcp, monkeypatch):
        """Missing Slack token returns error."""
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

        fn = get_tool_fn(registered_mcp, "messaging_react")
        result = fn(channel="C123", message_id="1234.5678", emoji="thumbsup")

        assert "error" in result
        assert "SLACK_BOT_TOKEN" in result["error"]

    def test_missing_channel_returns_error(self, registered_mcp, monkeypatch):
        """Missing channel returns error."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        fn = get_tool_fn(registered_mcp, "messaging_react")
        result = fn(channel="", message_id="1234.5678", emoji="thumbsup")

        assert "error" in result
        assert "channel" in result["error"].lower()

    def test_missing_message_id_returns_error(self, registered_mcp, monkeypatch):
        """Missing message_id returns error."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        fn = get_tool_fn(registered_mcp, "messaging_react")
        result = fn(channel="C123", message_id="", emoji="thumbsup")

        assert "error" in result
        assert "message" in result["error"].lower()

    def test_missing_emoji_returns_error(self, registered_mcp, monkeypatch):
        """Missing emoji returns error."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        fn = get_tool_fn(registered_mcp, "messaging_react")
        result = fn(channel="C123", message_id="1234.5678", emoji="")

        assert "error" in result
        assert "emoji" in result["error"].lower()

    @patch("httpx.Client")
    def test_react_success(self, mock_client_class, registered_mcp, monkeypatch):
        """Successful reaction add."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        fn = get_tool_fn(registered_mcp, "messaging_react")
        result = fn(channel="C123", message_id="1234.5678", emoji="thumbsup")

        assert result["success"] is True
        assert result["emoji"] == "thumbsup"


class TestMessagingUpload:
    """Tests for messaging_upload tool."""

    def test_unknown_platform_returns_error(self, registered_mcp):
        """Unknown platform returns error."""
        fn = get_tool_fn(registered_mcp, "messaging_upload")
        result = fn(platform="teams", filename="test.txt", content="hello")

        assert "error" in result
        assert "teams" in result["error"].lower()

    def test_missing_filename_returns_error(self, registered_mcp, monkeypatch):
        """Missing filename returns error."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        fn = get_tool_fn(registered_mcp, "messaging_upload")
        result = fn(platform="slack", filename="", content="hello", channel="C123")

        assert "error" in result
        assert "filename" in result["error"].lower()

    def test_missing_content_returns_error(self, registered_mcp, monkeypatch):
        """Missing content returns error."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        fn = get_tool_fn(registered_mcp, "messaging_upload")
        result = fn(platform="slack", filename="test.txt", content="", channel="C123")

        assert "error" in result
        assert "content" in result["error"].lower()


class TestMessagingListChannels:
    """Tests for messaging_list_channels tool."""

    def test_missing_token_returns_error(self, registered_mcp, monkeypatch):
        """Missing Slack token returns error."""
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

        fn = get_tool_fn(registered_mcp, "messaging_list_channels")
        result = fn()

        assert "error" in result
        assert "SLACK_BOT_TOKEN" in result["error"]

    @patch("httpx.Client")
    def test_list_channels_success(self, mock_client_class, registered_mcp, monkeypatch):
        """Successful channel list."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "channels": [
                {"id": "C123", "name": "general", "is_private": False, "num_members": 50},
                {"id": "C456", "name": "random", "is_private": False, "num_members": 30},
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        fn = get_tool_fn(registered_mcp, "messaging_list_channels")
        result = fn()

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["channels"]) == 2
        assert result["channels"][0]["name"] == "general"


class TestMessagingValidate:
    """Tests for messaging_validate tool."""

    def test_unknown_platform_returns_error(self, registered_mcp):
        """Unknown platform returns error."""
        fn = get_tool_fn(registered_mcp, "messaging_validate")
        result = fn(platform="telegram")

        assert result["valid"] is False
        assert "telegram" in result["error"].lower()

    def test_slack_missing_token_returns_invalid(self, registered_mcp, monkeypatch):
        """Missing Slack token returns invalid."""
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

        fn = get_tool_fn(registered_mcp, "messaging_validate")
        result = fn(platform="slack")

        assert result["valid"] is False
        assert "SLACK_BOT_TOKEN" in result["error"]

    def test_discord_missing_webhook_returns_invalid(self, registered_mcp, monkeypatch):
        """Missing Discord webhook returns invalid."""
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

        fn = get_tool_fn(registered_mcp, "messaging_validate")
        result = fn(platform="discord")

        assert result["valid"] is False
        assert "DISCORD_WEBHOOK_URL" in result["error"]


class TestCredentialManagerIntegration:
    """Tests for CredentialManager integration."""

    def test_uses_credential_manager_for_slack(self, mcp):
        """Uses CredentialManager when provided."""
        creds = CredentialManager.for_testing({"slack": "xoxb-test-token"})
        register_tools(mcp, credentials=creds)

        # Tool should be registered
        assert "messaging_send" in mcp._tool_manager._tools

    def test_uses_credential_manager_for_discord(self, mcp):
        """Uses CredentialManager for Discord when provided."""
        creds = CredentialManager.for_testing({
            "discord_webhook": "https://discord.com/api/webhooks/123/abc"
        })
        register_tools(mcp, credentials=creds)

        # Tool should be registered
        assert "messaging_send" in mcp._tool_manager._tools
