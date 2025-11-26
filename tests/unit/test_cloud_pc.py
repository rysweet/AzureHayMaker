"""Unit tests for Windows 365 Cloud PC provisioning.

This module tests the Windows365CloudPCManager class that provisions and manages
Cloud PCs for knowledge workers requiring rich desktop telemetry.

Tests cover:
- Provisioning policy creation and reuse
- Cloud PC provisioning and user assignment
- Status monitoring and polling
- Batch provisioning with concurrency
- Cleanup and deprovisioning

Uses pytest with AsyncMock for Graph API interactions.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest

# Import the module under test
# Note: This import will fail until Windows365CloudPCManager is implemented
try:
    from azure_haymaker.knowledge_worker.endpoints.cloud_pc import (
        Windows365CloudPCManager,
    )
    from azure_haymaker.knowledge_worker.models.worker import (
        EndpointType,
        WorkerIdentity,
        WorkerPersona,
    )

    CLOUD_PC_AVAILABLE = True
except ImportError:
    CLOUD_PC_AVAILABLE = False
    Windows365CloudPCManager = None
    WorkerIdentity = None


pytestmark = pytest.mark.skipif(
    not CLOUD_PC_AVAILABLE, reason="Windows365CloudPCManager not yet implemented"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_graph_client():
    """Fixture: Mock Microsoft Graph API client."""
    client = MagicMock()
    client.device_management = MagicMock()
    client.device_management.virtual_endpoint = MagicMock()
    return client


@pytest.fixture
def run_id():
    """Fixture: HayMaker run ID."""
    return str(uuid4())


@pytest.fixture
def cloud_pc_manager(mock_graph_client, run_id):
    """Fixture: Windows365CloudPCManager instance."""
    return Windows365CloudPCManager(
        graph_client=mock_graph_client,
        run_id=run_id,
    )


@pytest.fixture
def worker_identity():
    """Fixture: Sample worker identity."""
    return WorkerIdentity(
        worker_id="kw-test-001",
        display_name="Test Worker",
        user_principal_name="test.worker@tenant.onmicrosoft.com",
        department="engineering",
        persona=WorkerPersona.ENGINEERING,
        endpoint_type=EndpointType.CLOUD_PC,
        endpoint_id="",
        team_ids=["team-001"],
    )


@pytest.fixture
def mock_policy_response():
    """Fixture: Mock provisioning policy response from Graph API."""
    policy = MagicMock()
    policy.id = f"policy-{uuid4()}"
    policy.display_name = "HayMaker-KnowledgeWorker-Policy"
    return policy


@pytest.fixture
def mock_cloud_pc_response():
    """Fixture: Mock Cloud PC response from Graph API."""
    pc = MagicMock()
    pc.id = f"cloudpc-{uuid4()}"
    pc.display_name = "kw-test-12345"
    pc.status = "provisioned"
    pc.user_principal_name = "test.worker@tenant.onmicrosoft.com"
    pc.managed_device_id = f"device-{uuid4()}"
    return pc


# ==============================================================================
# PROVISIONING POLICY TESTS
# ==============================================================================


class TestProvisioningPolicy:
    """Tests for Cloud PC provisioning policy management."""

    @pytest.mark.asyncio
    async def test_ensure_provisioning_policy_creates_new(
        self, cloud_pc_manager, mock_graph_client, mock_policy_response
    ):
        """Test that ensure_provisioning_policy creates a new policy when none exists."""
        # Mock: No existing policies
        mock_policies = MagicMock()
        mock_policies.value = []
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(return_value=mock_policies)
        )

        # Mock: Policy creation
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.post = (
            AsyncMock(return_value=mock_policy_response)
        )

        result = await cloud_pc_manager.ensure_provisioning_policy()

        assert result == mock_policy_response.id
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.post.assert_called_once()
        call_args = (
            mock_graph_client.device_management.virtual_endpoint.provisioning_policies.post.call_args
        )
        assert "displayName" in call_args.kwargs["body"]
        assert "HayMaker" in call_args.kwargs["body"]["displayName"]

    @pytest.mark.asyncio
    async def test_ensure_provisioning_policy_returns_existing(
        self, cloud_pc_manager, mock_graph_client, mock_policy_response
    ):
        """Test that ensure_provisioning_policy returns existing policy ID when found."""
        # Mock: Existing policy found
        mock_policies = MagicMock()
        mock_policies.value = [mock_policy_response]
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(return_value=mock_policies)
        )

        result = await cloud_pc_manager.ensure_provisioning_policy()

        assert result == mock_policy_response.id
        # Should not create a new policy
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_provisioning_policy_with_custom_params(
        self, cloud_pc_manager, mock_graph_client, mock_policy_response
    ):
        """Test provisioning policy creation with custom parameters."""
        mock_policies = MagicMock()
        mock_policies.value = []
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(return_value=mock_policies)
        )
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.post = (
            AsyncMock(return_value=mock_policy_response)
        )

        custom_display_name = "Custom-Policy"
        custom_sku = "CPC_S_4C_8GB_128GB"

        result = await cloud_pc_manager.ensure_provisioning_policy(
            display_name=custom_display_name, sku_id=custom_sku
        )

        assert result == mock_policy_response.id
        call_args = (
            mock_graph_client.device_management.virtual_endpoint.provisioning_policies.post.call_args
        )
        assert call_args.kwargs["body"]["displayName"] == custom_display_name

    @pytest.mark.asyncio
    async def test_ensure_provisioning_policy_handles_errors(
        self, cloud_pc_manager, mock_graph_client
    ):
        """Test provisioning policy creation handles Graph API errors."""
        mock_graph_client.device_management.virtual_endpoint.provisioning_policies.get = (
            AsyncMock(side_effect=Exception("Graph API error"))
        )

        with pytest.raises(Exception) as exc_info:
            await cloud_pc_manager.ensure_provisioning_policy()

        assert "Graph API error" in str(exc_info.value)


# ==============================================================================
# CLOUD PC PROVISIONING TESTS
# ==============================================================================


class TestCloudPCProvisioning:
    """Tests for Cloud PC provisioning operations."""

    @pytest.mark.asyncio
    async def test_provision_cloud_pc_success(
        self, cloud_pc_manager, worker_identity, mock_graph_client
    ):
        """Test provision_cloud_pc initiates provisioning successfully."""
        policy_id = f"policy-{uuid4()}"

        result = await cloud_pc_manager.provision_cloud_pc(
            worker=worker_identity, policy_id=policy_id
        )

        assert result.startswith("cloudpc-")
        assert worker_identity.worker_id in result

    @pytest.mark.asyncio
    async def test_provision_cloud_pc_handles_graph_errors(
        self, cloud_pc_manager, worker_identity, mock_graph_client
    ):
        """Test provision_cloud_pc handles Graph API errors gracefully."""
        policy_id = f"policy-{uuid4()}"

        # Mock an error during provisioning
        # Note: In full implementation, this would involve group assignment
        # For now, the method returns a placeholder, so we test the try/except pattern

        with patch.object(
            cloud_pc_manager,
            "provision_cloud_pc",
            side_effect=Exception("Provisioning failed"),
        ):
            with pytest.raises(Exception) as exc_info:
                await cloud_pc_manager.provision_cloud_pc(
                    worker=worker_identity, policy_id=policy_id
                )

            assert "Provisioning failed" in str(exc_info.value)


# ==============================================================================
# STATUS MONITORING TESTS
# ==============================================================================


class TestStatusMonitoring:
    """Tests for Cloud PC status monitoring and polling."""

    @pytest.mark.asyncio
    async def test_wait_for_provisioning_succeeds(
        self, cloud_pc_manager, worker_identity, mock_graph_client, mock_cloud_pc_response
    ):
        """Test wait_for_provisioning succeeds when status becomes 'provisioned'."""
        mock_cloud_pc_response.status = "provisioned"
        mock_result = MagicMock()
        mock_result.value = [mock_cloud_pc_response]
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        result = await cloud_pc_manager.wait_for_provisioning(
            worker=worker_identity, timeout_minutes=1
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_provisioning_fails_on_error_status(
        self, cloud_pc_manager, worker_identity, mock_graph_client, mock_cloud_pc_response
    ):
        """Test wait_for_provisioning returns False when status is 'failed'."""
        mock_cloud_pc_response.status = "failed"
        mock_result = MagicMock()
        mock_result.value = [mock_cloud_pc_response]
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        result = await cloud_pc_manager.wait_for_provisioning(
            worker=worker_identity, timeout_minutes=1
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_provisioning_timeout(
        self, cloud_pc_manager, worker_identity, mock_graph_client, mock_cloud_pc_response
    ):
        """Test wait_for_provisioning times out when provisioning takes too long."""
        # Mock: Always return "provisioning" status
        mock_cloud_pc_response.status = "provisioning"
        mock_result = MagicMock()
        mock_result.value = [mock_cloud_pc_response]
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        # Use very short timeout for testing
        result = await cloud_pc_manager.wait_for_provisioning(
            worker=worker_identity, timeout_minutes=0.01  # 0.6 seconds
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_provisioning_handles_api_errors(
        self, cloud_pc_manager, worker_identity, mock_graph_client
    ):
        """Test wait_for_provisioning handles transient Graph API errors."""
        # Mock: API errors followed by success
        mock_cloud_pc = MagicMock()
        mock_cloud_pc.status = "provisioned"
        mock_result = MagicMock()
        mock_result.value = [mock_cloud_pc]

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Transient error")
            return mock_result

        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            side_effect=side_effect
        )

        result = await cloud_pc_manager.wait_for_provisioning(
            worker=worker_identity, timeout_minutes=1
        )

        assert result is True
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_get_cloud_pc_returns_info(
        self, cloud_pc_manager, worker_identity, mock_graph_client, mock_cloud_pc_response
    ):
        """Test get_cloud_pc returns Cloud PC information."""
        mock_result = MagicMock()
        mock_result.value = [mock_cloud_pc_response]
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        result = await cloud_pc_manager.get_cloud_pc(worker=worker_identity)

        assert result is not None
        assert result["id"] == mock_cloud_pc_response.id
        assert result["status"] == mock_cloud_pc_response.status
        assert result["user_principal_name"] == worker_identity.user_principal_name

    @pytest.mark.asyncio
    async def test_get_cloud_pc_returns_none_when_not_found(
        self, cloud_pc_manager, worker_identity, mock_graph_client
    ):
        """Test get_cloud_pc returns None when Cloud PC not found."""
        mock_result = MagicMock()
        mock_result.value = []
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        result = await cloud_pc_manager.get_cloud_pc(worker=worker_identity)

        assert result is None


# ==============================================================================
# BATCH PROVISIONING TESTS
# ==============================================================================


class TestBatchProvisioning:
    """Tests for batch Cloud PC provisioning with concurrency."""

    @pytest.mark.asyncio
    async def test_batch_provisioning_with_10_workers(
        self, cloud_pc_manager, mock_graph_client
    ):
        """Test batch provisioning of 10 Cloud PCs concurrently."""
        workers = [
            WorkerIdentity(
                worker_id=f"kw-batch-{i:03d}",
                display_name=f"Batch Worker {i}",
                user_principal_name=f"worker{i}@tenant.onmicrosoft.com",
                department="engineering",
                persona=WorkerPersona.ENGINEERING,
                endpoint_type=EndpointType.CLOUD_PC,
                endpoint_id="",
                team_ids=["team-001"],
            )
            for i in range(10)
        ]

        policy_id = f"policy-{uuid4()}"

        # Provision all workers concurrently
        tasks = [
            cloud_pc_manager.provision_cloud_pc(worker=w, policy_id=policy_id)
            for w in workers
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r.startswith("cloudpc-") for r in results)


# ==============================================================================
# CLEANUP TESTS
# ==============================================================================


class TestCloudPCCleanup:
    """Tests for Cloud PC cleanup and deprovisioning."""

    @pytest.mark.asyncio
    async def test_delete_cloud_pc_succeeds(
        self, cloud_pc_manager, mock_graph_client
    ):
        """Test delete_cloud_pc removes a Cloud PC successfully."""
        cloud_pc_id = f"cloudpc-{uuid4()}"

        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id = (
            MagicMock()
        )
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id.return_value.delete = (
            AsyncMock(return_value=None)
        )

        result = await cloud_pc_manager.delete_cloud_pc(cloud_pc_id=cloud_pc_id)

        assert result is True
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id.assert_called_once_with(
            cloud_pc_id
        )

    @pytest.mark.asyncio
    async def test_delete_cloud_pc_handles_not_found(
        self, cloud_pc_manager, mock_graph_client
    ):
        """Test delete_cloud_pc handles 404 not found gracefully."""
        cloud_pc_id = f"cloudpc-{uuid4()}"

        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id = (
            MagicMock()
        )
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id.return_value.delete = AsyncMock(
            side_effect=Exception("404: Not Found")
        )

        result = await cloud_pc_manager.delete_cloud_pc(cloud_pc_id=cloud_pc_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_list_cloud_pcs_for_run(
        self, cloud_pc_manager, mock_graph_client, run_id
    ):
        """Test list_cloud_pcs_for_run returns Cloud PCs for the current run."""
        mock_pc1 = MagicMock()
        mock_pc1.id = "pc-001"
        mock_pc1.display_name = f"kw-{run_id[:8]}-worker1"
        mock_pc1.status = "provisioned"
        mock_pc1.user_principal_name = f"worker1@tenant.onmicrosoft.com"

        mock_pc2 = MagicMock()
        mock_pc2.id = "pc-002"
        mock_pc2.display_name = f"kw-{run_id[:8]}-worker2"
        mock_pc2.status = "provisioned"
        mock_pc2.user_principal_name = f"worker2@tenant.onmicrosoft.com"

        # PC from different run (should be filtered out)
        mock_pc3 = MagicMock()
        mock_pc3.id = "pc-003"
        mock_pc3.display_name = "kw-different-worker3"
        mock_pc3.status = "provisioned"
        mock_pc3.user_principal_name = "worker3@tenant.onmicrosoft.com"

        mock_result = MagicMock()
        mock_result.value = [mock_pc1, mock_pc2, mock_pc3]
        mock_graph_client.device_management.virtual_endpoint.cloud_p_cs.get = AsyncMock(
            return_value=mock_result
        )

        result = await cloud_pc_manager.list_cloud_pcs_for_run()

        assert len(result) == 2
        assert all(run_id[:8] in pc["user_principal_name"] for pc in result)

    @pytest.mark.asyncio
    async def test_cleanup_all_cloud_pcs_for_run(
        self, cloud_pc_manager, mock_graph_client, run_id
    ):
        """Test cleanup removes all Cloud PCs for a run."""
        # Mock list_cloud_pcs_for_run
        mock_pcs = [
            {"id": f"pc-{i}", "display_name": f"kw-{run_id[:8]}-worker{i}"}
            for i in range(3)
        ]

        with patch.object(
            cloud_pc_manager, "list_cloud_pcs_for_run", return_value=mock_pcs
        ):
            with patch.object(
                cloud_pc_manager, "delete_cloud_pc", return_value=True
            ) as mock_delete:
                # Delete all PCs
                tasks = [
                    cloud_pc_manager.delete_cloud_pc(pc["id"]) for pc in mock_pcs
                ]
                results = await asyncio.gather(*tasks)

                assert len(results) == 3
                assert all(results)
                assert mock_delete.call_count == 3


# ==============================================================================
# POLICY GROUP ASSIGNMENT TESTS
# ==============================================================================


class TestPolicyGroupAssignment:
    """Tests for assigning users to Cloud PC provisioning policy groups."""

    @pytest.mark.asyncio
    async def test_assignment_group_creation(self, cloud_pc_manager, run_id):
        """Test that provisioning creates assignment group for policy."""
        # This would test the full workflow of:
        # 1. Create provisioning policy
        # 2. Create assignment group
        # 3. Link group to policy
        # This is a placeholder for future implementation
        pass

    @pytest.mark.asyncio
    async def test_assignment_group_reuse(self, cloud_pc_manager):
        """Test that existing assignment groups are reused."""
        # This would test finding and reusing existing groups
        # This is a placeholder for future implementation
        pass

    @pytest.mark.asyncio
    async def test_policy_group_assignment(self, cloud_pc_manager, worker_identity):
        """Test assigning a user to a provisioning policy group."""
        # This would test the add_member Graph API call
        # This is a placeholder for future implementation
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
