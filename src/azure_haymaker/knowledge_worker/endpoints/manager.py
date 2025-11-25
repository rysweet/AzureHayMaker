"""Endpoint manager for Knowledge Worker Activity Framework.

Provides unified management of both Cloud PC and CLI container
endpoints for knowledge workers.
"""

import logging
from typing import Any

from azure_haymaker.knowledge_worker.endpoints.cli_container import (
    M365CLIContainerManager,
)
from azure_haymaker.knowledge_worker.endpoints.cloud_pc import (
    Windows365CloudPCManager,
)
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerConfig,
    WorkerIdentity,
)

logger = logging.getLogger(__name__)


class EndpointManager:
    """Unified endpoint management for knowledge workers.

    Coordinates provisioning and management across both endpoint types:
    - Windows 365 Cloud PCs (for rich telemetry)
    - M365 CLI Containers (for cost-effective scale)

    Attributes:
        cloud_pc_manager: Manager for Cloud PC endpoints
        container_manager: Manager for CLI container endpoints
        run_id: HayMaker run ID for this deployment
    """

    def __init__(
        self,
        graph_client: Any,
        config: Any,
        run_id: str,
    ):
        """Initialize EndpointManager.

        Args:
            graph_client: Microsoft Graph API client
            config: Orchestrator configuration
            run_id: HayMaker run ID for resource tagging
        """
        self.run_id = run_id
        self.cloud_pc_manager = Windows365CloudPCManager(graph_client, run_id)
        self.container_manager = M365CLIContainerManager(config, run_id)
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
            for worker, config in cloud_pc_workers:
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

            for (worker, config), endpoint_id in zip(container_workers, endpoint_ids):
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
