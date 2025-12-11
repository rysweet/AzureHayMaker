"""Configuration file loader for multi-deployment scenarios.

This module provides functionality to load deployment configurations from
YAML and JSON files, merge them with CLI arguments, and validate against
Pydantic models.

The loader supports:
- YAML and JSON formats (auto-detected by extension)
- CLI argument override (CLI args take precedence over file values)
- Pydantic validation for type safety
- Clear error messages for validation failures

Example:
    >>> result = load_config_file("deployment.yaml")
    >>> if result.error:
    ...     print(f"Error: {result.error}")
    >>> else:
    ...     print(f"Loaded config from: {result.source}")
    ...     config = result.data
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class ConfigSource(str, Enum):
    """Source of configuration value."""

    FILE = "file"
    CLI = "cli"
    DEFAULT = "default"


@dataclass
class ConfigResult:
    """Result of config file loading and validation.

    Attributes:
        data: Parsed configuration data (dict)
        source: Source of the configuration (file path)
        error: Error message if loading/validation failed
        warnings: List of warning messages (e.g., unused keys)
    """

    data: dict[str, Any] | None = None
    source: str | None = None
    error: str | None = None
    warnings: list[str] | None = None

    @property
    def is_valid(self) -> bool:
        """Check if config loaded successfully."""
        return self.error is None and self.data is not None


def load_config_file(file_path: str) -> ConfigResult:
    """Load configuration from YAML or JSON file.

    Auto-detects format based on file extension (.yaml, .yml, .json).

    Args:
        file_path: Path to configuration file

    Returns:
        ConfigResult with loaded data or error message

    Example:
        >>> result = load_config_file("kw-deployment.yaml")
        >>> if result.is_valid:
        ...     config_data = result.data
    """
    path = Path(file_path)

    # Check file exists
    if not path.exists():
        return ConfigResult(error=f"Config file not found: {file_path}")

    # Security: Reject symlinks to prevent reading sensitive files
    if path.is_symlink():
        return ConfigResult(error=f"Config file cannot be a symlink: {file_path}")

    # Check file is readable
    if not path.is_file():
        return ConfigResult(error=f"Config path is not a file: {file_path}")

    try:
        content = path.read_text()
    except Exception as e:
        return ConfigResult(error=f"Failed to read config file: {e}")

    # Auto-detect format by extension
    extension = path.suffix.lower()

    try:
        if extension in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        elif extension == ".json":
            data = json.loads(content)
        else:
            return ConfigResult(
                error=f"Unsupported file format: {extension}. Use .yaml, .yml, or .json"
            )

        # Validate that we got a dict
        if not isinstance(data, dict):
            return ConfigResult(
                error=f"Config file must contain a mapping/object, got {type(data).__name__}"
            )

        return ConfigResult(data=data, source=str(path.absolute()))

    except yaml.YAMLError as e:
        return ConfigResult(error=f"Invalid YAML: {e}")
    except json.JSONDecodeError as e:
        return ConfigResult(error=f"Invalid JSON: {e}")
    except Exception as e:
        return ConfigResult(error=f"Failed to parse config file: {e}")


def merge_with_cli_args(
    config_data: dict[str, Any],
    cli_args: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, ConfigSource]]:
    """Merge config file data with CLI arguments.

    CLI arguments take precedence over config file values. Returns both
    the merged configuration and a source map for tracking where each
    value came from.

    Args:
        config_data: Configuration loaded from file
        cli_args: Arguments provided via CLI (non-None values only)

    Returns:
        Tuple of (merged_config, source_map)
        - merged_config: Combined configuration with CLI overrides
        - source_map: Map of field_name -> ConfigSource

    Example:
        >>> file_config = {"workers": 10, "duration": 8}
        >>> cli_args = {"duration": 2}  # Override duration
        >>> merged, sources = merge_with_cli_args(file_config, cli_args)
        >>> assert merged["duration"] == 2  # CLI wins
        >>> assert sources["duration"] == ConfigSource.CLI
        >>> assert sources["workers"] == ConfigSource.FILE
    """
    merged = config_data.copy()
    source_map: dict[str, ConfigSource] = {}

    # Mark all file values as from file
    for key in config_data.keys():
        source_map[key] = ConfigSource.FILE

    # Override with CLI args (only non-None values)
    for key, value in cli_args.items():
        if value is not None:
            merged[key] = value
            source_map[key] = ConfigSource.CLI

    return merged, source_map


def validate_config(config_data: dict[str, Any], schema_class: type) -> ConfigResult:
    """Validate configuration against a Pydantic model.

    Args:
        config_data: Configuration dictionary to validate
        schema_class: Pydantic model class to validate against

    Returns:
        ConfigResult with validated data or validation errors

    Example:
        >>> from azure_haymaker.knowledge_worker import DeploymentConfig
        >>> config = {"name": "test", "total_workers": 5}
        >>> result = validate_config(config, DeploymentConfig)
        >>> if result.is_valid:
        ...     deployment = result.data  # Pydantic model instance
    """
    try:
        # Create Pydantic model instance (validates on creation)
        validated_instance = schema_class(**config_data)
        return ConfigResult(data=validated_instance)
    except Exception as e:
        # Format validation errors clearly
        error_msg = _format_validation_error(e)
        return ConfigResult(error=error_msg)


def _format_validation_error(error: Exception) -> str:
    """Format Pydantic validation errors for user-friendly display.

    Args:
        error: Exception from Pydantic validation

    Returns:
        Formatted error message with actionable details
    """
    # Check if it's a Pydantic validation error
    if hasattr(error, "errors"):
        error_lines = ["Configuration validation failed:"]
        for err in error.errors():
            field = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            error_lines.append(f"  - {field}: {msg}")
        return "\n".join(error_lines)

    # Generic error
    return f"Configuration validation failed: {error}"


def get_cli_overrides(
    name: str | None = None,
    workers: int | None = None,
    department: str | None = None,
    tenant_domain: str | None = None,
    duration: int | None = None,
    endpoint_type: str | None = None,
    enable_markers: bool | None = None,
    marker_style: str | None = None,
    marker_format: str | None = None,
    enable_ai_generation: bool | None = None,
    email_directive: str | None = None,
    ai_model: str | None = None,
) -> dict[str, Any]:
    """Extract CLI arguments that should override config file values.

    Only includes arguments that were explicitly provided (non-None).
    This is a helper function for commands.py to gather CLI overrides.

    Args:
        name: Deployment name
        workers: Number of workers
        department: Department name
        tenant_domain: M365 tenant domain
        duration: Duration in hours
        endpoint_type: Endpoint type
        enable_markers: Enable email markers
        marker_style: Marker style
        marker_format: Marker format
        enable_ai_generation: Enable AI generation
        email_directive: AI generation directive
        ai_model: Anthropic model name

    Returns:
        Dictionary of non-None CLI arguments

    Note:
        This function uses a simple pattern: only explicitly-provided
        CLI arguments (non-None values) are included in the override dict.
        For boolean flags, use the raw value from Click (which will be None
        if not explicitly set via CLI).
    """
    cli_overrides = {}

    # Add non-None values
    if name is not None:
        cli_overrides["name"] = name
    if workers is not None:
        cli_overrides["total_workers"] = workers
    if tenant_domain is not None:
        cli_overrides["tenant_domain"] = tenant_domain
    if duration is not None:
        cli_overrides["duration_hours"] = duration

    # Handle department - needs special processing for single-dept deployments
    # This will be handled in commands.py where we understand the context

    # Marker configuration
    if enable_markers is not None:
        cli_overrides["email_markers_enabled"] = enable_markers
    if marker_style is not None:
        cli_overrides["marker_style"] = marker_style
    if marker_format is not None:
        cli_overrides["marker_format"] = marker_format

    # Email generation config - these nest under email_generation
    email_gen_overrides = {}
    if enable_ai_generation is not None:
        email_gen_overrides["enabled"] = enable_ai_generation
    if email_directive is not None:
        email_gen_overrides["directive"] = email_directive
    if ai_model is not None:
        email_gen_overrides["model"] = ai_model

    if email_gen_overrides:
        cli_overrides["email_generation"] = email_gen_overrides

    return cli_overrides


def format_source_indicator(source: ConfigSource) -> str:
    """Format a source indicator for display in dry-run output.

    Args:
        source: Configuration source

    Returns:
        Formatted string like "[file]" or "[cli]"

    Example:
        >>> format_source_indicator(ConfigSource.FILE)
        '[file]'
        >>> format_source_indicator(ConfigSource.CLI)
        '[cli]'
    """
    return f"[{source.value}]"


__all__ = [
    "ConfigResult",
    "ConfigSource",
    "load_config_file",
    "merge_with_cli_args",
    "validate_config",
    "get_cli_overrides",
    "format_source_indicator",
]
