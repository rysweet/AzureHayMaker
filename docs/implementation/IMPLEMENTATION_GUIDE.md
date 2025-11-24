# Container Manager Implementation Guide

**Quick reference for builder agent implementing the class extraction.**

## File Paths

All files relative to: `/Users/ryan/src/tmphay/worktrees/feat-issue-20-split-container`

### Source Files to Create
```
src/azure_haymaker/orchestrator/image_verifier.py
src/azure_haymaker/orchestrator/container_deployer.py
src/azure_haymaker/orchestrator/container_monitor.py
src/azure_haymaker/orchestrator/container_lifecycle.py
```

### Source Files to Modify
```
src/azure_haymaker/orchestrator/container_manager.py  (593 → 80 lines)
src/azure_haymaker/orchestrator/__init__.py            (add exports)
```

### Test File (NO MODIFICATIONS)
```
tests/unit/test_container_manager.py  (566 assertions - must pass unchanged)
```

---

## Phase 1: Extract ImageVerifier

### Create: image_verifier.py

**Lines to extract from container_manager.py**: 29-93
- `ImageSigningError` exception (lines 29-32)
- `IMAGE_SIGNATURE_REGISTRY` constant (lines 35-40)
- `verify_image_signature()` function (lines 43-93)

**New class structure**:
```python
"""Container image signature verification."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ImageSigningError(Exception):
    """Raised when container image signing verification fails."""
    pass


IMAGE_SIGNATURE_REGISTRY = {
    # Format: "registry/image:tag": "sha256:digest"
}


class ImageVerifier:
    """Validates container image signatures and registry policies."""

    async def verify_signature(
        self,
        image_ref: str,
        registry_client: Any = None,
    ) -> bool:
        """Verify container image signature.

        Args:
            image_ref: Container image reference
            registry_client: Optional registry client

        Returns:
            True if signature is valid

        Raises:
            ImageSigningError: If verification fails
        """
        # Move logic from verify_image_signature() here


# Standalone function for backward compatibility
async def verify_image_signature(
    image_ref: str,
    registry_client: Any = None,
) -> bool:
    """Standalone wrapper for verify_signature."""
    verifier = ImageVerifier()
    return await verifier.verify_signature(image_ref, registry_client)
```

**Update container_manager.py**:
```python
# At top
from azure_haymaker.orchestrator.image_verifier import (
    ImageSigningError,
    ImageVerifier,
    verify_image_signature,
)

# Remove lines 29-93
```

**Test validation**:
```bash
pytest tests/unit/test_container_manager.py::TestImageSignatureVerification -v
```

---

## Phase 2: Extract ContainerMonitor

### Create: container_monitor.py

**Lines to extract from container_manager.py**: 224-273 (get_status method) + 486-541 (standalone)

**New class structure**:
```python
"""Container App status monitoring."""

import asyncio
import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class ContainerAppError(Exception):
    """Raised when container app operations fail."""
    pass


class ContainerMonitor:
    """Monitors Container App status and health."""

    def __init__(
        self,
        resource_group_name: str,
        subscription_id: str,
    ):
        """Initialize with Azure resource identifiers."""
        if not resource_group_name or not subscription_id:
            raise ValueError("resource_group_name and subscription_id are required")

        self.resource_group_name = resource_group_name
        self.subscription_id = subscription_id

    async def get_status(self, app_name: str) -> str:
        """Get current status of container app."""
        # Move logic from ContainerManager.get_status() here


# Standalone function for backward compatibility
async def get_container_status(
    app_name: str,
    resource_group_name: str,
    subscription_id: str,
) -> str:
    """Get status of container app."""
    if not app_name or not resource_group_name or not subscription_id:
        raise ValueError("app_name, resource_group_name, and subscription_id are required")

    monitor = ContainerMonitor(
        resource_group_name=resource_group_name,
        subscription_id=subscription_id,
    )
    return await monitor.get_status(app_name)
```

**Update container_manager.py**:
```python
# At top
from azure_haymaker.orchestrator.container_monitor import ContainerMonitor

# In ContainerManager.__init__
self._monitor = ContainerMonitor(
    resource_group_name=config.resource_group_name,
    subscription_id=config.target_subscription_id,
)

# Replace get_status method with delegation
async def get_status(self, app_name: str) -> str:
    """Get status (delegates to ContainerMonitor)."""
    return await self._monitor.get_status(app_name)

# Update standalone function
async def get_container_status(...) -> str:
    monitor = ContainerMonitor(...)
    return await monitor.get_status(app_name)
```

**Test validation**:
```bash
pytest tests/unit/test_container_manager.py::TestGetContainerStatusFunction -v
pytest tests/unit/test_container_manager.py::TestContainerManagerValidation::test_get_status_invalid_app_name -v
```

---

## Phase 3: Extract ContainerLifecycle

### Create: container_lifecycle.py

**Lines to extract from container_manager.py**: 275-318 (delete method) + 544-593 (standalone)

**New class structure**:
```python
"""Container App lifecycle management."""

import asyncio
import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class ContainerAppError(Exception):
    """Raised when container app operations fail."""
    pass


class ContainerLifecycle:
    """Manages Container App lifecycle and cleanup operations."""

    def __init__(
        self,
        resource_group_name: str,
        subscription_id: str,
    ):
        """Initialize with Azure resource identifiers."""
        if not resource_group_name or not subscription_id:
            raise ValueError("resource_group_name and subscription_id are required")

        self.resource_group_name = resource_group_name
        self.subscription_id = subscription_id

    async def delete(self, app_name: str) -> bool:
        """Delete container app."""
        # Move logic from ContainerManager.delete() here


# Standalone function for backward compatibility
async def delete_container_app(
    app_name: str,
    resource_group_name: str,
    subscription_id: str,
) -> bool:
    """Delete container app."""
    if not app_name or not resource_group_name or not subscription_id:
        raise ValueError("app_name, resource_group_name, and subscription_id are required")

    lifecycle = ContainerLifecycle(
        resource_group_name=resource_group_name,
        subscription_id=subscription_id,
    )
    return await lifecycle.delete(app_name)
```

**Update container_manager.py**:
```python
# At top
from azure_haymaker.orchestrator.container_lifecycle import ContainerLifecycle

# In ContainerManager.__init__
self._lifecycle = ContainerLifecycle(
    resource_group_name=config.resource_group_name,
    subscription_id=config.target_subscription_id,
)

# Replace delete method with delegation
async def delete(self, app_name: str) -> bool:
    """Delete container app (delegates to ContainerLifecycle)."""
    return await self._lifecycle.delete(app_name)

# Update standalone function
async def delete_container_app(...) -> bool:
    lifecycle = ContainerLifecycle(...)
    return await lifecycle.delete(app_name)
```

**Test validation**:
```bash
pytest tests/unit/test_container_manager.py::TestDeleteContainerAppFunction -v
pytest tests/unit/test_container_manager.py::TestContainerManagerValidation::test_delete_invalid_app_name -v
```

---

## Phase 4: Extract ContainerDeployer

### Create: container_deployer.py

**Lines to extract from container_manager.py**: 98-132, 133-223, 320-451

**Structure**:
- Constructor validation logic (lines 98-132)
- Deploy method (lines 133-223, minus image verification)
- All private helper methods (lines 320-451)

**New class structure**:
```python
"""Container App deployment and configuration."""

import asyncio
import logging
from typing import Any

from azure.identity import DefaultAzureCredential

from azure_haymaker.models.config import OrchestratorConfig
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails

logger = logging.getLogger(__name__)


class ContainerAppError(Exception):
    """Raised when container app operations fail."""
    pass


class ContainerDeployer:
    """Builds and deploys Container Apps with VNet and security configuration."""

    def __init__(self, config: OrchestratorConfig):
        """Initialize with orchestrator configuration.

        Args:
            config: OrchestratorConfig with deployment settings

        Raises:
            ValueError: If configuration is invalid
        """
        if not config:
            raise ValueError("Configuration is required")

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

        NOTE: Image verification should be done by caller (ContainerManager facade).

        Args:
            scenario: Scenario metadata
            sp: Service principal details

        Returns:
            Resource ID of deployed container app

        Raises:
            ContainerAppError: If deployment fails
        """
        # Move deployment logic here (WITHOUT image verification)

    def _generate_app_name(self, scenario_name: str) -> str:
        """Generate valid Azure container app name."""

    def _build_container(self, app_name: str, sp: ServicePrincipalDetails) -> dict[str, Any]:
        """Build container configuration with resource limits."""

    def _build_template(self, container: dict[str, Any]) -> dict[str, Any]:
        """Build container app template."""

    def _build_configuration(self, sp: ServicePrincipalDetails) -> dict[str, Any]:
        """Build configuration with VNet and secrets."""

    def _get_region(self) -> str:
        """Get deployment region."""

    def _validate_resources(self) -> None:
        """Validate CPU/memory constraints."""
        if self.config.container_memory_gb < 64:
            raise ValueError(
                f"Container memory must be at least 64GB, got {self.config.container_memory_gb}GB"
            )
        if self.config.container_cpu_cores < 2:
            raise ValueError(
                f"Container CPU cores must be at least 2, got {self.config.container_cpu_cores}"
            )

    def _validate_vnet(self) -> None:
        """Validate VNet configuration."""
        if self.config.vnet_integration_enabled and not all(
            [self.config.vnet_resource_group, self.config.vnet_name, self.config.subnet_name]
        ):
            raise ValueError(
                "VNet integration enabled but vnet_resource_group, vnet_name, "
                "or subnet_name not provided"
            )
```

**Update container_manager.py**:
```python
# At top
from azure_haymaker.orchestrator.container_deployer import ContainerDeployer

# In ContainerManager.__init__
self._deployer = ContainerDeployer(config=config)

# Replace deploy method with delegation (KEEP image verification in facade)
async def deploy(
    self,
    scenario: ScenarioMetadata,
    sp: ServicePrincipalDetails,
) -> str:
    """Deploy container app (delegates to ContainerDeployer)."""
    if not scenario or not scenario.scenario_name:
        raise ValueError("Valid scenario with scenario_name is required")
    if not sp or not sp.client_id:
        raise ValueError("Valid service principal is required")

    # Verify image signature BEFORE delegating
    image_ref = f"{self.config.container_registry}/{self.config.container_image}"
    logger.info(f"Verifying image signature for {image_ref}")
    await self._verifier.verify_signature(image_ref)
    logger.info(f"Image signature verified for {image_ref}")

    # Delegate to deployer
    return await self._deployer.deploy(scenario=scenario, sp=sp)

# Delegate private methods for test compatibility
def _generate_app_name(self, scenario_name: str) -> str:
    return self._deployer._generate_app_name(scenario_name)

def _build_container(self, app_name: str, sp: ServicePrincipalDetails) -> dict:
    return self._deployer._build_container(app_name, sp)

def _build_configuration(self, sp: ServicePrincipalDetails) -> dict:
    return self._deployer._build_configuration(sp)
```

**Test validation**:
```bash
pytest tests/unit/test_container_manager.py::TestContainerManagerAppNameGeneration -v
pytest tests/unit/test_container_manager.py::TestContainerManagerBuildContainer -v
pytest tests/unit/test_container_manager.py::TestContainerManagerBuildConfiguration -v
pytest tests/unit/test_container_manager.py::TestDeployContainerAppFunction -v
```

---

## Phase 5: Finalize ContainerManager Facade

### Refactor: container_manager.py

**Final structure** (~80 lines):
```python
"""Container Manager for Azure HayMaker - Facade for container operations."""

import logging

from azure_haymaker.models.config import OrchestratorConfig
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails
from azure_haymaker.orchestrator.container_deployer import (
    ContainerAppError,
    ContainerDeployer,
)
from azure_haymaker.orchestrator.container_lifecycle import ContainerLifecycle
from azure_haymaker.orchestrator.container_monitor import ContainerMonitor
from azure_haymaker.orchestrator.image_verifier import (
    ImageSigningError,
    ImageVerifier,
    verify_image_signature,
)

logger = logging.getLogger(__name__)


class ContainerManager:
    """Facade for container management operations.

    Maintains backward compatibility while delegating to specialized classes.
    """

    def __init__(self, config: OrchestratorConfig):
        """Initialize ContainerManager with configuration."""
        if not config:
            raise ValueError("Configuration is required")

        self.config = config
        self.resource_group_name = config.resource_group_name

        # Initialize delegates
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

    async def deploy(self, scenario, sp) -> str:
        """Deploy container app."""
        # Validation + image verification + delegation (see Phase 4)

    async def get_status(self, app_name: str) -> str:
        """Get status."""
        return await self._monitor.get_status(app_name)

    async def delete(self, app_name: str) -> bool:
        """Delete container app."""
        return await self._lifecycle.delete(app_name)

    # Private methods for test compatibility
    def _generate_app_name(self, scenario_name: str) -> str:
        return self._deployer._generate_app_name(scenario_name)

    def _build_container(self, app_name: str, sp) -> dict:
        return self._deployer._build_container(app_name, sp)

    def _build_configuration(self, sp) -> dict:
        return self._deployer._build_configuration(sp)


# Standalone functions (see previous phases for implementations)
async def deploy_container_app(scenario, sp, config) -> str:
    manager = ContainerManager(config=config)
    return await manager.deploy(scenario=scenario, sp=sp)


async def get_container_status(app_name, resource_group_name, subscription_id) -> str:
    monitor = ContainerMonitor(
        resource_group_name=resource_group_name,
        subscription_id=subscription_id,
    )
    return await monitor.get_status(app_name)


async def delete_container_app(app_name, resource_group_name, subscription_id) -> bool:
    lifecycle = ContainerLifecycle(
        resource_group_name=resource_group_name,
        subscription_id=subscription_id,
    )
    return await lifecycle.delete(app_name)
```

**Test validation**:
```bash
pytest tests/unit/test_container_manager.py -v
```

**Success criteria**: All 566 assertions pass

---

## Phase 6: Update Public API Exports

### Modify: __init__.py

**Current exports** (lines 3-9):
```python
from .container_manager import (
    ContainerAppError,
    ContainerManager,
    delete_container_app,
    deploy_container_app,
    get_container_status,
)
```

**Updated exports**:
```python
from .container_manager import (
    ContainerAppError,
    ContainerManager,
    ImageSigningError,
    delete_container_app,
    deploy_container_app,
    get_container_status,
    verify_image_signature,
)

# Optionally expose specialized classes for future consumers
from .container_deployer import ContainerDeployer
from .container_lifecycle import ContainerLifecycle
from .container_monitor import ContainerMonitor
from .image_verifier import ImageVerifier
```

**Update __all__** (line 43+):
```python
__all__ = [
    # ... existing exports ...
    "ContainerManager",
    "ContainerAppError",
    "ImageSigningError",
    "deploy_container_app",
    "get_container_status",
    "delete_container_app",
    "verify_image_signature",
    "ContainerDeployer",
    "ContainerMonitor",
    "ContainerLifecycle",
    "ImageVerifier",
]
```

**Test validation**:
```bash
# Test imports work
python -c "from azure_haymaker.orchestrator import ContainerManager"
python -c "from azure_haymaker.orchestrator import ContainerDeployer"
python -c "from azure_haymaker.orchestrator import verify_image_signature"

# Run full test suite
pytest tests/unit/test_container_manager.py -v
```

---

## Common Pitfalls to Avoid

### 1. Don't Move ContainerAppError Exception Duplicates
- `ContainerAppError` is used by ALL classes
- Create it in each new module (monitor, lifecycle, deployer)
- Import it from individual modules in container_manager.py
- Alternative: Create shared exceptions.py (adds complexity)

### 2. Keep Image Verification in Facade
- `ContainerManager.deploy()` must call `verify_signature()` BEFORE delegating
- Don't move image verification into `ContainerDeployer.deploy()`
- Reason: Maintains security validation at facade level

### 3. Preserve Private Method Access
- Tests call `manager._generate_app_name()`
- Facade must expose these methods: `return self._deployer._generate_app_name(name)`
- Don't remove or rename these methods

### 4. Maintain Validation Order
- Scenario/SP validation happens in facade's `deploy()` method
- Resource validation happens in `ContainerDeployer.__init__()`
- Don't duplicate validations

### 5. Handle Imports Carefully
- Each new module needs its own imports (asyncio, logging, Azure SDK)
- Don't create circular imports (facade → specialized classes only)
- Test imports after each phase

---

## Test Validation Checklist

After each phase, run specific test classes:

```bash
# Phase 1 - ImageVerifier
pytest tests/unit/test_container_manager.py::TestImageSignatureVerification -v

# Phase 2 - ContainerMonitor
pytest tests/unit/test_container_manager.py::TestGetContainerStatusFunction -v

# Phase 3 - ContainerLifecycle
pytest tests/unit/test_container_manager.py::TestDeleteContainerAppFunction -v

# Phase 4 - ContainerDeployer
pytest tests/unit/test_container_manager.py::TestContainerManagerAppNameGeneration -v
pytest tests/unit/test_container_manager.py::TestContainerManagerBuildContainer -v
pytest tests/unit/test_container_manager.py::TestContainerManagerBuildConfiguration -v

# Phase 5 - Full facade
pytest tests/unit/test_container_manager.py -v

# Phase 6 - Final validation
pytest tests/unit/test_container_manager.py -v
pytest tests/ -k container  # Run any related tests
```

**Success criteria for completion**: All 566 test assertions pass with zero test file modifications.

---

## Quick Reference: Line Extraction Map

| Lines | Content | Target File |
|-------|---------|-------------|
| 23-26 | ContainerAppError | All new modules |
| 29-32 | ImageSigningError | image_verifier.py |
| 35-40 | IMAGE_SIGNATURE_REGISTRY | image_verifier.py |
| 43-93 | verify_image_signature() | image_verifier.py |
| 98-132 | ContainerManager.__init__ validation | container_deployer.py (_validate_*) |
| 133-223 | ContainerManager.deploy() | container_deployer.py + facade |
| 224-273 | ContainerManager.get_status() | container_monitor.py |
| 275-318 | ContainerManager.delete() | container_lifecycle.py |
| 320-451 | Private helper methods | container_deployer.py |
| 456-484 | deploy_container_app() | container_manager.py (wraps facade) |
| 486-541 | get_container_status() | container_monitor.py |
| 544-593 | delete_container_app() | container_lifecycle.py |

---

## Implementation Time Estimate

- Phase 1 (ImageVerifier): 30 minutes
- Phase 2 (ContainerMonitor): 30 minutes
- Phase 3 (ContainerLifecycle): 30 minutes
- Phase 4 (ContainerDeployer): 60 minutes
- Phase 5 (Facade refactor): 45 minutes
- Phase 6 (Public API): 15 minutes
- **Total**: ~3.5 hours

---

**Ready for implementation. Follow phases sequentially and validate tests after each phase.**
