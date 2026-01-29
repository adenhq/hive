"""
Slack platform adapter using the Slack Web API.

Uses httpx for HTTP calls to avoid additional dependencies.
Requires a Slack Bot Token (xoxb-...) with appropriate scopes.

Required Bot Token Scopes:
- chat:write - Send messages
- channels:history - Read public channel messages
- groups:history - Read private channel messages (optional)
- reactions:write - Add reactions
- files:write - Upload files
- channels:read - List channels
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

import httpx

from .base import (
    Channel,
    FileUploadResult,
    Message,
    MessagingPlatform,
    SendResult,
)


class SlackPlatform(MessagingPlatform):
    """
    Slack platform adapter using the Web API.
    
    Example:
        platform = SlackPlatform(token="xoxb-...")
        result = platform.send_message("#general", "Hello from Hive!")
    """
    
    BASE_URL = "https://slack.com/api"
    DEFAULT_TIMEOUT = 30.0
    
    def __init__(self, token: str, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize Slack platform adapter.
        
        Args:
            token: Slack Bot Token (xoxb-...)
            timeout: HTTP request timeout in seconds
        """
        self._token = token
        self._timeout = timeout
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            timeout=timeout,
        )
    
    @property
    def platform_name(self) -> str:
        return "slack"
    
    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Parse Slack API response and handle errors."""
        response.raise_for_status()
        data = response.json()
        
        if not data.get("ok", False):
            error = data.get("error", "Unknown error")
            raise SlackAPIError(error, data)
        
        return data
    
    def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SendResult:
        """
        Send a message to a Slack channel.
        
        Args:
            channel: Channel ID (C...) or name (#general)
            text: Message text (Slack markdown supported)
            thread_id: Thread timestamp to reply to
            **kwargs: Additional options (blocks, attachments, etc.)
            
        Returns:
            SendResult with message details
        """
        payload: dict[str, Any] = {
            "channel": channel,
            "text": text,
        }
        
        if thread_id:
            payload["thread_ts"] = thread_id
        
        # Support advanced features
        if "blocks" in kwargs:
            payload["blocks"] = kwargs["blocks"]
        if "attachments" in kwargs:
            payload["attachments"] = kwargs["attachments"]
        if "unfurl_links" in kwargs:
            payload["unfurl_links"] = kwargs["unfurl_links"]
        if "unfurl_media" in kwargs:
            payload["unfurl_media"] = kwargs["unfurl_media"]
        
        try:
            response = self._client.post("/chat.postMessage", json=payload)
            data = self._handle_response(response)
            
            return SendResult(
                success=True,
                message_id=data.get("ts"),
                thread_id=data.get("message", {}).get("thread_ts"),
                channel=data.get("channel"),
                raw_response=data,
            )
        except SlackAPIError as e:
            return SendResult(
                success=False,
                error=str(e),
                raw_response=e.response_data,
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
        Get recent messages from a Slack channel.
        
        Args:
            channel: Channel ID (C...)
            limit: Number of messages to return (1-100)
            before: Fetch messages before this timestamp
            
        Returns:
            List of Message objects, newest first
        """
        limit = max(1, min(100, limit))
        
        params: dict[str, Any] = {
            "channel": channel,
            "limit": limit,
        }
        
        if before:
            params["latest"] = before
        
        try:
            response = self._client.get("/conversations.history", params=params)
            data = self._handle_response(response)
            
            messages = []
            for msg in data.get("messages", []):
                # Skip non-message types (join, leave, etc.)
                if msg.get("subtype") and msg.get("subtype") != "bot_message":
                    continue
                
                messages.append(Message(
                    id=msg.get("ts", ""),
                    channel=channel,
                    content=msg.get("text", ""),
                    author=msg.get("user", msg.get("bot_id", "unknown")),
                    timestamp=self._ts_to_iso(msg.get("ts", "")),
                    thread_id=msg.get("thread_ts"),
                    metadata={
                        "reactions": msg.get("reactions", []),
                        "reply_count": msg.get("reply_count", 0),
                        "files": msg.get("files", []),
                    },
                ))
            
            return messages
            
        except (SlackAPIError, httpx.HTTPStatusError, httpx.RequestError):
            return []
    
    def add_reaction(
        self,
        channel: str,
        message_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        """
        Add an emoji reaction to a message.
        
        Args:
            channel: Channel ID containing the message
            message_id: Message timestamp (ts)
            emoji: Emoji name without colons (e.g., 'thumbsup')
            
        Returns:
            Dict with 'success' and optional 'error'
        """
        # Remove colons if present
        emoji = emoji.strip(":")
        
        payload = {
            "channel": channel,
            "timestamp": message_id,
            "name": emoji,
        }
        
        try:
            response = self._client.post("/reactions.add", json=payload)
            self._handle_response(response)
            return {"success": True}
        except SlackAPIError as e:
            # "already_reacted" is not really an error
            if "already_reacted" in str(e):
                return {"success": True, "note": "Already reacted"}
            return {"success": False, "error": str(e)}
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            return {"success": False, "error": str(e)}
    
    def upload_file(
        self,
        channel: str,
        filename: str,
        content: bytes,
        title: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> FileUploadResult:
        """
        Upload a file to a Slack channel.
        
        Args:
            channel: Channel ID to upload to
            filename: Name for the file
            content: File content as bytes
            title: Optional title for the file
            comment: Optional message to accompany the file
            
        Returns:
            FileUploadResult with file details
        """
        # Use multipart form data for file upload
        files = {"file": (filename, content)}
        data: dict[str, Any] = {
            "channels": channel,
            "filename": filename,
        }
        
        if title:
            data["title"] = title
        if comment:
            data["initial_comment"] = comment
        
        try:
            # File uploads need different headers
            response = httpx.post(
                f"{self.BASE_URL}/files.upload",
                headers={"Authorization": f"Bearer {self._token}"},
                data=data,
                files=files,
                timeout=self._timeout,
            )
            response_data = response.json()
            
            if not response_data.get("ok", False):
                return FileUploadResult(
                    success=False,
                    error=response_data.get("error", "Upload failed"),
                )
            
            file_info = response_data.get("file", {})
            return FileUploadResult(
                success=True,
                file_id=file_info.get("id"),
                url=file_info.get("permalink"),
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
        List available Slack channels.
        
        Args:
            include_private: Whether to include private channels
            limit: Maximum number of channels to return
            
        Returns:
            List of Channel objects
        """
        limit = max(1, min(1000, limit))
        
        types = ["public_channel"]
        if include_private:
            types.append("private_channel")
        
        params = {
            "types": ",".join(types),
            "limit": limit,
            "exclude_archived": True,
        }
        
        try:
            response = self._client.get("/conversations.list", params=params)
            data = self._handle_response(response)
            
            channels = []
            for ch in data.get("channels", []):
                channels.append(Channel(
                    id=ch.get("id", ""),
                    name=ch.get("name", ""),
                    is_private=ch.get("is_private", False),
                    member_count=ch.get("num_members"),
                ))
            
            return channels
            
        except (SlackAPIError, httpx.HTTPStatusError, httpx.RequestError):
            return []
    
    def validate_credentials(self) -> dict[str, Any]:
        """
        Validate the Slack bot token.
        
        Returns:
            Dict with 'valid' bool and user/bot info if valid
        """
        try:
            response = self._client.get("/auth.test")
            data = self._handle_response(response)
            
            return {
                "valid": True,
                "user": data.get("user"),
                "user_id": data.get("user_id"),
                "team": data.get("team"),
                "team_id": data.get("team_id"),
            }
        except (SlackAPIError, httpx.HTTPStatusError, httpx.RequestError) as e:
            return {
                "valid": False,
                "error": str(e),
            }
    
    def _ts_to_iso(self, ts: str) -> str:
        """Convert Slack timestamp to ISO 8601 format."""
        try:
            # Slack ts is Unix timestamp with microseconds: "1234567890.123456"
            unix_ts = float(ts)
            dt = datetime.fromtimestamp(unix_ts)
            return dt.isoformat()
        except (ValueError, TypeError):
            return ts
    
    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self) -> "SlackPlatform":
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()


class SlackAPIError(Exception):
    """Exception raised when Slack API returns an error."""
    
    def __init__(self, message: str, response_data: dict[str, Any] | None = None):
        super().__init__(message)
        self.response_data = response_data or {}
