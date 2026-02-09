"""
Discord Tool - Send messages and interact with Discord servers via Discord API.

Supports:
- Bot tokens (DISCORD_BOT_TOKEN)

API Reference: https://discord.com/developers/docs
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

DISCORD_API_BASE = "https://discord.com/api/v10"


class _DiscordClient:
    """Internal client wrapping Discord API calls."""

    def __init__(self, bot_token: str):
        self._token = bot_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bot {self._token}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle Discord API response format."""
        if response.status_code == 204:
            return {"success": True}

        if response.status_code != 200:
            try:
                data = response.json()
                message = data.get("message", response.text)
            except Exception:
                message = response.text
            return {"error": f"HTTP {response.status_code}: {message}"}

        return response.json()

    def list_guilds(self) -> dict[str, Any]:
        """List guilds (servers) the bot is a member of."""
        response = httpx.get(
            f"{DISCORD_API_BASE}/users/@me/guilds",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_channels(self, guild_id: str) -> dict[str, Any]:
        """List channels for a guild."""
        response = httpx.get(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/channels",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def send_message(
        self,
        channel_id: str,
        content: str,
        *,
        tts: bool = False,
    ) -> dict[str, Any]:
        """Send a message to a channel."""
        body: dict[str, Any] = {"content": content, "tts": tts}
        response = httpx.post(
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
        before: str | None = None,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Get recent messages from a channel."""
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if before:
            params["before"] = before
        if after:
            params["after"] = after

        response = httpx.get(
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Discord tools with the MCP server."""

    def _get_token() -> str | None:
        """Get Discord bot token from credential manager or environment."""
        if credentials is not None:
            token = credentials.get("discord")
            if token is not None and not isinstance(token, str):
                raise TypeError(
                    f"Expected string from credentials.get('discord'), got {type(token).__name__}"
                )
            return token
        return os.getenv("DISCORD_BOT_TOKEN")

    def _get_client() -> _DiscordClient | dict[str, str]:
        """Get a Discord client, or return an error dict if no credentials."""
        token = _get_token()
        if not token:
            return {
                "error": "Discord credentials not configured",
                "help": (
                    "Set DISCORD_BOT_TOKEN environment variable or configure via credential store"
                ),
            }
        return _DiscordClient(token)

    @mcp.tool()
    def discord_list_guilds() -> dict:
        """
        List Discord guilds (servers) the bot is a member of.

        Returns guild IDs and names. Use guild IDs with discord_list_channels.

        Returns:
            Dict with list of guilds or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.list_guilds()
            if "error" in result:
                return result
            return {"guilds": result, "success": True}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def discord_list_channels(guild_id: str) -> dict:
        """
        List channels for a Discord guild (server).

        Args:
            guild_id: Guild (server) ID. Enable Developer Mode in Discord and
                       right-click the server to copy ID. Or use discord_list_guilds.

        Returns:
            Dict with list of channels or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.list_channels(guild_id)
            if "error" in result:
                return result
            return {"channels": result, "success": True}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def discord_send_message(channel_id: str, content: str, tts: bool = False) -> dict:
        """
        Send a message to a Discord channel.

        Args:
            channel_id: Channel ID (right-click channel > Copy ID in Dev Mode)
            content: Message text (max 2000 characters)
            tts: Whether to use text-to-speech

        Returns:
            Dict with message details or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.send_message(channel_id, content, tts=tts)
            if "error" in result:
                return result
            return {"success": True, "message": result}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def discord_get_messages(
        channel_id: str,
        limit: int = 50,
        before: str | None = None,
        after: str | None = None,
    ) -> dict:
        """
        Get recent messages from a Discord channel.

        Args:
            channel_id: Channel ID
            limit: Max messages to return (1-100, default 50)
            before: Message ID to get messages before (for pagination)
            after: Message ID to get messages after (for pagination)

        Returns:
            Dict with list of messages or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.get_messages(
                channel_id, limit=limit, before=before, after=after
            )
            if "error" in result:
                return result
            return {"messages": result, "success": True}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
