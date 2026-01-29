"""Tests for Discord platform adapter."""
import pytest
from unittest.mock import patch, MagicMock

from aden_tools.tools.messaging_tool.platforms.discord import DiscordPlatform


class TestDiscordPlatform:
    """Tests for DiscordPlatform class."""

    def test_platform_name(self):
        """Platform name is 'discord'."""
        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        assert platform.platform_name == "discord"
        platform.close()

    @patch("httpx.Client")
    def test_send_message_success(self, mock_client_class):
        """Successful message send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "987654321",
            "channel_id": "456",
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = platform.send_message(channel="", text="Hello!")

        assert result.success is True
        assert result.message_id == "987654321"
        assert result.channel == "456"

        # Verify payload
        call_args = mock_client.post.call_args
        assert "content" in call_args[1]["json"]
        assert call_args[1]["json"]["content"] == "Hello!"

    @patch("httpx.Client")
    def test_send_message_with_username_override(self, mock_client_class):
        """Message with custom username."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123"}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = platform.send_message(
            channel="",
            text="Hello!",
            username="CustomBot",
            avatar_url="https://example.com/avatar.png",
        )

        assert result.success is True

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["username"] == "CustomBot"
        assert call_args[1]["json"]["avatar_url"] == "https://example.com/avatar.png"

    @patch("httpx.Client")
    def test_send_message_with_embeds(self, mock_client_class):
        """Message with embeds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123"}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        embed = {
            "title": "Test Embed",
            "description": "This is a test",
            "color": 0x5865F2,
        }

        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = platform.send_message(channel="", text="", embeds=[embed])

        assert result.success is True

        call_args = mock_client.post.call_args
        assert "embeds" in call_args[1]["json"]
        assert call_args[1]["json"]["embeds"][0]["title"] == "Test Embed"

    @patch("httpx.Client")
    def test_send_message_error(self, mock_client_class):
        """API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"message": "Invalid webhook"}'
        mock_response.json.return_value = {"message": "Invalid webhook"}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/invalid")
        result = platform.send_message(channel="", text="Hello!")

        assert result.success is False
        assert "Invalid webhook" in result.error

    def test_get_messages_not_supported(self):
        """get_messages returns empty list for webhooks."""
        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        messages = platform.get_messages(channel="C123")

        assert messages == []
        platform.close()

    def test_add_reaction_not_supported(self):
        """add_reaction returns error for webhooks."""
        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = platform.add_reaction(channel="C123", message_id="123", emoji="thumbsup")

        assert result["success"] is False
        assert "cannot" in result["error"].lower()
        platform.close()

    def test_list_channels_not_supported(self):
        """list_channels returns empty list for webhooks."""
        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        channels = platform.list_channels()

        assert channels == []
        platform.close()

    @patch("httpx.Client")
    def test_upload_file_success(self, mock_client_class):
        """Successful file upload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123",
            "attachments": [
                {"id": "456", "url": "https://cdn.discord.com/attachments/..."},
            ],
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = platform.upload_file(
            channel="",
            filename="test.txt",
            content=b"Hello, World!",
            comment="Here's a file",
        )

        assert result.success is True
        assert result.file_id == "456"
        assert "discord" in result.url

    @patch("httpx.Client")
    def test_validate_credentials_success(self, mock_client_class):
        """Successful credential validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Test Webhook",
            "channel_id": "123",
            "guild_id": "456",
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = platform.validate_credentials()

        assert result["valid"] is True
        assert result["name"] == "Test Webhook"

    @patch("httpx.Client")
    def test_validate_credentials_invalid(self, mock_client_class):
        """Invalid webhook validation."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/invalid")
        result = platform.validate_credentials()

        assert result["valid"] is False
        assert "404" in result["error"]

    @patch("httpx.Client")
    def test_send_embed_convenience_method(self, mock_client_class):
        """send_embed convenience method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123"}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = platform.send_embed(
            title="Alert",
            description="Something happened!",
            color=0xFF0000,
            footer="Powered by Hive",
        )

        assert result.success is True

        call_args = mock_client.post.call_args
        embeds = call_args[1]["json"]["embeds"]
        assert len(embeds) == 1
        assert embeds[0]["title"] == "Alert"
        assert embeds[0]["color"] == 0xFF0000
        assert embeds[0]["footer"]["text"] == "Powered by Hive"

    def test_context_manager(self):
        """Platform can be used as context manager."""
        with DiscordPlatform(webhook_url="https://discord.com/api/webhooks/123/abc") as platform:
            assert platform.platform_name == "discord"
