# Container Manager Class Extraction Architecture

## Executive Summary

This document defines the architecture for extracting 4 focused classes from the 593-line ContainerManager monolith while maintaining 100% backward compatibility and ensuring all 566 test assertions pass unchanged.

## Current State Analysis

### Existing Module Structure
- **File**: `src/azure_haymaker/orchestrator/container_manager.py`
- **Lines**: 593
- **Classes**: 1 (ContainerManager) + 2 exceptions
- **Functions**: 4 (1 verification + 3 standalone wrappers)
- **Test Assertions**: 566 (must remain unchanged)

### Public API Surface
```python
# Classes
ContainerManager
ContainerAppError
ImageSigningError

# Functions
verify_image_signature()
deploy_container_app()
get_container_status()
delete_container_app()
```

### Consumers
- `orchestrator/orchestrator.py` - imports ContainerManager, deploy_container_app
- `orchestrator/execute_processor.py` - imports ContainerManager, deploy_container_app
- `orchestrator/__init__.py` - re-exports public API
- `tests/unit/test_container_manager.py` - tests all functionality

## Target Architecture

### Design Principle: Facade Pattern with Dependency Injection

The refactoring follows the **Facade Pattern** where:
1. **ContainerManager becomes a thin facade** delegating to specialized classes
2. **Shared configuration** is injected once into the facade, then passed to delegates
3. **Original public API** remains 100% unchanged
4. **Standalone functions** continue wrapping the facade

### Class Responsibility Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       ContainerManager                          │
│                       (Facade - 80 lines)                       │
│                                                                  │
│  + __init__(config: OrchestratorConfig)                        │
│  + deploy(scenario, sp) -> str                                  │
│  + get_status(app_name) -> str                                  │
│  + delete(app_name) -> bool                                     │
│                                                                  │
│  Private: _deployer, _monitor, _lifecycle, _verifier           │
└────────┬────────────┬──────────────┬──────────────┬────────────┘
         │            │              │              │
         │            │              │              │
         v            v              v              v
┌────────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐
│ Container  │  │Container │  │ Container  │  │  Image   │
│ Deployer   │  │ Monitor  │  │ Lifecycle  │  │Verifier  │
│ (200 LOC)  │  │(150 LOC) │  │ (150 LOC)  │  │(100 LOC) │
└────────────┘  └──────────┘  └────────────┘  └──────────┘

   Deployment     Status         Deletion      Signature
   Container      Checks         Resource      Validation
   Creation                      Cleanup
```

## Class Specifications

### 1. ImageVerifier (100 lines)

**File**: `src/azure_haymaker/orchestrator/image_verifier.py`

**Purpose**: Validate container image signatures before deployment

**Public API**:
```python
class ImageVerifier:
    """Validates container image signatures and registry policies."""

    async def verify_signature(
        self,
        image_ref: str,
        registry_client: Any = None,
    ) -> bool:
        """Verify image signature.

        Args:
            image_ref: Container image reference
            registry_client: Optional registry client

        Returns:
            True if signature is valid

        Raises:
            ImageSigningError: If verification fails
        """

# Standalone function for backward compatibility
async def verify_image_signature(
    image_ref: str,
    registry_client: Any = None,
) -> bool:
    """Standalone wrapper for verify_signature."""
    verifier = ImageVerifier()
    return await verifier.verify_signature(image_ref, registry_client)
```

**Responsibilities**:
- Image signature verification
- Registry approval validation
- Digest format checking
- Tag policy enforcement

**Configuration Dependencies**: None (stateless)

**Test Coverage**: 8 test methods (TestImageSignatureVerification class)

---

### 2. ContainerDeployer (200 lines)

**File**: `src/azure_haymaker/orchestrator/container_deployer.py`

**Purpose**: Build and deploy Container Apps with VNet integration

**Public API**:
```python
class ContainerDeployer:
    """Builds and deploys Container Apps with VNet and security configuration."""

    def __init__(self, config: OrchestratorConfig):
        """Initialize with orchestrator configuration.

        Args:
            config: OrchestratorConfig with deployment settings

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config
        self.resource_group_name = config.resource_group_name
        self.subscription_id = config.target_subscription_id

        # Validate resource constraints
        self._validate_resources()

        # Validate VNet configuration
        self._validate_vnet()

    async def deploy(
        self,
        scenario: ScenarioMetadata,
        sp: ServicePrincipalDetails,
    ) -> str:
        """Deploy container app for scenario.

        Args:
            scenario: Scenario metadata
            sp: Service principal details

        Returns:
            Resource ID of deployed container app

        Raises:
            ContainerAppError: If deployment fails
        """

    def _generate_app_name(self, scenario_name: str) -> str:
        """Generate valid Azure container app name."""

    def _build_container(
        self,
        app_name: str,
        sp: ServicePrincipalDetails
    ) -> dict[str, Any]:
        """Build container configuration with resource limits."""

    def _build_template(self, container: dict[str, Any]) -> dict[str, Any]:
        """Build container app template."""

    def _build_configuration(
        self,
        sp: ServicePrincipalDetails
    ) -> dict[str, Any]:
        """Build configuration with VNet and secrets."""

    def _get_region(self) -> str:
        """Get deployment region."""

    def _validate_resources(self) -> None:
        """Validate CPU/memory constraints."""

    def _validate_vnet(self) -> None:
        """Validate VNet configuration."""
```

**Responsibilities**:
- Container App deployment orchestration
- Container configuration building (64GB/2CPU)
- VNet integration configuration
- Key Vault secret references
- App name generation and sanitization
- Azure SDK client management
- Resource constraint validation

**Configuration Dependencies**:
- OrchestratorConfig (full access)

**Test Coverage**:
- TestContainerManagerInit (4 methods - validation tests)
- TestContainerManagerAppNameGeneration (3 methods)
- TestContainerManagerBuildContainer (3 methods)
- TestContainerManagerBuildConfiguration (3 methods)
- TestContainerManagerEdgeCases (partial - 3 methods)
- TestContainerDeploymentWithImageVerification (1 method)

---

### 3. ContainerMonitor (150 lines)

**File**: `src/azure_haymaker/orchestrator/container_monitor.py`

**Purpose**: Query and report Container App status

**Public API**:
```python
class ContainerMonitor:
    """Monitors Container App status and health."""

    def __init__(
        self,
        resource_group_name: str,
        subscription_id: str,
    ):
        """Initialize with Azure resource identifiers.

        Args:
            resource_group_name: Resource group name
            subscription_id: Azure subscription ID

        Raises:
            ValueError: If parameters are invalid
        """
        if not resource_group_name or not subscription_id:
            raise ValueError("resource_group_name and subscription_id are required")

        self.resource_group_name = resource_group_name
        self.subscription_id = subscription_id

    async def get_status(self, app_name: str) -> str:
        """Get current status of container app.

        Args:
            app_name: Name of the container app

        Returns:
            Status string (Running, Provisioning, Failed, etc.)

        Raises:
            ContainerAppError: If status check fails
        """
```

**Responsibilities**:
- Container App status queries
- Running status determination
- Provisioning state tracking
- Error handling for not found scenarios

**Configuration Dependencies**:
- resource_group_name (string)
- subscription_id (string)

**Test Coverage**:
- TestGetContainerStatusFunction (1 method)
- TestContainerManagerValidation (partial - 1 method)

---

### 4. ContainerLifecycle (150 lines)

**File**: `src/azure_haymaker/orchestrator/container_lifecycle.py`

**Purpose**: Manage Container App deletion and cleanup

**Public API**:
```python
class ContainerLifecycle:
    """Manages Container App lifecycle and cleanup operations."""

    def __init__(
        self,
        resource_group_name: str,
        subscription_id: str,
    ):
        """Initialize with Azure resource identifiers.

        Args:
            resource_group_name: Resource group name
            subscription_id: Azure subscription ID

        Raises:
            ValueError: If parameters are invalid
        """
        if not resource_group_name or not subscription_id:
            raise ValueError("resource_group_name and subscription_id are required")

        self.resource_group_name = resource_group_name
        self.subscription_id = subscription_id

    async def delete(self, app_name: str) -> bool:
        """Delete container app.

        Args:
            app_name: Name of the container app

        Returns:
            True if deleted, False if not found

        Raises:
            ContainerAppError: If deletion fails
        """
```

**Responsibilities**:
- Container App deletion
- Cleanup operations
- Resource not found handling

**Configuration Dependencies**:
- resource_group_name (string)
- subscription_id (string)

**Test Coverage**:
- TestDeleteContainerAppFunction (1 method)
- TestContainerManagerValidation (partial - 1 method)

---

### 5. ContainerManager (Facade - 80 lines)

**File**: `src/azure_haymaker/orchestrator/container_manager.py` (refactored)

**Purpose**: Maintain backward compatibility via delegation

**Implementation**:
```python
class ContainerManager:
    """Facade for container management operations.

    Maintains backward compatibility while delegating to specialized classes.
    """

    def __init__(self, config: OrchestratorConfig):
        """Initialize ContainerManager with configuration.

        Args:
            config: OrchestratorConfig with deployment settings

        Raises:
            ValueError: If configuration is invalid
        """
        if not config:
            raise ValueError("Configuration is required")

        self.config = config
        self.resource_group_name = config.resource_group_name

        # Initialize delegates with shared configuration
        self._deployer = ContainerDeployer(config=config)
        self._monitor = ContainerMonitor(
            resource_group_name=config.resource_group_name,
            subscription_id=config.target_subscription_id,
        )
        self._lifecycle = ContainerLifecycle(
            resource_group_name=config.resource_group_name,
            subscription_id=config.target_subscription_id,
        )
        self._verifier = ImageVerifier()

    async def deploy(
        self,
        scenario: ScenarioMetadata,
        sp: ServicePrincipalDetails,
    ) -> str:
        """Deploy container app (delegates to ContainerDeployer)."""
        # Verify image signature first
        image_ref = f"{self.config.container_registry}/{self.config.container_image}"
        await self._verifier.verify_signature(image_ref)

        # Delegate to deployer
        return await self._deployer.deploy(scenario=scenario, sp=sp)

    async def get_status(self, app_name: str) -> str:
        """Get status (delegates to ContainerMonitor)."""
        return await self._monitor.get_status(app_name)

    async def delete(self, app_name: str) -> bool:
        """Delete container app (delegates to ContainerLifecycle)."""
        return await self._lifecycle.delete(app_name)

    def _generate_app_name(self, scenario_name: str) -> str:
        """Generate app name (delegates to ContainerDeployer)."""
        return self._deployer._generate_app_name(scenario_name)

    def _build_container(self, app_name: str, sp: ServicePrincipalDetails) -> dict:
        """Build container (delegates to ContainerDeployer)."""
        return self._deployer._build_container(app_name, sp)

    def _build_configuration(self, sp: ServicePrincipalDetails) -> dict:
        """Build configuration (delegates to ContainerDeployer)."""
        return self._deployer._build_configuration(sp)
```

**Key Design Decision**: The facade delegates **private methods** to maintain test compatibility. This allows existing tests accessing `manager._generate_app_name()` to continue working.

---

## Configuration Sharing Strategy

### Dependency Injection Pattern

**Principle**: Each class receives **only what it needs**

```
OrchestratorConfig (full)
         │
         ├──> ContainerDeployer (full config - needs all settings)
         │
         ├──> ContainerMonitor (resource_group_name, subscription_id)
         │
         ├──> ContainerLifecycle (resource_group_name, subscription_id)
         │
         └──> ImageVerifier (no config - stateless)
```

### Rationale

1. **ContainerDeployer needs full config**: Must access container_registry, container_image, vnet settings, Key Vault URL, resource constraints
2. **Monitor/Lifecycle need minimal**: Only need resource identifiers for Azure SDK calls
3. **ImageVerifier is stateless**: Pure validation logic, no configuration
4. **Facade holds config**: Maintains `self.config` for backward compatibility

This follows the **Interface Segregation Principle**: clients should not depend on interfaces they don't use.

---

## Facade Pattern for Backward Compatibility

### Strategy: Zero Breaking Changes

**Approach**: The refactored ContainerManager acts as a **transparent proxy**

```python
# Old code (still works)
manager = ContainerManager(config=config)
result = await manager.deploy(scenario, sp)
status = await manager.get_status("app-name")
deleted = await manager.delete("app-name")

# Private methods (used by tests) still work
app_name = manager._generate_app_name("scenario")
container = manager._build_container("app", sp)
```

**Implementation Details**:

1. **Public methods** delegate to specialized classes
2. **Private methods** delegate to ContainerDeployer (maintains test compatibility)
3. **Constructor** validates configuration (same behavior)
4. **Attributes** preserved (`self.config`, `self.resource_group_name`)

### Key Insight

The existing tests access **private methods** (e.g., `manager._generate_app_name()`). Rather than refactoring tests, we:

1. Keep private method names in the facade
2. Delegate to the specialized class's method
3. Tests continue passing unchanged

This is **pragmatic over purist**: maintaining test stability is more valuable than perfect encapsulation.

---

## Standalone Function Wrappers

### Current Design
```python
async def deploy_container_app(
    scenario: ScenarioMetadata,
    sp: ServicePrincipalDetails,
    config: OrchestratorConfig,
) -> str:
    manager = ContainerManager(config=config)
    return await manager.deploy(scenario=scenario, sp=sp)
```

### Refactored Design

**No changes required** - standalone functions continue wrapping the facade:

```python
# src/azure_haymaker/orchestrator/container_manager.py

async def deploy_container_app(
    scenario: ScenarioMetadata,
    sp: ServicePrincipalDetails,
    config: OrchestratorConfig,
) -> str:
    """Deploy container app (convenience wrapper)."""
    manager = ContainerManager(config=config)
    return await manager.deploy(scenario=scenario, sp=sp)

async def get_container_status(
    app_name: str,
    resource_group_name: str,
    subscription_id: str,
) -> str:
    """Get status (convenience wrapper)."""
    monitor = ContainerMonitor(
        resource_group_name=resource_group_name,
        subscription_id=subscription_id,
    )
    return await monitor.get_status(app_name)

async def delete_container_app(
    app_name: str,
    resource_group_name: str,
    subscription_id: str,
) -> bool:
    """Delete app (convenience wrapper)."""
    lifecycle = ContainerLifecycle(
        resource_group_name=resource_group_name,
        subscription_id=subscription_id,
    )
    return await lifecycle.delete(app_name)
```

**Decision**: `get_container_status()` and `delete_container_app()` bypass the facade and call specialized classes directly because they:
1. Don't need the full OrchestratorConfig
2. Accept minimal parameters
3. Are standalone entry points (not tied to a manager instance)

---

## Test Preservation Strategy

### Requirement: Zero Test Changes

All 566 test assertions must pass without modification.

### Test Organization
```
tests/unit/test_container_manager.py
├── TestContainerManagerInit (4 methods) ────────> Facade validation
├── TestContainerManagerAppNameGeneration (3) ───> Facade delegates to Deployer
├── TestContainerManagerBuildContainer (3) ──────> Facade delegates to Deployer
├── TestContainerManagerBuildConfiguration (3) ──> Facade delegates to Deployer
├── TestContainerManagerValidation (3) ──────────> Facade validation
├── TestDeployContainerAppFunction (2) ──────────> Standalone wrapper
├── TestGetContainerStatusFunction (1) ──────────> Standalone wrapper
├── TestDeleteContainerAppFunction (1) ──────────> Standalone wrapper
├── TestContainerAppError (1) ───────────────────> Exception class
├── TestContainerManagerEdgeCases (4) ───────────> Facade + Deployer
├── TestImageSignatureVerification (8) ──────────> ImageVerifier
└── TestContainerDeploymentWithImageVerification (1) > Integration
```

### Strategy by Test Class

**1. Tests using ContainerManager directly**:
- No changes needed
- Facade delegates to specialized classes
- All assertions continue passing

**2. Tests accessing private methods**:
- No changes needed
- Facade exposes delegate methods
- Example: `manager._generate_app_name()` → `self._deployer._generate_app_name()`

**3. Tests using standalone functions**:
- No changes needed
- Functions continue wrapping facade or specialized classes

**4. Exception tests**:
- No changes needed
- Exceptions remain in container_manager.py

### Validation Approach

Run tests after each extraction:

```bash
# After extracting ImageVerifier
pytest tests/unit/test_container_manager.py::TestImageSignatureVerification -v

# After extracting ContainerDeployer
pytest tests/unit/test_container_manager.py::TestContainerManagerBuildContainer -v

# After extracting ContainerMonitor
pytest tests/unit/test_container_manager.py::TestGetContainerStatusFunction -v

# After extracting ContainerLifecycle
pytest tests/unit/test_container_manager.py::TestDeleteContainerAppFunction -v

# Final validation - all tests
pytest tests/unit/test_container_manager.py -v
```

**Success Criteria**: All 566 assertions pass without any test file modifications.

---

## Implementation Order

### Phase 1: Extract ImageVerifier (Stateless)
1. Create `src/azure_haymaker/orchestrator/image_verifier.py`
2. Move `ImageSigningError` class
3. Move `IMAGE_SIGNATURE_REGISTRY` constant
4. Create `ImageVerifier` class with `verify_signature()` method
5. Keep `verify_image_signature()` standalone function
6. Update imports in `container_manager.py`
7. Run tests: `TestImageSignatureVerification`

**Why first?**: No dependencies, easiest to extract, standalone function already exists

---

### Phase 2: Extract ContainerMonitor (Minimal Config)
1. Create `src/azure_haymaker/orchestrator/container_monitor.py`
2. Create `ContainerMonitor` class with constructor validation
3. Move `get_status()` logic from ContainerManager
4. Update `get_container_status()` standalone function to use ContainerMonitor
5. Update ContainerManager facade to delegate to monitor
6. Run tests: `TestGetContainerStatusFunction`, `TestContainerManagerValidation`

**Why second?**: Simple delegation, minimal config needs

---

### Phase 3: Extract ContainerLifecycle (Minimal Config)
1. Create `src/azure_haymaker/orchestrator/container_lifecycle.py`
2. Create `ContainerLifecycle` class with constructor validation
3. Move `delete()` logic from ContainerManager
4. Update `delete_container_app()` standalone function to use ContainerLifecycle
5. Update ContainerManager facade to delegate to lifecycle
6. Run tests: `TestDeleteContainerAppFunction`, `TestContainerManagerValidation`

**Why third?**: Similar to Monitor, prepares for final extraction

---

### Phase 4: Extract ContainerDeployer (Full Config)
1. Create `src/azure_haymaker/orchestrator/container_deployer.py`
2. Create `ContainerDeployer` class with full config validation
3. Move all deployment logic:
   - `deploy()`
   - `_generate_app_name()`
   - `_build_container()`
   - `_build_template()`
   - `_build_configuration()`
   - `_get_region()`
   - `_validate_resources()` (extracted from __init__)
   - `_validate_vnet()` (extracted from __init__)
4. Update ContainerManager facade to delegate to deployer
5. Run tests: All deployment and build tests

**Why last?**: Most complex, depends on ImageVerifier, affects most tests

---

### Phase 5: Refactor ContainerManager to Facade
1. Update ContainerManager to create delegate instances
2. Update all methods to delegate to specialized classes
3. Keep private methods for test compatibility
4. Verify all 566 test assertions pass
5. Update module docstring

**Why final?**: Orchestrates all extracted classes

---

### Phase 6: Update Public API Exports
1. Update `src/azure_haymaker/orchestrator/__init__.py`:
   ```python
   from .container_manager import (
       ContainerAppError,
       ContainerManager,
       ImageSigningError,  # Added
       delete_container_app,
       deploy_container_app,
       get_container_status,
       verify_image_signature,
   )

   # Optionally expose specialized classes
   from .container_deployer import ContainerDeployer
   from .container_lifecycle import ContainerLifecycle
   from .container_monitor import ContainerMonitor
   from .image_verifier import ImageVerifier
   ```

2. Run full test suite: `pytest tests/unit/test_container_manager.py -v`

**Backward Compatibility**: Existing imports continue working:
```python
from azure_haymaker.orchestrator import ContainerManager  # Still works
from azure_haymaker.orchestrator.container_manager import deploy_container_app  # Still works
```

---

## File Structure After Refactoring

```
src/azure_haymaker/orchestrator/
├── container_manager.py          (80 lines - facade + standalone functions)
├── container_deployer.py         (200 lines - new)
├── container_monitor.py          (150 lines - new)
├── container_lifecycle.py        (150 lines - new)
├── image_verifier.py             (100 lines - new)
├── __init__.py                   (updated exports)
└── ... (other modules)
```

**Total Lines**: 680 lines (up from 593 due to extracted constructors and validation)

**Line Count Increase Rationale**:
- Each extracted class needs its own constructor validation
- Facade needs delegate initialization
- Better separation of concerns justifies modest increase
- Still within reasonable bounds for maintainability

---

## Key Architectural Decisions

### 1. Why Facade Over Direct Refactoring?

**Decision**: Keep ContainerManager as a facade rather than removing it

**Rationale**:
- 100% backward compatibility guaranteed
- Existing tests pass unchanged
- Consumer code (orchestrator.py, execute_processor.py) requires no updates
- Gradual migration path: consumers can eventually use specialized classes

**Alternative Rejected**: Force all consumers to use specialized classes directly
- Would require updating 4 files
- Would require rewriting all tests
- Higher risk of introducing bugs

---

### 2. Why Inject Full Config to Deployer?

**Decision**: ContainerDeployer receives full OrchestratorConfig

**Rationale**:
- Needs 10+ config fields (registry, image, vnet settings, Key Vault URL, etc.)
- Cleaner API than passing 10+ individual parameters
- Matches original ContainerManager signature
- Future-proof: new config fields automatically available

**Alternative Rejected**: Pass individual parameters
- Constructor would have 10+ parameters
- Higher coupling to config structure changes
- More verbose and error-prone

---

### 3. Why Keep Private Methods in Facade?

**Decision**: Facade exposes `_generate_app_name()`, `_build_container()`, etc.

**Rationale**:
- Tests directly access these methods: `manager._generate_app_name("test")`
- Changing tests is risky and time-consuming
- Delegation is simple: `return self._deployer._generate_app_name(name)`
- Pragmatic over purist: test stability > perfect encapsulation

**Alternative Rejected**: Make tests use specialized classes directly
- Would require rewriting 10+ test methods
- Tests would lose integration coverage
- Higher risk of test bugs

---

### 4. Why ImageVerifier is Stateless?

**Decision**: ImageVerifier has no constructor, no instance state

**Rationale**:
- Signature verification is pure logic (no config needed)
- Registry validation is based on hardcoded approved registries
- Stateless design enables easy testing and reuse
- Matches existing `verify_image_signature()` standalone function

**Alternative Rejected**: Inject approved registries via constructor
- Over-engineering for current needs
- Can be added later if registry config becomes dynamic

---

### 5. Why Separate Monitor and Lifecycle?

**Decision**: Split status checking and deletion into two classes

**Rationale**:
- **Single Responsibility Principle**: Monitoring vs. lifecycle management are distinct concerns
- Different extension paths: monitoring might add health checks, metrics; lifecycle might add restart, scale operations
- Meets target of 4 extracted classes (Deployer, Monitor, Lifecycle, Verifier)
- Each ~150 lines is a manageable size

**Alternative Rejected**: Single "ContainerOperations" class
- Would be ~300 lines (still too large)
- Mixed responsibilities
- Doesn't meet extraction target

---

## Migration Path for Consumers

### Immediate: No Changes Required

All existing code continues working:

```python
# orchestrator.py - no changes needed
from azure_haymaker.orchestrator.container_manager import ContainerManager

manager = ContainerManager(config=config)
await manager.deploy(scenario, sp)
```

### Future: Optional Migration to Specialized Classes

Consumers can gradually adopt specialized classes for clearer intent:

```python
# Example: Use ContainerMonitor directly
from azure_haymaker.orchestrator.container_monitor import ContainerMonitor

monitor = ContainerMonitor(
    resource_group_name="rg",
    subscription_id="sub",
)
status = await monitor.get_status("app-name")
```

This provides **flexibility without breaking changes**.

---

## Risk Mitigation

### Risk: Test Failures

**Mitigation**:
1. Extract classes incrementally (one at a time)
2. Run tests after each extraction
3. Keep facade delegation transparent
4. Maintain private method access in facade

**Validation**: Run full test suite after each phase

---

### Risk: Import Errors

**Mitigation**:
1. Update `__init__.py` to re-export all public symbols
2. Keep backward-compatible import paths
3. Test imports in all consumer modules

**Validation**:
```bash
python -c "from azure_haymaker.orchestrator import ContainerManager"
python -c "from azure_haymaker.orchestrator.container_manager import deploy_container_app"
```

---

### Risk: Circular Dependencies

**Mitigation**:
1. Dependency flow: Facade → Specialized Classes (one direction only)
2. No cross-dependencies between specialized classes
3. ImageVerifier, Monitor, Lifecycle have zero dependencies on each other

**Validation**: Check with import analyzer or manual code review

---

### Risk: Configuration Drift

**Mitigation**:
1. OrchestratorConfig is immutable (frozen dataclass or equivalent)
2. All classes receive config at construction
3. No runtime config modifications

**Validation**: Review OrchestratorConfig definition

---

## Success Metrics

### Quantitative
- 566 test assertions pass unchanged ✓
- 4 classes extracted (Deployer, Monitor, Lifecycle, Verifier) ✓
- ~150 lines per extracted class ✓
- Facade ~80 lines ✓
- Zero changes to consumer code ✓

### Qualitative
- Each class has single, clear responsibility ✓
- Configuration injection is explicit and minimal ✓
- Public API maintains 100% backward compatibility ✓
- Code is easier to understand and extend ✓

---

## Implementation Checklist

### Pre-Implementation
- [ ] Review architecture document with team
- [ ] Confirm backward compatibility requirements
- [ ] Set up feature branch
- [ ] Run baseline test suite (confirm all 566 assertions pass)

### Phase 1: ImageVerifier
- [ ] Create `image_verifier.py`
- [ ] Move `ImageSigningError` class
- [ ] Create `ImageVerifier` class
- [ ] Update imports in `container_manager.py`
- [ ] Run `TestImageSignatureVerification` tests

### Phase 2: ContainerMonitor
- [ ] Create `container_monitor.py`
- [ ] Create `ContainerMonitor` class
- [ ] Move `get_status()` logic
- [ ] Update `get_container_status()` standalone function
- [ ] Update facade delegation
- [ ] Run monitor-related tests

### Phase 3: ContainerLifecycle
- [ ] Create `container_lifecycle.py`
- [ ] Create `ContainerLifecycle` class
- [ ] Move `delete()` logic
- [ ] Update `delete_container_app()` standalone function
- [ ] Update facade delegation
- [ ] Run lifecycle-related tests

### Phase 4: ContainerDeployer
- [ ] Create `container_deployer.py`
- [ ] Create `ContainerDeployer` class
- [ ] Move deployment logic (8 methods)
- [ ] Update facade delegation
- [ ] Run deployment-related tests

### Phase 5: Facade Refactoring
- [ ] Update `ContainerManager` to delegate all operations
- [ ] Maintain private methods for test compatibility
- [ ] Run full test suite

### Phase 6: Public API
- [ ] Update `__init__.py` exports
- [ ] Update module docstrings
- [ ] Run full test suite
- [ ] Verify imports in consumer modules

### Post-Implementation
- [ ] Run full test suite: `pytest tests/unit/test_container_manager.py -v`
- [ ] Verify all 566 assertions pass
- [ ] Code review
- [ ] Update PR description with architecture summary

---

## Conclusion

This architecture provides:

1. **Clear SRP boundaries**: Each class has one focused responsibility
2. **100% backward compatibility**: Facade pattern maintains existing API
3. **Zero test changes**: All 566 assertions pass unchanged
4. **Flexible configuration**: Dependency injection with minimal coupling
5. **Low-risk implementation**: Incremental extraction with validation at each step

The refactoring transforms a 593-line monolith into 5 focused modules totaling ~680 lines, with each component having a clear, testable responsibility. The facade pattern ensures existing code continues working while enabling future consumers to adopt specialized classes as needed.

**Ready for builder agent implementation.**
