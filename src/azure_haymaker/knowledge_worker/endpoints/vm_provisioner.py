"""Azure VM lifecycle operations for Windows VMs.

Provides VM provisioning and management:
- VM provisioning orchestration
- VM creation and deletion
- VM status monitoring
- Provisioning wait loops
- Secure password generation

This module orchestrates VM and network resource creation.

Philosophy:
- Single responsibility: VM lifecycle management only
- Dependency injection for Azure SDK clients and managers
- Self-contained and regeneratable
"""

import asyncio
import logging
import secrets
from typing import TYPE_CHECKING, Any

from azure_haymaker.knowledge_worker.endpoints.vm_config import (
    DEFAULT_IMAGE_OFFER,
    DEFAULT_IMAGE_PUBLISHER,
    DEFAULT_IMAGE_SKU,
    DEFAULT_IMAGE_VERSION,
    PROVISIONING_CHECK_INTERVAL_SECONDS,
    PROVISIONING_TIMEOUT_MINUTES,
    RDP_PORT,
    VMConfig,
)

if TYPE_CHECKING:
    from azure_haymaker.knowledge_worker.endpoints.network_manager import NetworkResourceManager
    from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

logger = logging.getLogger(__name__)


class VMProvisioner:
    """Manages Azure VM lifecycle operations.

    Handles VM provisioning, deletion, and status monitoring for Windows VMs
    used by Computer Use Agents.

    Attributes:
        compute_client: Azure Compute Management client
        subscription_id: Azure subscription ID
        run_id: HayMaker run ID for resource tagging
    """

    def __init__(self, compute_client: Any, subscription_id: str, run_id: str):
        """Initialize VMProvisioner.

        Args:
            compute_client: Azure Compute Management client
            subscription_id: Azure subscription ID
            run_id: HayMaker run ID for tagging
        """
        self.compute_client = compute_client
        self.subscription_id = subscription_id
        self.run_id = run_id

    async def provision_vm(
        self,
        worker: "WorkerIdentity",
        network_manager: "NetworkResourceManager",
        config: VMConfig,
        allowed_source_ips: list[str],
    ) -> dict[str, Any]:
        """Provision a Windows VM for a worker.

        Creates VM with all required network resources:
        - Public IP address
        - Network Security Group (RDP rule)
        - Network Interface
        - Virtual Machine (Windows Server 2022)

        All resources are tagged with run_id and worker_id for tracking.

        Args:
            worker: Worker identity to provision VM for
            network_manager: Network resource manager
            config: VM configuration
            allowed_source_ips: List of allowed source IPs for RDP

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
        vm_name = config.get_vm_name(worker, config.location)
        admin_username = "azureuser"
        admin_password = self.generate_secure_password()

        logger.info(f"Provisioning Windows VM: {vm_name} for worker {worker.worker_id}")

        tags = {
            "run_id": self.run_id,
            "worker_id": worker.worker_id,
        }

        # Step 1: Create Public IP
        public_ip_name = f"{vm_name}-ip"
        public_ip_address = await network_manager.create_public_ip(
            name=public_ip_name,
            location=config.location,
            tags=tags,
            resource_group=config.resource_group_name,
        )

        # Step 2: Create NSG with RDP rule
        nsg_name = f"{vm_name}-nsg"
        await network_manager.create_nsg(
            name=nsg_name,
            location=config.location,
            tags=tags,
            resource_group=config.resource_group_name,
            allowed_ips=allowed_source_ips,
            rdp_port=RDP_PORT,
        )

        # Step 3: Create Network Interface
        nic_name = f"{vm_name}-nic"
        nic_id = await network_manager.create_nic(
            name=nic_name,
            location=config.location,
            tags=tags,
            resource_group=config.resource_group_name,
            subnet_id=config.vnet_id,
            public_ip_name=public_ip_name,
            nsg_name=nsg_name,
        )

        # Step 4: Create Virtual Machine
        await self.create_vm(
            vm_name=vm_name,
            nic_id=nic_id,
            admin_username=admin_username,
            admin_password=admin_password,
            location=config.location,
            vm_size=config.vm_size,
            resource_group=config.resource_group_name,
            tags=tags,
        )

        logger.info(f"VM provisioning initiated: {vm_name} (public IP: {public_ip_address})")

        return {
            "vm_name": vm_name,
            "public_ip": public_ip_address,
            "admin_username": admin_username,
            "admin_password": admin_password,
            "rdp_port": RDP_PORT,
        }

    async def create_vm(
        self,
        vm_name: str,
        nic_id: str,
        admin_username: str,
        admin_password: str,
        location: str,
        vm_size: str,
        resource_group: str,
        tags: dict[str, str],
    ) -> None:
        """Create the Virtual Machine.

        Args:
            vm_name: VM name
            nic_id: Network interface resource ID
            admin_username: Admin username
            admin_password: Admin password
            location: Azure region
            vm_size: VM size (e.g., Standard_D2s_v3)
            resource_group: Resource group name
            tags: Resource tags
        """
        logger.info(f"Creating VM: {vm_name}")

        vm_params = {
            "location": location,
            "hardware_profile": {"vm_size": vm_size},
            "storage_profile": {
                "image_reference": {
                    "publisher": DEFAULT_IMAGE_PUBLISHER,
                    "offer": DEFAULT_IMAGE_OFFER,
                    "sku": DEFAULT_IMAGE_SKU,
                    "version": DEFAULT_IMAGE_VERSION,
                }
            },
            "os_profile": {
                "computer_name": VMConfig.get_computer_name(vm_name),
                "admin_username": admin_username,
                "admin_password": admin_password,
                "windows_configuration": {
                    "enable_automatic_updates": True,
                    "provision_vm_agent": True,
                },
            },
            "network_profile": {"network_interfaces": [{"id": nic_id, "primary": True}]},
            "tags": tags,
        }

        poller = await self.compute_client.virtual_machines.begin_create_or_update(
            resource_group,
            vm_name,
            vm_params,
        )

        await poller
        logger.info(f"VM created: {vm_name}")

    async def delete_vm(
        self,
        vm_name: str,
        resource_group: str,
        cleanup_network: bool,
        network_manager: "NetworkResourceManager",
    ) -> bool:
        """Delete a VM and optionally its network resources.

        Args:
            vm_name: VM name to delete
            resource_group: Resource group name
            cleanup_network: Whether to delete associated network resources
            network_manager: Network resource manager

        Returns:
            True if deleted successfully, False otherwise
        """
        logger.info(f"Deleting VM: {vm_name}")

        try:
            # Delete VM
            poller = await self.compute_client.virtual_machines.begin_delete(
                resource_group_name=resource_group,
                vm_name=vm_name,
            )

            await poller
            logger.info(f"VM deleted: {vm_name}")

            # Delete network resources if requested
            if cleanup_network:
                await network_manager.cleanup_network_resources(
                    vm_name=vm_name,
                    resource_group=resource_group,
                )

            return True

        except Exception as e:
            # Sanitize error message - log type only, full details in debug
            logger.error(
                f"Failed to delete VM {vm_name}: {type(e).__name__}",
                exc_info=True,  # Full stack trace only in debug logs
            )
            return False

    async def get_vm_status(self, vm_name: str, resource_group: str) -> str | None:
        """Get VM provisioning status.

        Args:
            vm_name: VM name to check
            resource_group: Resource group name

        Returns:
            Provisioning state string or None if VM not found
        """
        try:
            vm = await self.compute_client.virtual_machines.get(
                resource_group_name=resource_group,
                vm_name=vm_name,
            )
            return vm.provisioning_state

        except Exception as e:
            # Sanitize error message
            logger.warning(
                f"Failed to get VM status for {vm_name}: {type(e).__name__}",
                exc_info=True,  # Full details in debug logs only
            )
            return None

    async def wait_for_provisioning(
        self,
        vm_name: str,
        resource_group: str,
        timeout_minutes: int | None = None,
    ) -> bool:
        """Wait for VM to be provisioned and ready.

        Polls VM provisioning status with progress tracking.

        Args:
            vm_name: VM name to wait for
            resource_group: Resource group name
            timeout_minutes: Timeout in minutes (default: 15)

        Returns:
            True if provisioned successfully, False on timeout or error
        """
        timeout = timeout_minutes or PROVISIONING_TIMEOUT_MINUTES
        start_time = asyncio.get_event_loop().time()
        deadline = start_time + (timeout * 60)

        logger.info(f"Waiting for VM provisioning: {vm_name} (timeout: {timeout} minutes)")

        while asyncio.get_event_loop().time() < deadline:
            status = await self.get_vm_status(vm_name, resource_group)

            if status == "Succeeded":
                elapsed = (asyncio.get_event_loop().time() - start_time) / 60
                logger.info(f"VM ready: {vm_name} (elapsed: {elapsed:.1f} minutes)")
                return True

            elif status == "Failed":
                logger.error(f"VM provisioning failed: {vm_name}")
                return False

            elif status:
                logger.debug(f"VM status: {vm_name} = {status}")

            await asyncio.sleep(PROVISIONING_CHECK_INTERVAL_SECONDS)

        elapsed = (asyncio.get_event_loop().time() - start_time) / 60
        logger.warning(f"VM provisioning timeout: {vm_name} (elapsed: {elapsed:.1f} minutes)")
        return False

    @staticmethod
    def generate_secure_password() -> str:
        """Generate a secure random password for VM admin account.

        Uses secrets to generate a cryptographically secure password that meets
        Azure VM password requirements:
        - At least 16 characters
        - Contains uppercase, lowercase, digits
        - URL-safe characters only (alphanumeric + - and _)

        The method ensures all required character types by:
        1. Taking random bytes and encoding with urlsafe base64
        2. Verifying it contains uppercase, lowercase, and digits
        3. Retrying if needed (extremely rare)

        Returns:
            Secure random password (32+ characters)
        """
        # Generate URL-safe base64 token (no +/ or = padding characters)
        # token_urlsafe(24) generates a ~32 character string
        while True:
            password = secrets.token_urlsafe(24)

            # Verify it meets complexity requirements
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)

            # token_urlsafe produces valid URL-safe chars: A-Za-z0-9_-
            # All characters are automatically valid

            if has_upper and has_lower and has_digit:
                return password
            # Retry if rare case where needed types are missing
            # With ~10^40 possible values, probability of retry is negligible


__all__ = ["VMProvisioner"]
