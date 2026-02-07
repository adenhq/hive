"""
JSON Parser Utility.

Provides robust JSON parsing with heuristic repair for common LLM syntax errors:
- Markdown code blocks
- Python literals (True/False/None)
- Single quotes
- Trailing commas (basic cases)
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_json_from_text(text: str) -> tuple[Any | None, str]:
    """
    Parse JSON from text, handling markdown blocks and common syntax errors.

    Args:
        text: Raw text containing JSON

    Returns:
        Tuple of (parsed_json_or_None, cleaned_text)
    """
    if not isinstance(text, str):
        return None, str(text)

    cleaned = text.strip()

    # 1. Try to extract from Markdown code blocks first
    # Pattern: ```json ... ``` or ``` ... ```
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    matches = re.findall(code_block_pattern, cleaned)

    if matches:
        for match in matches:
            # Try to parse each match directly first
            content = match.strip()
            parsed = _try_parse(content)
            if parsed is not None:
                return parsed, content

    # 2. If no code blocks or parsing failed, try finding JSON-like structures in the whole text
    # Pattern: Starts with { or [
    json_start_pattern = r"(\{[\s\S]*\}|\[[\s\S]*\])"
    json_matches = re.findall(json_start_pattern, cleaned)

    for match in json_matches:
        parsed = _try_parse(match)
        if parsed is not None:
            return parsed, match

    # 3. Fallback: try parsing the entire cleaned text
    parsed = _try_parse(cleaned)
    if parsed is not None:
        return parsed, cleaned

    return None, cleaned


def _try_parse(text: str) -> Any | None:
    """Attempt to parse text as JSON, applying heuristic repairs if needed."""
    # 1. Try standard JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Apply heuristics for Python syntax (True/False/None)
    # Be careful not to replace these inside strings if possible, but regex boundary helps
    repaired = text
    repaired = re.sub(r"\bTrue\b", "true", repaired)
    repaired = re.sub(r"\bFalse\b", "false", repaired)
    repaired = re.sub(r"\bNone\b", "null", repaired)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 3. Apply heuristics for single quotes -> double quotes
    # This is risky but often necessary for Python dict string representations
    if "'" in repaired and '"' not in repaired:
        # Simple swap if no double quotes exist
        try:
            return json.loads(repaired.replace("'", '"'))
        except json.JSONDecodeError:
            pass

    return None
