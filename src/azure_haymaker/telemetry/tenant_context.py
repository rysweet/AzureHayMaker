"""Tenant telemetry context for cross-tenant orchestration.

Provides tenant-scoped telemetry with:
- Tenant_id dimension added to all metrics
- Tenant-specific trace context propagation
- Isolated log queries by tenant

Integrates with OpenTelemetry to ensure all spans and metrics
include tenant identification for cross-tenant monitoring.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind, Status, StatusCode

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

# Context variable to store current tenant ID across async boundaries
_current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)

# Standard attribute names for tenant context
TENANT_ID_ATTRIBUTE = "azure.tenant_id"
EXECUTION_ID_ATTRIBUTE = "haymaker.execution_id"
SCENARIO_NAME_ATTRIBUTE = "haymaker.scenario_name"


def get_current_tenant_id() -> str | None:
    """Get the current tenant ID from context.

    Returns:
        Current tenant ID if set, None otherwise

    Example:
        >>> with TenantTelemetryContext(tenant_id="tenant-123"):
        ...     print(get_current_tenant_id())
        'tenant-123'
    """
    return _current_tenant_id.get()


def set_tenant_context(
    span: Span,
    tenant_id: str | None = None,
    execution_id: str | None = None,
    scenario_name: str | None = None,
) -> None:
    """Set tenant context attributes on a span.

    Adds tenant identification and optional execution context to the span.
    Uses current context tenant_id if not explicitly provided.

    Args:
        span: OpenTelemetry span to add attributes to
        tenant_id: Azure tenant ID (uses context if not provided)
        execution_id: Optional execution run ID
        scenario_name: Optional scenario name

    Example:
        >>> tracer = trace.get_tracer(__name__)
        >>> with tracer.start_as_current_span("operation") as span:
        ...     set_tenant_context(span, tenant_id="tenant-123", execution_id="exec-456")
    """
    # Use provided tenant_id or fall back to context
    effective_tenant_id = tenant_id or get_current_tenant_id()

    if effective_tenant_id:
        span.set_attribute(TENANT_ID_ATTRIBUTE, effective_tenant_id)

    if execution_id:
        span.set_attribute(EXECUTION_ID_ATTRIBUTE, execution_id)

    if scenario_name:
        span.set_attribute(SCENARIO_NAME_ATTRIBUTE, scenario_name)


def create_tenant_span(
    name: str,
    tenant_id: str | None = None,
    execution_id: str | None = None,
    scenario_name: str | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Span:
    """Create a new span with tenant context.

    Creates an OpenTelemetry span with tenant identification attributes.
    The span is not automatically started - use with 'with' statement or
    call span.start() manually.

    Args:
        name: Name of the span
        tenant_id: Azure tenant ID (uses context if not provided)
        execution_id: Optional execution run ID
        scenario_name: Optional scenario name
        kind: Span kind (default INTERNAL)
        attributes: Additional span attributes

    Returns:
        OpenTelemetry span with tenant context

    Example:
        >>> with create_tenant_span("process_scenario", tenant_id="tenant-123") as span:
        ...     span.set_attribute("scenario.count", 5)
        ...     # Do work
    """
    tracer = trace.get_tracer(__name__)

    # Build attributes dict
    span_attributes: dict[str, Any] = {}

    # Add tenant context
    effective_tenant_id = tenant_id or get_current_tenant_id()
    if effective_tenant_id:
        span_attributes[TENANT_ID_ATTRIBUTE] = effective_tenant_id

    if execution_id:
        span_attributes[EXECUTION_ID_ATTRIBUTE] = execution_id

    if scenario_name:
        span_attributes[SCENARIO_NAME_ATTRIBUTE] = scenario_name

    # Add custom attributes
    if attributes:
        span_attributes.update(attributes)

    return tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=span_attributes,
    )


class TenantTelemetryContext:
    """Context manager for tenant-scoped telemetry.

    Sets tenant context for all telemetry operations within the context.
    Automatically propagates tenant_id to all spans created within the scope.

    Example:
        >>> with TenantTelemetryContext(
        ...     tenant_id="tenant-123",
        ...     execution_id="exec-456",
        ... ):
        ...     # All spans created here will have tenant_id attribute
        ...     tracer = trace.get_tracer(__name__)
        ...     with tracer.start_as_current_span("operation") as span:
        ...         set_tenant_context(span)  # Picks up tenant_id from context
    """

    def __init__(
        self,
        tenant_id: str,
        execution_id: str | None = None,
        scenario_name: str | None = None,
        create_span: bool = True,
        span_name: str | None = None,
    ):
        """Initialize tenant telemetry context.

        Args:
            tenant_id: Azure tenant ID for this context
            execution_id: Optional execution run ID
            scenario_name: Optional scenario name
            create_span: Whether to create a root span (default True)
            span_name: Name for root span (default "tenant_operation")
        """
        self._tenant_id = tenant_id
        self._execution_id = execution_id
        self._scenario_name = scenario_name
        self._create_span = create_span
        self._span_name = span_name or "tenant_operation"
        self._token: Any | None = None
        self._span: Span | None = None
        self._span_context: Any | None = None

    def __enter__(self) -> TenantTelemetryContext:
        """Enter context, setting tenant ID and optionally creating span."""
        # Set tenant context variable
        self._token = _current_tenant_id.set(self._tenant_id)

        # Create root span if requested
        if self._create_span:
            self._span_context = create_tenant_span(
                name=self._span_name,
                tenant_id=self._tenant_id,
                execution_id=self._execution_id,
                scenario_name=self._scenario_name,
            )
            self._span = self._span_context.__enter__()

        logger.debug(
            f"Entered tenant telemetry context: tenant_id={self._tenant_id}, "
            f"execution_id={self._execution_id}"
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context, resetting tenant ID and closing span."""
        # Close span if created
        if self._span_context is not None:
            # Set error status if exception occurred
            if exc_type is not None and self._span is not None:
                self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))
                self._span.record_exception(exc_val)

            self._span_context.__exit__(exc_type, exc_val, exc_tb)

        # Reset context variable
        if self._token is not None:
            _current_tenant_id.reset(self._token)

        logger.debug(f"Exited tenant telemetry context: tenant_id={self._tenant_id}")

    @property
    def tenant_id(self) -> str:
        """Get the tenant ID for this context."""
        return self._tenant_id

    @property
    def execution_id(self) -> str | None:
        """Get the execution ID for this context."""
        return self._execution_id

    @property
    def scenario_name(self) -> str | None:
        """Get the scenario name for this context."""
        return self._scenario_name

    @property
    def span(self) -> Span | None:
        """Get the root span for this context (if created)."""
        return self._span

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the root span.

        Args:
            name: Event name
            attributes: Optional event attributes

        Example:
            >>> with TenantTelemetryContext(tenant_id="tenant-123") as ctx:
            ...     ctx.add_event("scenario_started", {"scenario_name": "compute-01"})
        """
        if self._span is not None:
            self._span.add_event(name, attributes=attributes)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the root span.

        Args:
            key: Attribute key
            value: Attribute value

        Example:
            >>> with TenantTelemetryContext(tenant_id="tenant-123") as ctx:
            ...     ctx.set_attribute("scenario.count", 5)
        """
        if self._span is not None:
            self._span.set_attribute(key, value)


def iter_tenant_spans(
    tenant_id: str,
    execution_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Query pattern for tenant-specific spans (documentation helper).

    This function documents the query pattern for filtering spans by tenant.
    Actual implementation depends on your telemetry backend (Application Insights,
    Jaeger, etc.).

    For Azure Application Insights, use KQL:
    ```kusto
    traces
    | where customDimensions.azure_tenant_id == "{tenant_id}"
    | where customDimensions.haymaker_execution_id == "{execution_id}"
    | order by timestamp desc
    ```

    Args:
        tenant_id: Azure tenant ID to filter by
        execution_id: Optional execution ID to filter by

    Yields:
        This is a documentation-only function showing the query pattern.
        In practice, query your telemetry backend directly.
    """
    # This is a documentation-only function
    # In practice, query Application Insights or your telemetry backend
    raise NotImplementedError(
        "Query your telemetry backend directly. "
        "See function docstring for Azure Application Insights KQL example."
    )
