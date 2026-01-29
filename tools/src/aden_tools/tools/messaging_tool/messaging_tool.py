"""
Messaging Tool - Send messages to Slack and Discord.

Provides a unified interface for messaging across platforms:
- Slack: Full support (send, read, react, upload, list channels)
- Discord: Webhook-based (send, upload only)

Requires appropriate credentials:
- Slack: SLACK_BOT_TOKEN environment variable
- Discord: DISCORD_WEBHOOK_URL environment variable
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager


def register_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> None:
    """Register messaging tools with the MCP server."""

    def _get_slack_token() -> str | None:
        """Get Slack token from credentials or environment."""
        if credentials is not None:
            return credentials.get("slack")
        return os.getenv("SLACK_BOT_TOKEN")

    def _get_discord_webhook() -> str | None:
        """Get Discord webhook URL from credentials or environment."""
        if credentials is not None:
            return credentials.get("discord_webhook")
        return os.getenv("DISCORD_WEBHOOK_URL")

    @mcp.tool()
    def messaging_send(
        platform: str,
        message: str,
        channel: str = "",
        thread_id: str = "",
        username: str = "",
        avatar_url: str = "",
    ) -> dict:
        """
        Send a message to Slack or Discord.

        For Slack, requires SLACK_BOT_TOKEN. For Discord, requires DISCORD_WEBHOOK_URL.

        Args:
            platform: Platform to send to - "slack" or "discord"
            message: Message text (markdown supported on both platforms)
            channel: Channel ID for Slack (e.g., "C1234567890" or "#general").
                     Ignored for Discord webhooks (channel determined by webhook URL).
            thread_id: Optional thread ID to reply to (Slack: message timestamp)
            username: Override bot username (Discord only)
            avatar_url: Override bot avatar URL (Discord only)

        Returns:
            Dict with 'success', 'message_id', and optional 'error'
        """
        platform = platform.lower().strip()

        if platform not in ("slack", "discord"):
            return {
                "error": f"Unknown platform: {platform}. Use 'slack' or 'discord'.",
            }

        if not message:
            return {"error": "Message cannot be empty"}

        if platform == "slack":
            token = _get_slack_token()
            if not token:
                return {
                    "error": "SLACK_BOT_TOKEN environment variable not set",
                    "help": "Get a bot token at https://api.slack.com/apps",
                }

            if not channel:
                return {"error": "Channel is required for Slack messages"}

            from .platforms.slack import SlackPlatform

            try:
                with SlackPlatform(token) as slack:
                    result = slack.send_message(
                        channel=channel,
                        text=message,
                        thread_id=thread_id if thread_id else None,
                    )

                    if result.success:
                        return {
                            "success": True,
                            "platform": "slack",
                            "message_id": result.message_id,
                            "channel": result.channel,
                            "thread_id": result.thread_id,
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.error,
                        }
            except Exception as e:
                return {"error": f"Slack error: {str(e)}"}

        else:  # discord
            webhook_url = _get_discord_webhook()
            if not webhook_url:
                return {
                    "error": "DISCORD_WEBHOOK_URL environment variable not set",
                    "help": "Create a webhook at https://support.discord.com/hc/en-us/articles/228383668",
                }

            from .platforms.discord import DiscordPlatform

            try:
                kwargs = {}
                if username:
                    kwargs["username"] = username
                if avatar_url:
                    kwargs["avatar_url"] = avatar_url

                with DiscordPlatform(webhook_url) as discord:
                    result = discord.send_message(
                        channel="",  # Ignored for webhooks
                        text=message,
                        thread_id=thread_id if thread_id else None,
                        **kwargs,
                    )

                    if result.success:
                        return {
                            "success": True,
                            "platform": "discord",
                            "message_id": result.message_id,
                            "channel": result.channel,
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.error,
                        }
            except Exception as e:
                return {"error": f"Discord error: {str(e)}"}

    @mcp.tool()
    def messaging_read(
        channel: str,
        limit: int = 10,
        before: str = "",
    ) -> dict:
        """
        Read recent messages from a Slack channel.

        Note: Only supported for Slack. Discord webhooks cannot read messages.
        Requires SLACK_BOT_TOKEN with channels:history scope.

        Args:
            channel: Slack channel ID (e.g., "C1234567890")
            limit: Number of messages to return (1-100, default 10)
            before: Fetch messages before this timestamp (optional)

        Returns:
            Dict with 'success', 'messages' list, and optional 'error'
        """
        token = _get_slack_token()
        if not token:
            return {
                "error": "SLACK_BOT_TOKEN environment variable not set",
                "help": "Get a bot token at https://api.slack.com/apps",
            }

        if not channel:
            return {"error": "Channel ID is required"}

        limit = max(1, min(100, limit))

        from .platforms.slack import SlackPlatform

        try:
            with SlackPlatform(token) as slack:
                messages = slack.get_messages(
                    channel=channel,
                    limit=limit,
                    before=before if before else None,
                )

                return {
                    "success": True,
                    "platform": "slack",
                    "channel": channel,
                    "messages": [
                        {
                            "id": msg.id,
                            "content": msg.content,
                            "author": msg.author,
                            "timestamp": msg.timestamp,
                            "thread_id": msg.thread_id,
                            "reply_count": msg.metadata.get("reply_count", 0),
                        }
                        for msg in messages
                    ],
                    "count": len(messages),
                }
        except Exception as e:
            return {"error": f"Failed to read messages: {str(e)}"}

    @mcp.tool()
    def messaging_react(
        channel: str,
        message_id: str,
        emoji: str,
    ) -> dict:
        """
        Add an emoji reaction to a Slack message.

        Note: Only supported for Slack. Discord webhooks cannot add reactions.
        Requires SLACK_BOT_TOKEN with reactions:write scope.

        Args:
            channel: Slack channel ID containing the message
            message_id: Message timestamp (ts) to react to
            emoji: Emoji name without colons (e.g., "thumbsup", "rocket", "white_check_mark")

        Returns:
            Dict with 'success' and optional 'error'
        """
        token = _get_slack_token()
        if not token:
            return {
                "error": "SLACK_BOT_TOKEN environment variable not set",
                "help": "Get a bot token at https://api.slack.com/apps",
            }

        if not channel:
            return {"error": "Channel ID is required"}
        if not message_id:
            return {"error": "Message ID (timestamp) is required"}
        if not emoji:
            return {"error": "Emoji name is required"}

        from .platforms.slack import SlackPlatform

        try:
            with SlackPlatform(token) as slack:
                result = slack.add_reaction(
                    channel=channel,
                    message_id=message_id,
                    emoji=emoji,
                )

                return {
                    "success": result.get("success", False),
                    "platform": "slack",
                    "channel": channel,
                    "message_id": message_id,
                    "emoji": emoji,
                    "error": result.get("error"),
                }
        except Exception as e:
            return {"error": f"Failed to add reaction: {str(e)}"}

    @mcp.tool()
    def messaging_upload(
        platform: str,
        filename: str,
        content: str,
        channel: str = "",
        title: str = "",
        comment: str = "",
    ) -> dict:
        """
        Upload a file to Slack or Discord.

        For Slack, requires SLACK_BOT_TOKEN with files:write scope.
        For Discord, requires DISCORD_WEBHOOK_URL.

        Args:
            platform: Platform to upload to - "slack" or "discord"
            filename: Name for the file (e.g., "report.txt", "data.json")
            content: File content as string (will be encoded to UTF-8)
            channel: Channel ID for Slack. Ignored for Discord webhooks.
            title: Optional title for the file (Slack only)
            comment: Optional message to accompany the file

        Returns:
            Dict with 'success', 'file_id', 'url', and optional 'error'
        """
        platform = platform.lower().strip()

        if platform not in ("slack", "discord"):
            return {
                "error": f"Unknown platform: {platform}. Use 'slack' or 'discord'.",
            }

        if not filename:
            return {"error": "Filename is required"}
        if not content:
            return {"error": "Content is required"}

        # Encode content to bytes
        content_bytes = content.encode("utf-8")

        if platform == "slack":
            token = _get_slack_token()
            if not token:
                return {
                    "error": "SLACK_BOT_TOKEN environment variable not set",
                    "help": "Get a bot token at https://api.slack.com/apps",
                }

            if not channel:
                return {"error": "Channel is required for Slack file uploads"}

            from .platforms.slack import SlackPlatform

            try:
                with SlackPlatform(token) as slack:
                    result = slack.upload_file(
                        channel=channel,
                        filename=filename,
                        content=content_bytes,
                        title=title if title else None,
                        comment=comment if comment else None,
                    )

                    if result.success:
                        return {
                            "success": True,
                            "platform": "slack",
                            "file_id": result.file_id,
                            "url": result.url,
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.error,
                        }
            except Exception as e:
                return {"error": f"Slack upload error: {str(e)}"}

        else:  # discord
            webhook_url = _get_discord_webhook()
            if not webhook_url:
                return {
                    "error": "DISCORD_WEBHOOK_URL environment variable not set",
                    "help": "Create a webhook at https://support.discord.com/hc/en-us/articles/228383668",
                }

            from .platforms.discord import DiscordPlatform

            try:
                with DiscordPlatform(webhook_url) as discord:
                    result = discord.upload_file(
                        channel="",  # Ignored for webhooks
                        filename=filename,
                        content=content_bytes,
                        comment=comment if comment else None,
                    )

                    if result.success:
                        return {
                            "success": True,
                            "platform": "discord",
                            "file_id": result.file_id,
                            "url": result.url,
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.error,
                        }
            except Exception as e:
                return {"error": f"Discord upload error: {str(e)}"}

    @mcp.tool()
    def messaging_list_channels(
        include_private: bool = False,
        limit: int = 100,
    ) -> dict:
        """
        List available Slack channels.

        Note: Only supported for Slack. Discord webhooks cannot list channels.
        Requires SLACK_BOT_TOKEN with channels:read scope.

        Args:
            include_private: Whether to include private channels (default False)
            limit: Maximum number of channels to return (1-1000, default 100)

        Returns:
            Dict with 'success', 'channels' list, and optional 'error'
        """
        token = _get_slack_token()
        if not token:
            return {
                "error": "SLACK_BOT_TOKEN environment variable not set",
                "help": "Get a bot token at https://api.slack.com/apps",
            }

        limit = max(1, min(1000, limit))

        from .platforms.slack import SlackPlatform

        try:
            with SlackPlatform(token) as slack:
                channels = slack.list_channels(
                    include_private=include_private,
                    limit=limit,
                )

                return {
                    "success": True,
                    "platform": "slack",
                    "channels": [
                        {
                            "id": ch.id,
                            "name": ch.name,
                            "is_private": ch.is_private,
                            "member_count": ch.member_count,
                        }
                        for ch in channels
                    ],
                    "count": len(channels),
                }
        except Exception as e:
            return {"error": f"Failed to list channels: {str(e)}"}

    @mcp.tool()
    def messaging_validate(
        platform: str,
    ) -> dict:
        """
        Validate messaging credentials for a platform.

        Tests that the configured credentials are valid and working.

        Args:
            platform: Platform to validate - "slack" or "discord"

        Returns:
            Dict with 'valid' bool, platform info if valid, and 'error' if invalid
        """
        platform = platform.lower().strip()

        if platform not in ("slack", "discord"):
            return {
                "valid": False,
                "error": f"Unknown platform: {platform}. Use 'slack' or 'discord'.",
            }

        if platform == "slack":
            token = _get_slack_token()
            if not token:
                return {
                    "valid": False,
                    "error": "SLACK_BOT_TOKEN environment variable not set",
                    "help": "Get a bot token at https://api.slack.com/apps",
                }

            from .platforms.slack import SlackPlatform

            try:
                with SlackPlatform(token) as slack:
                    result = slack.validate_credentials()
                    return {
                        "platform": "slack",
                        **result,
                    }
            except Exception as e:
                return {
                    "valid": False,
                    "error": str(e),
                }

        else:  # discord
            webhook_url = _get_discord_webhook()
            if not webhook_url:
                return {
                    "valid": False,
                    "error": "DISCORD_WEBHOOK_URL environment variable not set",
                    "help": "Create a webhook at https://support.discord.com/hc/en-us/articles/228383668",
                }

            from .platforms.discord import DiscordPlatform

            try:
                with DiscordPlatform(webhook_url) as discord:
                    result = discord.validate_credentials()
                    return {
                        "platform": "discord",
                        **result,
                    }
            except Exception as e:
                return {
                    "valid": False,
                    "error": str(e),
                }
