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
    TenantConfig,
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

        # Check environment variables FIRST (allows App Service direct config)
        main_sp_secret = os.getenv("MAIN_SP_CLIENT_SECRET")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        log_analytics_key = os.getenv("LOG_ANALYTICS_WORKSPACE_KEY")

        # Cross-tenant credentials (optional - for deploying to different tenant)
        target_tenant_sp_id = os.getenv("TARGET_TENANT_SP_CLIENT_ID")
        target_tenant_sp_secret = os.getenv("TARGET_TENANT_SP_CLIENT_SECRET")

        # Only try Key Vault if env vars not set
        if not main_sp_secret or not anthropic_api_key or not log_analytics_key:
            try:
                credential = DefaultAzureCredential()
                kv_client = SecretClient(vault_url=key_vault_url, credential=credential)

                if not main_sp_secret:
                    main_sp_secret = kv_client.get_secret("main-sp-client-secret").value
                if not anthropic_api_key:
                    anthropic_api_key = kv_client.get_secret("anthropic-api-key").value
                if not log_analytics_key:
                    log_analytics_key = kv_client.get_secret("log-analytics-workspace-key").value

                # Try loading cross-tenant secret if target tenant differs and ID provided
                if (not target_tenant_sp_secret and target_tenant_sp_id
                    and target_tenant_id != os.getenv("AZURE_TENANT_ID", "")):
                    secret_name = f"target-tenant-{target_tenant_id[:8]}-sp-secret"
                    try:
                        target_tenant_sp_secret = kv_client.get_secret(secret_name).value
                        logger.info(f"Loaded target tenant SP secret from Key Vault: {secret_name}")
                    except Exception:
                        logger.warning(
                            f"Target tenant SP secret not found in Key Vault: {secret_name}. "
                            f"Set TARGET_TENANT_SP_CLIENT_SECRET env var if cross-tenant deployment needed."
                        )

            except Exception as e:
                raise ConfigurationError(
                    f"Secrets not in env vars and Key Vault failed ({key_vault_url}): {e}. "
                    f"Set MAIN_SP_CLIENT_SECRET, ANTHROPIC_API_KEY, LOG_ANALYTICS_WORKSPACE_KEY as env vars."
                ) from e

        # Build configuration object
        try:
            config = OrchestratorConfig(
                target_tenant_id=target_tenant_id,
                target_subscription_id=target_subscription_id,
                main_sp_client_id=main_sp_client_id,
                main_sp_client_secret=SecretStr(main_sp_secret),
                target_tenant_sp_client_id=target_tenant_sp_id,
                target_tenant_sp_client_secret=SecretStr(target_tenant_sp_secret) if target_tenant_sp_secret else None,
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

            # Log cross-tenant mode detection
            if config.is_cross_tenant:
                orchestrator_tenant = os.getenv("AZURE_TENANT_ID", "unknown")
                logger.info(
                    f"Cross-tenant mode enabled: orchestrator={orchestrator_tenant[:8]}... "
                    f"-> target={target_tenant_id[:8]}..."
                )
            else:
                logger.info("Single-tenant mode (default)")

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


def load_tenant_configs_from_keyvault(
    kv_client: SecretClient,
    prefix_filter: str | None = None
) -> dict[str, TenantConfig]:
    """Load tenant configurations from Key Vault (Phase 2 multi-tenant support).

    Discovers and loads tenant configurations stored in Key Vault following
    the naming convention:
    - tenant-{prefix}-config: JSON with tenant_id, subscription_id, sp_client_id,
                              display_name, enabled, resource_group
    - tenant-{prefix}-secret: Service principal client secret

    Args:
        kv_client: Authenticated SecretClient for Key Vault
        prefix_filter: Optional prefix to filter tenants (e.g., "prod" loads only
                      tenant-prod-* secrets). If None, loads all tenant-*-config secrets.

    Returns:
        Dictionary mapping tenant_id to TenantConfig

    Raises:
        ConfigurationError: If a tenant config is malformed or missing required fields

    Example:
        >>> credential = DefaultAzureCredential()
        >>> kv_client = SecretClient(vault_url="https://my-vault.vault.azure.net", credential=credential)
        >>> tenants = load_tenant_configs_from_keyvault(kv_client)
        >>> for tenant_id, config in tenants.items():
        ...     print(f"Loaded tenant: {config.display}")

    Key Vault Secret Format:
        # tenant-customerA-config (JSON):
        {
            "tenant_id": "12345678-...",
            "subscription_id": "87654321-...",
            "sp_client_id": "abcdef12-...",
            "display_name": "Customer A",
            "enabled": true,
            "resource_group": "rg-customerA"
        }

        # tenant-customerA-secret (plain text):
        the-sp-client-secret-value
    """
    import json

    tenants: dict[str, TenantConfig] = {}

    try:
        # List all secrets to find tenant configs
        secret_properties = list(kv_client.list_properties_of_secrets())

        # Find all tenant config secrets
        config_secrets = []
        for prop in secret_properties:
            name = prop.name
            if name and name.startswith("tenant-") and name.endswith("-config"):
                # Extract prefix (e.g., "customerA" from "tenant-customerA-config")
                prefix = name[7:-7]  # Strip "tenant-" and "-config"
                if prefix_filter is None or prefix.startswith(prefix_filter):
                    config_secrets.append((name, prefix))

        logger.info(f"Found {len(config_secrets)} tenant config(s) in Key Vault")

        # Load each tenant config
        for config_name, prefix in config_secrets:
            secret_name = f"tenant-{prefix}-secret"

            try:
                # Load config JSON
                config_secret = kv_client.get_secret(config_name)
                if not config_secret.value:
                    logger.warning(f"Empty config secret: {config_name}, skipping")
                    continue

                config_data = json.loads(config_secret.value)

                # Load SP secret
                try:
                    sp_secret = kv_client.get_secret(secret_name)
                    if not sp_secret.value:
                        raise ConfigurationError(
                            f"Empty SP secret for tenant {prefix}: {secret_name}"
                        )
                except Exception as e:
                    raise ConfigurationError(
                        f"Failed to load SP secret for tenant {prefix}: {secret_name}. "
                        f"Ensure the secret exists. Error: {e}"
                    ) from e

                # Validate required fields
                required_fields = ["tenant_id", "subscription_id", "sp_client_id"]
                missing = [f for f in required_fields if f not in config_data]
                if missing:
                    raise ConfigurationError(
                        f"Tenant config {config_name} missing required fields: {missing}"
                    )

                # Build TenantConfig
                tenant_config = TenantConfig(
                    tenant_id=config_data["tenant_id"],
                    subscription_id=config_data["subscription_id"],
                    sp_client_id=config_data["sp_client_id"],
                    sp_client_secret=SecretStr(sp_secret.value),
                    display_name=config_data.get("display_name"),
                    enabled=config_data.get("enabled", True),
                    resource_group=config_data.get("resource_group"),
                )

                tenants[tenant_config.tenant_id] = tenant_config
                logger.info(f"Loaded tenant config: {tenant_config.display}")

            except json.JSONDecodeError as e:
                raise ConfigurationError(
                    f"Invalid JSON in tenant config {config_name}: {e}"
                ) from e
            except ValidationError as e:
                raise ConfigurationError(
                    f"Invalid tenant config {config_name}: {e}"
                ) from e

    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(
            f"Failed to load tenant configs from Key Vault: {e}"
        ) from e

    return tenants


async def load_config_with_tenants(
    load_tenants_from_keyvault: bool = True,
    tenant_prefix_filter: str | None = None
) -> OrchestratorConfig:
    """Load configuration with multi-tenant registry from Key Vault.

    This is the recommended entry point for Phase 2+ deployments that need
    multi-tenant support. It loads the base configuration and optionally
    populates the tenant registry from Key Vault.

    Args:
        load_tenants_from_keyvault: If True, load tenant configs from Key Vault
        tenant_prefix_filter: Optional prefix to filter tenant configs

    Returns:
        OrchestratorConfig with populated tenant registry

    Raises:
        ConfigurationError: If configuration loading fails

    Example:
        >>> config = await load_config_with_tenants()
        >>> print(f"Loaded {len(config.tenants)} tenants")
        >>> for tenant in config.list_tenants():
        ...     print(f"  - {tenant.display}")
    """
    # Load base configuration
    config = await load_config_from_env_and_keyvault()

    if load_tenants_from_keyvault:
        try:
            credential = DefaultAzureCredential()
            kv_client = SecretClient(
                vault_url=config.key_vault_url,
                credential=credential
            )

            tenants = load_tenant_configs_from_keyvault(
                kv_client,
                prefix_filter=tenant_prefix_filter
            )

            # Update config with loaded tenants
            # Note: Pydantic models are immutable by default, so we create a new config
            config_dict = config.model_dump()
            config_dict["tenants"] = {
                tid: t.model_dump() for tid, t in tenants.items()
            }
            config = OrchestratorConfig(**config_dict)

            if tenants:
                logger.info(
                    f"Multi-tenant mode: loaded {len(tenants)} tenant(s) from Key Vault"
                )

        except Exception as e:
            # Log warning but don't fail - tenants are optional
            logger.warning(
                f"Failed to load tenant configs from Key Vault: {e}. "
                "Continuing without multi-tenant registry."
            )

    return config
