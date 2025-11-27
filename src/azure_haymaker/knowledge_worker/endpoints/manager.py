"""Endpoint manager for Knowledge Worker Activity Framework.

Provides unified management of Cloud PC, Windows VM, and CLI container
endpoints for knowledge workers with cascade fallback support.
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
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerConfig,
    WorkerIdentity,
)

logger = logging.getLogger(__name__)


class AllEndpointsFailedError(Exception):
    """Raised when all endpoint types fail to provision.

    This error indicates that the cascade fallback exhausted all options:
    Cloud PC → Windows VM → Container, and none succeeded.
    """

    pass


class EndpointManager:
    """Unified endpoint management for knowledge workers.

    Coordinates provisioning and management across all endpoint types
    with cascade fallback support:
    - Windows 365 Cloud PCs (for rich telemetry)
    - Azure Windows VMs (fallback for Computer Use Agents)
    - M365 CLI Containers (for cost-effective scale)

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
        """Initialize EndpointManager.

        Args:
            cloud_pc_manager: Pre-configured Cloud PC manager (optional)
            windows_vm_manager: Pre-configured Windows VM manager (optional)
            container_manager: Pre-configured container manager (optional)
            graph_client: Microsoft Graph API client (for default managers)
            config: Orchestrator configuration (for default managers)
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

        self._provisioned_endpoints: dict[str, dict[str, Any]] = {}

    async def provision_endpoint(
        self,
        worker: WorkerIdentity,
        activity_config: WorkerConfig,
    ) -> str:
        """Provision an endpoint for a worker based on their endpoint type.

        Args:
            worker: Worker identity with endpoint_type specified
            activity_config: Activity configuration for the worker

        Returns:
            Endpoint ID
        """
        endpoint_type = worker.endpoint_type

        if endpoint_type == EndpointType.CLOUD_PC:
            endpoint_id = await self._provision_cloud_pc(worker)
        else:
            endpoint_id = await self._provision_container(worker, activity_config)

        # Track provisioned endpoint
        self._provisioned_endpoints[worker.worker_id] = {
            "endpoint_id": endpoint_id,
            "endpoint_type": endpoint_type.value,
            "worker_id": worker.worker_id,
        }

        return endpoint_id

    async def provision_endpoint_with_fallback(
        self,
        worker: WorkerIdentity,
    ) -> dict[str, Any]:
        """Provision an endpoint with cascade fallback support.

        Attempts to provision endpoints in this order:
        1. Cloud PC (if cloud_pc_manager available)
        2. Windows VM (if Cloud PC fails and windows_vm_manager available)
        3. CLI Container (if both Cloud PC and Windows VM fail)

        Updates worker.endpoint_type and worker.endpoint_id to reflect
        the actually provisioned endpoint type.

        Args:
            worker: Worker identity to provision endpoint for

        Returns:
            Dictionary with:
            {
                "endpoint_type": EndpointType,
                "endpoint_id": str,
                "success": bool,
                "details": dict (varies by endpoint type)
            }

        Raises:
            AllEndpointsFailedError: If all endpoint types fail
        """
        failures: list[tuple[str, str]] = []  # (endpoint_type, reason)

        # Try Cloud PC first
        if self.cloud_pc_manager:
            try:
                logger.info(f"Attempting Cloud PC provisioning for {worker.worker_id}")
                cloud_pc_id = await self._provision_cloud_pc_with_fallback(worker)

                if cloud_pc_id:
                    # Update worker
                    worker.endpoint_type = EndpointType.CLOUD_PC
                    worker.endpoint_id = cloud_pc_id

                    # Track provisioned endpoint
                    self._provisioned_endpoints[worker.worker_id] = {
                        "endpoint_id": cloud_pc_id,
                        "endpoint_type": EndpointType.CLOUD_PC.value,
                        "worker_id": worker.worker_id,
                    }

                    logger.info(
                        f"Cloud PC provisioned successfully for {worker.worker_id}: {cloud_pc_id}"
                    )
                    return {
                        "endpoint_type": EndpointType.CLOUD_PC,
                        "endpoint_id": cloud_pc_id,
                        "success": True,
                        "details": {},
                    }
                else:
                    reason = "Cloud PC provisioning timeout"
                    failures.append(("Cloud PC", reason))
                    logger.warning(f"Cloud PC failed for {worker.worker_id}: {reason}")

            except Exception as e:
                reason = str(e)
                failures.append(("Cloud PC", reason))
                logger.warning(f"Cloud PC failed for {worker.worker_id}: {e}")

        # Try Windows VM fallback
        if self.windows_vm_manager:
            try:
                logger.info(
                    f"Attempting Windows VM fallback provisioning for {worker.worker_id}"
                )
                vm_details = await self._provision_windows_vm(worker)

                if vm_details:
                    vm_name = vm_details["vm_name"]

                    # Update worker
                    worker.endpoint_type = EndpointType.WINDOWS_VM
                    worker.endpoint_id = vm_name

                    # Track provisioned endpoint
                    self._provisioned_endpoints[worker.worker_id] = {
                        "endpoint_id": vm_name,
                        "endpoint_type": EndpointType.WINDOWS_VM.value,
                        "worker_id": worker.worker_id,
                        "details": vm_details,
                    }

                    logger.info(
                        f"Windows VM provisioned successfully for {worker.worker_id}: {vm_name}"
                    )
                    return {
                        "endpoint_type": EndpointType.WINDOWS_VM,
                        "endpoint_id": vm_name,
                        "success": True,
                        "details": vm_details,
                    }

            except Exception as e:
                reason = str(e)
                failures.append(("Windows VM", reason))
                logger.warning(f"Windows VM failed for {worker.worker_id}: {e}")

        # Try Container fallback
        if self.container_manager:
            try:
                logger.info(
                    f"Attempting Container fallback provisioning for {worker.worker_id}"
                )
                container_result = await self._provision_container_with_fallback(worker)

                if container_result:
                    container_id = container_result.get("container_id")

                    # Update worker
                    worker.endpoint_type = EndpointType.CLI_CONTAINER
                    worker.endpoint_id = container_id

                    # Track provisioned endpoint
                    self._provisioned_endpoints[worker.worker_id] = {
                        "endpoint_id": container_id,
                        "endpoint_type": EndpointType.CLI_CONTAINER.value,
                        "worker_id": worker.worker_id,
                        "details": container_result,
                    }

                    logger.info(
                        f"Container provisioned successfully for {worker.worker_id}: {container_id}"
                    )
                    return {
                        "endpoint_type": EndpointType.CLI_CONTAINER,
                        "endpoint_id": container_id,
                        "success": True,
                        "details": container_result,
                    }

            except Exception as e:
                reason = str(e)
                failures.append(("Container", reason))
                logger.error(f"Container failed for {worker.worker_id}: {e}")

        # All endpoints failed
        failure_summary = "; ".join([f"{ep}: {reason}" for ep, reason in failures])
        error_msg = (
            f"All endpoint types failed for worker {worker.worker_id}: {failure_summary}"
        )
        logger.error(error_msg)
        raise AllEndpointsFailedError(error_msg)

    async def _provision_cloud_pc_with_fallback(
        self, worker: WorkerIdentity
    ) -> str | None:
        """Provision Cloud PC with timeout handling.

        Args:
            worker: Worker identity

        Returns:
            Cloud PC ID if successful, None if timeout
        """
        policy_id = await self.cloud_pc_manager.ensure_provisioning_policy()
        cloud_pc_id = await self.cloud_pc_manager.provision_cloud_pc(worker, policy_id)

        # Wait for provisioning with timeout
        success = await self.cloud_pc_manager.wait_for_provisioning(worker)

        return cloud_pc_id if success else None

    async def _provision_windows_vm(self, worker: WorkerIdentity) -> dict[str, Any]:
        """Provision Windows VM with wait for ready.

        Args:
            worker: Worker identity

        Returns:
            VM details dictionary

        Raises:
            Exception: If VM provisioning fails
        """
        vm_details = await self.windows_vm_manager.provision_vm(worker)
        vm_name = vm_details["vm_name"]

        # Wait for VM to be ready
        success = await self.windows_vm_manager.wait_for_provisioning(vm_name)

        if not success:
            raise Exception(f"Windows VM provisioning timeout for {vm_name}")

        return vm_details

    async def _provision_container_with_fallback(
        self, worker: WorkerIdentity
    ) -> dict[str, Any]:
        """Provision CLI container.

        Args:
            worker: Worker identity

        Returns:
            Container details dictionary

        Raises:
            Exception: If container provisioning fails
        """
        # For containers, we use a simple approach - just provision
        # The actual WorkerConfig doesn't matter much for fallback scenarios
        from azure_haymaker.knowledge_worker.models.worker import WorkerConfig

        default_config = WorkerConfig()
        container_id = await self.container_manager.deploy_worker_container(
            worker, default_config
        )

        return {
            "container_id": container_id,
            "status": "running",
        }

    async def provision_batch(
        self,
        workers: list[tuple[WorkerIdentity, WorkerConfig]],
    ) -> dict[str, str]:
        """Provision endpoints for multiple workers.

        Separates workers by endpoint type and provisions in parallel.

        Args:
            workers: List of (identity, config) tuples

        Returns:
            Dictionary mapping worker_id to endpoint_id
        """
        cloud_pc_workers = []
        container_workers = []

        # Separate by endpoint type
        for worker, config in workers:
            if worker.endpoint_type == EndpointType.CLOUD_PC:
                cloud_pc_workers.append((worker, config))
            else:
                container_workers.append((worker, config))

        results: dict[str, str] = {}

        # Provision Cloud PCs
        if cloud_pc_workers:
            logger.info(f"Provisioning {len(cloud_pc_workers)} Cloud PCs")
            for worker, _config in cloud_pc_workers:
                try:
                    endpoint_id = await self._provision_cloud_pc(worker)
                    results[worker.worker_id] = endpoint_id
                    self._provisioned_endpoints[worker.worker_id] = {
                        "endpoint_id": endpoint_id,
                        "endpoint_type": EndpointType.CLOUD_PC.value,
                    }
                except Exception as e:
                    logger.error(
                        f"Failed to provision Cloud PC for {worker.worker_id}: {e}"
                    )

        # Provision containers
        if container_workers:
            logger.info(f"Provisioning {len(container_workers)} CLI containers")
            endpoint_ids = await self.container_manager.deploy_batch(container_workers)

            for (worker, _config), endpoint_id in zip(container_workers, endpoint_ids, strict=False):
                results[worker.worker_id] = endpoint_id
                self._provisioned_endpoints[worker.worker_id] = {
                    "endpoint_id": endpoint_id,
                    "endpoint_type": EndpointType.CLI_CONTAINER.value,
                }

        logger.info(f"Provisioned {len(results)} endpoints")
        return results

    async def delete_endpoint(
        self,
        worker_id: str,
    ) -> bool:
        """Delete an endpoint for a worker.

        Args:
            worker_id: Worker ID whose endpoint to delete

        Returns:
            True if deleted successfully
        """
        endpoint_info = self._provisioned_endpoints.get(worker_id)
        if not endpoint_info:
            logger.warning(f"No endpoint found for worker {worker_id}")
            return False

        endpoint_id = endpoint_info["endpoint_id"]
        endpoint_type = endpoint_info["endpoint_type"]

        if endpoint_type == EndpointType.CLOUD_PC.value:
            success = await self.cloud_pc_manager.delete_cloud_pc(endpoint_id)
        elif endpoint_type == EndpointType.WINDOWS_VM.value:
            success = await self.windows_vm_manager.delete_vm(endpoint_id)
        else:
            success = await self.container_manager.delete_container(endpoint_id)

        if success:
            del self._provisioned_endpoints[worker_id]

        return success

    async def delete_all_endpoints(self) -> int:
        """Delete all provisioned endpoints.

        Returns:
            Number of successfully deleted endpoints
        """
        deleted = 0
        worker_ids = list(self._provisioned_endpoints.keys())

        for worker_id in worker_ids:
            if await self.delete_endpoint(worker_id):
                deleted += 1

        logger.info(f"Deleted {deleted} of {len(worker_ids)} endpoints")
        return deleted

    async def get_endpoint_status(
        self,
        worker_id: str,
    ) -> dict[str, Any] | None:
        """Get status of a worker's endpoint.

        Args:
            worker_id: Worker ID to check

        Returns:
            Status dictionary or None if not found
        """
        endpoint_info = self._provisioned_endpoints.get(worker_id)
        if not endpoint_info:
            return None

        endpoint_type = endpoint_info["endpoint_type"]
        endpoint_id = endpoint_info["endpoint_id"]

        if endpoint_type == EndpointType.CLOUD_PC.value:
            # Would need worker identity to check Cloud PC status
            return {"type": "cloud_pc", "id": endpoint_id, "status": "unknown"}
        else:
            status = await self.container_manager.get_container_status(
                endpoint_id.split("/")[-1]
            )
            return status

    def get_all_endpoints(self) -> dict[str, dict[str, Any]]:
        """Get all provisioned endpoints.

        Returns:
            Dictionary mapping worker_id to endpoint info
        """
        return self._provisioned_endpoints.copy()

    def get_endpoint_counts(self) -> dict[str, int]:
        """Get count of endpoints by type.

        Returns:
            Dictionary with counts by endpoint type
        """
        counts = {
            EndpointType.CLOUD_PC.value: 0,
            EndpointType.WINDOWS_VM.value: 0,
            EndpointType.CLI_CONTAINER.value: 0,
        }

        for info in self._provisioned_endpoints.values():
            endpoint_type = info.get("endpoint_type", EndpointType.CLI_CONTAINER.value)
            counts[endpoint_type] = counts.get(endpoint_type, 0) + 1

        return counts

    async def _provision_cloud_pc(
        self,
        worker: WorkerIdentity,
    ) -> str:
        """Provision a Cloud PC for a worker.

        Args:
            worker: Worker identity

        Returns:
            Cloud PC ID
        """
        # Ensure provisioning policy exists
        policy_id = await self.cloud_pc_manager.ensure_provisioning_policy()

        # Provision Cloud PC
        return await self.cloud_pc_manager.provision_cloud_pc(worker, policy_id)

    async def _provision_container(
        self,
        worker: WorkerIdentity,
        activity_config: WorkerConfig,
    ) -> str:
        """Provision a CLI container for a worker.

        Args:
            worker: Worker identity
            activity_config: Activity configuration

        Returns:
            Container resource ID
        """
        return await self.container_manager.deploy_worker_container(
            worker, activity_config
        )
