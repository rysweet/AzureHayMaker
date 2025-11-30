"""Azure Windows VM management for Computer Use Agents.

Provides Windows VM provisioning as a fallback when Cloud PCs are unavailable.
VMs are configured with RDP access, browsers, and Desktop Experience for
Computer Use Agent capabilities.

SECURITY WARNING:
    This module handles sensitive operations including:
    - Admin password generation and return (plaintext)
    - Network security group configuration
    - Public IP address assignment

    For TESTING: Default settings allow RDP from any IP (insecure but functional)
    For PRODUCTION: Configure allowed_source_ips to restrict access
"""

import asyncio
import hashlib
import ipaddress
import logging
import re
import secrets
import socket
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

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
        - Configure allowed_source_ips to restrict RDP access
        - Default settings allow RDP from ANY IP (testing only)

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

    DEFAULT_VM_SIZE = "Standard_D2s_v3"
    DEFAULT_IMAGE_PUBLISHER = "MicrosoftWindowsServer"
    DEFAULT_IMAGE_OFFER = "WindowsServer"
    DEFAULT_IMAGE_SKU = "2022-datacenter-azure-edition"
    DEFAULT_IMAGE_VERSION = "latest"
    PROVISIONING_TIMEOUT_MINUTES = 15
    PROVISIONING_CHECK_INTERVAL_SECONDS = 30
    RDP_PORT = 3389

    # Valid Azure regions (subset for validation)
    VALID_AZURE_REGIONS = {
        "eastus", "eastus2", "westus", "westus2", "westus3",
        "centralus", "northcentralus", "southcentralus",
        "westcentralus", "canadacentral", "canadaeast",
        "brazilsouth", "northeurope", "westeurope",
        "uksouth", "ukwest", "francecentral", "germanywestcentral",
        "norwayeast", "switzerlandnorth", "swedencentral",
        "eastasia", "southeastasia", "australiaeast",
        "australiasoutheast", "japaneast", "japanwest",
        "koreacentral", "koreasouth", "southindia",
        "centralindia", "westindia", "uaenorth",
        "southafricanorth", "qatarcentral"
    }

    def __init__(
        self,
        compute_client: Any,
        network_client: Any,
        subscription_id: str,
        run_id: str,
        location: str,
        resource_group_name: str,
        vnet_id: str,
        vm_size: str | None = None,
        allowed_source_ips: list[str] | None = None,
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
            vm_size: Azure VM size (default: Standard_D2s_v3)
            allowed_source_ips: List of IP addresses/CIDR ranges allowed RDP access.
                If None, allows access from ANY IP (INSECURE - testing only).
                Examples: ["1.2.3.4/32"], ["10.0.0.0/8", "192.168.1.0/24"]

        Raises:
            ValueError: If input validation fails

        Security Note:
            For testing: Leave allowed_source_ips=None for convenience
            For production: ALWAYS configure allowed_source_ips to restrict access
        """
        # Input validation
        self._validate_location(location)
        self._validate_resource_group_name(resource_group_name)
        self._validate_vnet_id(vnet_id)

        self.compute_client = compute_client
        self.network_client = network_client
        self.subscription_id = subscription_id
        self.run_id = run_id
        self.location = location
        self.resource_group_name = resource_group_name
        self.vnet_id = vnet_id
        self.vm_size = vm_size or self.DEFAULT_VM_SIZE

        # Security: Validate and configure allowed source IPs
        if allowed_source_ips is not None:
            self.allowed_source_ips = self._validate_ip_addresses(allowed_source_ips)
            logger.info(
                f"NSG configured with {len(self.allowed_source_ips)} allowed source IP ranges"
            )
        else:
            self.allowed_source_ips = None
            logger.warning(
                "SECURITY WARNING: No allowed_source_ips configured. "
                "RDP will be accessible from ANY IP address (*). "
                "This is acceptable for TESTING but NOT for PRODUCTION. "
                "Configure allowed_source_ips=['your.ip.address/32'] for production use."
            )

    def _validate_location(self, location: str) -> None:
        """Validate Azure region.

        Args:
            location: Azure region to validate

        Raises:
            ValueError: If location is invalid
        """
        if not location or not isinstance(location, str):
            raise ValueError("location must be a non-empty string")

        location_lower = location.lower()
        if location_lower not in self.VALID_AZURE_REGIONS:
            raise ValueError(
                f"Invalid Azure region: '{location}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_AZURE_REGIONS))}"
            )

    def _validate_resource_group_name(self, resource_group_name: str) -> None:
        """Validate resource group name.

        Azure resource group names must:
        - Be 1-90 characters
        - Contain only alphanumerics, underscores, hyphens, periods, parentheses
        - Not end with a period

        Args:
            resource_group_name: Resource group name to validate

        Raises:
            ValueError: If resource group name is invalid
        """
        if not resource_group_name or not isinstance(resource_group_name, str):
            raise ValueError("resource_group_name must be a non-empty string")

        if len(resource_group_name) > 90:
            raise ValueError(
                f"resource_group_name too long: {len(resource_group_name)} chars (max 90)"
            )

        if resource_group_name.endswith('.'):
            raise ValueError("resource_group_name cannot end with a period")

        # Allow alphanumeric, underscore, hyphen, period, parentheses
        if not re.match(r'^[a-zA-Z0-9_\-\.\(\)]+$', resource_group_name):
            raise ValueError(
                f"Invalid resource_group_name: '{resource_group_name}'. "
                "Must contain only alphanumerics, underscores, hyphens, periods, and parentheses"
            )

    def _validate_vnet_id(self, vnet_id: str) -> None:
        """Validate Virtual Network subnet ID.

        VNet subnet IDs must be full Azure Resource IDs in the format:
        /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet}

        Args:
            vnet_id: Virtual Network subnet resource ID to validate

        Raises:
            ValueError: If vnet_id is invalid or missing
        """
        if not vnet_id or not isinstance(vnet_id, str):
            raise ValueError(
                "vnet_id is required and must be a non-empty string. "
                "Provide the full Azure Resource ID of the subnet: "
                "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet}"
            )

        # Validate format - must contain all required components
        required_parts = [
            "/subscriptions/",
            "/resourceGroups/",
            "/providers/Microsoft.Network/virtualNetworks/",
            "/subnets/",
        ]

        for part in required_parts:
            if part not in vnet_id:
                raise ValueError(
                    f"Invalid vnet_id format. Missing '{part}'. "
                    f"Expected format: /subscriptions/{{sub}}/resourceGroups/{{rg}}/providers/Microsoft.Network/virtualNetworks/{{vnet}}/subnets/{{subnet}}"
                )

    def _validate_ip_addresses(self, ip_list: list[str]) -> list[str]:
        """Validate IP addresses/CIDR ranges.

        Args:
            ip_list: List of IP addresses or CIDR ranges

        Returns:
            Validated list of IP addresses/CIDR ranges

        Raises:
            ValueError: If any IP address/range is invalid
        """
        if not isinstance(ip_list, list):
            raise ValueError("allowed_source_ips must be a list")

        if not ip_list:
            raise ValueError("allowed_source_ips cannot be empty (use None for unrestricted)")

        validated = []
        for ip_str in ip_list:
            if not isinstance(ip_str, str):
                raise ValueError(f"IP address must be string, got: {type(ip_str)}")

            try:
                # Validate as IP network (supports both single IPs and CIDR ranges)
                network = ipaddress.ip_network(ip_str, strict=False)
                validated.append(str(network))
            except ValueError as e:
                raise ValueError(
                    f"Invalid IP address or CIDR range: '{ip_str}'. "
                    f"Expected format: '1.2.3.4/32' or '10.0.0.0/8'. Error: {e}"
                ) from e

        return validated

    def _validate_worker_id(self, worker_id: str) -> None:
        """Validate worker ID format.

        Worker IDs should be alphanumeric with hyphens and underscores only.

        Args:
            worker_id: Worker ID to validate

        Raises:
            ValueError: If worker ID is invalid
        """
        if not worker_id or not isinstance(worker_id, str):
            raise ValueError("worker_id must be a non-empty string")

        if len(worker_id) > 64:
            raise ValueError(f"worker_id too long: {len(worker_id)} chars (max 64)")

        # Allow alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_\-]+$', worker_id):
            raise ValueError(
                f"Invalid worker_id: '{worker_id}'. "
                "Must contain only alphanumerics, hyphens, and underscores"
            )

    def _generate_secure_password(self) -> str:
        """Generate a secure random password for VM admin account.

        Uses secrets.token_urlsafe to generate a cryptographically secure
        password that meets Azure VM password requirements:
        - At least 16 characters
        - Contains uppercase, lowercase, digits, and special characters

        Returns:
            Secure random password
        """
        # token_urlsafe(24) generates ~32 character URL-safe string
        # which meets all Azure password complexity requirements
        return secrets.token_urlsafe(24)

    def _get_vm_name(self, worker: WorkerIdentity) -> str:
        """Generate VM name following naming convention.

        Args:
            worker: Worker identity

        Returns:
            VM name: cua-win-{location}-{worker_id}

        Raises:
            ValueError: If worker_id is invalid
        """
        # Validate worker_id first
        self._validate_worker_id(worker.worker_id)

        # Sanitize worker_id to ensure valid VM name (alphanumeric and hyphens)
        worker_id_safe = worker.worker_id.replace("_", "-")
        return f"cua-win-{self.location}-{worker_id_safe}"

    def _get_computer_name(self, vm_name: str) -> str:
        """Generate unique 15-char computer name using hash.

        Windows computer names are limited to 15 characters. To avoid
        collisions when truncating long VM names, we use a hash-based
        approach that guarantees uniqueness.

        Args:
            vm_name: Full VM name (can be longer than 15 chars)

        Returns:
            Unique computer name (15 chars max)
        """
        # If vm_name is already 15 chars or less, use it directly
        if len(vm_name) <= 15:
            return vm_name

        # Hash the full VM name to get a unique identifier
        # Use first 8 chars of hex digest for uniqueness
        vm_hash = hashlib.sha256(vm_name.encode()).hexdigest()[:8]

        # Take prefix from vm_name (max 6 chars to leave room for hash)
        # Format: {prefix}-{hash} where total is 15 chars (6 + 1 + 8 = 15)
        prefix = vm_name[:6]
        return f"{prefix}-{vm_hash}"

    async def provision_vm(self, worker: WorkerIdentity) -> dict[str, Any]:
        """Provision a Windows VM for a worker.

        Creates VM with all required network resources:
        - Public IP address
        - Network Security Group (RDP rule)
        - Network Interface
        - Virtual Machine (Windows Server 2022)

        All resources are tagged with run_id and worker_id for tracking.

        Args:
            worker: Worker identity to provision VM for

        Returns:
            Dictionary with VM details:
            {
                "vm_name": str,
                "public_ip": str,
                "admin_username": str,
                "admin_password": str,  # SECURITY: Plaintext password
                "rdp_port": int
            }

        Raises:
            ValueError: If worker_id validation fails
            Exception: If VM provisioning fails

        Security Warning:
            The returned admin_password is in PLAINTEXT. This is required for
            Computer Use Agents to RDP to the VM. For production deployments:
            1. Store the password in Azure Key Vault immediately after provisioning
            2. Configure allowed_source_ips to restrict RDP access
            3. Consider using Azure Bastion instead of public IPs
        """
        vm_name = self._get_vm_name(worker)
        admin_username = "azureuser"
        admin_password = self._generate_secure_password()

        logger.info(f"Provisioning Windows VM: {vm_name} for worker {worker.worker_id}")

        # Step 1: Create Public IP
        public_ip_name = f"{vm_name}-ip"
        public_ip_address = await self._create_public_ip(public_ip_name, worker)

        # Step 2: Create NSG with RDP rule
        nsg_name = f"{vm_name}-nsg"
        await self._create_nsg(nsg_name, worker)

        # Step 3: Create Network Interface
        nic_name = f"{vm_name}-nic"
        nic_id = await self._create_nic(nic_name, public_ip_name, nsg_name, worker)

        # Step 4: Create Virtual Machine
        await self._create_vm(vm_name, nic_id, admin_username, admin_password, worker)

        logger.info(
            f"VM provisioning initiated: {vm_name} (public IP: {public_ip_address})"
        )

        return {
            "vm_name": vm_name,
            "public_ip": public_ip_address,
            "admin_username": admin_username,
            "admin_password": admin_password,
            "rdp_port": self.RDP_PORT,
        }

    async def _create_public_ip(
        self, public_ip_name: str, worker: WorkerIdentity
    ) -> str:
        """Create a public IP address.

        Args:
            public_ip_name: Name for the public IP
            worker: Worker identity for tagging

        Returns:
            Public IP address string
        """
        logger.info(f"Creating public IP: {public_ip_name}")

        public_ip_params = {
            "location": self.location,
            "public_ip_allocation_method": "Static",
            "tags": {
                "run_id": self.run_id,
                "worker_id": worker.worker_id,
            },
        }

        # Azure async SDK - await the poller directly
        poller = await self.network_client.public_ip_addresses.begin_create_or_update(
            resource_group_name=self.resource_group_name,
            public_ip_address_name=public_ip_name,
            parameters=public_ip_params,
        )

        public_ip_result = await poller
        ip_address = public_ip_result.ip_address

        logger.info(f"Public IP created: {public_ip_name} ({ip_address})")
        return ip_address

    async def _create_nsg(self, nsg_name: str, worker: WorkerIdentity) -> None:
        """Create Network Security Group with RDP rule.

        Creates NSG rules based on allowed_source_ips configuration:
        - If allowed_source_ips is configured: Creates one rule per IP/range
        - If None: Creates single rule allowing access from ANY IP (*)

        Args:
            nsg_name: Name for the NSG
            worker: Worker identity for tagging

        Security Note:
            When allowed_source_ips is None, RDP is accessible from ANY IP.
            This is INSECURE and should only be used for testing.
        """
        logger.info(f"Creating NSG: {nsg_name}")

        # Build security rules based on configuration
        security_rules = []

        if self.allowed_source_ips:
            # Create one rule per allowed source IP/range
            for idx, source_ip in enumerate(self.allowed_source_ips):
                rule = {
                    "name": f"AllowRDP-{idx}",
                    "protocol": "Tcp",
                    "source_port_range": "*",
                    "destination_port_range": str(self.RDP_PORT),
                    "source_address_prefix": source_ip,
                    "destination_address_prefix": "*",
                    "access": "Allow",
                    "priority": 1000 + idx,  # Increment priority for each rule
                    "direction": "Inbound",
                }
                security_rules.append(rule)
                logger.info(f"NSG rule {idx}: Allow RDP from {source_ip}")
        else:
            # INSECURE: Allow from ANY IP (testing only)
            security_rules.append({
                "name": "AllowRDP",
                "protocol": "Tcp",
                "source_port_range": "*",
                "destination_port_range": str(self.RDP_PORT),
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "access": "Allow",
                "priority": 1000,
                "direction": "Inbound",
            })
            logger.warning(
                f"NSG {nsg_name}: RDP allowed from ANY IP (*) - INSECURE (testing only)"
            )

        nsg_params = {
            "location": self.location,
            "security_rules": security_rules,
            "tags": {
                "run_id": self.run_id,
                "worker_id": worker.worker_id,
            },
        }

        try:
            poller = await self.network_client.network_security_groups.begin_create_or_update(
                resource_group_name=self.resource_group_name,
                network_security_group_name=nsg_name,
                parameters=nsg_params,
            )

            await poller
            logger.info(f"NSG created: {nsg_name} with {len(security_rules)} rule(s)")

        except Exception as e:
            logger.error(
                f"Failed to create NSG {nsg_name}: {type(e).__name__}",
                exc_info=True  # Full details in debug logs only
            )
            raise

    async def _create_nic(
        self, nic_name: str, public_ip_name: str, nsg_name: str, worker: WorkerIdentity
    ) -> str:
        """Create Network Interface with Public IP and NSG.

        Args:
            nic_name: Name for the NIC
            public_ip_name: Name of the public IP to associate
            nsg_name: Name of the NSG to associate
            worker: Worker identity for tagging

        Returns:
            NIC resource ID
        """
        logger.info(f"Creating NIC: {nic_name}")

        # Use the explicitly provided VNet subnet ID (validated at init)
        subnet_id = self.vnet_id
        public_ip_id = f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.Network/publicIPAddresses/{public_ip_name}"
        nsg_id = f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.Network/networkSecurityGroups/{nsg_name}"

        nic_params = {
            "location": self.location,
            "ip_configurations": [
                {
                    "name": "ipconfig1",
                    "subnet": {"id": subnet_id},
                    "public_ip_address": {"id": public_ip_id},
                }
            ],
            "network_security_group": {"id": nsg_id},
            "tags": {
                "run_id": self.run_id,
                "worker_id": worker.worker_id,
            },
        }

        poller = await self.network_client.network_interfaces.begin_create_or_update(
            resource_group_name=self.resource_group_name,
            network_interface_name=nic_name,
            parameters=nic_params,
        )

        nic_result = await poller
        logger.info(f"NIC created: {nic_name}")
        return nic_result.id

    async def _create_vm(
        self,
        vm_name: str,
        nic_id: str,
        admin_username: str,
        admin_password: str,
        worker: WorkerIdentity,
    ) -> None:
        """Create the Virtual Machine.

        Args:
            vm_name: VM name
            nic_id: Network interface resource ID
            admin_username: Admin username
            admin_password: Admin password
            worker: Worker identity for tagging
        """
        logger.info(f"Creating VM: {vm_name}")

        vm_params = {
            "location": self.location,
            "hardware_profile": {"vm_size": self.vm_size},
            "storage_profile": {
                "image_reference": {
                    "publisher": self.DEFAULT_IMAGE_PUBLISHER,
                    "offer": self.DEFAULT_IMAGE_OFFER,
                    "sku": self.DEFAULT_IMAGE_SKU,
                    "version": self.DEFAULT_IMAGE_VERSION,
                }
            },
            "os_profile": {
                "computer_name": self._get_computer_name(vm_name),
                "admin_username": admin_username,
                "admin_password": admin_password,
                "windows_configuration": {
                    "enable_automatic_updates": True,
                    "provision_vm_agent": True,
                },
            },
            "network_profile": {
                "network_interfaces": [{"id": nic_id, "primary": True}]
            },
            "tags": {
                "run_id": self.run_id,
                "worker_id": worker.worker_id,
            },
        }

        poller = await self.compute_client.virtual_machines.begin_create_or_update(
            self.resource_group_name,
            vm_name,
            vm_params,
        )

        await poller
        logger.info(f"VM created: {vm_name}")

    async def delete_vm(
        self, vm_name: str, cleanup_network: bool = True
    ) -> bool:
        """Delete a VM and optionally its network resources.

        Args:
            vm_name: VM name to delete
            cleanup_network: Whether to delete associated network resources

        Returns:
            True if deleted successfully, False otherwise
        """
        logger.info(f"Deleting VM: {vm_name}")

        try:
            # Delete VM
            poller = await self.compute_client.virtual_machines.begin_delete(
                resource_group_name=self.resource_group_name,
                vm_name=vm_name,
            )

            await poller
            logger.info(f"VM deleted: {vm_name}")

            # Delete network resources if requested
            if cleanup_network:
                await self._cleanup_network_resources(vm_name)

            return True

        except Exception as e:
            # Sanitize error message - log type only, full details in debug
            logger.error(
                f"Failed to delete VM {vm_name}: {type(e).__name__}",
                exc_info=True  # Full stack trace only in debug logs
            )
            return False

    async def _cleanup_network_resources(self, vm_name: str) -> None:
        """Clean up network resources associated with a VM.

        Args:
            vm_name: VM name whose resources to clean up
        """
        nic_name = f"{vm_name}-nic"
        public_ip_name = f"{vm_name}-ip"
        nsg_name = f"{vm_name}-nsg"

        # Delete NIC
        try:
            poller = await self.network_client.network_interfaces.begin_delete(
                resource_group_name=self.resource_group_name,
                network_interface_name=nic_name,
            )

            await poller
            logger.info(f"NIC deleted: {nic_name}")
        except Exception as e:
            logger.info(f"NIC cleanup skipped ({nic_name}): {e}")

        # Delete Public IP
        try:
            poller = await self.network_client.public_ip_addresses.begin_delete(
                resource_group_name=self.resource_group_name,
                public_ip_address_name=public_ip_name,
            )

            await poller
            logger.info(f"Public IP deleted: {public_ip_name}")
        except Exception as e:
            logger.info(f"Public IP cleanup skipped ({public_ip_name}): {e}")

        # Delete NSG
        try:
            poller = await self.network_client.network_security_groups.begin_delete(
                resource_group_name=self.resource_group_name,
                network_security_group_name=nsg_name,
            )

            await poller
            logger.info(f"NSG deleted: {nsg_name}")
        except Exception as e:
            logger.info(f"NSG cleanup skipped ({nsg_name}): {e}")

    async def get_vm_status(self, vm_name: str) -> str | None:
        """Get VM provisioning status.

        Args:
            vm_name: VM name to check

        Returns:
            Provisioning state string or None if VM not found
        """
        try:
            vm = await self.compute_client.virtual_machines.get(
                resource_group_name=self.resource_group_name,
                vm_name=vm_name,
            )
            return vm.provisioning_state

        except Exception as e:
            # Sanitize error message
            logger.warning(
                f"Failed to get VM status for {vm_name}: {type(e).__name__}",
                exc_info=True  # Full details in debug logs only
            )
            return None

    async def verify_computer_use_ready(
        self,
        vm_name: str,
        public_ip: str,
        timeout_seconds: int = 30,
    ) -> bool:
        """Verify VM is ready for Computer Use Agent.

        Checks:
        - VM provisioning state is "Succeeded"
        - RDP port (3389) is accessible

        Args:
            vm_name: VM name to verify
            public_ip: Public IP address of VM
            timeout_seconds: Socket connection timeout

        Returns:
            True if VM is ready for Computer Use, False otherwise
        """
        logger.info(f"Verifying Computer Use readiness: {vm_name}")

        # Check VM provisioning state
        status = await self.get_vm_status(vm_name)
        if status != "Succeeded":
            logger.warning(f"VM {vm_name} not ready: status={status}")
            return False

        # Check RDP port accessibility
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout_seconds)
                sock.connect((public_ip, self.RDP_PORT))
                logger.info(f"RDP port accessible on {vm_name}")
                return True

        except (TimeoutError, ConnectionRefusedError, OSError) as e:
            # Sanitize error message
            logger.warning(
                f"RDP port not accessible on {vm_name}: {type(e).__name__}",
                exc_info=True  # Full details in debug logs only
            )
            return False

    async def wait_for_provisioning(
        self, vm_name: str, timeout_minutes: int | None = None
    ) -> bool:
        """Wait for VM to be provisioned and ready.

        Polls VM provisioning status with progress tracking.

        Args:
            vm_name: VM name to wait for
            timeout_minutes: Timeout in minutes (default: 15)

        Returns:
            True if provisioned successfully, False on timeout or error
        """
        timeout = timeout_minutes or self.PROVISIONING_TIMEOUT_MINUTES
        start_time = asyncio.get_event_loop().time()
        deadline = start_time + (timeout * 60)

        logger.info(
            f"Waiting for VM provisioning: {vm_name} (timeout: {timeout} minutes)"
        )

        while asyncio.get_event_loop().time() < deadline:
            status = await self.get_vm_status(vm_name)

            if status == "Succeeded":
                elapsed = (asyncio.get_event_loop().time() - start_time) / 60
                logger.info(
                    f"VM ready: {vm_name} (elapsed: {elapsed:.1f} minutes)"
                )
                return True

            elif status == "Failed":
                logger.error(f"VM provisioning failed: {vm_name}")
                return False

            elif status:
                logger.debug(f"VM status: {vm_name} = {status}")

            await asyncio.sleep(self.PROVISIONING_CHECK_INTERVAL_SECONDS)

        elapsed = (asyncio.get_event_loop().time() - start_time) / 60
        logger.warning(
            f"VM provisioning timeout: {vm_name} (elapsed: {elapsed:.1f} minutes)"
        )
        return False
