# Endpoint Manager Refactoring Specification

## Overview
Refactor `azure_haymaker/knowledge_worker/endpoints/manager.py` (553 LOC) into 3 modular components following Bricks & Studs pattern.

## Current State Analysis

### File: `src/azure_haymaker/knowledge_worker/endpoints/manager.py`
- **Size**: 553 lines of code
- **Complexity**: High - manages 3 endpoint types with cascade fallback logic
- **Responsibilities**: Too many (violates Single Responsibility Principle)

### Current Structure
1. **Initialization & Setup** (~50 LOC)
   - EndpointManager.__init__()
   - Manager references for Cloud PC, Windows VM, Container

2. **Lifecycle Management** (~200 LOC)
   - `provision_endpoint()` - Routes to specific provider
   - `provision_batch()` - Batch provisioning
   - `delete_endpoint()` - Delete single endpoint
   - `delete_all_endpoints()` - Cleanup all
   - `get_endpoint_status()` - Status checking
   - `get_all_endpoints()` - List all
   - `get_endpoint_counts()` - Statistics

3. **Provider-Specific Logic** (~180 LOC)
   - `_provision_cloud_pc()` - Cloud PC provisioning
   - `_provision_container()` - Container provisioning
   - Private helpers for each provider type

4. **Fallback Coordination** (~120 LOC)
   - `provision_endpoint_with_fallback()` - Main fallback orchestration
   - `_provision_cloud_pc_with_fallback()` - Cloud PC with timeout
   - `_provision_windows_vm()` - Windows VM with ready wait
   - `_provision_container_with_fallback()` - Container provisioning
   - Cascade logic: Cloud PC → Windows VM → Container

### Dependencies
```python
from azure_haymaker.knowledge_worker.endpoints.cli_container import M365CLIContainerManager
from azure_haymaker.knowledge_worker.endpoints.cloud_pc import Windows365CloudPCManager
from azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager
from azure_haymaker.knowledge_worker.models.worker import EndpointType, WorkerConfig, WorkerIdentity
```

### Test Coverage
- **Test file**: `tests/unit/test_endpoint_manager.py` (609 LOC)
- **Coverage**: Comprehensive fallback testing
- **Key test scenarios**:
  - Successful provisioning (no fallback)
  - Cloud PC → Windows VM fallback
  - Windows VM → Container fallback
  - All endpoints fail error handling
  - Worker endpoint_type updates
  - Metrics tracking

## Target Architecture

### Module Split Strategy

#### Module 1: `lifecycle.py` (~200 LOC)
**Responsibility**: Endpoint lifecycle operations

**Public API (`__all__`)**:
- `EndpointLifecycleManager`

**Methods**:
- `provision_endpoint(worker, activity_config) -> str`
- `provision_batch(workers) -> dict[str, str]`
- `delete_endpoint(worker_id) -> bool`
- `delete_all_endpoints() -> int`
- `get_endpoint_status(worker_id) -> dict | None`
- `get_all_endpoints() -> dict[str, dict]`
- `get_endpoint_counts() -> dict[str, int]`

**State**:
- `_provisioned_endpoints: dict[str, dict[str, Any]]`
- `run_id: str`

**Dependencies**:
- `providers.py` for actual provisioning
- `worker.EndpointType` for type constants

#### Module 2: `providers.py` (~180 LOC)
**Responsibility**: Provider-specific provisioning logic

**Public API (`__all__`)**:
- `EndpointProviderManager`

**Methods**:
- `provision_cloud_pc(worker) -> str`
- `provision_windows_vm(worker) -> dict[str, Any]`
- `provision_container(worker, config) -> str`
- `delete_cloud_pc(endpoint_id) -> bool`
- `delete_windows_vm(endpoint_id) -> bool`
- `delete_container(endpoint_id) -> bool`

**State**:
- `cloud_pc_manager: Windows365CloudPCManager | None`
- `windows_vm_manager: WindowsVMManager | None`
- `container_manager: M365CLIContainerManager | None`
- `run_id: str`

**Dependencies**:
- `cli_container.M365CLIContainerManager`
- `cloud_pc.Windows365CloudPCManager`
- `windows_vm.WindowsVMManager`

#### Module 3: `fallback.py` (~170 LOC)
**Responsibility**: Cascade fallback coordination

**Public API (`__all__`)**:
- `EndpointFallbackCoordinator`
- `AllEndpointsFailedError`
- `ProvisioningError`

**Methods**:
- `provision_with_fallback(worker) -> dict[str, Any]`

**Private methods**:
- `_try_cloud_pc(worker) -> dict | None`
- `_try_windows_vm(worker) -> dict | None`
- `_try_container(worker) -> dict | None`

**Logic**:
- Cascade: Cloud PC → Windows VM → Container
- Tracks failures with reasons
- Updates worker.endpoint_type and worker.endpoint_id
- Raises AllEndpointsFailedError if all fail

**Dependencies**:
- `providers.EndpointProviderManager`
- `worker.EndpointType, WorkerIdentity`

### Integration Layer: `manager.py` (NEW - ~50 LOC)

**Purpose**: Backward compatibility facade

**Public API (`__all__`)**:
- `EndpointManager` (facade class)
- `AllEndpointsFailedError` (re-export)
- `ProvisioningError` (re-export)

**Composition**:
```python
class EndpointManager:
    def __init__(self, cloud_pc_manager=None, windows_vm_manager=None,
                 container_manager=None, graph_client=None, config=None, run_id=""):
        self._lifecycle = EndpointLifecycleManager(run_id)
        self._providers = EndpointProviderManager(
            cloud_pc_manager, windows_vm_manager, container_manager, run_id
        )
        self._fallback = EndpointFallbackCoordinator(self._providers)

    # Delegate all methods to appropriate component
    def provision_endpoint(self, worker, activity_config):
        return self._lifecycle.provision_endpoint(
            worker, activity_config, self._providers
        )

    def provision_endpoint_with_fallback(self, worker):
        return self._fallback.provision_with_fallback(worker)

    # ... etc
```

## MANDATORY Requirements (CANNOT be optimized away)

1. ✅ **MUST split into exactly 3 modules** + 1 facade
   - `lifecycle.py` (~200 LOC)
   - `providers.py` (~180 LOC)
   - `fallback.py` (~170 LOC)
   - `manager.py` (NEW facade ~50 LOC)

2. ✅ **MUST keep all modules <300 LOC**

3. ✅ **MUST follow Bricks & Studs pattern**
   - Each module = self-contained "brick"
   - `__all__` defines public "studs" (interfaces)
   - Modules can be regenerated independently

4. ✅ **MUST maintain all endpoint contracts**
   - All public methods preserve signatures
   - All return types unchanged
   - All exceptions preserved

5. ✅ **MUST add `__all__` exports to all modules**

6. ✅ **MUST maintain 100% backward compatibility**
   - Existing imports work: `from ...endpoints.manager import EndpointManager`
   - All test cases pass without modification
   - Public API unchanged

## Design Principles

### Bricks & Studs Pattern
- **Brick** = Self-contained module with ONE responsibility
- **Stud** = Public contract (functions, API, data model) others connect to
- **Regeneratable** = Can be rebuilt from spec without breaking connections
- **Isolated** = All code, tests, fixtures inside the module's folder (eventually)

### Zero Circular Dependencies
- `lifecycle.py` depends on `providers.py`
- `fallback.py` depends on `providers.py`
- `manager.py` depends on all three
- NO reverse dependencies

### Clear Boundaries
```
lifecycle.py:  WHO has what endpoints (tracking, status, counts)
providers.py:  HOW to provision each type (Cloud PC, VM, Container)
fallback.py:   WHEN to try alternatives (cascade logic)
manager.py:    FACADE for backward compatibility
```

## Success Criteria

- [ ] All 3 modules created with clear boundaries
- [ ] Each module <300 LOC
- [ ] All modules have `__all__` exports
- [ ] Backward compatibility facade in manager.py
- [ ] All existing tests pass (test_endpoint_manager.py)
- [ ] No new complexity introduced
- [ ] Philosophy compliance verified
- [ ] No circular dependencies

## Migration Path

1. Create new modules (lifecycle, providers, fallback)
2. Implement each with `__all__` exports
3. Create new facade manager.py that composes them
4. Run tests to verify backward compatibility
5. NO changes to test files required

## Notes for Architect Agent

- Focus on clean module boundaries
- Preserve all existing behavior
- Think about which methods belong in which module based on responsibility
- Consider state management (where does `_provisioned_endpoints` live?)
- Keep fallback logic self-contained
- Provider manager should be stateless for each operation

## References

- Original file: `src/azure_haymaker/knowledge_worker/endpoints/manager.py`
- Tests: `tests/unit/test_endpoint_manager.py`
- Pattern guide: `.claude/context/PATTERNS.md` (Bricks & Studs)
- Philosophy: `.claude/context/PHILOSOPHY.md`
