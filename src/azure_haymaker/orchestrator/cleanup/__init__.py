"""Cleanup package for Azure HayMaker orchestrator.

This package provides modular cleanup functionality split into focused modules:
- resource_graph: Query Azure Resource Graph for managed resources
- resource_deletion: Delete resources with retry logic
- sp_cleanup: Delete service principals and secrets

For backward compatibility, all public APIs are re-exported from
azure_haymaker.orchestrator.cleanup (the parent module).
"""

from azure_haymaker.orchestrator.cleanup.resource_deletion import (
    ResourceDeletion,
    force_delete_resources,
)
from azure_haymaker.orchestrator.cleanup.resource_graph import (
    CleanupReport,
    CleanupStatus,
    query_managed_resources,
    verify_cleanup_complete,
)
from azure_haymaker.orchestrator.cleanup.sp_cleanup import delete_service_principals

__all__ = [
    "CleanupStatus",
    "CleanupReport",
    "ResourceDeletion",
    "query_managed_resources",
    "verify_cleanup_complete",
    "force_delete_resources",
    "delete_service_principals",
]
