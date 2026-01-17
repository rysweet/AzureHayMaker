"""Azure HayMaker - Autonomous Azure Infrastructure Testing Framework."""

from azure_haymaker import constants
from azure_haymaker.agent_base import AgentBase, AgentConfig, SimpleAgent

# Phase 4: Tenant-isolated storage and telemetry
from azure_haymaker.storage import TenantStorageManager, get_tenant_blob_path
from azure_haymaker.telemetry import (
    TenantTelemetryContext,
    create_tenant_span,
    get_current_tenant_id,
    set_tenant_context,
)


def hello() -> str:
    return "Hello from azure-haymaker!"


__all__ = [
    # Constants (Issue #21)
    "constants",
    # Agent base classes
    "AgentBase",
    "AgentConfig",
    "SimpleAgent",
    "hello",
    # Phase 4: Tenant-isolated storage
    "TenantStorageManager",
    "get_tenant_blob_path",
    # Phase 4: Tenant telemetry
    "TenantTelemetryContext",
    "create_tenant_span",
    "get_current_tenant_id",
    "set_tenant_context",
]

# Trigger dev deployment
# Trigger CI
