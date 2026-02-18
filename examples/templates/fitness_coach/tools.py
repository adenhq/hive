"""Custom tools for Fitness Coach Agent.

Provides save_profile — persists user profile and sheet ID to disk so the
agent can skip intake on subsequent starts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from framework.llm.provider import Tool, ToolResult, ToolUse

logger = logging.getLogger(__name__)

PROFILE_PATH = Path.home() / ".hive" / "agents" / "fitness_coach" / "profile.json"

TOOLS = {
    "save_profile": Tool(
        name="save_profile",
        description=(
            "Save the user's profile and Google Sheet ID to disk so the agent "
            "remembers them on next startup. Call this after set_output in intake."
        ),
        parameters={
            "type": "object",
            "properties": {
                "user_profile": {
                    "type": "string",
                    "description": "JSON string of the user profile",
                },
                "sheet_id": {
                    "type": "string",
                    "description": "The Google Sheet spreadsheet ID",
                },
            },
            "required": ["user_profile", "sheet_id"],
        },
    ),
}


def _save_profile(user_profile: str, sheet_id: str) -> str:
    """Write profile and sheet_id to disk."""
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"user_profile": user_profile, "sheet_id": sheet_id}
    PROFILE_PATH.write_text(json.dumps(data, indent=2))
    logger.info("Saved profile to %s", PROFILE_PATH)
    return json.dumps({"saved": True, "path": str(PROFILE_PATH)})


def load_profile() -> dict | None:
    """Load saved profile from disk. Returns None if not found."""
    if PROFILE_PATH.exists():
        try:
            return json.loads(PROFILE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def tool_executor(tool_use: ToolUse) -> ToolResult:
    """Unified tool executor for custom tools."""
    if tool_use.name == "save_profile":
        result = _save_profile(
            user_profile=tool_use.input.get("user_profile", ""),
            sheet_id=tool_use.input.get("sheet_id", ""),
        )
        return ToolResult(tool_use_id=tool_use.id, content=result)

    return ToolResult(
        tool_use_id=tool_use.id,
        content=json.dumps({"error": f"Unknown tool: {tool_use.name}"}),
        is_error=True,
    )
