"""
Discord platform adapter using Discord Webhooks.

Uses webhook URLs for sending messages - no bot token required.
This is a simpler integration that supports sending but not reading.

Limitations of Webhooks (vs Bot):
- Cannot read messages (send only)
- Cannot add reactions
- Cannot list channels
- Limited to channels where webhook is configured

For full Discord bot functionality, consider using discord.py library.
"""
from __future__ import annotations

from typing import Any, List, Optional

import httpx

from .base import (
    Channel,
    FileUploadResult,
    Message,
    MessagingPlatform,
    SendResult,
)


class DiscordPlatform(MessagingPlatform):
    """
    Discord platform adapter using Webhooks.
    
    Webhooks provide a simple way to send messages without a bot.
    
    Example:
        platform = DiscordPlatform(webhook_url="https://discord.com/api/webhooks/...")
        result = platform.send_message("", "Hello from Hive!")  # channel ignored for webhooks
    """
    
    DEFAULT_TIMEOUT = 30.0
    
    def __init__(
        self,
        webhook_url: str,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize Discord webhook adapter.
        
        Args:
            webhook_url: Discord webhook URL
            timeout: HTTP request timeout in seconds
        """
        self._webhook_url = webhook_url
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    @property
    def platform_name(self) -> str:
        return "discord"
    
    def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SendResult:
        """
        Send a message via Discord webhook.
        
        Note: channel parameter is ignored for webhooks - the webhook
        is already configured for a specific channel.
        
        Args:
            channel: Ignored for webhooks (channel is determined by webhook URL)
            text: Message content (Discord markdown supported)
            thread_id: Thread ID to reply to (if webhook supports threads)
            **kwargs: Additional options:
                - username: Override the webhook's default username
                - avatar_url: Override the webhook's default avatar
                - embeds: List of embed objects for rich messages
                - tts: Whether this is a TTS message
                
        Returns:
            SendResult with message details
        """
        payload: dict[str, Any] = {
            "content": text,
        }
        
        # Optional overrides
        if "username" in kwargs:
            payload["username"] = kwargs["username"]
        if "avatar_url" in kwargs:
            payload["avatar_url"] = kwargs["avatar_url"]
        if "embeds" in kwargs:
            payload["embeds"] = kwargs["embeds"]
        if kwargs.get("tts"):
            payload["tts"] = True
        
        # Thread support
        url = self._webhook_url
        if thread_id:
            url = f"{url}?thread_id={thread_id}"
        
        # Add wait=true to get message details in response
        if "?" in url:
            url = f"{url}&wait=true"
        else:
            url = f"{url}?wait=true"
        
        try:
            response = self._client.post(url, json=payload)
            
            if response.status_code == 204:
                # Success but no content (when wait=false)
                return SendResult(
                    success=True,
                    message_id=None,
                )
            
            if response.status_code not in (200, 201):
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("message", f"HTTP {response.status_code}")
                return SendResult(
                    success=False,
                    error=error_msg,
                    raw_response=error_data,
                )
            
            data = response.json()
            return SendResult(
                success=True,
                message_id=data.get("id"),
                channel=data.get("channel_id"),
                raw_response=data,
            )
            
        except httpx.HTTPStatusError as e:
            return SendResult(
                success=False,
                error=f"HTTP {e.response.status_code}: {e.response.text}",
            )
        except httpx.RequestError as e:
            return SendResult(
                success=False,
                error=f"Network error: {str(e)}",
            )
    
    def get_messages(
        self,
        channel: str,
        limit: int = 10,
        before: Optional[str] = None,
    ) -> List[Message]:
        """
        Get messages - NOT SUPPORTED for webhooks.
        
        Discord webhooks can only send messages, not read them.
        Returns empty list with a warning.
        
        For reading messages, use a Discord Bot with the discord.py library.
        """
        # Webhooks cannot read messages
        return []
    
    def add_reaction(
        self,
        channel: str,
        message_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        """
        Add reaction - NOT SUPPORTED for webhooks.
        
        Discord webhooks cannot add reactions.
        For reactions, use a Discord Bot.
        """
        return {
            "success": False,
            "error": "Discord webhooks cannot add reactions. Use a Discord Bot instead.",
        }
    
    def upload_file(
        self,
        channel: str,
        filename: str,
        content: bytes,
        title: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> FileUploadResult:
        """
        Upload a file via Discord webhook.
        
        Args:
            channel: Ignored for webhooks
            filename: Name for the file
            content: File content as bytes
            title: Ignored for Discord (use comment instead)
            comment: Message to accompany the file
            
        Returns:
            FileUploadResult with file details
        """
        files = {"file": (filename, content)}
        data: dict[str, Any] = {}
        
        if comment:
            data["content"] = comment
        
        url = f"{self._webhook_url}?wait=true"
        
        try:
            response = self._client.post(url, data=data, files=files)
            
            if response.status_code not in (200, 201):
                error_data = response.json() if response.content else {}
                return FileUploadResult(
                    success=False,
                    error=error_data.get("message", f"HTTP {response.status_code}"),
                )
            
            data = response.json()
            attachments = data.get("attachments", [])
            
            if attachments:
                return FileUploadResult(
                    success=True,
                    file_id=attachments[0].get("id"),
                    url=attachments[0].get("url"),
                )
            
            return FileUploadResult(
                success=True,
                file_id=data.get("id"),
            )
            
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            return FileUploadResult(
                success=False,
                error=str(e),
            )
    
    def list_channels(
        self,
        include_private: bool = False,
        limit: int = 100,
    ) -> List[Channel]:
        """
        List channels - NOT SUPPORTED for webhooks.
        
        Discord webhooks are bound to a single channel and cannot list others.
        For listing channels, use a Discord Bot.
        """
        return []
    
    def validate_credentials(self) -> dict[str, Any]:
        """
        Validate the Discord webhook URL.
        
        Makes a GET request to the webhook URL to verify it's valid.
        """
        try:
            # GET on webhook URL returns webhook info
            response = self._client.get(self._webhook_url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": True,
                    "name": data.get("name"),
                    "channel_id": data.get("channel_id"),
                    "guild_id": data.get("guild_id"),
                }
            else:
                return {
                    "valid": False,
                    "error": f"HTTP {response.status_code}",
                }
        except httpx.RequestError as e:
            return {
                "valid": False,
                "error": str(e),
            }
    
    def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x5865F2,  # Discord blurple
        fields: list[dict[str, Any]] | None = None,
        footer: str | None = None,
        thumbnail_url: str | None = None,
        image_url: str | None = None,
        author_name: str | None = None,
        author_icon_url: str | None = None,
    ) -> SendResult:
        """
        Send a rich embed message.
        
        This is a convenience method for creating Discord embeds.
        
        Args:
            title: Embed title
            description: Embed description
            color: Embed color as integer (default: Discord blurple)
            fields: List of field dicts with 'name', 'value', and optional 'inline'
            footer: Footer text
            thumbnail_url: URL for thumbnail image
            image_url: URL for main image
            author_name: Author name
            author_icon_url: Author icon URL
            
        Returns:
            SendResult with message details
        """
        embed: dict[str, Any] = {
            "title": title,
            "description": description,
            "color": color,
        }
        
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}
        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}
        if image_url:
            embed["image"] = {"url": image_url}
        if author_name:
            embed["author"] = {"name": author_name}
            if author_icon_url:
                embed["author"]["icon_url"] = author_icon_url
        
        return self.send_message("", "", embeds=[embed])
    
    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self) -> "DiscordPlatform":
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()
