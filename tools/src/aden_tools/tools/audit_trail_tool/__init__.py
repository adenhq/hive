"""
Audit Trail Tool - Generate decision timelines from agent runs.

Provides tools for analyzing agent decisions and creating
human-readable audit trails for debugging and compliance.
"""

from .audit_trail_tool import register_tools

__all__ = ["register_tools"]
