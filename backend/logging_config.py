"""
Structured JSON Logging for Voice AI Platform

This module provides structured JSON logging for consistent, machine-parseable logs
across the entire application. It replaces print() statements and standard logging
with structured events that include context, timestamps, and severity levels.

Usage:
    from backend.logging_config import get_logger, LogContext

    logger = get_logger("my_module")
    
    # Simple log
    logger.info("User action completed", extra={"user_id": 123, "action": "update"})
    
    # With context manager
    with LogContext(agent_id=456, call_id="call_789"):
        logger.info("Processing call")
    
    # Error logging
    try:
        risky_operation()
    except Exception as e:
        logger.error("Operation failed", exc_info=True, extra={"retry_count": 3})
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional, ContextManager
from contextvars import ContextVar
import threading

# Context storage for cross-cutting concerns (agent_id, call_id, etc.)
_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON."""

    def __init__(self, include_timestamp: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "thread": record.threadName,
            "process": record.process,
        }

        # Add timestamp if enabled
        if self.include_timestamp:
            log_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Add exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_type:
                log_data["exception"] = {
                    "type": exc_type.__name__,
                    "message": str(exc_value),
                    "traceback": "".join(traceback.format_exception(*record.exc_info)),
                }

        # Add extra fields from record
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in [
                "msg", "args", "created", "filename", "funcName", "levelname",
                "levelno", "lineno", "module", "msecs", "message", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "asctime", "filename", "getMessage", "args", "msg", "level",
                "pathname", "lineno", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "module",
                "funcName", "filename", "name", "levelname", "levelno", "message"
            ]
        }

        # Add context from context var
        context = _log_context.get()
        if context:
            log_data["context"] = context

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str)


class StructuredLogger:
    """Wrapper around standard logger with structured logging support."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Add JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

        # Also add file handler for error logs
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(error_handler)

    def _log(self, level: int, msg: str, exc_info: bool = False, **kwargs: Any):
        """Internal logging method."""
        extra = kwargs.pop("extra", {})
        if exc_info:
            extra["exc_info"] = True
        self.logger.log(level, msg, extra=extra)

    def debug(self, msg: str, **kwargs: Any):
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs: Any):
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any):
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, exc_info: bool = False, **kwargs: Any):
        self._log(logging.ERROR, msg, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, exc_info: bool = False, **kwargs: Any):
        self._log(logging.CRITICAL, msg, exc_info=exc_info, **kwargs)

    def exception(self, msg: str, **kwargs: Any):
        self._log(logging.ERROR, msg, exc_info=True, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


class LogContext(ContextManager[Dict[str, Any]]):
    """Context manager for adding cross-cutting context to logs.

    Usage:
        with LogContext(agent_id=123, call_id="call_456"):
            logger.info("This log includes context")
    """

    def __init__(self, **context_kwargs: Any):
        self.context_kwargs = context_kwargs
        self.token = None

    def __enter__(self) -> Dict[str, Any]:
        current = _log_context.get()
        updated = {**current, **self.context_kwargs}
        self.token = _log_context.set(updated)
        return updated

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            _log_context.reset(self.token)
        return False


# Initialize root logger
root_logger = get_logger("voice_ai")


def configure_logging(level: str = "INFO"):
    """Configure the root logging level."""
    logging.getLogger("voice_ai").setLevel(level.upper())
