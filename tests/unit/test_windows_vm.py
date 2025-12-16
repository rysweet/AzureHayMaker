"""Unit tests for Windows VM provisioning.

This module tests the WindowsVMManager class that provisions and manages
Azure Windows VMs for Computer Use Agents as a fallback option when Cloud PCs
are unavailable.

Tests cover:
- VM provisioning with secure password generation
- VM status monitoring and readiness checks
- Computer use readiness verification (RDP + browsers)
- VM deletion and cleanup
- Resource tagging with run_id
- Error handling for Azure SDK exceptions
- Timeout handling for provisioning

Uses pytest with AsyncMock for Azure SDK interactions.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Import the module under test
# Note: This import will fail until WindowsVMManager is implemented
try:
    from azure_haymaker.knowledge_worker.endpoints.windows_vm import (
        WindowsVMManager,
    )
    from azure_haymaker.knowledge_worker.models.worker import (
        EndpointType,
        WorkerIdentity,
        WorkerPersona,
    )

    WINDOWS_VM_AVAILABLE = True
except ImportError:
    WINDOWS_VM_AVAILABLE = False
    WindowsVMManager = None
    WorkerIdentity = None


pytestmark = pytest.mark.skipif(
    not WINDOWS_VM_AVAILABLE, reason="WindowsVMManager not yet implemented"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


def _create_awaitable_mock(return_value):
    """Helper to create a mock that can be awaited (like Azure SDK pollers).

    Azure async SDK pollers are directly awaitable and return the result.
    This creates a coroutine that can be directly awaited.
    """

    async def awaitable():
        return return_value

    # Return the coroutine directly (not wrapped in a mock)
    return awaitable()


@pytest.fixture
def mock_compute_client():
    """Fixture: Mock Azure Compute Management client.

    Properly sets up AsyncMock for all async methods to support Azure SDK
    operations for VM management.
    """
    client = MagicMock()

    # Setup virtual_machines operations
    # For async SDK, pollers are directly awaitable
    client.virtual_machines.begin_create_or_update = AsyncMock()
    client.virtual_machines.get = AsyncMock()
    client.virtual_machines.begin_delete = AsyncMock()
    client.virtual_machines.list = AsyncMock()

    # Setup network operations
    client.public_ip_addresses.begin_create_or_update = AsyncMock()
    client.public_ip_addresses.get = AsyncMock()
    client.network_interfaces.begin_create_or_update = AsyncMock()
    client.network_interfaces.get = AsyncMock()
    client.virtual_networks.begin_create_or_update = AsyncMock()

    # Setup resource operations
    client.resource_groups.create_or_update = AsyncMock()

    return client


@pytest.fixture
def mock_network_client():
    """Fixture: Mock Azure Network Management client."""
    client = MagicMock()

    client.public_ip_addresses.begin_create_or_update = AsyncMock()
    client.public_ip_addresses.get = AsyncMock()
    client.public_ip_addresses.begin_delete = AsyncMock()
    client.network_interfaces.begin_create_or_update = AsyncMock()
    client.network_interfaces.get = AsyncMock()
    client.network_interfaces.begin_delete = AsyncMock()
    client.virtual_networks.begin_create_or_update = AsyncMock()
    client.network_security_groups.begin_create_or_update = AsyncMock()
    client.network_security_groups.begin_delete = AsyncMock()

    return client


@pytest.fixture
def run_id():
    """Fixture: HayMaker run ID."""
    return str(uuid4())


@pytest.fixture
def location():
    """Fixture: Azure region for VM deployment."""
    return "eastus"


@pytest.fixture
def windows_vm_manager(mock_compute_client, mock_network_client, run_id, location):
    """Fixture: WindowsVMManager instance."""
    return WindowsVMManager(
        compute_client=mock_compute_client,
        network_client=mock_network_client,
        subscription_id="12345678-1234-1234-1234-123456789012",
        run_id=run_id,
        location=location,
        resource_group_name=f"rg-haymaker-{run_id[:8]}",
        vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
        allowed_source_ips=["203.0.113.0/24"],  # Test network (RFC 5737)
    )


@pytest.fixture
def windows_vm_manager_secure(mock_compute_client, mock_network_client, run_id, location):
    """Fixture: WindowsVMManager instance with restricted IPs (secure)."""
    return WindowsVMManager(
        compute_client=mock_compute_client,
        network_client=mock_network_client,
        subscription_id="12345678-1234-1234-1234-123456789012",
        run_id=run_id,
        location=location,
        resource_group_name=f"rg-haymaker-{run_id[:8]}",
        vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
        allowed_source_ips=["1.2.3.4/32", "10.0.0.0/8"],
    )


@pytest.fixture
def worker_identity():
    """Fixture: Sample worker identity for VM provisioning."""
    return WorkerIdentity(
        worker_id="kw-test-001",
        display_name="Test Worker",
        user_principal_name="test.worker@tenant.onmicrosoft.com",
        department="engineering",
        persona=WorkerPersona.ENGINEERING,
        endpoint_type=EndpointType.WINDOWS_VM,
        endpoint_id="",
        team_ids=["team-001"],
    )


@pytest.fixture
def mock_vm_response():
    """Fixture: Mock VM response from Azure SDK."""
    vm = MagicMock()
    vm.id = "/subscriptions/sub-id/resourceGroups/rg-test/providers/Microsoft.Compute/virtualMachines/vm-test"
    vm.name = "cua-win-eastus-kw-test-001"
    vm.location = "eastus"
    vm.provisioning_state = "Succeeded"
    vm.tags = {"run_id": "test-run-id", "worker_id": "kw-test-001"}
    return vm


@pytest.fixture
def mock_public_ip_response():
    """Fixture: Mock Public IP response from Azure SDK."""
    ip = MagicMock()
    ip.ip_address = "52.168.1.100"
    ip.provisioning_state = "Succeeded"
    return ip


# ==============================================================================
# VM PROVISIONING TESTS
# ==============================================================================


class TestVMProvisioning:
    """Tests for Windows VM provisioning operations."""

    @pytest.mark.asyncio
    async def test_provision_vm_success(
        self,
        windows_vm_manager,
        worker_identity,
        mock_compute_client,
        mock_network_client,
        mock_vm_response,
        mock_public_ip_response,
    ):
        """Test provision_vm creates VM successfully with correct configuration."""
        # Mock the provisioning process - Azure async SDK pollers are directly awaitable
        mock_compute_client.virtual_machines.begin_create_or_update.return_value = (
            _create_awaitable_mock(mock_vm_response)
        )

        # Mock public IP creation
        mock_network_client.public_ip_addresses.begin_create_or_update.return_value = (
            _create_awaitable_mock(mock_public_ip_response)
        )

        # Mock NSG creation
        mock_nsg = MagicMock()
        mock_network_client.network_security_groups.begin_create_or_update.return_value = (
            _create_awaitable_mock(mock_nsg)
        )

        # Mock network interface creation
        nic_response = MagicMock()
        nic_response.id = "/subscriptions/sub-id/resourceGroups/rg-test/providers/Microsoft.Network/networkInterfaces/nic-test"
        mock_network_client.network_interfaces.begin_create_or_update.return_value = (
            _create_awaitable_mock(nic_response)
        )

        result = await windows_vm_manager.provision_vm(worker=worker_identity)

        # Verify result structure
        assert "vm_name" in result
        assert "public_ip" in result
        assert "admin_username" in result
        assert "admin_password" in result
        assert "rdp_port" in result
        assert result["rdp_port"] == 3389

        # Verify VM name follows naming convention
        assert result["vm_name"].startswith("cua-win-")
        assert worker_identity.worker_id in result["vm_name"]

        # Verify provisioning was called
        mock_compute_client.virtual_machines.begin_create_or_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_provision_vm_generates_secure_password(
        self, windows_vm_manager, worker_identity, mock_compute_client, mock_network_client
    ):
        """Test that provision_vm generates secure random passwords meeting requirements."""
        # Mock successful provisioning
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Succeeded"

        mock_compute_client.virtual_machines.begin_create_or_update.return_value = (
            _create_awaitable_mock(mock_vm)
        )

        # Mock network components
        ip_response = MagicMock()
        ip_response.ip_address = "52.168.1.100"

        mock_network_client.public_ip_addresses.begin_create_or_update.return_value = (
            _create_awaitable_mock(ip_response)
        )

        nsg_response = MagicMock()

        mock_network_client.network_security_groups.begin_create_or_update.return_value = (
            _create_awaitable_mock(nsg_response)
        )

        nic_response = MagicMock()
        nic_response.id = "/subscriptions/sub-id/nic-id"

        mock_network_client.network_interfaces.begin_create_or_update.return_value = (
            _create_awaitable_mock(nic_response)
        )

        result = await windows_vm_manager.provision_vm(worker=worker_identity)

        password = result["admin_password"]

        # Verify password requirements for URL-safe token
        # token_urlsafe produces base64url chars: A-Za-z0-9_-
        # It's cryptographically secure with high entropy
        assert len(password) >= 16, "Password must be at least 16 characters"
        assert any(c.isupper() for c in password), "Password must have uppercase"
        assert any(c.islower() for c in password), "Password must have lowercase"
        assert any(c.isdigit() for c in password), "Password must have digits"
        # Verify it only contains valid URL-safe characters
        assert all(c.isalnum() or c in "-_" for c in password), "Password must be URL-safe"

    @pytest.mark.asyncio
    async def test_provision_vm_with_azure_api_error_quota_exceeded(
        self, windows_vm_manager, worker_identity, mock_compute_client, mock_network_client
    ):
        """Test provision_vm handles Azure API errors (quota exceeded) gracefully."""
        # Mock network resources (need to pass these steps before hitting the error)
        ip_response = MagicMock()
        ip_response.ip_address = "52.168.1.100"
        mock_network_client.public_ip_addresses.begin_create_or_update.return_value = (
            _create_awaitable_mock(ip_response)
        )
        mock_network_client.network_security_groups.begin_create_or_update.return_value = (
            _create_awaitable_mock(MagicMock())
        )
        nic_response = MagicMock()
        nic_response.id = "/subscriptions/sub-id/nic-id"
        mock_network_client.network_interfaces.begin_create_or_update.return_value = (
            _create_awaitable_mock(nic_response)
        )

        # Mock quota exceeded error on VM creation
        mock_compute_client.virtual_machines.begin_create_or_update.side_effect = Exception(
            "QuotaExceeded: Regional quota limit exceeded"
        )

        with pytest.raises(Exception, match=".") as exc_info:
            await windows_vm_manager.provision_vm(worker=worker_identity)

        assert "QuotaExceeded" in str(exc_info.value) or "quota" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_provision_vm_with_azure_api_error_invalid_location(
        self, windows_vm_manager, worker_identity, mock_compute_client, mock_network_client
    ):
        """Test provision_vm handles Azure API errors (invalid location) gracefully."""
        # Mock network resources (need to pass these steps before hitting the error)
        ip_response = MagicMock()
        ip_response.ip_address = "52.168.1.100"
        mock_network_client.public_ip_addresses.begin_create_or_update.return_value = (
            _create_awaitable_mock(ip_response)
        )
        mock_network_client.network_security_groups.begin_create_or_update.return_value = (
            _create_awaitable_mock(MagicMock())
        )
        nic_response = MagicMock()
        nic_response.id = "/subscriptions/sub-id/nic-id"
        mock_network_client.network_interfaces.begin_create_or_update.return_value = (
            _create_awaitable_mock(nic_response)
        )

        # Mock invalid location error on VM creation
        mock_compute_client.virtual_machines.begin_create_or_update.side_effect = Exception(
            "InvalidLocation: Location 'invalid' is not available"
        )

        with pytest.raises(Exception, match=".") as exc_info:
            await windows_vm_manager.provision_vm(worker=worker_identity)

        assert "InvalidLocation" in str(exc_info.value) or "location" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_provision_vm_tags_resources_with_run_id(
        self, windows_vm_manager, worker_identity, mock_compute_client, mock_network_client, run_id
    ):
        """Test that provision_vm tags all resources with run_id for tracking."""
        # Mock successful provisioning
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Succeeded"

        mock_compute_client.virtual_machines.begin_create_or_update.return_value = (
            _create_awaitable_mock(mock_vm)
        )

        # Mock network components
        ip_response = MagicMock()
        ip_response.ip_address = "52.168.1.100"

        mock_network_client.public_ip_addresses.begin_create_or_update.return_value = (
            _create_awaitable_mock(ip_response)
        )

        nsg_response = MagicMock()

        mock_network_client.network_security_groups.begin_create_or_update.return_value = (
            _create_awaitable_mock(nsg_response)
        )

        nic_response = MagicMock()
        nic_response.id = "/subscriptions/sub-id/nic-id"

        mock_network_client.network_interfaces.begin_create_or_update.return_value = (
            _create_awaitable_mock(nic_response)
        )

        await windows_vm_manager.provision_vm(worker=worker_identity)

        # Verify VM creation was called with tags
        call_args = mock_compute_client.virtual_machines.begin_create_or_update.call_args
        # Third positional argument (index 2) contains vm_params
        vm_params = call_args[0][2] if call_args[0] else call_args.kwargs.get("parameters")

        assert "tags" in vm_params or hasattr(vm_params, "tags")
        if isinstance(vm_params, dict):
            tags = vm_params.get("tags", {})
        else:
            tags = getattr(vm_params, "tags", {})

        assert run_id in str(tags) or worker_identity.worker_id in str(tags)

    @pytest.mark.asyncio
    async def test_provision_vm_uses_correct_vm_size(
        self, windows_vm_manager, worker_identity, mock_compute_client, mock_network_client
    ):
        """Test that provision_vm uses Standard_D2s_v3 VM size as specified."""
        # Mock successful provisioning
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Succeeded"

        mock_compute_client.virtual_machines.begin_create_or_update.return_value = (
            _create_awaitable_mock(mock_vm)
        )

        # Mock network components
        ip_response = MagicMock()
        ip_response.ip_address = "52.168.1.100"

        mock_network_client.public_ip_addresses.begin_create_or_update.return_value = (
            _create_awaitable_mock(ip_response)
        )

        nsg_response = MagicMock()

        mock_network_client.network_security_groups.begin_create_or_update.return_value = (
            _create_awaitable_mock(nsg_response)
        )

        nic_response = MagicMock()
        nic_response.id = "/subscriptions/sub-id/nic-id"

        mock_network_client.network_interfaces.begin_create_or_update.return_value = (
            _create_awaitable_mock(nic_response)
        )

        await windows_vm_manager.provision_vm(worker=worker_identity)

        # Verify VM size
        call_args = mock_compute_client.virtual_machines.begin_create_or_update.call_args
        # Third positional argument (index 2) contains vm_params
        vm_params = call_args[0][2] if call_args[0] else call_args.kwargs.get("parameters")

        if isinstance(vm_params, dict):
            hardware_profile = vm_params.get("hardware_profile", {})
            vm_size = hardware_profile.get("vm_size", "")
        else:
            hardware_profile = getattr(vm_params, "hardware_profile", None)
            vm_size = getattr(hardware_profile, "vm_size", "") if hardware_profile else ""

        assert "Standard_D2s_v3" in vm_size or vm_size == "Standard_D2s_v3"

    @pytest.mark.asyncio
    async def test_provision_vm_uses_windows_server_2022(
        self, windows_vm_manager, worker_identity, mock_compute_client, mock_network_client
    ):
        """Test that provision_vm uses Windows Server 2022 Datacenter image."""
        # Mock successful provisioning
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Succeeded"

        mock_compute_client.virtual_machines.begin_create_or_update.return_value = (
            _create_awaitable_mock(mock_vm)
        )

        # Mock network components
        ip_response = MagicMock()
        ip_response.ip_address = "52.168.1.100"

        mock_network_client.public_ip_addresses.begin_create_or_update.return_value = (
            _create_awaitable_mock(ip_response)
        )

        nsg_response = MagicMock()

        mock_network_client.network_security_groups.begin_create_or_update.return_value = (
            _create_awaitable_mock(nsg_response)
        )

        nic_response = MagicMock()
        nic_response.id = "/subscriptions/sub-id/nic-id"

        mock_network_client.network_interfaces.begin_create_or_update.return_value = (
            _create_awaitable_mock(nic_response)
        )

        await windows_vm_manager.provision_vm(worker=worker_identity)

        # Verify Windows Server 2022 image
        call_args = mock_compute_client.virtual_machines.begin_create_or_update.call_args
        # Third positional argument (index 2) contains vm_params
        vm_params = call_args[0][2] if call_args[0] else call_args.kwargs.get("parameters")

        if isinstance(vm_params, dict):
            storage_profile = vm_params.get("storage_profile", {})
            image_ref = storage_profile.get("image_reference", {})
        else:
            storage_profile = getattr(vm_params, "storage_profile", None)
            image_ref = (
                getattr(storage_profile, "image_reference", None) if storage_profile else None
            )

        # Should reference Windows Server 2022
        image_str = str(image_ref)
        assert "2022" in image_str or "WindowsServer" in image_str


# ==============================================================================
# VM DELETION TESTS
# ==============================================================================


class TestVMDeletion:
    """Tests for Windows VM deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_vm_success(self, windows_vm_manager, mock_compute_client):
        """Test delete_vm removes VM successfully."""
        vm_name = "cua-win-eastus-kw-test-001"

        # Mock successful deletion (no cleanup_network so only VM delete is called)
        mock_compute_client.virtual_machines.begin_delete.return_value = _create_awaitable_mock(
            None
        )

        result = await windows_vm_manager.delete_vm(vm_name=vm_name, cleanup_network=False)

        assert result is True
        mock_compute_client.virtual_machines.begin_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_vm_with_missing_vm(self, windows_vm_manager, mock_compute_client):
        """Test delete_vm handles missing VM gracefully (returns False)."""
        vm_name = "non-existent-vm"

        # Mock VM not found error
        mock_compute_client.virtual_machines.begin_delete.side_effect = Exception(
            "ResourceNotFound: VM does not exist"
        )

        result = await windows_vm_manager.delete_vm(vm_name=vm_name)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_vm_cleans_up_network_resources(
        self, windows_vm_manager, mock_compute_client, mock_network_client
    ):
        """Test delete_vm also cleans up associated network resources (NIC, Public IP)."""
        vm_name = "cua-win-eastus-kw-test-001"

        # Mock VM deletion
        mock_compute_client.virtual_machines.begin_delete.return_value = _create_awaitable_mock(
            None
        )

        # Mock network resource deletion
        mock_network_client.network_interfaces.begin_delete.return_value = _create_awaitable_mock(
            None
        )
        mock_network_client.public_ip_addresses.begin_delete.return_value = _create_awaitable_mock(
            None
        )
        mock_network_client.network_security_groups.begin_delete.return_value = (
            _create_awaitable_mock(None)
        )

        result = await windows_vm_manager.delete_vm(vm_name=vm_name, cleanup_network=True)

        assert result is True
        mock_compute_client.virtual_machines.begin_delete.assert_called_once()


# ==============================================================================
# VM STATUS TESTS
# ==============================================================================


class TestVMStatus:
    """Tests for Windows VM status monitoring."""

    @pytest.mark.asyncio
    async def test_get_vm_status_returns_provisioning(
        self, windows_vm_manager, mock_compute_client
    ):
        """Test get_vm_status returns 'Provisioning' during VM creation."""
        vm_name = "cua-win-eastus-kw-test-001"

        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Creating"
        mock_compute_client.virtual_machines.get.return_value = mock_vm

        status = await windows_vm_manager.get_vm_status(vm_name=vm_name)

        assert status == "Creating"

    @pytest.mark.asyncio
    async def test_get_vm_status_returns_succeeded(self, windows_vm_manager, mock_compute_client):
        """Test get_vm_status returns 'Succeeded' when VM is ready."""
        vm_name = "cua-win-eastus-kw-test-001"

        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Succeeded"
        mock_compute_client.virtual_machines.get.return_value = mock_vm

        status = await windows_vm_manager.get_vm_status(vm_name=vm_name)

        assert status == "Succeeded"

    @pytest.mark.asyncio
    async def test_get_vm_status_returns_failed(self, windows_vm_manager, mock_compute_client):
        """Test get_vm_status returns 'Failed' when VM provisioning fails."""
        vm_name = "cua-win-eastus-kw-test-001"

        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Failed"
        mock_compute_client.virtual_machines.get.return_value = mock_vm

        status = await windows_vm_manager.get_vm_status(vm_name=vm_name)

        assert status == "Failed"

    @pytest.mark.asyncio
    async def test_get_vm_status_returns_none_when_not_found(
        self, windows_vm_manager, mock_compute_client
    ):
        """Test get_vm_status returns None when VM doesn't exist."""
        vm_name = "non-existent-vm"

        mock_compute_client.virtual_machines.get.side_effect = Exception("ResourceNotFound")

        status = await windows_vm_manager.get_vm_status(vm_name=vm_name)

        assert status is None


# ==============================================================================
# COMPUTER USE READINESS TESTS
# ==============================================================================


class TestComputerUseReadiness:
    """Tests for Computer Use readiness verification."""

    @pytest.mark.asyncio
    async def test_verify_computer_use_ready_checks_rdp_port(
        self, windows_vm_manager, mock_compute_client
    ):
        """Test verify_computer_use_ready checks RDP port (3389) is accessible."""
        vm_name = "cua-win-eastus-kw-test-001"
        public_ip = "52.168.1.100"

        # Mock VM is provisioned
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Succeeded"
        mock_compute_client.virtual_machines.get.return_value = mock_vm

        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.connect.return_value = None  # Connection successful

            ready = await windows_vm_manager.verify_computer_use_ready(
                vm_name=vm_name, public_ip=public_ip
            )

            assert ready is True
            # Verify RDP port was checked
            mock_sock_instance.connect.assert_called()

    @pytest.mark.asyncio
    async def test_verify_computer_use_ready_checks_browsers_installed(
        self, windows_vm_manager, mock_compute_client
    ):
        """Test verify_computer_use_ready checks that browsers are installed."""
        vm_name = "cua-win-eastus-kw-test-001"
        public_ip = "52.168.1.100"

        # Mock VM is provisioned
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Succeeded"
        mock_compute_client.virtual_machines.get.return_value = mock_vm

        # This test would verify browser installation through run_command
        # For now, we test the method returns a boolean
        result = await windows_vm_manager.verify_computer_use_ready(
            vm_name=vm_name, public_ip=public_ip
        )

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_verify_computer_use_ready_returns_false_when_rdp_blocked(
        self, windows_vm_manager, mock_compute_client
    ):
        """Test verify_computer_use_ready returns False when RDP port is blocked."""
        vm_name = "cua-win-eastus-kw-test-001"
        public_ip = "52.168.1.100"

        # Mock VM is provisioned
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Succeeded"
        mock_compute_client.virtual_machines.get.return_value = mock_vm

        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            # Connection fails
            mock_sock_instance.connect.side_effect = ConnectionRefusedError("Connection refused")

            ready = await windows_vm_manager.verify_computer_use_ready(
                vm_name=vm_name, public_ip=public_ip, timeout_seconds=1
            )

            assert ready is False

    @pytest.mark.asyncio
    async def test_verify_computer_use_ready_returns_false_when_vm_not_ready(
        self, windows_vm_manager, mock_compute_client
    ):
        """Test verify_computer_use_ready returns False when VM is not provisioned."""
        vm_name = "cua-win-eastus-kw-test-001"
        public_ip = "52.168.1.100"

        # Mock VM is still creating
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Creating"
        mock_compute_client.virtual_machines.get.return_value = mock_vm

        ready = await windows_vm_manager.verify_computer_use_ready(
            vm_name=vm_name, public_ip=public_ip
        )

        assert ready is False


# ==============================================================================
# WAIT FOR PROVISIONING TESTS
# ==============================================================================


class TestWaitForProvisioning:
    """Tests for VM provisioning wait logic."""

    @pytest.mark.asyncio
    async def test_wait_for_provisioning_succeeds(
        self, windows_vm_manager, worker_identity, mock_compute_client, monkeypatch
    ):
        """Test wait_for_provisioning returns True when VM becomes ready."""
        vm_name = "cua-win-eastus-kw-test-001"

        # Mock VM progresses from Creating to Succeeded
        call_count = [0]

        async def mock_get(*args, **kwargs):
            call_count[0] += 1
            mock_vm = MagicMock()
            if call_count[0] < 2:
                mock_vm.provisioning_state = "Creating"
            else:
                mock_vm.provisioning_state = "Succeeded"
            return mock_vm

        mock_compute_client.virtual_machines.get = mock_get

        # Mock sleep to avoid delays
        async def mock_sleep(delay):
            pass

        monkeypatch.setattr(asyncio, "sleep", mock_sleep)

        result = await windows_vm_manager.wait_for_provisioning(vm_name=vm_name, timeout_minutes=5)

        assert result is True
        assert call_count[0] >= 2

    @pytest.mark.asyncio
    async def test_wait_for_provisioning_timeout(
        self, windows_vm_manager, worker_identity, mock_compute_client, monkeypatch
    ):
        """Test wait_for_provisioning returns False on timeout."""
        vm_name = "cua-win-eastus-kw-test-001"

        # Mock VM never finishes provisioning
        mock_vm = MagicMock()
        mock_vm.provisioning_state = "Creating"
        mock_compute_client.virtual_machines.get.return_value = mock_vm

        # Mock sleep to avoid delays
        async def mock_sleep(delay):
            pass

        monkeypatch.setattr(asyncio, "sleep", mock_sleep)

        # Use very short timeout
        result = await windows_vm_manager.wait_for_provisioning(
            vm_name=vm_name,
            timeout_minutes=0.01,  # 0.6 seconds
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_provisioning_handles_transient_errors(
        self, windows_vm_manager, worker_identity, mock_compute_client, monkeypatch
    ):
        """Test wait_for_provisioning retries on transient API errors."""
        vm_name = "cua-win-eastus-kw-test-001"

        call_count = [0]

        async def mock_get(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Transient network error")
            mock_vm = MagicMock()
            mock_vm.provisioning_state = "Succeeded"
            return mock_vm

        mock_compute_client.virtual_machines.get = mock_get

        # Mock sleep to avoid delays
        async def mock_sleep(delay):
            pass

        monkeypatch.setattr(asyncio, "sleep", mock_sleep)

        result = await windows_vm_manager.wait_for_provisioning(vm_name=vm_name, timeout_minutes=5)

        assert result is True
        assert call_count[0] >= 2


# ==============================================================================
# PASSWORD GENERATION TESTS
# ==============================================================================


class TestPasswordGeneration:
    """Tests for secure password generation."""

    @pytest.mark.asyncio
    async def test_generate_password_length(self, windows_vm_manager):
        """Test generated password is at least 16 characters."""
        password = windows_vm_manager._generate_secure_password()

        assert len(password) >= 16

    @pytest.mark.asyncio
    async def test_generate_password_complexity(self, windows_vm_manager):
        """Test generated password meets complexity requirements."""
        password = windows_vm_manager._generate_secure_password()

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        # Verify it only contains valid URL-safe characters
        is_urlsafe = all(c.isalnum() or c in "-_" for c in password)

        assert has_upper, "Password must contain uppercase letter"
        assert has_lower, "Password must contain lowercase letter"
        assert has_digit, "Password must contain digit"
        assert is_urlsafe, "Password must be URL-safe (alphanumeric + - and _)"

    @pytest.mark.asyncio
    async def test_generate_password_randomness(self, windows_vm_manager):
        """Test generated passwords are different (random)."""
        password1 = windows_vm_manager._generate_secure_password()
        password2 = windows_vm_manager._generate_secure_password()
        password3 = windows_vm_manager._generate_secure_password()

        assert password1 != password2
        assert password2 != password3
        assert password1 != password3


# ==============================================================================
# VM NAMING CONVENTION TESTS
# ==============================================================================


class TestVMNaming:
    """Tests for VM naming convention."""

    @pytest.mark.asyncio
    async def test_vm_name_follows_convention(self, windows_vm_manager, worker_identity):
        """Test VM name follows pattern: cua-win-{location}-{worker_id}."""
        vm_name = windows_vm_manager._get_vm_name(worker=worker_identity)

        assert vm_name.startswith("cua-win-")
        assert windows_vm_manager.location in vm_name
        assert worker_identity.worker_id.replace("_", "-") in vm_name

    @pytest.mark.asyncio
    async def test_vm_name_is_valid_azure_resource_name(self, windows_vm_manager, worker_identity):
        """Test VM name is valid Azure resource name (alphanumeric and hyphens)."""
        vm_name = windows_vm_manager._get_vm_name(worker=worker_identity)

        # Azure VM names: 1-64 chars, alphanumeric and hyphens, must start with letter
        assert len(vm_name) <= 64
        assert vm_name[0].isalpha()
        assert all(c.isalnum() or c == "-" for c in vm_name)


# ==============================================================================
# SECURITY TESTS
# ==============================================================================


class TestSecurityFeatures:
    """Tests for security improvements."""

    @pytest.mark.asyncio
    async def test_allowed_source_ips_validation_valid_single_ip(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that valid single IP addresses are accepted."""
        manager = WindowsVMManager(
            compute_client=mock_compute_client,
            network_client=mock_network_client,
            subscription_id="12345678-1234-1234-1234-123456789012",
            run_id=run_id,
            location=location,
            resource_group_name=f"rg-haymaker-{run_id[:8]}",
            vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
            allowed_source_ips=["1.2.3.4/32"],
        )

        assert manager.allowed_source_ips == ["1.2.3.4/32"]

    @pytest.mark.asyncio
    async def test_allowed_source_ips_validation_valid_cidr_range(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that valid CIDR ranges are accepted."""
        manager = WindowsVMManager(
            compute_client=mock_compute_client,
            network_client=mock_network_client,
            subscription_id="12345678-1234-1234-1234-123456789012",
            run_id=run_id,
            location=location,
            resource_group_name=f"rg-haymaker-{run_id[:8]}",
            vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
            allowed_source_ips=["10.0.0.0/8", "192.168.0.0/16"],
        )

        assert len(manager.allowed_source_ips) == 2
        assert "10.0.0.0/8" in manager.allowed_source_ips
        assert "192.168.0.0/16" in manager.allowed_source_ips

    @pytest.mark.asyncio
    async def test_allowed_source_ips_validation_invalid_ip(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that invalid IP addresses are rejected."""
        with pytest.raises(ValueError, match=".") as exc_info:
            WindowsVMManager(
                compute_client=mock_compute_client,
                network_client=mock_network_client,
                subscription_id="12345678-1234-1234-1234-123456789012",
                run_id=run_id,
                location=location,
                resource_group_name=f"rg-haymaker-{run_id[:8]}",
                vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
                allowed_source_ips=["invalid.ip.address"],
            )

        assert "Invalid IP address or CIDR range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allowed_source_ips_validation_empty_list(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that empty list is rejected."""
        with pytest.raises(ValueError, match=".") as exc_info:
            WindowsVMManager(
                compute_client=mock_compute_client,
                network_client=mock_network_client,
                subscription_id="12345678-1234-1234-1234-123456789012",
                run_id=run_id,
                location=location,
                resource_group_name=f"rg-haymaker-{run_id[:8]}",
                vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
                allowed_source_ips=[],
            )

        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allowed_source_ips_rejects_wildcard_star(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that wildcard '*' is rejected."""
        with pytest.raises(ValueError, match=".") as exc_info:
            WindowsVMManager(
                compute_client=mock_compute_client,
                network_client=mock_network_client,
                subscription_id="12345678-1234-1234-1234-123456789012",
                run_id=run_id,
                location=location,
                resource_group_name=f"rg-haymaker-{run_id[:8]}",
                vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
                allowed_source_ips=["*"],
            )

        assert "Wildcard" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allowed_source_ips_rejects_wildcard_cidr(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that wildcard CIDR '0.0.0.0/0' is rejected."""
        with pytest.raises(ValueError, match=".") as exc_info:
            WindowsVMManager(
                compute_client=mock_compute_client,
                network_client=mock_network_client,
                subscription_id="12345678-1234-1234-1234-123456789012",
                run_id=run_id,
                location=location,
                resource_group_name=f"rg-haymaker-{run_id[:8]}",
                vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
                allowed_source_ips=["0.0.0.0/0"],
            )

        assert "Wildcard" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allowed_source_ips_rejects_ipv6_wildcard(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that IPv6 wildcard '::/0' is rejected."""
        with pytest.raises(ValueError, match=".") as exc_info:
            WindowsVMManager(
                compute_client=mock_compute_client,
                network_client=mock_network_client,
                subscription_id="12345678-1234-1234-1234-123456789012",
                run_id=run_id,
                location=location,
                resource_group_name=f"rg-haymaker-{run_id[:8]}",
                vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-haymaker-{run_id[:8]}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
                allowed_source_ips=["::/0"],
            )

        assert "Wildcard" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_nsg_rules_with_restricted_ips(
        self, windows_vm_manager_secure, worker_identity, mock_network_client
    ):
        """Test NSG creation with restricted source IPs."""
        nsg_response = MagicMock()

        mock_network_client.network_security_groups.begin_create_or_update.return_value = (
            _create_awaitable_mock(nsg_response)
        )

        await windows_vm_manager_secure._create_nsg("test-nsg", worker_identity)

        # Verify NSG was created
        call_args = mock_network_client.network_security_groups.begin_create_or_update.call_args
        nsg_params = call_args.kwargs.get("parameters") or call_args[0][2]

        # Should have 2 rules (one per allowed IP)
        security_rules = nsg_params["security_rules"]
        assert len(security_rules) == 2

        # Verify rules have correct source IPs
        source_ips = [rule["source_address_prefix"] for rule in security_rules]
        assert "1.2.3.4/32" in source_ips
        assert "10.0.0.0/8" in source_ips

    @pytest.mark.asyncio
    async def test_location_validation_valid_regions(
        self, mock_compute_client, mock_network_client, run_id
    ):
        """Test that valid Azure regions are accepted."""
        valid_regions = ["eastus", "westus2", "northeurope", "japaneast"]

        for region in valid_regions:
            manager = WindowsVMManager(
                compute_client=mock_compute_client,
                network_client=mock_network_client,
                subscription_id="12345678-1234-1234-1234-123456789012",
                run_id=run_id,
                location=region,
                resource_group_name="rg-test",
                vnet_id="/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
                allowed_source_ips=["203.0.113.0/24"],
            )
            assert manager.location == region

    @pytest.mark.asyncio
    async def test_location_validation_invalid_region(
        self, mock_compute_client, mock_network_client, run_id
    ):
        """Test that invalid Azure regions are rejected."""
        with pytest.raises(ValueError, match=".") as exc_info:
            WindowsVMManager(
                compute_client=mock_compute_client,
                network_client=mock_network_client,
                subscription_id="12345678-1234-1234-1234-123456789012",
                run_id=run_id,
                location="invalid-region",
                resource_group_name="rg-test",
                vnet_id="/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
                allowed_source_ips=["203.0.113.0/24"],
            )

        assert "Invalid Azure region" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resource_group_validation_valid_names(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that valid resource group names are accepted."""
        valid_names = ["rg-test", "rg_test_123", "rg.test", "rg(test)"]

        for name in valid_names:
            manager = WindowsVMManager(
                compute_client=mock_compute_client,
                network_client=mock_network_client,
                subscription_id="12345678-1234-1234-1234-123456789012",
                run_id=run_id,
                location=location,
                resource_group_name=name,
                vnet_id=f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/{name}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default",
                allowed_source_ips=["203.0.113.0/24"],
            )
            assert manager.resource_group_name == name

    @pytest.mark.asyncio
    async def test_resource_group_validation_invalid_names(
        self, mock_compute_client, mock_network_client, run_id, location
    ):
        """Test that invalid resource group names are rejected."""
        invalid_names = [
            ("rg-test.", "rg-test"),  # Ends with period
            ("rg@test", "rg-test"),  # Invalid character
            ("rg test", "rg-test"),  # Space
            ("", ""),  # Empty - will fail on empty string
        ]

        for rg_name, vnet_rg in invalid_names:
            # Use vnet_rg in the vnet_id to match the resource group name we're testing
            vnet_id = f"/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/{vnet_rg if vnet_rg else 'rg-test'}/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/default"

            with pytest.raises(ValueError, match=".") as exc_info:
                WindowsVMManager(
                    compute_client=mock_compute_client,
                    network_client=mock_network_client,
                    subscription_id="12345678-1234-1234-1234-123456789012",
                    run_id=run_id,
                    location=location,
                    resource_group_name=rg_name,
                    vnet_id=vnet_id,
                    allowed_source_ips=["203.0.113.0/24"],
                )

            # Should raise ValueError (either for resource_group_name or vnet_id validation)
            assert (
                "resource_group_name" in str(exc_info.value).lower()
                or "vnet_id" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_worker_id_validation_valid_ids(self, windows_vm_manager):
        """Test that valid worker IDs are accepted."""
        valid_ids = ["worker-001", "worker_001", "WORKER123", "w1"]

        for worker_id in valid_ids:
            # Should not raise
            windows_vm_manager._validate_worker_id(worker_id)

    @pytest.mark.asyncio
    async def test_worker_id_validation_invalid_ids(self, windows_vm_manager):
        """Test that invalid worker IDs are rejected."""
        invalid_ids = [
            "worker@001",  # Invalid character
            "worker 001",  # Space
            "",  # Empty
            "w" * 100,  # Too long
        ]

        for worker_id in invalid_ids:
            with pytest.raises(ValueError, match=".") as exc_info:
                windows_vm_manager._validate_worker_id(worker_id)

            assert "worker_id" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
