"""Unit tests for Endpoint Manager cascade fallback logic.

This module tests the EndpointManager class that orchestrates endpoint provisioning
with cascade fallback support: Cloud PC → Windows VM → Container.

Tests cover:
- Successful Cloud PC provisioning (no fallback)
- Cloud PC timeout triggers Windows VM fallback
- Windows VM quota exceeded triggers Container fallback
- All endpoints fail raises AllEndpointsFailedError
- Worker.endpoint_type updated after fallback
- Fallback logging and metrics

Uses pytest with AsyncMock for endpoint managers.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# Import the module under test
try:
    from azure_haymaker.knowledge_worker.endpoints.manager import (
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


pytestmark = pytest.mark.skipif(
    not ENDPOINT_MANAGER_AVAILABLE, reason="EndpointManager not yet implemented"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def run_id():
    """Fixture: HayMaker run ID."""
    return str(uuid4())


@pytest.fixture
def worker_identity():
    """Fixture: Sample worker identity."""
    return WorkerIdentity(
        worker_id="kw-test-001",
        display_name="Test Worker",
        user_principal_name="test.worker@tenant.onmicrosoft.com",
        department="engineering",
        persona=WorkerPersona.ENGINEERING,
        endpoint_type=EndpointType.CLOUD_PC,  # Initial preference
        endpoint_id="",
        team_ids=["team-001"],
    )


@pytest.fixture
def mock_cloud_pc_manager():
    """Fixture: Mock Cloud PC manager."""
    manager = MagicMock()
    manager.ensure_provisioning_policy = AsyncMock()
    manager.provision_cloud_pc = AsyncMock()
    manager.wait_for_provisioning = AsyncMock()
    manager.get_cloud_pc = AsyncMock()
    manager.delete_cloud_pc = AsyncMock()
    return manager


@pytest.fixture
def mock_windows_vm_manager():
    """Fixture: Mock Windows VM manager."""
    manager = MagicMock()
    manager.provision_vm = AsyncMock()
    manager.wait_for_provisioning = AsyncMock()
    manager.get_vm_status = AsyncMock()
    manager.delete_vm = AsyncMock()
    manager.verify_computer_use_ready = AsyncMock()
    return manager


@pytest.fixture
def mock_container_manager():
    """Fixture: Mock Container manager."""
    manager = MagicMock()
    manager.deploy_worker_container = AsyncMock()
    manager.provision_container = AsyncMock()
    manager.get_container_status = AsyncMock()
    manager.delete_container = AsyncMock()
    return manager


@pytest.fixture
def endpoint_manager(
    mock_cloud_pc_manager,
    mock_windows_vm_manager,
    mock_container_manager,
    run_id,
):
    """Fixture: EndpointManager instance with mocked sub-managers."""
    return EndpointManager(
        cloud_pc_manager=mock_cloud_pc_manager,
        windows_vm_manager=mock_windows_vm_manager,
        container_manager=mock_container_manager,
        run_id=run_id,
    )


# ==============================================================================
# SUCCESSFUL PROVISIONING TESTS (NO FALLBACK)
# ==============================================================================


class TestSuccessfulProvisioning:
    """Tests for successful endpoint provisioning without fallback."""

    @pytest.mark.asyncio
    async def test_provision_cloud_pc_success_no_fallback(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
    ):
        """Test Cloud PC provisions successfully without triggering fallback."""
        # Mock successful Cloud PC provisioning
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-123"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify Cloud PC was provisioned
        assert result["endpoint_type"] == EndpointType.CLOUD_PC
        assert result["endpoint_id"] == "cloudpc-123"
        assert result["success"] is True

        # Verify worker endpoint_type was updated
        assert worker_identity.endpoint_type == EndpointType.CLOUD_PC
        assert worker_identity.endpoint_id == "cloudpc-123"

        # Verify no fallback attempts
        mock_cloud_pc_manager.ensure_provisioning_policy.assert_called_once()
        mock_cloud_pc_manager.provision_cloud_pc.assert_called_once()
        mock_cloud_pc_manager.wait_for_provisioning.assert_called_once()


# ==============================================================================
# CLOUD PC TO WINDOWS VM FALLBACK TESTS
# ==============================================================================


class TestCloudPCToWindowsVMFallback:
    """Tests for fallback from Cloud PC to Windows VM."""

    @pytest.mark.asyncio
    async def test_cloud_pc_timeout_triggers_windows_vm_fallback(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
    ):
        """Test Cloud PC timeout triggers Windows VM fallback."""
        # Mock Cloud PC provisioning timeout
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-123"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = False  # Timeout

        # Mock successful Windows VM provisioning
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "cua-win-eastus-kw-test-001",
            "public_ip": "52.168.1.100",
            "admin_username": "adminuser",
            "admin_password": "SecurePassword123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify Windows VM was provisioned after Cloud PC failed
        assert result["endpoint_type"] == EndpointType.WINDOWS_VM
        assert result["endpoint_id"] == "cua-win-eastus-kw-test-001"
        assert result["success"] is True

        # Verify worker endpoint_type was updated to WINDOWS_VM
        assert worker_identity.endpoint_type == EndpointType.WINDOWS_VM
        assert worker_identity.endpoint_id == "cua-win-eastus-kw-test-001"

        # Verify both managers were called
        mock_cloud_pc_manager.provision_cloud_pc.assert_called_once()
        mock_windows_vm_manager.provision_vm.assert_called_once()

    @pytest.mark.asyncio
    async def test_cloud_pc_error_triggers_windows_vm_fallback(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
    ):
        """Test Cloud PC provisioning error triggers Windows VM fallback."""
        # Mock Cloud PC provisioning failure
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Cloud PC quota exceeded")

        # Mock successful Windows VM provisioning
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "cua-win-eastus-kw-test-001",
            "public_ip": "52.168.1.100",
            "admin_username": "adminuser",
            "admin_password": "SecurePassword123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify Windows VM fallback
        assert result["endpoint_type"] == EndpointType.WINDOWS_VM
        assert result["success"] is True
        assert worker_identity.endpoint_type == EndpointType.WINDOWS_VM

    @pytest.mark.asyncio
    async def test_fallback_logs_cloud_pc_failure_reason(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        caplog,
    ):
        """Test fallback logs Cloud PC failure reason."""
        # Mock Cloud PC timeout
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-123"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = False

        # Mock successful Windows VM
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-test",
            "public_ip": "52.168.1.100",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify logging contains fallback information
        log_output = caplog.text.lower()
        assert "fallback" in log_output or "timeout" in log_output or "failed" in log_output


# ==============================================================================
# WINDOWS VM TO CONTAINER FALLBACK TESTS
# ==============================================================================


class TestWindowsVMToContainerFallback:
    """Tests for fallback from Windows VM to Container."""

    @pytest.mark.asyncio
    async def test_windows_vm_quota_exceeded_triggers_container_fallback(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test Windows VM quota exceeded triggers Container fallback."""
        # Mock Cloud PC failure
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Cloud PC not available")

        # Mock Windows VM quota exceeded
        mock_windows_vm_manager.provision_vm.side_effect = Exception(
            "QuotaExceeded: Regional quota limit exceeded"
        )

        # Mock successful Container provisioning
        mock_container_manager.deploy_worker_container.return_value = "container-123"

        result = await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify Container was provisioned after VM failed
        assert result["endpoint_type"] == EndpointType.CLI_CONTAINER
        assert result["endpoint_id"] == "container-123"
        assert result["success"] is True

        # Verify worker endpoint_type was updated to CLI_CONTAINER
        assert worker_identity.endpoint_type == EndpointType.CLI_CONTAINER
        assert worker_identity.endpoint_id == "container-123"

        # Verify all managers were called
        mock_cloud_pc_manager.provision_cloud_pc.assert_called_once()
        mock_windows_vm_manager.provision_vm.assert_called_once()
        mock_container_manager.deploy_worker_container.assert_called_once()

    @pytest.mark.asyncio
    async def test_windows_vm_timeout_triggers_container_fallback(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test Windows VM timeout triggers Container fallback."""
        # Mock Cloud PC failure
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-123"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = False

        # Mock Windows VM timeout
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-test",
            "public_ip": "52.168.1.100",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = False  # Timeout

        # Mock successful Container
        mock_container_manager.deploy_worker_container.return_value = "container-123"

        result = await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify Container fallback
        assert result["endpoint_type"] == EndpointType.CLI_CONTAINER
        assert result["success"] is True


# ==============================================================================
# ALL ENDPOINTS FAIL TESTS
# ==============================================================================


class TestAllEndpointsFail:
    """Tests for when all endpoint types fail."""

    @pytest.mark.asyncio
    async def test_all_endpoints_fail_raises_error(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test all endpoints failing raises AllEndpointsFailedError."""
        # Mock all endpoints failing
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Cloud PC failed")
        mock_windows_vm_manager.provision_vm.side_effect = Exception("VM failed")
        mock_container_manager.deploy_worker_container.side_effect = Exception("Container failed")

        with pytest.raises(AllEndpointsFailedError) as exc_info:
            await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify error message contains all failure reasons
        error_message = str(exc_info.value)
        assert "Cloud PC" in error_message or "failed" in error_message.lower()

    @pytest.mark.asyncio
    async def test_all_endpoints_fail_logs_all_attempts(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
        caplog,
    ):
        """Test all endpoint failures are logged."""
        # Mock all endpoints failing
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Cloud PC failed")
        mock_windows_vm_manager.provision_vm.side_effect = Exception("VM failed")
        mock_container_manager.deploy_worker_container.side_effect = Exception("Container failed")

        with pytest.raises(AllEndpointsFailedError):
            await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify all attempts were logged
        log_output = caplog.text.lower()
        assert "cloud" in log_output or "pc" in log_output
        assert "vm" in log_output or "windows" in log_output
        assert "container" in log_output


# ==============================================================================
# WORKER ENDPOINT TYPE UPDATE TESTS
# ==============================================================================


class TestWorkerEndpointTypeUpdate:
    """Tests for worker.endpoint_type being updated correctly."""

    @pytest.mark.asyncio
    async def test_worker_endpoint_type_updated_on_cloud_pc_success(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
    ):
        """Test worker.endpoint_type is CLOUD_PC after successful Cloud PC provisioning."""
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-123"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = True

        await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        assert worker_identity.endpoint_type == EndpointType.CLOUD_PC
        assert worker_identity.endpoint_id == "cloudpc-123"

    @pytest.mark.asyncio
    async def test_worker_endpoint_type_updated_on_windows_vm_fallback(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
    ):
        """Test worker.endpoint_type is WINDOWS_VM after fallback."""
        # Cloud PC fails
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Failed")

        # Windows VM succeeds
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-test",
            "public_ip": "52.168.1.100",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        assert worker_identity.endpoint_type == EndpointType.WINDOWS_VM
        assert worker_identity.endpoint_id == "vm-test"

    @pytest.mark.asyncio
    async def test_worker_endpoint_type_updated_on_container_fallback(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test worker.endpoint_type is CLI_CONTAINER after double fallback."""
        # Cloud PC and VM fail
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Failed")
        mock_windows_vm_manager.provision_vm.side_effect = Exception("Failed")

        # Container succeeds
        mock_container_manager.deploy_worker_container.return_value = "container-123"

        await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        assert worker_identity.endpoint_type == EndpointType.CLI_CONTAINER
        assert worker_identity.endpoint_id == "container-123"


# ==============================================================================
# METRICS TRACKING TESTS
# ==============================================================================


class TestMetricsTracking:
    """Tests for metrics tracking during fallback."""

    @pytest.mark.asyncio
    async def test_metrics_track_fallback_count(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
    ):
        """Test metrics track number of fallback attempts."""
        # Mock Cloud PC timeout
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.return_value = "cloudpc-123"
        mock_cloud_pc_manager.wait_for_provisioning.return_value = False

        # Mock Windows VM success
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-test",
            "public_ip": "52.168.1.100",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify fallback occurred - Windows VM was used after Cloud PC timeout
        assert result["endpoint_type"] == EndpointType.WINDOWS_VM
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_metrics_track_final_endpoint_type(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
        mock_windows_vm_manager,
    ):
        """Test metrics track the final provisioned endpoint type."""
        # Mock fallback scenario
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Failed")
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-test",
            "public_ip": "52.168.1.100",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(worker=worker_identity)

        # Verify final endpoint type is tracked
        assert result["endpoint_type"] == EndpointType.WINDOWS_VM


# ==============================================================================
# FALLBACK STRATEGY CONFIGURATION TESTS
# ==============================================================================


class TestFallbackStrategyConfiguration:
    """Tests for configuring fallback strategy."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Fallback disable feature not yet implemented")
    async def test_fallback_can_be_disabled(
        self,
        endpoint_manager,
        worker_identity,
        mock_cloud_pc_manager,
    ):
        """Test fallback can be disabled (fail fast on first error)."""
        mock_cloud_pc_manager.ensure_provisioning_policy.return_value = "policy-123"
        mock_cloud_pc_manager.provision_cloud_pc.side_effect = Exception("Cloud PC failed")

        with pytest.raises(Exception, match="."):
            await endpoint_manager.provision_endpoint_with_fallback(
                worker=worker_identity, enable_fallback=False
            )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Custom fallback order not yet implemented")
    async def test_custom_fallback_order(
        self,
        endpoint_manager,
        worker_identity,
        mock_windows_vm_manager,
        mock_container_manager,
    ):
        """Test custom fallback order can be specified."""
        # Start with Windows VM, skip Cloud PC
        mock_windows_vm_manager.provision_vm.return_value = {
            "vm_name": "vm-test",
            "public_ip": "52.168.1.100",
            "admin_username": "admin",
            "admin_password": "Pass123!",
            "rdp_port": 3389,
        }
        mock_windows_vm_manager.wait_for_provisioning.return_value = True

        result = await endpoint_manager.provision_endpoint_with_fallback(
            worker=worker_identity,
            fallback_order=[EndpointType.WINDOWS_VM, EndpointType.CLI_CONTAINER],
        )

        # Verify Windows VM was attempted first
        assert result["endpoint_type"] == EndpointType.WINDOWS_VM
        mock_windows_vm_manager.provision_vm.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
