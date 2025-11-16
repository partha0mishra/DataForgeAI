"""Logging utilities for DataForge platform."""

import logging
import sys
from typing import Optional
from datetime import datetime
import json


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        return json.dumps(log_data)


def get_logger(
    name: str,
    level: str = "INFO",
    format_type: str = "json",
) -> logging.Logger:
    """Get configured logger.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type (json or text)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Set level
    logger.setLevel(getattr(logging, level.upper()))

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Set formatter
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter with correlation ID support."""

    def process(self, msg, kwargs):
        """Add correlation ID to log record."""
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        if hasattr(self, "correlation_id"):
            kwargs["extra"]["correlation_id"] = self.correlation_id

        return msg, kwargs
