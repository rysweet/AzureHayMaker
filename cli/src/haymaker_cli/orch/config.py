"""Configuration management for orchestrator CLI commands."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from haymaker_cli.orch.models import ConfigError


class OrchestratorConfig(BaseModel):
    """Orchestrator configuration for Azure Container Apps.

    Configuration priority (highest to lowest):
    1. Environment variables (AZURE_SUBSCRIPTION_ID, etc.)
    2. Configuration file (~/.haymaker/config.yaml)
    3. Default values
    """

    subscription_id: str = Field(description="Azure subscription ID")
    resource_group: str = Field(description="Azure resource group name")
    container_app_name: str | None = Field(
        default=None, description="Default container app name (optional)"
    )
    location: str = Field(default="eastus", description="Default Azure region")
    tenant_id: str | None = Field(default=None, description="Azure tenant ID (optional)")


def get_config_path() -> Path:
    """Get path to CLI configuration file.

    Creates config directory with secure permissions (0700) and ensures
    config file has restrictive permissions (0600) for security.

    Returns:
        Path to ~/.haymaker/config.yaml

    Example:
        >>> path = get_config_path()
        >>> path.name
        'config.yaml'
    """
    config_dir = Path.home() / ".haymaker"
    config_dir.mkdir(parents=True, exist_ok=True)
    # Set directory permissions to owner-only (drwx------)
    config_dir.chmod(0o700)

    config_path = config_dir / "config.yaml"
    # If config file exists, ensure it has secure permissions
    if config_path.exists():
        config_path.chmod(0o600)  # -rw------- (owner read/write only)

    return config_path


def load_orchestrator_config(
    subscription_id: str | None = None,
    resource_group: str | None = None,
    container_app_name: str | None = None,
) -> OrchestratorConfig:
    """Load orchestrator configuration from environment, file, or parameters.

    Configuration priority (highest to lowest):
    1. Function parameters (if provided)
    2. Environment variables (AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, etc.)
    3. Configuration file (~/.haymaker/config.yaml under 'orchestrator' key)
    4. Default values (where applicable)

    Args:
        subscription_id: Azure subscription ID (overrides env/config)
        resource_group: Azure resource group name (overrides env/config)
        container_app_name: Container app name (overrides env/config)

    Returns:
        Loaded orchestrator configuration

    Raises:
        ConfigError: If required configuration is missing or invalid

    Example:
        >>> # Load from environment/config
        >>> config = load_orchestrator_config()  # doctest: +SKIP

        >>> # Override specific values
        >>> config = load_orchestrator_config(
        ...     subscription_id="my-sub-id",
        ...     resource_group="my-rg"
        ... )  # doctest: +SKIP
    """
    # Priority 1: Function parameters
    # Priority 2: Environment variables
    env_subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
    env_resource_group = resource_group or os.getenv("AZURE_RESOURCE_GROUP")
    env_container_app_name = container_app_name or os.getenv("AZURE_CONTAINER_APP_NAME")
    env_location = os.getenv("AZURE_LOCATION", "eastus")
    env_tenant_id = os.getenv("AZURE_TENANT_ID")

    # If both required values from env/params, use them
    if env_subscription_id and env_resource_group:
        return OrchestratorConfig(
            subscription_id=env_subscription_id,
            resource_group=env_resource_group,
            container_app_name=env_container_app_name,
            location=env_location,
            tenant_id=env_tenant_id,
        )

    # Priority 3: Load from configuration file
    config_path = get_config_path()

    if not config_path.exists():
        # If no config file and missing required env vars, raise error
        raise ConfigError(
            "Configuration not found. Either:\n"
            "1. Set environment variables: AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP\n"
            "2. Create configuration file with: haymaker config set orchestrator.subscription_id <id>\n"
            f"3. Configuration file expected at: {config_path}",
            details={
                "config_path": str(config_path),
                "env_vars": "AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP",
            },
        )

    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
    except Exception as e:
        raise ConfigError(
            f"Failed to read configuration file: {config_path}",
            details={"error": str(e), "path": str(config_path)},
        ) from e

    # Extract orchestrator section
    orch_config = config_data.get("orchestrator", {})

    # Merge: env/params override config file
    final_subscription_id = env_subscription_id or orch_config.get("subscription_id")
    final_resource_group = env_resource_group or orch_config.get("resource_group")
    final_container_app_name = env_container_app_name or orch_config.get("container_app_name")
    final_location = env_location if env_location != "eastus" else orch_config.get(
        "location", "eastus"
    )
    final_tenant_id = env_tenant_id or orch_config.get("tenant_id")

    # Validate required fields
    if not final_subscription_id:
        raise ConfigError(
            "Azure subscription ID not configured. Set via:\n"
            "1. Environment variable: AZURE_SUBSCRIPTION_ID\n"
            "2. Configuration: haymaker config set orchestrator.subscription_id <id>\n"
            "3. Command flag: --subscription-id <id>",
            details={"missing_field": "subscription_id"},
        )

    if not final_resource_group:
        raise ConfigError(
            "Azure resource group not configured. Set via:\n"
            "1. Environment variable: AZURE_RESOURCE_GROUP\n"
            "2. Configuration: haymaker config set orchestrator.resource_group <name>\n"
            "3. Command flag: --resource-group <name>",
            details={"missing_field": "resource_group"},
        )

    return OrchestratorConfig(
        subscription_id=final_subscription_id,
        resource_group=final_resource_group,
        container_app_name=final_container_app_name,
        location=final_location,
        tenant_id=final_tenant_id,
    )


def save_orchestrator_config(config: OrchestratorConfig) -> None:
    """Save orchestrator configuration to file with secure permissions.

    Updates the 'orchestrator' section of the configuration file while
    preserving other sections (profiles, etc.).

    Args:
        config: Orchestrator configuration to save

    Example:
        >>> config = OrchestratorConfig(
        ...     subscription_id="my-sub",
        ...     resource_group="my-rg"
        ... )
        >>> save_orchestrator_config(config)  # doctest: +SKIP
    """
    config_path = get_config_path()

    # Load existing config or create new
    if config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
    else:
        config_data = {}

    # Update orchestrator section
    config_data["orchestrator"] = config.model_dump(exclude_none=True)

    # Write back to file
    with open(config_path, "w") as f:
        yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)

    # Ensure secure file permissions
    config_path.chmod(0o600)  # -rw------- (owner read/write only)


def set_orchestrator_config_value(key: str, value: str) -> None:
    """Set a single orchestrator configuration value.

    Args:
        key: Configuration key (subscription_id, resource_group, container_app_name, location, tenant_id)
        value: Configuration value

    Raises:
        ConfigError: If key is invalid

    Example:
        >>> set_orchestrator_config_value('subscription_id', 'my-sub-id')  # doctest: +SKIP
        >>> set_orchestrator_config_value('resource_group', 'my-rg')  # doctest: +SKIP
    """
    valid_keys = {"subscription_id", "resource_group", "container_app_name", "location", "tenant_id"}

    if key not in valid_keys:
        raise ConfigError(
            f"Invalid configuration key: {key}",
            details={
                "invalid_key": key,
                "valid_keys": ", ".join(sorted(valid_keys)),
            },
        )

    # Load existing config or create minimal one
    try:
        existing_config = load_orchestrator_config()
    except ConfigError:
        # Create minimal config with required fields
        existing_config = OrchestratorConfig(
            subscription_id=value if key == "subscription_id" else "",
            resource_group=value if key == "resource_group" else "",
        )

    # Update the specified field
    setattr(existing_config, key, value)

    # Save updated config
    save_orchestrator_config(existing_config)


def get_orchestrator_config_value(key: str) -> str | None:
    """Get a single orchestrator configuration value.

    Args:
        key: Configuration key

    Returns:
        Configuration value or None if not set

    Example:
        >>> value = get_orchestrator_config_value('subscription_id')  # doctest: +SKIP
        >>> print(value)  # doctest: +SKIP
        'my-subscription-id'
    """
    try:
        config = load_orchestrator_config()
    except ConfigError:
        return None

    return getattr(config, key, None)
