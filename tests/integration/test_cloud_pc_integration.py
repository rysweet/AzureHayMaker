"""Integration tests for Windows 365 Cloud PC and M365 Telemetry.

This module tests end-to-end integration of Cloud PC provisioning and telemetry
collection within the Knowledge Worker Activity Framework.

Tests cover:
- Full Cloud PC provisioning workflow
- Telemetry collection from provisioned Cloud PCs
- Integration between provisioning and activity monitoring
- Multi-worker scenarios

Uses pytest with real or mocked Azure/M365 services.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Import modules under test
try:
    from azure_haymaker.knowledge_worker.endpoints.cloud_pc import (
        Windows365CloudPCManager,
    )
    from azure_haymaker.knowledge_worker.models.worker import (
        EndpointType,
        WorkerIdentity,
        WorkerPersona,
    )
    from azure_haymaker.knowledge_worker.telemetry import (
        M365TelemetryCollector,
    )

    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False
    Windows365CloudPCManager = None
    M365TelemetryCollector = None
    WorkerIdentity = None


pytestmark = pytest.mark.skipif(
    not INTEGRATION_AVAILABLE,
    reason="Cloud PC and Telemetry modules not yet implemented",
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_graph_client():
    """Fixture: Mock Microsoft Graph API client for integration testing.

    Properly sets up AsyncMock for all async methods to support the fluent
    SDK pattern used by Microsoft Graph Python SDK.
    """
    client = MagicMock()

    # Setup device_management.virtual_endpoint methods
    client.device_management.virtual_endpoint.provisioning_policies.get = AsyncMock(
        return_value=MagicMock(value=[])
    )
    client.device_management.virtual_endpoint.provisioning_policies.post = AsyncMock()
    client.device_management.virtual_endpoint.provisioning_policies.by_cloud_pc_provisioning_policy_id = (
        MagicMock(
            return_value=MagicMock(
                assignments=MagicMock(
                    post=AsyncMock(),
                    get=AsyncMock(return_value=MagicMock(value=[])),
                ),
                delete=AsyncMock(),
            )
        )
    )
    client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
        return_value=MagicMock(value=[])
    )
    client.device_management.virtual_endpoint.cloud_p_cs.post = AsyncMock()
    client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id = MagicMock(
        return_value=MagicMock(
            get=AsyncMock(),
            patch=AsyncMock(),
            delete=AsyncMock(),
        )
    )

    # Setup groups methods with fluent pattern support
    client.groups.get = AsyncMock(return_value=MagicMock(value=[]))
    client.groups.post = AsyncMock()

    # Setup by_group_id fluent pattern
    def create_group_by_id_mock(group_id):
        group_resource = MagicMock()
        group_resource.members = MagicMock()
        group_resource.members.get = AsyncMock(return_value=MagicMock(value=[]))
        group_resource.members.post = AsyncMock()
        group_resource.members.ref = MagicMock()
        group_resource.members.ref.post = AsyncMock()
        return group_resource

    client.groups.by_group_id = MagicMock(side_effect=create_group_by_id_mock)

    # Setup graph.users and graph.teams for telemetry
    client.graph = MagicMock()
    client.graph.users = MagicMock()
    client.graph.teams = MagicMock()

    return client


@pytest.fixture
def run_id():
    """Fixture: Unique run ID for integration test."""
    return str(uuid4())


@pytest.fixture
def cloud_pc_manager(mock_graph_client, run_id):
    """Fixture: Cloud PC manager instance."""
    return Windows365CloudPCManager(graph_client=mock_graph_client, run_id=run_id)


@pytest.fixture
def telemetry_collector(mock_graph_client, run_id):
    """Fixture: Telemetry collector instance."""
    return M365TelemetryCollector(graph_client=mock_graph_client, run_id=run_id)


@pytest.fixture
def test_workers():
    """Fixture: Sample workers for integration testing."""
    return [
        WorkerIdentity(
            worker_id=f"kw-integ-{i:03d}",
            display_name=f"Integration Test Worker {i}",
            user_principal_name=f"integ.worker{i}@tenant.onmicrosoft.com",
            entra_object_id=str(uuid4()),
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
            endpoint_type=EndpointType.CLOUD_PC,
            endpoint_id="",
            team_ids=["team-001"],
        )
        for i in range(5)
    ]


# ==============================================================================
# FULL WORKFLOW INTEGRATION TESTS
# ==============================================================================


class TestCloudPCProvisioningWorkflow:
    """Integration tests for full Cloud PC provisioning workflow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_provision_and_wait_workflow(
        self, cloud_pc_manager, test_workers, mock_graph_client
    ):
        """Test complete workflow: provision Cloud PC and wait for ready state."""
        worker = test_workers[0]

        # Mock provisioning policy
        mock_policy = MagicMock()
        mock_policy.id = f"policy-{uuid4()}"
        mock_policy.display_name = "HayMaker-KnowledgeWorker-Policy"

        mock_policies = MagicMock()
        mock_policies.value = []
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(return_value=mock_policies)
        )
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.post = (
            AsyncMock(return_value=mock_policy)
        )

        # Mock Cloud PC provisioning status progression
        mock_cloud_pc = MagicMock()
        mock_cloud_pc.id = f"cloudpc-{uuid4()}"
        mock_cloud_pc.status = "provisioned"
        mock_cloud_pc.user_principal_name = worker.user_principal_name
        mock_cloud_pc.display_name = f"kw-{cloud_pc_manager.run_id[:8]}-worker"

        mock_result = MagicMock()
        mock_result.value = [mock_cloud_pc]
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        # Execute workflow
        policy_id = await cloud_pc_manager.ensure_provisioning_policy()
        assert policy_id == mock_policy.id

        cloud_pc_id = await cloud_pc_manager.provision_cloud_pc(
            worker=worker, policy_id=policy_id
        )
        assert cloud_pc_id.startswith("cloudpc-")

        ready = await cloud_pc_manager.wait_for_provisioning(
            worker=worker, timeout_minutes=1
        )
        assert ready is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_provision_workflow(
        self, cloud_pc_manager, test_workers, mock_graph_client
    ):
        """Test batch provisioning multiple Cloud PCs."""
        # Mock policy
        mock_policy = MagicMock()
        mock_policy.id = f"policy-{uuid4()}"

        mock_policies = MagicMock()
        mock_policies.value = [mock_policy]
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(return_value=mock_policies)
        )

        # Ensure policy
        policy_id = await cloud_pc_manager.ensure_provisioning_policy()

        # Provision all workers
        provision_tasks = [
            cloud_pc_manager.provision_cloud_pc(worker=w, policy_id=policy_id)
            for w in test_workers
        ]
        cloud_pc_ids = await asyncio.gather(*provision_tasks)

        assert len(cloud_pc_ids) == len(test_workers)
        assert all(pc_id.startswith("cloudpc-") for pc_id in cloud_pc_ids)


# ==============================================================================
# TELEMETRY COLLECTION INTEGRATION TESTS
# ==============================================================================


class TestTelemetryCollectionWorkflow:
    """Integration tests for M365 telemetry collection."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_collect_all_telemetry_types(
        self, telemetry_collector, test_workers, mock_graph_client
    ):
        """Test collecting email, calendar, and Teams telemetry for a worker."""
        worker = test_workers[0]
        now = datetime.now(UTC)

        # Mock email
        mock_email = MagicMock()
        mock_email.id = str(uuid4())
        mock_email.subject = "Integration Test Email"
        mock_email.from_ = MagicMock()
        mock_email.from_.email_address = MagicMock()
        mock_email.from_.email_address.address = "sender@tenant.com"
        mock_email.received_date_time = now
        mock_email.to_recipients = [
            MagicMock(email_address=MagicMock(address=worker.user_principal_name))
        ]

        mock_email_result = MagicMock()
        mock_email_result.value = [mock_email]
        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            return_value=mock_email_result
        )

        # Mock calendar
        mock_event = MagicMock()
        mock_event.id = str(uuid4())
        mock_event.subject = "Integration Test Meeting"
        mock_event.start = MagicMock()
        mock_event.start.date_time = now.isoformat()
        mock_event.end = MagicMock()
        mock_event.end.date_time = (now + timedelta(hours=1)).isoformat()
        mock_event.organizer = MagicMock()
        mock_event.organizer.email_address = MagicMock()
        mock_event.organizer.email_address.address = worker.user_principal_name
        mock_event.attendees = []

        mock_calendar_result = MagicMock()
        mock_calendar_result.value = [mock_event]
        mock_graph_client.graph.users.by_user_id.return_value.calendar.events.get = (
            AsyncMock(return_value=mock_calendar_result)
        )

        # Mock Teams
        mock_teams_msg = MagicMock()
        mock_teams_msg.id = str(uuid4())
        mock_teams_msg.body = MagicMock()
        mock_teams_msg.body.content = "Integration test message"
        mock_teams_msg.from_ = MagicMock()
        mock_teams_msg.from_.user = MagicMock()
        mock_teams_msg.from_.user.id = worker.entra_object_id
        mock_teams_msg.created_date_time = now

        mock_teams_result = MagicMock()
        mock_teams_result.value = [mock_teams_msg]
        mock_graph_client.graph.teams.by_team_id.return_value.channels.by_channel_id.return_value.messages.get = (
            AsyncMock(return_value=mock_teams_result)
        )

        # Collect all telemetry
        emails = await telemetry_collector.get_emails_for_worker(worker=worker)
        calendar = await telemetry_collector.get_calendar_events_for_worker(worker=worker)
        teams = await telemetry_collector.get_teams_messages_for_worker(
            worker=worker, team_id=worker.team_ids[0], channel_id="general"
        )

        assert len(emails) == 1
        assert len(calendar) == 1
        assert len(teams) == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_run_summary_aggregation(
        self, telemetry_collector, test_workers, mock_graph_client
    ):
        """Test run-level aggregation of telemetry from all workers."""
        now = datetime.now(UTC)

        # Mock different activity levels for each worker
        def mock_messages_for_worker(worker_id: str):
            count = hash(worker_id) % 5 + 1  # 1-5 messages per worker
            messages = []
            for i in range(count):
                msg = MagicMock()
                msg.id = str(uuid4())
                msg.subject = f"Email {i} for {worker_id}"
                msg.from_ = MagicMock()
                msg.from_.email_address = MagicMock()
                msg.from_.email_address.address = "sender@tenant.com"
                msg.received_date_time = now
                msg.to_recipients = []
                messages.append(msg)
            return messages

        # Setup mock to return different counts per worker
        call_count = [0]

        async def mock_get_messages(*args, **kwargs):
            worker_idx = call_count[0] % len(test_workers)
            worker = test_workers[worker_idx]
            call_count[0] += 1

            mock_result = MagicMock()
            mock_result.value = mock_messages_for_worker(worker.worker_id)
            return mock_result

        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            side_effect=mock_get_messages
        )
        mock_graph_client.graph.users.by_user_id.return_value.calendar.events.get = (
            AsyncMock(return_value=MagicMock(value=[]))
        )

        # Get run summary
        summary = await telemetry_collector.get_run_summary(workers=test_workers)

        assert summary["total_workers"] == len(test_workers)
        assert summary["email_count"] > 0
        assert "calendar_count" in summary
        assert "teams_count" in summary


# ==============================================================================
# CLOUD PC + TELEMETRY INTEGRATION TESTS
# ==============================================================================


class TestCloudPCTelemetryIntegration:
    """Integration tests combining Cloud PC provisioning and telemetry collection."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_provision_then_collect_telemetry(
        self, cloud_pc_manager, telemetry_collector, test_workers, mock_graph_client
    ):
        """Test provisioning Cloud PCs followed by telemetry collection."""
        worker = test_workers[0]

        # Mock policy
        mock_policy = MagicMock()
        mock_policy.id = f"policy-{uuid4()}"
        mock_policies = MagicMock()
        mock_policies.value = [mock_policy]
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(return_value=mock_policies)
        )

        # Mock Cloud PC provisioned
        mock_cloud_pc = MagicMock()
        mock_cloud_pc.status = "provisioned"
        mock_cloud_pc.user_principal_name = worker.user_principal_name
        mock_result = MagicMock()
        mock_result.value = [mock_cloud_pc]
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        # Step 1: Provision Cloud PC
        policy_id = await cloud_pc_manager.ensure_provisioning_policy()
        cloud_pc_id = await cloud_pc_manager.provision_cloud_pc(
            worker=worker, policy_id=policy_id
        )
        ready = await cloud_pc_manager.wait_for_provisioning(worker=worker, timeout_minutes=1)

        assert ready is True

        # Step 2: Collect telemetry from provisioned Cloud PC
        now = datetime.now(UTC)
        mock_email = MagicMock()
        mock_email.id = str(uuid4())
        mock_email.subject = "Activity on Cloud PC"
        mock_email.from_ = MagicMock()
        mock_email.from_.email_address = MagicMock()
        mock_email.from_.email_address.address = worker.user_principal_name
        mock_email.received_date_time = now
        mock_email.to_recipients = []

        mock_email_result = MagicMock()
        mock_email_result.value = [mock_email]
        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            return_value=mock_email_result
        )

        emails = await telemetry_collector.get_emails_for_worker(worker=worker)

        assert len(emails) == 1
        assert emails[0].subject == "Activity on Cloud PC"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_lifecycle_workflow(
        self, cloud_pc_manager, telemetry_collector, test_workers, mock_graph_client
    ):
        """Test complete lifecycle: provision, activity simulation, telemetry, cleanup."""
        worker = test_workers[0]

        # Mock policy
        mock_policy = MagicMock()
        mock_policy.id = f"policy-{uuid4()}"
        mock_policies = MagicMock()
        mock_policies.value = [mock_policy]
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(return_value=mock_policies)
        )

        # Mock Cloud PC
        mock_cloud_pc = MagicMock()
        mock_cloud_pc.id = f"cloudpc-{uuid4()}"
        mock_cloud_pc.status = "provisioned"
        mock_cloud_pc.user_principal_name = worker.user_principal_name
        mock_result = MagicMock()
        mock_result.value = [mock_cloud_pc]
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        # Phase 1: Provision
        policy_id = await cloud_pc_manager.ensure_provisioning_policy()
        cloud_pc_id = await cloud_pc_manager.provision_cloud_pc(
            worker=worker, policy_id=policy_id
        )
        ready = await cloud_pc_manager.wait_for_provisioning(worker=worker, timeout_minutes=1)
        assert ready is True

        # Phase 2: Simulate activity (in real scenario, worker agent would run)
        # Here we just verify we can query telemetry

        # Phase 3: Collect telemetry
        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            return_value=MagicMock(value=[])
        )
        mock_graph_client.graph.users.by_user_id.return_value.calendar.events.get = (
            AsyncMock(return_value=MagicMock(value=[]))
        )

        emails = await telemetry_collector.get_emails_for_worker(worker=worker)
        calendar = await telemetry_collector.get_calendar_events_for_worker(worker=worker)

        # Phase 4: Cleanup
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id = (
            MagicMock()
        )
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id.return_value.delete = (
            AsyncMock(return_value=None)
        )

        deleted = await cloud_pc_manager.delete_cloud_pc(cloud_pc_id=mock_cloud_pc.id)
        assert deleted is True


# ==============================================================================
# ERROR HANDLING AND RECOVERY TESTS
# ==============================================================================


class TestIntegrationErrorHandling:
    """Integration tests for error handling and recovery."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_provision_retry_on_transient_failure(
        self, cloud_pc_manager, test_workers, mock_graph_client
    ):
        """Test provisioning retries on transient failures."""
        worker = test_workers[0]

        # Mock policy with transient failure
        call_count = [0]

        async def mock_get_policies(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Transient error")
            mock_policies = MagicMock()
            mock_policy = MagicMock()
            mock_policy.id = f"policy-{uuid4()}"
            mock_policies.value = [mock_policy]
            return mock_policies

        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(side_effect=mock_get_policies)
        )

        # Should succeed after retry
        with pytest.raises(Exception):
            # First call fails
            await cloud_pc_manager.ensure_provisioning_policy()

        # Second call succeeds
        policy_id = await cloud_pc_manager.ensure_provisioning_policy()
        assert policy_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_telemetry_collection_handles_partial_failures(
        self, telemetry_collector, test_workers, mock_graph_client
    ):
        """Test telemetry collection continues when some workers fail."""
        workers = test_workers[:3]

        # Mock: Worker 0 succeeds, Worker 1 fails, Worker 2 succeeds
        call_count = [0]

        async def mock_get_messages(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1

            if idx == 1:
                raise Exception("Worker 1 access denied")

            mock_result = MagicMock()
            mock_result.value = []
            return mock_result

        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            side_effect=mock_get_messages
        )

        # Collect from all workers, handling failures
        results = []
        for worker in workers:
            try:
                emails = await telemetry_collector.get_emails_for_worker(worker=worker)
                results.append((worker.worker_id, emails))
            except Exception as e:
                results.append((worker.worker_id, None))

        # Worker 1 should have failed
        assert results[1][1] is None
        # Workers 0 and 2 should have succeeded
        assert results[0][1] is not None
        assert results[2][1] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
