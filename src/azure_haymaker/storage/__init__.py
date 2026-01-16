"""Azure HayMaker Tenant-Isolated Storage Module.

Provides tenant-scoped blob operations for cross-tenant orchestration.
Storage paths follow the format: {tenant_id}/{execution_id}/{artifact_name}

Philosophy:
- Single responsibility: Tenant-scoped storage operations
- Backward compatible: Works in single-tenant mode (no tenant prefix)
- Self-contained: All storage isolation logic in this module

Public API (the "studs"):
    TenantStorageManager: Manages tenant-scoped blob operations
    get_tenant_blob_path: Build tenant-prefixed blob path

Example:
    >>> from azure_haymaker.storage import TenantStorageManager
    >>> manager = TenantStorageManager(blob_service_client)
    >>> await manager.upload_tenant_data(
    ...     tenant_id="tenant-123",
    ...     execution_id="exec-456",
    ...     artifact_name="results.json",
    ...     data=b'{"status": "success"}',
    ... )
"""

from azure_haymaker.storage.tenant_storage import (
    TenantStorageManager,
    get_tenant_blob_path,
)

__all__ = ["TenantStorageManager", "get_tenant_blob_path"]
