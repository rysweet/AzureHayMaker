"""Tests for m365_client module.

Comprehensive unit tests for M365 Graph API client factory including:
- M365ClientConfig creation and environment loading
- M365Client wrapper functionality
- M365ClientFactory client creation
- Authentication handling
- Error responses for missing credentials
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from azure_haymaker.knowledge_worker.m365_client import (
    M365Client,
    M365ClientConfig,
    M365ClientFactory,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# UNIT TESTS - M365ClientConfig
# =============================================================================


class TestM365ClientConfig:
    """Tests for M365ClientConfig dataclass."""

    def test_config_creation(self) -> None:
        """Test basic config creation."""
        config = M365ClientConfig(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret",
        )

        assert config.tenant_id == "test-tenant-id"
        assert config.client_id == "test-client-id"
        assert config.client_secret == "test-secret"

    def test_config_secret_hidden_from_repr(self) -> None:
        """Test that client_secret is hidden in repr for security."""
        config = M365ClientConfig(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="super-secret-value",
        )

        repr_str = repr(config)

        # Secret should not appear in repr
        assert "super-secret-value" not in repr_str
        # Other fields should appear
        assert "test-tenant-id" in repr_str
        assert "test-client-id" in repr_str


# =============================================================================
# UNIT TESTS - M365ClientConfig.from_env()
# =============================================================================


class TestM365ClientConfigFromEnv:
    """Tests for loading config from environment variables."""

    def test_from_env_success(self) -> None:
        """Test successful config loading from environment."""
        env_vars = {
            "KW_TENANT_ID": "env-tenant-id",
            "KW_APP_ID": "env-app-id",
            "KW_CLIENT_SECRET": "env-secret",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = M365ClientConfig.from_env()

            assert config.tenant_id == "env-tenant-id"
            assert config.client_id == "env-app-id"
            assert config.client_secret == "env-secret"

    def test_from_env_missing_tenant_id(self) -> None:
        """Test error when KW_TENANT_ID is missing."""
        env_vars = {
            "KW_APP_ID": "env-app-id",
            "KW_CLIENT_SECRET": "env-secret",
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(ValueError, match="KW_TENANT_ID"),
        ):
            M365ClientConfig.from_env()

    def test_from_env_missing_app_id(self) -> None:
        """Test error when KW_APP_ID is missing."""
        env_vars = {
            "KW_TENANT_ID": "env-tenant-id",
            "KW_CLIENT_SECRET": "env-secret",
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(ValueError, match="KW_APP_ID"),
        ):
            M365ClientConfig.from_env()

    def test_from_env_missing_client_secret(self) -> None:
        """Test error when KW_CLIENT_SECRET is missing."""
        env_vars = {
            "KW_TENANT_ID": "env-tenant-id",
            "KW_APP_ID": "env-app-id",
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(ValueError, match="KW_CLIENT_SECRET"),
        ):
            M365ClientConfig.from_env()

    def test_from_env_multiple_missing(self) -> None:
        """Test error lists all missing variables."""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="Missing required environment variables"),
        ):
            M365ClientConfig.from_env()

    def test_from_env_empty_values_treated_as_missing(self) -> None:
        """Test empty string values are treated as missing."""
        env_vars = {
            "KW_TENANT_ID": "",  # Empty
            "KW_APP_ID": "env-app-id",
            "KW_CLIENT_SECRET": "env-secret",
        }

        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(ValueError, match="KW_TENANT_ID"),
        ):
            M365ClientConfig.from_env()


# =============================================================================
# UNIT TESTS - M365Client Wrapper
# =============================================================================


class TestM365Client:
    """Tests for M365Client wrapper class."""

    def test_client_creation(self) -> None:
        """Test M365Client wrapper creation."""
        mock_graph_client = MagicMock()

        client = M365Client(graph_client=mock_graph_client)

        assert client._graph_client is mock_graph_client

    def test_graph_property(self) -> None:
        """Test graph property returns underlying client."""
        mock_graph_client = MagicMock()
        mock_graph_client.users = MagicMock()

        client = M365Client(graph_client=mock_graph_client)

        assert client.graph is mock_graph_client
        assert client.graph.users is mock_graph_client.users

    def test_graph_property_access_multiple_times(self) -> None:
        """Test graph property returns same instance."""
        mock_graph_client = MagicMock()

        client = M365Client(graph_client=mock_graph_client)

        # Multiple accesses should return same object
        assert client.graph is client.graph
        assert id(client.graph) == id(mock_graph_client)


# =============================================================================
# UNIT TESTS - M365ClientFactory
# =============================================================================


class TestM365ClientFactory:
    """Tests for M365ClientFactory."""

    @patch("azure_haymaker.knowledge_worker.m365_client.GraphServiceClient")
    @patch("azure_haymaker.knowledge_worker.m365_client.ClientSecretCredential")
    def test_create_with_config(
        self,
        mock_credential_class: MagicMock,
        mock_graph_client_class: MagicMock,
    ) -> None:
        """Test factory creates client with provided config."""
        mock_credential = MagicMock()
        mock_credential_class.return_value = mock_credential

        mock_graph_client = MagicMock()
        mock_graph_client_class.return_value = mock_graph_client

        config = M365ClientConfig(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        client = M365ClientFactory.create(config=config)

        # Verify credential was created with correct params
        mock_credential_class.assert_called_once_with(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        # Verify GraphServiceClient was created with credential and scopes
        mock_graph_client_class.assert_called_once_with(
            mock_credential,
            scopes=["https://graph.microsoft.com/.default"],
        )

        # Verify returned client wraps the graph client
        assert isinstance(client, M365Client)
        assert client.graph is mock_graph_client

    @patch("azure_haymaker.knowledge_worker.m365_client.GraphServiceClient")
    @patch("azure_haymaker.knowledge_worker.m365_client.ClientSecretCredential")
    @patch("azure_haymaker.knowledge_worker.m365_client.M365ClientConfig.from_env")
    def test_create_without_config_uses_env(
        self,
        mock_from_env: MagicMock,
        mock_credential_class: MagicMock,
        mock_graph_client_class: MagicMock,
    ) -> None:
        """Test factory loads config from env when not provided."""
        mock_from_env.return_value = M365ClientConfig(
            tenant_id="env-tenant",
            client_id="env-client",
            client_secret="env-secret",
        )
        mock_credential = MagicMock()
        mock_credential_class.return_value = mock_credential
        mock_graph_client = MagicMock()
        mock_graph_client_class.return_value = mock_graph_client

        M365ClientFactory.create()

        mock_from_env.assert_called_once()
        mock_credential_class.assert_called_once_with(
            tenant_id="env-tenant",
            client_id="env-client",
            client_secret="env-secret",
        )

    @patch("azure_haymaker.knowledge_worker.m365_client.M365ClientConfig.from_env")
    def test_create_propagates_config_error(
        self,
        mock_from_env: MagicMock,
    ) -> None:
        """Test factory propagates config loading errors."""
        mock_from_env.side_effect = ValueError("Missing KW_TENANT_ID")

        with pytest.raises(ValueError, match="Missing KW_TENANT_ID"):
            M365ClientFactory.create()

    @patch("azure_haymaker.knowledge_worker.m365_client.GraphServiceClient")
    @patch("azure_haymaker.knowledge_worker.m365_client.ClientSecretCredential")
    def test_create_uses_default_scopes(
        self,
        mock_credential_class: MagicMock,
        mock_graph_client_class: MagicMock,
    ) -> None:
        """Test factory uses correct Graph API scopes."""
        mock_credential = MagicMock()
        mock_credential_class.return_value = mock_credential
        mock_graph_client = MagicMock()
        mock_graph_client_class.return_value = mock_graph_client

        config = M365ClientConfig(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        M365ClientFactory.create(config=config)

        # Verify correct scope is used
        call_kwargs = mock_graph_client_class.call_args[1]
        assert call_kwargs["scopes"] == ["https://graph.microsoft.com/.default"]


# =============================================================================
# INTEGRATION TESTS - Full Flow
# =============================================================================


class TestM365ClientIntegration:
    """Integration tests for M365 client creation flow."""

    @patch("azure_haymaker.knowledge_worker.m365_client.GraphServiceClient")
    @patch("azure_haymaker.knowledge_worker.m365_client.ClientSecretCredential")
    def test_full_client_creation_flow(
        self,
        mock_credential_class: MagicMock,
        mock_graph_client_class: MagicMock,
    ) -> None:
        """Test complete client creation and usage flow."""
        # Setup mocks
        mock_credential = MagicMock()
        mock_credential_class.return_value = mock_credential

        mock_users = MagicMock()
        mock_graph_client = MagicMock()
        mock_graph_client.users = mock_users
        mock_graph_client_class.return_value = mock_graph_client

        # Create config
        config = M365ClientConfig(
            tenant_id="integration-tenant",
            client_id="integration-client",
            client_secret="integration-secret",
        )

        # Create client
        client = M365ClientFactory.create(config=config)

        # Verify client is properly configured
        assert isinstance(client, M365Client)
        assert client.graph is mock_graph_client
        assert client.graph.users is mock_users

        # Verify correct authentication was configured
        mock_credential_class.assert_called_once_with(
            tenant_id="integration-tenant",
            client_id="integration-client",
            client_secret="integration-secret",
        )

    def test_config_from_env_with_factory_integration(self) -> None:
        """Test complete flow from environment to client."""
        env_vars = {
            "KW_TENANT_ID": "env-integration-tenant",
            "KW_APP_ID": "env-integration-client",
            "KW_CLIENT_SECRET": "env-integration-secret",
        }

        with (
            patch.dict(os.environ, env_vars, clear=False),
            patch("azure_haymaker.knowledge_worker.m365_client.GraphServiceClient") as mock_graph,
            patch(
                "azure_haymaker.knowledge_worker.m365_client.ClientSecretCredential"
            ) as mock_cred,
        ):
            mock_cred.return_value = MagicMock()
            mock_graph.return_value = MagicMock()

            # Create client using environment variables
            client = M365ClientFactory.create()

            assert isinstance(client, M365Client)
            mock_cred.assert_called_once_with(
                tenant_id="env-integration-tenant",
                client_id="env-integration-client",
                client_secret="env-integration-secret",
            )


# =============================================================================
# UNIT TESTS - Error Handling
# =============================================================================


class TestM365ClientErrorHandling:
    """Tests for error handling scenarios."""

    @patch("azure_haymaker.knowledge_worker.m365_client.ClientSecretCredential")
    def test_credential_creation_error(
        self,
        mock_credential_class: MagicMock,
    ) -> None:
        """Test handling of credential creation errors."""
        mock_credential_class.side_effect = Exception("Invalid credentials")

        config = M365ClientConfig(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="invalid-secret",
        )

        with pytest.raises(Exception, match="Invalid credentials"):
            M365ClientFactory.create(config=config)

    @patch("azure_haymaker.knowledge_worker.m365_client.GraphServiceClient")
    @patch("azure_haymaker.knowledge_worker.m365_client.ClientSecretCredential")
    def test_graph_client_creation_error(
        self,
        mock_credential_class: MagicMock,
        mock_graph_client_class: MagicMock,
    ) -> None:
        """Test handling of Graph client creation errors."""
        mock_credential = MagicMock()
        mock_credential_class.return_value = mock_credential
        mock_graph_client_class.side_effect = Exception("Failed to create client")

        config = M365ClientConfig(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
        )

        with pytest.raises(Exception, match="Failed to create client"):
            M365ClientFactory.create(config=config)


# =============================================================================
# UNIT TESTS - Security Considerations
# =============================================================================


class TestM365ClientSecurity:
    """Tests for security-related behavior."""

    def test_config_secret_not_in_string(self) -> None:
        """Test client_secret doesn't appear in string representations."""
        config = M365ClientConfig(
            tenant_id="tenant-123",
            client_id="client-456",
            client_secret="my-super-secret-key",
        )

        # Convert to various string representations
        str_repr = str(config)
        repr_str = repr(config)

        # Secret should never appear
        assert "my-super-secret-key" not in str_repr
        assert "my-super-secret-key" not in repr_str

    @patch("azure_haymaker.knowledge_worker.m365_client.GraphServiceClient")
    @patch("azure_haymaker.knowledge_worker.m365_client.ClientSecretCredential")
    def test_secret_not_stored_in_client(
        self,
        mock_credential_class: MagicMock,
        mock_graph_client_class: MagicMock,
    ) -> None:
        """Test client doesn't expose the secret after creation."""
        mock_credential = MagicMock()
        mock_credential_class.return_value = mock_credential
        mock_graph_client = MagicMock()
        mock_graph_client_class.return_value = mock_graph_client

        config = M365ClientConfig(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="sensitive-secret",
        )

        client = M365ClientFactory.create(config=config)

        # Client should not have direct access to secret
        assert not hasattr(client, "client_secret")
        assert not hasattr(client, "_client_secret")

        # Check string representation doesn't leak
        client_str = str(client)
        assert "sensitive-secret" not in client_str
