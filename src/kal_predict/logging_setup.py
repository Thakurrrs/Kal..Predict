"""Structured logging initialization with trace ID injection."""

import logging
import logging.config
from pathlib import Path
from typing import Optional
import json
from kal_predict.trace import get_trace_id


class TraceIDFilter(logging.Filter):
    """Add trace_id to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject trace ID into log record."""
        record.trace_id = get_trace_id()
        return True


class JSONFormatter(logging.Formatter):
    """Format logs as JSON with trace ID."""

    def format(self, record: logging.LogRecord) -> str:
        """Format record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    config_path: Optional[Path] = None,
) -> None:
    """Initialize structured logging with trace ID injection.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json" or "text")
        config_path: Optional path to YAML config file
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Add trace ID filter to all handlers
    for handler in root_logger.handlers:
        handler.addFilter(TraceIDFilter())

    # Configure JSON formatter if requested
    if log_format == "json":
        for handler in root_logger.handlers:
            handler.setFormatter(JSONFormatter())

    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized", extra={"level": log_level, "format": log_format})


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with trace ID injection."""
    logger = logging.getLogger(name)
    logger.addFilter(TraceIDFilter())
    return logger
