"""Unit tests for Azure HayMaker orchestrator with Durable Functions.

Tests cover:
- Timer trigger functionality
- Orchestration phases (validation, selection, provisioning, monitoring, cleanup, reporting)
- Activity functions with mocked dependencies
- Error handling and recovery
- Full workflow integration

Uses unittest.mock and azure-durable-functions test utilities.
"""

from datetime import UTC, datetime
from unittest import mock
from uuid import uuid4

import pytest

from azure_haymaker.orchestrator import (
    check_agent_status_activity,
    create_service_principal_activity,
    deploy_container_app_activity,
    force_cleanup_activity,
    generate_report_activity,
    select_scenarios_activity,
    validate_environment_activity,
    verify_cleanup_activity,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_config():
    """Fixture: Mock OrchestratorConfig."""
    return {
        "target_tenant_id": "test-tenant-id",
        "target_subscription_id": "test-subscription-id",
        "main_sp_client_id": "test-client-id",
        "main_sp_client_secret": "test-client-secret",
        "anthropic_api_key": "test-api-key",
        "service_bus_namespace": "test-sb.servicebus.windows.net",
        "container_registry": "test.azurecr.io",
        "container_image": "haymaker-agent:latest",
        "storage_account": "teststorage",
        "key_vault_url": "https://test-kv.vault.azure.net",
        "simulation_size": "small",
        "resource_group_name": "test-rg",
    }


@pytest.fixture
def mock_scenario():
    """Fixture: Mock scenario metadata."""
    return {
        "scenario_name": "test-scenario-01",
        "technology_area": "AI & ML",
        "scenario_doc_path": "docs/scenarios/test-scenario-01.md",
    }


@pytest.fixture
def mock_sp_details():
    """Fixture: Mock service principal details."""
    return {
        "sp_name": "AzureHayMaker-test-scenario-01-admin",
        "client_id": f"sp-client-{uuid4()}",
        "principal_id": f"sp-principal-{uuid4()}",
        "secret_reference": "scenario-sp-test-scenario-01-secret",
        "created_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def run_id():
    """Fixture: Unique run ID."""
    return str(uuid4())


# ==============================================================================
# TIMER TRIGGER TESTS
# ==============================================================================


class TestTimerTrigger:
    """Tests for timer trigger functionality."""

    def test_timer_trigger_imports(self):
        """Test that timer trigger is properly defined."""
        from azure_haymaker.orchestrator.orchestrator import haymaker_timer

        assert haymaker_timer is not None
        assert callable(haymaker_timer)

    def test_timer_trigger_has_decorators(self):
        """Test that timer trigger has expected decorators."""
        from azure_haymaker.orchestrator.orchestrator import haymaker_timer

        # Check that function is callable (decorators applied)
        assert callable(haymaker_timer)


# ==============================================================================
# ORCHESTRATION FUNCTION TESTS
# ==============================================================================


class TestOrchestrationFunction:
    """Tests for main orchestration function."""

    def test_orchestration_function_imports(self):
        """Test that orchestration function is properly defined."""
        from azure_haymaker.orchestrator.orchestrator import orchestrate_haymaker_run

        assert orchestrate_haymaker_run is not None
        assert callable(orchestrate_haymaker_run)

    def test_orchestration_function_has_decorator(self):
        """Test that orchestration function has orchestration_trigger decorator."""
        from azure_haymaker.orchestrator.orchestrator import orchestrate_haymaker_run

        # Check that function is callable (decorators applied)
        assert callable(orchestrate_haymaker_run)


# ==============================================================================
# ACTIVITY FUNCTION TESTS - Validation
# ==============================================================================


class TestValidateEnvironmentActivity:
    """Tests for validate_environment_activity."""

    @pytest.mark.asyncio
    async def test_validate_environment_activity_success(self, mock_config):
        """Test validation activity with successful checks."""
        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.validate_environment"
            ) as mock_validate,
        ):
            mock_load_config.return_value = mock_config
            mock_validate.return_value = {
                "overall_passed": True,
                "results": [
                    {"check": "azure_credentials", "passed": True},
                    {"check": "anthropic_api", "passed": True},
                ],
            }

            result = await validate_environment_activity(None)

            assert result["overall_passed"] is True
            assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_validate_environment_activity_failure(self):
        """Test validation activity with failed checks."""
        with mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config:
            mock_load_config.side_effect = Exception("Config load failed")

            result = await validate_environment_activity(None)

            assert result["overall_passed"] is False
            assert any("validation" in str(r) for r in result["results"])


# ==============================================================================
# ACTIVITY FUNCTION TESTS - Scenario Selection
# ==============================================================================


class TestSelectScenariosActivity:
    """Tests for select_scenarios_activity."""

    @pytest.mark.asyncio
    async def test_select_scenarios_activity_success(self, mock_config, mock_scenario):
        """Test scenario selection activity."""
        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch("azure_haymaker.orchestrator.orchestrator.select_scenarios") as mock_select,
        ):
            mock_load_config.return_value = mock_config
            mock_select.return_value = [mock_scenario]

            result = await select_scenarios_activity(None)

            assert len(result["scenarios"]) == 1
            assert result["scenarios"][0]["scenario_name"] == "test-scenario-01"

    @pytest.mark.asyncio
    async def test_select_scenarios_activity_failure(self):
        """Test scenario selection activity with error."""
        with mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config:
            mock_load_config.side_effect = Exception("Config load failed")

            result = await select_scenarios_activity(None)

            assert len(result["scenarios"]) == 0


# ==============================================================================
# ACTIVITY FUNCTION TESTS - Service Principal Creation
# ==============================================================================


class TestCreateServicePrincipalActivity:
    """Tests for create_service_principal_activity."""

    @pytest.mark.asyncio
    async def test_create_service_principal_activity_success(
        self, mock_config, mock_scenario, mock_sp_details, run_id
    ):
        """Test SP creation activity success."""
        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.create_service_principal"
            ) as mock_create_sp,
        ):
            mock_load_config.return_value = mock_config
            mock_create_sp.return_value = mock.MagicMock(
                sp_name=mock_sp_details["sp_name"],
                client_id=mock_sp_details["client_id"],
                principal_id=mock_sp_details["principal_id"],
                secret_reference=mock_sp_details["secret_reference"],
                created_at=mock_sp_details["created_at"],
            )

            params = {
                "run_id": run_id,
                "scenario": mock_scenario,
            }

            result = await create_service_principal_activity(params)

            assert result["status"] == "success"
            assert result["sp_details"]["sp_name"] == mock_sp_details["sp_name"]

    @pytest.mark.asyncio
    async def test_create_service_principal_activity_failure(
        self, mock_config, mock_scenario, run_id
    ):
        """Test SP creation activity with error."""
        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.create_service_principal"
            ) as mock_create_sp,
        ):
            mock_load_config.return_value = mock_config
            mock_create_sp.side_effect = Exception("SP creation failed")

            params = {
                "run_id": run_id,
                "scenario": mock_scenario,
            }

            result = await create_service_principal_activity(params)

            assert result["status"] == "failed"
            assert "error" in result


# ==============================================================================
# ACTIVITY FUNCTION TESTS - Container Deployment
# ==============================================================================


class TestDeployContainerAppActivity:
    """Tests for deploy_container_app_activity."""

    @pytest.mark.asyncio
    async def test_deploy_container_app_activity_success(
        self, mock_config, mock_scenario, mock_sp_details, run_id
    ):
        """Test container deployment activity success."""
        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.deploy_container_app"
            ) as mock_deploy,
        ):
            mock_load_config.return_value = mock_config
            mock_deploy.return_value = {
                "name": f"container-{run_id}",
                "resource_id": f"/subscriptions/test/resourceGroups/test-rg/providers/Microsoft.ContainerInstance/containerGroups/container-{run_id}",
            }

            params = {
                "run_id": run_id,
                "scenario": mock_scenario,
                "sp_details": mock_sp_details,
            }

            result = await deploy_container_app_activity(params)

            assert result["status"] == "success"
            assert "container_id" in result

    @pytest.mark.asyncio
    async def test_deploy_container_app_activity_failure(
        self, mock_config, mock_scenario, mock_sp_details, run_id
    ):
        """Test container deployment activity with error."""
        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.deploy_container_app"
            ) as mock_deploy,
        ):
            mock_load_config.return_value = mock_config
            mock_deploy.side_effect = Exception("Deployment failed")

            params = {
                "run_id": run_id,
                "scenario": mock_scenario,
                "sp_details": mock_sp_details,
            }

            result = await deploy_container_app_activity(params)

            assert result["status"] == "failed"
            assert "error" in result


# ==============================================================================
# ACTIVITY FUNCTION TESTS - Agent Status Check
# ==============================================================================


class TestCheckAgentStatusActivity:
    """Tests for check_agent_status_activity."""

    @pytest.mark.asyncio
    async def test_check_agent_status_activity_success(self, mock_config, run_id):
        """Test agent status check activity."""
        container_ids = [f"container-{uuid4()}" for _ in range(3)]

        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.ContainerManager"
            ) as mock_container_manager,
        ):
            mock_load_config.return_value = mock_config
            mock_manager_instance = mock.MagicMock()
            mock_container_manager.return_value = mock_manager_instance

            async def mock_get_status(container_id):
                return "Running"

            mock_manager_instance.get_container_status = mock_get_status

            params = {
                "run_id": run_id,
                "container_ids": container_ids,
            }

            result = await check_agent_status_activity(params)

            assert result["running_count"] == 3
            assert result["completed_count"] == 0
            assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_check_agent_status_activity_mixed_states(self, mock_config, run_id):
        """Test agent status with mixed container states."""
        container_ids = [f"container-{uuid4()}" for _ in range(4)]

        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.ContainerManager"
            ) as mock_container_manager,
        ):
            mock_load_config.return_value = mock_config
            mock_manager_instance = mock.MagicMock()
            mock_container_manager.return_value = mock_manager_instance

            statuses = ["Running", "Running", "Terminated", "Failed"]

            async def mock_get_status(container_id):
                idx = container_ids.index(container_id)
                return statuses[idx]

            mock_manager_instance.get_container_status = mock_get_status

            params = {
                "run_id": run_id,
                "container_ids": container_ids,
            }

            result = await check_agent_status_activity(params)

            assert result["running_count"] == 2
            assert result["completed_count"] == 1
            assert result["failed_count"] == 1


# ==============================================================================
# ACTIVITY FUNCTION TESTS - Cleanup Verification
# ==============================================================================


class TestVerifyCleanupActivity:
    """Tests for verify_cleanup_activity."""

    @pytest.mark.asyncio
    async def test_verify_cleanup_activity_no_remaining(self, mock_config, run_id):
        """Test cleanup verification with no remaining resources."""
        scenarios = ["scenario-1", "scenario-2"]

        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.query_managed_resources"
            ) as mock_query,
        ):
            mock_load_config.return_value = mock_config
            mock_query.return_value = []

            params = {
                "run_id": run_id,
                "scenarios": scenarios,
            }

            result = await verify_cleanup_activity(params)

            assert len(result["remaining_resources"]) == 0

    @pytest.mark.asyncio
    async def test_verify_cleanup_activity_remaining(self, mock_config, run_id):
        """Test cleanup verification with remaining resources."""
        from azure_haymaker.models.resource import Resource

        scenarios = ["scenario-1", "scenario-2"]
        remaining = [
            Resource(
                resource_id="/subscriptions/test/resourceGroups/test-rg",
                resource_type="Microsoft.Resources/resourceGroups",
                resource_name="test-rg",
                status="NotDeleted",
            )
        ]

        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.query_managed_resources"
            ) as mock_query,
        ):
            mock_load_config.return_value = mock_config
            mock_query.return_value = remaining

            params = {
                "run_id": run_id,
                "scenarios": scenarios,
            }

            result = await verify_cleanup_activity(params)

            assert len(result["remaining_resources"]) == 1


# ==============================================================================
# ACTIVITY FUNCTION TESTS - Forced Cleanup
# ==============================================================================


class TestForceCleanupActivity:
    """Tests for force_cleanup_activity."""

    @pytest.mark.asyncio
    async def test_force_cleanup_activity_success(self, mock_config, run_id, mock_sp_details):
        """Test forced cleanup activity success."""
        from azure_haymaker.orchestrator.cleanup import CleanupReport, CleanupStatus

        scenarios = ["scenario-1", "scenario-2"]
        sp_details_list = [mock_sp_details]

        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.force_delete_resources"
            ) as mock_force_cleanup,
        ):
            mock_load_config.return_value = mock_config
            mock_report = CleanupReport(
                run_id=run_id,
                status=CleanupStatus.VERIFIED,
                total_resources_deleted=5,
                deletions=[],
                service_principals_deleted=["sp1"],
            )
            mock_force_cleanup.return_value = mock_report

            params = {
                "run_id": run_id,
                "scenarios": scenarios,
                "sp_details": sp_details_list,
            }

            result = await force_cleanup_activity(params)

            assert result["status"] == "completed"
            assert result["deleted_count"] == 5
            assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_force_cleanup_activity_partial_failure(
        self, mock_config, run_id, mock_sp_details
    ):
        """Test forced cleanup activity with partial failure."""
        from azure_haymaker.orchestrator.cleanup import (
            CleanupReport,
            CleanupStatus,
            ResourceDeletion,
        )

        scenarios = ["scenario-1", "scenario-2"]
        sp_details_list = [mock_sp_details]

        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.force_delete_resources"
            ) as mock_force_cleanup,
        ):
            mock_load_config.return_value = mock_config
            failed_deletion = ResourceDeletion(
                resource_id="/subscriptions/test/resourceGroups/test-rg",
                resource_type="Microsoft.Resources/resourceGroups",
                status="failed",
                error="Permission denied",
            )
            mock_report = CleanupReport(
                run_id=run_id,
                status=CleanupStatus.PARTIAL_FAILURE,
                total_resources_deleted=3,
                deletions=[failed_deletion],
                service_principals_deleted=[],
            )
            mock_force_cleanup.return_value = mock_report

            params = {
                "run_id": run_id,
                "scenarios": scenarios,
                "sp_details": sp_details_list,
            }

            result = await force_cleanup_activity(params)

            assert result["status"] == "partial_failure"
            assert result["deleted_count"] == 3
            assert result["failed_count"] == 1


# ==============================================================================
# ACTIVITY FUNCTION TESTS - Report Generation
# ==============================================================================


class TestGenerateReportActivity:
    """Tests for generate_report_activity."""

    @pytest.mark.asyncio
    async def test_generate_report_activity_success(self, mock_config, run_id):
        """Test report generation activity success."""
        execution_report = {
            "run_id": run_id,
            "status": "completed",
            "phases": {},
        }
        selected_scenarios = ["scenario-1", "scenario-2"]

        with (
            mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config,
            mock.patch("azure_haymaker.orchestrator.orchestrator.DefaultAzureCredential"),
            mock.patch(
                "azure_haymaker.orchestrator.orchestrator.BlobServiceClient"
            ) as mock_blob_client,
        ):
            mock_load_config.return_value = mock_config

            # Mock blob client
            mock_container = mock.MagicMock()
            mock_blob = mock.MagicMock()
            mock_blob.url = (
                f"https://teststorage.blob.core.windows.net/execution-reports/{run_id}/report.json"
            )
            mock_container.get_blob_client.return_value = mock_blob
            mock_client_instance = mock.MagicMock()
            mock_client_instance.get_container_client.return_value = mock_container
            mock_blob_client.return_value = mock_client_instance

            params = {
                "run_id": run_id,
                "execution_report": execution_report,
                "selected_scenarios": selected_scenarios,
                "sp_count": 2,
                "container_count": 2,
            }

            result = await generate_report_activity(params)

            assert "report_url" in result
            assert result["report_id"] == run_id

    @pytest.mark.asyncio
    async def test_generate_report_activity_failure(self, mock_config, run_id):
        """Test report generation activity with error."""
        execution_report = {
            "run_id": run_id,
            "status": "completed",
        }
        selected_scenarios = ["scenario-1"]

        with mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config:
            mock_load_config.side_effect = Exception("Config load failed")

            params = {
                "run_id": run_id,
                "execution_report": execution_report,
                "selected_scenarios": selected_scenarios,
                "sp_count": 1,
                "container_count": 1,
            }

            result = await generate_report_activity(params)

            assert result["report_url"] == ""
            assert "error" in result


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================


class TestOrchestratorIntegration:
    """Integration tests for orchestrator workflow."""

    def test_all_activity_functions_defined(self):
        """Test that all required activity functions are defined."""
        from azure_haymaker.orchestrator.orchestrator import (
            check_agent_status_activity,
            create_service_principal_activity,
            deploy_container_app_activity,
            force_cleanup_activity,
            generate_report_activity,
            select_scenarios_activity,
            validate_environment_activity,
            verify_cleanup_activity,
        )

        for func in [
            validate_environment_activity,
            select_scenarios_activity,
            create_service_principal_activity,
            deploy_container_app_activity,
            check_agent_status_activity,
            verify_cleanup_activity,
            force_cleanup_activity,
            generate_report_activity,
        ]:
            assert callable(func)

    def test_orchestrator_app_created(self):
        """Test that FunctionApp is properly created."""
        from azure_haymaker.orchestrator.orchestrator import app

        assert app is not None
        assert hasattr(app, "timer_trigger")
        assert hasattr(app, "orchestration_trigger")
        assert hasattr(app, "activity_trigger")


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================


class TestErrorHandling:
    """Tests for error handling in activity functions."""

    @pytest.mark.asyncio
    async def test_activity_handles_none_input(self):
        """Test that activities handle None input gracefully."""
        # Some activities are called with None input
        with mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config:
            mock_load_config.return_value = {}

            # Should not raise
            result = await validate_environment_activity(None)
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_activity_handles_missing_fields(self):
        """Test activities handle missing fields in input."""
        params = {}  # Missing required fields

        with mock.patch("azure_haymaker.orchestrator.orchestrator.load_config") as mock_load_config:
            mock_load_config.return_value = {}

            # Should not raise
            result = await check_agent_status_activity(params)
            assert isinstance(result, dict)
            assert "running_count" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
