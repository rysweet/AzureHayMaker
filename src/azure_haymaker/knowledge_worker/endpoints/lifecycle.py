"""Endpoint lifecycle management for Knowledge Worker Activity Framework.

Tracks WHO has what endpoints, their status, and statistics.

Philosophy:
- Single responsibility: Lifecycle state tracking only
- No provisioning logic: Just tracks what's been provisioned
- No deletion logic: Just untracks what's been deleted
- Self-contained brick with clear public API

Public API (the "studs"):
    EndpointLifecycleManager: Manages endpoint lifecycle state
"""

import logging
from typing import Any

from azure_haymaker.knowledge_worker.models.worker import EndpointType

logger = logging.getLogger(__name__)

__all__ = ["EndpointLifecycleManager"]


class EndpointLifecycleManager:
    """Manages lifecycle state of provisioned endpoints.

    Tracks which workers have which endpoints without knowing HOW they
    were provisioned or how to delete them.

    Attributes:
        run_id: HayMaker run ID for this deployment
        _provisioned_endpoints: Dictionary mapping worker_id to endpoint info
    """

    def __init__(self, run_id: str = ""):
        """Initialize lifecycle manager.

        Args:
            run_id: HayMaker run ID for resource tagging
        """
        self.run_id = run_id
        self._provisioned_endpoints: dict[str, dict[str, Any]] = {}

    def track_endpoint(
        self,
        worker_id: str,
        endpoint_id: str,
        endpoint_type: EndpointType,
        details: dict | None = None,
    ) -> None:
        """Track a newly provisioned endpoint.

        Args:
            worker_id: Worker identifier
            endpoint_id: Endpoint resource ID
            endpoint_type: Type of endpoint (CLOUD_PC, WINDOWS_VM, CLI_CONTAINER)
            details: Optional additional details about the endpoint
        """
        self._provisioned_endpoints[worker_id] = {
            "endpoint_id": endpoint_id,
            "endpoint_type": endpoint_type.value,
            "worker_id": worker_id,
        }

        if details:
            self._provisioned_endpoints[worker_id]["details"] = details

        logger.debug(
            f"Tracking endpoint for {worker_id}: "
            f"{endpoint_type.value} -> {endpoint_id}"
        )

    def untrack_endpoint(self, worker_id: str) -> bool:
        """Remove endpoint from tracking.

        Args:
            worker_id: Worker identifier

        Returns:
            True if endpoint was tracked and removed, False if not found
        """
        if worker_id in self._provisioned_endpoints:
            endpoint_info = self._provisioned_endpoints[worker_id]
            del self._provisioned_endpoints[worker_id]
            logger.debug(
                f"Untracked endpoint for {worker_id}: "
                f"{endpoint_info.get('endpoint_type')} -> "
                f"{endpoint_info.get('endpoint_id')}"
            )
            return True

        logger.warning(f"No endpoint found for worker {worker_id}")
        return False

    def get_endpoint_info(self, worker_id: str) -> dict[str, Any] | None:
        """Get tracked endpoint information.

        Args:
            worker_id: Worker identifier

        Returns:
            Endpoint info dict or None if not found
        """
        return self._provisioned_endpoints.get(worker_id)

    def get_all_endpoints(self) -> dict[str, dict[str, Any]]:
        """Get all tracked endpoints.

        Returns:
            Copy of _provisioned_endpoints dict
        """
        return self._provisioned_endpoints.copy()

    def get_endpoint_counts(self) -> dict[str, int]:
        """Get count of endpoints by type.

        Returns:
            Dictionary mapping endpoint type to count
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

    def clear_all(self) -> int:
        """Clear all tracked endpoints.

        Returns:
            Number of endpoints cleared
        """
        count = len(self._provisioned_endpoints)
        self._provisioned_endpoints.clear()
        logger.info(f"Cleared {count} tracked endpoints")
        return count
