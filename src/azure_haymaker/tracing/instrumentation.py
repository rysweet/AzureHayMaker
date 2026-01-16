"""Instrumentation helpers and decorators for tracing.

Provides convenience decorators and utilities for adding tracing to
functions and methods without cluttering business logic.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

if TYPE_CHECKING:
    from opentelemetry.trace import Span

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def traced(
    name: str | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to add tracing to a synchronous function.

    Creates a span for the decorated function, automatically recording
    exceptions and setting status.

    Args:
        name: Span name. Defaults to function name if not provided.
        kind: Span kind (INTERNAL, SERVER, CLIENT, etc.)
        attributes: Static attributes to add to every span.

    Returns:
        Decorated function with tracing.

    Example:
        >>> @traced("process-data")
        ... def process_data(data: dict) -> dict:
        ...     return {"processed": True, **data}
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=attributes,
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def traced_async(
    name: str | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Decorator to add tracing to an async function.

    Creates a span for the decorated async function, automatically recording
    exceptions and setting status.

    Args:
        name: Span name. Defaults to function name if not provided.
        kind: Span kind (INTERNAL, SERVER, CLIENT, etc.)
        attributes: Static attributes to add to every span.

    Returns:
        Decorated async function with tracing.

    Example:
        >>> @traced_async("fetch-data", kind=SpanKind.CLIENT)
        ... async def fetch_data(url: str) -> dict:
        ...     # async http call
        ...     return {"data": "..."}
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        span_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=attributes,
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def add_span_attributes(span: Span | None = None, **attributes: Any) -> None:
    """Add attributes to the current or specified span.

    Convenience function for adding multiple attributes to a span.
    Silently ignores None span (for cases where tracing may not be active).

    Args:
        span: Span to add attributes to. If None, uses current span.
        **attributes: Key-value pairs to add as span attributes.

    Example:
        >>> with tracer.start_as_current_span("operation") as span:
        ...     add_span_attributes(span, user_id="123", action="create")
    """
    if span is None:
        span = trace.get_current_span()

    if span is None or not span.is_recording():
        return

    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)


def get_current_trace_context() -> dict[str, str] | None:
    """Get the current trace context as a dictionary.

    Returns W3C trace context headers that can be propagated to downstream
    services. Returns None if no active span.

    Returns:
        Dictionary with traceparent and optionally tracestate headers,
        or None if no active span.

    Example:
        >>> ctx = get_current_trace_context()
        >>> if ctx:
        ...     headers = {**ctx}  # Add to HTTP request headers
    """
    span = trace.get_current_span()
    if span is None or not span.get_span_context().is_valid:
        return None

    ctx = span.get_span_context()

    # Format as W3C traceparent header
    # Format: version-trace_id-span_id-flags
    traceparent = f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-{ctx.trace_flags:02x}"

    return {"traceparent": traceparent}
