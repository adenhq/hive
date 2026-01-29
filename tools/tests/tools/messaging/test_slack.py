"""Tests for Slack platform adapter."""
import pytest
from unittest.mock import patch, MagicMock

from aden_tools.tools.messaging_tool.platforms.slack import SlackPlatform, SlackAPIError


class TestSlackPlatform:
    """Tests for SlackPlatform class."""

    def test_platform_name(self):
        """Platform name is 'slack'."""
        platform = SlackPlatform(token="xoxb-test")
        assert platform.platform_name == "slack"
        platform.close()

    @patch("httpx.Client")
    def test_send_message_success(self, mock_client_class):
        """Successful message send."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C123",
            "message": {},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        result = platform.send_message(channel="C123", text="Hello!")

        assert result.success is True
        assert result.message_id == "1234567890.123456"
        assert result.channel == "C123"

        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/chat.postMessage"
        assert call_args[1]["json"]["channel"] == "C123"
        assert call_args[1]["json"]["text"] == "Hello!"

    @patch("httpx.Client")
    def test_send_message_with_thread(self, mock_client_class):
        """Message send with thread_id."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C123",
            "message": {"thread_ts": "1234567890.000000"},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        result = platform.send_message(
            channel="C123",
            text="Reply!",
            thread_id="1234567890.000000",
        )

        assert result.success is True

        # Verify thread_ts was included
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["thread_ts"] == "1234567890.000000"

    @patch("httpx.Client")
    def test_send_message_api_error(self, mock_client_class):
        """API error handling."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": False,
            "error": "channel_not_found",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        result = platform.send_message(channel="C999", text="Hello!")

        assert result.success is False
        assert "channel_not_found" in result.error

    @patch("httpx.Client")
    def test_get_messages_success(self, mock_client_class):
        """Successful message fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "messages": [
                {"ts": "1234567890.123456", "text": "Hello", "user": "U123"},
                {"ts": "1234567890.123457", "text": "World", "user": "U456"},
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        messages = platform.get_messages(channel="C123", limit=10)

        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "World"

    @patch("httpx.Client")
    def test_get_messages_filters_subtypes(self, mock_client_class):
        """Subtypes like 'channel_join' are filtered out."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "messages": [
                {"ts": "1234567890.123456", "text": "Hello", "user": "U123"},
                {"ts": "1234567890.123457", "text": "joined", "user": "U456", "subtype": "channel_join"},
                {"ts": "1234567890.123458", "text": "Bot msg", "bot_id": "B123", "subtype": "bot_message"},
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        messages = platform.get_messages(channel="C123", limit=10)

        # Should have 2 messages (normal + bot_message), channel_join filtered
        assert len(messages) == 2

    @patch("httpx.Client")
    def test_add_reaction_success(self, mock_client_class):
        """Successful reaction add."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        result = platform.add_reaction(
            channel="C123",
            message_id="1234567890.123456",
            emoji="thumbsup",
        )

        assert result["success"] is True

        # Verify emoji was stripped of colons
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["name"] == "thumbsup"

    @patch("httpx.Client")
    def test_add_reaction_strips_colons(self, mock_client_class):
        """Colons are stripped from emoji name."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        result = platform.add_reaction(
            channel="C123",
            message_id="1234567890.123456",
            emoji=":rocket:",
        )

        assert result["success"] is True
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["name"] == "rocket"

    @patch("httpx.Client")
    def test_list_channels_success(self, mock_client_class):
        """Successful channel list."""
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
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        channels = platform.list_channels()

        assert len(channels) == 2
        assert channels[0].id == "C123"
        assert channels[0].name == "general"
        assert channels[1].member_count == 30

    @patch("httpx.Client")
    def test_validate_credentials_success(self, mock_client_class):
        """Successful credential validation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "user": "testbot",
            "user_id": "U123",
            "team": "Test Team",
            "team_id": "T123",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-test")
        result = platform.validate_credentials()

        assert result["valid"] is True
        assert result["user"] == "testbot"
        assert result["team"] == "Test Team"

    @patch("httpx.Client")
    def test_validate_credentials_invalid_token(self, mock_client_class):
        """Invalid token validation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": False,
            "error": "invalid_auth",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = SlackPlatform(token="xoxb-invalid")
        result = platform.validate_credentials()

        assert result["valid"] is False
        assert "invalid_auth" in result["error"]

    def test_context_manager(self):
        """Platform can be used as context manager."""
        with SlackPlatform(token="xoxb-test") as platform:
            assert platform.platform_name == "slack"


class TestSlackAPIError:
    """Tests for SlackAPIError exception."""

    def test_error_message(self):
        """Error includes message."""
        error = SlackAPIError("channel_not_found")
        assert "channel_not_found" in str(error)

    def test_error_with_response_data(self):
        """Error includes response data."""
        error = SlackAPIError(
            "channel_not_found",
            response_data={"ok": False, "error": "channel_not_found"},
        )
        assert error.response_data["error"] == "channel_not_found"
