"""
Communication Tool - Chat logging and conversation management for agent development.

Provides tools to log, store, and analyze conversations between users, Claude, and agents
to support agent testing and improvement workflows.
"""

from .communication_tool import register_tools

__all__ = ["register_tools"]