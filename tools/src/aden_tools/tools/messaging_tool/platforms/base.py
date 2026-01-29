"""
Base classes for messaging platform adapters.

Provides abstract interface that all platform implementations must follow.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Message:
    """Represents a message from a messaging platform."""
    
    id: str
    """Unique message identifier (Slack: ts, Discord: message_id)"""
    
    channel: str
    """Channel ID or name where message was posted"""
    
    content: str
    """Message text content"""
    
    author: str
    """Author username or ID"""
    
    timestamp: str
    """ISO 8601 timestamp or platform-specific timestamp"""
    
    thread_id: Optional[str] = None
    """Parent thread ID if this is a reply"""
    
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional platform-specific metadata"""


@dataclass
class SendResult:
    """Result of sending a message."""
    
    success: bool
    """Whether the message was sent successfully"""
    
    message_id: Optional[str] = None
    """ID of the sent message (for reactions, threading, etc.)"""
    
    thread_id: Optional[str] = None
    """Thread ID if message started or is in a thread"""
    
    channel: Optional[str] = None
    """Channel where message was posted"""
    
    error: Optional[str] = None
    """Error message if success is False"""
    
    raw_response: Optional[dict[str, Any]] = None
    """Raw API response for debugging"""


@dataclass
class Channel:
    """Represents a channel/conversation."""
    
    id: str
    """Unique channel identifier"""
    
    name: str
    """Human-readable channel name"""
    
    is_private: bool = False
    """Whether this is a private channel/DM"""
    
    member_count: Optional[int] = None
    """Number of members (if available)"""


@dataclass
class FileUploadResult:
    """Result of uploading a file."""
    
    success: bool
    """Whether the file was uploaded successfully"""
    
    file_id: Optional[str] = None
    """Platform-specific file identifier"""
    
    url: Optional[str] = None
    """URL to access the file (if available)"""
    
    error: Optional[str] = None
    """Error message if success is False"""


class MessagingPlatform(ABC):
    """
    Abstract base class for messaging platform adapters.
    
    All platform implementations (Slack, Discord, etc.) must implement
    this interface to ensure consistent behavior across platforms.
    """
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'slack', 'discord')."""
        pass
    
    @abstractmethod
    def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SendResult:
        """
        Send a message to a channel.
        
        Args:
            channel: Channel ID or name
            text: Message text (markdown supported on most platforms)
            thread_id: Optional thread to reply to
            **kwargs: Platform-specific options
            
        Returns:
            SendResult with success status and message details
        """
        pass
    
    @abstractmethod
    def get_messages(
        self,
        channel: str,
        limit: int = 10,
        before: Optional[str] = None,
    ) -> List[Message]:
        """
        Get recent messages from a channel.
        
        Args:
            channel: Channel ID
            limit: Maximum number of messages to return (1-100)
            before: Fetch messages before this timestamp/ID
            
        Returns:
            List of Message objects, newest first
        """
        pass
    
    @abstractmethod
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
            message_id: Message ID/timestamp to react to
            emoji: Emoji name (without colons, e.g., 'thumbsup')
            
        Returns:
            Dict with 'success' bool and optional 'error' string
        """
        pass
    
    @abstractmethod
    def upload_file(
        self,
        channel: str,
        filename: str,
        content: bytes,
        title: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> FileUploadResult:
        """
        Upload a file to a channel.
        
        Args:
            channel: Channel ID to upload to
            filename: Name for the file
            content: File content as bytes
            title: Optional title for the file
            comment: Optional message to accompany the file
            
        Returns:
            FileUploadResult with success status and file details
        """
        pass
    
    @abstractmethod
    def list_channels(
        self,
        include_private: bool = False,
        limit: int = 100,
    ) -> List[Channel]:
        """
        List available channels.
        
        Args:
            include_private: Whether to include private channels/DMs
            limit: Maximum number of channels to return
            
        Returns:
            List of Channel objects
        """
        pass
    
    def validate_credentials(self) -> dict[str, Any]:
        """
        Validate that credentials are properly configured.
        
        Returns:
            Dict with 'valid' bool, 'error' string if invalid,
            and optional 'user' info if valid
        """
        # Default implementation - subclasses should override
        return {"valid": True}
