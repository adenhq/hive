"""
Messaging Tool - Send messages to Slack and Discord.

Supports:
- Slack: Send, read, react, file upload via Bot Token
- Discord: Send messages and files via Webhooks
"""
from .messaging_tool import register_tools

__all__ = ["register_tools"]
