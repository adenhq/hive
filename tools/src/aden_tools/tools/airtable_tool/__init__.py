"""
Airtable tool module for Aden MCP Server.

Provides tools for interacting with Airtable:
- List bases and tables
- List, create, and update records

Usage:
    from aden_tools.tools.airtable_tool import register_tools

    register_tools(mcp, credentials=credentials)
"""

from .airtable import register_tools

__all__ = ["register_tools"]
