"""Unit tests for container_deployer module.

Tests for Container App deployment functionality including configuration building,
VNet integration, and Azure Container Apps API orchestration.

This module tests:
- ContainerDeployer initialization and validation
- Container configuration building
- Template and configuration building
- App name generation
- Resource validation
- VNet validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from azure_haymaker.models.config import OrchestratorConfig
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails
from azure_haymaker.orchestrator.container_deployer import (
    ContainerAppError,
    ContainerDeployer,
)


def create_mock_config(
    resource_group: str = "test-rg",
    subscription_id: str = "sub-123",
    target_tenant_id: str = "tenant-456",
    container_memory_gb: int = 64,
    container_cpu_cores: int = 2,
    vnet_enabled: bool = False,
    is_cross_tenant: bool = False,
) -> MagicMock:
    """Create a mock OrchestratorConfig for testing."""
    config = MagicMock(spec=OrchestratorConfig)
    config.resource_group_name = resource_group
    config.target_subscription_id = subscription_id
    config.target_tenant_id = target_tenant_id
    config.container_memory_gb = container_memory_gb
    config.container_cpu_cores = container_cpu_cores
    config.vnet_integration_enabled = vnet_enabled
    config.vnet_resource_group = "vnet-rg" if vnet_enabled else None
    config.vnet_name = "test-vnet" if vnet_enabled else None
    config.subnet_name = "test-subnet" if vnet_enabled else None
    config.key_vault_url = "https://test-vault.vault.azure.net/"
    config.container_registry = "testacr.azurecr.io"
    config.container_image = "haymaker:latest"
    config.main_sp_client_id = "main-sp-client-id"
    config.is_cross_tenant = is_cross_tenant
    config.target_tenant_sp_client_id = "target-sp-client-id" if is_cross_tenant else None
    config.target_tenant_sp_client_secret = (
        SecretStr("target-sp-secret") if is_cross_tenant else None
    )
    return config


def create_mock_scenario(name: str = "compute-01") -> ScenarioMetadata:
    """Create a mock ScenarioMetadata for testing."""
    return ScenarioMetadata(
        scenario_name=name,
        scenario_doc_path="/docs/scenarios/compute/compute-01.md",
        agent_path="/agents/compute-01/agent.py",
        technology_area="compute",
    )


def create_mock_sp_details(client_id: str = "sp-client-id") -> MagicMock:
    """Create a mock ServicePrincipalDetails for testing.

    Uses MagicMock because the actual model has many required fields.
    """
    mock_sp = MagicMock(spec=ServicePrincipalDetails)
    mock_sp.client_id = client_id
    mock_sp.principal_id = "sp-obj-id"
    mock_sp.sp_name = "test-sp"
    mock_sp.secret_reference = "sp-secret-ref"
    mock_sp.scenario_name = "test-scenario"
    return mock_sp


class TestContainerDeployerInit:
    """Tests for ContainerDeployer initialization."""

    def test_init_with_valid_config(self) -> None:
        """Test successful initialization with valid config."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)

        assert deployer.config == config
        assert deployer.resource_group_name == "test-rg"
        assert deployer.subscription_id == "sub-123"

    def test_init_requires_config(self) -> None:
        """Test that None config raises ValueError."""
        with pytest.raises(ValueError, match="Configuration is required"):
            ContainerDeployer(None)  # type: ignore[arg-type]

    def test_init_validates_memory_minimum(self) -> None:
        """Test that config with < 64GB memory raises ValueError."""
        config = create_mock_config(container_memory_gb=32)

        with pytest.raises(ValueError, match="Container memory must be at least 64GB"):
            ContainerDeployer(config)

    def test_init_validates_cpu_minimum(self) -> None:
        """Test that config with < 2 CPU cores raises ValueError."""
        config = create_mock_config(container_cpu_cores=1)

        with pytest.raises(ValueError, match="Container CPU cores must be at least 2"):
            ContainerDeployer(config)

    def test_init_validates_vnet_config_when_enabled(self) -> None:
        """Test that VNet config is validated when VNet integration is enabled."""
        config = create_mock_config(vnet_enabled=True)
        # Override to simulate incomplete VNet config
        config.vnet_resource_group = None

        with pytest.raises(ValueError, match="VNet integration enabled but"):
            ContainerDeployer(config)


class TestContainerDeployerGenerateAppName:
    """Tests for app name generation."""

    def test_generate_app_name_basic(self) -> None:
        """Test basic app name generation."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)

        name = deployer._generate_app_name("compute-01-linux-vm")

        assert name == "compute-01-linux-vm"

    def test_generate_app_name_converts_to_lowercase(self) -> None:
        """Test that uppercase is converted to lowercase."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)

        name = deployer._generate_app_name("Compute-01-Linux-VM")

        assert name == "compute-01-linux-vm"

    def test_generate_app_name_replaces_underscores(self) -> None:
        """Test that underscores are replaced with hyphens."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)

        name = deployer._generate_app_name("compute_01_linux_vm")

        assert name == "compute-01-linux-vm"

    def test_generate_app_name_removes_invalid_chars(self) -> None:
        """Test that invalid characters are removed."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)

        name = deployer._generate_app_name("compute@01!linux#vm")

        assert name == "compute01linuxvm"

    def test_generate_app_name_truncates_to_63_chars(self) -> None:
        """Test that names longer than 63 chars are truncated."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)

        long_name = "a" * 100
        name = deployer._generate_app_name(long_name)

        assert len(name) == 63


class TestContainerDeployerBuildContainer:
    """Tests for container configuration building."""

    def test_build_container_basic(self) -> None:
        """Test basic container configuration."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        sp = create_mock_sp_details()

        container = deployer._build_container("test-app", sp)

        assert container["name"] == "test-app"
        assert container["image"] == "testacr.azurecr.io/haymaker:latest"
        assert container["resources"]["cpu"] == "2"
        assert container["resources"]["memory"] == "64Gi"

    def test_build_container_includes_env_vars(self) -> None:
        """Test that container includes required environment variables."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        sp = create_mock_sp_details()

        container = deployer._build_container("test-app", sp)

        env_vars = {env["name"]: env for env in container["env"]}
        assert "AZURE_CLIENT_ID" in env_vars
        assert env_vars["AZURE_CLIENT_ID"]["value"] == "sp-client-id"
        assert "AZURE_TENANT_ID" in env_vars
        assert "AZURE_SUBSCRIPTION_ID" in env_vars
        assert "KEY_VAULT_URL" in env_vars

    def test_build_container_includes_secret_refs(self) -> None:
        """Test that container includes Key Vault secret references."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        sp = create_mock_sp_details()

        container = deployer._build_container("test-app", sp)

        env_vars = {env["name"]: env for env in container["env"]}
        assert "AZURE_CLIENT_SECRET" in env_vars
        assert env_vars["AZURE_CLIENT_SECRET"]["secretRef"] == "sp-client-secret"
        assert "ANTHROPIC_API_KEY" in env_vars
        assert env_vars["ANTHROPIC_API_KEY"]["secretRef"] == "anthropic-api-key"


class TestContainerDeployerBuildTemplate:
    """Tests for template building."""

    def test_build_template_basic(self) -> None:
        """Test basic template structure."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        container = {"name": "test-app", "image": "test:latest"}

        template = deployer._build_template(container)

        assert "containers" in template
        assert len(template["containers"]) == 1
        assert template["containers"][0] == container


class TestContainerDeployerBuildConfiguration:
    """Tests for configuration building."""

    def test_build_configuration_includes_secrets(self) -> None:
        """Test that configuration includes Key Vault secret references."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        sp = create_mock_sp_details()

        configuration = deployer._build_configuration(sp)

        assert "secrets" in configuration
        secret_names = [s["name"] for s in configuration["secrets"]]
        assert "sp-client-secret" in secret_names
        assert "anthropic-api-key" in secret_names

    def test_build_configuration_includes_registry(self) -> None:
        """Test that configuration includes registry configuration."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        sp = create_mock_sp_details()

        configuration = deployer._build_configuration(sp)

        assert "registries" in configuration
        assert len(configuration["registries"]) == 1
        assert configuration["registries"][0]["server"] == "testacr.azurecr.io"


class TestContainerDeployerGetRegion:
    """Tests for region retrieval."""

    def test_get_region_returns_default(self) -> None:
        """Test that get_region returns default 'eastus'."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)

        region = deployer._get_region()

        assert region == "eastus"


class TestContainerDeployerDeploy:
    """Tests for the deploy method."""

    @pytest.mark.asyncio
    async def test_deploy_validates_scenario(self) -> None:
        """Test that deploy validates scenario input."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        sp = create_mock_sp_details()

        with pytest.raises(ValueError, match="Valid scenario with scenario_name is required"):
            await deployer.deploy(None, sp)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_deploy_validates_scenario_name(self) -> None:
        """Test that deploy validates scenario has a name."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        sp = create_mock_sp_details()
        scenario = MagicMock(spec=ScenarioMetadata)
        scenario.scenario_name = None

        with pytest.raises(ValueError, match="Valid scenario with scenario_name is required"):
            await deployer.deploy(scenario, sp)

    @pytest.mark.asyncio
    async def test_deploy_validates_service_principal(self) -> None:
        """Test that deploy validates service principal input."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        scenario = create_mock_scenario()

        with pytest.raises(ValueError, match="Valid service principal is required"):
            await deployer.deploy(scenario, None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_deploy_validates_sp_client_id(self) -> None:
        """Test that deploy validates SP has client_id."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        scenario = create_mock_scenario()
        sp = MagicMock(spec=ServicePrincipalDetails)
        sp.client_id = None

        with pytest.raises(ValueError, match="Valid service principal is required"):
            await deployer.deploy(scenario, sp)

    @pytest.mark.asyncio
    async def test_deploy_handles_environment_not_found(self) -> None:
        """Test that deploy handles missing Container Apps Environment."""
        config = create_mock_config()
        deployer = ContainerDeployer(config)
        scenario = create_mock_scenario()
        sp = create_mock_sp_details()

        # Mock the credentials module for lazy import
        mock_creds_module = MagicMock()
        mock_creds_module.get_tenant_credential = MagicMock(return_value=MagicMock())

        # Mock the ContainerAppsAPIClient module for lazy import
        mock_appcontainers_module = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {
                    "azure_haymaker.utils.credentials": mock_creds_module,
                    "azure.mgmt.appcontainers": mock_appcontainers_module,
                },
            ),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.side_effect = Exception("Environment not found")

            with pytest.raises(ContainerAppError, match="Container Apps Environment"):
                await deployer.deploy(scenario, sp)

    @pytest.mark.asyncio
    async def test_deploy_cross_tenant_requires_credentials(self) -> None:
        """Test that cross-tenant deploy requires target tenant credentials."""
        config = create_mock_config(is_cross_tenant=True)
        config.target_tenant_sp_client_id = None  # Missing credential

        deployer = ContainerDeployer(config)
        scenario = create_mock_scenario()
        sp = create_mock_sp_details()

        mock_env = MagicMock()
        mock_env.id = "/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/env"
        mock_env.name = "env"
        mock_env.provisioning_state = "Succeeded"
        mock_env.location = "eastus"

        # Mock the credentials module for lazy import
        mock_creds_module = MagicMock()
        mock_creds_module.get_tenant_credential = MagicMock(return_value=MagicMock())

        # Mock the ContainerAppsAPIClient module for lazy import
        mock_appcontainers_module = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {
                    "azure_haymaker.utils.credentials": mock_creds_module,
                    "azure.mgmt.appcontainers": mock_appcontainers_module,
                },
            ),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.return_value = mock_env

            with pytest.raises(ContainerAppError, match="TARGET_TENANT_SP_CLIENT_ID"):
                await deployer.deploy(scenario, sp)


class TestContainerDeployerValidation:
    """Tests for validation methods."""

    def test_validate_resources_passes_with_minimum(self) -> None:
        """Test validation passes with minimum resource requirements."""
        config = create_mock_config(container_memory_gb=64, container_cpu_cores=2)
        # If init succeeds, validation passed
        deployer = ContainerDeployer(config)
        assert deployer is not None

    def test_validate_resources_passes_with_more_than_minimum(self) -> None:
        """Test validation passes with more than minimum resources."""
        config = create_mock_config(container_memory_gb=128, container_cpu_cores=4)
        deployer = ContainerDeployer(config)
        assert deployer is not None

    def test_validate_vnet_passes_when_disabled(self) -> None:
        """Test VNet validation passes when VNet is disabled."""
        config = create_mock_config(vnet_enabled=False)
        # Missing VNet config should be OK when disabled
        config.vnet_resource_group = None
        config.vnet_name = None
        config.subnet_name = None

        deployer = ContainerDeployer(config)
        assert deployer is not None

    def test_validate_vnet_passes_when_complete(self) -> None:
        """Test VNet validation passes when config is complete."""
        config = create_mock_config(vnet_enabled=True)
        # VNet config is set by create_mock_config when vnet_enabled=True
        deployer = ContainerDeployer(config)
        assert deployer is not None

    def test_validate_vnet_fails_missing_resource_group(self) -> None:
        """Test VNet validation fails when resource group is missing."""
        config = create_mock_config(vnet_enabled=True)
        config.vnet_resource_group = None

        with pytest.raises(ValueError, match="VNet integration enabled"):
            ContainerDeployer(config)

    def test_validate_vnet_fails_missing_vnet_name(self) -> None:
        """Test VNet validation fails when vnet_name is missing."""
        config = create_mock_config(vnet_enabled=True)
        config.vnet_name = None

        with pytest.raises(ValueError, match="VNet integration enabled"):
            ContainerDeployer(config)

    def test_validate_vnet_fails_missing_subnet(self) -> None:
        """Test VNet validation fails when subnet_name is missing."""
        config = create_mock_config(vnet_enabled=True)
        config.subnet_name = None

        with pytest.raises(ValueError, match="VNet integration enabled"):
            ContainerDeployer(config)
