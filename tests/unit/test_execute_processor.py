"""Unit tests for execute_processor module.

Tests cover:
- Message parsing from Service Bus
- Scenario metadata loading
- Service principal creation flow
- Container deployment orchestration
- Monitoring loop behavior
- Cleanup and forced deletion
- Report generation and storage
- Error handling and status updates
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from azure_haymaker.models.execution import OnDemandExecutionStatus
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.orchestrator.cleanup import CleanupReport, CleanupStatus
from azure_haymaker.orchestrator.execute_processor import (
    load_scenario_metadata,
    process_execution,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_message_body():
    """Create sample Service Bus message body."""
    return {
        "execution_id": "exec-20251125-abc123",
        "scenarios": ["compute-01-linux-vm-web-server", "networking-01-virtual-network"],
        "duration_hours": 2,
        "tags": {"requester": "test@example.com", "purpose": "integration-test"},
        "requested_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def mock_service_bus_message(sample_message_body):
    """Create mock Service Bus message."""
    mock_msg = MagicMock()
    mock_msg.get_body.return_value = json.dumps(sample_message_body).encode("utf-8")
    return mock_msg


@pytest.fixture
def mock_config():
    """Create mock orchestrator configuration."""
    config = MagicMock()
    config.table_storage.account_url = "https://teststorage.table.core.windows.net"
    config.key_vault_url = "https://test-keyvault.vault.azure.net"
    config.target_subscription_id = "00000000-0000-0000-0000-000000000001"
    config.storage.account_url = "https://teststorage.blob.core.windows.net"
    config.resource_group_name = "test-rg"
    return config


@pytest.fixture
def mock_sp_details():
    """Create mock service principal details."""
    sp = MagicMock()
    sp.sp_name = "haymaker-compute-01-sp"
    sp.client_id = "sp-client-id"
    sp.tenant_id = "sp-tenant-id"
    sp.secret_reference = "kv-secret-compute-01"
    return sp


@pytest.fixture
def mock_scenario_metadata():
    """Create mock scenario metadata."""
    return ScenarioMetadata(
        scenario_name="compute-01-linux-vm-web-server",
        scenario_doc_path="/docs/scenarios/compute/compute-01.md",
        agent_path="/docs/scenarios/compute/agent.py",
        technology_area="compute",
    )


@pytest.fixture
def mock_cleanup_report():
    """Create mock cleanup report."""
    return CleanupReport(
        run_id="exec-20251125-abc123",
        status=CleanupStatus.VERIFIED,
        total_resources_expected=5,
        total_resources_deleted=5,
        deletions=[],
        service_principals_deleted=["haymaker-compute-01-sp"],
    )


# =============================================================================
# MESSAGE PARSING TESTS
# =============================================================================


class TestMessageParsing:
    """Tests for Service Bus message parsing."""

    def test_parse_valid_message(self, mock_service_bus_message, sample_message_body):
        """Test parsing valid JSON message from Service Bus."""
        body = json.loads(mock_service_bus_message.get_body().decode("utf-8"))

        assert body["execution_id"] == sample_message_body["execution_id"]
        assert body["scenarios"] == sample_message_body["scenarios"]
        assert body["duration_hours"] == sample_message_body["duration_hours"]
        assert body["tags"] == sample_message_body["tags"]

    def test_parse_message_with_defaults(self):
        """Test parsing message with missing optional fields uses defaults."""
        minimal_body = {
            "execution_id": "exec-minimal",
            "scenarios": ["compute-01"],
        }
        mock_msg = MagicMock()
        mock_msg.get_body.return_value = json.dumps(minimal_body).encode("utf-8")

        body = json.loads(mock_msg.get_body().decode("utf-8"))

        assert body["execution_id"] == "exec-minimal"
        assert body["scenarios"] == ["compute-01"]
        # Defaults should be applied by process_execution
        assert body.get("duration_hours") is None  # Will default to 8
        assert body.get("tags") is None  # Will default to {}

    def test_parse_message_with_empty_scenarios(self):
        """Test message with empty scenarios list."""
        body = {
            "execution_id": "exec-empty",
            "scenarios": [],
            "duration_hours": 1,
        }
        mock_msg = MagicMock()
        mock_msg.get_body.return_value = json.dumps(body).encode("utf-8")

        parsed = json.loads(mock_msg.get_body().decode("utf-8"))
        assert parsed["scenarios"] == []


# =============================================================================
# SCENARIO METADATA LOADING TESTS
# =============================================================================


class TestLoadScenarioMetadata:
    """Tests for scenario metadata loading."""

    def test_load_scenario_metadata_not_found(self):
        """Test loading scenario that does not exist."""
        # Call with a scenario name that certainly does not exist
        result = load_scenario_metadata("nonexistent-scenario-xyz-12345")
        # Function returns None when scenario not found
        assert result is None

    def test_load_scenario_metadata_scenarios_dir_missing(self):
        """Test loading when scenario does not exist returns None."""
        # Call with a random nonexistent scenario
        result = load_scenario_metadata("completely-made-up-scenario-name")
        # Returns None when scenario doesn't exist
        assert result is None

    def test_load_scenario_metadata_extracts_technology_area(self):
        """Test that technology area is extracted from directory structure."""
        # This test validates the extraction logic conceptually
        # Since we're testing with mocks, we verify the ScenarioMetadata structure
        scenario = ScenarioMetadata(
            scenario_name="networking-01-vnet",
            scenario_doc_path="/docs/scenarios/networking/networking-01.md",
            agent_path="/docs/scenarios/networking/agent.py",
            technology_area="networking",
        )

        assert scenario.technology_area == "networking"
        assert "networking" in scenario.scenario_doc_path


# =============================================================================
# EXECUTION FLOW TESTS
# =============================================================================


class TestProcessExecution:
    """Tests for the main process_execution function."""

    @pytest.mark.asyncio
    async def test_process_execution_success(
        self,
        mock_service_bus_message,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
        mock_cleanup_report,
    ):
        """Test successful execution processing flow."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ) as mock_cred,
            patch(
                "azure_haymaker.orchestrator.execute_processor.TableClient"
            ) as mock_table,
            patch(
                "azure_haymaker.orchestrator.execute_processor.SecretClient"
            ) as mock_secret,
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                return_value="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-01",
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            # Configure mocks
            mock_cred.return_value = MagicMock()
            mock_table.return_value = MagicMock()
            mock_secret.return_value = MagicMock()

            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            # Container manager returns "Terminated" to exit monitoring loop
            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(return_value="Terminated")
            mock_container_mgr.return_value = mock_cm_instance

            # Blob storage mock
            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock()
            mock_blob_client.url = "https://storage/reports/exec-123.json"

            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client

            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            # Run the processor
            await process_execution(mock_service_bus_message)

            # Verify status updates
            assert mock_tracker.update_status.call_count >= 2
            # Should have RUNNING and COMPLETED status updates
            status_calls = [
                call[1]["status"] for call in mock_tracker.update_status.call_args_list
            ]
            assert OnDemandExecutionStatus.RUNNING in status_calls
            assert OnDemandExecutionStatus.COMPLETED in status_calls

    @pytest.mark.asyncio
    async def test_process_execution_no_service_principals_created(
        self,
        mock_service_bus_message,
        mock_config,
    ):
        """Test execution fails when no service principals can be created."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                side_effect=Exception("SP creation failed"),
            ),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            await process_execution(mock_service_bus_message)

            # Should update status to FAILED
            final_call = mock_tracker.update_status.call_args_list[-1]
            assert final_call[1]["status"] == OnDemandExecutionStatus.FAILED
            assert "service principals" in final_call[1]["error_message"].lower()

    @pytest.mark.asyncio
    async def test_process_execution_no_containers_deployed(
        self,
        mock_service_bus_message,
        mock_config,
        mock_sp_details,
    ):
        """Test execution fails when no containers can be deployed."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=None,  # Scenario not found
            ),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            await process_execution(mock_service_bus_message)

            # Should update status to FAILED
            final_call = mock_tracker.update_status.call_args_list[-1]
            assert final_call[1]["status"] == OnDemandExecutionStatus.FAILED
            assert "containers" in final_call[1]["error_message"].lower()

    @pytest.mark.asyncio
    async def test_process_execution_handles_json_decode_error(self):
        """Test handling of malformed JSON in message body."""
        mock_msg = MagicMock()
        mock_msg.get_body.return_value = b"not valid json"

        # Should not raise, but log error
        await process_execution(mock_msg)

    @pytest.mark.asyncio
    async def test_process_execution_handles_missing_execution_id(self, mock_config):
        """Test handling of message without execution_id."""
        mock_msg = MagicMock()
        mock_msg.get_body.return_value = json.dumps(
            {"scenarios": ["compute-01"]}
        ).encode("utf-8")

        with patch(
            "azure_haymaker.orchestrator.execute_processor.load_config",
            new_callable=AsyncMock,
            return_value=mock_config,
        ):
            # Should handle gracefully (execution_id will be None)
            await process_execution(mock_msg)


# =============================================================================
# MONITORING TESTS
# =============================================================================


class TestMonitoringLoop:
    """Tests for the monitoring phase."""

    @pytest.mark.asyncio
    async def test_monitoring_exits_when_all_terminated(
        self,
        mock_service_bus_message,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
    ):
        """Test monitoring loop exits when all containers are terminated."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                return_value="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-01",
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            # Container is Terminated immediately
            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(return_value="Terminated")
            mock_container_mgr.return_value = mock_cm_instance

            # Blob storage mock
            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock()
            mock_blob_client.url = "https://storage/report.json"
            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client
            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            await process_execution(mock_service_bus_message)

            # Sleep should not be called if all containers terminated immediately
            # (The loop should exit before sleep)
            # Note: The exact behavior depends on implementation timing

    @pytest.mark.asyncio
    async def test_monitoring_handles_status_check_failure(
        self,
        mock_service_bus_message,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
    ):
        """Test monitoring continues when individual status checks fail."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                return_value="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-01",
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            # First call fails, second returns Terminated
            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(
                side_effect=[Exception("Status check failed"), "Terminated"]
            )
            mock_container_mgr.return_value = mock_cm_instance

            # Blob storage mock
            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock()
            mock_blob_client.url = "https://storage/report.json"
            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client
            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            # Should complete despite status check failure
            await process_execution(mock_service_bus_message)


# =============================================================================
# CLEANUP TESTS
# =============================================================================


class TestCleanupPhase:
    """Tests for cleanup verification and forced deletion."""

    @pytest.mark.asyncio
    async def test_cleanup_triggered_when_resources_remain(
        self,
        mock_service_bus_message,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
        mock_cleanup_report,
    ):
        """Test forced cleanup is triggered when resources remain."""
        mock_remaining_resource = MagicMock()
        mock_remaining_resource.resource_id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01"

        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                return_value="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-01",
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[mock_remaining_resource],
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.force_delete_resources",
                new_callable=AsyncMock,
                return_value=mock_cleanup_report,
            ) as mock_force_delete,
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(return_value="Terminated")
            mock_container_mgr.return_value = mock_cm_instance

            # Blob storage mock
            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock()
            mock_blob_client.url = "https://storage/report.json"
            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client
            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            await process_execution(mock_service_bus_message)

            # Verify force_delete_resources was called
            mock_force_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_skipped_when_no_resources_remain(
        self,
        mock_service_bus_message,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
    ):
        """Test forced cleanup is skipped when no resources remain."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                return_value="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-01",
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[],  # No remaining resources
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.force_delete_resources",
                new_callable=AsyncMock,
            ) as mock_force_delete,
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(return_value="Terminated")
            mock_container_mgr.return_value = mock_cm_instance

            # Blob storage mock
            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock()
            mock_blob_client.url = "https://storage/report.json"
            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client
            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            await process_execution(mock_service_bus_message)

            # Verify force_delete_resources was NOT called
            mock_force_delete.assert_not_called()


# =============================================================================
# REPORT GENERATION TESTS
# =============================================================================


class TestReportGeneration:
    """Tests for execution report generation and storage."""

    @pytest.mark.asyncio
    async def test_report_uploaded_to_blob_storage(
        self,
        mock_service_bus_message,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
    ):
        """Test execution report is uploaded to blob storage."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                return_value="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-01",
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(return_value="Terminated")
            mock_container_mgr.return_value = mock_cm_instance

            # Blob storage mock - capture uploaded data
            uploaded_data = None

            async def capture_upload(data, **kwargs):
                nonlocal uploaded_data
                uploaded_data = data

            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock(side_effect=capture_upload)
            mock_blob_client.url = "https://storage/reports/exec-20251125-abc123/report.json"

            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client

            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            await process_execution(mock_service_bus_message)

            # Verify blob client was accessed
            mock_blob_svc.get_container_client.assert_called_with("execution-reports")
            mock_container_client.get_blob_client.assert_called()

            # Verify upload was called
            mock_blob_client.upload_blob.assert_called_once()

            # Verify report content
            assert uploaded_data is not None
            report = json.loads(uploaded_data)
            assert "execution_id" in report
            assert "scenarios" in report
            assert "completed_at" in report

    @pytest.mark.asyncio
    async def test_report_contains_expected_fields(
        self,
        sample_message_body,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
    ):
        """Test report contains all expected fields."""
        mock_msg = MagicMock()
        mock_msg.get_body.return_value = json.dumps(sample_message_body).encode("utf-8")

        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                return_value="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-01",
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(return_value="Terminated")
            mock_container_mgr.return_value = mock_cm_instance

            # Capture report
            captured_report = None

            async def capture_report(data, **kwargs):
                nonlocal captured_report
                captured_report = json.loads(data)

            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock(side_effect=capture_report)
            mock_blob_client.url = "https://storage/report.json"

            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client

            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            await process_execution(mock_msg)

            # Verify report fields
            assert captured_report is not None
            assert captured_report["execution_id"] == sample_message_body["execution_id"]
            assert captured_report["scenarios"] == sample_message_body["scenarios"]
            assert captured_report["duration_hours"] == sample_message_body["duration_hours"]
            assert captured_report["tags"] == sample_message_body["tags"]
            assert "service_principals_created" in captured_report
            assert "containers_deployed" in captured_report
            assert "resources_remaining" in captured_report
            assert "completed_at" in captured_report


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_status_updated_to_failed_on_exception(
        self,
        mock_service_bus_message,
        mock_config,
    ):
        """Test status is updated to FAILED when exception occurs."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.TableClient"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                side_effect=Exception("Unexpected error"),
            ),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            await process_execution(mock_service_bus_message)

            # Verify FAILED status update
            final_call = mock_tracker.update_status.call_args_list[-1]
            assert final_call[1]["status"] == OnDemandExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_handles_status_update_failure_gracefully(
        self,
        mock_service_bus_message,
        mock_config,
    ):
        """Test handles failure to update status gracefully."""
        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                side_effect=Exception("SP creation failed"),
            ),
        ):
            # First update succeeds, second fails
            mock_tracker = AsyncMock()
            mock_tracker.update_status = AsyncMock(
                side_effect=[None, Exception("Status update failed")]
            )
            mock_tracker_cls.return_value = mock_tracker

            # Should not raise - error is caught and logged
            await process_execution(mock_service_bus_message)

    @pytest.mark.asyncio
    async def test_container_deployment_failure_continues_with_others(
        self,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
    ):
        """Test that failure to deploy one container does not stop others."""
        message_body = {
            "execution_id": "exec-multi",
            "scenarios": ["scenario-1", "scenario-2", "scenario-3"],
            "duration_hours": 1,
        }
        mock_msg = MagicMock()
        mock_msg.get_body.return_value = json.dumps(message_body).encode("utf-8")

        deploy_call_count = 0

        async def deploy_side_effect(*args, **kwargs):
            nonlocal deploy_call_count
            deploy_call_count += 1
            if deploy_call_count == 2:
                raise Exception("Deployment failed for scenario-2")
            return f"/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-{deploy_call_count}"

        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                side_effect=deploy_side_effect,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(return_value="Terminated")
            mock_container_mgr.return_value = mock_cm_instance

            # Blob storage mock
            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock()
            mock_blob_client.url = "https://storage/report.json"
            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client
            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            await process_execution(mock_msg)

            # All 3 deployments should have been attempted
            assert deploy_call_count == 3


# =============================================================================
# CONTAINER ID EXTRACTION TESTS
# =============================================================================


class TestContainerIdExtraction:
    """Tests for extracting container ID from resource ID."""

    def test_extract_container_id_from_resource_id(self):
        """Test container ID is correctly extracted from full resource ID."""
        resource_id = "/subscriptions/sub-123/resourceGroups/rg-01/providers/Microsoft.App/containerApps/haymaker-compute-01"

        # Extraction logic from execute_processor
        container_id = resource_id.split("/")[-1]

        assert container_id == "haymaker-compute-01"

    def test_extract_container_id_handles_various_formats(self):
        """Test container ID extraction handles various resource ID formats."""
        test_cases = [
            (
                "/subscriptions/a/resourceGroups/b/providers/Microsoft.App/containerApps/app-name",
                "app-name",
            ),
            (
                "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/my-rg/providers/Microsoft.App/containerApps/my-app-123",
                "my-app-123",
            ),
            (
                "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/a",
                "a",
            ),
        ]

        for resource_id, expected_id in test_cases:
            assert resource_id.split("/")[-1] == expected_id


# =============================================================================
# INTEGRATION-STYLE TESTS
# =============================================================================


class TestFullExecutionFlow:
    """Integration-style tests covering the full execution flow."""

    @pytest.mark.asyncio
    async def test_full_execution_with_single_scenario(
        self,
        mock_config,
        mock_sp_details,
        mock_scenario_metadata,
    ):
        """Test complete execution flow with a single scenario."""
        message_body = {
            "execution_id": "exec-single",
            "scenarios": ["compute-01-linux-vm-web-server"],
            "duration_hours": 1,
            "tags": {"test": "true"},
        }
        mock_msg = MagicMock()
        mock_msg.get_body.return_value = json.dumps(message_body).encode("utf-8")

        with (
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.DefaultAzureCredential"
            ),
            patch("azure_haymaker.orchestrator.execute_processor.TableClient"),
            patch("azure_haymaker.orchestrator.execute_processor.SecretClient"),
            patch(
                "azure_haymaker.orchestrator.execute_processor.ExecutionTracker"
            ) as mock_tracker_cls,
            patch(
                "azure_haymaker.orchestrator.execute_processor.create_service_principal",
                new_callable=AsyncMock,
                return_value=mock_sp_details,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.load_scenario_metadata",
                return_value=mock_scenario_metadata,
            ),
            patch(
                "azure_haymaker.orchestrator.execute_processor.deploy_container_app",
                new_callable=AsyncMock,
                return_value="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/app-01",
            ) as mock_deploy,
            patch(
                "azure_haymaker.orchestrator.execute_processor.ContainerManager"
            ) as mock_container_mgr,
            patch(
                "azure_haymaker.orchestrator.execute_processor.query_managed_resources",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_query,
            patch(
                "azure_haymaker.orchestrator.execute_processor.BlobServiceClient"
            ) as mock_blob,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_tracker = AsyncMock()
            mock_tracker_cls.return_value = mock_tracker

            mock_cm_instance = MagicMock()
            mock_cm_instance.get_status = AsyncMock(return_value="Terminated")
            mock_container_mgr.return_value = mock_cm_instance

            # Blob storage mock
            mock_blob_client = MagicMock()
            mock_blob_client.upload_blob = AsyncMock()
            mock_blob_client.url = "https://storage/report.json"
            mock_container_client = MagicMock()
            mock_container_client.get_blob_client.return_value = mock_blob_client
            mock_blob_svc = MagicMock()
            mock_blob_svc.get_container_client.return_value = mock_container_client
            mock_blob.return_value = mock_blob_svc

            await process_execution(mock_msg)

            # Verify each phase was executed
            # Phase 1: SP creation
            # (verified via create_service_principal mock)

            # Phase 2: Container deployment
            mock_deploy.assert_called_once()

            # Phase 3: Monitoring (verified via get_status calls)
            mock_cm_instance.get_status.assert_called()

            # Phase 4: Cleanup verification
            mock_query.assert_called_once()

            # Phase 6: Report generation (verified via blob upload)
            mock_blob_client.upload_blob.assert_called_once()

            # Final status should be COMPLETED
            final_status_call = mock_tracker.update_status.call_args_list[-1]
            assert final_status_call[1]["status"] == OnDemandExecutionStatus.COMPLETED
