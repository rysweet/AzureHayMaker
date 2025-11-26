"""M365 Graph API client factory for Knowledge Worker agents.

Provides factory class for creating authenticated GraphServiceClient instances
using client secret credentials from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Any

from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient


@dataclass
class M365ClientConfig:
    """Configuration for M365 Graph API client authentication.

    Attributes:
        tenant_id: Azure AD tenant ID
        client_id: Application (client) ID
        client_secret: Client secret value
    """

    tenant_id: str
    client_id: str
    client_secret: str

    @classmethod
    def from_env(cls) -> "M365ClientConfig":
        """Load configuration from environment variables.

        Reads KW_TENANT_ID, KW_APP_ID, and KW_CLIENT_SECRET from environment.

        Returns:
            M365ClientConfig populated from environment

        Raises:
            ValueError: If any required environment variable is missing
        """
        tenant_id = os.environ.get("KW_TENANT_ID", "")
        client_id = os.environ.get("KW_APP_ID", "")
        client_secret = os.environ.get("KW_CLIENT_SECRET", "")

        missing = []
        if not tenant_id:
            missing.append("KW_TENANT_ID")
        if not client_id:
            missing.append("KW_APP_ID")
        if not client_secret:
            missing.append("KW_CLIENT_SECRET")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )


class M365Client:
    """Wrapper for GraphServiceClient that implements the M365Client protocol.

    The operations classes expect a client with a `graph` property that
    returns the actual GraphServiceClient for API calls.

    Example:
        >>> client = M365ClientFactory.create()
        >>> ops = EmailOperations(worker, client, validator)
        >>> await ops.send_email(to=["user@tenant.onmicrosoft.com"], ...)
    """

    def __init__(self, graph_client: GraphServiceClient) -> None:
        """Initialize M365Client wrapper.

        Args:
            graph_client: The authenticated GraphServiceClient
        """
        self._graph_client = graph_client

    @property
    def graph(self) -> Any:
        """Access to Microsoft Graph client.

        Returns:
            GraphServiceClient instance for making API calls
        """
        return self._graph_client


class M365ClientFactory:
    """Factory for creating authenticated M365 Graph API clients."""

    @staticmethod
    def create(config: M365ClientConfig | None = None) -> M365Client:
        """Create an authenticated M365Client.

        Args:
            config: Client configuration. If None, loads from environment.

        Returns:
            M365Client wrapper containing authenticated GraphServiceClient

        Raises:
            ValueError: If credentials are missing or invalid
        """
        if config is None:
            config = M365ClientConfig.from_env()

        credential = ClientSecretCredential(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_secret=config.client_secret,
        )

        graph_client = GraphServiceClient(credential)
        return M365Client(graph_client)
