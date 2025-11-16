"""Unit tests for configuration models."""

import pytest
from pydantic import ValidationError

from azure_haymaker.models.config import (
    CosmosDBConfig,
    LogAnalyticsConfig,
    OrchestratorConfig,
    SimulationSize,
    StorageConfig,
    TableStorageConfig,
)


class TestSimulationSize:
    """Tests for SimulationSize enum."""

    def test_simulation_size_values(self) -> None:
        """Test that simulation size enum has expected values."""
        assert SimulationSize.SMALL == "small"
        assert SimulationSize.MEDIUM == "medium"
        assert SimulationSize.LARGE == "large"

    def test_scenario_count_mapping(self) -> None:
        """Test scenario count calculation for each simulation size."""
        assert SimulationSize.SMALL.scenario_count() == 5
        assert SimulationSize.MEDIUM.scenario_count() == 15
        assert SimulationSize.LARGE.scenario_count() == 30


class TestStorageConfig:
    """Tests for storage configuration models."""

    def test_storage_config_valid(self) -> None:
        """Test valid storage configuration."""
        config = StorageConfig(
            account_name="haymakerstorage",
            container_logs="execution-logs",
            container_state="execution-state",
            container_reports="execution-reports",
            container_scenarios="scenarios",
        )
        assert config.account_name == "haymakerstorage"
        assert config.container_logs == "execution-logs"

    def test_storage_config_account_url(self) -> None:
        """Test account URL generation."""
        config = StorageConfig(
            account_name="haymakerstorage",
            container_logs="execution-logs",
            container_state="execution-state",
            container_reports="execution-reports",
            container_scenarios="scenarios",
        )
        assert config.account_url == "https://haymakerstorage.blob.core.windows.net"

    def test_table_storage_config_valid(self) -> None:
        """Test valid Table Storage configuration."""
        config = TableStorageConfig(
            account_name="haymakertables",
            table_execution_runs="ExecutionRuns",
            table_scenario_status="ScenarioStatus",
            table_resource_inventory="ResourceInventory",
        )
        assert config.account_name == "haymakertables"
        assert config.table_execution_runs == "ExecutionRuns"

    def test_cosmosdb_config_valid(self) -> None:
        """Test valid Cosmos DB configuration."""
        config = CosmosDBConfig(
            endpoint="https://haymakerdb.documents.azure.com:443/",
            database_name="haymaker",
            container_metrics="metrics",
        )
        assert config.endpoint == "https://haymakerdb.documents.azure.com:443/"
        assert config.database_name == "haymaker"


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig model."""

    def test_config_valid_minimal(self) -> None:
        """Test valid configuration with minimal required fields."""
        config = OrchestratorConfig(
            target_tenant_id="12345678-1234-1234-1234-123456789012",
            target_subscription_id="87654321-4321-4321-4321-210987654321",
            main_sp_client_id="11111111-1111-1111-1111-111111111111",
            vnet_integration_enabled=False,  # Disable VNet for unit test
            main_sp_client_secret="super-secret-value",
            anthropic_api_key="sk-ant-test-key",
            service_bus_namespace="haymaker-sb",
            container_registry="haymaker.azurecr.io",
            container_image="haymaker-agent:latest",
            key_vault_url="https://haymaker-kv.vault.azure.net",
            simulation_size=SimulationSize.SMALL,
            storage=StorageConfig(
                account_name="haymakerstorage",
                container_logs="execution-logs",
                container_state="execution-state",
                container_reports="execution-reports",
                container_scenarios="scenarios",
            ),
            table_storage=TableStorageConfig(
                account_name="haymakertables",
                table_execution_runs="ExecutionRuns",
                table_scenario_status="ScenarioStatus",
                table_resource_inventory="ResourceInventory",
            ),
            cosmosdb=CosmosDBConfig(
                endpoint="https://haymakerdb.documents.azure.com:443/",
                database_name="haymaker",
                container_metrics="metrics",
            ),
            log_analytics=LogAnalyticsConfig(
                workspace_id="12345678-1234-1234-1234-123456789012",
                workspace_key="workspace-key-value",
            ),
        )

        assert config.target_tenant_id == "12345678-1234-1234-1234-123456789012"
        assert config.simulation_size == SimulationSize.SMALL

    def test_config_scenario_count_property(self) -> None:
        """Test scenario count property calculation."""
        config = OrchestratorConfig(
            target_tenant_id="12345678-1234-1234-1234-123456789012",
            target_subscription_id="87654321-4321-4321-4321-210987654321",
            main_sp_client_id="11111111-1111-1111-1111-111111111111",
            vnet_integration_enabled=False,  # Disable VNet for unit test
            main_sp_client_secret="super-secret-value",
            anthropic_api_key="sk-ant-test-key",
            service_bus_namespace="haymaker-sb",
            container_registry="haymaker.azurecr.io",
            container_image="haymaker-agent:latest",
            key_vault_url="https://haymaker-kv.vault.azure.net",
            simulation_size=SimulationSize.MEDIUM,
            storage=StorageConfig(
                account_name="haymakerstorage",
                container_logs="execution-logs",
                container_state="execution-state",
                container_reports="execution-reports",
                container_scenarios="scenarios",
            ),
            table_storage=TableStorageConfig(
                account_name="haymakertables",
                table_execution_runs="ExecutionRuns",
                table_scenario_status="ScenarioStatus",
                table_resource_inventory="ResourceInventory",
            ),
            cosmosdb=CosmosDBConfig(
                endpoint="https://haymakerdb.documents.azure.com:443/",
                database_name="haymaker",
                container_metrics="metrics",
            ),
            log_analytics=LogAnalyticsConfig(
                workspace_id="12345678-1234-1234-1234-123456789012",
                workspace_key="workspace-key-value",
            ),
        )

        assert config.scenario_count == 15

    def test_config_missing_required_fields(self) -> None:
        """Test that configuration requires all mandatory fields."""
        with pytest.raises(ValidationError) as exc_info:
            OrchestratorConfig()  # type: ignore

        errors = exc_info.value.errors()
        required_fields = {
            "target_tenant_id",
            "target_subscription_id",
            "main_sp_client_id",
            "main_sp_client_secret",
            "anthropic_api_key",
            "service_bus_namespace",
            "container_registry",
            "container_image",
            "key_vault_url",
            "simulation_size",
            "storage",
            "table_storage",
            "cosmosdb",
            "log_analytics",
        }

        error_fields = {err["loc"][0] for err in errors}
        assert required_fields.issubset(error_fields)

    def test_config_scrub_secrets(self) -> None:
        """Test that secrets are scrubbed from string representation."""
        config = OrchestratorConfig(
            target_tenant_id="12345678-1234-1234-1234-123456789012",
            target_subscription_id="87654321-4321-4321-4321-210987654321",
            main_sp_client_id="11111111-1111-1111-1111-111111111111",
            vnet_integration_enabled=False,  # Disable VNet for unit test
            main_sp_client_secret="super-secret-value",
            anthropic_api_key="sk-ant-test-key",
            service_bus_namespace="haymaker-sb",
            container_registry="haymaker.azurecr.io",
            container_image="haymaker-agent:latest",
            key_vault_url="https://haymaker-kv.vault.azure.net",
            simulation_size=SimulationSize.SMALL,
            storage=StorageConfig(
                account_name="haymakerstorage",
                container_logs="execution-logs",
                container_state="execution-state",
                container_reports="execution-reports",
                container_scenarios="scenarios",
            ),
            table_storage=TableStorageConfig(
                account_name="haymakertables",
                table_execution_runs="ExecutionRuns",
                table_scenario_status="ScenarioStatus",
                table_resource_inventory="ResourceInventory",
            ),
            cosmosdb=CosmosDBConfig(
                endpoint="https://haymakerdb.documents.azure.com:443/",
                database_name="haymaker",
                container_metrics="metrics",
            ),
            log_analytics=LogAnalyticsConfig(
                workspace_id="12345678-1234-1234-1234-123456789012",
                workspace_key="workspace-key-value",
            ),
        )

        config_str = str(config)
        config_repr = repr(config)

        # Secrets should not appear in string representations
        assert "super-secret-value" not in config_str
        assert "sk-ant-test-key" not in config_str
        assert "workspace-key-value" not in config_str

        assert "super-secret-value" not in config_repr
        assert "sk-ant-test-key" not in config_repr
        assert "workspace-key-value" not in config_repr

        # But should contain redacted placeholders
        assert "***REDACTED***" in config_str or "SecretStr" in config_str
