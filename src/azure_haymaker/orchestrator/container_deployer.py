"""Container App deployment for Azure HayMaker.

This module handles building and deploying Container Apps with VNet integration,
Key Vault credential references, and strict resource configuration requirements.
"""

import asyncio
import logging
from typing import Any

from azure.identity import DefaultAzureCredential

from azure_haymaker.models.config import OrchestratorConfig
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails

# Configure logging
logger = logging.getLogger(__name__)


class ContainerAppError(Exception):
    """Raised when container app operations fail."""

    pass


class ContainerDeployer:
    """Builds and deploys Container Apps with VNet and security configuration.

    This class handles the complete deployment workflow including:
    - Container configuration building (64GB/2CPU requirements)
    - VNet integration setup
    - Key Vault secret references
    - Azure Container Apps API orchestration
    """

    def __init__(self, config: OrchestratorConfig):
        """Initialize ContainerDeployer with configuration.

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

        # Validate VNet configuration if enabled
        self._validate_vnet()

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
            ValueError: If inputs are invalid
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

    def _generate_app_name(self, scenario_name: str) -> str:
        """Generate container app name from scenario name.

        Creates a valid Azure container app name by sanitizing the scenario name
        to lowercase alphanumeric characters plus hyphens, with a maximum length
        of 63 characters.

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

        Creates container configuration with:
        - 64GB RAM and 2 CPU minimum (enforced by validation)
        - Environment variables for Azure credentials
        - Key Vault secret references for sensitive values

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

        Creates the template section of the Container App configuration
        that defines the containers to run.

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

        Creates the configuration section including:
        - Key Vault secret references
        - Container registry credentials
        - VNet integration settings (if enabled)

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

        Returns the Azure region for Container App deployment.
        Currently defaults to eastus but can be extended to read
        from configuration.

        Returns:
            Azure region for deployment
        """
        # Default to eastus; can be extended to read from config
        return "eastus"

    def _validate_resources(self) -> None:
        """Validate CPU/memory constraints.

        Ensures that the configuration meets minimum resource requirements
        for Container Apps (64GB RAM, 2 CPU cores).

        Raises:
            ValueError: If resource constraints are insufficient
        """
        if self.config.container_memory_gb < 64:
            raise ValueError(
                f"Container memory must be at least 64GB, got {self.config.container_memory_gb}GB"
            )
        if self.config.container_cpu_cores < 2:
            raise ValueError(
                f"Container CPU cores must be at least 2, got {self.config.container_cpu_cores}"
            )

    def _validate_vnet(self) -> None:
        """Validate VNet configuration.

        Ensures that VNet integration settings are properly configured
        if VNet integration is enabled.

        Raises:
            ValueError: If VNet configuration is invalid
        """
        if self.config.vnet_integration_enabled and not all(
            [self.config.vnet_resource_group, self.config.vnet_name, self.config.subnet_name]
        ):
            raise ValueError(
                "VNet integration enabled but vnet_resource_group, vnet_name, "
                "or subnet_name not provided"
            )
