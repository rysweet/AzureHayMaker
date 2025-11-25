"""M365 CLI Container management for Knowledge Worker Activity Framework.

Provides container deployment and management for workers using
CLI-based M365 activity execution.
"""

import asyncio
import logging
from typing import Any

from azure_haymaker.knowledge_worker.models.worker import (
    WorkerConfig,
    WorkerIdentity,
)

logger = logging.getLogger(__name__)


class M365CLIContainerManager:
    """Manages M365 CLI containers for knowledge worker activity.

    Each container runs M365 CLI (PnP) with certificate authentication,
    executing worker activities via Graph API calls. This provides
    a cost-effective alternative to Cloud PCs for scale workers.

    Container Configuration:
        - Image: M365 CLI with Python activity scheduler
        - Resources: 0.25 vCPU, 0.5 GB RAM
        - Auth: Certificate-based via Key Vault mount

    Attributes:
        config: Orchestrator configuration
        run_id: HayMaker run ID for this deployment
    """

    CONTAINER_IMAGE = "haymakerorchacr.azurecr.io/kw-m365-cli:latest"
    DEFAULT_CPU = "0.25"
    DEFAULT_MEMORY = "0.5Gi"

    def __init__(
        self,
        config: Any,
        run_id: str,
    ):
        """Initialize M365CLIContainerManager.

        Args:
            config: Orchestrator configuration with container settings
            run_id: HayMaker run ID for resource tagging
        """
        self.config = config
        self.run_id = run_id

    async def deploy_worker_container(
        self,
        worker: WorkerIdentity,
        activity_config: WorkerConfig,
    ) -> str:
        """Deploy a container for a knowledge worker.

        The container runs M365 CLI with:
        - Certificate authentication
        - Worker identity configuration
        - Activity schedule

        Args:
            worker: Worker identity
            activity_config: Activity patterns for this worker

        Returns:
            Container App resource ID
        """
        container_name = f"kw-{self.run_id[:8]}-{worker.worker_id}"

        # Build environment variables
        env_vars = {
            "WORKER_ID": worker.worker_id,
            "WORKER_UPN": worker.user_principal_name,
            "WORKER_DEPARTMENT": worker.department,
            "WORKER_PERSONA": worker.persona.value,
            "TEAM_IDS": ",".join(worker.team_ids),
            "M365_APP_ID": getattr(self.config, "m365_app_client_id", ""),
            "M365_TENANT_ID": getattr(self.config, "target_tenant_id", ""),
            "M365_CERT_PATH": "/secrets/m365-cert.pem",
            "EMAIL_PER_HOUR": str(activity_config.email_per_hour),
            "TEAMS_MESSAGES_PER_HOUR": str(activity_config.teams_messages_per_hour),
            "DOCUMENTS_PER_DAY": str(activity_config.documents_per_day),
            "MEETINGS_PER_DAY": str(activity_config.meetings_per_day),
            "WORK_START_HOUR": str(activity_config.work_start_hour),
            "WORK_END_HOUR": str(activity_config.work_end_hour),
        }

        try:
            # Deploy container
            resource_id = await self._deploy_container_app(
                name=container_name,
                image=self.CONTAINER_IMAGE,
                env_vars=env_vars,
                cpu=self.DEFAULT_CPU,
                memory=self.DEFAULT_MEMORY,
            )

            logger.info(
                f"CLI container deployed for worker: {worker.worker_id} -> {resource_id}"
            )

            return resource_id

        except Exception as e:
            logger.error(
                f"Failed to deploy container for {worker.worker_id}: {e}"
            )
            raise

    async def deploy_batch(
        self,
        workers: list[tuple[WorkerIdentity, WorkerConfig]],
        max_parallel: int = 10,
    ) -> list[str]:
        """Deploy containers for multiple workers in parallel.

        Args:
            workers: List of (identity, config) tuples
            max_parallel: Maximum concurrent deployments

        Returns:
            List of container resource IDs
        """
        resource_ids: list[str] = []

        # Deploy in batches
        for i in range(0, len(workers), max_parallel):
            batch = workers[i : i + max_parallel]

            tasks = [
                self.deploy_worker_container(worker, config)
                for worker, config in batch
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, str):
                    resource_ids.append(result)
                else:
                    logger.error(f"Container deployment failed: {result}")

        logger.info(
            f"Deployed {len(resource_ids)} of {len(workers)} containers"
        )
        return resource_ids

    async def stop_container(
        self,
        container_name: str,
    ) -> bool:
        """Stop a running container.

        Args:
            container_name: Container app name

        Returns:
            True if stopped successfully
        """
        try:
            # In production, this would use the Container Apps API
            # to stop the container revision
            logger.info(f"Stopped container: {container_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop container {container_name}: {e}")
            return False

    async def delete_container(
        self,
        resource_id: str,
    ) -> bool:
        """Delete a container app.

        Args:
            resource_id: Full Azure resource ID

        Returns:
            True if deleted successfully
        """
        try:
            # In production, this would use the Container Apps API
            # or Azure Resource Manager to delete the container app
            logger.info(f"Deleted container: {resource_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete container {resource_id}: {e}")
            return False

    async def list_containers_for_run(self) -> list[dict[str, Any]]:
        """List all containers for this run.

        Returns:
            List of container info dictionaries
        """
        try:
            # In production, this would query the Container Apps API
            # filtering by naming convention or tags
            logger.info(f"Listed containers for run: {self.run_id}")
            return []

        except Exception as e:
            logger.error(f"Failed to list containers for run {self.run_id}: {e}")
            return []

    async def get_container_status(
        self,
        container_name: str,
    ) -> dict[str, Any] | None:
        """Get status of a container.

        Args:
            container_name: Container app name

        Returns:
            Status dictionary or None if not found
        """
        try:
            # In production, this would query the Container Apps API
            return {
                "name": container_name,
                "status": "running",
                "replicas": 1,
            }

        except Exception as e:
            logger.error(f"Failed to get container status for {container_name}: {e}")
            return None

    async def _deploy_container_app(
        self,
        name: str,
        image: str,
        env_vars: dict[str, str],
        cpu: str,
        memory: str,
    ) -> str:
        """Internal method to deploy a container app.

        This would use the Azure Container Apps SDK in production.

        Args:
            name: Container app name
            image: Container image
            env_vars: Environment variables
            cpu: CPU allocation
            memory: Memory allocation

        Returns:
            Resource ID of deployed container
        """
        # Placeholder for actual Container Apps deployment
        # In production, this would use:
        # - azure-mgmt-appcontainers SDK
        # - or the existing ContainerDeployer from HayMaker

        resource_id = (
            f"/subscriptions/placeholder/resourceGroups/placeholder/"
            f"providers/Microsoft.App/containerApps/{name}"
        )

        logger.debug(
            f"Deploying container app: {name} "
            f"(image: {image}, cpu: {cpu}, memory: {memory})"
        )

        return resource_id
