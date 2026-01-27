"""Tests for logging configuration module."""

import logging
import tempfile
from pathlib import Path

import pytest

from framework.logging_config import (
    disable_framework_logging,
    get_logger,
    set_framework_log_level,
    setup_logging,
)


def test_setup_logging_basic():
    """Test basic logging setup."""
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    assert logger.level == logging.NOTSET  # Inherits from root
    assert logging.getLogger().level == logging.INFO


def test_setup_logging_with_file():
    """Test logging setup with file output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        setup_logging(level="DEBUG", log_file=log_file)

        logger = get_logger(__name__)
        logger.debug("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content


def test_setup_logging_custom_format():
    """Test logging setup with custom format."""
    custom_format = "%(levelname)s: %(message)s"
    setup_logging(level="INFO", format_string=custom_format)

    # Should not raise any errors
    logger = get_logger(__name__)
    logger.info("Test")


def test_get_logger():
    """Test logger creation."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_set_framework_log_level():
    """Test setting framework log level."""
    # Create a framework logger
    framework_logger = logging.getLogger("framework.test")

    set_framework_log_level("DEBUG")
    assert framework_logger.level == logging.DEBUG

    set_framework_log_level("WARNING")
    assert framework_logger.level == logging.WARNING


def test_disable_framework_logging():
    """Test disabling framework logging."""
    framework_logger = logging.getLogger("framework")
    disable_framework_logging()

    # Logger should be set to a level higher than CRITICAL
    assert framework_logger.level > logging.CRITICAL


def test_setup_logging_without_timestamp():
    """Test logging setup without timestamps."""
    setup_logging(level="INFO", include_timestamp=False)

    # Should not raise any errors
    logger = get_logger(__name__)
    logger.info("Test without timestamp")


def test_logging_levels():
    """Test different logging levels."""
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        setup_logging(level=level)
        numeric_level = getattr(logging, level)
        assert logging.getLogger().level == numeric_level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
