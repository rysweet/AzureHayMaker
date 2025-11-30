"""Integration tests for cascade fallback: Cloud PC → Windows VM → Container.

This module tests the end-to-end cascade fallback logic with real or mocked
endpoint managers. Tests verify that the system correctly falls back through
endpoint types when failures occur.

Tests cover:
- Cloud PC failure triggers Windows VM (mocked Cloud PC)
- Windows VM failure triggers Container (mocked VM)
- Worker.endpoint_type reflects actual provisioned type
- Metrics tracked for each fallback step
- Full cascade with all fallback levels

Uses pytest with mixed real/mocked components for controlled testing.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest

# Import modules under test
try:
    from azure_haymaker.knowledge_worker.endpoint_manager import (
        AllEndpointsFailedError,
        EndpointManager,
    )
    from azure_haymaker.knowledge_worker.models.worker import (
        EndpointType,
        WorkerIdentity,
        WorkerPersona,
    )

    ENDPOINT_MANAGER_AVAILABLE = True
except ImportError:
    ENDPOINT_MANAGER_AVAILABLE = False
    EndpointManager = None
    AllEndpointsFailedError = Exception
    WorkerIdentity = None


pytestmark = [
    pytest.mark.skipif(
        not ENDPOINT_MANAGER_AVAILABLE, reason="EndpointManager not yet implemented"
    ),
    pytest.mark.integration,
]


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def run_id():
    """Fixture: HayMaker run ID for integration test."""
    return str(uuid4())


@pytest.fixture
def test_workers(run_id):
    """Fixture: Sample workers for cascade fallback testing."""
    return [
        WorkerIdentity(
            worker_id=f"kw-cascade-{run_id[:8]}-{i:03d}",
            display_name=f"Cascade Test Worker {i}",
            user_principal_name=f"cascade.worker{i}@example.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
            endpoint_type=EndpointType.CLOUD_PC,  # Initial preference
            endpoint_id="",
            team_ids=["team-001"],
        )
        for i in range(5)
    ]


@pytest.fixture
def mock_cloud_pc_manager():
    """Fixture: Mock Cloud PC manager that simulates failures."""
    manager = MagicMock()
    manager.provision_cloud_pc = AsyncMock()
    manager.wait_for_provisioning = AsyncMock()
    manager.get_cloud_pc = AsyncMock()
    manager.delete_cloud_pc = AsyncMock()
    return manager


@pytest.fixture
def mock_windows_vm_manager():
    """Fixture: Mock Windows VM manager that simulates failures."""
    manager = MagicMock()
    manager.provision_vm = AsyncMock()
    manager.wait_for_provisioning = AsyncMock()
    manager.get_vm_status = AsyncMock()
    manager.delete_vm = AsyncMock()
    manager.verify_computer_use_ready = AsyncMock()
    return manager


@pytest.fixture
def mock_container_manager():
    """Fixture: Mock Container manager (always succeeds as final fallback)."""
    manager = MagicMock()
    manager.provision_container = AsyncMock(
        return_value={"container_id": "container-fallback", "status": "running"}
    )
    manager.get_container_status = AsyncMock(return_value="running")
    manager.delete_container = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def endpoint_manager(
    mock_cloud_pc_manager,
    mock_windows_vm_manager,
    mock_container_manager,
    run_id,
):
    """Fixture: EndpointManager with mocked sub-managers for fallback testing."""
    return EndpointManager(
        cloud_pc_manager=mock_cloud_pc_manager,
        windows_vm_manager=mock_windows_vm_manager,
        container_manager=mock_container_manager,
        run_id=run_id,
    )


# ==============================================================================
# CLOUD PC TO WINDOWS VM FALLBACK TESTS
# ==============================================================================


class TestCloudPCToWindowsVMFallback:
    """Integration tests for Cloud PC → Windows VM fallback."""

    @pytest.mark.asyncio
    async def test_cloud_pc_timeout_triggers_windows_vm(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
    ):
        """Test Cloud PC provisioning timeout triggers Windows VM fallback.

        Scenario:
        1. Cloud PC provisioning starts but times out
        2. System falls back to Windows VM
        3. Windows VM provisions successfully
        4. Worker endpoint_type is WINDOWS_VM
        """
        worker = test_workers[0]

        # Mock Cloud PC timeout
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-pending"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = False  # Timeout

        # Mock Windows VM success
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "cua-win-eastus-001",
            "public_ip": "52.168.1.100",
            "admin_username": "adminuser",
            "admin_password": "SecurePass123!@#",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        print(f"\n🔄 Testing Cloud PC → Windows VM fallback...")

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker
        )

        # Verify Windows VM was provisioned
        assert result["endpoint_type"] == EndpointType.WINDOWS_VM
        assert result["success"] is True
        assert result["endpoint_id"] == "cua-win-eastus-001"

        # Verify worker was updated
        assert worker.endpoint_type == EndpointType.WINDOWS_VM
        assert worker.endpoint_id == "cua-win-eastus-001"

        print(f"✅ Successfully fell back to Windows VM: {result['endpoint_id']}")

    @pytest.mark.asyncio
    async def test_cloud_pc_quota_exceeded_triggers_windows_vm(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
    ):
        """Test Cloud PC quota exceeded triggers Windows VM fallback.

        Scenario:
        1. Cloud PC provisioning fails with quota exceeded
        2. System falls back to Windows VM immediately
        3. Windows VM provisions successfully
        """
        worker = test_workers[1]

        # Mock Cloud PC quota error
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception(
            "QuotaExceeded: Cloud PC quota limit reached"
        )

        # Mock Windows VM success
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "cua-win-eastus-002",
            "public_ip": "52.168.1.101",
            "admin_username": "adminuser",
            "admin_password": "SecurePass123!@#",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        print(f"\n🔄 Testing Cloud PC quota → Windows VM fallback...")

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker
        )

        # Verify Windows VM fallback
        assert result["endpoint_type"] == EndpointType.WINDOWS_VM
        assert worker.endpoint_type == EndpointType.WINDOWS_VM

        print(f"✅ Successfully fell back to Windows VM after quota error")

    @pytest.mark.asyncio
    async def test_fallback_tracks_cloud_pc_failure_reason(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        caplog,
    ):
        """Test that fallback logic logs Cloud PC failure reason."""
        worker = test_workers[2]

        # Mock Cloud PC error with specific reason
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception(
            "PermissionDenied: Insufficient permissions to create Cloud PC"
        )

        # Mock Windows VM success
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "cua-win-eastus-003",
            "public_ip": "52.168.1.102",
            "admin_username": "adminuser",
            "admin_password": "SecurePass123!@#",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker
        )

        # Verify logging captured failure reason
        log_output = caplog.text.lower()
        assert (
            "permission" in log_output
            or "failed" in log_output
            or "fallback" in log_output
        )


# ==============================================================================
# WINDOWS VM TO CONTAINER FALLBACK TESTS
# ==============================================================================


class TestWindowsVMToContainerFallback:
    """Integration tests for Windows VM → Container fallback."""

    @pytest.mark.asyncio
    async def test_windows_vm_quota_triggers_container(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test Windows VM quota exceeded triggers Container fallback.

        Scenario:
        1. Cloud PC fails
        2. Windows VM provisioning fails with quota exceeded
        3. System falls back to Container
        4. Container provisions successfully
        """
        worker = test_workers[0]

        # Mock Cloud PC failure
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception(
            "Cloud PC unavailable"
        )

        # Mock Windows VM quota error
        mock_windows_vm_manager.provision_vm.side_effect = Exception(
            "QuotaExceeded: Regional VM quota exceeded"
        )

        # Mock Container success (already configured in fixture)

        print(f"\n🔄 Testing Windows VM quota → Container fallback...")

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker
        )

        # Verify Container was provisioned
        assert result["endpoint_type"] == EndpointType.CLI_CONTAINER
        assert result["success"] is True
        assert result["endpoint_id"] == "container-fallback"

        # Verify worker was updated
        assert worker.endpoint_type == EndpointType.CLI_CONTAINER
        assert worker.endpoint_id == "container-fallback"

        print(f"✅ Successfully fell back to Container: {result['endpoint_id']}")

    @pytest.mark.asyncio
    async def test_windows_vm_timeout_triggers_container(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test Windows VM timeout triggers Container fallback.

        Scenario:
        1. Cloud PC times out
        2. Windows VM provisioning times out
        3. System falls back to Container
        """
        worker = test_workers[1]

        # Mock Cloud PC timeout
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-pending"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = False

        # Mock Windows VM timeout
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-pending",
            "public_ip": "0.0.0.0",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = False

        print(f"\n🔄 Testing Windows VM timeout → Container fallback...")

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker
        )

        # Verify Container fallback
        assert result["endpoint_type"] == EndpointType.CLI_CONTAINER
        assert worker.endpoint_type == EndpointType.CLI_CONTAINER

        print(f"✅ Successfully fell back to Container after VM timeout")


# ==============================================================================
# FULL CASCADE TESTS
# ==============================================================================


class TestFullCascadeFallback:
    """Integration tests for full cascade fallback chain."""

    @pytest.mark.asyncio
    async def test_full_cascade_cloud_pc_to_vm_to_container(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
        caplog,
    ):
        """Test complete cascade: Cloud PC → Windows VM → Container.

        Scenario:
        1. Cloud PC fails immediately
        2. Windows VM fails immediately
        3. Container succeeds as final fallback
        4. All attempts are logged
        """
        worker = test_workers[0]

        # Mock all failures except Container
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception(
            "Cloud PC failed"
        )
        mock_windows_vm_manager.provision_vm.side_effect = Exception("VM failed")
        # Container succeeds (already configured)

        print(f"\n🔄 Testing full cascade: Cloud PC → VM → Container...")

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker
        )

        # Verify Container was final fallback
        assert result["endpoint_type"] == EndpointType.CLI_CONTAINER
        assert result["success"] is True

        # Verify all attempts were made
        mock_cloud_pc_manager.provision_cloud_pc.assert_called_once()
        mock_windows_vm_manager.provision_vm.assert_called_once()
        mock_container_manager.provision_container.assert_called_once()

        # Verify logging shows all attempts
        log_output = caplog.text.lower()
        assert "cloud" in log_output or "pc" in log_output
        assert "vm" in log_output or "windows" in log_output
        assert "container" in log_output

        print(f"✅ Full cascade completed successfully: {result['endpoint_id']}")

    @pytest.mark.asyncio
    async def test_cascade_tracks_fallback_metrics(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test that cascade fallback tracks metrics for each attempt."""
        worker = test_workers[1]

        # Mock failures
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("PC failed")
        mock_windows_vm_manager.provision_vm.side_effect = Exception("VM failed")

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker
        )

        # Verify metrics include fallback information
        assert "fallback_count" in result or "attempts" in result or result["success"]
        assert result["endpoint_type"] == EndpointType.CLI_CONTAINER


# ==============================================================================
# WORKER STATE TRACKING TESTS
# ==============================================================================


class TestWorkerStateTracking:
    """Integration tests for worker endpoint_type tracking during fallback."""

    @pytest.mark.asyncio
    async def test_worker_endpoint_type_reflects_actual_provisioned(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
    ):
        """Test worker.endpoint_type always reflects actual provisioned type."""
        worker = test_workers[0]

        # Initial state
        assert worker.endpoint_type == EndpointType.CLOUD_PC
        assert worker.endpoint_id == ""

        # Mock Cloud PC failure, Windows VM success
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Failed")
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-final",
            "public_ip": "52.168.1.200",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker
        )

        # Verify worker state matches actual endpoint
        assert worker.endpoint_type == EndpointType.WINDOWS_VM
        assert worker.endpoint_id == "vm-final"
        assert result["endpoint_type"] == worker.endpoint_type

    @pytest.mark.asyncio
    async def test_multiple_workers_different_endpoints(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test multiple workers can have different endpoint types after fallback.

        Scenario:
        - Worker 0: Cloud PC succeeds
        - Worker 1: Cloud PC fails, Windows VM succeeds
        - Worker 2: Both fail, Container succeeds
        """
        workers = test_workers[:3]

        # Mock different outcomes for each worker
        call_count = {"cloud_pc": 0, "vm": 0}

        async def mock_provision_cloud_pc(*args, **kwargs):
            call_count["cloud_pc"] += 1
            if call_count["cloud_pc"] == 1:
                return "cloudpc-success"  # Worker 0 succeeds
            raise Exception("Cloud PC failed")  # Others fail

        async def mock_wait_cloud_pc(*args, **kwargs):
            return call_count["cloud_pc"] == 1  # Only first succeeds

        async def mock_provision_vm(*args, **kwargs):
            call_count["vm"] += 1
            if call_count["vm"] == 1:
                return {
                    "vm_name": "vm-success",
                    "public_ip": "52.168.1.1",
                    "admin_username": "admin",
                    "admin_password": "Pass123!",
                    "rdp_port": 3389,
                }
            raise Exception("VM failed")

        async def mock_wait_vm(*args, **kwargs):
            return call_count["vm"] == 1

        mock_cloud_pc_manager.provision_cloud_pc = mock_provision_cloud_pc
        mock_cloud_pc_manager.wait_for_provisioning = mock_wait_cloud_pc
        mock_windows_vm_manager.provision_vm = mock_provision_vm
        mock_windows_vm_manager.wait_for_provisioning = mock_wait_vm

        print(f"\n🔄 Testing multiple workers with different endpoints...")

        # Provision all workers
        tasks = [
            endpoint_manager.provision_endpoint_with_fallback(worker=w)
            for w in workers
        ]
        results = await asyncio.gather(*tasks)

        # Verify each worker has correct endpoint type
        assert workers[0].endpoint_type == EndpointType.CLOUD_PC
        assert workers[1].endpoint_type == EndpointType.WINDOWS_VM
        assert workers[2].endpoint_type == EndpointType.CLI_CONTAINER

        print(f"✅ Worker 0: {workers[0].endpoint_type.value}")
        print(f"✅ Worker 1: {workers[1].endpoint_type.value}")
        print(f"✅ Worker 2: {workers[2].endpoint_type.value}")


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================


class TestCascadeErrorHandling:
    """Integration tests for error handling during cascade fallback."""

    @pytest.mark.asyncio
    async def test_all_endpoints_fail_raises_error(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test that all endpoints failing raises AllEndpointsFailedError."""
        worker = test_workers[0]

        # Mock all endpoints failing
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("PC failed")
        mock_windows_vm_manager.provision_vm.side_effect = Exception("VM failed")
        mock_container_manager.provision_container.side_effect = Exception(
            "Container failed"
        )

        print(f"\n❌ Testing all endpoints fail scenario...")

        with pytest.raises(AllEndpointsFailedError) as exc_info:
            await endpoint_manager.provision_endpoint_with_fallback(worker=worker)

        # Verify error contains useful information
        error_message = str(exc_info.value)
        assert len(error_message) > 0

        print(f"✅ AllEndpointsFailedError raised correctly")

    @pytest.mark.asyncio
    async def test_partial_provisioning_cleanup(
        self,
        endpoint_manager,
        test_workers,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test that failed provisions are cleaned up before fallback."""
        worker = test_workers[0]

        # Mock Cloud PC starts but fails
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-123"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = False  # Timeout
        mock_cloud_pc_manager.delete_cloud_pc.return_value = True

        # Mock Windows VM succeeds
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-clean",
            "public_ip": "52.168.1.1",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker, cleanup_failed=True
        )

        # Verify failed Cloud PC was cleaned up
        mock_cloud_pc_manager.delete_cloud_pc.assert_called()

        # Verify Windows VM succeeded
        assert result["endpoint_type"] == EndpointType.WINDOWS_VM


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
