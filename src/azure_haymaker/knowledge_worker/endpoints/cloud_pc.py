"""Windows 365 Cloud PC management for Knowledge Worker Activity Framework.

Provides Cloud PC provisioning and management for workers requiring
rich desktop telemetry.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
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
        self._permission_fallbacks: list[dict[str, Any]] = []

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
        selected_sku = sku_id or self.DEFAULT_SKU

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
                "cloudPcNamingTemplate": f"kw-{self.run_id[:8]}-%RAND:5%",
                "microsoftManagedDesktop": {
                    "type": "starterManaged",
                    "profile": selected_sku,
                },
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

        Cloud PCs are provisioned by assigning users to policy assignment groups.
        The actual provisioning happens asynchronously via Windows 365 service.

        Gracefully handles permission errors by falling back to mock provisioning.

        Args:
            worker: Worker identity to assign Cloud PC
            policy_id: Provisioning policy ID

        Returns:
            Cloud PC ID (placeholder until async provisioning completes, or mock ID on fallback)
        """
        try:
            logger.info(
                f"Cloud PC provisioning initiated for worker: {worker.worker_id}"
            )

            # Step 1: Get or create the assignment group for this policy
            group_id = await self._get_or_create_assignment_group(policy_id)

            # Step 2: Add user to the assignment group
            await self._add_user_to_group(worker, group_id)

            # Step 3: Assign group to policy (if not already assigned)
            await self._assign_group_to_policy(policy_id, group_id)

            logger.info(
                f"Cloud PC provisioning group assignment complete for {worker.worker_id}"
            )

            # Return placeholder ID - actual Cloud PC ID will be available
            # after async provisioning completes
            return f"pending-{worker.worker_id}"

        except Exception as e:
            # Check if this is a permission error
            error_msg = str(e).lower()
            if "insufficient privileges" in error_msg or "403" in error_msg or "unauthorized" in error_msg:
                return await self._handle_permission_fallback(worker, policy_id, e)

            # For other errors, re-raise
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

        Polls Cloud PC provisioning status with progress tracking and logging.

        Args:
            worker: Worker identity
            timeout_minutes: Timeout in minutes (default: 90)

        Returns:
            True if provisioned successfully, False on timeout or error
        """
        timeout = timeout_minutes or self.PROVISIONING_TIMEOUT_MINUTES
        start_time = datetime.now()
        deadline = start_time + timedelta(minutes=timeout)
        last_status = None
        check_count = 0

        logger.info(
            f"Waiting for Cloud PC provisioning: {worker.worker_id} "
            f"(timeout: {timeout} minutes)"
        )

        while datetime.now() < deadline:
            check_count += 1
            elapsed = (datetime.now() - start_time).total_seconds() / 60

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

                    # Log status changes
                    if status != last_status:
                        logger.info(
                            f"Cloud PC status for {worker.worker_id}: {status} "
                            f"(elapsed: {elapsed:.1f} min, check: {check_count})"
                        )
                        last_status = status

                    if status == "provisioned":
                        logger.info(
                            f"Cloud PC ready for {worker.worker_id} "
                            f"(total time: {elapsed:.1f} minutes)"
                        )
                        return True
                    elif status in ("failed", "error"):
                        logger.error(
                            f"Cloud PC provisioning failed for {worker.worker_id}: {status}"
                        )
                        return False
                    else:
                        logger.debug(
                            f"Cloud PC status for {worker.worker_id}: {status} "
                            f"(check {check_count}, elapsed {elapsed:.1f} min)"
                        )
                else:
                    # No Cloud PC found yet - provisioning not started
                    if check_count % 5 == 0:  # Log every 5th check
                        logger.debug(
                            f"Cloud PC not found yet for {worker.worker_id} "
                            f"(check {check_count}, elapsed {elapsed:.1f} min)"
                        )

            except Exception as e:
                logger.warning(
                    f"Error checking Cloud PC status for {worker.worker_id}: {e} "
                    f"(check {check_count}, will retry)"
                )

            await asyncio.sleep(self.PROVISIONING_CHECK_INTERVAL_SECONDS)

        elapsed_total = (datetime.now() - start_time).total_seconds() / 60
        logger.warning(
            f"Cloud PC provisioning timeout for {worker.worker_id} "
            f"(elapsed: {elapsed_total:.1f} minutes, checks: {check_count})"
        )
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

    async def provision_batch(
        self,
        workers: list[WorkerIdentity],
        policy_id: str,
        max_concurrent: int = 10,
    ) -> list[tuple[WorkerIdentity, str]]:
        """Provision Cloud PCs for multiple workers efficiently.

        Provisions Cloud PCs concurrently with rate limiting to avoid
        overwhelming the Graph API.

        Args:
            workers: List of worker identities
            policy_id: Provisioning policy ID
            max_concurrent: Maximum concurrent provisioning operations

        Returns:
            List of (worker, cloud_pc_id) tuples
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def provision_one(worker: WorkerIdentity) -> tuple[WorkerIdentity, str]:
            async with semaphore:
                cloud_pc_id = await self.provision_cloud_pc(
                    worker=worker, policy_id=policy_id
                )
                return (worker, cloud_pc_id)

        tasks = [provision_one(worker) for worker in workers]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, Exception):
                logger.error(f"Batch provisioning error: {result}")
            else:
                results.append(result)

        logger.info(
            f"Batch provisioning complete: {len(results)}/{len(workers)} successful"
        )
        return results

    async def _get_or_create_assignment_group(self, policy_id: str) -> str:
        """Get or create an Entra group for Cloud PC policy assignment.

        Args:
            policy_id: Provisioning policy ID

        Returns:
            Entra group ID
        """
        group_name = f"HayMaker-CloudPC-{self.run_id[:8]}"

        try:
            # Search for existing group
            groups = await self.graph_client.groups.get(
                request_configuration={
                    "query_parameters": {"filter": f"displayName eq '{group_name}'"}
                }
            )

            if groups.value:
                logger.info(f"Using existing assignment group: {group_name}")
                return groups.value[0].id

            # Create new group
            group_data = {
                "displayName": group_name,
                "mailNickname": f"haymaker-cloudpc-{self.run_id[:8]}",
                "description": f"Cloud PC assignment group for HayMaker run {self.run_id}",
                "mailEnabled": False,
                "securityEnabled": True,
                "groupTypes": [],
            }

            group = await self.graph_client.groups.post(body=group_data)
            logger.info(f"Created assignment group: {group_name} ({group.id})")
            return group.id

        except Exception as e:
            logger.error(f"Failed to get/create assignment group: {e}")
            raise

    async def _add_user_to_group(
        self, worker: WorkerIdentity, group_id: str
    ) -> None:
        """Add a user to an Entra group.

        Args:
            worker: Worker identity
            group_id: Entra group ID
        """
        try:
            # Check if user already in group
            members = await self.graph_client.groups.by_group_id(
                group_id
            ).members.get()

            member_ids = [m.id for m in (members.value or [])]
            if worker.entra_object_id in member_ids:
                logger.debug(
                    f"User {worker.worker_id} already in group {group_id}"
                )
                return

            # Add user to group
            reference_data = {
                "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{worker.entra_object_id}"
            }

            await self.graph_client.groups.by_group_id(group_id).members.ref.post(
                body=reference_data
            )

            logger.info(
                f"Added user {worker.worker_id} to Cloud PC assignment group"
            )

        except Exception as e:
            logger.error(
                f"Failed to add user {worker.worker_id} to group {group_id}: {e}"
            )
            raise

    async def _assign_group_to_policy(
        self, policy_id: str, group_id: str
    ) -> None:
        """Assign an Entra group to a Cloud PC provisioning policy.

        Args:
            policy_id: Provisioning policy ID
            group_id: Entra group ID
        """
        try:
            # Check existing assignments
            assignments = await self.graph_client.device_management.virtual_endpoint.provisioning_policies.by_cloud_pc_provisioning_policy_id(
                policy_id
            ).assignments.get()

            # Check if group already assigned
            assigned_group_ids = [
                a.target.group_id for a in (assignments.value or []) if hasattr(a.target, "group_id")
            ]

            if group_id in assigned_group_ids:
                logger.debug(f"Group {group_id} already assigned to policy {policy_id}")
                return

            # Create assignment
            assignment_data = {
                "target": {
                    "@odata.type": "#microsoft.graph.groupAssignmentTarget",
                    "groupId": group_id,
                }
            }

            await self.graph_client.device_management.virtual_endpoint.provisioning_policies.by_cloud_pc_provisioning_policy_id(
                policy_id
            ).assignments.post(
                body=assignment_data
            )

            logger.info(f"Assigned group {group_id} to policy {policy_id}")

        except Exception as e:
            logger.error(f"Failed to assign group {group_id} to policy {policy_id}: {e}")
            raise

    async def _handle_permission_fallback(
        self,
        worker: WorkerIdentity,
        policy_id: str,
        error: Exception,
    ) -> str:
        """Handle graceful degradation when CloudPC permissions missing.

        When CloudPC.ReadWrite.All permission is not available, this method
        provides mock provisioning to allow framework testing to continue.

        Args:
            worker: Worker identity
            policy_id: Provisioning policy ID (unused in fallback)
            error: The permission error that triggered fallback

        Returns:
            Mock Cloud PC ID for tracking
        """
        logger.warning(
            f"CloudPC.ReadWrite.All permission not available: {error}. "
            f"Using mock provisioning for {worker.worker_id}"
        )

        mock_id = f"mock-cloudpc-{worker.worker_id}"
        self._track_permission_fallback("CloudPC.ReadWrite.All", worker.worker_id)

        return mock_id

    def _track_permission_fallback(self, permission: str, resource_id: str) -> None:
        """Track permission fallback for audit.

        Args:
            permission: Permission that was missing
            resource_id: Resource ID that triggered fallback
        """
        self._permission_fallbacks.append({
            "permission": permission,
            "resource_id": resource_id,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    def get_permission_status(self) -> dict[str, Any]:
        """Get permission fallback status report.

        Returns:
            Dictionary with:
            - has_cloudpc_permission: True if no fallbacks occurred
            - fallback_count: Number of permission fallbacks
            - fallbacks: List of fallback events
        """
        return {
            "has_cloudpc_permission": len(self._permission_fallbacks) == 0,
            "fallback_count": len(self._permission_fallbacks),
            "fallbacks": self._permission_fallbacks.copy(),
        }
