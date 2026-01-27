"""
Audit Trail Tool - Generate decision timelines from agent runs.

Provides tools to query and format decision timelines for analysis and debugging.
"""
from __future__ import annotations

from fastmcp import FastMCP

from .audit_trail_tool import register_tools

__all__ = ["register_tools"]
