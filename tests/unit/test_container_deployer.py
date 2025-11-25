"""
Unit tests for container_deployer module.

Tests cover:
- ContainerDeployer class initialization and validation
- Container app deployment with VNet integration
- Configuration building (container, template, secrets)
- Resource constraint validation (64GB RAM, 2 CPU minimum)
- Error handling and deployment failures

Testing approach:
- Mock Azure Container Apps SDK
- Test configuration validation at boundaries
- Focus on deployment workflow and error cases
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from azure_haymaker.models.config import OrchestratorConfig
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails
from azure_haymaker.orchestrator.container_deployer import (
    ContainerAppError,
    ContainerDeployer,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_config():
    """Create a valid orchestrator configuration."""
    config = Mock(spec=OrchestratorConfig)
    config.resource_group_name = "haymaker-rg"
    config.target_subscription_id = "sub-123"
    config.target_tenant_id = "tenant-123"
    config.container_memory_gb = 64
    config.container_cpu_cores = 2
    config.container_registry = "haymakerorchacr.azurecr.io"
    config.container_image = "haymaker-agent:latest"
    config.key_vault_url = "https://haymaker-kv.vault.azure.net/"
    config.main_sp_client_id = "main-sp-client-id"
    config.vnet_integration_enabled = False
    config.vnet_resource_group = None
    config.vnet_name = None
    config.subnet_name = None
    return config


@pytest.fixture
def mock_scenario():
    """Create a sample scenario metadata."""
    return ScenarioMetadata(
        scenario_name="compute-01-linux-vm",
        scenario_doc_path="/docs/compute-01.md",
        agent_path="/scenarios/compute-01/agent.py",
        technology_area="compute",
    )


@pytest.fixture
def mock_sp():
    """Create a sample service principal."""
    from datetime import datetime, UTC
    return ServicePrincipalDetails(
        sp_name="test-sp",
        client_id="sp-client-id",
        principal_id="sp-principal-id",
        secret_reference="sp-secret-ref",
        created_at=datetime.now(UTC),
        scenario_name="test-scenario",
    )


# ==============================================================================
# TESTS: Initialization and Validation
# ==============================================================================


def test_container_deployer_init_valid_config(mock_config):
    """Test ContainerDeployer initialization with valid config."""
    deployer = ContainerDeployer(mock_config)

    assert deployer.config == mock_config
    assert deployer.resource_group_name == "haymaker-rg"
    assert deployer.subscription_id == "sub-123"


def test_container_deployer_init_no_config():
    """Test error when config is None."""
    with pytest.raises(ValueError, match="Configuration is required"):
        ContainerDeployer(None)


def test_container_deployer_init_insufficient_memory(mock_config):
    """Test error when memory is less than 64GB."""
    mock_config.container_memory_gb = 32

    with pytest.raises(ValueError, match="Container memory must be at least 64GB"):
        ContainerDeployer(mock_config)


def test_container_deployer_init_insufficient_cpu(mock_config):
    """Test error when CPU cores are less than 2."""
    mock_config.container_cpu_cores = 1

    with pytest.raises(ValueError, match="Container CPU cores must be at least 2"):
        ContainerDeployer(mock_config)


def test_container_deployer_init_vnet_enabled_missing_config(mock_config):
    """Test error when VNet integration enabled but config missing."""
    mock_config.vnet_integration_enabled = True
    mock_config.vnet_resource_group = None

    with pytest.raises(ValueError, match="VNet integration enabled"):
        ContainerDeployer(mock_config)


# ==============================================================================
# TESTS: App Name Generation
# ==============================================================================


def test_generate_app_name_normal(mock_config):
    """Test app name generation with normal scenario name."""
    deployer = ContainerDeployer(mock_config)
    name = deployer._generate_app_name("compute-01-linux-vm")

    assert name == "compute-01-linux-vm"
    assert len(name) <= 32


def test_generate_app_name_with_underscores(mock_config):
    """Test app name generation converts underscores to hyphens."""
    deployer = ContainerDeployer(mock_config)
    name = deployer._generate_app_name("compute_01_linux_vm")

    assert name == "compute-01-linux-vm"
    assert "_" not in name


def test_generate_app_name_too_long(mock_config):
    """Test app name is truncated to 32 characters."""
    deployer = ContainerDeployer(mock_config)
    long_name = "a" * 50
    name = deployer._generate_app_name(long_name)

    assert len(name) == 32


def test_generate_app_name_invalid_characters(mock_config):
    """Test invalid characters are removed from app name."""
    deployer = ContainerDeployer(mock_config)
    name = deployer._generate_app_name("compute@01#linux$vm")

    assert "@" not in name
    assert "#" not in name
    assert "$" not in name


# ==============================================================================
# TESTS: Container Configuration Building
# ==============================================================================


def test_build_container_happy_path(mock_config, mock_sp):
    """Test container configuration building."""
    deployer = ContainerDeployer(mock_config)
    container = deployer._build_container("test-app", mock_sp)

    assert container["name"] == "test-app"
    assert container["image"] == "haymakerorchacr.azurecr.io/haymaker-agent:latest"
    assert container["resources"]["cpu"] == "2"
    assert container["resources"]["memory"] == "64Gi"

    # Verify environment variables
    env_vars = {env["name"]: env for env in container["env"]}
    assert "AZURE_CLIENT_ID" in env_vars
    assert env_vars["AZURE_CLIENT_ID"]["value"] == "sp-client-id"
    assert "AZURE_TENANT_ID" in env_vars
    assert "AZURE_CLIENT_SECRET" in env_vars
    assert env_vars["AZURE_CLIENT_SECRET"]["secretRef"] == "sp-client-secret"


def test_build_template(mock_config, mock_sp):
    """Test template building with container."""
    deployer = ContainerDeployer(mock_config)
    container = deployer._build_container("test-app", mock_sp)
    template = deployer._build_template(container)

    assert "containers" in template
    assert len(template["containers"]) == 1
    assert template["containers"][0] == container


def test_build_configuration(mock_config, mock_sp):
    """Test configuration building with secrets and registry."""
    deployer = ContainerDeployer(mock_config)
    configuration = deployer._build_configuration(mock_sp)

    assert "secrets" in configuration
    assert "registries" in configuration

    # Verify secrets include Key Vault references
    secrets = {s["name"]: s for s in configuration["secrets"]}
    assert "sp-client-secret" in secrets
    assert "keyVaultUrl" in secrets["sp-client-secret"]
    assert "anthropic-api-key" in secrets

    # Verify registry configuration
    registries = configuration["registries"]
    assert len(registries) == 1
    assert registries[0]["server"] == "haymakerorchacr.azurecr.io"


# ==============================================================================
# TESTS: Deployment (with mocked SDK)
# ==============================================================================


@pytest.mark.asyncio
async def test_deploy_happy_path(mock_config, mock_scenario, mock_sp):
    """Test successful container app deployment."""
    with patch.dict(
        "os.environ",
        {
            "AZURE_TENANT_ID": "tenant-123",
            "AZURE_CLIENT_ID": "client-123",
            "AZURE_CLIENT_SECRET": "secret-123",
        },
    ):
        with patch("subprocess.run") as mock_run:
            # Mock successful CLI login
            mock_run.side_effect = [
                Mock(returncode=0, stdout="", stderr=""),  # az login
                Mock(returncode=0, stdout='{"username": "acr", "passwords": [{"value": "pw"}]}', stderr=""),  # ACR creds
                Mock(returncode=0, stdout="test-fqdn.azurecontainerapps.io\n", stderr=""),  # az containerapp create
            ]

            with patch("azure.mgmt.appcontainers.ContainerAppsAPIClient") as mock_client:
                # Mock environment lookup
                mock_env = Mock()
                mock_env.id = "/subscriptions/sub-123/resourceGroups/haymaker-rg/providers/Microsoft.App/managedEnvironments/haymaker-fastapi-cae"
                mock_env.name = "haymaker-fastapi-cae"
                mock_env.provisioning_state = "Succeeded"
                mock_env.location = "eastus"

                mock_env_client = Mock()
                mock_env_client.managed_environments = Mock()
                mock_env_client.managed_environments.get = Mock(return_value=mock_env)
                mock_client.return_value = mock_env_client

                deployer = ContainerDeployer(mock_config)
                resource_id = await deployer.deploy(mock_scenario, mock_sp)

                assert "/containerApps/compute-01-linux-vm" in resource_id
                assert "haymaker-rg" in resource_id


@pytest.mark.asyncio
async def test_deploy_invalid_scenario(mock_config, mock_sp):
    """Test error when scenario is invalid."""
    deployer = ContainerDeployer(mock_config)

    with pytest.raises(ValueError, match="Valid scenario"):
        await deployer.deploy(None, mock_sp)


@pytest.mark.asyncio
async def test_deploy_invalid_sp(mock_config, mock_scenario):
    """Test error when service principal is invalid."""
    deployer = ContainerDeployer(mock_config)

    with pytest.raises(ValueError, match="Valid service principal"):
        await deployer.deploy(mock_scenario, None)


@pytest.mark.asyncio
async def test_deploy_environment_not_found(mock_config, mock_scenario, mock_sp):
    """Test error when Container Apps environment doesn't exist."""
    with patch.dict(
        "os.environ",
        {
            "AZURE_TENANT_ID": "tenant-123",
            "AZURE_CLIENT_ID": "client-123",
            "AZURE_CLIENT_SECRET": "secret-123",
        },
    ):
        with patch("azure.mgmt.appcontainers.ContainerAppsAPIClient") as mock_client:
            mock_env_client = Mock()
            mock_env_client.managed_environments = Mock()
            mock_env_client.managed_environments.get = Mock(
                side_effect=Exception("Environment not found")
            )
            mock_client.return_value = mock_env_client

            deployer = ContainerDeployer(mock_config)

            with pytest.raises(ContainerAppError, match="Container Apps Environment not accessible"):
                await deployer.deploy(mock_scenario, mock_sp)


@pytest.mark.asyncio
async def test_deploy_cli_failure(mock_config, mock_scenario, mock_sp):
    """Test error handling when Azure CLI deployment fails."""
    with patch.dict(
        "os.environ",
        {
            "AZURE_TENANT_ID": "tenant-123",
            "AZURE_CLIENT_ID": "client-123",
            "AZURE_CLIENT_SECRET": "secret-123",
        },
    ):
        with patch("subprocess.run") as mock_run:
            # Mock failed CLI deployment
            mock_run.side_effect = [
                Mock(returncode=0, stdout="", stderr=""),  # az login
                Mock(returncode=0, stdout='{"username": "acr", "passwords": [{"value": "pw"}]}', stderr=""),  # ACR creds
                Mock(returncode=1, stdout="", stderr="Deployment failed: quota exceeded"),  # Failed deployment
            ]

            with patch("azure.mgmt.appcontainers.ContainerAppsAPIClient") as mock_client:
                mock_env = Mock()
                mock_env.id = "/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/env"
                mock_env.name = "haymaker-fastapi-cae"
                mock_env.provisioning_state = "Succeeded"
                mock_env.location = "eastus"

                mock_env_client = Mock()
                mock_env_client.managed_environments = Mock()
                mock_env_client.managed_environments.get = Mock(return_value=mock_env)
                mock_client.return_value = mock_env_client

                deployer = ContainerDeployer(mock_config)

                with pytest.raises(ContainerAppError, match="Failed to deploy via CLI"):
                    await deployer.deploy(mock_scenario, mock_sp)


# ==============================================================================
# TESTS: Helper Methods
# ==============================================================================


def test_get_region(mock_config):
    """Test region retrieval."""
    deployer = ContainerDeployer(mock_config)
    region = deployer._get_region()

    assert region == "eastus"
