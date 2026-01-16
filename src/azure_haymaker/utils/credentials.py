"""Centralized Azure credential management for Azure HayMaker.

This module provides a singleton factory for Azure credentials to avoid
redundant authentication overhead from creating new DefaultAzureCredential
instances across the codebase.

Phase 2 adds MultiTenantCredentialFactory for thread-safe credential caching
per tenant in multi-tenant deployments.

Usage:
    from azure_haymaker.utils.credentials import get_credential

    # Get cached credential (recommended)
    credential = get_credential()

    # Or use the factory directly
    from azure_haymaker.utils.credentials import AzureCredentialFactory
    credential = AzureCredentialFactory.get_credential()

    # Force a new credential (rare use case)
    fresh_credential = AzureCredentialFactory.get_credential(force_refresh=True)

    # Multi-tenant: Get credential for specific tenant
    from azure_haymaker.utils.credentials import MultiTenantCredentialFactory
    credential = MultiTenantCredentialFactory.get_credential_for_tenant(tenant_config)
"""

import logging
import threading
from typing import TYPE_CHECKING

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

if TYPE_CHECKING:
    from azure_haymaker.models.config import OrchestratorConfig, TenantConfig

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


class MultiTenantCredentialFactory:
    """Thread-safe factory for cached credentials per tenant.

    This class maintains a cache of ClientSecretCredential instances,
    one per tenant. Credentials are created lazily and cached for reuse.
    Thread-safe for concurrent access.

    Phase 2 feature for multi-tenant deployments.

    Example:
        >>> from azure_haymaker.models.config import TenantConfig
        >>> tenant = TenantConfig(
        ...     tenant_id="12345678-...",
        ...     subscription_id="...",
        ...     sp_client_id="...",
        ...     sp_client_secret=SecretStr("...")
        ... )
        >>> credential = MultiTenantCredentialFactory.get_credential_for_tenant(tenant)
        >>> # Use credential for Azure SDK clients
        >>> client = ResourceManagementClient(credential, tenant.subscription_id)
    """

    _credentials: dict[str, ClientSecretCredential] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_credential_for_tenant(
        cls, tenant_config: "TenantConfig", force_refresh: bool = False
    ) -> ClientSecretCredential:
        """Get or create a cached credential for a specific tenant.

        Args:
            tenant_config: TenantConfig with credentials for the tenant
            force_refresh: If True, create a new credential even if cached

        Returns:
            ClientSecretCredential for the tenant

        Raises:
            ValueError: If tenant_config is disabled

        Example:
            >>> credential = MultiTenantCredentialFactory.get_credential_for_tenant(tenant)
        """
        if not tenant_config.enabled:
            raise ValueError(
                f"Tenant {tenant_config.tenant_id[:8]}... is disabled. "
                "Cannot create credential for disabled tenant."
            )

        tenant_id = tenant_config.tenant_id

        with cls._lock:
            if tenant_id not in cls._credentials or force_refresh:
                logger.debug(
                    f"Creating new ClientSecretCredential for tenant {tenant_id[:8]}..."
                )
                cls._credentials[tenant_id] = ClientSecretCredential(
                    tenant_id=tenant_config.tenant_id,
                    client_id=tenant_config.sp_client_id,
                    client_secret=tenant_config.sp_client_secret.get_secret_value()
                )
            return cls._credentials[tenant_id]

    @classmethod
    def clear_cache(cls, tenant_id: str | None = None) -> None:
        """Clear cached credentials.

        Args:
            tenant_id: If provided, clear only this tenant's credential.
                      If None, clear all cached credentials.
        """
        with cls._lock:
            if tenant_id:
                if tenant_id in cls._credentials:
                    del cls._credentials[tenant_id]
                    logger.debug(f"Cleared credential cache for tenant {tenant_id[:8]}...")
            else:
                cls._credentials.clear()
                logger.debug("Cleared all multi-tenant credential caches")

    @classmethod
    def get_cached_tenant_ids(cls) -> list[str]:
        """Get list of tenant IDs with cached credentials.

        Returns:
            List of tenant IDs that have cached credentials
        """
        with cls._lock:
            return list(cls._credentials.keys())


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


def get_tenant_credential(
    config: "OrchestratorConfig",
    tenant_id: str | None = None
) -> DefaultAzureCredential | ClientSecretCredential:
    """Get credential for target tenant operations (multi-tenant aware).

    Priority order for credential selection:
    1. If tenant_id provided and found in tenant registry -> use registry credential
    2. If cross-tenant mode (Phase 1) -> use target_tenant_sp credentials
    3. Single-tenant mode -> use cached DefaultAzureCredential

    Args:
        config: Orchestrator configuration with optional cross-tenant credentials
        tenant_id: Optional specific tenant ID to get credential for.
                  If provided, will check the tenant registry first.

    Returns:
        Credential instance appropriate for target tenant operations

    Raises:
        ValueError: If cross-tenant mode enabled but credentials missing,
                   or if tenant_id provided but not found in registry

    Example:
        >>> config = load_config()
        >>> # Phase 1: Use target_tenant credentials
        >>> credential = get_tenant_credential(config)
        >>>
        >>> # Phase 2: Use specific tenant from registry
        >>> credential = get_tenant_credential(config, tenant_id="12345678-...")
        >>> graph_client = GraphServiceClient(credential)
    """
    # Phase 2: Check tenant registry first if tenant_id provided
    if tenant_id:
        tenant_config = config.get_tenant_config(tenant_id)
        if tenant_config:
            logger.debug(
                f"Using multi-tenant registry credential for {tenant_config.display}"
            )
            return MultiTenantCredentialFactory.get_credential_for_tenant(tenant_config)
        else:
            # Check if tenant exists but is disabled
            if tenant_id in config.tenants:
                raise ValueError(
                    f"Tenant {tenant_id[:8]}... is disabled in registry. "
                    "Enable it or remove the tenant_id parameter."
                )
            # Tenant not in registry - fall through to Phase 1 logic
            logger.debug(
                f"Tenant {tenant_id[:8]}... not found in registry, "
                "falling back to Phase 1 logic"
            )

    # Phase 1: Cross-tenant mode with explicit credentials
    if config.is_cross_tenant:
        # Validate cross-tenant credentials present
        if not config.target_tenant_sp_client_id:
            raise ValueError(
                "Cross-tenant mode detected (target_tenant_id differs from AZURE_TENANT_ID) "
                "but TARGET_TENANT_SP_CLIENT_ID not configured. "
                "Set environment variable or Key Vault secret."
            )
        if not config.target_tenant_sp_client_secret:
            raise ValueError(
                "Cross-tenant mode detected but TARGET_TENANT_SP_CLIENT_SECRET not configured. "
                "Set environment variable or Key Vault secret."
            )

        # Return explicit credential for target tenant
        logger.debug(
            f"Using cross-tenant credential for tenant {config.target_tenant_id[:8]}..."
        )
        return ClientSecretCredential(
            tenant_id=config.target_tenant_id,
            client_id=config.target_tenant_sp_client_id,
            client_secret=config.target_tenant_sp_client_secret.get_secret_value()
        )

    # Single-tenant mode: Use existing cached credential
    logger.debug("Using default orchestrator credential (single-tenant mode)")
    return get_credential()


__all__ = [
    "AzureCredentialFactory",
    "MultiTenantCredentialFactory",
    "get_credential",
    "get_async_credential",
    "get_tenant_credential",
]
