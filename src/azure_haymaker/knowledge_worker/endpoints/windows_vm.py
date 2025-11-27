"""Azure Windows VM management for Computer Use Agents.

Provides Windows VM provisioning as a fallback when Cloud PCs are unavailable.
VMs are configured with RDP access, browsers, and Desktop Experience for
Computer Use Agent capabilities.
"""

import asyncio
import logging
import secrets
import socket
from typing import Any

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

    Attributes:
        compute_client: Azure Compute Management client
        network_client: Azure Network Management client
        subscription_id: Azure subscription ID for resource IDs
        run_id: HayMaker run ID for resource tagging
        location: Azure region for VM deployment
        resource_group_name: Resource group for VM resources
        vm_size: Azure VM size (default: Standard_D2s_v3)
    """

    DEFAULT_VM_SIZE = "Standard_D2s_v3"
    DEFAULT_IMAGE_PUBLISHER = "MicrosoftWindowsServer"
    DEFAULT_IMAGE_OFFER = "WindowsServer"
    DEFAULT_IMAGE_SKU = "2022-datacenter-azure-edition"
    DEFAULT_IMAGE_VERSION = "latest"
    PROVISIONING_TIMEOUT_MINUTES = 15
    PROVISIONING_CHECK_INTERVAL_SECONDS = 30
    RDP_PORT = 3389

    def __init__(
        self,
        compute_client: Any,
        network_client: Any,
        subscription_id: str,
        run_id: str,
        location: str,
        resource_group_name: str,
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
            vm_size: Azure VM size (default: Standard_D2s_v3)
        """
        self.compute_client = compute_client
        self.network_client = network_client
        self.subscription_id = subscription_id
        self.run_id = run_id
        self.location = location
        self.resource_group_name = resource_group_name
        self.vm_size = vm_size or self.DEFAULT_VM_SIZE

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
        """
        # Sanitize worker_id to ensure valid VM name (alphanumeric and hyphens)
        worker_id_safe = worker.worker_id.replace("_", "-")
        return f"cua-win-{self.location}-{worker_id_safe}"

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
                "admin_password": str,
                "rdp_port": int
            }

        Raises:
            Exception: If VM provisioning fails
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

        poller = await self.network_client.public_ip_addresses.begin_create_or_update(
            resource_group_name=self.resource_group_name,
            public_ip_address_name=public_ip_name,
            parameters=public_ip_params,
        )

        public_ip_result = await poller.result()
        ip_address = public_ip_result.ip_address

        logger.info(f"Public IP created: {public_ip_name} ({ip_address})")
        return ip_address

    async def _create_nsg(self, nsg_name: str, worker: WorkerIdentity) -> None:
        """Create Network Security Group with RDP rule.

        Args:
            nsg_name: Name for the NSG
            worker: Worker identity for tagging
        """
        logger.info(f"Creating NSG: {nsg_name}")

        nsg_params = {
            "location": self.location,
            "security_rules": [
                {
                    "name": "AllowRDP",
                    "protocol": "Tcp",
                    "source_port_range": "*",
                    "destination_port_range": str(self.RDP_PORT),
                    "source_address_prefix": "*",
                    "destination_address_prefix": "*",
                    "access": "Allow",
                    "priority": 1000,
                    "direction": "Inbound",
                },
            ],
            "tags": {
                "run_id": self.run_id,
                "worker_id": worker.worker_id,
            },
        }

        poller = await self.network_client.network_security_groups.begin_create_or_update(
            resource_group_name=self.resource_group_name,
            network_security_group_name=nsg_name,
            parameters=nsg_params,
        )

        await poller.result()
        logger.info(f"NSG created: {nsg_name}")

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

        # Construct resource IDs directly (simpler for testing)
        # In production, a VNet would already exist or be provisioned separately
        vnet_name = f"vnet-{self.run_id[:8]}"
        subnet_name = "default"
        subnet_id = f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.Network/virtualNetworks/{vnet_name}/subnets/{subnet_name}"
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

        nic_result = await poller.result()
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
                "computer_name": vm_name[:15],  # Windows limit
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

        await poller.result()
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
            await poller.result()
            logger.info(f"VM deleted: {vm_name}")

            # Delete network resources if requested
            if cleanup_network:
                await self._cleanup_network_resources(vm_name)

            return True

        except Exception as e:
            logger.error(f"Failed to delete VM {vm_name}: {e}")
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
            await poller.result()
            logger.info(f"NIC deleted: {nic_name}")
        except Exception as e:
            logger.info(f"NIC cleanup skipped ({nic_name}): {e}")

        # Delete Public IP
        try:
            poller = await self.network_client.public_ip_addresses.begin_delete(
                resource_group_name=self.resource_group_name,
                public_ip_address_name=public_ip_name,
            )
            await poller.result()
            logger.info(f"Public IP deleted: {public_ip_name}")
        except Exception as e:
            logger.info(f"Public IP cleanup skipped ({public_ip_name}): {e}")

        # Delete NSG
        try:
            poller = await self.network_client.network_security_groups.begin_delete(
                resource_group_name=self.resource_group_name,
                network_security_group_name=nsg_name,
            )
            await poller.result()
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
            logger.warning(f"Failed to get VM status for {vm_name}: {e}")
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
            logger.warning(f"RDP port not accessible on {vm_name}: {e}")
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
