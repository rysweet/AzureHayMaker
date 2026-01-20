# Module Specification: lifecycle.py

## Purpose
Endpoint lifecycle management - tracking WHO has what endpoints, their status, and statistics.

## Responsibility
Manages the lifecycle state of provisioned endpoints without knowing HOW they were provisioned.

## Public API

### Exports (`__all__`)
```python
__all__ = ["EndpointLifecycleManager"]
```

### Class: `EndpointLifecycleManager`

**State**:
```python
_provisioned_endpoints: dict[str, dict[str, Any]]  # worker_id -> endpoint info
run_id: str
```

**Methods**:

#### `__init__(run_id: str = "")`
Initialize lifecycle manager.

#### `track_endpoint(worker_id: str, endpoint_id: str, endpoint_type: EndpointType, details: dict = None) -> None`
Track a newly provisioned endpoint.

Args:
- `worker_id`: Worker identifier
- `endpoint_id`: Endpoint resource ID
- `endpoint_type`: Type of endpoint (CLOUD_PC, WINDOWS_VM, CLI_CONTAINER)
- `details`: Optional additional details

#### `untrack_endpoint(worker_id: str) -> bool`
Remove endpoint from tracking.

Args:
- `worker_id`: Worker identifier

Returns:
- True if endpoint was tracked and removed

#### `get_endpoint_info(worker_id: str) -> dict[str, Any] | None`
Get tracked endpoint information.

Args:
- `worker_id`: Worker identifier

Returns:
- Endpoint info dict or None if not found

#### `get_all_endpoints() -> dict[str, dict[str, Any]]`
Get all tracked endpoints.

Returns:
- Copy of _provisioned_endpoints dict

#### `get_endpoint_counts() -> dict[str, int]`
Get count of endpoints by type.

Returns:
- Dict mapping endpoint type to count

#### `clear_all() -> int`
Clear all tracked endpoints.

Returns:
- Number of endpoints cleared

## Dependencies

```python
from azure_haymaker.knowledge_worker.models.worker import EndpointType
from typing import Any
```

## Implementation Notes

- This module is STATEFUL - it tracks provisioned endpoints
- Does NOT know how to provision or delete - just tracks state
- Should be ~100 LOC

## Philosophy Alignment

- **Single Responsibility**: Only tracks endpoint lifecycle state
- **Brick**: Self-contained state management
- **Stud**: Clear public API via `__all__`
- **Regeneratable**: Can be rebuilt from this spec
