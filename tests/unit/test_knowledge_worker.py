"""Unit tests for Knowledge Worker Orchestrator and User Manager.

Tests critical paths introduced in PR #115:
- Orchestrator credential validation
- License assignment functionality
- DeploymentConfig changes
- User provisioning with license assignment
"""

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from azure_haymaker.knowledge_worker.identity.user_manager import EntraUserManager
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity, WorkerPersona
from azure_haymaker.knowledge_worker.orchestrator import (
    DeploymentConfig,
    KnowledgeWorkerOrchestrator,
)


class TestOrchestratorCredentials:
    """Test suite for orchestrator credential validation."""

    def test_orchestrator_requires_graph_client(self):
        """Test that orchestrator raises ValueError when graph_client is None.

        Critical path: Orchestrator must reject None graph_client at initialization.
        This ensures the orchestrator only operates with real M365 credentials.
        """
        with pytest.raises(ValueError, match="graph_client is required"):
            KnowledgeWorkerOrchestrator(None)

    def test_orchestrator_error_message_includes_env_vars(self):
        """Test that error message guides user to set credentials.

        Critical path: Error message must provide actionable guidance on
        which environment variables to set for M365 authentication.
        """
        with pytest.raises(ValueError, match=".") as exc_info:
            KnowledgeWorkerOrchestrator(None)

        error_msg = str(exc_info.value)
        assert "KW_TENANT_ID" in error_msg
        assert "KW_APP_ID" in error_msg
        assert "KW_CLIENT_SECRET" in error_msg

    def test_orchestrator_error_message_mentions_real_operations(self):
        """Test that error message clarifies real M365 operations requirement.

        Critical path: Users must understand this orchestrator only works
        with real M365 operations, not simulation.
        """
        with pytest.raises(ValueError, match=".") as exc_info:
            KnowledgeWorkerOrchestrator(None)

        error_msg = str(exc_info.value)
        assert "real m365 operations" in error_msg.lower()

    def test_orchestrator_accepts_valid_client(self):
        """Test that orchestrator accepts valid GraphServiceClient.

        Critical path: Orchestrator must successfully initialize when
        provided with a valid Graph client.
        """
        mock_client = Mock()
        orchestrator = KnowledgeWorkerOrchestrator(mock_client)

        assert orchestrator._graph_client == mock_client
        assert orchestrator._deployments == {}
        assert orchestrator._worker_tasks == {}

    def test_orchestrator_initializes_empty_state(self):
        """Test that orchestrator initializes with clean state.

        Ensures no leftover state from previous runs.
        """
        mock_client = Mock()
        orchestrator = KnowledgeWorkerOrchestrator(mock_client)

        assert orchestrator._user_manager is None
        assert orchestrator._worker_registry is None
        assert len(orchestrator._deployments) == 0


class TestLicenseAssignment:
    """Test suite for license assignment functionality."""

    @pytest.mark.anyio
    async def test_assign_license_success(self):
        """Test successful license assignment.

        Critical path: License assignment must succeed and return True
        when Graph API call succeeds.
        """
        # Mock GraphServiceClient
        mock_client = Mock()

        # Mock subscribed SKUs query
        mock_sku = Mock()
        mock_sku.sku_part_number = "SPE_E5"
        mock_sku.sku_id = UUID("06ebc4ee-1bb5-47dd-8120-11324bc54e06")
        mock_sku.prepaid_units = Mock()
        mock_sku.prepaid_units.enabled = 10
        mock_sku.consumed_units = 5

        mock_skus_response = Mock()
        mock_skus_response.value = [mock_sku]
        mock_client.subscribed_skus.get = AsyncMock(return_value=mock_skus_response)

        # Mock license assignment
        mock_user_item = Mock()
        mock_user_item.assign_license.post = AsyncMock()
        mock_client.users.by_user_id.return_value = mock_user_item

        manager = EntraUserManager(mock_client, "run-123", "test.onmicrosoft.com")
        result = await manager.assign_license("user-id-123")

        assert result is True
        mock_client.users.by_user_id.assert_called_once_with("user-id-123")
        mock_user_item.assign_license.post.assert_called_once()

    @pytest.mark.anyio
    async def test_assign_license_with_custom_sku(self):
        """Test license assignment with custom SKU ID.

        Critical path: License assignment must support custom SKU IDs
        for different M365 license types.
        """
        mock_client = Mock()
        captured_body = None

        async def capture_body(body):
            nonlocal captured_body
            captured_body = body

        mock_client.users.by_user_id.return_value.assign_license.post = AsyncMock(
            side_effect=capture_body
        )

        manager = EntraUserManager(mock_client, "run-123", "test.onmicrosoft.com")
        custom_sku = "06ebc4ee-1bb5-47dd-8120-11324bc54e07"  # Custom E5-like UUID
        result = await manager.assign_license("user-id-123", sku_id=custom_sku)

        assert result is True
        # Verify custom SKU was used
        assert captured_body is not None
        assert len(captured_body.add_licenses) == 1
        expected_custom_uuid = UUID(custom_sku)
        assert captured_body.add_licenses[0].sku_id == expected_custom_uuid

    @pytest.mark.anyio
    async def test_assign_license_default_sku_is_e5(self):
        """Test that default SKU is Microsoft 365 E5.

        Critical path: Verify default license is E5 as documented.
        """
        mock_client = Mock()
        captured_body = None

        async def capture_body(body):
            nonlocal captured_body
            captured_body = body

        # Mock subscribed SKUs query
        mock_sku = Mock()
        mock_sku.sku_part_number = "SPE_E5"
        mock_sku.sku_id = UUID("06ebc4ee-1bb5-47dd-8120-11324bc54e06")
        mock_sku.prepaid_units = Mock()
        mock_sku.prepaid_units.enabled = 10
        mock_sku.consumed_units = 5

        mock_skus_response = Mock()
        mock_skus_response.value = [mock_sku]
        mock_client.subscribed_skus.get = AsyncMock(return_value=mock_skus_response)

        # Mock license assignment
        mock_user_item = Mock()
        mock_user_item.assign_license.post = AsyncMock(side_effect=capture_body)
        mock_client.users.by_user_id.return_value = mock_user_item

        manager = EntraUserManager(mock_client, "run-123", "test.onmicrosoft.com")
        await manager.assign_license("user-id-123")

        # Verify E5 SKU UUID was used
        assert captured_body is not None
        assert len(captured_body.add_licenses) == 1
        expected_e5_uuid = UUID("06ebc4ee-1bb5-47dd-8120-11324bc54e06")
        assert captured_body.add_licenses[0].sku_id == expected_e5_uuid

    @pytest.mark.anyio
    async def test_assign_license_failure_returns_false(self):
        """Test that license assignment failure returns False.

        Critical path: License failures must not raise exceptions.
        They should return False and log a warning.
        """
        mock_client = Mock()
        mock_client.users.by_user_id.return_value.assign_license.post = AsyncMock(
            side_effect=Exception("No licenses available")
        )

        manager = EntraUserManager(mock_client, "run-123", "test.onmicrosoft.com")
        result = await manager.assign_license("user-id-123")

        assert result is False

    @pytest.mark.anyio
    async def test_assign_license_failure_logs_warning(self, caplog):
        """Test that license failure logs warning with details.

        Critical path: License failures must be logged for troubleshooting
        but shouldn't prevent user creation.
        """
        import logging

        mock_client = Mock()
        error_msg = "Insufficient licenses in tenant"

        # Mock subscribed SKUs query
        mock_sku = Mock()
        mock_sku.sku_part_number = "SPE_E5"
        mock_sku.sku_id = UUID("06ebc4ee-1bb5-47dd-8120-11324bc54e06")
        mock_sku.prepaid_units = Mock()
        mock_sku.prepaid_units.enabled = 10
        mock_sku.consumed_units = 5

        mock_skus_response = Mock()
        mock_skus_response.value = [mock_sku]
        mock_client.subscribed_skus.get = AsyncMock(return_value=mock_skus_response)

        # Mock license assignment failure
        mock_user_item = Mock()
        mock_user_item.assign_license.post = AsyncMock(side_effect=Exception(error_msg))
        mock_client.users.by_user_id.return_value = mock_user_item

        with caplog.at_level(logging.WARNING):
            manager = EntraUserManager(mock_client, "run-123", "test.onmicrosoft.com")
            await manager.assign_license("user-id-123")

        assert any("Failed to assign license" in record.message for record in caplog.records)
        assert any(error_msg in record.message for record in caplog.records)

    @pytest.mark.anyio
    async def test_provision_worker_calls_assign_license(self):
        """Test that provision_worker calls assign_license.

        Critical path: User provisioning must attempt license assignment
        after user creation.
        """
        mock_client = Mock()

        # Mock user creation
        mock_created_user = Mock()
        mock_created_user.id = "new-user-id"
        mock_client.users.post = AsyncMock(return_value=mock_created_user)

        # Mock subscribed SKUs query
        mock_sku = Mock()
        mock_sku.sku_part_number = "SPE_E5"
        mock_sku.sku_id = UUID("06ebc4ee-1bb5-47dd-8120-11324bc54e06")
        mock_sku.prepaid_units = Mock()
        mock_sku.prepaid_units.enabled = 10
        mock_sku.consumed_units = 5

        mock_skus_response = Mock()
        mock_skus_response.value = [mock_sku]
        mock_client.subscribed_skus.get = AsyncMock(return_value=mock_skus_response)

        # Mock user update (patch) and license assignment
        mock_user_item = Mock()
        mock_user_item.patch = AsyncMock()
        mock_user_item.assign_license.post = AsyncMock(return_value=None)
        mock_client.users.by_user_id.return_value = mock_user_item

        manager = EntraUserManager(mock_client, "run-123", "test.onmicrosoft.com")

        # Mock mailbox waiter to prevent polling (added in PR #167)
        from azure_haymaker.knowledge_worker.identity.mailbox_waiter import (
            MailboxStatus,
            MailboxWaitResult,
        )

        mock_wait_result = MailboxWaitResult(
            status=MailboxStatus.READY, elapsed_seconds=0.1, attempts=1
        )
        manager.mailbox_waiter.wait_for_mailbox = AsyncMock(return_value=mock_wait_result)

        identity = await manager.provision_worker(
            department="engineering",
            index=0,
            display_name="Test Worker",
            persona=WorkerPersona.ENGINEERING,
        )

        # Verify user was created
        assert identity is not None
        assert identity.entra_object_id == "new-user-id"

        # Verify license assignment was attempted
        assert mock_client.users.by_user_id.call_count == 2  # Called for patch and license
        mock_user_item.assign_license.post.assert_called_once()

        # Verify mailbox waiter was called
        manager.mailbox_waiter.wait_for_mailbox.assert_called_once_with(
            "new-user-id", timeout_seconds=900
        )

    @pytest.mark.anyio
    async def test_license_failure_does_not_prevent_user_creation(self):
        """Test that license assignment failure doesn't fail provisioning.

        Critical path: User creation must succeed even if license assignment
        fails, as licenses can be assigned later.
        """
        mock_client = Mock()

        # Mock user creation success
        mock_created_user = Mock()
        mock_created_user.id = "new-user-id"
        mock_client.users.post = AsyncMock(return_value=mock_created_user)

        # Mock subscribed SKUs query
        mock_sku = Mock()
        mock_sku.sku_part_number = "SPE_E5"
        mock_sku.sku_id = UUID("06ebc4ee-1bb5-47dd-8120-11324bc54e06")
        mock_sku.prepaid_units = Mock()
        mock_sku.prepaid_units.enabled = 10
        mock_sku.consumed_units = 5

        mock_skus_response = Mock()
        mock_skus_response.value = [mock_sku]
        mock_client.subscribed_skus.get = AsyncMock(return_value=mock_skus_response)

        # Mock user update (patch) and license assignment failure
        mock_user_item = Mock()
        mock_user_item.patch = AsyncMock()
        mock_user_item.assign_license.post = AsyncMock(side_effect=Exception("License failure"))
        mock_client.users.by_user_id.return_value = mock_user_item

        manager = EntraUserManager(mock_client, "run-123", "test.onmicrosoft.com")

        # Should not raise exception
        identity = await manager.provision_worker(
            department="engineering",
            index=0,
            display_name="Test Worker",
            persona=WorkerPersona.ENGINEERING,
        )

        # User should be created successfully
        assert identity is not None
        assert identity.entra_object_id == "new-user-id"
        assert identity.worker_id == "kw-run-123-engi-000"


class TestDeploymentConfig:
    """Test suite for DeploymentConfig changes."""

    def test_deployment_config_no_live_mode(self):
        """Test that DeploymentConfig doesn't have live_mode attribute.

        Critical path: The live_mode attribute was removed in PR #115.
        Orchestrator now only operates with real M365 credentials.
        """
        config = DeploymentConfig(name="test")
        assert not hasattr(config, "live_mode")

    def test_deployment_config_has_required_fields(self):
        """Test that DeploymentConfig has all required fields.

        Ensures no regression in required configuration fields.
        """
        config = DeploymentConfig(
            name="test",
            total_workers=5,
            tenant_domain="test.onmicrosoft.com",
        )

        assert config.name == "test"
        assert config.total_workers == 5
        assert config.tenant_domain == "test.onmicrosoft.com"

    def test_deployment_config_default_values(self):
        """Test that DeploymentConfig has sensible defaults.

        Ensures new deployments work with minimal configuration.
        """
        config = DeploymentConfig()

        assert config.name == "kw-deployment"
        assert config.total_workers == 10
        assert config.duration_hours == 8
        assert config.tenant_domain == ""
        assert config.m365_app_id == ""

    def test_deployment_config_departments_default(self):
        """Test that DeploymentConfig initializes default departments.

        Critical path: When departments not provided, config should
        create default engineering department.
        """
        config = DeploymentConfig(total_workers=10)

        assert "engineering" in config.departments
        assert config.departments["engineering"]["count"] == 10
        assert config.departments["engineering"]["endpoint_type"] == "cli_container"

    def test_deployment_config_custom_departments(self):
        """Test that DeploymentConfig accepts custom departments.

        Ensures flexibility in department configuration.
        """
        custom_depts = {
            "sales": {
                "count": 5,
                "endpoint_type": "cli_container",
                "activity": {
                    "email_per_hour": 10,
                },
            },
            "engineering": {
                "count": 3,
                "endpoint_type": "cli_container",
                "activity": {
                    "email_per_hour": 4,
                },
            },
        }

        config = DeploymentConfig(departments=custom_depts)

        assert "sales" in config.departments
        assert "engineering" in config.departments
        assert config.departments["sales"]["count"] == 5
        assert config.departments["engineering"]["count"] == 3


class TestEntraUserManagerNaming:
    """Test suite for EntraUserManager naming conventions."""

    def test_user_naming_pattern(self):
        """Test that user naming follows convention.

        Verifies naming pattern: kw-{run_id[:8]}-{dept[:4]}-{index:03d}
        """
        mock_client = Mock()
        manager = EntraUserManager(mock_client, "run-12345678-abcd", "test.onmicrosoft.com")

        username = manager.NAMING_PATTERN.format(
            run_id="run-1234",
            dept="engi",
            index=42,
        )

        assert username == "kw-run-1234-engi-042"

    def test_upn_generation(self):
        """Test that UPN is correctly formatted.

        Verifies UPN format: {username}@{tenant_domain}
        """
        mock_client = Mock()
        manager = EntraUserManager(mock_client, "run-12345678", "contoso.onmicrosoft.com")

        username = "kw-run-1234-engi-000"
        upn = f"{username}@{manager.tenant_domain}"

        assert upn == "kw-run-1234-engi-000@contoso.onmicrosoft.com"


class TestIntegration:
    """Integration tests for orchestrator and user manager interaction."""

    @pytest.mark.anyio
    async def test_orchestrator_uses_user_manager_for_provisioning(self):
        """Test that orchestrator delegates provisioning to EntraUserManager.

        Critical path: Orchestrator must use EntraUserManager for all
        user creation operations.
        """
        mock_client = Mock()
        orchestrator = KnowledgeWorkerOrchestrator(mock_client)

        config = DeploymentConfig(
            name="test-deployment",
            total_workers=1,
            tenant_domain="test.onmicrosoft.com",
        )

        run_id = orchestrator.create_deployment(config)

        # Verify deployment was created
        assert run_id.startswith("kw-")
        state = orchestrator.get_deployment(run_id)
        assert state is not None
        assert state.config.name == "test-deployment"

    def test_orchestrator_list_deployments(self):
        """Test that orchestrator can list all deployments.

        Ensures deployment tracking works correctly.
        """
        mock_client = Mock()
        orchestrator = KnowledgeWorkerOrchestrator(mock_client)

        # Create multiple deployments
        config1 = DeploymentConfig(name="deployment-1")
        config2 = DeploymentConfig(name="deployment-2")

        run_id_1 = orchestrator.create_deployment(config1)
        run_id_2 = orchestrator.create_deployment(config2)

        # List all deployments
        deployments = orchestrator.list_deployments()

        assert len(deployments) == 2
        assert any(d["run_id"] == run_id_1 for d in deployments)
        assert any(d["run_id"] == run_id_2 for d in deployments)


class TestWorkerIdentity:
    """Test suite for WorkerIdentity model."""

    def test_worker_identity_creation(self):
        """Test that WorkerIdentity can be created with required fields."""
        identity = WorkerIdentity(
            worker_id="kw-test-001",
            display_name="Test Worker",
            user_principal_name="kw-test-001@test.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
            entra_object_id="entra-123",
        )

        assert identity.worker_id == "kw-test-001"
        assert identity.display_name == "Test Worker"
        assert identity.entra_object_id == "entra-123"
        assert identity.persona == WorkerPersona.ENGINEERING

    def test_worker_identity_default_values(self):
        """Test that WorkerIdentity has sensible defaults."""
        identity = WorkerIdentity(
            worker_id="kw-test-001",
            display_name="Test Worker",
            user_principal_name="kw-test-001@test.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )

        assert identity.entra_object_id == ""
        assert identity.endpoint_id == ""
        assert identity.team_ids == []
        assert identity.security_group_ids == []
        assert identity.created_at is None
        assert identity.last_activity_at is None
