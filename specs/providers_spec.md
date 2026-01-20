# Module Specification: providers.py

## Purpose
Provider-specific provisioning and deletion logic - HOW to interact with each endpoint type.

## Responsibility
Encapsulates provider-specific operations for Cloud PC, Windows VM, and CLI Container endpoints.

## Public API

### Exports (`__all__`)
```python
__all__ = ["EndpointProviderManager", "ProvisioningError"]
```

### Exception: `ProvisioningError`
Raised when endpoint provisioning fails.

### Class: `EndpointProviderManager`

**State**:
```python
cloud_pc_manager: Windows365CloudPCManager | None
windows_vm_manager: WindowsVMManager | None
container_manager: M365CLIContainerManager | None
run_id: str
```

**Methods**:

#### `__init__(cloud_pc_manager=None, windows_vm_manager=None, container_manager=None, graph_client=None, config=None, run_id="")`
Initialize provider manager with optional pre-configured managers or factory parameters.

Args:
- `cloud_pc_manager`: Pre-configured Cloud PC manager (optional)
- `windows_vm_manager`: Pre-configured Windows VM manager (optional)
- `container_manager`: Pre-configured container manager (optional)
- `graph_client`: Microsoft Graph API client (for default Cloud PC manager)
- `config`: Orchestrator configuration (for default container manager)
- `run_id`: HayMaker run ID for resource tagging

#### `async provision_cloud_pc(worker: WorkerIdentity) -> str`
Provision a Cloud PC endpoint.

Args:
- `worker`: Worker identity

Returns:
- Cloud PC ID

Raises:
- `ProvisioningError`: If manager not configured or provisioning fails

#### `async provision_cloud_pc_with_timeout(worker: WorkerIdentity) -> str | None`
Provision Cloud PC with timeout handling.

Args:
- `worker`: Worker identity

Returns:
- Cloud PC ID if successful, None if timeout

Raises:
- `ProvisioningError`: If manager not configured

#### `async provision_windows_vm(worker: WorkerIdentity) -> dict[str, Any]`
Provision a Windows VM endpoint.

Args:
- `worker`: Worker identity

Returns:
- VM details dict with keys: vm_name, public_ip, admin_username, admin_password, rdp_port

Raises:
- `ProvisioningError`: If manager not configured
- `Exception`: If provisioning or ready wait fails

#### `async provision_container(worker: WorkerIdentity, activity_config: WorkerConfig) -> str`
Provision a CLI container endpoint.

Args:
- `worker`: Worker identity
- `activity_config`: Activity configuration

Returns:
- Container resource ID

Raises:
- `ProvisioningError`: If manager not configured

#### `async delete_cloud_pc(endpoint_id: str) -> bool`
Delete a Cloud PC endpoint.

Args:
- `endpoint_id`: Cloud PC ID

Returns:
- True if deleted successfully

Raises:
- `ProvisioningError`: If manager not configured

#### `async delete_windows_vm(endpoint_id: str) -> bool`
Delete a Windows VM endpoint.

Args:
- `endpoint_id`: VM name

Returns:
- True if deleted successfully

Raises:
- `ProvisioningError`: If manager not configured

#### `async delete_container(endpoint_id: str) -> bool`
Delete a container endpoint.

Args:
- `endpoint_id`: Container resource ID

Returns:
- True if deleted successfully

Raises:
- `ProvisioningError`: If manager not configured

#### `async get_container_status(container_name: str) -> dict[str, Any]`
Get container status.

Args:
- `container_name`: Container name (last segment of resource ID)

Returns:
- Status dictionary

Raises:
- `ProvisioningError`: If manager not configured

## Dependencies

```python
from azure_haymaker.knowledge_worker.endpoints.cli_container import M365CLIContainerManager
from azure_haymaker.knowledge_worker.endpoints.cloud_pc import Windows365CloudPCManager
from azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager
from azure_haymaker.knowledge_worker.models.worker import WorkerConfig, WorkerIdentity
from typing import Any
```

## Implementation Notes

- This module encapsulates ALL provider-specific logic
- Methods are thin wrappers that delegate to appropriate manager
- Handles manager initialization with defaults
- Should be ~180 LOC

## Philosophy Alignment

- **Single Responsibility**: Provider interaction only
- **Brick**: Self-contained provider logic
- **Stud**: Clear public API via `__all__`
- **Regeneratable**: Can be rebuilt from this spec
- **Zero-BS**: All methods work or raise clear errors, no stubs
