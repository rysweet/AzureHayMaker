# Orchestrator Cleanup Refactoring Specification

## Overview

The orchestrator cleanup module has been refactored from a single 518-line file into three focused modules, each under 300 LOC, following the Bricks & Studs pattern for improved maintainability and clarity.

## Module Architecture

### 1. resource_graph.py (~173 LOC)

**Purpose**: Query Azure Resource Graph for AzureHayMaker-managed resources

**Public API** (`__all__`):
- `CleanupStatus` - Enum for cleanup operation status
- `CleanupReport` - Pydantic model for cleanup results
- `query_managed_resources` - Query resources for a specific run
- `verify_cleanup_complete` - Verify all resources deleted

**Usage**:
```python
from azure_haymaker.orchestrator.cleanup.resource_graph import (
    query_managed_resources,
    verify_cleanup_complete,
    CleanupReport,
    CleanupStatus,
)

# Query managed resources for a run
resources = await query_managed_resources(
    subscription_id="sub-12345",
    run_id="run-abc-123"
)

# Verify cleanup completion
report = await verify_cleanup_complete(run_id="run-abc-123")
if report.status == CleanupStatus.VERIFIED:
    print("All resources deleted successfully")
```

### 2. resource_deletion.py (~173 LOC)

**Purpose**: Delete Azure resources with retry logic for dependency handling

**Public API** (`__all__`):
- `ResourceDeletion` - Pydantic model for deletion attempt records
- `force_delete_resources` - Delete resources with retry logic

**Usage**:
```python
from azure_haymaker.orchestrator.cleanup.resource_deletion import (
    force_delete_resources,
    ResourceDeletion,
)

# Force delete remaining resources with automatic retry
report = await force_delete_resources(
    resources=remaining_resources,
    subscription_id="sub-12345"
)

print(f"Deleted {report.total_resources_deleted}/{report.total_resources_expected} resources")
```

### 3. sp_cleanup.py (~172 LOC)

**Purpose**: Delete service principals and their Key Vault secrets

**Public API** (`__all__`):
- `delete_service_principals` - Delete SPs and their secrets

**Usage**:
```python
from azure_haymaker.orchestrator.cleanup.sp_cleanup import delete_service_principals

# Delete service principals and secrets
deleted_sps = await delete_service_principals(
    sp_details=sp_list,
    kv_client=key_vault_client
)

print(f"Deleted {len(deleted_sps)} service principals")
```

### 4. cleanup.py (coordinator, ~20 LOC)

**Purpose**: Backward-compatible re-export module

The main `cleanup.py` module now serves as a coordinator that re-exports all public APIs from the specialized modules. This maintains backward compatibility with existing code.

**Usage** (backward compatible):
```python
# Old imports still work
from azure_haymaker.orchestrator.cleanup import (
    CleanupStatus,
    CleanupReport,
    ResourceDeletion,
    query_managed_resources,
    verify_cleanup_complete,
    force_delete_resources,
)
```

## Design Principles

### Bricks & Studs Pattern

Each module is a self-contained "brick" with clear "studs" (public API):
- **Brick**: Self-contained module with ONE responsibility
- **Stud**: Public contracts defined via `__all__`
- **Regeneratable**: Can be rebuilt from spec without breaking connections

### Separation of Concerns

1. **resource_graph.py**: Queries Azure Resource Graph (read operations)
2. **resource_deletion.py**: Deletes Azure resources (write operations)
3. **sp_cleanup.py**: Manages service principal lifecycle (identity operations)

### Backward Compatibility

All existing imports from `azure_haymaker.orchestrator.cleanup` continue to work without modification. Tests require no changes.

## Coordination with knowledge_worker/cleanup/cleanup_manager.py

These modules handle different resource types:

- **orchestrator/cleanup**: Azure Resource Manager resources (VMs, networks, resource groups)
- **knowledge_worker/cleanup**: M365/Entra resources (users, groups, Teams, Cloud PCs)

Both use similar patterns (CleanupReport, retry logic) but different APIs (Azure RM vs Microsoft Graph).

## Module Specifications

### resource_graph.py

**Responsibility**: Query Azure Resource Graph for managed resources

**Dependencies**:
- `azure.mgmt.resourcegraph` - Resource Graph queries
- `azure_haymaker.utils.credentials` - Azure credentials
- `azure_haymaker.models.resource` - Resource model

**Key Functions**:
- `_query_azure_resources` - Internal query logic (shared by query and verify)
- `query_managed_resources` - Query with pagination support
- `verify_cleanup_complete` - Verify zero resources remain

**Models**:
- `CleanupStatus` - VERIFIED | VERIFICATION_FAILED | PARTIAL_FAILURE | FORCE_DELETION_COMPLETE
- `CleanupReport` - Contains status, resource counts, deletion records, remaining resources

### resource_deletion.py

**Responsibility**: Delete Azure resources with dependency-aware retry logic

**Dependencies**:
- `azure.mgmt.resource` - Resource Management Client
- `azure_haymaker.utils.credentials` - Azure credentials
- `azure_haymaker.models.resource` - Resource model

**Key Functions**:
- `force_delete_resources` - Main deletion coordinator
- `_delete_resource_with_retry` - Single resource deletion with exponential backoff

**Retry Logic**:
- Max 5 attempts per resource
- Exponential backoff (2^attempt seconds, max 60s)
- Retries on: conflict, contains, dependency, locked errors
- No retry on: authentication, non-retryable HTTP errors
- ResourceNotFoundError treated as success (idempotent)

**Models**:
- `ResourceDeletion` - Record with resource_id, status, attempts, error, deleted_at

### sp_cleanup.py

**Responsibility**: Delete service principals and Key Vault secrets

**Dependencies**:
- `msgraph.graph_service_client` - Microsoft Graph API
- `azure.keyvault.secrets` - Key Vault secret management
- `azure_haymaker.utils.credentials` - Azure credentials
- `azure_haymaker.orchestrator.sp_manager` - OData sanitization

**Key Functions**:
- `delete_service_principals` - Main SP deletion function
  - Finds SP by display name using OData filter
  - Deletes SP from Entra ID
  - Deletes corresponding Key Vault secret
  - Returns list of successfully deleted SP names

## Testing Strategy

### Existing Tests Continue to Work

All tests in `tests/unit/test_cleanup.py` continue to pass without modification due to backward-compatible re-exports in main `cleanup.py` module.

### Test Coverage Maintained

- **Resource Graph Queries**: 7 tests
  - Success scenarios
  - Empty results
  - Pagination
  - Filtering
  - Error handling

- **Cleanup Verification**: 6 tests
  - All resources deleted
  - Partial deletion
  - Remaining resources
  - Resource details

- **Resource Deletion**: 10 tests
  - Single/multiple resources
  - Retry logic
  - Max retries
  - Not found handling
  - Timestamp recording
  - Service principal deletion

- **CleanupReport**: 3 tests
  - Creation
  - Failure detection
  - Success validation

**Total**: 26 tests, 100% pass rate maintained

## Migration Guide

### For New Code

Use the specific modules directly for clarity:

```python
# Recommended for new code
from azure_haymaker.orchestrator.cleanup.resource_graph import query_managed_resources
from azure_haymaker.orchestrator.cleanup.resource_deletion import force_delete_resources
from azure_haymaker.orchestrator.cleanup.sp_cleanup import delete_service_principals
```

### For Existing Code

No changes needed - all imports continue to work:

```python
# Existing imports work unchanged
from azure_haymaker.orchestrator.cleanup import (
    query_managed_resources,
    force_delete_resources,
)
```

## Success Criteria

- ✅ 3 modules, each <300 LOC
- ✅ Clear separation of concerns
- ✅ `__all__` exports defined for each module
- ✅ 100% backward compatibility
- ✅ All 26 tests pass without modification
- ✅ Philosophy compliant (Bricks & Studs, Zero-BS, Ruthless Simplicity)

## Files Created

```
src/azure_haymaker/orchestrator/cleanup/
├── __init__.py              # Package initialization
├── resource_graph.py        # Resource Graph queries (~173 LOC)
├── resource_deletion.py     # Resource deletion logic (~173 LOC)
└── sp_cleanup.py           # Service principal cleanup (~172 LOC)

src/azure_haymaker/orchestrator/cleanup.py  # Coordinator with re-exports (~20 LOC)
```

## Implementation Notes

### Line Count Targets

- `resource_graph.py`: 173 LOC (models + 3 functions)
- `resource_deletion.py`: 173 LOC (model + 2 functions)
- `sp_cleanup.py`: 172 LOC (1 function with Graph/KV operations)
- `cleanup.py`: 20 LOC (imports + `__all__` only)

### Import Strategy

Each new module imports only what it needs:
- Minimize cross-dependencies between cleanup modules
- Share models via imports (e.g., `CleanupReport` used across modules)
- Keep imports at top of file for clarity

### Error Handling

Maintain existing error handling patterns:
- `CleanupError` for cleanup-specific failures
- `CredentialError` for authentication issues
- Detailed logging at INFO (success) and ERROR (failures) levels
- All errors include context (run_id, resource_id, etc.)

## Quality Audit Compliance

This refactoring addresses Quality Audit #237 requirement:
- **Before**: cleanup.py = 518 LOC (173% over limit)
- **After**: 3 modules averaging 173 LOC each (all under 300 LOC limit)

Related to PR #262 (cleanup_manager.py refactoring for Knowledge Worker cleanup).
