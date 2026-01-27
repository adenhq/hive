"""Logging configuration for the Aden Agent Framework.

This module provides utilities for configuring logging across the framework,
making it easy to set up appropriate log levels and formats for different
environments (development, production, testing).
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None,
    include_timestamp: bool = True,
) -> None:
    """Configure logging for the framework.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        format_string: Custom format string for log messages
        include_timestamp: Whether to include timestamps in log messages

    Example:
        >>> from framework.logging_config import setup_logging
        >>> setup_logging(level="DEBUG", log_file=Path("agent.log"))
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Default format with timestamp
    if format_string is None:
        if include_timestamp:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        else:
            format_string = "%(name)s - %(levelname)s - %(message)s"

    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(format_string))
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(format_string))
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> from framework.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Agent started")
    """
    return logging.getLogger(name)


def set_framework_log_level(level: str) -> None:
    """Set log level for all framework loggers.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        >>> from framework.logging_config import set_framework_log_level
        >>> set_framework_log_level("DEBUG")
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Set level for all framework loggers
    for logger_name in logging.Logger.manager.loggerDict:
        if logger_name.startswith("framework"):
            logging.getLogger(logger_name).setLevel(numeric_level)


def disable_framework_logging() -> None:
    """Disable all framework logging (useful for testing).

    Example:
        >>> from framework.logging_config import disable_framework_logging
        >>> disable_framework_logging()
    """
    logging.getLogger("framework").setLevel(logging.CRITICAL + 1)
