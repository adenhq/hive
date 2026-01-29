"""
Unit tests for aden_tools logging configuration.
"""

import logging
import sys
from aden_tools.utils.logging import configure_logging, get_logger

def test_configure_logging_is_idempotent():
    """
    Test that calling configure_logging multiple times does not add multiple handlers.
    This prevents duplicate log entries.
    """

    #Reset logging for testing
    logger = logging.getLogger("aden_tools")
    logger.handlers = []

    #First call
    configure_logging()
    assert len(logger.handlers) == 1

    #Second call
    configure_logging()
    assert len(logger.handlers) == 1

def test_logger_writes_to_stderr(capsys):
    """
    Test that logs are written to stderr, leaving stdout clean for JSON-RPC.
    """

    #Reset logger
    root_logger = logging.getLogger("aden_tools")
    root_logger.handlers = []

    log = get_logger("aden_tools.test_component")

    test_message = "This is a test message"
    log.info(test_message)

    captured = capsys.readouterr()

    # Assert stdout is empty (crucial for MCP/JSON-RPC)
    assert captured.out == ""

    # Assert stderr contains the message
    assert test_message in captured.err
    assert "INFO" in captured.err
    assert "test_component" in captured.err

def test_get_logger_returns_aden_tools_child():
    """Test that get_logger returns a logger under the aden_tools namespace."""
    log = get_logger("my_feature")
    assert log.name == "my_feature"

    log_default = get_logger()
    assert log_default.name == "aden_tools" 

    log_child = get_logger("aden_tools.pdf_reader")
    assert log_child.name == "aden_tools.pdf_reader"