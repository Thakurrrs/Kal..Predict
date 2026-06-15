import logging

from kal_predict.logging_setup import (
    SecretRedactionFilter,
    TraceIDFilter,
    get_logger,
    redact_secrets,
    setup_logging,
)
from kal_predict.trace import reset_trace_id, set_trace_id


def _make_record(msg, args=()):
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=msg,
        args=args,
        exc_info=None,
    )


def test_redact_secrets_masks_pem_block():
    """A PEM private key embedded in text is replaced with a marker."""
    pem = "-----BEGIN PRIVATE KEY-----\nMIIBVgIBADANBg\nsecretbytes\n-----END PRIVATE KEY-----"
    text = f"loaded key: {pem} done"
    redacted = redact_secrets(text)
    assert "secretbytes" not in redacted
    assert "BEGIN PRIVATE KEY" not in redacted
    assert "[REDACTED_PRIVATE_KEY]" in redacted


def test_redact_secrets_passes_through_clean_text():
    """Text without key material is unchanged."""
    assert redact_secrets("nothing secret here") == "nothing secret here"


def test_secret_redaction_filter_rewrites_message():
    """The logging filter strips key material from the record message."""
    pem = "-----BEGIN RSA PRIVATE KEY-----\nABCDEF\n-----END RSA PRIVATE KEY-----"
    record = _make_record(f"key={pem}")
    filter_obj = SecretRedactionFilter()
    assert filter_obj.filter(record) is True
    assert "ABCDEF" not in record.getMessage()
    assert "[REDACTED_PRIVATE_KEY]" in record.getMessage()


def test_setup_logging_initializes():
    """Test that setup_logging() completes without error."""
    reset_trace_id()
    setup_logging(log_level="DEBUG", log_format="json")
    logger = logging.getLogger("test")
    logger.info("test message")


def test_trace_id_filter_adds_trace_id():
    """Test that TraceIDFilter injects trace ID into records."""
    reset_trace_id()
    set_trace_id("test-trace-123")

    filter_obj = TraceIDFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test",
        args=(),
        exc_info=None,
    )

    assert filter_obj.filter(record) is True
    assert record.trace_id == "test-trace-123"


def test_get_logger_returns_logger():
    """Test that get_logger returns a logger instance."""
    reset_trace_id()
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"
