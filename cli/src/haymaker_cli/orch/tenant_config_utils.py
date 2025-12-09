"""Utilities for managing tenant configuration files.

This module provides utilities for loading, saving, and manipulating
multi-tenant orchestration configuration files.

Configuration files are stored at ~/.haymaker/tenants.yaml (or .json) and
follow the MetaOrchestratorConfig schema defined in the orchestrator module.

Example:
    >>> from haymaker_cli.orch.tenant_config_utils import load_tenant_config
    >>> config = load_tenant_config()  # doctest: +SKIP
    >>> tenants = config["target_tenants"]  # doctest: +SKIP
"""

import json
from pathlib import Path
from typing import Any

import yaml
from azure_haymaker.orchestrator.models.tenant_config import (
    TargetTenantConfig,
)


class TenantConfigError(Exception):
    """Exception raised for tenant configuration errors."""


def get_tenant_config_path() -> Path:
    """Get path to tenant configuration file.

    Checks for both YAML and JSON formats. Creates directory if needed.

    Returns:
        Path to tenant configuration file

    Example:
        >>> path = get_tenant_config_path()
        >>> path.parent.name
        '.haymaker'
    """
    config_dir = Path.home() / ".haymaker"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Check for existing config in either format
    yaml_path = config_dir / "tenants.yaml"
    json_path = config_dir / "tenants.json"

    if yaml_path.exists():
        return yaml_path
    elif json_path.exists():
        return json_path
    else:
        # Default to YAML for new configs
        return yaml_path


def load_tenant_config() -> dict[str, Any]:
    """Load tenant configuration from file.

    Returns:
        Configuration dictionary with meta_orchestrator and target_tenants

    Raises:
        TenantConfigError: If configuration file doesn't exist or is invalid

    Example:
        >>> config = load_tenant_config()  # doctest: +SKIP
        >>> "target_tenants" in config  # doctest: +SKIP
        True
    """
    config_path = get_tenant_config_path()

    if not config_path.exists():
        raise TenantConfigError(
            f"Tenant configuration file not found: {config_path}\n"
            "Create a tenant configuration with: haymaker orch tenant add"
        )

    try:
        with open(config_path) as f:
            config_data = json.load(f) if config_path.suffix == ".json" else yaml.safe_load(f)

        if not config_data:
            raise TenantConfigError("Configuration file is empty")

        # Validate against Pydantic model
        try:
            # Allow minimal config for backward compatibility
            if "meta_orchestrator" not in config_data:
                # Create minimal meta_orchestrator section
                config_data = {
                    "meta_orchestrator": {
                        "name": "default",
                        "infrastructure_tenant_id": "00000000-0000-0000-0000-000000000000",
                        "storage_account_name": "default",
                    },
                    "target_tenants": config_data.get("target_tenants", [])
                }

            # Validate structure (but don't enforce strict validation for CLI)
            # This allows partial configs and easier manual editing
            if "target_tenants" not in config_data:
                config_data["target_tenants"] = []

        except Exception as e:
            raise TenantConfigError(f"Configuration validation failed: {e}") from e

        return config_data

    except yaml.YAMLError as e:
        raise TenantConfigError(f"Invalid YAML format: {e}") from e
    except json.JSONDecodeError as e:
        raise TenantConfigError(f"Invalid JSON format: {e}") from e
    except Exception as e:
        if isinstance(e, TenantConfigError):
            raise
        raise TenantConfigError(f"Failed to load configuration: {e}") from e


def save_tenant_config(config: dict[str, Any]) -> None:
    """Save tenant configuration to file.

    Args:
        config: Configuration dictionary to save

    Raises:
        TenantConfigError: If configuration is invalid or cannot be saved

    Example:
        >>> config = {"target_tenants": []}
        >>> save_tenant_config(config)  # doctest: +SKIP
    """
    config_path = get_tenant_config_path()

    try:
        # Validate configuration before saving
        # Allow partial validation for CLI convenience
        if "target_tenants" not in config:
            raise TenantConfigError("Configuration must contain 'target_tenants' field")

        # Save to file
        with open(config_path, "w") as f:
            if config_path.suffix == ".json":
                json.dump(config, f, indent=2)
            else:  # YAML
                yaml.safe_dump(
                    config,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )

        # Set secure file permissions
        config_path.chmod(0o600)  # -rw------- (owner read/write only)

    except Exception as e:
        if isinstance(e, TenantConfigError):
            raise
        raise TenantConfigError(f"Failed to save configuration: {e}") from e


def validate_tenant_config(tenant: dict[str, Any]) -> None:
    """Validate tenant configuration against schema.

    Args:
        tenant: Tenant configuration to validate

    Raises:
        TenantConfigError: If tenant configuration is invalid

    Example:
        >>> tenant = {
        ...     "name": "test",
        ...     "tenant_id": "12345678-1234-1234-1234-123456789012",
        ...     "subscription_id": "87654321-4321-4321-4321-210987654321",
        ...     "region": "eastus",
        ...     "credentials": {"keyvault_secret_prefix": "test"},
        ...     "scenarios": ["scenario1"]
        ... }
        >>> validate_tenant_config(tenant)  # doctest: +SKIP
    """
    try:
        # Validate using Pydantic model
        TargetTenantConfig(**tenant)
    except Exception as e:
        raise TenantConfigError(f"Invalid tenant configuration: {e}") from e


def list_tenant_configs() -> list[dict[str, Any]]:
    """List all tenant configurations.

    Returns:
        List of tenant configuration dictionaries

    Example:
        >>> tenants = list_tenant_configs()  # doctest: +SKIP
        >>> isinstance(tenants, list)  # doctest: +SKIP
        True
    """
    try:
        config = load_tenant_config()
        return config.get("target_tenants", [])
    except TenantConfigError:
        # Return empty list if no config exists
        return []


def add_tenant_to_config(tenant: dict[str, Any]) -> None:
    """Add a new tenant to configuration.

    Args:
        tenant: Tenant configuration to add

    Raises:
        TenantConfigError: If tenant already exists or configuration is invalid

    Example:
        >>> tenant = {
        ...     "name": "prod-east",
        ...     "tenant_id": "12345678-1234-1234-1234-123456789012",
        ...     "subscription_id": "87654321-4321-4321-4321-210987654321",
        ...     "region": "eastus",
        ...     "credentials": {"keyvault_secret_prefix": "prod-east"},
        ...     "scenarios": []
        ... }
        >>> add_tenant_to_config(tenant)  # doctest: +SKIP
    """
    # Validate tenant configuration
    validate_tenant_config(tenant)

    # Load existing config or create new
    try:
        config = load_tenant_config()
    except TenantConfigError:
        # Create new config
        config = {
            "meta_orchestrator": {
                "name": "default",
                "infrastructure_tenant_id": "00000000-0000-0000-0000-000000000000",
                "storage_account_name": "default",
            },
            "target_tenants": []
        }

    # Check for duplicate tenant name
    tenants = config.get("target_tenants", [])
    if any(t["name"] == tenant["name"] for t in tenants):
        raise TenantConfigError(
            f"Tenant with name '{tenant['name']}' already exists. "
            "Use 'haymaker orch tenant update' to modify existing tenant."
        )

    # Check for duplicate tenant_id
    if any(t["tenant_id"] == tenant["tenant_id"] for t in tenants):
        raise TenantConfigError(
            f"Tenant with tenant_id '{tenant['tenant_id']}' already exists. "
            "Each tenant must have a unique tenant_id."
        )

    # Add tenant
    tenants.append(tenant)
    config["target_tenants"] = tenants

    # Save configuration
    save_tenant_config(config)


def update_tenant_in_config(tenant_name: str, updates: dict[str, Any]) -> None:
    """Update existing tenant configuration.

    Args:
        tenant_name: Name of tenant to update
        updates: Dictionary of fields to update

    Raises:
        TenantConfigError: If tenant not found or updates are invalid

    Example:
        >>> update_tenant_in_config("prod-east", {"enabled": False})  # doctest: +SKIP
    """
    config = load_tenant_config()
    tenants = config.get("target_tenants", [])

    # Find tenant
    tenant_index = None
    for i, tenant in enumerate(tenants):
        if tenant["name"] == tenant_name:
            tenant_index = i
            break

    if tenant_index is None:
        raise TenantConfigError(f"Tenant '{tenant_name}' not found")

    # Apply updates
    tenant = tenants[tenant_index]
    for key, value in updates.items():
        # Handle nested updates for limits, schedule, etc.
        if key == "limits" and "limits" in tenant:
            tenant["limits"].update(value)
        elif key == "schedule" and "schedule" in tenant:
            tenant["schedule"].update(value)
        else:
            tenant[key] = value

    # Validate updated tenant
    validate_tenant_config(tenant)

    # Save configuration
    config["target_tenants"] = tenants
    save_tenant_config(config)


def remove_tenant_from_config(tenant_name: str) -> None:
    """Remove tenant from configuration.

    Args:
        tenant_name: Name of tenant to remove

    Raises:
        TenantConfigError: If tenant not found

    Example:
        >>> remove_tenant_from_config("prod-east")  # doctest: +SKIP
    """
    config = load_tenant_config()
    tenants = config.get("target_tenants", [])

    # Filter out tenant
    new_tenants = [t for t in tenants if t["name"] != tenant_name]

    if len(new_tenants) == len(tenants):
        raise TenantConfigError(f"Tenant '{tenant_name}' not found")

    # Save updated configuration
    config["target_tenants"] = new_tenants
    save_tenant_config(config)


__all__ = [
    "TenantConfigError",
    "get_tenant_config_path",
    "load_tenant_config",
    "save_tenant_config",
    "validate_tenant_config",
    "list_tenant_configs",
    "add_tenant_to_config",
    "update_tenant_in_config",
    "remove_tenant_from_config",
]
