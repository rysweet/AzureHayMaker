"""Cascade fallback coordination for endpoint provisioning.

Orchestrates WHEN to try alternatives when provisioning fails.
Implements the cascade strategy: Cloud PC → Windows VM → Container.

Philosophy:
- Single responsibility: Fallback coordination only
- No provisioning logic: Delegates to provider manager
- Updates worker state: Reflects actually provisioned endpoint type
- Self-contained brick with clear public API

Public API (the "studs"):
    EndpointFallbackCoordinator: Cascade fallback orchestration
    AllEndpointsFailedError: Exception when all fallbacks exhausted
"""

import logging
from typing import Any

from azure_haymaker.knowledge_worker.endpoints.providers import EndpointProviderManager
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerConfig,
    WorkerIdentity,
)

logger = logging.getLogger(__name__)

__all__ = ["EndpointFallbackCoordinator", "AllEndpointsFailedError"]


class AllEndpointsFailedError(Exception):
    """Raised when all endpoint types fail to provision.

    This error indicates that the cascade fallback exhausted all options:
    Cloud PC → Windows VM → Container, and none succeeded.
    """

    pass


class EndpointFallbackCoordinator:
    """Cascade fallback coordinator for endpoint provisioning.

    Orchestrates fallback strategy when provisioning fails:
    1. Try Cloud PC first
    2. Fallback to Windows VM if Cloud PC fails
    3. Fallback to Container if Windows VM fails
    4. Raise AllEndpointsFailedError if all fail

    Attributes:
        _provider_manager: Provider manager for provisioning operations
    """

    def __init__(self, provider_manager: EndpointProviderManager):
        """Initialize fallback coordinator.

        Args:
            provider_manager: Provider manager for provisioning operations
        """
        self._provider_manager = provider_manager

    async def provision_with_fallback(self, worker: WorkerIdentity) -> dict[str, Any]:
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
        result = await self._try_cloud_pc(worker, failures)
        if result:
            return result

        # Try Windows VM fallback
        result = await self._try_windows_vm(worker, failures)
        if result:
            return result

        # Try Container fallback
        result = await self._try_container(worker, failures)
        if result:
            return result

        # All endpoints failed
        failure_summary = "; ".join([f"{ep}: {reason}" for ep, reason in failures])
        error_msg = (
            f"All endpoint types failed for worker {worker.worker_id}: "
            f"{failure_summary}"
        )
        logger.error(error_msg)
        raise AllEndpointsFailedError(error_msg)

    async def _try_cloud_pc(
        self, worker: WorkerIdentity, failures: list
    ) -> dict[str, Any] | None:
        """Try to provision Cloud PC endpoint.

        Args:
            worker: Worker identity
            failures: List to append failure info to

        Returns:
            Result dict if successful, None if failed
        """
        if not self._provider_manager.cloud_pc_manager:
            return None

        try:
            logger.info(f"Attempting Cloud PC provisioning for {worker.worker_id}")
            cloud_pc_id = await self._provider_manager.provision_cloud_pc_with_timeout(
                worker
            )

            if cloud_pc_id:
                # Update worker
                worker.endpoint_type = EndpointType.CLOUD_PC
                worker.endpoint_id = cloud_pc_id

                logger.info(
                    f"Cloud PC provisioned successfully for {worker.worker_id}: "
                    f"{cloud_pc_id}"
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
                return None

        except Exception as e:
            reason = type(e).__name__
            failures.append(("Cloud PC", reason))
            logger.warning(f"Cloud PC failed for {worker.worker_id}: {e}")
            return None

    async def _try_windows_vm(
        self, worker: WorkerIdentity, failures: list
    ) -> dict[str, Any] | None:
        """Try to provision Windows VM endpoint.

        Args:
            worker: Worker identity
            failures: List to append failure info to

        Returns:
            Result dict if successful, None if failed
        """
        if not self._provider_manager.windows_vm_manager:
            return None

        try:
            logger.info(
                f"Attempting Windows VM fallback provisioning for {worker.worker_id}"
            )
            vm_details = await self._provider_manager.provision_windows_vm(worker)

            if vm_details:
                vm_name = vm_details["vm_name"]

                # Update worker
                worker.endpoint_type = EndpointType.WINDOWS_VM
                worker.endpoint_id = vm_name

                logger.info(
                    f"Windows VM provisioned successfully for {worker.worker_id}: "
                    f"{vm_name}"
                )
                return {
                    "endpoint_type": EndpointType.WINDOWS_VM,
                    "endpoint_id": vm_name,
                    "success": True,
                    "details": vm_details,
                }

        except Exception as e:
            reason = type(e).__name__
            failures.append(("Windows VM", reason))
            logger.warning(f"Windows VM failed for {worker.worker_id}: {e}")

        return None

    async def _try_container(
        self, worker: WorkerIdentity, failures: list
    ) -> dict[str, Any] | None:
        """Try to provision CLI container endpoint.

        Args:
            worker: Worker identity
            failures: List to append failure info to

        Returns:
            Result dict if successful, None if failed
        """
        if not self._provider_manager.container_manager:
            return None

        try:
            logger.info(
                f"Attempting Container fallback provisioning for {worker.worker_id}"
            )

            # For containers in fallback, use default config
            default_config = WorkerConfig()
            container_id = await self._provider_manager.container_manager.deploy_worker_container(
                worker, default_config
            )

            if not container_id:
                raise Exception(f"No container_id returned for {worker.worker_id}")

            # Update worker
            worker.endpoint_type = EndpointType.CLI_CONTAINER
            worker.endpoint_id = container_id

            logger.info(
                f"Container provisioned successfully for {worker.worker_id}: "
                f"{container_id}"
            )
            return {
                "endpoint_type": EndpointType.CLI_CONTAINER,
                "endpoint_id": container_id,
                "success": True,
                "details": {
                    "container_id": container_id,
                    "status": "running",
                },
            }

        except Exception as e:
            reason = type(e).__name__
            failures.append(("Container", reason))
            logger.error(f"Container failed for {worker.worker_id}: {e}")

        return None
