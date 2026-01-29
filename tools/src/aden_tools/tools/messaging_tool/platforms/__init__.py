"""Platform adapters for messaging services."""
from .base import MessagingPlatform, Message, SendResult
from .slack import SlackPlatform
from .discord import DiscordPlatform

__all__ = [
    "MessagingPlatform",
    "Message",
    "SendResult",
    "SlackPlatform",
    "DiscordPlatform",
]
