"""Azure Windows VM management for Computer Use Agents.

Provides Windows VM provisioning as a fallback when Cloud PCs are unavailable.
VMs are configured with RDP access, browsers, and Desktop Experience for
Computer Use Agent capabilities.

This module is a facade that delegates to specialized submodules:
- vm_config: Configuration models and validation
- security_validator: Security enforcement and IP whitelisting
- network_manager: Network resource management
- vm_provisioner: VM lifecycle operations

SECURITY REQUIREMENTS:
    This module enforces security-first design:
    - allowed_source_ips parameter is REQUIRED (no wildcards allowed)
    - Admin password generation uses cryptographic randomness
    - Network security groups reject wildcard IP ranges ('*', '0.0.0.0/0')
    - Public IP addresses require explicit IP whitelisting

    BREAKING CHANGE: allowed_source_ips is now REQUIRED.
    Must specify explicit IPs/ranges: allowed_source_ips=["203.0.113.0/24"]

Example:
    >>> manager = WindowsVMManager(
    ...     compute_client=compute_client,
    ...     network_client=network_client,
    ...     subscription_id="sub-id",
    ...     run_id="run-123",
    ...     location="eastus",
    ...     resource_group_name="my-rg",
    ...     vnet_id="/subscriptions/.../subnets/default",
    ...     allowed_source_ips=["203.0.113.0/24"]
    ... )
    >>> vm_details = await manager.provision_vm(worker)
    >>> await manager.delete_vm(vm_name)
"""

import logging
from typing import Any

from azure_haymaker.knowledge_worker.endpoints.network_manager import NetworkResourceManager
from azure_haymaker.knowledge_worker.endpoints.security_validator import (
    SecurityValidator,
    verify_computer_use_ready,
)
from azure_haymaker.knowledge_worker.endpoints.vm_config import (
    DEFAULT_VM_SIZE,
    PROVISIONING_CHECK_INTERVAL_SECONDS,
    PROVISIONING_TIMEOUT_MINUTES,
    RDP_PORT,
    VALID_AZURE_REGIONS,
    AzureRegionValidator,
    ResourceValidator,
    VMConfig,
)
from azure_haymaker.knowledge_worker.endpoints.vm_provisioner import VMProvisioner
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

logger = logging.getLogger(__name__)


class WindowsVMManager:
    """Provisions and manages Azure Windows VMs for Computer Use Agents.

    Uses Azure Compute and Network SDKs for VM management:
    - VM provisioning with Windows Server 2022
    - Network configuration (Public IP, NSG, NIC)
    - RDP access setup
    - Computer use readiness verification

    VMs provide fallback compute for Computer Use Agents when Cloud PCs
    are unavailable or quota exceeded.

    SECURITY CONSIDERATIONS:
        - Admin passwords are returned in plaintext (required for Computer Use Agents)
        - For production, store passwords in Azure Key Vault after provisioning
        - allowed_source_ips is REQUIRED and must contain explicit IPs/ranges
        - Wildcard IPs ('*', '0.0.0.0/0') are rejected at initialization

    Attributes:
        compute_client: Azure Compute Management client
        network_client: Azure Network Management client
        subscription_id: Azure subscription ID for resource IDs
        run_id: HayMaker run ID for resource tagging
        location: Azure region for VM deployment
        resource_group_name: Resource group for VM resources
        vm_size: Azure VM size (default: Standard_D2s_v3)
        allowed_source_ips: List of IP addresses/CIDR ranges allowed RDP access
    """

    DEFAULT_VM_SIZE = DEFAULT_VM_SIZE
    DEFAULT_IMAGE_PUBLISHER = "MicrosoftWindowsServer"
    DEFAULT_IMAGE_OFFER = "WindowsServer"
    DEFAULT_IMAGE_SKU = "2022-datacenter-azure-edition"
    DEFAULT_IMAGE_VERSION = "latest"
    PROVISIONING_TIMEOUT_MINUTES = PROVISIONING_TIMEOUT_MINUTES
    PROVISIONING_CHECK_INTERVAL_SECONDS = PROVISIONING_CHECK_INTERVAL_SECONDS
    RDP_PORT = RDP_PORT
    VALID_AZURE_REGIONS = VALID_AZURE_REGIONS

    def __init__(
        self,
        compute_client: Any,
        network_client: Any,
        subscription_id: str,
        run_id: str,
        location: str,
        resource_group_name: str,
        vnet_id: str,
        allowed_source_ips: list[str],
        vm_size: str | None = None,
    ):
        """Initialize WindowsVMManager.

        Args:
            compute_client: Azure Compute Management client
            network_client: Azure Network Management client
            subscription_id: Azure subscription ID for resource IDs
            run_id: HayMaker run ID for resource tagging
            location: Azure region for VM deployment
            resource_group_name: Resource group name for VM resources
            vnet_id: Full Azure Resource ID of the Virtual Network
                Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet}
            allowed_source_ips: REQUIRED list of IP addresses/CIDR ranges allowed RDP access.
                Must be specific IPs/ranges, wildcards are rejected.
                Examples: ["1.2.3.4/32"], ["10.0.0.0/8", "192.168.1.0/24"]
            vm_size: Azure VM size (default: Standard_D2s_v3)

        Raises:
            ValueError: If input validation fails

        Security Note:
            allowed_source_ips is REQUIRED and cannot be None or contain wildcards.
            This prevents accidental exposure of RDP to the entire internet.
        """
        # Input validation
        AzureRegionValidator.validate(location)
        ResourceValidator.validate_resource_group(resource_group_name)
        ResourceValidator.validate_vnet_id(vnet_id)

        # Store attributes for compatibility
        self.compute_client = compute_client
        self.network_client = network_client
        self.subscription_id = subscription_id
        self.run_id = run_id
        self.location = location
        self.resource_group_name = resource_group_name
        self.vnet_id = vnet_id
        self.vm_size = vm_size or self.DEFAULT_VM_SIZE

        # Initialize configuration
        self.config = VMConfig(
            location=location,
            resource_group_name=resource_group_name,
            vnet_id=vnet_id,
            vm_size=self.vm_size,
        )

        # Initialize security validator
        security_validator = SecurityValidator()
        self.allowed_source_ips = security_validator.validate_ip_addresses(allowed_source_ips)
        logger.info(f"NSG configured with {len(self.allowed_source_ips)} allowed source IP ranges")

        # Initialize managers
        self.network_manager = NetworkResourceManager(network_client, subscription_id)
        self.vm_provisioner = VMProvisioner(compute_client, subscription_id, run_id)

    # Validation methods for backward compatibility
    def _validate_location(self, location: str) -> None:
        """Validate Azure region (backward compatibility).

        Args:
            location: Azure region to validate

        Raises:
            ValueError: If location is invalid
        """
        AzureRegionValidator.validate(location)

    def _validate_resource_group_name(self, resource_group_name: str) -> None:
        """Validate resource group name (backward compatibility).

        Args:
            resource_group_name: Resource group name to validate

        Raises:
            ValueError: If resource group name is invalid
        """
        ResourceValidator.validate_resource_group(resource_group_name)

    def _validate_vnet_id(self, vnet_id: str) -> None:
        """Validate Virtual Network subnet ID (backward compatibility).

        Args:
            vnet_id: Virtual Network subnet resource ID to validate

        Raises:
            ValueError: If vnet_id is invalid or missing
        """
        ResourceValidator.validate_vnet_id(vnet_id)

    def _validate_ip_addresses(self, ip_list: list[str]) -> list[str]:
        """Validate IP addresses/CIDR ranges (backward compatibility).

        Args:
            ip_list: List of IP addresses or CIDR ranges

        Returns:
            Validated list of IP addresses/CIDR ranges

        Raises:
            ValueError: If any IP address/range is invalid or contains wildcards
        """
        security_validator = SecurityValidator()
        return security_validator.validate_ip_addresses(ip_list)

    def _validate_worker_id(self, worker_id: str) -> None:
        """Validate worker ID format (backward compatibility).

        Args:
            worker_id: Worker ID to validate

        Raises:
            ValueError: If worker ID is invalid
        """
        ResourceValidator.validate_worker_id(worker_id)

    def _generate_secure_password(self) -> str:
        """Generate a secure random password (backward compatibility).

        Returns:
            Secure random password (32+ characters)
        """
        return VMProvisioner.generate_secure_password()

    def _get_vm_name(self, worker: WorkerIdentity) -> str:
        """Generate VM name (backward compatibility).

        Args:
            worker: Worker identity

        Returns:
            VM name: cua-win-{location}-{worker_id}

        Raises:
            ValueError: If worker_id is invalid
        """
        return self.config.get_vm_name(worker, self.location)

    def _get_computer_name(self, vm_name: str) -> str:
        """Generate unique 15-char computer name (backward compatibility).

        Args:
            vm_name: Full VM name

        Returns:
            Unique computer name (15 chars max)
        """
        return VMConfig.get_computer_name(vm_name)

    async def provision_vm(self, worker: WorkerIdentity) -> dict[str, Any]:
        """Provision a Windows VM for a worker.

        Delegates to VMProvisioner for full provisioning workflow.

        Args:
            worker: Worker identity to provision VM for

        Returns:
            Dictionary with VM details (see VMProvisioner.provision_vm)

        Raises:
            ValueError: If worker_id validation fails
            Exception: If VM provisioning fails
        """
        return await self.vm_provisioner.provision_vm(
            worker=worker,
            network_manager=self.network_manager,
            config=self.config,
            allowed_source_ips=self.allowed_source_ips,
        )

    async def _create_public_ip(self, public_ip_name: str, worker: WorkerIdentity) -> str:
        """Create a public IP address (backward compatibility).

        Args:
            public_ip_name: Name for the public IP
            worker: Worker identity for tagging

        Returns:
            Public IP address string
        """
        tags = {
            "run_id": self.run_id,
            "worker_id": worker.worker_id,
        }
        return await self.network_manager.create_public_ip(
            name=public_ip_name,
            location=self.location,
            tags=tags,
            resource_group=self.resource_group_name,
        )

    async def _create_nsg(self, nsg_name: str, worker: WorkerIdentity) -> None:
        """Create Network Security Group with RDP rule (backward compatibility).

        Args:
            nsg_name: Name for the NSG
            worker: Worker identity for tagging
        """
        tags = {
            "run_id": self.run_id,
            "worker_id": worker.worker_id,
        }
        await self.network_manager.create_nsg(
            name=nsg_name,
            location=self.location,
            tags=tags,
            resource_group=self.resource_group_name,
            allowed_ips=self.allowed_source_ips,
            rdp_port=self.RDP_PORT,
        )

    async def _create_nic(
        self, nic_name: str, public_ip_name: str, nsg_name: str, worker: WorkerIdentity
    ) -> str:
        """Create Network Interface (backward compatibility).

        Args:
            nic_name: Name for the NIC
            public_ip_name: Name of the public IP to associate
            nsg_name: Name of the NSG to associate
            worker: Worker identity for tagging

        Returns:
            NIC resource ID
        """
        tags = {
            "run_id": self.run_id,
            "worker_id": worker.worker_id,
        }
        return await self.network_manager.create_nic(
            name=nic_name,
            location=self.location,
            tags=tags,
            resource_group=self.resource_group_name,
            subnet_id=self.vnet_id,
            public_ip_name=public_ip_name,
            nsg_name=nsg_name,
        )

    async def _create_vm(
        self,
        vm_name: str,
        nic_id: str,
        admin_username: str,
        admin_password: str,
        worker: WorkerIdentity,
    ) -> None:
        """Create the Virtual Machine (backward compatibility).

        Args:
            vm_name: VM name
            nic_id: Network interface resource ID
            admin_username: Admin username
            admin_password: Admin password
            worker: Worker identity for tagging
        """
        tags = {
            "run_id": self.run_id,
            "worker_id": worker.worker_id,
        }
        await self.vm_provisioner.create_vm(
            vm_name=vm_name,
            nic_id=nic_id,
            admin_username=admin_username,
            admin_password=admin_password,
            location=self.location,
            vm_size=self.vm_size,
            resource_group=self.resource_group_name,
            tags=tags,
        )

    async def delete_vm(self, vm_name: str, cleanup_network: bool = True) -> bool:
        """Delete a VM and optionally its network resources.

        Delegates to VMProvisioner for deletion.

        Args:
            vm_name: VM name to delete
            cleanup_network: Whether to delete associated network resources

        Returns:
            True if deleted successfully, False otherwise
        """
        return await self.vm_provisioner.delete_vm(
            vm_name=vm_name,
            resource_group=self.resource_group_name,
            cleanup_network=cleanup_network,
            network_manager=self.network_manager,
        )

    async def _cleanup_network_resources(self, vm_name: str) -> None:
        """Clean up network resources (backward compatibility).

        Args:
            vm_name: VM name whose resources to clean up
        """
        await self.network_manager.cleanup_network_resources(
            vm_name=vm_name,
            resource_group=self.resource_group_name,
        )

    async def get_vm_status(self, vm_name: str) -> str | None:
        """Get VM provisioning status.

        Delegates to VMProvisioner.

        Args:
            vm_name: VM name to check

        Returns:
            Provisioning state string or None if VM not found
        """
        return await self.vm_provisioner.get_vm_status(
            vm_name=vm_name,
            resource_group=self.resource_group_name,
        )

    async def verify_computer_use_ready(
        self,
        vm_name: str,
        public_ip: str,
        timeout_seconds: int = 30,
    ) -> bool:
        """Verify VM is ready for Computer Use Agent.

        Delegates to security_validator module.

        Args:
            vm_name: VM name to verify
            public_ip: Public IP address of VM
            timeout_seconds: Socket connection timeout

        Returns:
            True if VM is ready for Computer Use, False otherwise
        """

        async def get_status_func(name: str) -> str | None:
            return await self.get_vm_status(name)

        return await verify_computer_use_ready(
            vm_name=vm_name,
            public_ip=public_ip,
            rdp_port=self.RDP_PORT,
            get_vm_status_func=get_status_func,
            timeout_seconds=timeout_seconds,
        )

    async def wait_for_provisioning(self, vm_name: str, timeout_minutes: int | None = None) -> bool:
        """Wait for VM to be provisioned and ready.

        Delegates to VMProvisioner.

        Args:
            vm_name: VM name to wait for
            timeout_minutes: Timeout in minutes (default: 15)

        Returns:
            True if provisioned successfully, False on timeout or error
        """
        return await self.vm_provisioner.wait_for_provisioning(
            vm_name=vm_name,
            resource_group=self.resource_group_name,
            timeout_minutes=timeout_minutes,
        )


__all__ = ["WindowsVMManager"]
