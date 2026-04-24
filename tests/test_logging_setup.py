import logging

from kal_predict.logging_setup import TraceIDFilter, get_logger, setup_logging
from kal_predict.trace import reset_trace_id, set_trace_id


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
