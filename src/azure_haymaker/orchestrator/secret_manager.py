"""Key Vault secret management for Service Principal credentials.

This module handles storing and retrieving service principal secrets
from Azure Key Vault.

Philosophy:
- Single responsibility: Secret storage operations
- Secure by default
- Clear error handling for missing secrets
"""

import asyncio
import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)


async def store_secret(
    key_vault_client: SecretClient,
    secret_name: str,
    secret_value: str,
) -> None:
    """Store a secret in Azure Key Vault.

    Args:
        key_vault_client: Key Vault client for secret operations
        secret_name: Name of the secret to store
        secret_value: Secret value to store

    Raises:
        Exception: If secret storage fails
    """
    try:
        await asyncio.to_thread(
            key_vault_client.set_secret,
            secret_name,
            secret_value,
        )
        logger.info(f"Secret stored in Key Vault: {secret_name}")
    except Exception as e:
        logger.error(f"Failed to store secret {secret_name}: {e}")
        raise


async def delete_secret(
    key_vault_client: SecretClient,
    secret_name: str,
) -> None:
    """Delete a secret from Azure Key Vault.

    Args:
        key_vault_client: Key Vault client for secret operations
        secret_name: Name of the secret to delete

    Note:
        Does not raise error if secret doesn't exist (idempotent)
    """
    try:
        await asyncio.to_thread(
            key_vault_client.begin_delete_secret,
            secret_name,
        )
        logger.info(f"Secret deleted from Key Vault: {secret_name}")
    except ResourceNotFoundError:
        # Secret not found, that's okay
        logger.warning(f"Key Vault secret {secret_name} not found for deletion")
    except Exception as e:
        logger.error(f"Error deleting Key Vault secret {secret_name}: {e}")


def get_secret_name_for_sp(sp_name: str) -> str:
    """Generate Key Vault secret name for a service principal.

    Args:
        sp_name: Service principal name (e.g., "AzureHayMaker-scenario1-admin")

    Returns:
        Secret name (e.g., "scenario-sp-scenario1-secret")

    Example:
        >>> get_secret_name_for_sp("AzureHayMaker-test-scenario-admin")
        'scenario-sp-test-scenario-secret'
    """
    return sp_name.replace("AzureHayMaker-", "scenario-sp-").replace("-admin", "-secret")


__all__ = [
    "delete_secret",
    "get_secret_name_for_sp",
    "store_secret",
]
