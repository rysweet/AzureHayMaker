"""Authentication providers for HayMaker CLI."""

import os
from abc import ABC, abstractmethod
from typing import Any

from azure.identity import (
    AzureCliCredential,
    ClientSecretCredential,
    DefaultAzureCredential,
)
from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    """Authentication configuration."""

    type: str = Field(
        default="service_principal",
        description="Authentication type (service_principal, azure_ad, or api_key)",
    )
    api_key: str | None = Field(default=None, description="API key for api_key auth")
    tenant_id: str | None = Field(default=None, description="Tenant ID for Azure AD auth")
    client_id: str | None = Field(default=None, description="Client ID for service principal")
    client_secret: str | None = Field(
        default=None, description="Client secret for service principal"
    )


class AuthProvider(ABC):
    """Base authentication provider."""

    @abstractmethod
    def get_auth_header(self) -> dict[str, str]:
        """Get authentication header for HTTP requests.

        Returns:
            Dictionary with authentication header (e.g., {'Authorization': 'Bearer ...'})
        """


class ApiKeyAuthProvider(AuthProvider):
    """API key authentication provider."""

    def __init__(self, api_key: str):
        """Initialize API key auth provider.

        Args:
            api_key: API key for authentication
        """
        self.api_key = api_key

    def get_auth_header(self) -> dict[str, str]:
        """Get authentication header with API key.

        Returns:
            Dictionary with x-api-key header
        """
        return {"x-api-key": self.api_key}


class ServicePrincipalAuthProvider(AuthProvider):
    """Service Principal authentication provider using client credentials.

    This is the recommended auth method for CLI and automation scenarios.
    Uses the same service principal configured in .env for the orchestrator.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
    ):
        """Initialize service principal auth provider.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Service principal client/application ID
            client_secret: Service principal client secret
            scope: Optional OAuth scope (default: https://management.azure.com/.default)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.scope = scope or "https://management.azure.com/.default"

        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    def get_auth_header(self) -> dict[str, str]:
        """Get authentication header with Azure AD token.

        Returns:
            Dictionary with Authorization Bearer token header
        """
        token = self.credential.get_token(self.scope)
        return {"Authorization": f"Bearer {token.token}"}


class AzureADAuthProvider(AuthProvider):
    """Azure AD authentication provider using Azure CLI credentials."""

    def __init__(self, tenant_id: str | None = None, scope: str | None = None):
        """Initialize Azure AD auth provider.

        Args:
            tenant_id: Optional Azure AD tenant ID
            scope: Optional OAuth scope (default: https://management.azure.com/.default)
        """
        self.tenant_id = tenant_id
        self.scope = scope or "https://management.azure.com/.default"

        # Try to use Azure CLI credential first, fallback to default credential
        try:
            if tenant_id:
                self.credential = AzureCliCredential(tenant_id=tenant_id)
            else:
                self.credential = AzureCliCredential()
        except Exception:
            self.credential = DefaultAzureCredential(
                exclude_managed_identity_credential=True,
                exclude_shared_token_cache_credential=False,
            )

    def get_auth_header(self) -> dict[str, str]:
        """Get authentication header with Azure AD token.

        Returns:
            Dictionary with Authorization Bearer token header
        """
        token = self.credential.get_token(self.scope)
        return {"Authorization": f"Bearer {token.token}"}


def create_auth_provider(config: AuthConfig | dict[str, Any] | None = None) -> AuthProvider:
    """Create authentication provider from configuration.

    Priority order:
    1. Explicit config parameter
    2. Environment variables (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
    3. Fall back to Azure CLI credentials

    Args:
        config: Authentication configuration

    Returns:
        Configured AuthProvider instance

    Raises:
        ValueError: If authentication configuration is invalid

    Example:
        >>> # Service principal from environment (.env)
        >>> # AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET must be set
        >>> auth = create_auth_provider()
        >>> auth.get_auth_header()  # doctest: +SKIP
        {'Authorization': 'Bearer ...'}

        >>> # Explicit service principal config
        >>> auth = create_auth_provider({
        ...     "type": "service_principal",
        ...     "tenant_id": "...",
        ...     "client_id": "...",
        ...     "client_secret": "..."
        ... })
    """
    # Convert dict to AuthConfig if needed
    if isinstance(config, dict):
        config = AuthConfig(**config)
    elif config is None:
        config = AuthConfig()

    # Check environment variables for service principal (preferred)
    env_tenant_id = os.getenv("AZURE_TENANT_ID")
    env_client_id = os.getenv("AZURE_CLIENT_ID")
    env_client_secret = os.getenv("AZURE_CLIENT_SECRET") or os.getenv("MAIN_SP_CLIENT_SECRET")
    env_api_key = os.getenv("HAYMAKER_API_KEY")

    # Auto-detect auth type based on available credentials
    if config.type == "service_principal" or (
        config.type != "api_key" and env_tenant_id and env_client_id and env_client_secret
    ):
        # Use service principal auth
        tenant_id = config.tenant_id or env_tenant_id
        client_id = config.client_id or env_client_id
        client_secret = config.client_secret or env_client_secret

        if not all([tenant_id, client_id, client_secret]):
            raise ValueError(
                "Service principal authentication requires AZURE_TENANT_ID, "
                "AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET (or MAIN_SP_CLIENT_SECRET) "
                "environment variables, or explicit configuration."
            )

        # Type guard: after the check above, we know these are non-None
        assert tenant_id is not None
        assert client_id is not None
        assert client_secret is not None

        # Use the API scope for the orchestrator API
        api_scope = f"api://{client_id}/.default"
        return ServicePrincipalAuthProvider(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            scope=api_scope,
        )

    elif config.type == "api_key":
        api_key = config.api_key or env_api_key
        if not api_key:
            raise ValueError(
                "API key authentication selected but no API key provided. "
                "Set HAYMAKER_API_KEY environment variable or provide api_key in config."
            )
        return ApiKeyAuthProvider(api_key=api_key)

    elif config.type == "azure_ad":
        tenant_id = config.tenant_id or env_tenant_id
        return AzureADAuthProvider(tenant_id=tenant_id)

    else:
        raise ValueError(
            f"Unknown authentication type: {config.type}. "
            "Must be 'service_principal', 'azure_ad', or 'api_key'."
        )
