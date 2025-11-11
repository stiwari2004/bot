"""
Minimal OpenTelemetry helpers. Tracing is optional and enabled when opentelemetry API is installed.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

try:
    from opentelemetry import trace

    _TRACER = trace.get_tracer("app.tracing")
except Exception:  # pragma: no cover - optional dependency
    _TRACER = None


@contextmanager
def tracing_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Iterator[None]:
    """Return a context manager that records a tracing span when OpenTelemetry is configured."""
    if not _TRACER:
        yield
        return

    span = _TRACER.start_span(name)
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    try:
        with trace.use_span(span, end_on_exit=True):
            yield
    finally:
        if span.is_recording():
            span.end()



