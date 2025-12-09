"""Integration tests for Phase 3 - Cross-tenant activity integration.

Tests that critical activities (sp_manager, container_deployer, execution_tracker)
correctly operate in both single-tenant and cross-tenant modes.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from azure_haymaker.orchestrator.container_deployer import ContainerDeployer
from azure_haymaker.orchestrator.execution_tracker import ExecutionTracker
from azure_haymaker.orchestrator.sp_manager import (
    ServicePrincipalDetails,
    create_service_principal,
    delete_service_principal,
)
from azure_haymaker.orchestrator.tenant_auth import TenantCredential
from pydantic import SecretStr


@pytest.fixture
def mock_tenant_context():
    """Create mock tenant context with credentials."""
    return {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "tenant_name": "tenant-alpha",
        "subscription_id": "22222222-2222-2222-2222-222222222222",
        "region": "eastus",
        "credential": TenantCredential(
            client_id="client-id-123",
            client_secret=SecretStr("client-secret-456"),
            tenant_id="11111111-1111-1111-1111-111111111111",
            subscription_id="22222222-2222-2222-2222-222222222222",
        ),
    }


@pytest.fixture
def mock_key_vault_client():
    """Create mock Key Vault client."""
    mock_client = MagicMock()
    mock_client.set_secret = MagicMock()
    mock_client.get_secret = MagicMock()
    mock_client.begin_delete_secret = MagicMock()
    return mock_client


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossTenantSPManager:
    """Test sp_manager.py cross-tenant functionality."""

    async def test_create_sp_single_tenant_mode(self, mock_key_vault_client):
        """Test SP creation in single-tenant mode (backward compatibility)."""
        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient"
        ) as mock_graph:
            # Mock Graph API responses
            mock_app = MagicMock()
            mock_app.id = "app-object-id"
            mock_app.app_id = "app-client-id"

            mock_sp = MagicMock()
            mock_sp.id = "sp-object-id"

            mock_password = MagicMock()
            mock_password.secret_text = "generated-secret"

            mock_graph_instance = mock_graph.return_value
            mock_graph_instance.applications.post = AsyncMock(return_value=mock_app)
            mock_graph_instance.applications.by_application_id.return_value.get = (
                AsyncMock(return_value=mock_app)
            )
            mock_graph_instance.service_principals.post = AsyncMock(return_value=mock_sp)
            mock_graph_instance.applications.by_application_id.return_value.add_password.post = AsyncMock(
                return_value=mock_password
            )

            with patch(
                "azure_haymaker.orchestrator.sp_manager.AuthorizationManagementClient"
            ) as mock_auth:
                mock_auth_instance = mock_auth.return_value
                mock_auth_instance.role_assignments.create = MagicMock()

                with patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs)):
                    with patch("asyncio.sleep", return_value=None):
                        # Test without tenant_context (single-tenant mode)
                        result = await create_service_principal(
                            scenario_name="test-scenario",
                            subscription_id="sub-123",
                            roles=["Contributor"],
                            key_vault_client=mock_key_vault_client,
                            tenant_context=None,  # Single-tenant mode
                        )

                        assert result.client_id == "app-client-id"
                        assert result.principal_id == "sp-object-id"
                        assert "test-scenario" in result.sp_name
                        mock_key_vault_client.set_secret.assert_called_once()

    async def test_create_sp_cross_tenant_mode(
        self, mock_key_vault_client, mock_tenant_context
    ):
        """Test SP creation in cross-tenant mode with tenant context."""
        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient"
        ) as mock_graph:
            # Mock Graph API responses
            mock_app = MagicMock()
            mock_app.id = "app-object-id"
            mock_app.app_id = "app-client-id"

            mock_sp = MagicMock()
            mock_sp.id = "sp-object-id"

            mock_password = MagicMock()
            mock_password.secret_text = "generated-secret"

            mock_graph_instance = mock_graph.return_value
            mock_graph_instance.applications.post = AsyncMock(return_value=mock_app)
            mock_graph_instance.applications.by_application_id.return_value.get = (
                AsyncMock(return_value=mock_app)
            )
            mock_graph_instance.service_principals.post = AsyncMock(return_value=mock_sp)
            mock_graph_instance.applications.by_application_id.return_value.add_password.post = AsyncMock(
                return_value=mock_password
            )

            with patch(
                "azure_haymaker.orchestrator.sp_manager.AuthorizationManagementClient"
            ) as mock_auth:
                mock_auth_instance = mock_auth.return_value
                mock_auth_instance.role_assignments.create = MagicMock()

                with patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs)):
                    with patch("asyncio.sleep", return_value=None):
                        # Test WITH tenant_context (cross-tenant mode)
                        result = await create_service_principal(
                            scenario_name="test-scenario",
                            subscription_id="sub-123",
                            roles=["Contributor"],
                            key_vault_client=mock_key_vault_client,
                            tenant_context=mock_tenant_context,  # Cross-tenant mode
                        )

                        assert result.client_id == "app-client-id"
                        assert result.principal_id == "sp-object-id"
                        mock_key_vault_client.set_secret.assert_called_once()

    async def test_delete_sp_cross_tenant_mode(
        self, mock_key_vault_client, mock_tenant_context
    ):
        """Test SP deletion in cross-tenant mode."""
        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient"
        ) as mock_graph:
            # Mock Graph API responses
            mock_sp = MagicMock()
            mock_sp.id = "sp-object-id"

            mock_sp_list = MagicMock()
            mock_sp_list.value = [mock_sp]

            mock_graph_instance = mock_graph.return_value
            mock_graph_instance.service_principals.get = AsyncMock(
                return_value=mock_sp_list
            )

            mock_delete_client = MagicMock()
            mock_delete_client.delete = AsyncMock()
            mock_graph_instance.service_principals.by_service_principal_id = MagicMock(
                return_value=mock_delete_client
            )

            with patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs)):
                # Test deletion with tenant context
                await delete_service_principal(
                    sp_name="AzureHayMaker-test-scenario-admin",
                    key_vault_client=mock_key_vault_client,
                    tenant_context=mock_tenant_context,
                )

                # Verify Key Vault secret deletion was attempted
                mock_key_vault_client.begin_delete_secret.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossTenantExecutionTracker:
    """Test execution_tracker.py cross-tenant functionality."""

    async def test_execution_tracker_single_tenant_mode(self):
        """Test execution tracker in single-tenant mode."""
        mock_table_client = MagicMock()
        mock_table_client.create_entity = AsyncMock()

        # Single-tenant mode (no tenant_context)
        tracker = ExecutionTracker(mock_table_client, tenant_context=None)

        execution_id = await tracker.create_execution(
            scenarios=["scenario-01"], duration_hours=2
        )

        assert execution_id.startswith("exec-")
        mock_table_client.create_entity.assert_called_once()

        # Verify PartitionKey does NOT have tenant prefix in single-tenant mode
        call_args = mock_table_client.create_entity.call_args
        entity = call_args[1]["entity"]
        assert entity["PartitionKey"] == execution_id  # No tenant prefix

    async def test_execution_tracker_cross_tenant_mode(self, mock_tenant_context):
        """Test execution tracker in cross-tenant mode with tenant isolation."""
        mock_table_client = MagicMock()
        mock_table_client.create_entity = AsyncMock()
        mock_table_client.query_entities = AsyncMock(return_value=[])

        # Cross-tenant mode (with tenant_context)
        tracker = ExecutionTracker(mock_table_client, tenant_context=mock_tenant_context)

        execution_id = await tracker.create_execution(
            scenarios=["scenario-01"], duration_hours=2
        )

        assert execution_id.startswith("exec-")
        mock_table_client.create_entity.assert_called_once()

        # Verify PartitionKey has tenant prefix in cross-tenant mode
        call_args = mock_table_client.create_entity.call_args
        entity = call_args[1]["entity"]
        tenant_id = mock_tenant_context["tenant_id"]
        assert entity["PartitionKey"].startswith(
            f"{tenant_id}#"
        )  # Tenant prefix applied
        assert entity["tenant_id"] == tenant_id  # Tenant field injected


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossTenantContainerDeployer:
    """Test container_deployer.py cross-tenant functionality."""

    async def test_container_deployer_single_tenant_mode(self):
        """Test container deployer in single-tenant mode."""
        from azure_haymaker.models.config import OrchestratorConfig
        from azure_haymaker.models.scenario import ScenarioMetadata

        config = OrchestratorConfig(
            resource_group_name="rg-test",
            target_subscription_id="sub-123",
            target_tenant_id="tenant-123",
            container_memory_gb=64,
            container_cpu_cores=2,
            key_vault_url="https://kv.vault.azure.net/",
            container_registry="myregistry.azurecr.io",
            container_image="haymaker:latest",
            main_sp_client_id="sp-123",
            vnet_integration_enabled=False,
        )

        # Single-tenant mode (no tenant_context)
        deployer = ContainerDeployer(config, tenant_context=None)

        assert deployer.subscription_id == "sub-123"
        assert deployer.resource_group_name == "rg-test"
        assert deployer.tenant_context is None

    async def test_container_deployer_cross_tenant_mode(self, mock_tenant_context):
        """Test container deployer in cross-tenant mode."""
        from azure_haymaker.models.config import OrchestratorConfig

        config = OrchestratorConfig(
            resource_group_name="rg-infra",
            target_subscription_id="sub-infra",
            target_tenant_id="tenant-infra",
            container_memory_gb=64,
            container_cpu_cores=2,
            key_vault_url="https://kv.vault.azure.net/",
            container_registry="myregistry.azurecr.io",
            container_image="haymaker:latest",
            main_sp_client_id="sp-infra",
            vnet_integration_enabled=False,
        )

        # Add resource_group_name to tenant context
        tenant_ctx = mock_tenant_context.copy()
        tenant_ctx["resource_group_name"] = "rg-tenant-alpha"

        # Cross-tenant mode (with tenant_context)
        deployer = ContainerDeployer(config, tenant_context=tenant_ctx)

        # Should use tenant context values, not config values
        assert deployer.subscription_id == tenant_ctx["subscription_id"]
        assert deployer.resource_group_name == "rg-tenant-alpha"
        assert deployer.tenant_context is not None


@pytest.mark.integration
@pytest.mark.asyncio
class TestEndToEndCrossTenantOrchestration:
    """End-to-end test for cross-tenant orchestration flow."""

    async def test_full_cross_tenant_workflow(
        self, mock_key_vault_client, mock_tenant_context
    ):
        """Test complete workflow: create SP -> track execution -> deploy container."""
        # Step 1: Create service principal in target tenant
        with patch(
            "azure_haymaker.orchestrator.sp_manager.GraphServiceClient"
        ) as mock_graph:
            mock_app = MagicMock()
            mock_app.id = "app-object-id"
            mock_app.app_id = "app-client-id"

            mock_sp = MagicMock()
            mock_sp.id = "sp-object-id"

            mock_password = MagicMock()
            mock_password.secret_text = "generated-secret"

            mock_graph_instance = mock_graph.return_value
            mock_graph_instance.applications.post = AsyncMock(return_value=mock_app)
            mock_graph_instance.applications.by_application_id.return_value.get = (
                AsyncMock(return_value=mock_app)
            )
            mock_graph_instance.service_principals.post = AsyncMock(return_value=mock_sp)
            mock_graph_instance.applications.by_application_id.return_value.add_password.post = AsyncMock(
                return_value=mock_password
            )

            with patch(
                "azure_haymaker.orchestrator.sp_manager.AuthorizationManagementClient"
            ) as mock_auth:
                mock_auth_instance = mock_auth.return_value
                mock_auth_instance.role_assignments.create = MagicMock()

                with patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs)):
                    with patch("asyncio.sleep", return_value=None):
                        sp_details = await create_service_principal(
                            scenario_name="e2e-scenario",
                            subscription_id=mock_tenant_context["subscription_id"],
                            roles=["Contributor"],
                            key_vault_client=mock_key_vault_client,
                            tenant_context=mock_tenant_context,
                        )

        assert sp_details.client_id == "app-client-id"

        # Step 2: Track execution with tenant isolation
        mock_table_client = MagicMock()
        mock_table_client.create_entity = AsyncMock()
        mock_table_client.query_entities = AsyncMock(return_value=[])

        tracker = ExecutionTracker(mock_table_client, tenant_context=mock_tenant_context)
        execution_id = await tracker.create_execution(
            scenarios=["e2e-scenario"], duration_hours=2
        )

        assert execution_id.startswith("exec-")

        # Step 3: Verify container deployer uses tenant context
        from azure_haymaker.models.config import OrchestratorConfig

        config = OrchestratorConfig(
            resource_group_name="rg-infra",
            target_subscription_id="sub-infra",
            target_tenant_id="tenant-infra",
            container_memory_gb=64,
            container_cpu_cores=2,
            key_vault_url="https://kv.vault.azure.net/",
            container_registry="myregistry.azurecr.io",
            container_image="haymaker:latest",
            main_sp_client_id="sp-infra",
            vnet_integration_enabled=False,
        )

        tenant_ctx = mock_tenant_context.copy()
        tenant_ctx["resource_group_name"] = "rg-tenant-alpha"

        deployer = ContainerDeployer(config, tenant_context=tenant_ctx)

        # Verify deployer is configured for target tenant
        assert deployer.subscription_id == mock_tenant_context["subscription_id"]
        assert deployer.resource_group_name == "rg-tenant-alpha"

        # Success: All components integrated with tenant awareness
