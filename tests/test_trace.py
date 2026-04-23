import uuid
from kal_predict.trace import (
    generate_trace_id,
    set_trace_id,
    get_trace_id,
    reset_trace_id,
)


def test_generate_trace_id_returns_uuid():
    """Test that trace IDs are valid UUIDs."""
    trace_id = generate_trace_id()
    assert uuid.UUID(trace_id)  # Raises if invalid


def test_get_trace_id_auto_generates():
    """Test that get_trace_id generates a new ID if not set."""
    reset_trace_id()
    trace_id = get_trace_id()
    assert trace_id is not None
    assert uuid.UUID(trace_id)


def test_set_and_get_trace_id():
    """Test that trace IDs can be set and retrieved."""
    reset_trace_id()
    test_id = "test-trace-id-123"
    set_trace_id(test_id)
    assert get_trace_id() == test_id


def test_trace_id_persists():
    """Test that trace ID persists across calls."""
    reset_trace_id()
    id1 = get_trace_id()
    id2 = get_trace_id()
    assert id1 == id2
