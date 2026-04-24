"""Trace ID generation and correlation context management."""

import contextvars
import uuid
from typing import Optional

# Context variable to store the current trace ID
_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)


def generate_trace_id() -> str:
    """Generate a new trace ID (UUID4)."""
    return str(uuid.uuid4())


def set_trace_id(trace_id: str) -> None:
    """Set the current trace ID in context."""
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """Get the current trace ID, or generate a new one if not set."""
    trace_id = _trace_id_var.get()
    if trace_id is None:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
    return trace_id


def reset_trace_id() -> None:
    """Reset the trace ID context (for testing)."""
    _trace_id_var.set(None)
