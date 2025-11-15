"""Structured logging utilities for DataForge platform."""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict, Processor


def add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add ISO8601 timestamp to log entries."""
    from datetime import datetime

    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_log_level(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add log level to event dict."""
    if method_name == "warn":
        method_name = "warning"
    event_dict["level"] = method_name.upper()
    return event_dict


def add_logger_name(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add logger name to event dict."""
    event_dict["logger"] = logger.name
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    service_name: str = "dataforge",
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, output logs as JSON; else use human-readable format
        service_name: Name of the service for log context

    Example:
        configure_logging(log_level="DEBUG", json_format=True)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Select processors based on format
    processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add service name to all logs
    structlog.contextvars.bind_contextvars(service=service_name)

    if json_format:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console output for development
        processors.extend([
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **initial_context: Any) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__ of calling module)
        **initial_context: Additional context to bind to this logger

    Returns:
        BoundLogger: Configured logger instance

    Example:
        logger = get_logger(__name__, component="pipeline")
        logger.info("Pipeline started", pipeline_id="123")
    """
    logger = structlog.get_logger(name)

    if initial_context:
        logger = logger.bind(**initial_context)

    return logger


class LoggerAdapter:
    """
    Adapter to add structured context to logger.

    Example:
        logger = get_logger(__name__)
        with LoggerAdapter(logger, user_id="user123"):
            logger.info("Processing data")  # Automatically includes user_id
    """

    def __init__(self, logger: structlog.stdlib.BoundLogger, **context: Any):
        """
        Initialize logger adapter with context.

        Args:
            logger: Logger instance
            **context: Context variables to bind
        """
        self.logger = logger
        self.context = context

    def __enter__(self) -> structlog.stdlib.BoundLogger:
        """Enter context manager and bind context variables."""
        structlog.contextvars.bind_contextvars(**self.context)
        return self.logger

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and unbind context variables."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_function_call(logger: Optional[structlog.stdlib.BoundLogger] = None):
    """
    Decorator to log function calls with parameters and results.

    Args:
        logger: Logger instance (uses function's module logger if None)

    Example:
        @log_function_call()
        def process_data(data_id: str) -> dict:
            return {"status": "success"}
    """
    import functools
    import time

    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            start_time = time.time()

            logger.debug(
                "Function called",
                function=func_name,
                args=args[:3] if len(args) > 3 else args,  # Limit arg logging
                kwargs=kwargs,
            )

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.debug(
                    "Function completed",
                    function=func_name,
                    duration_seconds=round(duration, 3),
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "Function failed",
                    function=func_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=round(duration, 3),
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


def mask_sensitive_data(
    data: Dict[str, Any],
    sensitive_keys: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Mask sensitive data in dictionaries for logging.

    Args:
        data: Dictionary potentially containing sensitive data
        sensitive_keys: Keys to mask (default: password, token, api_key, secret)

    Returns:
        dict: Data with sensitive fields masked

    Example:
        safe_data = mask_sensitive_data({"password": "secret123"})
        # Returns: {"password": "***MASKED***"}
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "password",
            "token",
            "api_key",
            "secret",
            "secret_key",
            "access_key",
            "private_key",
            "credentials",
        ]

    masked_data = data.copy()

    for key in sensitive_keys:
        if key in masked_data:
            masked_data[key] = "***MASKED***"

    return masked_data


# Pre-configured logger for quick use
default_logger = get_logger("dataforge")
