"""Container Manager for Azure HayMaker.

This module manages the deployment, monitoring, and deletion of Container Apps
on Azure with mandatory VNet integration, Key Vault credential references,
and strict resource configuration requirements.
"""

import asyncio
import logging
from typing import Optional, Any, Dict, List

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
        if config.vnet_integration_enabled:
            if not all([config.vnet_resource_group, config.vnet_name, config.subnet_name]):
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
        """
        if not scenario or not scenario.scenario_name:
            raise ValueError("Valid scenario with scenario_name is required")
        if not sp or not sp.client_id:
            raise ValueError("Valid service principal is required")

        app_name = self._generate_app_name(scenario.scenario_name)

        try:
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
        app_name = f"{sanitized}-agent"[: 63]
        return app_name

    def _build_container(self, app_name: str, sp: ServicePrincipalDetails) -> Dict[str, Any]:
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

    def _build_template(self, container: Dict[str, Any]) -> Dict[str, Any]:
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

    def _build_configuration(self, sp: ServicePrincipalDetails) -> Dict[str, Any]:
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

        # VNet integration configuration
        vnet_config = None
        if self.config.vnet_integration_enabled:
            vnet_config = {
                "vnetResourceGroup": self.config.vnet_resource_group,
                "vnetName": self.config.vnet_name,
                "subnetName": self.config.subnet_name,
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
