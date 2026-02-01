"""
Hive Logging Module
===================
Centralized logging configuration for production use.

Features:
- Configurable log levels
- Console and file output
- Structured formatting
- Context-aware logging

Usage:
    from logging_config import get_logger
    
    logger = get_logger(__name__)
    logger.info("Application started")
    logger.error("Error occurred", exc_info=True)
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Log level from environment
LOG_LEVEL = os.getenv("HIVE_LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("HIVE_LOG_FILE", "")
LOG_FORMAT = os.getenv(
    "HIVE_LOG_FORMAT",
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Valid log levels
VALID_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        level: Optional override for log level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level
    log_level = VALID_LEVELS.get(level or LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt='%H:%M:%S'))
    logger.addHandler(console_handler)
    
    # File handler (if configured)
    if LOG_FILE:
        file_path = Path(LOG_FILE)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(file_handler)
    
    return logger


def configure_root_logger(level: str = "INFO", log_file: Optional[str] = None):
    """
    Configure the root logger for the application.
    
    Call this once at application startup.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
    """
    log_level = VALID_LEVELS.get(level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(file_path, encoding='utf-8'))
    
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt='%H:%M:%S',
        handlers=handlers
    )


class LogContext:
    """
    Context manager for temporary log level changes.
    
    Usage:
        with LogContext("DEBUG"):
            logger.debug("This will be logged")
    """
    
    def __init__(self, level: str, logger_name: Optional[str] = None):
        self.level = VALID_LEVELS.get(level.upper(), logging.DEBUG)
        self.logger = logging.getLogger(logger_name)
        self.original_level = self.logger.level
    
    def __enter__(self):
        self.logger.setLevel(self.level)
        return self
    
    def __exit__(self, *args):
        self.logger.setLevel(self.original_level)


# Convenience functions for quick logging
def log_info(message: str):
    """Quick info log."""
    logging.info(message)

def log_error(message: str, exc_info: bool = False):
    """Quick error log."""
    logging.error(message, exc_info=exc_info)

def log_warning(message: str):
    """Quick warning log."""
    logging.warning(message)

def log_debug(message: str):
    """Quick debug log."""
    logging.debug(message)


# Alias for compatibility
def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup logging for the application.
    
    This is an alias for configure_root_logger for backward compatibility.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
    """
    configure_root_logger(level, log_file)
