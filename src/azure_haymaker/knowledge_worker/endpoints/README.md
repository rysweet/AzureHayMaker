# Endpoint Management Modules

Modular endpoint management for Knowledge Worker Activity Framework following the Bricks & Studs pattern.

## Architecture Overview

The endpoint management system is split into four focused modules:

```
endpoints/
├── lifecycle.py       # WHO has what endpoints (tracking & status)
├── providers.py       # HOW to provision each type (Cloud PC, VM, Container)
├── fallback.py        # WHEN to try alternatives (cascade logic)
└── manager.py         # FACADE for backward compatibility
```

## Module Responsibilities

### `lifecycle.py` - Endpoint Lifecycle Management

**Purpose**: Tracks WHO has what endpoints, their status, and statistics.

**Public API**:
- `EndpointLifecycleManager` - Manages lifecycle state of provisioned endpoints

**Key Methods**:
- `track_endpoint()` - Track newly provisioned endpoint
- `untrack_endpoint()` - Remove endpoint from tracking
- `get_endpoint_info()` - Get tracked endpoint information
- `get_all_endpoints()` - Get all tracked endpoints
- `get_endpoint_counts()` - Statistics by endpoint type

**State**: Maintains `_provisioned_endpoints` dictionary

### `providers.py` - Provider-Specific Operations

**Purpose**: Encapsulates HOW to interact with each endpoint type.

**Public API**:
- `EndpointProviderManager` - Provider-specific provisioning and deletion
- `ProvisioningError` - Exception for provisioning failures

**Key Methods**:
- `provision_cloud_pc()` - Provision Cloud PC endpoint
- `provision_cloud_pc_with_timeout()` - With timeout handling
- `provision_windows_vm()` - Provision Windows VM endpoint
- `provision_container()` - Provision CLI container endpoint
- `delete_*()` - Deletion methods for each type

**Dependencies**: Wraps Cloud PC, Windows VM, and Container managers

### `fallback.py` - Cascade Fallback Coordination

**Purpose**: Orchestrates WHEN to try alternatives when provisioning fails.

**Public API**:
- `EndpointFallbackCoordinator` - Cascade fallback logic
- `AllEndpointsFailedError` - Exception when all fallbacks exhausted

**Cascade Strategy**:
1. Try Cloud PC first
2. Fallback to Windows VM if Cloud PC fails
3. Fallback to Container if Windows VM fails
4. Raise AllEndpointsFailedError if all fail

**Key Methods**:
- `provision_with_fallback()` - Main fallback orchestration

**Behavior**: Updates `worker.endpoint_type` and `worker.endpoint_id` to reflect actual provisioned type

### `manager.py` - Facade (Backward Compatibility)

**Purpose**: Provides the original EndpointManager API by composing the three modules.

**Public API** (preserved for backward compatibility):
- `EndpointManager` - Main facade class
- `ProvisioningError` - Re-exported from providers
- `AllEndpointsFailedError` - Re-exported from fallback

**Composition**:
```python
class EndpointManager:
    def __init__(self, ...):
        self._providers = EndpointProviderManager(...)
        self._lifecycle = EndpointLifecycleManager(...)
        self._fallback = EndpointFallbackCoordinator(self._providers)
```

**Methods**: All original methods preserved, delegating to appropriate module

## Usage Examples

### Basic Provisioning

```python
from azure_haymaker.knowledge_worker.endpoints.manager import EndpointManager

# Initialize (same as before)
manager = EndpointManager(
    cloud_pc_manager=cloud_pc,
    windows_vm_manager=vm,
    container_manager=container,
    run_id="haymaker-run-123"
)

# Provision endpoint (routes to specific provider)
endpoint_id = await manager.provision_endpoint(worker, activity_config)

# Get status
status = await manager.get_endpoint_status(worker.worker_id)

# Get statistics
counts = manager.get_endpoint_counts()
# Returns: {"cloud_pc": 5, "windows_vm": 2, "cli_container": 10}
```

### Fallback Provisioning

```python
# Provision with automatic fallback
result = await manager.provision_endpoint_with_fallback(worker)
# Returns: {
#     "endpoint_type": EndpointType.WINDOWS_VM,  # Fallback from Cloud PC
#     "endpoint_id": "vm-eastus-worker-001",
#     "success": True,
#     "details": {...}
# }

# Worker object is updated automatically
assert worker.endpoint_type == EndpointType.WINDOWS_VM
assert worker.endpoint_id == "vm-eastus-worker-001"
```

### Batch Provisioning

```python
workers = [
    (worker1, config1),
    (worker2, config2),
    (worker3, config3),
]

results = await manager.provision_batch(workers)
# Returns: {
#     "kw-001": "cloudpc-123",
#     "kw-002": "container-456",
#     "kw-003": "cloudpc-789"
# }
```

### Cleanup

```python
# Delete specific endpoint
success = await manager.delete_endpoint("kw-001")

# Delete all endpoints
deleted_count = await manager.delete_all_endpoints()
print(f"Deleted {deleted_count} endpoints")
```

## Design Principles

### Bricks & Studs Pattern

Each module is a self-contained "brick" with clear "studs" (public interfaces):

- **Brick** = Self-contained module with ONE responsibility
- **Stud** = Public contract defined via `__all__` exports
- **Regeneratable** = Can be rebuilt from specification independently
- **No Circular Dependencies** = Clean dependency hierarchy

### Dependency Hierarchy

```
manager.py (facade)
    ├── lifecycle.py (state tracking)
    ├── providers.py (provider operations)
    └── fallback.py (cascade logic)
            └── providers.py (provisioning)
```

NO reverse dependencies - clean one-way flow.

### Single Responsibility

- **lifecycle.py**: State tracking ONLY
- **providers.py**: Provider interaction ONLY
- **fallback.py**: Cascade coordination ONLY
- **manager.py**: Composition ONLY

## Backward Compatibility

The refactoring is **100% backward compatible**:

- Original imports work: `from ...endpoints.manager import EndpointManager`
- Original API preserved: All methods have same signatures
- Original behavior preserved: All tests pass without modification
- Original exceptions preserved: `AllEndpointsFailedError`, `ProvisioningError`

## Testing

All tests in `tests/unit/test_endpoint_manager.py` pass without modification.

Test coverage includes:
- Successful provisioning (no fallback)
- Cloud PC → Windows VM fallback
- Windows VM → Container fallback
- All endpoints fail error handling
- Worker endpoint_type updates
- Metrics tracking

## Migration from Original

NO migration required - the facade preserves the original API exactly.

Existing code continues to work:
```python
# Original code (still works)
from azure_haymaker.knowledge_worker.endpoints.manager import EndpointManager

manager = EndpointManager(cloud_pc_manager=..., run_id="...")
result = await manager.provision_endpoint_with_fallback(worker)
```

## Benefits of Refactoring

1. **Reduced Complexity**: 553 LOC → 4 focused modules (~150 LOC each)
2. **Clear Boundaries**: Each module has single responsibility
3. **Testability**: Each module can be tested independently
4. **Maintainability**: Changes isolated to specific modules
5. **Philosophy Compliance**: Follows Bricks & Studs pattern
6. **Zero Breaking Changes**: 100% backward compatible

## References

- Original file: `manager.py` (553 LOC - preserved as facade ~100 LOC)
- Pattern guide: `.claude/context/PATTERNS.md` (Bricks & Studs)
- Philosophy: `.claude/context/PHILOSOPHY.md`
- Tests: `tests/unit/test_endpoint_manager.py`
