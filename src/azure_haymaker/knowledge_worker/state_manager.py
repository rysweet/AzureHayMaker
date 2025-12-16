"""Deployment state persistence for Knowledge Worker orchestrator.

Manages persistent storage of deployment state to ~/.azure_haymaker/
enabling monitoring and recovery across sessions.

State is stored as JSON files with the following structure:
- ~/.azure_haymaker/deployments/{run_id}.json: Deployment state
- ~/.azure_haymaker/workers/{run_id}/{worker_id}.json: Worker details
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

logger = logging.getLogger(__name__)


class DeploymentStateManager:
    """Manages persistent storage of KW deployment state.

    Stores deployment configuration, phase, status, and worker details
    to disk for monitoring and recovery.

    Attributes:
        state_dir: Base directory for state storage (~/.azure_haymaker)
        deployments_dir: Directory for deployment state files
        workers_dir: Directory for worker details
    """

    def __init__(self, state_dir: Path | None = None):
        """Initialize state manager.

        Args:
            state_dir: Base directory for state storage.
                      Defaults to ~/.azure_haymaker
        """
        self.state_dir = state_dir or Path.home() / ".azure_haymaker"
        self.deployments_dir = self.state_dir / "deployments"
        self.workers_dir = self.state_dir / "workers"

        # Create directories if they don't exist
        self.deployments_dir.mkdir(parents=True, exist_ok=True)
        self.workers_dir.mkdir(parents=True, exist_ok=True)

    def save_deployment(
        self,
        run_id: str,
        name: str,
        phase: str,
        status: str,
        worker_count: int,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Save deployment state to disk.

        Args:
            run_id: Deployment run ID
            name: Deployment name
            phase: Current deployment phase
            status: Current deployment status
            worker_count: Number of workers in deployment
            started_at: When deployment started
            completed_at: When deployment completed
            error: Error message if failed
            config: Additional configuration data

        Raises:
            OSError: If file write fails
        """
        deployment_file = self.deployments_dir / f"{run_id}.json"

        state = {
            "run_id": run_id,
            "name": name,
            "phase": phase,
            "status": status,
            "worker_count": worker_count,
            "started_at": started_at.isoformat() if started_at else None,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "error": error,
            "config": config or {},
            "updated_at": datetime.now().isoformat(),
        }

        try:
            deployment_file.write_text(json.dumps(state, indent=2))
            logger.debug(f"Saved deployment state: {run_id}")
        except Exception as e:
            logger.error(f"Failed to save deployment state for {run_id}: {e}")
            raise

    def load_deployment(self, run_id: str) -> dict[str, Any] | None:
        """Load deployment state from disk.

        Args:
            run_id: Deployment run ID

        Returns:
            Dictionary with deployment state, or None if not found
        """
        deployment_file = self.deployments_dir / f"{run_id}.json"

        if not deployment_file.exists():
            return None

        try:
            state = json.loads(deployment_file.read_text())
            logger.debug(f"Loaded deployment state: {run_id}")
            return state
        except Exception as e:
            logger.error(f"Failed to load deployment state for {run_id}: {e}")
            return None

    def list_deployments(self) -> list[dict[str, Any]]:
        """List all deployment states.

        Returns:
            List of deployment state dictionaries, sorted by updated_at descending
        """
        deployments = []

        for file_path in self.deployments_dir.glob("*.json"):
            try:
                state = json.loads(file_path.read_text())
                deployments.append(state)
            except Exception as e:
                logger.warning(f"Failed to load deployment from {file_path}: {e}")

        # Sort by updated_at descending (most recent first)
        deployments.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return deployments

    def delete_deployment(self, run_id: str) -> bool:
        """Delete deployment state from disk.

        Args:
            run_id: Deployment run ID

        Returns:
            True if deleted, False if not found
        """
        deployment_file = self.deployments_dir / f"{run_id}.json"

        if deployment_file.exists():
            deployment_file.unlink()
            logger.info(f"Deleted deployment state: {run_id}")
            return True

        return False

    def save_worker(
        self,
        run_id: str,
        worker: WorkerIdentity,
    ) -> None:
        """Save worker details to disk.

        Args:
            run_id: Deployment run ID
            worker: Worker identity with details

        Raises:
            OSError: If file write fails
        """
        worker_run_dir = self.workers_dir / run_id
        worker_run_dir.mkdir(parents=True, exist_ok=True)

        worker_file = worker_run_dir / f"{worker.worker_id}.json"

        worker_data = {
            "worker_id": worker.worker_id,
            "display_name": worker.display_name,
            "user_principal_name": worker.user_principal_name,
            "entra_object_id": worker.entra_object_id,
            "persona": worker.persona.value,
            "endpoint_type": worker.endpoint_type.value,
            "department": worker.department,
            "team_ids": worker.team_ids,
            "run_id": run_id,
            "updated_at": datetime.now().isoformat(),
        }

        try:
            worker_file.write_text(json.dumps(worker_data, indent=2))
            logger.debug(f"Saved worker: {worker.worker_id}")
        except Exception as e:
            logger.error(f"Failed to save worker {worker.worker_id}: {e}")
            raise

    def load_workers(self, run_id: str) -> list[dict[str, Any]]:
        """Load all workers for a deployment.

        Args:
            run_id: Deployment run ID

        Returns:
            List of worker data dictionaries
        """
        worker_run_dir = self.workers_dir / run_id

        if not worker_run_dir.exists():
            return []

        workers = []
        for file_path in worker_run_dir.glob("*.json"):
            try:
                worker_data = json.loads(file_path.read_text())
                workers.append(worker_data)
            except Exception as e:
                logger.warning(f"Failed to load worker from {file_path}: {e}")

        return workers

    def delete_workers(self, run_id: str) -> int:
        """Delete all worker files for a deployment.

        Args:
            run_id: Deployment run ID

        Returns:
            Number of worker files deleted
        """
        worker_run_dir = self.workers_dir / run_id

        if not worker_run_dir.exists():
            return 0

        count = 0
        for file_path in worker_run_dir.glob("*.json"):
            file_path.unlink()
            count += 1

        # Remove directory if empty
        import contextlib

        with contextlib.suppress(OSError):
            worker_run_dir.rmdir()

        logger.info(f"Deleted {count} worker files for {run_id}")
        return count

    def get_recent_deployments(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most recent deployments.

        Args:
            limit: Maximum number of deployments to return

        Returns:
            List of deployment state dictionaries, most recent first
        """
        all_deployments = self.list_deployments()
        return all_deployments[:limit]


__all__ = ["DeploymentStateManager"]
