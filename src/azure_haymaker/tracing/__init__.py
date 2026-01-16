"""Azure HayMaker Distributed Tracing Module.

Provides OpenTelemetry-based distributed tracing with Azure Application Insights export.
Enables cross-container trace correlation for the orchestration workflow.

Philosophy:
- Single responsibility: Tracing initialization and context propagation
- Backward compatible: Tracing is optional via environment configuration
- Self-contained: All tracing logic isolated in this module

Public API (the "studs"):
    init_tracing: Initialize OpenTelemetry with optional Application Insights export
    get_tracer: Get a named tracer instance for creating spans
    TraceContext: Dataclass for trace context propagation across containers

Example:
    >>> from azure_haymaker.tracing import init_tracing, get_tracer, TraceContext
    >>> init_tracing("my-service")
    >>> tracer = get_tracer(__name__)
    >>> with tracer.start_as_current_span("operation"):
    ...     # traced operation
    ...     pass
"""

from azure_haymaker.tracing.context import TraceContext
from azure_haymaker.tracing.core import get_tracer, init_tracing

__all__ = ["init_tracing", "get_tracer", "TraceContext"]
