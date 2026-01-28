"""
Sanitize tool errors for safe user-facing responses.

Do not return raw exception text or resolved paths to callers.
Log full details server-side; return generic messages only.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def sanitize_error(
    exc: BaseException,
    generic_message: str,
    *,
    path: str | None = None,
    log_level: str = "warning",
) -> str:
    """
    Log exception with full context (path, exc_info) and return a safe message.

    Use for tool error responses to avoid leaking paths or exception details.
    """
    log = getattr(logger, log_level, logger.warning)
    extra = f" path={path!r}" if path else ""
    log("Tool error: %s%s", generic_message, extra, exc_info=True)
    return generic_message


def error_response(
    exc: BaseException,
    generic_message: str,
    *,
    path: str | None = None,
    log_level: str = "warning",
) -> dict[str, Any]:
    """
    Log exception with full context and return {"error": generic_message}.
    """
    msg = sanitize_error(exc, generic_message, path=path, log_level=log_level)
    return {"error": msg}
