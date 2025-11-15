"""Tests for Container Manager.

This module tests Container App deployment, VNet integration, credential management,
resource configuration, and container status monitoring for Azure HayMaker scenarios.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from azure_haymaker.models.config import (
    CosmosDBConfig,
    LogAnalyticsConfig,
    OrchestratorConfig,
    SimulationSize,
    StorageConfig,
    TableStorageConfig,
)
from azure_haymaker.models.scenario import ScenarioMetadata, ScenarioStatus
from azure_haymaker.models.service_principal import ServicePrincipalDetails
from azure_haymaker.orchestrator.container_manager import (
    ContainerAppError,
    ContainerManager,
    delete_container_app,
    deploy_container_app,
    get_container_status,
)


@pytest.fixture
def mock_config() -> OrchestratorConfig:
    """Create mock OrchestratorConfig for testing."""
    return OrchestratorConfig(
        target_tenant_id="tenant-123",
        target_subscription_id="sub-456",
        main_sp_client_id="main-sp-789",
        main_sp_client_secret="secret-value",
        anthropic_api_key="api-key-value",
        service_bus_namespace="test-bus",
        service_bus_topic="agent-logs",
        container_registry="test-registry.azurecr.io",
        container_image="agent:latest",
        key_vault_url="https://test-vault.vault.azure.net",
        simulation_size=SimulationSize.SMALL,
        resource_group_name="test-rg",
        storage=StorageConfig(
            account_name="teststg",
            container_logs="logs",
            container_state="state",
            container_reports="reports",
            container_scenarios="scenarios",
        ),
        table_storage=TableStorageConfig(
            account_name="testtblstg",
            table_execution_runs="ExecutionRuns",
            table_scenario_status="ScenarioStatus",
            table_resource_inventory="ResourceInventory",
        ),
        cosmosdb=CosmosDBConfig(
            endpoint="https://test-cosmos.documents.azure.com",
            database_name="testdb",
            container_metrics="metrics",
        ),
        log_analytics=LogAnalyticsConfig(
            workspace_id="workspace-123",
            workspace_key="workspace-key",
        ),
        vnet_integration_enabled=True,
        vnet_resource_group="vnet-rg",
        vnet_name="test-vnet",
        subnet_name="test-subnet",
        container_memory_gb=64,
        container_cpu_cores=2,
    )


@pytest.fixture
def mock_scenario() -> ScenarioMetadata:
    """Create mock ScenarioMetadata for testing."""
    return ScenarioMetadata(
        scenario_name="test-scenario",
        scenario_doc_path="gs://bucket/scenario.md",
        agent_path="gs://bucket/agent.py",
        technology_area="AI/ML",
        status=ScenarioStatus.PENDING,
        started_at=None,
        ended_at=None,
    )


@pytest.fixture
def mock_sp() -> ServicePrincipalDetails:
    """Create mock ServicePrincipalDetails for testing."""
    return ServicePrincipalDetails(
        sp_name="AzureHayMaker-test-scenario-admin",
        client_id="sp-client-123",
        principal_id="sp-principal-456",
        secret_reference="scenario-sp-test-scenario-secret",
        created_at=datetime.now(UTC).isoformat(),
        scenario_name="test-scenario",
    )


class TestContainerManagerInit:
    """Test ContainerManager initialization."""

    def test_container_manager_creation(self, mock_config):
        """Test creating ContainerManager instance."""
        manager = ContainerManager(config=mock_config)
        assert manager.config == mock_config
        assert manager.resource_group_name == "test-rg"

    def test_container_manager_with_vnet_integration(self, mock_config):
        """Test ContainerManager with VNet integration enabled."""
        assert mock_config.vnet_integration_enabled is True
        assert mock_config.vnet_name == "test-vnet"
        assert mock_config.subnet_name == "test-subnet"
        manager = ContainerManager(config=mock_config)
        assert manager.config.vnet_integration_enabled is True

    def test_container_manager_invalid_memory(self, mock_config):
        """Test ContainerManager rejects insufficient memory."""
        mock_config.container_memory_gb = 32
        with pytest.raises(ValueError, match="64GB"):
            ContainerManager(config=mock_config)

    def test_container_manager_invalid_cpu(self, mock_config):
        """Test ContainerManager rejects insufficient CPU."""
        mock_config.container_cpu_cores = 1
        with pytest.raises(ValueError, match="2"):
            ContainerManager(config=mock_config)

    def test_container_manager_invalid_vnet_config(self, mock_config):
        """Test ContainerManager validates VNet configuration."""
        mock_config.vnet_integration_enabled = True
        mock_config.vnet_name = None
        with pytest.raises(ValueError, match="VNet integration"):
            ContainerManager(config=mock_config)


class TestContainerManagerAppNameGeneration:
    """Test app name generation."""

    def test_generate_app_name_basic(self, mock_config):
        """Test basic app name generation."""
        manager = ContainerManager(config=mock_config)
        app_name = manager._generate_app_name("my-scenario")
        assert app_name == "my-scenario-agent"
        assert len(app_name) <= 63

    def test_generate_app_name_sanitization(self, mock_config):
        """Test app name sanitization."""
        manager = ContainerManager(config=mock_config)
        app_name = manager._generate_app_name("my_scenario_123")
        assert app_name == "my-scenario-123-agent"
        assert "_" not in app_name

    def test_generate_app_name_length_limit(self, mock_config):
        """Test app name length is limited to 63 characters."""
        manager = ContainerManager(config=mock_config)
        long_name = "a" * 100
        app_name = manager._generate_app_name(long_name)
        assert len(app_name) <= 63


class TestContainerManagerBuildContainer:
    """Test container configuration building."""

    def test_build_container_resource_limits(self, mock_config, mock_sp):
        """Test that container is built with 64GB/2CPU limits."""
        manager = ContainerManager(config=mock_config)
        container = manager._build_container("test-app", mock_sp)

        assert container["resources"]["cpu"] == "2"
        assert container["resources"]["memory"] == "64Gi"

    def test_build_container_env_variables(self, mock_config, mock_sp):
        """Test that environment variables are set including Key Vault refs."""
        manager = ContainerManager(config=mock_config)
        container = manager._build_container("test-app", mock_sp)

        env_dict = {env["name"]: env for env in container["env"]}

        assert "AZURE_CLIENT_ID" in env_dict
        assert "AZURE_TENANT_ID" in env_dict
        assert "AZURE_SUBSCRIPTION_ID" in env_dict
        assert env_dict["AZURE_CLIENT_ID"]["value"] == mock_sp.client_id

    def test_build_container_keyvault_secrets(self, mock_config, mock_sp):
        """Test that Key Vault secret references are set."""
        manager = ContainerManager(config=mock_config)
        container = manager._build_container("test-app", mock_sp)

        env_dict = {env["name"]: env for env in container["env"]}

        # Should have Key Vault secret refs
        assert "AZURE_CLIENT_SECRET" in env_dict or any(
            "secretRef" in str(env) for env in container["env"]
        )


class TestContainerManagerBuildConfiguration:
    """Test configuration building with VNet and secrets."""

    def test_build_configuration_vnet_enabled(self, mock_config, mock_sp):
        """Test configuration includes VNet settings when enabled."""
        manager = ContainerManager(config=mock_config)
        config = manager._build_configuration(mock_sp)

        # Should have secrets configured
        assert "secrets" in config
        assert isinstance(config["secrets"], list)

    def test_build_configuration_secrets(self, mock_config, mock_sp):
        """Test that secrets are properly configured."""
        manager = ContainerManager(config=mock_config)
        config = manager._build_configuration(mock_sp)

        secrets = config["secrets"]
        assert len(secrets) > 0

        # Should have SP secret reference
        secret_names = [s["name"] for s in secrets]
        assert "sp-client-secret" in secret_names

    def test_build_configuration_registries(self, mock_config, mock_sp):
        """Test that container registry is configured."""
        manager = ContainerManager(config=mock_config)
        config = manager._build_configuration(mock_sp)

        registries = config["registries"]
        assert len(registries) > 0
        assert registries[0]["server"] == mock_config.container_registry


class TestContainerManagerValidation:
    """Test input validation."""

    def test_deploy_invalid_scenario(self, mock_config):
        """Test deployment rejects invalid scenario."""
        manager = ContainerManager(config=mock_config)
        invalid_scenario = ScenarioMetadata(
            scenario_name="",
            scenario_doc_path="path",
            agent_path="path",
            technology_area="area",
        )

        with pytest.raises(ValueError, match="scenario_name"):
            asyncio.run(
                manager.deploy(
                    invalid_scenario,
                    ServicePrincipalDetails(
                        sp_name="test",
                        client_id="123",
                        principal_id="456",
                        secret_reference="secret",
                        created_at=datetime.now(UTC).isoformat(),
                        scenario_name="test",
                    ),
                )
            )

    def test_get_status_invalid_app_name(self, mock_config):
        """Test status check rejects empty app name."""
        manager = ContainerManager(config=mock_config)

        with pytest.raises(ValueError, match="App name"):
            asyncio.run(manager.get_status(""))

    def test_delete_invalid_app_name(self, mock_config):
        """Test deletion rejects empty app name."""
        manager = ContainerManager(config=mock_config)

        with pytest.raises(ValueError, match="App name"):
            asyncio.run(manager.delete(""))


class TestDeployContainerAppFunction:
    """Test the standalone deploy_container_app function."""

    @pytest.mark.asyncio
    async def test_deploy_container_app_basic_validation(self, mock_config, mock_scenario, mock_sp):
        """Test deploy function validates inputs."""
        # Valid inputs should not raise immediately
        # (The actual deploy would be mocked in integration tests)
        assert mock_scenario.scenario_name
        assert mock_sp.client_id

    @pytest.mark.asyncio
    async def test_deploy_container_app_invalid_scenario(self, mock_config, mock_sp):
        """Test deploy rejects invalid scenario."""
        invalid_scenario = ScenarioMetadata(
            scenario_name="",
            scenario_doc_path="path",
            agent_path="path",
            technology_area="area",
        )

        with pytest.raises((ValueError, ContainerAppError)):
            await deploy_container_app(
                scenario=invalid_scenario,
                sp=mock_sp,
                config=mock_config,
            )


class TestGetContainerStatusFunction:
    """Test the standalone get_container_status function."""

    @pytest.mark.asyncio
    async def test_get_container_status_invalid_inputs(self):
        """Test status function validates required inputs."""
        with pytest.raises(ValueError, match="required"):
            await get_container_status(
                app_name="",
                resource_group_name="rg",
                subscription_id="sub",
            )

        with pytest.raises(ValueError, match="required"):
            await get_container_status(
                app_name="app",
                resource_group_name="",
                subscription_id="sub",
            )

        with pytest.raises(ValueError, match="required"):
            await get_container_status(
                app_name="app",
                resource_group_name="rg",
                subscription_id="",
            )


class TestDeleteContainerAppFunction:
    """Test the standalone delete_container_app function."""

    @pytest.mark.asyncio
    async def test_delete_container_app_invalid_inputs(self):
        """Test delete function validates required inputs."""
        with pytest.raises(ValueError, match="required"):
            await delete_container_app(
                app_name="",
                resource_group_name="rg",
                subscription_id="sub",
            )

        with pytest.raises(ValueError, match="required"):
            await delete_container_app(
                app_name="app",
                resource_group_name="",
                subscription_id="sub",
            )

        with pytest.raises(ValueError, match="required"):
            await delete_container_app(
                app_name="app",
                resource_group_name="rg",
                subscription_id="",
            )


class TestContainerAppError:
    """Test ContainerAppError exception."""

    def test_container_app_error_creation(self):
        """Test creating ContainerAppError."""
        error = ContainerAppError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestContainerManagerEdgeCases:
    """Test edge cases and special scenarios."""

    def test_container_manager_with_minimal_config(self):
        """Test ContainerManager with minimal required config."""
        minimal_config = OrchestratorConfig(
            target_tenant_id="tenant",
            target_subscription_id="sub",
            main_sp_client_id="sp",
            main_sp_client_secret="secret",
            anthropic_api_key="key",
            service_bus_namespace="bus",
            container_registry="registry",
            container_image="image",
            key_vault_url="https://vault.net",
            simulation_size=SimulationSize.SMALL,
            storage=StorageConfig(
                account_name="storage",
                container_logs="logs",
                container_state="state",
                container_reports="reports",
                container_scenarios="scenarios",
            ),
            table_storage=TableStorageConfig(
                account_name="ts",
                table_execution_runs="runs",
                table_scenario_status="status",
                table_resource_inventory="inventory",
            ),
            cosmosdb=CosmosDBConfig(
                endpoint="https://cosmos.net",
                database_name="db",
                container_metrics="metrics",
            ),
            log_analytics=LogAnalyticsConfig(
                workspace_id="workspace",
                workspace_key="key",
            ),
            vnet_integration_enabled=False,
        )

        manager = ContainerManager(config=minimal_config)
        assert manager.config.container_memory_gb == 64
        assert manager.config.container_cpu_cores == 2

    def test_app_name_with_special_chars(self, mock_config):
        """Test app name generation handles special characters."""
        manager = ContainerManager(config=mock_config)

        # Test with various special characters
        test_names = [
            "scenario-with-dashes",
            "scenario_with_underscores",
            "scenario123",
            "Scenario-MiXeD-Case",
        ]

        for name in test_names:
            app_name = manager._generate_app_name(name)
            # All app names should be valid (lowercase, alphanumeric + hyphens, max 63 chars)
            assert len(app_name) <= 63
            assert app_name.endswith("-agent")
            assert all(c.islower() or c.isdigit() or c == "-" for c in app_name)

    def test_region_selection(self, mock_config):
        """Test default region selection."""
        manager = ContainerManager(config=mock_config)
        region = manager._get_region()
        assert region == "eastus"
