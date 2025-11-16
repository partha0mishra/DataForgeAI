"""Tests for logging module."""

import pytest
from dataforge_common.logging import get_logger, JSONFormatter
import logging


def test_get_logger():
    """Test logger creation."""
    logger = get_logger("test_logger")
    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


def test_logger_level():
    """Test logger level configuration."""
    logger = get_logger("test_level", level="DEBUG")
    assert logger.level == logging.DEBUG


def test_json_formatter():
    """Test JSON formatting."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    assert "Test message" in formatted
    assert "INFO" in formatted
