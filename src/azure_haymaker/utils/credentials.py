"""Centralized Azure credential management for Azure HayMaker.

This module provides a singleton factory for Azure credentials to avoid
redundant authentication overhead from creating new DefaultAzureCredential
instances across the codebase.

Usage:
    from azure_haymaker.utils.credentials import get_credential

    # Get cached credential (recommended)
    credential = get_credential()

    # Or use the factory directly
    from azure_haymaker.utils.credentials import AzureCredentialFactory
    credential = AzureCredentialFactory.get_credential()

    # Force a new credential (rare use case)
    fresh_credential = AzureCredentialFactory.get_credential(force_refresh=True)
"""

import logging
import threading

from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

logger = logging.getLogger(__name__)


class AzureCredentialFactory:
    """Factory for cached Azure credentials.

    This class caches DefaultAzureCredential instances to avoid redundant
    authentication overhead. The credential is thread-safe and can be shared
    across the application.

    The factory maintains separate caches for sync and async credentials
    since they are different types.

    Example:
        >>> credential = AzureCredentialFactory.get_credential()
        >>> blob_client = BlobServiceClient(account_url, credential=credential)

        >>> async_credential = AzureCredentialFactory.get_async_credential()
        >>> async_client = AsyncBlobServiceClient(account_url, credential=async_credential)
    """

    _credential: DefaultAzureCredential | None = None
    _async_credential: AsyncDefaultAzureCredential | None = None
    _credential_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_credential(cls, force_refresh: bool = False) -> DefaultAzureCredential:
        """Get cached DefaultAzureCredential instance.

        This method returns a cached credential instance. The credential
        handles token refresh automatically, so a single instance can be
        reused throughout the application lifecycle.

        Args:
            force_refresh: If True, creates a new credential instance
                          even if one is cached. Use sparingly.

        Returns:
            DefaultAzureCredential instance for Azure SDK clients.

        Example:
            >>> credential = AzureCredentialFactory.get_credential()
            >>> client = ResourceManagementClient(credential, subscription_id)
        """
        with cls._credential_lock:
            if cls._credential is None or force_refresh:
                logger.debug("Creating new DefaultAzureCredential instance")
                cls._credential = DefaultAzureCredential()
            return cls._credential

    @classmethod
    def get_async_credential(cls, force_refresh: bool = False) -> AsyncDefaultAzureCredential:
        """Get cached async DefaultAzureCredential instance.

        This method returns a cached async credential instance for use
        with async Azure SDK clients.

        Args:
            force_refresh: If True, creates a new credential instance
                          even if one is cached. Use sparingly.

        Returns:
            AsyncDefaultAzureCredential instance for async Azure SDK clients.

        Example:
            >>> credential = AzureCredentialFactory.get_async_credential()
            >>> async with BlobServiceClient(url, credential=credential) as client:
            ...     await client.get_account_information()
        """
        with cls._credential_lock:
            if cls._async_credential is None or force_refresh:
                logger.debug("Creating new AsyncDefaultAzureCredential instance")
                cls._async_credential = AsyncDefaultAzureCredential()
            return cls._async_credential

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached credentials.

        This is useful for testing or when credentials need to be
        re-acquired (e.g., after token expiration issues).
        """
        with cls._credential_lock:
            cls._credential = None
            cls._async_credential = None
            logger.debug("Credential cache cleared")


def get_credential(force_refresh: bool = False) -> DefaultAzureCredential:
    """Convenience function to get cached Azure credential.

    This is the recommended way to obtain Azure credentials throughout
    the codebase. It returns a cached DefaultAzureCredential instance.

    Args:
        force_refresh: If True, creates a new credential instance.

    Returns:
        DefaultAzureCredential instance.

    Example:
        >>> from azure_haymaker.utils.credentials import get_credential
        >>> credential = get_credential()
        >>> client = SecretClient(vault_url, credential=credential)
    """
    return AzureCredentialFactory.get_credential(force_refresh=force_refresh)


def get_async_credential(
    force_refresh: bool = False,
) -> AsyncDefaultAzureCredential:
    """Convenience function to get cached async Azure credential.

    This is the recommended way to obtain async Azure credentials.

    Args:
        force_refresh: If True, creates a new credential instance.

    Returns:
        AsyncDefaultAzureCredential instance.

    Example:
        >>> from azure_haymaker.utils.credentials import get_async_credential
        >>> credential = get_async_credential()
        >>> async with client:
        ...     await client.do_something()
    """
    return AzureCredentialFactory.get_async_credential(force_refresh=force_refresh)


__all__ = [
    "AzureCredentialFactory",
    "get_credential",
    "get_async_credential",
]
