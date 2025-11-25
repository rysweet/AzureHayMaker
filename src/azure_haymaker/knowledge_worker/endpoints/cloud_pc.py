"""Windows 365 Cloud PC management for Knowledge Worker Activity Framework.

Provides Cloud PC provisioning and management for workers requiring
rich desktop telemetry.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

logger = logging.getLogger(__name__)


class Windows365CloudPCManager:
    """Provisions and manages Windows 365 Cloud PCs for workers.

    Uses Graph API Beta endpoint for Cloud PC management:
    - Provisioning policies
    - Device provisioning
    - User assignment

    Cloud PCs provide rich desktop telemetry including:
    - Full Windows event logs
    - Process execution history
    - User behavior analytics

    Attributes:
        graph_client: Microsoft Graph API client
        run_id: HayMaker run ID for this deployment
    """

    PROVISIONING_POLICY_NAME = "HayMaker-KnowledgeWorker-Policy"
    DEFAULT_SKU = "CPC_S_2C_4GB_64GB"  # 2 vCPU, 4GB RAM, 64GB storage
    DEFAULT_IMAGE = "MicrosoftWindowsDesktop_windows-ent-cpc_win11-22h2-ent-cpc-m365"
    PROVISIONING_TIMEOUT_MINUTES = 90
    PROVISIONING_CHECK_INTERVAL_SECONDS = 60

    def __init__(
        self,
        graph_client: Any,
        run_id: str,
    ):
        """Initialize Windows365CloudPCManager.

        Args:
            graph_client: Microsoft Graph API client
            run_id: HayMaker run ID for resource tagging
        """
        self.graph_client = graph_client
        self.run_id = run_id

    async def ensure_provisioning_policy(
        self,
        display_name: str | None = None,
        image_id: str | None = None,
        sku_id: str | None = None,
    ) -> str:
        """Create or get provisioning policy for Cloud PCs.

        Args:
            display_name: Policy display name
            image_id: Gallery image ID
            sku_id: Cloud PC SKU ID

        Returns:
            Policy ID
        """
        policy_name = display_name or self.PROVISIONING_POLICY_NAME
        image = image_id or self.DEFAULT_IMAGE
        sku = sku_id or self.DEFAULT_SKU

        try:
            # Check if policy exists
            policies = await self.graph_client.device_management.virtual_endpoint.provisioning_policies.get()

            existing = next(
                (p for p in (policies.value or []) if p.display_name == policy_name),
                None,
            )

            if existing:
                logger.info(f"Using existing provisioning policy: {policy_name}")
                return existing.id

            # Create new policy
            policy_data = {
                "displayName": policy_name,
                "description": f"HayMaker Knowledge Worker Policy - Run {self.run_id}",
                "provisioningType": "dedicated",
                "imageId": image,
                "imageType": "gallery",
                "domainJoinConfiguration": {
                    "type": "azureADJoin",
                },
            }

            result = await self.graph_client.device_management.virtual_endpoint.provisioning_policies.post(
                body=policy_data
            )

            logger.info(f"Created provisioning policy: {policy_name} ({result.id})")
            return result.id

        except Exception as e:
            logger.error(f"Failed to ensure provisioning policy: {e}")
            raise

    async def provision_cloud_pc(
        self,
        worker: WorkerIdentity,
        policy_id: str,
    ) -> str:
        """Provision a Cloud PC for a worker.

        Args:
            worker: Worker identity to assign Cloud PC
            policy_id: Provisioning policy ID

        Returns:
            Cloud PC ID (or placeholder if provisioning is asynchronous)
        """
        try:
            # Cloud PCs are provisioned by assigning users to policy groups
            # The actual provisioning happens asynchronously

            logger.info(
                f"Cloud PC provisioning initiated for worker: {worker.worker_id}"
            )

            # In a full implementation, this would:
            # 1. Add user to provisioning policy assignment group
            # 2. Wait for provisioning to complete
            # 3. Return the Cloud PC ID

            return f"cloudpc-{worker.worker_id}"

        except Exception as e:
            logger.error(
                f"Failed to provision Cloud PC for {worker.worker_id}: {e}"
            )
            raise

    async def wait_for_provisioning(
        self,
        worker: WorkerIdentity,
        timeout_minutes: int | None = None,
    ) -> bool:
        """Wait for Cloud PC to be provisioned and ready.

        Args:
            worker: Worker identity
            timeout_minutes: Timeout in minutes (default: 90)

        Returns:
            True if provisioned successfully, False on timeout or error
        """
        timeout = timeout_minutes or self.PROVISIONING_TIMEOUT_MINUTES
        start_time = datetime.now()
        deadline = start_time + timedelta(minutes=timeout)

        logger.info(
            f"Waiting for Cloud PC provisioning: {worker.worker_id} "
            f"(timeout: {timeout} minutes)"
        )

        while datetime.now() < deadline:
            try:
                # Check provisioning status
                cloud_pcs = await self.graph_client.device_management.virtual_endpoint.cloud_p_cs.get(
                    request_configuration={
                        "query_parameters": {
                            "filter": f"userPrincipalName eq '{worker.user_principal_name}'"
                        }
                    }
                )

                if cloud_pcs.value:
                    pc = cloud_pcs.value[0]
                    status = pc.status

                    if status == "provisioned":
                        logger.info(f"Cloud PC ready for {worker.worker_id}")
                        return True
                    elif status in ("failed", "error"):
                        logger.error(
                            f"Cloud PC provisioning failed for {worker.worker_id}: {status}"
                        )
                        return False
                    else:
                        logger.debug(
                            f"Cloud PC status for {worker.worker_id}: {status}"
                        )

            except Exception as e:
                logger.warning(
                    f"Error checking Cloud PC status for {worker.worker_id}: {e}"
                )

            await asyncio.sleep(self.PROVISIONING_CHECK_INTERVAL_SECONDS)

        logger.warning(f"Cloud PC provisioning timeout for {worker.worker_id}")
        return False

    async def get_cloud_pc(
        self,
        worker: WorkerIdentity,
    ) -> dict[str, Any] | None:
        """Get Cloud PC information for a worker.

        Args:
            worker: Worker identity

        Returns:
            Cloud PC info dictionary or None if not found
        """
        try:
            cloud_pcs = await self.graph_client.device_management.virtual_endpoint.cloud_p_cs.get(
                request_configuration={
                    "query_parameters": {
                        "filter": f"userPrincipalName eq '{worker.user_principal_name}'"
                    }
                }
            )

            if cloud_pcs.value:
                pc = cloud_pcs.value[0]
                return {
                    "id": pc.id,
                    "display_name": pc.display_name,
                    "status": pc.status,
                    "user_principal_name": pc.user_principal_name,
                    "managed_device_id": pc.managed_device_id,
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get Cloud PC for {worker.worker_id}: {e}")
            return None

    async def delete_cloud_pc(
        self,
        cloud_pc_id: str,
    ) -> bool:
        """Delete a Cloud PC.

        Args:
            cloud_pc_id: Cloud PC ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            await self.graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id(
                cloud_pc_id
            ).delete()

            logger.info(f"Deleted Cloud PC: {cloud_pc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete Cloud PC {cloud_pc_id}: {e}")
            return False

    async def list_cloud_pcs_for_run(self) -> list[dict[str, Any]]:
        """List all Cloud PCs for this run.

        Returns:
            List of Cloud PC info dictionaries
        """
        try:
            # Filter by display name pattern that includes run ID
            cloud_pcs = await self.graph_client.device_management.virtual_endpoint.cloud_p_cs.get()

            run_prefix = f"kw-{self.run_id[:8]}"
            return [
                {
                    "id": pc.id,
                    "display_name": pc.display_name,
                    "status": pc.status,
                    "user_principal_name": pc.user_principal_name,
                }
                for pc in (cloud_pcs.value or [])
                if pc.user_principal_name and run_prefix in pc.user_principal_name
            ]

        except Exception as e:
            logger.error(f"Failed to list Cloud PCs for run {self.run_id}: {e}")
            return []
