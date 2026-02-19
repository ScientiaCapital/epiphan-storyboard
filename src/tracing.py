"""
Request Tracing & Structured Logging Module

Provides correlation IDs, structured JSON logging, and error categorization
for enterprise observability requirements (SOC2, debugging, SLAs).
"""

import os
import sys
import json
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from contextvars import ContextVar
from functools import wraps

# Context variable for request-scoped correlation ID
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Output format:
    {
        "timestamp": "2024-01-15T10:30:00.000Z",
        "level": "INFO",
        "message": "Request completed",
        "correlation_id": "abc-123",
        "extra": {...}
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if available
        correlation_id = _correlation_id.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add source location for errors
        if record.levelno >= logging.ERROR:
            log_entry["source"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
            }

        # Add any extra fields
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "exc_info", "exc_text",
                "message"
            }:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry)


class RequestLogger:
    """
    Request-scoped logger with correlation ID support.

    Usage:
        logger = RequestLogger("my-component")
        logger.set_correlation_id("abc-123")
        logger.info("Processing request", model="llama", tokens=100)
    """

    def __init__(self, name: str = "vllm-worker"):
        self.logger = logging.getLogger(name)

    def set_correlation_id(self, correlation_id: str):
        """Set the correlation ID for the current request context"""
        _correlation_id.set(correlation_id)

    def get_correlation_id(self) -> str:
        """Get the current correlation ID"""
        return _correlation_id.get()

    def clear_correlation_id(self):
        """Clear the correlation ID"""
        _correlation_id.set("")

    def _log(self, level: int, message: str, **kwargs):
        """Log with extra fields"""
        extra = kwargs if kwargs else {}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def request_start(
        self,
        request_id: str,
        route: str = "",
        model: str = "",
        stream: bool = False,
        **kwargs
    ):
        """Log request start with standard fields"""
        self.info(
            "Request started",
            request_id=request_id,
            route=route,
            model=model,
            stream=stream,
            **kwargs
        )

    def request_complete(
        self,
        request_id: str,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        **kwargs
    ):
        """Log request completion with standard fields"""
        level = logging.INFO if success else logging.ERROR
        self._log(
            level,
            "Request completed",
            request_id=request_id,
            latency_ms=round(latency_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=success,
            **kwargs
        )

    def request_error(
        self,
        request_id: str,
        error_code: str,
        error_message: str,
        **kwargs
    ):
        """Log request error with categorization"""
        self.error(
            "Request failed",
            request_id=request_id,
            error_code=error_code,
            error_message=error_message,
            **kwargs
        )


# Error codes for categorization
class ErrorCodes:
    # Client errors (4xx)
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_MODEL = "INVALID_MODEL"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    CONTEXT_LENGTH_EXCEEDED = "CONTEXT_LENGTH_EXCEEDED"
    CONTENT_FILTER = "CONTENT_FILTER"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    MODEL_NOT_LOADED = "MODEL_NOT_LOADED"
    OUT_OF_MEMORY = "OUT_OF_MEMORY"
    TIMEOUT = "TIMEOUT"
    ENGINE_ERROR = "ENGINE_ERROR"

    @staticmethod
    def categorize_error(error_message: str) -> str:
        """Categorize an error message into an error code"""
        message_lower = error_message.lower()

        if "context length" in message_lower or "max_tokens" in message_lower:
            return ErrorCodes.CONTEXT_LENGTH_EXCEEDED
        elif "model" in message_lower and ("not found" in message_lower or "invalid" in message_lower):
            return ErrorCodes.INVALID_MODEL
        elif "out of memory" in message_lower or "oom" in message_lower:
            return ErrorCodes.OUT_OF_MEMORY
        elif "timeout" in message_lower:
            return ErrorCodes.TIMEOUT
        elif "parameter" in message_lower or "invalid" in message_lower:
            return ErrorCodes.INVALID_PARAMETERS
        else:
            return ErrorCodes.INTERNAL_ERROR


def setup_structured_logging(
    level: str = "INFO",
    json_format: bool = True
):
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, output JSON; otherwise use standard format
    """
    # Get level from env or parameter
    log_level = os.getenv("LOG_LEVEL", level).upper()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers
    root_logger.handlers = []

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level))

    # Set formatter based on preference
    use_json = os.getenv("LOG_FORMAT", "json" if json_format else "text").lower() == "json"

    if use_json:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        ))

    root_logger.addHandler(handler)

    return root_logger


# Global logger instance
_request_logger: Optional[RequestLogger] = None


def get_logger() -> RequestLogger:
    """Get or create the global request logger"""
    global _request_logger
    if _request_logger is None:
        _request_logger = RequestLogger()
    return _request_logger
