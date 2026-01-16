"""Azure HayMaker Tenant Telemetry Module.

Provides tenant-scoped telemetry context for cross-tenant orchestration.
Adds tenant_id dimension to all metrics and spans for isolated monitoring.

Philosophy:
- Single responsibility: Tenant context propagation in telemetry
- Backward compatible: Works without tenant context
- Self-contained: All tenant telemetry logic in this module

Public API (the "studs"):
    TenantTelemetryContext: Context manager for tenant-scoped telemetry
    set_tenant_context: Set tenant context on current span
    create_tenant_span: Create a new span with tenant context

Example:
    >>> from azure_haymaker.telemetry import TenantTelemetryContext, create_tenant_span
    >>> with TenantTelemetryContext(tenant_id="tenant-123"):
    ...     with create_tenant_span("operation", tenant_id="tenant-123"):
    ...         # All spans will have tenant_id attribute
    ...         pass
"""

from azure_haymaker.telemetry.tenant_context import (
    TenantTelemetryContext,
    create_tenant_span,
    get_current_tenant_id,
    set_tenant_context,
)

__all__ = [
    "TenantTelemetryContext",
    "create_tenant_span",
    "get_current_tenant_id",
    "set_tenant_context",
]
