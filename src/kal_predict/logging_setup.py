"""Structured logging initialization with trace ID injection."""

import json
import logging
import logging.config
import re
from pathlib import Path
from typing import Optional

from kal_predict.trace import get_trace_id

# Matches a PEM private key block so key material can never reach logs.
_PEM_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
_REDACTED = "[REDACTED_PRIVATE_KEY]"


def redact_secrets(text: str) -> str:
    """Replace any PEM private-key block in ``text`` with a redaction marker."""
    if "PRIVATE KEY" not in text:
        return text
    return _PEM_PRIVATE_KEY_RE.sub(_REDACTED, text)


class SecretRedactionFilter(logging.Filter):
    """Strip PEM private-key material from log messages and args."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_secrets(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            else:
                record.args = tuple(
                    redact_secrets(a) if isinstance(a, str) else a for a in record.args
                )
        return True


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

    # Add trace ID + secret redaction filters to all handlers
    for handler in root_logger.handlers:
        handler.addFilter(TraceIDFilter())
        handler.addFilter(SecretRedactionFilter())

    # Configure JSON formatter if requested
    if log_format == "json":
        for handler in root_logger.handlers:
            handler.setFormatter(JSONFormatter())

    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized", extra={"level": log_level, "format": log_format})


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with trace ID injection and secret redaction."""
    logger = logging.getLogger(name)
    logger.addFilter(TraceIDFilter())
    logger.addFilter(SecretRedactionFilter())
    return logger
