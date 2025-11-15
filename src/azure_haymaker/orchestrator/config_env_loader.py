"""Load environment configuration from .env files for local development.

This module provides functionality to load .env files with appropriate
security warnings for production environments.
"""

import logging
import os
from pathlib import Path

from dotenv import dotenv_values

logger = logging.getLogger(__name__)


def load_dotenv_with_warnings() -> dict[str, str]:
    """Load .env file from project root and return as dictionary.

    This function searches for a .env file in the project root directory
    and loads its contents. It emits appropriate log messages based on
    the environment (production vs development).

    Priority order for configuration:
    1. Environment variables (explicit override)
    2. Azure Key Vault (production secrets)
    3. .env file (local development only)

    Returns:
        dict[str, str]: Environment variables loaded from .env file.
                       Returns empty dict if .env file not found.

    Side Effects:
        - Reads .env file from project root
        - Logs WARNING if AZURE_FUNCTIONS_ENVIRONMENT indicates production
        - Logs INFO about .env usage for development
        - Logs DEBUG if .env file not found

    Example:
        >>> dotenv_vars = load_dotenv_with_warnings()
        >>> if "AZURE_TENANT_ID" in dotenv_vars:
        ...     print(f"Found tenant: {dotenv_vars['AZURE_TENANT_ID']}")
    """
    # Find .env file in project root (3 levels up from this file)
    # Path: src/azure_haymaker/orchestrator/config_env_loader.py -> project root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"

    if not env_path.exists():
        logger.debug(
            ".env file not found at %s - skipping .env loading. "
            "This is normal for production deployments.",
            env_path,
        )
        return {}

    # Check if we're running in production
    azure_env = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT", "").lower()
    is_production = azure_env == "production"

    if is_production:
        logger.warning(
            "WARNING: .env file detected in production environment (%s). "
            "For security, production deployments should use Azure Key Vault "
            "for secrets management. The .env file should only be used for "
            "local development. Path: %s",
            azure_env,
            env_path,
        )
    else:
        logger.info(
            "Loading configuration from .env file for local development. "
            "Environment: %s, Path: %s",
            azure_env or "development",
            env_path,
        )

    # Load .env file and convert to regular dict
    try:
        dotenv_dict = dotenv_values(env_path)
        # Filter out None values and convert to dict[str, str]
        result = {k: v for k, v in dotenv_dict.items() if v is not None}
        logger.debug("Loaded %d variables from .env file", len(result))
        return result
    except Exception as e:
        logger.error(
            "Failed to load .env file from %s: %s. "
            "Configuration will fall back to environment variables and Key Vault.",
            env_path,
            e,
        )
        return {}
