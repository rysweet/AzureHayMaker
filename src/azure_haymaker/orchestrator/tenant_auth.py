"""Tenant authentication and credential management for cross-tenant orchestration.

This module provides secure credential management for authenticating to multiple
Azure tenants using Key Vault-backed credential storage with caching.

Phase 1 (MVP) - Foundation: Cross-tenant authentication and credential retrieval.
"""

from azure.core.exceptions import AzureError, ResourceNotFoundError
from pydantic import BaseModel, SecretStr


class CredentialNotFoundError(Exception):
    """Raised when tenant credentials cannot be found in Key Vault."""

    pass


class InvalidCredentialError(Exception):
    """Raised when tenant credentials are invalid or malformed."""

    pass


class TenantCredential(BaseModel):
    """Tenant service principal credentials with secure secret handling.

    Encapsulates credentials for authenticating to a target tenant,
    with secure secret handling using Pydantic SecretStr.

    Attributes:
        client_id: Service principal application (client) ID
        client_secret: Service principal client secret (masked in logs)
        tenant_id: Azure tenant ID
        subscription_id: Azure subscription ID
    """

    client_id: str
    client_secret: SecretStr
    tenant_id: str
    subscription_id: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary (for storage or serialization).

        Returns:
            Dictionary with all credential fields (secret explicitly unwrapped)
        """
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret.get_secret_value(),
            "tenant_id": self.tenant_id,
            "subscription_id": self.subscription_id,
        }

    def __str__(self) -> str:
        """String representation with masked secret.

        Returns:
            String representation with client_secret masked
        """
        return (
            f"TenantCredential(client_id={self.client_id}, "
            f"tenant_id={self.tenant_id}, "
            f"subscription_id={self.subscription_id}, "
            f"client_secret=***)"
        )


class TenantCredentialManager:
    """Manages cross-tenant authentication and credential retrieval.

    Provides secure credential management with Key Vault backend storage
    and in-memory caching for performance. Credentials are stored per-tenant
    with a naming convention: {tenant-name}-{credential-type}

    Attributes:
        kv_client: Azure Key Vault SecretClient for credential storage
        _credential_cache: In-memory cache of retrieved credentials
    """

    def __init__(self, keyvault_client):
        """Initialize credential manager.

        Args:
            keyvault_client: Azure Key Vault SecretClient instance
        """
        self.kv_client = keyvault_client
        self._credential_cache: dict[str, TenantCredential] = {}

    async def get_tenant_credential(self, tenant_name: str) -> TenantCredential:
        """Retrieve credential for target tenant from Key Vault.

        Implements caching: credentials are cached per session and automatically
        refreshed when needed (Azure SDK handles token refresh).

        Args:
            tenant_name: Tenant identifier (used as prefix for KV secrets)

        Returns:
            TenantCredential with authentication details

        Raises:
            CredentialNotFoundError: If secrets not found in Key Vault
            InvalidCredentialError: If credentials are malformed
        """
        # Check cache first
        if tenant_name in self._credential_cache:
            return self._credential_cache[tenant_name]

        # Retrieve from Key Vault
        try:
            client_id_secret_name = f"{tenant_name}-client-id"
            client_secret_secret_name = f"{tenant_name}-client-secret"
            tenant_id_secret_name = f"{tenant_name}-tenant-id"
            subscription_id_secret_name = f"{tenant_name}-subscription-id"

            # Get all secrets
            client_id_secret = self.kv_client.get_secret(client_id_secret_name)
            client_secret_secret = self.kv_client.get_secret(client_secret_secret_name)
            tenant_id_secret = self.kv_client.get_secret(tenant_id_secret_name)
            subscription_id_secret = self.kv_client.get_secret(subscription_id_secret_name)

            # Extract values
            client_id = client_id_secret.value
            client_secret = client_secret_secret.value
            tenant_id = tenant_id_secret.value
            subscription_id = subscription_id_secret.value

            # Validate not empty
            if not client_secret or not client_id or not tenant_id or not subscription_id:
                raise InvalidCredentialError(
                    f"Credentials for tenant '{tenant_name}' are incomplete or empty"
                )

            # Create credential object with SecretStr wrapping
            credential = TenantCredential(
                client_id=client_id,
                client_secret=SecretStr(client_secret),
                tenant_id=tenant_id,
                subscription_id=subscription_id,
            )

            # Cache it
            self._credential_cache[tenant_name] = credential

            return credential

        except ResourceNotFoundError as e:
            raise CredentialNotFoundError(
                f"Credentials not found for tenant '{tenant_name}'. "
                f"Expected secrets with prefix '{tenant_name}-*' in Key Vault"
            ) from e
        except AzureError as e:
            raise InvalidCredentialError(
                f"Failed to retrieve credentials for tenant '{tenant_name}': {e}"
            ) from e

    async def validate_tenant_access(self, tenant_name: str) -> bool:
        """Validate that target tenant SP has required permissions.

        Performs basic validation by retrieving credentials and checking
        for completeness. In a full implementation, this would also
        verify Azure RBAC permissions.

        Args:
            tenant_name: Tenant identifier

        Returns:
            True if credentials are valid and accessible, False otherwise
        """
        try:
            # Get credential
            credential = await self.get_tenant_credential(tenant_name)

            # Basic validation: check that all fields are present and non-empty
            # In full implementation, would test actual Azure access here
            # For now, return True if credentials are retrievable and complete
            return bool(
                credential.client_id
                and credential.client_secret.get_secret_value()
                and credential.tenant_id
                and credential.subscription_id
            )

        except (CredentialNotFoundError, InvalidCredentialError):
            return False
        except Exception:
            # Any other error during validation
            return False

    async def store_tenant_credentials(
        self,
        tenant_name: str,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        subscription_id: str,
    ) -> None:
        """Store tenant credentials in Key Vault.

        Stores credentials with naming convention:
        - {tenant-name}-client-id
        - {tenant-name}-client-secret
        - {tenant-name}-tenant-id
        - {tenant-name}-subscription-id

        Args:
            tenant_name: Tenant identifier
            client_id: Service principal client ID
            client_secret: Service principal client secret
            tenant_id: Azure tenant ID
            subscription_id: Azure subscription ID
        """
        client_id_secret_name = f"{tenant_name}-client-id"
        client_secret_secret_name = f"{tenant_name}-client-secret"
        tenant_id_secret_name = f"{tenant_name}-tenant-id"
        subscription_id_secret_name = f"{tenant_name}-subscription-id"

        # Store all secrets
        self.kv_client.set_secret(client_id_secret_name, client_id)
        self.kv_client.set_secret(client_secret_secret_name, client_secret)
        self.kv_client.set_secret(tenant_id_secret_name, tenant_id)
        self.kv_client.set_secret(subscription_id_secret_name, subscription_id)

    async def rotate_credentials(self, tenant_name: str, new_client_secret: str) -> None:
        """Rotate tenant credentials in Key Vault.

        Updates the client secret for a tenant and invalidates the cache
        to force fresh retrieval on next access.

        Args:
            tenant_name: Tenant identifier
            new_client_secret: New service principal client secret
        """
        client_secret_secret_name = f"{tenant_name}-client-secret"

        # Update secret in Key Vault
        self.kv_client.set_secret(client_secret_secret_name, new_client_secret)

        # Invalidate cache
        self.invalidate_cache(tenant_name)

    def invalidate_cache(self, tenant_name: str | None = None) -> None:
        """Invalidate credential cache.

        Args:
            tenant_name: Specific tenant to invalidate, or None for all
        """
        if tenant_name:
            self._credential_cache.pop(tenant_name, None)
        else:
            self._credential_cache.clear()

    async def get_all_tenant_names(self) -> list[str]:
        """List all tenant identifiers that have credentials stored.

        Queries Key Vault for secrets matching the pattern {tenant-name}-client-id
        and extracts tenant names.

        Returns:
            Sorted list of tenant names with credentials in Key Vault
        """
        tenant_names = set()

        # List all secrets in Key Vault
        secrets = self.kv_client.list_secrets()

        for secret in secrets:
            secret_name = secret["name"]

            # Check if this is a client-id secret (our identifier for a tenant)
            if secret_name.endswith("-client-id"):
                # Extract tenant name (everything before "-client-id")
                tenant_name = secret_name[: -len("-client-id")]
                tenant_names.add(tenant_name)

        return sorted(tenant_names)
