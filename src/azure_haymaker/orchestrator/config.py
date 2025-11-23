"""Configuration loading for Azure HayMaker orchestrator.

This module loads configuration from environment variables and Azure Key Vault,
adhering to the Zero-BS Philosophy: no defaults for secrets, fail fast on missing config.

Configuration Priority Order:
1. Environment variables (explicit override) - highest priority
2. Azure Key Vault (production secrets)
3. .env file (local development only) - lowest priority
"""

import logging
import os

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from pydantic import SecretStr, ValidationError

from azure_haymaker.models.config import (
    CosmosDBConfig,
    LogAnalyticsConfig,
    OrchestratorConfig,
    SimulationSize,
    StorageConfig,
    TableStorageConfig,
)
from azure_haymaker.orchestrator.config_env_loader import load_dotenv_with_warnings

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


def _get_required_env(var_name: str, dotenv_vars: dict[str, str] | None = None) -> str:
    """Get required environment variable with .env fallback.

    Priority order:
    1. Environment variable (explicit override)
    2. .env file value (if provided via dotenv_vars)
    3. Raise ConfigurationError if not found

    Args:
        var_name: Name of the environment variable
        dotenv_vars: Optional dict of variables loaded from .env file

    Returns:
        str: The environment variable value

    Raises:
        ConfigurationError: If the variable is not found in either source
    """
    # 1. Check environment variable first (highest priority)
    value = os.getenv(var_name)
    if value:
        return value

    # 2. Check .env file fallback
    if dotenv_vars and var_name in dotenv_vars:
        logger.info("Using %s from .env file (not set in environment)", var_name)
        return dotenv_vars[var_name]

    # 3. Not found - raise error
    raise ConfigurationError(
        f"Required environment variable {var_name} is not set. "
        f"Please set this variable in your environment or .env file."
    )


def _get_optional_env(var_name: str, default: str) -> str:
    """Get optional environment variable with default value."""
    return os.getenv(var_name, default)


async def load_config_from_env_and_keyvault() -> OrchestratorConfig:
    """Load configuration from environment variables and Azure Key Vault.

    This function loads non-secret configuration from environment variables
    and retrieves secrets from Azure Key Vault using Managed Identity.

    Configuration Priority Order:
    1. Environment variables (explicit override) - highest priority
    2. Azure Key Vault (production secrets)
    3. .env file (local development only) - lowest priority

    Required Environment Variables:
        AZURE_TENANT_ID: Target Azure tenant ID
        AZURE_SUBSCRIPTION_ID: Target subscription ID
        AZURE_CLIENT_ID: Main service principal client ID
        KEY_VAULT_URL: Key Vault URL
        SERVICE_BUS_NAMESPACE: Service Bus namespace
        CONTAINER_REGISTRY: Container registry URL
        CONTAINER_IMAGE: Agent container image
        SIMULATION_SIZE: Simulation size (small/medium/large)
        STORAGE_ACCOUNT_NAME: Blob storage account name
        TABLE_STORAGE_ACCOUNT_NAME: Table storage account name
        COSMOSDB_ENDPOINT: Cosmos DB endpoint URL
        COSMOSDB_DATABASE: Cosmos DB database name
        LOG_ANALYTICS_WORKSPACE_ID: Log Analytics workspace ID

    Optional Environment Variables:
        RESOURCE_GROUP_NAME: Resource group name (default: azure-haymaker-rg)
        SERVICE_BUS_TOPIC: Service Bus topic name (default: agent-logs)
        VNET_INTEGRATION_ENABLED: Enable VNet integration (default: false)
        VNET_RESOURCE_GROUP: VNet resource group (required if VNet enabled)
        VNET_NAME: VNet name (required if VNet enabled)
        SUBNET_NAME: Subnet name (required if VNet enabled)

    Key Vault Secrets (retrieved automatically):
        main-sp-client-secret: Main service principal secret
        anthropic-api-key: Anthropic API key
        log-analytics-workspace-key: Log Analytics workspace key

    Returns:
        OrchestratorConfig: Validated configuration object

    Raises:
        ConfigurationError: If required configuration is missing or invalid
    """
    try:
        # Load .env file first (lowest priority - will be overridden by env vars)
        dotenv_vars = load_dotenv_with_warnings()

        # Load required environment variables (with .env fallback)
        target_tenant_id = _get_required_env("AZURE_TENANT_ID", dotenv_vars)
        target_subscription_id = _get_required_env("AZURE_SUBSCRIPTION_ID", dotenv_vars)
        main_sp_client_id = _get_required_env("AZURE_CLIENT_ID", dotenv_vars)
        key_vault_url = _get_required_env("KEY_VAULT_URL", dotenv_vars)
        service_bus_namespace = _get_required_env("SERVICE_BUS_NAMESPACE", dotenv_vars)
        container_registry = _get_required_env("CONTAINER_REGISTRY", dotenv_vars)
        container_image = _get_required_env("CONTAINER_IMAGE", dotenv_vars)
        simulation_size_str = _get_required_env("SIMULATION_SIZE", dotenv_vars)

        # Storage configuration
        storage_account_name = _get_required_env("STORAGE_ACCOUNT_NAME", dotenv_vars)
        table_storage_account_name = _get_required_env("TABLE_STORAGE_ACCOUNT_NAME", dotenv_vars)

        # Cosmos DB configuration (optional for dev where Cosmos DB not deployed)
        cosmosdb_endpoint = _get_optional_env("COSMOSDB_ENDPOINT", "")
        cosmosdb_database = _get_optional_env("COSMOSDB_DATABASE", "haymaker")

        # Log Analytics configuration
        log_analytics_workspace_id = _get_required_env("LOG_ANALYTICS_WORKSPACE_ID", dotenv_vars)

        # Optional environment variables
        resource_group_name = _get_optional_env("RESOURCE_GROUP_NAME", "azure-haymaker-rg")
        service_bus_topic = _get_optional_env("SERVICE_BUS_TOPIC", "agent-logs")

        # VNet configuration
        vnet_integration_enabled = os.getenv("VNET_INTEGRATION_ENABLED", "false").lower() == "true"
        vnet_resource_group = os.getenv("VNET_RESOURCE_GROUP")
        vnet_name = os.getenv("VNET_NAME")
        subnet_name = os.getenv("SUBNET_NAME")

        # Validate simulation size
        try:
            simulation_size = SimulationSize(simulation_size_str.lower())
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid simulation size: {simulation_size_str}. "
                f"Must be one of: small, medium, large"
            ) from e

        # Retrieve secrets from Key Vault
        try:
            credential = DefaultAzureCredential()
            kv_client = SecretClient(vault_url=key_vault_url, credential=credential)

            main_sp_secret_obj = kv_client.get_secret("main-sp-client-secret")
            anthropic_api_key_obj = kv_client.get_secret("anthropic-api-key")
            log_analytics_key_obj = kv_client.get_secret("log-analytics-workspace-key")

            if not main_sp_secret_obj.value:
                raise ConfigurationError("main-sp-client-secret value is None")
            if not anthropic_api_key_obj.value:
                raise ConfigurationError("anthropic-api-key value is None")
            if not log_analytics_key_obj.value:
                raise ConfigurationError("log-analytics-workspace-key value is None")

            main_sp_secret = main_sp_secret_obj.value
            anthropic_api_key = anthropic_api_key_obj.value
            log_analytics_key = log_analytics_key_obj.value

        except Exception as e:
            raise ConfigurationError(
                f"Failed to retrieve secrets from Key Vault ({key_vault_url}): {e}"
            ) from e

        # Build configuration object
        try:
            config = OrchestratorConfig(
                target_tenant_id=target_tenant_id,
                target_subscription_id=target_subscription_id,
                main_sp_client_id=main_sp_client_id,
                main_sp_client_secret=SecretStr(main_sp_secret),
                anthropic_api_key=SecretStr(anthropic_api_key),
                service_bus_namespace=service_bus_namespace,
                service_bus_topic=service_bus_topic,
                container_registry=container_registry,
                container_image=container_image,
                key_vault_url=key_vault_url,
                simulation_size=simulation_size,
                resource_group_name=resource_group_name,
                storage=StorageConfig(
                    account_name=storage_account_name,
                    container_logs="execution-logs",
                    container_state="execution-state",
                    container_reports="execution-reports",
                    container_scenarios="scenarios",
                ),
                table_storage=TableStorageConfig(
                    account_name=table_storage_account_name,
                    table_execution_runs="ExecutionRuns",
                    table_scenario_status="ScenarioStatus",
                    table_resource_inventory="ResourceInventory",
                ),
                cosmosdb=CosmosDBConfig(
                    endpoint=cosmosdb_endpoint,
                    database_name=cosmosdb_database,
                    container_metrics="metrics",
                ),
                log_analytics=LogAnalyticsConfig(
                    workspace_id=log_analytics_workspace_id,
                    workspace_key=SecretStr(log_analytics_key),
                ),
                vnet_integration_enabled=vnet_integration_enabled,
                vnet_resource_group=vnet_resource_group,
                vnet_name=vnet_name,
                subnet_name=subnet_name,
            )

            return config

        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}") from e

    except ConfigurationError:
        # Re-raise configuration errors as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise ConfigurationError(f"Unexpected error loading configuration: {e}") from e


async def load_config() -> OrchestratorConfig:
    """Convenience function to load configuration.

    This is the main entry point for loading configuration.
    It delegates to load_config_from_env_and_keyvault.

    Returns:
        OrchestratorConfig: Validated configuration object

    Raises:
        ConfigurationError: If configuration loading fails
    """
    return await load_config_from_env_and_keyvault()
