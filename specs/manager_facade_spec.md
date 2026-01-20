# Module Specification: manager.py (Facade)

## Purpose
Backward compatibility facade that composes the three modules and preserves the original EndpointManager API.

## Responsibility
Provides the original public API by delegating to lifecycle, providers, and fallback modules.

## Public API

### Exports (`__all__`)
```python
__all__ = [
    "EndpointManager",
    "ProvisioningError",
    "AllEndpointsFailedError",
]
```

### Class: `EndpointManager`

Unified endpoint management for knowledge workers.

Coordinates provisioning and management across all endpoint types
with cascade fallback support:
- Windows 365 Cloud PCs (for rich telemetry)
- Azure Windows VMs (fallback for Computer Use Agents)
- M365 CLI Containers (for cost-effective scale)

**Attributes**:
- `_lifecycle`: EndpointLifecycleManager instance
- `_providers`: EndpointProviderManager instance
- `_fallback`: EndpointFallbackCoordinator instance
- `run_id`: HayMaker run ID for this deployment

**Methods**:

#### `__init__(cloud_pc_manager=None, windows_vm_manager=None, container_manager=None, graph_client=None, config=None, run_id="")`
Initialize EndpointManager.

**IMPORTANT**: This signature MUST match the original exactly for backward compatibility.

Args:
- `cloud_pc_manager`: Pre-configured Cloud PC manager (optional)
- `windows_vm_manager`: Pre-configured Windows VM manager (optional)
- `container_manager`: Pre-configured container manager (optional)
- `graph_client`: Microsoft Graph API client (for default managers)
- `config`: Orchestrator configuration (for default managers)
- `run_id`: HayMaker run ID for resource tagging

Implementation:
```python
self.run_id = run_id
self._providers = EndpointProviderManager(
    cloud_pc_manager, windows_vm_manager, container_manager,
    graph_client, config, run_id
)
self._lifecycle = EndpointLifecycleManager(run_id)
self._fallback = EndpointFallbackCoordinator(self._providers)

# Keep references for backward compatibility properties
self.cloud_pc_manager = self._providers.cloud_pc_manager
self.windows_vm_manager = self._providers.windows_vm_manager
self.container_manager = self._providers.container_manager
```

#### `async provision_endpoint(worker: WorkerIdentity, activity_config: WorkerConfig) -> str`
Provision an endpoint for a worker based on their endpoint type.

Delegates to providers and tracks in lifecycle.

Args:
- `worker`: Worker identity with endpoint_type specified
- `activity_config`: Activity configuration for the worker

Returns:
- Endpoint ID

#### `async provision_endpoint_with_fallback(worker: WorkerIdentity) -> dict[str, Any]`
Provision an endpoint with cascade fallback support.

Delegates to fallback coordinator and tracks successful provision in lifecycle.

Args:
- `worker`: Worker identity to provision endpoint for

Returns:
- Result dictionary

Raises:
- `AllEndpointsFailedError`: If all endpoint types fail

#### `async provision_batch(workers: list[tuple[WorkerIdentity, WorkerConfig]]) -> dict[str, str]`
Provision endpoints for multiple workers.

Implementation:
- Separates workers by endpoint type
- Provisions Cloud PCs sequentially (calling provision_endpoint for each)
- Provisions containers in batch (if container_manager supports it)
- Tracks all in lifecycle

Args:
- `workers`: List of (identity, config) tuples

Returns:
- Dictionary mapping worker_id to endpoint_id

#### `async delete_endpoint(worker_id: str) -> bool`
Delete an endpoint for a worker.

Implementation:
1. Get endpoint info from lifecycle
2. Delegate deletion to providers based on endpoint type
3. Untrack from lifecycle on success

Args:
- `worker_id`: Worker ID whose endpoint to delete

Returns:
- True if deleted successfully

#### `async delete_all_endpoints() -> int`
Delete all provisioned endpoints.

Implementation:
- Iterate through all tracked endpoints
- Call delete_endpoint for each
- Return count of successfully deleted

Returns:
- Number of successfully deleted endpoints

#### `async get_endpoint_status(worker_id: str) -> dict[str, Any] | None`
Get status of a worker's endpoint.

Implementation:
- Get endpoint info from lifecycle
- For containers, delegate to providers.get_container_status
- For Cloud PC/VM, return basic info (full status requires additional calls)

Args:
- `worker_id`: Worker ID to check

Returns:
- Status dictionary or None if not found

#### `def get_all_endpoints() -> dict[str, dict[str, Any]]`
Get all provisioned endpoints.

Delegates to lifecycle.

Returns:
- Dictionary mapping worker_id to endpoint info

#### `def get_endpoint_counts() -> dict[str, int]`
Get count of endpoints by type.

Delegates to lifecycle.

Returns:
- Dictionary with counts by endpoint type

## Dependencies

```python
from azure_haymaker.knowledge_worker.endpoints.lifecycle import EndpointLifecycleManager
from azure_haymaker.knowledge_worker.endpoints.providers import EndpointProviderManager, ProvisioningError
from azure_haymaker.knowledge_worker.endpoints.fallback import EndpointFallbackCoordinator, AllEndpointsFailedError
from azure_haymaker.knowledge_worker.models.worker import EndpointType, WorkerConfig, WorkerIdentity
import logging
from typing import Any
```

## Implementation Notes

- This is a FACADE pattern - delegates everything
- NO business logic here - just composition and delegation
- Maintains exact original API for backward compatibility
- Should be ~100-120 LOC (mostly delegation methods)

## Backward Compatibility Requirements

### Original Import MUST Work
```python
from azure_haymaker.knowledge_worker.endpoints.manager import EndpointManager, AllEndpointsFailedError
```

### Original Usage MUST Work
```python
manager = EndpointManager(
    cloud_pc_manager=cloud_pc,
    windows_vm_manager=vm,
    container_manager=container,
    run_id="test-run"
)

# All methods work exactly as before
result = await manager.provision_endpoint_with_fallback(worker)
status = await manager.get_endpoint_status(worker.worker_id)
counts = manager.get_endpoint_counts()
```

### All Tests MUST Pass
The entire test suite in `tests/unit/test_endpoint_manager.py` must pass without modification.

## Philosophy Alignment

- **Single Responsibility**: Facade composition only
- **Brick**: Composes other bricks
- **Stud**: Preserves original public API
- **Regeneratable**: Can be rebuilt from this spec
- **Backward Compatible**: 100% preserves original behavior
