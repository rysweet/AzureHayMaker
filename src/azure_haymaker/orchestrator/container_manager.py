"""Container Manager for Azure HayMaker.

This module provides a unified facade for container management operations,
delegating to specialized classes for deployment, monitoring, lifecycle,
and image verification while maintaining backward compatibility.
"""

import logging
from typing import Any

from azure_haymaker.models.config import OrchestratorConfig
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails

# Import specialized classes
from .container_deployer import ContainerDeployer
from .container_lifecycle import ContainerLifecycle
from .container_monitor import ContainerMonitor
from .image_verifier import ImageVerifier

# Import exceptions and functions for re-export
from .container_deployer import ContainerAppError
from .container_lifecycle import delete_container_app
from .container_monitor import get_container_status
from .image_verifier import ImageSigningError, verify_image_signature

# Configure logging
logger = logging.getLogger(__name__)


class ContainerManager:
    """Facade for container management operations.

    This class maintains backward compatibility while delegating to specialized
    classes for deployment (ContainerDeployer), monitoring (ContainerMonitor),
    lifecycle management (ContainerLifecycle), and image verification (ImageVerifier).

    The facade pattern ensures existing consumer code continues working unchanged
    while providing a clean, single-responsibility architecture internally.
    """

    def __init__(self, config: OrchestratorConfig):
        """Initialize ContainerManager with configuration.

        Creates delegate instances for each specialized operation and validates
        the configuration meets all requirements.

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
        # Deployer needs full config for deployment operations
        self._deployer = ContainerDeployer(config=config)

        # Monitor and lifecycle need minimal config (resource identifiers)
        self._monitor = ContainerMonitor(
            resource_group_name=config.resource_group_name,
            subscription_id=config.target_subscription_id,
        )
        self._lifecycle = ContainerLifecycle(
            resource_group_name=config.resource_group_name,
            subscription_id=config.target_subscription_id,
        )

        # Verifier is stateless (no configuration needed)
        self._verifier = ImageVerifier()

    async def deploy(
        self,
        scenario: ScenarioMetadata,
        sp: ServicePrincipalDetails,
    ) -> str:
        """Deploy container app for scenario execution.

        Verifies the container image signature before delegating to ContainerDeployer
        for the actual deployment.

        Args:
            scenario: ScenarioMetadata with scenario details
            sp: ServicePrincipalDetails with SP credentials

        Returns:
            Resource ID of deployed container app

        Raises:
            ContainerAppError: If deployment fails
            ImageSigningError: If image signature verification fails
        """
        # Verify image signature first (security requirement)
        image_ref = f"{self.config.container_registry}/{self.config.container_image}"
        logger.info(f"Verifying image signature for {image_ref}")
        try:
            # Use standalone function for better testability (can be mocked)
            await verify_image_signature(image_ref)
            logger.info(f"Image signature verified for {image_ref}")
        except ImageSigningError as e:
            logger.error(f"Image signature verification failed: {e}")
            raise ContainerAppError(f"Container image signature verification failed: {e}") from e

        # Delegate to deployer
        return await self._deployer.deploy(scenario=scenario, sp=sp)

    async def get_status(self, app_name: str) -> str:
        """Get current status of container app.

        Delegates to ContainerMonitor for status checking.

        Args:
            app_name: Name of the container app

        Returns:
            Status string (Running, Provisioning, Failed, etc.)

        Raises:
            ContainerAppError: If status check fails
        """
        return await self._monitor.get_status(app_name)

    async def delete(self, app_name: str) -> bool:
        """Delete container app.

        Delegates to ContainerLifecycle for deletion operations.

        Args:
            app_name: Name of the container app to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            ContainerAppError: If deletion fails (other than not found)
        """
        return await self._lifecycle.delete(app_name)

    # Private methods delegated to specialized classes for test compatibility

    def _generate_app_name(self, scenario_name: str) -> str:
        """Generate app name (delegates to ContainerDeployer).

        This method is exposed for backward compatibility with existing tests
        that access private methods.

        Args:
            scenario_name: Scenario name

        Returns:
            Valid Azure container app name
        """
        return self._deployer._generate_app_name(scenario_name)

    def _build_container(self, app_name: str, sp: ServicePrincipalDetails) -> dict[str, Any]:
        """Build container (delegates to ContainerDeployer).

        This method is exposed for backward compatibility with existing tests
        that access private methods.

        Args:
            app_name: Container app name
            sp: Service principal for credentials

        Returns:
            Container configuration dict
        """
        return self._deployer._build_container(app_name, sp)

    def _build_configuration(self, sp: ServicePrincipalDetails) -> dict[str, Any]:
        """Build configuration (delegates to ContainerDeployer).

        This method is exposed for backward compatibility with existing tests
        that access private methods.

        Args:
            sp: Service principal for secret references

        Returns:
            Configuration dict with VNet and secret settings
        """
        return self._deployer._build_configuration(sp)

    def _get_region(self) -> str:
        """Get deployment region (delegates to ContainerDeployer).

        This method is exposed for backward compatibility with existing tests
        that access private methods.

        Returns:
            Azure region for deployment
        """
        return self._deployer._get_region()


# Standalone async functions for direct use


async def deploy_container_app(
    scenario: ScenarioMetadata,
    sp: ServicePrincipalDetails,
    config: OrchestratorConfig,
) -> str:
    """Deploy container app for scenario execution.

    This is the primary entry point for deploying Container Apps.
    Deploys with:
    - Container image signature verification (security requirement)
    - VNet integration (mandatory per security review)
    - Key Vault credential references for SP credentials
    - 64GB RAM and 2 CPU minimum configuration
    - Secure private endpoint networking

    Args:
        scenario: ScenarioMetadata with scenario execution details
        sp: ServicePrincipalDetails with service principal credentials
        config: OrchestratorConfig with deployment configuration

    Returns:
        Resource ID of deployed container app

    Raises:
        ContainerAppError: If deployment fails
        ValueError: If inputs are invalid
    """
    manager = ContainerManager(config=config)
    return await manager.deploy(scenario=scenario, sp=sp)
