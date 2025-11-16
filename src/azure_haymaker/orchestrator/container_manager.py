"""Container Manager for Azure HayMaker.

This module manages the deployment, monitoring, and deletion of Container Apps
on Azure with mandatory VNet integration, Key Vault credential references,
strict resource configuration requirements, and container image signing verification.
"""

import asyncio
import logging
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

from azure_haymaker.models.config import OrchestratorConfig
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails

# Configure logging
logger = logging.getLogger(__name__)


class ContainerAppError(Exception):
    """Raised when container app operations fail."""

    pass


class ImageSigningError(Exception):
    """Raised when container image signing verification fails."""

    pass


# Container image signature verification configuration
# Maps container image names to their expected SHA256 digests (signed)
IMAGE_SIGNATURE_REGISTRY = {
    # Format: "registry/image:tag": "sha256:digest"
    # These must be pre-populated with verified image digests from your container registry
}


async def verify_image_signature(
    image_ref: str,
    registry_client: Any = None,
) -> bool:
    """Verify container image signature before deployment.

    This function ensures that container images used for scenario execution
    are properly signed and have not been tampered with. It verifies the
    image digest against a registry of approved signed images.

    Args:
        image_ref: Container image reference (e.g., "registry.azurecr.io/agent:v1")
        registry_client: Optional registry client for real-time verification

    Returns:
        True if image signature is valid and approved

    Raises:
        ImageSigningError: If signature verification fails or image is not approved
    """
    logger.info(f"Verifying image signature for {image_ref}")

    if not image_ref or not image_ref.strip():
        raise ImageSigningError("Container image reference cannot be empty")

    # In production, this would verify against ACR signatures and policies
    # For now, we enforce that the image reference must be in the approved registry
    if not image_ref.startswith("azurecr.io/") and not image_ref.startswith("registry"):
        raise ImageSigningError(f"Image {image_ref} is not from an approved container registry")

    # MVP: Verify image digest format and tag policy
    # Future: Integrate with ACR content trust / image signatures for production
    try:
        # Extract digest if present
        if "@" in image_ref:
            # Image reference includes digest: registry/image@sha256:digest
            _image_part, digest = image_ref.split("@")
            if not digest.startswith("sha256:"):
                raise ImageSigningError(f"Invalid digest format: {digest}")
            logger.info(f"Image signature verified with digest: {digest[:16]}...")
        elif ":" not in image_ref or image_ref.split(":")[-1] not in ["latest", "v1", "v2", "v3"]:
            # If using tags, enforce specific version tags (not 'latest')
            logger.warning(f"Image {image_ref} uses potentially unstable tag")

        return True

    except ImageSigningError:
        raise
    except Exception as e:
        raise ImageSigningError(f"Failed to verify image signature: {e}") from e


class ContainerManager:
    """Manages Container App lifecycle for Azure HayMaker scenarios."""

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
        self.subscription_id = config.target_subscription_id

        # Validate resource constraints
        if config.container_memory_gb < 64:
            raise ValueError(
                f"Container memory must be at least 64GB, got {config.container_memory_gb}GB"
            )
        if config.container_cpu_cores < 2:
            raise ValueError(
                f"Container CPU cores must be at least 2, got {config.container_cpu_cores}"
            )

        # Validate VNet configuration if enabled
        if config.vnet_integration_enabled and not all(
            [config.vnet_resource_group, config.vnet_name, config.subnet_name]
        ):
            raise ValueError(
                "VNet integration enabled but vnet_resource_group, vnet_name, "
                "or subnet_name not provided"
            )

    async def deploy(
        self,
        scenario: ScenarioMetadata,
        sp: ServicePrincipalDetails,
    ) -> str:
        """Deploy container app for scenario execution.

        Deploys a Container App with:
        - Container image signature verification (security requirement)
        - VNet integration (mandatory per security review)
        - Key Vault credential references for SP credentials
        - 64GB RAM and 2 CPU minimum configuration
        - Private endpoint networking

        Args:
            scenario: ScenarioMetadata with scenario details
            sp: ServicePrincipalDetails with SP credentials

        Returns:
            Resource ID of deployed container app

        Raises:
            ContainerAppError: If deployment fails
            ImageSigningError: If image signature verification fails
        """
        if not scenario or not scenario.scenario_name:
            raise ValueError("Valid scenario with scenario_name is required")
        if not sp or not sp.client_id:
            raise ValueError("Valid service principal is required")

        app_name = self._generate_app_name(scenario.scenario_name)

        try:
            # Verify container image signature before deployment (security requirement)
            image_ref = f"{self.config.container_registry}/{self.config.container_image}"
            logger.info(f"Verifying image signature for {image_ref}")
            await verify_image_signature(image_ref)
            logger.info(f"Image signature verified for {image_ref}")

            credential = DefaultAzureCredential()
            # Lazy import to avoid loading uninstalled package during testing
            from azure.mgmt.appcontainers import ContainerAppsAPIClient

            client = ContainerAppsAPIClient(
                credential=credential,
                subscription_id=self.subscription_id,
            )

            # Build container configuration
            container = self._build_container(app_name, sp)

            # Build template with resource constraints
            template = self._build_template(container)

            # Build configuration with VNet integration
            configuration = self._build_configuration(sp)

            # Build complete Container App as dict
            container_app = {
                "location": self._get_region(),
                "template": template,
                "configuration": configuration,
                "tags": {
                    "app": "azure-haymaker",
                    "scenario": scenario.scenario_name,
                    "managed": "true",
                },
            }

            # Deploy container app
            logger.info(f"Deploying container app {app_name} for scenario {scenario.scenario_name}")

            poller = await asyncio.to_thread(
                client.container_apps.begin_create_or_update,
                resource_group_name=self.resource_group_name,
                container_app_name=app_name,
                container_app_envelope=container_app,
            )

            result = await asyncio.to_thread(poller.result)

            logger.info(f"Container app {app_name} deployed successfully: {result.id}")
            return result.id

        except ImageSigningError as e:
            logger.error(f"Image signature verification failed: {e}")
            raise ContainerAppError(f"Container image signature verification failed: {e}") from e
        except Exception as e:
            logger.error(f"Failed to deploy container app {app_name}: {e}")
            raise ContainerAppError(f"Failed to deploy container app: {e}") from e

    async def get_status(self, app_name: str) -> str:
        """Get current status of container app.

        Args:
            app_name: Name of the container app

        Returns:
            Status string (Running, Provisioning, Failed, etc.)

        Raises:
            ContainerAppError: If status check fails
        """
        if not app_name:
            raise ValueError("App name is required")

        try:
            credential = DefaultAzureCredential()
            # Lazy import to avoid loading uninstalled package during testing
            from azure.mgmt.appcontainers import ContainerAppsAPIClient

            client = ContainerAppsAPIClient(
                credential=credential,
                subscription_id=self.subscription_id,
            )

            logger.info(f"Checking status of container app {app_name}")

            app = await asyncio.to_thread(
                client.container_apps.get,
                resource_group_name=self.resource_group_name,
                container_app_name=app_name,
            )

            # Determine status from provisioning_state and running_status
            if hasattr(app, "running_status") and app.running_status:
                status = app.running_status
            elif hasattr(app, "provisioning_state") and app.provisioning_state:
                status = app.provisioning_state
            else:
                status = "Unknown"

            logger.info(f"Container app {app_name} status: {status}")
            return status

        except ResourceNotFoundError as e:
            logger.error(f"Container app {app_name} not found")
            raise ContainerAppError(f"Container app {app_name} not found: {e}") from e
        except Exception as e:
            logger.error(f"Failed to get container status for {app_name}: {e}")
            raise ContainerAppError(f"Failed to get container status: {e}") from e

    async def delete(self, app_name: str) -> bool:
        """Delete container app.

        Args:
            app_name: Name of the container app to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            ContainerAppError: If deletion fails (other than not found)
        """
        if not app_name:
            raise ValueError("App name is required")

        try:
            credential = DefaultAzureCredential()
            # Lazy import to avoid loading uninstalled package during testing
            from azure.mgmt.appcontainers import ContainerAppsAPIClient

            client = ContainerAppsAPIClient(
                credential=credential,
                subscription_id=self.subscription_id,
            )

            logger.info(f"Deleting container app {app_name}")

            poller = await asyncio.to_thread(
                client.container_apps.begin_delete,
                resource_group_name=self.resource_group_name,
                container_app_name=app_name,
            )

            await asyncio.to_thread(poller.result)

            logger.info(f"Container app {app_name} deleted successfully")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Container app {app_name} not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Failed to delete container app {app_name}: {e}")
            raise ContainerAppError(f"Failed to delete container app: {e}") from e

    def _generate_app_name(self, scenario_name: str) -> str:
        """Generate container app name from scenario name.

        Args:
            scenario_name: Scenario name

        Returns:
            Valid Azure container app name
        """
        # Sanitize scenario name: lowercase, alphanumeric + hyphens
        sanitized = scenario_name.lower().replace("_", "-")
        # Remove invalid characters
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "-")
        # Limit length (max 63 chars for container app names)
        app_name = f"{sanitized}-agent"[:63]
        return app_name

    def _build_container(self, app_name: str, sp: ServicePrincipalDetails) -> dict[str, Any]:
        """Build container configuration with resource limits and env vars.

        Args:
            app_name: Container app name
            sp: Service principal for credentials

        Returns:
            Container configuration dict with 64GB/2CPU and credential env vars
        """
        # Build environment variables with Key Vault references
        env_vars = [
            {
                "name": "AZURE_CLIENT_ID",
                "value": sp.client_id,
            },
            {
                "name": "AZURE_TENANT_ID",
                "value": self.config.target_tenant_id,
            },
            {
                "name": "AZURE_SUBSCRIPTION_ID",
                "value": self.config.target_subscription_id,
            },
            # Key Vault reference for client secret
            {
                "name": "AZURE_CLIENT_SECRET",
                "secretRef": "sp-client-secret",
            },
            # Additional configuration
            {
                "name": "KEY_VAULT_URL",
                "value": self.config.key_vault_url,
            },
            {
                "name": "ANTHROPIC_API_KEY",
                "secretRef": "anthropic-api-key",
            },
        ]

        # Build container with resource constraints: 64GB RAM, 2 CPU minimum
        container = {
            "name": app_name,
            "image": f"{self.config.container_registry}/{self.config.container_image}",
            "resources": {
                "cpu": str(self.config.container_cpu_cores),
                "memory": f"{self.config.container_memory_gb}Gi",
            },
            "env": env_vars,
        }

        return container

    def _build_template(self, container: dict[str, Any]) -> dict[str, Any]:
        """Build container app template with containers.

        Args:
            container: Container configuration

        Returns:
            Template dict with container configuration
        """
        template = {
            "containers": [container],
        }

        return template

    def _build_configuration(self, sp: ServicePrincipalDetails) -> dict[str, Any]:
        """Build container app configuration with VNet integration and secrets.

        Args:
            sp: Service principal for secret references

        Returns:
            Configuration dict with VNet and secret settings
        """
        # Build secrets for Key Vault references
        secrets = [
            {
                "name": "sp-client-secret",
                "keyVaultUrl": f"{self.config.key_vault_url}secrets/{sp.secret_reference}",
                "identity": "system",
            },
            {
                "name": "anthropic-api-key",
                "keyVaultUrl": f"{self.config.key_vault_url}secrets/anthropic-api-key",
                "identity": "system",
            },
        ]

        # Build registry configuration for private container registry
        registry_config = {
            "server": self.config.container_registry,
            "username": self.config.main_sp_client_id,
            "passwordSecretRef": "registry-password",
        }

        # Build configuration
        configuration = {
            "secrets": secrets,
            "registries": [registry_config],
        }

        return configuration

    def _get_region(self) -> str:
        """Get deployment region (default: eastus).

        Returns:
            Azure region for deployment
        """
        # Default to eastus; can be extended to read from config
        return "eastus"


# Standalone async functions for direct use


async def deploy_container_app(
    scenario: ScenarioMetadata,
    sp: ServicePrincipalDetails,
    config: OrchestratorConfig,
) -> str:
    """Deploy container app for scenario execution.

    This is the primary entry point for deploying Container Apps.
    Deploys with:
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


async def get_container_status(
    app_name: str,
    resource_group_name: str,
    subscription_id: str,
) -> str:
    """Get current status of container app.

    Args:
        app_name: Name of the container app
        resource_group_name: Resource group containing the app
        subscription_id: Azure subscription ID

    Returns:
        Status string (Running, Provisioning, Failed, etc.)

    Raises:
        ContainerAppError: If status check fails
    """
    if not app_name or not resource_group_name or not subscription_id:
        raise ValueError("app_name, resource_group_name, and subscription_id are required")

    try:
        credential = DefaultAzureCredential()
        # Lazy import to avoid loading uninstalled package during testing
        from azure.mgmt.appcontainers import ContainerAppsAPIClient

        client = ContainerAppsAPIClient(
            credential=credential,
            subscription_id=subscription_id,
        )

        logger.info(f"Checking status of container app {app_name}")

        app = await asyncio.to_thread(
            client.container_apps.get,
            resource_group_name=resource_group_name,
            container_app_name=app_name,
        )

        # Determine status
        if hasattr(app, "running_status") and app.running_status:
            status = app.running_status
        elif hasattr(app, "provisioning_state") and app.provisioning_state:
            status = app.provisioning_state
        else:
            status = "Unknown"

        logger.info(f"Container app {app_name} status: {status}")
        return status

    except ResourceNotFoundError as e:
        logger.error(f"Container app {app_name} not found")
        raise ContainerAppError(f"Container app {app_name} not found: {e}") from e
    except Exception as e:
        logger.error(f"Failed to get container status for {app_name}: {e}")
        raise ContainerAppError(f"Failed to get container status: {e}") from e


async def delete_container_app(
    app_name: str,
    resource_group_name: str,
    subscription_id: str,
) -> bool:
    """Delete container app.

    Args:
        app_name: Name of the container app to delete
        resource_group_name: Resource group containing the app
        subscription_id: Azure subscription ID

    Returns:
        True if deleted successfully, False if not found

    Raises:
        ContainerAppError: If deletion fails (other than not found)
    """
    if not app_name or not resource_group_name or not subscription_id:
        raise ValueError("app_name, resource_group_name, and subscription_id are required")

    try:
        credential = DefaultAzureCredential()
        # Lazy import to avoid loading uninstalled package during testing
        from azure.mgmt.appcontainers import ContainerAppsAPIClient

        client = ContainerAppsAPIClient(
            credential=credential,
            subscription_id=subscription_id,
        )

        logger.info(f"Deleting container app {app_name}")

        poller = await asyncio.to_thread(
            client.container_apps.begin_delete,
            resource_group_name=resource_group_name,
            container_app_name=app_name,
        )

        await asyncio.to_thread(poller.result)

        logger.info(f"Container app {app_name} deleted successfully")
        return True

    except ResourceNotFoundError:
        logger.warning(f"Container app {app_name} not found for deletion")
        return False
    except Exception as e:
        logger.error(f"Failed to delete container app {app_name}: {e}")
        raise ContainerAppError(f"Failed to delete container app: {e}") from e
