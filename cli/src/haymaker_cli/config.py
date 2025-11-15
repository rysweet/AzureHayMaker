"""Configuration management for HayMaker CLI."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from haymaker_cli.auth import AuthConfig


class ProfileConfig(BaseModel):
    """Profile configuration."""

    endpoint: str = Field(description="HayMaker API endpoint URL")
    auth: AuthConfig = Field(default_factory=AuthConfig, description="Authentication config")


class CliConfig(BaseModel):
    """CLI configuration."""

    profiles: dict[str, ProfileConfig] = Field(
        default_factory=dict, description="Named profiles"
    )
    default_profile: str = Field(default="default", description="Default profile name")


def get_config_path() -> Path:
    """Get path to CLI configuration file.

    Returns:
        Path to ~/.haymaker/config.yaml

    Example:
        >>> path = get_config_path()
        >>> path.name
        'config.yaml'
    """
    config_dir = Path.home() / ".haymaker"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


def load_cli_config(profile: str | None = None) -> ProfileConfig:
    """Load CLI configuration from file or environment.

    Priority order:
    1. Environment variables (HAYMAKER_ENDPOINT, HAYMAKER_API_KEY)
    2. Configuration file (~/.haymaker/config.yaml)
    3. Default values

    Args:
        profile: Profile name to load (defaults to 'default' or config.default_profile)

    Returns:
        Loaded profile configuration

    Raises:
        ValueError: If profile not found or configuration invalid

    Example:
        >>> # Load default profile
        >>> config = load_cli_config()  # doctest: +SKIP

        >>> # Load specific profile
        >>> config = load_cli_config('production')  # doctest: +SKIP
    """
    # Check environment variables first (highest priority)
    env_endpoint = os.getenv("HAYMAKER_ENDPOINT")
    env_api_key = os.getenv("HAYMAKER_API_KEY")
    env_tenant_id = os.getenv("HAYMAKER_TENANT_ID")

    if env_endpoint:
        # Build config from environment variables
        auth_config = AuthConfig()
        if env_api_key:
            auth_config.type = "api_key"
            auth_config.api_key = env_api_key
        elif env_tenant_id:
            auth_config.type = "azure_ad"
            auth_config.tenant_id = env_tenant_id

        return ProfileConfig(endpoint=env_endpoint, auth=auth_config)

    # Load from configuration file
    config_path = get_config_path()

    if not config_path.exists():
        raise ValueError(
            f"Configuration file not found: {config_path}\n"
            "Create configuration file or set HAYMAKER_ENDPOINT environment variable.\n"
            "Example:\n"
            "  haymaker config set endpoint https://haymaker.azurewebsites.net\n"
            "  haymaker config set api-key your-api-key"
        )

    with open(config_path) as f:
        config_data = yaml.safe_load(f) or {}

    config = CliConfig(**config_data)

    # Determine which profile to use
    profile_name = profile or config.default_profile

    if profile_name not in config.profiles:
        available = ", ".join(config.profiles.keys())
        raise ValueError(
            f"Profile '{profile_name}' not found in configuration.\n"
            f"Available profiles: {available}\n"
            "Create a new profile with: haymaker config set endpoint <url> --profile {profile_name}"
        )

    return config.profiles[profile_name]


def save_cli_config(config: CliConfig) -> None:
    """Save CLI configuration to file.

    Args:
        config: Configuration to save

    Example:
        >>> config = CliConfig(profiles={"default": ProfileConfig(endpoint="https://api.example.com")})
        >>> save_cli_config(config)  # doctest: +SKIP
    """
    config_path = get_config_path()

    with open(config_path, "w") as f:
        yaml.safe_dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)


def set_config_value(key: str, value: str, profile: str = "default") -> None:
    """Set configuration value.

    Args:
        key: Configuration key (e.g., 'endpoint', 'api-key', 'tenant-id')
        value: Configuration value
        profile: Profile name (default: 'default')

    Example:
        >>> set_config_value('endpoint', 'https://api.example.com')  # doctest: +SKIP
        >>> set_config_value('api-key', 'my-key', profile='production')  # doctest: +SKIP
    """
    config_path = get_config_path()

    # Load existing config or create new
    if config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
        config = CliConfig(**config_data)
    else:
        config = CliConfig()

    # Ensure profile exists
    if profile not in config.profiles:
        config.profiles[profile] = ProfileConfig(endpoint="")

    profile_config = config.profiles[profile]

    # Set value based on key
    if key == "endpoint":
        profile_config.endpoint = value
    elif key == "api-key":
        profile_config.auth.type = "api_key"
        profile_config.auth.api_key = value
    elif key == "tenant-id":
        profile_config.auth.type = "azure_ad"
        profile_config.auth.tenant_id = value
    else:
        raise ValueError(
            f"Unknown configuration key: {key}\n"
            "Valid keys: endpoint, api-key, tenant-id"
        )

    # Save updated config
    save_cli_config(config)


def get_config_value(key: str, profile: str = "default") -> str | None:
    """Get configuration value.

    Args:
        key: Configuration key
        profile: Profile name (default: 'default')

    Returns:
        Configuration value or None if not set

    Example:
        >>> get_config_value('endpoint')  # doctest: +SKIP
        'https://api.example.com'
    """
    try:
        profile_config = load_cli_config(profile)
    except ValueError:
        return None

    if key == "endpoint":
        return profile_config.endpoint
    elif key == "api-key":
        return profile_config.auth.api_key
    elif key == "tenant-id":
        return profile_config.auth.tenant_id
    else:
        return None


def list_config(profile: str = "default") -> dict[str, Any]:
    """List all configuration values for a profile.

    Args:
        profile: Profile name (default: 'default')

    Returns:
        Dictionary of configuration values

    Example:
        >>> list_config()  # doctest: +SKIP
        {'endpoint': 'https://api.example.com', 'auth_type': 'api_key'}
    """
    try:
        profile_config = load_cli_config(profile)
    except ValueError:
        return {}

    return {
        "endpoint": profile_config.endpoint,
        "auth_type": profile_config.auth.type,
        "tenant_id": profile_config.auth.tenant_id or "(not set)",
    }
