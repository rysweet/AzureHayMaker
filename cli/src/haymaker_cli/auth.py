"""Authentication providers for HayMaker CLI."""

import os
from abc import ABC, abstractmethod
from typing import Any

from azure.identity import AzureCliCredential, DefaultAzureCredential
from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    """Authentication configuration."""

    type: str = Field(default="api_key", description="Authentication type (api_key or azure_ad)")
    api_key: str | None = Field(default=None, description="API key for api_key auth")
    tenant_id: str | None = Field(default=None, description="Tenant ID for Azure AD auth")


class AuthProvider(ABC):
    """Base authentication provider."""

    @abstractmethod
    def get_auth_header(self) -> dict[str, str]:
        """Get authentication header for HTTP requests.

        Returns:
            Dictionary with authentication header (e.g., {'x-functions-key': 'key'})
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
            Dictionary with x-functions-key header
        """
        return {"x-functions-key": self.api_key}


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
            self.credential = AzureCliCredential(tenant_id=tenant_id)
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
    2. Environment variables (HAYMAKER_API_KEY or HAYMAKER_TENANT_ID)
    3. Default to Azure AD (using Azure CLI credentials)

    Args:
        config: Authentication configuration

    Returns:
        Configured AuthProvider instance

    Raises:
        ValueError: If authentication configuration is invalid

    Example:
        >>> # API key from config
        >>> auth = create_auth_provider({"type": "api_key", "api_key": "my-key"})
        >>> auth.get_auth_header()
        {'x-functions-key': 'my-key'}

        >>> # Azure AD from environment
        >>> os.environ['HAYMAKER_TENANT_ID'] = 'tenant-123'
        >>> auth = create_auth_provider()
        >>> auth.get_auth_header()  # doctest: +SKIP
        {'Authorization': 'Bearer ...'}
    """
    # Convert dict to AuthConfig if needed
    if isinstance(config, dict):
        config = AuthConfig(**config)
    elif config is None:
        config = AuthConfig()

    # Check environment variables as fallback
    env_api_key = os.getenv("HAYMAKER_API_KEY")
    env_tenant_id = os.getenv("HAYMAKER_TENANT_ID")

    # Determine auth type and create provider
    if config.type == "api_key":
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
            "Must be 'api_key' or 'azure_ad'."
        )
