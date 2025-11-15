"""Unit tests for configuration loading."""

import os
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.keyvault.secrets import SecretClient
from pydantic import SecretStr

from azure_haymaker.models.config import (
    OrchestratorConfig,
    SimulationSize,
)
from azure_haymaker.orchestrator.config import (
    ConfigurationError,
    load_config,
    load_config_from_env_and_keyvault,
)


class TestLoadConfigFromEnvAndKeyvault:
    """Tests for loading configuration from environment and Key Vault."""

    @pytest.fixture
    def mock_env(self) -> dict[str, str]:
        """Mock environment variables."""
        return {
            "AZURE_TENANT_ID": "12345678-1234-1234-1234-123456789012",
            "AZURE_SUBSCRIPTION_ID": "87654321-4321-4321-4321-210987654321",
            "AZURE_CLIENT_ID": "11111111-1111-1111-1111-111111111111",
            "KEY_VAULT_URL": "https://haymaker-kv.vault.azure.net",
            "SERVICE_BUS_NAMESPACE": "haymaker-sb",
            "CONTAINER_REGISTRY": "haymaker.azurecr.io",
            "CONTAINER_IMAGE": "haymaker-agent:latest",
            "SIMULATION_SIZE": "small",
            "STORAGE_ACCOUNT_NAME": "haymakerstorage",
            "TABLE_STORAGE_ACCOUNT_NAME": "haymakertables",
            "COSMOSDB_ENDPOINT": "https://haymakerdb.documents.azure.com:443/",
            "COSMOSDB_DATABASE": "haymaker",
            "LOG_ANALYTICS_WORKSPACE_ID": "12345678-1234-1234-1234-123456789012",
        }

    @pytest.fixture
    def mock_keyvault_client(self) -> MagicMock:
        """Mock Key Vault client."""
        client = MagicMock(spec=SecretClient)

        # Mock secret responses
        def get_secret(name: str) -> MagicMock:
            secret = MagicMock()
            if name == "main-sp-client-secret":
                secret.value = "super-secret-value"
            elif name == "anthropic-api-key":
                secret.value = "sk-ant-test-key"
            elif name == "log-analytics-workspace-key":
                secret.value = "workspace-key-value"
            else:
                raise ResourceNotFoundError(f"Secret {name} not found")
            return secret

        client.get_secret.side_effect = get_secret
        return client

    @pytest.mark.asyncio
    async def test_load_config_success(
        self, mock_env: dict[str, str], mock_keyvault_client: MagicMock
    ) -> None:
        """Test successful configuration loading."""
        with (
            patch.dict(os.environ, mock_env, clear=True),
            patch(
                "azure_haymaker.orchestrator.config.SecretClient",
                return_value=mock_keyvault_client,
            ),
        ):
            config = await load_config_from_env_and_keyvault()

            assert config.target_tenant_id == "12345678-1234-1234-1234-123456789012"
            assert config.main_sp_client_id == "11111111-1111-1111-1111-111111111111"
            assert config.simulation_size == SimulationSize.SMALL
            assert config.storage.account_name == "haymakerstorage"
            assert config.scenario_count == 5

            # Verify secrets are SecretStr
            assert isinstance(config.main_sp_client_secret, SecretStr)
            assert isinstance(config.anthropic_api_key, SecretStr)

    @pytest.mark.asyncio
    async def test_load_config_missing_env_var(self, mock_keyvault_client: MagicMock) -> None:
        """Test configuration loading fails with missing environment variable."""
        env_without_tenant = {
            "AZURE_SUBSCRIPTION_ID": "87654321-4321-4321-4321-210987654321",
            "KEY_VAULT_URL": "https://haymaker-kv.vault.azure.net",
        }

        with (
            patch.dict(os.environ, env_without_tenant, clear=True),
            patch(
                "azure_haymaker.orchestrator.config.SecretClient",
                return_value=mock_keyvault_client,
            ),
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                await load_config_from_env_and_keyvault()

            assert "AZURE_TENANT_ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_config_missing_keyvault_secret(self, mock_env: dict[str, str]) -> None:
        """Test configuration loading fails with missing Key Vault secret."""
        mock_client = MagicMock(spec=SecretClient)
        mock_client.get_secret.side_effect = ResourceNotFoundError("Secret not found")

        with patch.dict(os.environ, mock_env, clear=True):
            with patch("azure_haymaker.orchestrator.config.SecretClient", return_value=mock_client):
                with pytest.raises(ConfigurationError) as exc_info:
                    await load_config_from_env_and_keyvault()

                assert "Key Vault" in str(exc_info.value) or "secret" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_load_config_invalid_simulation_size(
        self, mock_env: dict[str, str], mock_keyvault_client: MagicMock
    ) -> None:
        """Test configuration loading fails with invalid simulation size."""
        invalid_env = {**mock_env, "SIMULATION_SIZE": "extra-large"}

        with (
            patch.dict(os.environ, invalid_env, clear=True),
            patch(
                "azure_haymaker.orchestrator.config.SecretClient",
                return_value=mock_keyvault_client,
            ),
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                await load_config_from_env_and_keyvault()

            assert "simulation" in str(exc_info.value).lower()


class TestLoadConfig:
    """Tests for the convenience load_config function."""

    @pytest.mark.asyncio
    async def test_load_config_delegates_to_env_and_keyvault(self) -> None:
        """Test that load_config delegates to load_config_from_env_and_keyvault."""
        mock_config = MagicMock(spec=OrchestratorConfig)

        with patch(
            "azure_haymaker.orchestrator.config.load_config_from_env_and_keyvault",
            return_value=mock_config,
        ):
            result = await load_config()
            assert result == mock_config
