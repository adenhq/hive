from __future__ import annotations

import logging
import os

_HANDLER_ATTR = "_aden_tools_logging_handler"

def configure_logging(level: str | None = None, fmt: str | None = None) -> None:
    """
    Configure aden_tools logging once (idempotent).
    Logs go to stderr by default to keep STDIO JSON-RPC clean.
    """

    base_logger = logging.getLogger("aden_tools")

    # Avoid duplicate handlers to keep idempotent setup.
    if any(getattr(h, _HANDLER_ATTR, False) for h in base_logger.handlers):
        return

    resolved_level = (level or os.getenv("ADEN_TOOLS_LOG_LEVEL", "INFO")).upper()
    resolved_fmt = fmt or os.getenv(
        "ADEN_TOOLS_LOG_FORMAT",
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # StreamHandler defaults to stderr, which is safe for STDIO JSON-RPC.
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(resolved_fmt))
    setattr(handler, _HANDLER_ATTR, True)

    try:
        base_logger.setLevel(resolved_level)
    except ValueError:
        base_logger.setLevel("INFO")

    base_logger.addHandler(handler)
    base_logger.propagate = False

def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger. Use __name__ from modules to inherit aden_tools config.
    """

    configure_logging()

    return logging.getLogger(name or "aden_tools")