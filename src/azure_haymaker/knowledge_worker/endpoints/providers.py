"""Provider-specific provisioning and deletion logic.

Encapsulates HOW to interact with each endpoint type: Cloud PC, Windows VM,
and CLI Container.

Philosophy:
- Single responsibility: Provider interaction only
- Thin wrappers: Delegates to appropriate provider manager
- No lifecycle tracking: Just provisions and deletes
- Self-contained brick with clear public API

Public API (the "studs"):
    EndpointProviderManager: Provider-specific operations
    ProvisioningError: Exception for provisioning failures
"""

import logging
from typing import Any

from azure_haymaker.knowledge_worker.endpoints.cli_container import (
    M365CLIContainerManager,
)
from azure_haymaker.knowledge_worker.endpoints.cloud_pc import (
    Windows365CloudPCManager,
)
from azure_haymaker.knowledge_worker.endpoints.windows_vm import WindowsVMManager
from azure_haymaker.knowledge_worker.models.worker import WorkerConfig, WorkerIdentity

logger = logging.getLogger(__name__)

__all__ = ["EndpointProviderManager", "ProvisioningError"]


class ProvisioningError(Exception):
    """Raised when endpoint provisioning fails."""

    pass


class EndpointProviderManager:
    """Provider-specific endpoint provisioning and deletion.

    Encapsulates all provider-specific logic for Cloud PC, Windows VM,
    and CLI Container endpoints.

    Attributes:
        cloud_pc_manager: Manager for Cloud PC endpoints
        windows_vm_manager: Manager for Windows VM endpoints
        container_manager: Manager for CLI container endpoints
        run_id: HayMaker run ID for this deployment
    """

    def __init__(
        self,
        cloud_pc_manager: Windows365CloudPCManager | None = None,
        windows_vm_manager: WindowsVMManager | None = None,
        container_manager: M365CLIContainerManager | None = None,
        graph_client: Any = None,
        config: Any = None,
        run_id: str = "",
    ):
        """Initialize provider manager.

        Args:
            cloud_pc_manager: Pre-configured Cloud PC manager (optional)
            windows_vm_manager: Pre-configured Windows VM manager (optional)
            container_manager: Pre-configured container manager (optional)
            graph_client: Microsoft Graph API client (for default Cloud PC manager)
            config: Orchestrator configuration (for default container manager)
            run_id: HayMaker run ID for resource tagging
        """
        self.run_id = run_id

        # Use provided managers or create defaults
        if cloud_pc_manager:
            self.cloud_pc_manager = cloud_pc_manager
        elif graph_client:
            self.cloud_pc_manager = Windows365CloudPCManager(graph_client, run_id)
        else:
            self.cloud_pc_manager = None

        self.windows_vm_manager = windows_vm_manager

        if container_manager:
            self.container_manager = container_manager
        elif config:
            self.container_manager = M365CLIContainerManager(config, run_id)
        else:
            self.container_manager = None

    async def provision_cloud_pc(self, worker: WorkerIdentity) -> str:
        """Provision a Cloud PC endpoint.

        Args:
            worker: Worker identity

        Returns:
            Cloud PC ID

        Raises:
            ProvisioningError: If manager not configured or provisioning fails
        """
        if not self.cloud_pc_manager:
            raise ProvisioningError("Cloud PC manager not configured")

        # Ensure provisioning policy exists
        policy_id = await self.cloud_pc_manager.ensure_provisioning_policy()

        # Provision Cloud PC
        return await self.cloud_pc_manager.provision_cloud_pc(worker, policy_id)

    async def provision_cloud_pc_with_timeout(
        self, worker: WorkerIdentity
    ) -> str | None:
        """Provision Cloud PC with timeout handling.

        Args:
            worker: Worker identity

        Returns:
            Cloud PC ID if successful, None if timeout

        Raises:
            ProvisioningError: If manager not configured
        """
        if not self.cloud_pc_manager:
            raise ProvisioningError("Cloud PC manager not configured")

        policy_id = await self.cloud_pc_manager.ensure_provisioning_policy()
        cloud_pc_id = await self.cloud_pc_manager.provision_cloud_pc(worker, policy_id)

        # Wait for provisioning with timeout
        success = await self.cloud_pc_manager.wait_for_provisioning(worker)

        return cloud_pc_id if success else None

    async def provision_windows_vm(self, worker: WorkerIdentity) -> dict[str, Any]:
        """Provision a Windows VM endpoint.

        Args:
            worker: Worker identity

        Returns:
            VM details dictionary with keys: vm_name, public_ip, admin_username,
            admin_password, rdp_port

        Raises:
            ProvisioningError: If manager not configured
            Exception: If provisioning or ready wait fails
        """
        if not self.windows_vm_manager:
            raise ProvisioningError("Windows VM manager not configured")

        vm_details = await self.windows_vm_manager.provision_vm(worker)
        vm_name = vm_details["vm_name"]

        # Wait for VM to be ready
        success = await self.windows_vm_manager.wait_for_provisioning(vm_name)

        if not success:
            raise Exception(f"Windows VM provisioning timeout for {vm_name}")

        return vm_details

    async def provision_container(
        self, worker: WorkerIdentity, activity_config: WorkerConfig
    ) -> str:
        """Provision a CLI container endpoint.

        Args:
            worker: Worker identity
            activity_config: Activity configuration

        Returns:
            Container resource ID

        Raises:
            ProvisioningError: If manager not configured
        """
        if not self.container_manager:
            raise ProvisioningError("Container manager not configured")

        return await self.container_manager.deploy_worker_container(
            worker, activity_config
        )

    async def delete_cloud_pc(self, endpoint_id: str) -> bool:
        """Delete a Cloud PC endpoint.

        Args:
            endpoint_id: Cloud PC ID

        Returns:
            True if deleted successfully

        Raises:
            ProvisioningError: If manager not configured
        """
        if not self.cloud_pc_manager:
            raise ProvisioningError("Cloud PC manager not configured")

        return await self.cloud_pc_manager.delete_cloud_pc(endpoint_id)

    async def delete_windows_vm(self, endpoint_id: str) -> bool:
        """Delete a Windows VM endpoint.

        Args:
            endpoint_id: VM name

        Returns:
            True if deleted successfully

        Raises:
            ProvisioningError: If manager not configured
        """
        if not self.windows_vm_manager:
            raise ProvisioningError("Windows VM manager not configured")

        return await self.windows_vm_manager.delete_vm(endpoint_id)

    async def delete_container(self, endpoint_id: str) -> bool:
        """Delete a container endpoint.

        Args:
            endpoint_id: Container resource ID

        Returns:
            True if deleted successfully

        Raises:
            ProvisioningError: If manager not configured
        """
        if not self.container_manager:
            raise ProvisioningError("Container manager not configured")

        return await self.container_manager.delete_container(endpoint_id)

    async def get_container_status(self, container_name: str) -> dict[str, Any]:
        """Get container status.

        Args:
            container_name: Container name (last segment of resource ID)

        Returns:
            Status dictionary

        Raises:
            ProvisioningError: If manager not configured
        """
        if not self.container_manager:
            raise ProvisioningError("Container manager not configured")

        return await self.container_manager.get_container_status(container_name)
