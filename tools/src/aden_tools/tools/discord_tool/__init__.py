"""
Discord integration tool for Aden Tools.

Allows agents to interact with Discord channels and messages.
Uses the Discord API v10.
"""

import logging
from typing import Any, Optional

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialManager

logger = logging.getLogger(__name__)


class DiscordClient:
    """Client for interacting with the Discord API."""

    def __init__(self, bot_token: str):
        """
        Initialize the Discord client.

        Args:
            bot_token: Discord Bot Token.
        """
        self.bot_token = bot_token
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "AdenTools/1.0",
        }

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Make a request to the Discord API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                )
                response.raise_for_status()
                # Some endpoints return 204 No Content
                if response.status_code == 204:
                    return None
                return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = f" - {e.response.text}"
            except Exception:
                pass
            logger.error(f"Discord API error: {e.response.status_code}{error_detail}")
            raise ValueError(f"Discord API error: {e.response.status_code}{error_detail}")
        except Exception as e:
            logger.error(f"Discord request failed: {str(e)}")
            raise RuntimeError(f"Discord request failed: {str(e)}")

    def list_channels(self, guild_id: str) -> list[dict[str, Any]]:
        """List channels in a guild."""
        return self._request("GET", f"guilds/{guild_id}/channels")

    def send_message(self, channel_id: str, content: str) -> dict[str, Any]:
        """Send a message to a channel."""
        payload = {"content": content}
        return self._request("POST", f"channels/{channel_id}/messages", json_data=payload)

    def get_recent_messages(self, channel_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent messages from a channel."""
        params = {"limit": limit}
        return self._request("GET", f"channels/{channel_id}/messages", params=params)


def register_tools(mcp: FastMCP, credentials: Optional[CredentialManager] = None) -> None:
    """Register Discord tools with the MCP server."""

    def get_client() -> DiscordClient:
        if credentials:
            bot_token = credentials.get("discord")
        else:
            import os
            bot_token = os.getenv("DISCORD_BOT_TOKEN")

        if not bot_token:
            raise ValueError("DISCORD_BOT_TOKEN must be set")
        
        return DiscordClient(bot_token)

    @mcp.tool()
    def discord_list_channels(guild_id: str) -> str:
        """
        List all channels in a specific Discord guild (server).

        Args:
            guild_id: The ID of the guild/server.

        Returns:
            JSON string containing a list of channels with their IDs, names, and types.
        """
        try:
            client = get_client()
            channels = client.list_channels(guild_id)
            # Return simplified view
            # Filter for text channels (type 0) and maybe voice (2)?
            # Just returning basic info for all
            result = [
                {"id": c["id"], "name": c["name"], "type": c["type"]}
                for c in channels
            ]
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing channels: {str(e)}"

    @mcp.tool()
    def discord_send_message(channel_id: str, content: str) -> str:
        """
        Send a text message to a Discord channel.

        Args:
            channel_id: The ID of the channel to send to.
            content: The text message content.

        Returns:
            JSON string with the sent message details (ID, content).
        """
        try:
            client = get_client()
            result = client.send_message(channel_id, content)
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error sending message: {str(e)}"

    @mcp.tool()
    def discord_get_recent_messages(channel_id: str, limit: int = 10) -> str:
        """
        Get recent messages from a Discord channel.

        Args:
            channel_id: The ID of the channel.
            limit: Number of messages to retrieve (default 10, max 100).

        Returns:
            JSON string containing list of messages.
        """
        try:
            client = get_client()
            messages = client.get_recent_messages(channel_id, limit)
            # Simplify
            result = [
                {
                    "id": m["id"],
                    "author": m["author"]["username"],
                    "content": m["content"],
                    "timestamp": m["timestamp"]
                }
                for m in messages
            ]
            import json
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error fetching messages: {str(e)}"
