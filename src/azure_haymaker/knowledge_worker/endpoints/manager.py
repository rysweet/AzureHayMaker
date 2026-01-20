"""Endpoint manager facade for Knowledge Worker Activity Framework.

Provides unified management of Cloud PC, Windows VM, and CLI container
endpoints for knowledge workers with cascade fallback support.

This module provides a facade that composes lifecycle, providers, and fallback
modules while maintaining 100% backward compatibility with the original API.

Philosophy:
- Facade pattern: Composes other modules
- Backward compatibility: Preserves original API exactly
- No business logic: Just delegation
- Self-contained brick with clear public API

Public API (the "studs"):
    EndpointManager: Unified endpoint management facade
    ProvisioningError: Re-exported from providers
    AllEndpointsFailedError: Re-exported from fallback
"""

import logging
from typing import Any

from azure_haymaker.knowledge_worker.endpoints.fallback import (
    AllEndpointsFailedError,
    EndpointFallbackCoordinator,
)
from azure_haymaker.knowledge_worker.endpoints.lifecycle import (
    EndpointLifecycleManager,
)
from azure_haymaker.knowledge_worker.endpoints.providers import (
    EndpointProviderManager,
    ProvisioningError,
)
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerConfig,
    WorkerIdentity,
)

logger = logging.getLogger(__name__)

__all__ = [
    "EndpointManager",
    "ProvisioningError",
    "AllEndpointsFailedError",
]


class EndpointManager:
    """Unified endpoint management for knowledge workers.

    Coordinates provisioning and management across all endpoint types
    with cascade fallback support:
    - Windows 365 Cloud PCs (for rich telemetry)
    - Azure Windows VMs (fallback for Computer Use Agents)
    - M365 CLI Containers (for cost-effective scale)

    This is a facade that composes lifecycle, providers, and fallback modules.

    Attributes:
        _lifecycle: Lifecycle manager for endpoint tracking
        _providers: Provider manager for endpoint operations
        _fallback: Fallback coordinator for cascade logic
        run_id: HayMaker run ID for this deployment
        cloud_pc_manager: Reference to Cloud PC manager (for compatibility)
        windows_vm_manager: Reference to Windows VM manager (for compatibility)
        container_manager: Reference to container manager (for compatibility)
    """

    def __init__(
        self,
        cloud_pc_manager=None,
        windows_vm_manager=None,
        container_manager=None,
        graph_client=None,
        config=None,
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

        # Initialize components
        self._providers = EndpointProviderManager(
            cloud_pc_manager,
            windows_vm_manager,
            container_manager,
            graph_client,
            config,
            run_id,
        )
        self._lifecycle = EndpointLifecycleManager(run_id)
        self._fallback = EndpointFallbackCoordinator(self._providers)

        # Keep references for backward compatibility
        self.cloud_pc_manager = self._providers.cloud_pc_manager
        self.windows_vm_manager = self._providers.windows_vm_manager
        self.container_manager = self._providers.container_manager

        # For backward compatibility with internal access
        self._provisioned_endpoints = self._lifecycle._provisioned_endpoints

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
        self._lifecycle.track_endpoint(
            worker.worker_id, endpoint_id, endpoint_type
        )

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
        result = await self._fallback.provision_with_fallback(worker)

        # Track the successfully provisioned endpoint
        self._lifecycle.track_endpoint(
            worker.worker_id,
            result["endpoint_id"],
            result["endpoint_type"],
            result.get("details"),
        )

        return result

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
                    self._lifecycle.track_endpoint(
                        worker.worker_id, endpoint_id, EndpointType.CLOUD_PC
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to provision Cloud PC for {worker.worker_id}: {e}"
                    )

        # Provision containers
        if container_workers:
            if not self.container_manager:
                raise ProvisioningError(
                    "Container manager not configured but containers requested"
                )
            logger.info(f"Provisioning {len(container_workers)} CLI containers")
            endpoint_ids = await self.container_manager.deploy_batch(container_workers)

            for (worker, _config), endpoint_id in zip(
                container_workers, endpoint_ids, strict=False
            ):
                results[worker.worker_id] = endpoint_id
                self._lifecycle.track_endpoint(
                    worker.worker_id, endpoint_id, EndpointType.CLI_CONTAINER
                )

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
        endpoint_info = self._lifecycle.get_endpoint_info(worker_id)
        if not endpoint_info:
            logger.warning(f"No endpoint found for worker {worker_id}")
            return False

        endpoint_id = endpoint_info["endpoint_id"]
        endpoint_type = endpoint_info["endpoint_type"]

        # Delegate deletion to providers
        if endpoint_type == EndpointType.CLOUD_PC.value:
            success = await self._providers.delete_cloud_pc(endpoint_id)
        elif endpoint_type == EndpointType.WINDOWS_VM.value:
            success = await self._providers.delete_windows_vm(endpoint_id)
        else:
            success = await self._providers.delete_container(endpoint_id)

        if success:
            self._lifecycle.untrack_endpoint(worker_id)

        return success

    async def delete_all_endpoints(self) -> int:
        """Delete all provisioned endpoints.

        Returns:
            Number of successfully deleted endpoints
        """
        deleted = 0
        all_endpoints = self._lifecycle.get_all_endpoints()
        worker_ids = list(all_endpoints.keys())

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
        endpoint_info = self._lifecycle.get_endpoint_info(worker_id)
        if not endpoint_info:
            return None

        endpoint_type = endpoint_info["endpoint_type"]
        endpoint_id = endpoint_info["endpoint_id"]

        if endpoint_type == EndpointType.CLOUD_PC.value:
            # Would need worker identity to check Cloud PC status
            return {"type": "cloud_pc", "id": endpoint_id, "status": "unknown"}
        else:
            if not self.container_manager:
                raise ProvisioningError("Container manager not configured")
            status = await self._providers.get_container_status(
                endpoint_id.split("/")[-1]
            )
            return status

    def get_all_endpoints(self) -> dict[str, dict[str, Any]]:
        """Get all provisioned endpoints.

        Returns:
            Dictionary mapping worker_id to endpoint info
        """
        return self._lifecycle.get_all_endpoints()

    def get_endpoint_counts(self) -> dict[str, int]:
        """Get count of endpoints by type.

        Returns:
            Dictionary with counts by endpoint type
        """
        return self._lifecycle.get_endpoint_counts()

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
        return await self._providers.provision_cloud_pc(worker)

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
        return await self._providers.provision_container(worker, activity_config)
