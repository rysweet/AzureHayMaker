"""Worker registry for cross-worker communication.

Provides a registry of all workers in a deployment to enable cross-worker
communication and activity coordination.
"""

import random
from dataclasses import dataclass, field

from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity


@dataclass
class WorkerRegistry:
    """Registry of all workers in a deployment for cross-worker communication.

    Maintains a mapping of worker identities to enable:
    - Cross-worker email communication with valid internal recipients
    - Department-based recipient selection for realistic activity patterns
    - Random recipient selection for varied communication patterns

    Attributes:
        run_id: HayMaker run ID for this deployment
        _workers: Internal mapping of worker_id to WorkerIdentity

    Example:
        >>> registry = WorkerRegistry("kw-abc12345")
        >>> registry.register(worker_identity)
        >>> recipients = registry.get_random_recipients("kw-abc12345-engi-001", count=2)
        >>> all_upns = registry.get_all_upns()
    """

    run_id: str
    _workers: dict[str, WorkerIdentity] = field(default_factory=dict)

    def register(self, identity: WorkerIdentity) -> None:
        """Register a worker identity.

        Args:
            identity: WorkerIdentity to register
        """
        self._workers[identity.worker_id] = identity

    def unregister(self, worker_id: str) -> None:
        """Unregister a worker by ID.

        Args:
            worker_id: ID of worker to remove
        """
        self._workers.pop(worker_id, None)

    def get(self, worker_id: str) -> WorkerIdentity | None:
        """Get a worker identity by ID.

        Args:
            worker_id: Worker ID to look up

        Returns:
            WorkerIdentity if found, None otherwise
        """
        return self._workers.get(worker_id)

    def get_all_upns(self) -> list[str]:
        """Get all worker UPNs for communication validation.

        Returns:
            List of user principal names for all registered workers
        """
        return [w.user_principal_name for w in self._workers.values() if w.user_principal_name]

    def get_all_workers(self) -> list[WorkerIdentity]:
        """Get all registered workers.

        Returns:
            List of all WorkerIdentity objects
        """
        return list(self._workers.values())

    def get_workers_by_department(self, department: str) -> list[WorkerIdentity]:
        """Get workers in a specific department.

        Args:
            department: Department name to filter by

        Returns:
            List of workers in the specified department
        """
        return [w for w in self._workers.values() if w.department.lower() == department.lower()]

    def get_random_recipients(
        self,
        exclude: str,
        count: int = 1,
    ) -> list[str]:
        """Get random worker UPNs for activity generation.

        Selects random recipients from registered workers, excluding
        the specified worker (typically the sender).

        Args:
            exclude: Worker ID to exclude from selection (usually self)
            count: Number of recipients to select

        Returns:
            List of randomly selected UPNs (may be fewer than count if
            not enough candidates available)
        """
        candidates = [
            w.user_principal_name
            for w in self._workers.values()
            if w.worker_id != exclude and w.user_principal_name
        ]
        return random.sample(candidates, min(count, len(candidates)))

    def get_random_recipients_from_department(
        self,
        exclude: str,
        department: str,
        count: int = 1,
    ) -> list[str]:
        """Get random worker UPNs from a specific department.

        Args:
            exclude: Worker ID to exclude from selection
            department: Department to select from
            count: Number of recipients to select

        Returns:
            List of randomly selected UPNs from the department
        """
        candidates = [
            w.user_principal_name
            for w in self._workers.values()
            if w.worker_id != exclude
            and w.department.lower() == department.lower()
            and w.user_principal_name
        ]
        return random.sample(candidates, min(count, len(candidates)))

    @property
    def worker_count(self) -> int:
        """Get the number of registered workers.

        Returns:
            Count of registered workers
        """
        return len(self._workers)


__all__ = ["WorkerRegistry"]
