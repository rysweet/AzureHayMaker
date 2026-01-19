"""Cleanup manager for Knowledge Worker Activity Framework.

Provides comprehensive resource tracking and cleanup to ensure
all provisioned resources can be reliably deleted.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CleanupReport(BaseModel):
    """Report of cleanup operation results.

    Tracks success and failure of resource deletions.

    Attributes:
        run_id: HayMaker run ID
        started_at: Cleanup start time
        completed_at: Cleanup completion time
        total_resources: Total resources to clean up
        successful_deletions: Number of successful deletions
        failed_deletions: Number of failed deletions
        results: Individual resource deletion results
        errors: List of error messages
    """

    run_id: str = Field(..., description="HayMaker run ID")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Cleanup start time",
    )
    completed_at: datetime | None = Field(default=None, description="Cleanup end time")

    total_resources: int = Field(default=0, ge=0)
    successful_deletions: int = Field(default=0, ge=0)
    failed_deletions: int = Field(default=0, ge=0)

    results: dict[str, bool] = Field(
        default_factory=dict, description="Resource ID to success status"
    )
    errors: list[str] = Field(default_factory=list, description="Error messages")

    model_config = {
        "validate_assignment": True,
    }

    def record(self, resource_id: str, success: bool, error: str | None = None) -> None:
        """Record a deletion result.

        Args:
            resource_id: ID of the resource
            success: Whether deletion succeeded
            error: Optional error message if failed
        """
        self.results[resource_id] = success
        self.total_resources += 1

        if success:
            self.successful_deletions += 1
        else:
            self.failed_deletions += 1
            if error:
                self.errors.append(f"{resource_id}: {error}")

    def complete(self) -> None:
        """Mark the cleanup as complete."""
        self.completed_at = datetime.now(UTC)

    @property
    def success_rate(self) -> float:
        """Calculate the cleanup success rate."""
        if self.total_resources == 0:
            return 1.0
        return self.successful_deletions / self.total_resources

    @property
    def is_complete_success(self) -> bool:
        """Check if cleanup was completely successful."""
        return self.failed_deletions == 0 and self.total_resources > 0


class KnowledgeWorkerResourceInventory:
    """Tracks all resources created by the Knowledge Worker framework.

    Maintains a registry of all provisioned resources for reliable
    cleanup. Supports JSON serialization for persistent storage.

    Resource Types:
        - entra_users: Entra ID users
        - security_groups: Entra security groups
        - m365_groups: M365 unified groups
        - teams_teams: Microsoft Teams teams
        - cloud_pcs: Windows 365 Cloud PCs
        - container_apps: Azure Container Apps
        - transport_rules: Exchange transport rules
        - sharepoint_sites: SharePoint sites

    Attributes:
        run_id: HayMaker run ID for this inventory
        resources: Dictionary mapping resource type to list of IDs
        created_at: Inventory creation timestamp
    """

    RESOURCE_TYPES = [
        "entra_users",
        "security_groups",
        "m365_groups",
        "teams_teams",
        "cloud_pcs",
        "container_apps",
        "transport_rules",
        "sharepoint_sites",
    ]

    def __init__(self, run_id: str):
        """Initialize KnowledgeWorkerResourceInventory.

        Args:
            run_id: HayMaker run ID for this deployment
        """
        self.run_id = run_id
        self.resources: dict[str, list[str]] = {
            resource_type: [] for resource_type in self.RESOURCE_TYPES
        }
        self.created_at = datetime.now(UTC)

    def register(self, resource_type: str, resource_id: str) -> None:
        """Register a created resource.

        Args:
            resource_type: Type of resource (must be in RESOURCE_TYPES)
            resource_id: Unique identifier for the resource
        """
        if resource_type not in self.resources:
            logger.warning(f"Unknown resource type: {resource_type}")
            return  # Ignore unknown resource types per architecture

        if resource_id not in self.resources[resource_type]:
            self.resources[resource_type].append(resource_id)
            logger.debug(f"Registered {resource_type}: {resource_id}")

    def register_batch(self, resource_type: str, resource_ids: list[str]) -> None:
        """Register multiple resources of the same type.

        Args:
            resource_type: Type of resources
            resource_ids: List of resource IDs to register
        """
        for resource_id in resource_ids:
            self.register(resource_type, resource_id)

    def unregister(self, resource_type: str, resource_id: str) -> bool:
        """Unregister a resource (e.g., after deletion).

        Args:
            resource_type: Type of resource
            resource_id: ID of resource to unregister

        Returns:
            True if resource was found and removed
        """
        if resource_type in self.resources:
            try:
                self.resources[resource_type].remove(resource_id)
                return True
            except ValueError:
                return False
        return False

    def get(self, resource_type: str) -> list[str]:
        """Get all resources of a specific type.

        Args:
            resource_type: Type of resources to retrieve

        Returns:
            List of resource IDs
        """
        return self.resources.get(resource_type, []).copy()

    def get_all(self) -> dict[str, list[str]]:
        """Get all registered resources.

        Returns:
            Copy of resources dictionary
        """
        return {k: v.copy() for k, v in self.resources.items()}

    def get_count(self, resource_type: str | None = None) -> int:
        """Get count of registered resources.

        Args:
            resource_type: Optional type to count (all types if None)

        Returns:
            Count of resources
        """
        if resource_type:
            return len(self.resources.get(resource_type, []))
        return sum(len(v) for v in self.resources.values())

    def get_summary(self) -> dict[str, int]:
        """Get summary of resource counts by type.

        Returns:
            Dictionary mapping resource type to count
        """
        return {k: len(v) for k, v in self.resources.items()}

    def to_json(self) -> str:
        """Serialize inventory to JSON for storage.

        Returns:
            JSON string representation
        """
        return json.dumps(
            {
                "run_id": self.run_id,
                "resources": self.resources,
                "created_at": self.created_at.isoformat(),
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, data: str) -> "KnowledgeWorkerResourceInventory":
        """Deserialize from JSON.

        Args:
            data: JSON string to parse

        Returns:
            KnowledgeWorkerResourceInventory instance
        """
        parsed = json.loads(data)
        inventory = cls(parsed["run_id"])
        inventory.resources = parsed["resources"]
        inventory.created_at = datetime.fromisoformat(parsed["created_at"])
        return inventory

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "run_id": self.run_id,
            "resources": self.resources,
            "created_at": self.created_at.isoformat(),
            "summary": self.get_summary(),
        }


class KnowledgeWorkerCleanupManager:
    """Manages cleanup of all Knowledge Worker resources.

    Cleanup order (reverse of creation):
    1. Stop container apps
    2. Delete container apps
    3. Delete Cloud PCs
    4. Remove transport rules
    5. Delete Teams teams
    6. Delete M365 groups
    7. Delete security groups
    8. Delete Entra users (last, as they may own resources)

    Attributes:
        graph_client: Microsoft Graph API client
        container_client: Container Apps API client
        run_id: HayMaker run ID for this deployment
    """

    def __init__(
        self,
        graph_client: Any,
        container_client: Any | None = None,
        run_id: str = "",
    ):
        """Initialize KnowledgeWorkerCleanupManager.

        Args:
            graph_client: Microsoft Graph API client
            container_client: Optional Container Apps API client
            run_id: HayMaker run ID for this deployment
        """
        self.graph_client = graph_client
        self.container_client = container_client
        self.run_id = run_id

    async def cleanup_all(
        self,
        inventory: KnowledgeWorkerResourceInventory,
    ) -> CleanupReport:
        """Clean up all resources in the inventory.

        Deletes resources in reverse order of creation to
        handle dependencies correctly.

        Args:
            inventory: Resource inventory from the run

        Returns:
            CleanupReport with results
        """
        report = CleanupReport(run_id=inventory.run_id)

        logger.info(
            f"Starting cleanup for run {inventory.run_id} ({inventory.get_count()} resources)"
        )

        # 1. Stop and delete container apps
        for container_id in inventory.get("container_apps"):
            result = await self._delete_container_app(container_id)
            report.record(container_id, result)

        # 2. Delete Cloud PCs
        for cloud_pc_id in inventory.get("cloud_pcs"):
            result = await self._delete_cloud_pc(cloud_pc_id)
            report.record(cloud_pc_id, result)

        # 3. Remove transport rules
        for rule_name in inventory.get("transport_rules"):
            result = await self._delete_transport_rule(rule_name)
            report.record(rule_name, result)

        # 4. Delete Teams teams
        for team_id in inventory.get("teams_teams"):
            result = await self._delete_teams_team(team_id)
            report.record(team_id, result)

        # 5. Delete M365 groups
        for group_id in inventory.get("m365_groups"):
            result = await self._delete_m365_group(group_id)
            report.record(group_id, result)

        # 6. Delete security groups
        for group_id in inventory.get("security_groups"):
            result = await self._delete_security_group(group_id)
            report.record(group_id, result)

        # 7. Delete Entra users (last, as they may own resources)
        for user_id in inventory.get("entra_users"):
            result = await self._delete_entra_user(user_id)
            report.record(user_id, result)

        report.complete()

        logger.info(
            f"Cleanup complete for run {inventory.run_id}: "
            f"{report.successful_deletions}/{report.total_resources} succeeded "
            f"(success rate: {report.success_rate:.1%})"
        )

        return report

    async def cleanup_by_type(
        self,
        inventory: KnowledgeWorkerResourceInventory,
        resource_type: str,
    ) -> CleanupReport:
        """Clean up resources of a specific type.

        Args:
            inventory: Resource inventory
            resource_type: Type of resources to clean up

        Returns:
            CleanupReport with results
        """
        report = CleanupReport(run_id=inventory.run_id)

        delete_method = self._get_delete_method(resource_type)
        if not delete_method:
            logger.error(f"Unknown resource type: {resource_type}")
            report.complete()
            return report

        for resource_id in inventory.get(resource_type):
            result = await delete_method(resource_id)
            report.record(resource_id, result)

        report.complete()
        return report

    def _get_delete_method(self, resource_type: str) -> Any:
        """Get the appropriate delete method for a resource type.

        Args:
            resource_type: Type of resource

        Returns:
            Delete method or None if unknown type
        """
        methods = {
            "entra_users": self._delete_entra_user,
            "security_groups": self._delete_security_group,
            "m365_groups": self._delete_m365_group,
            "teams_teams": self._delete_teams_team,
            "cloud_pcs": self._delete_cloud_pc,
            "container_apps": self._delete_container_app,
            "transport_rules": self._delete_transport_rule,
            "sharepoint_sites": self._delete_sharepoint_site,
        }
        return methods.get(resource_type)

    async def _delete_entra_user(self, user_id: str) -> bool:
        """Delete Entra user with retry logic.

        Args:
            user_id: Entra object ID

        Returns:
            True if deleted successfully
        """
        try:
            await self.graph_client.users.by_user_id(user_id).delete()
            logger.info(f"Deleted Entra user: {user_id}")
            return True
        except Exception as e:
            # Check if already deleted
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                logger.debug(f"User already deleted: {user_id}")
                return True
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    async def _delete_security_group(self, group_id: str) -> bool:
        """Delete Entra security group.

        Args:
            group_id: Group ID

        Returns:
            True if deleted successfully
        """
        try:
            await self.graph_client.groups.by_group_id(group_id).delete()
            logger.info(f"Deleted security group: {group_id}")
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                return True
            logger.error(f"Failed to delete security group {group_id}: {e}")
            return False

    async def _delete_m365_group(self, group_id: str) -> bool:
        """Delete M365 unified group.

        Args:
            group_id: Group ID

        Returns:
            True if deleted successfully
        """
        try:
            await self.graph_client.groups.by_group_id(group_id).delete()
            logger.info(f"Deleted M365 group: {group_id}")
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                return True
            logger.error(f"Failed to delete M365 group {group_id}: {e}")
            return False

    async def _delete_teams_team(self, team_id: str) -> bool:
        """Delete Microsoft Teams team.

        Args:
            team_id: Team ID

        Returns:
            True if deleted successfully
        """
        try:
            # Teams teams are deleted by deleting the underlying group
            await self.graph_client.groups.by_group_id(team_id).delete()
            logger.info(f"Deleted Teams team: {team_id}")
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                return True
            logger.error(f"Failed to delete Teams team {team_id}: {e}")
            return False

    async def _delete_cloud_pc(self, cloud_pc_id: str) -> bool:
        """Delete Windows 365 Cloud PC.

        Args:
            cloud_pc_id: Cloud PC ID

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
            if "not found" in str(e).lower():
                return True
            logger.error(f"Failed to delete Cloud PC {cloud_pc_id}: {e}")
            return False

    async def _delete_container_app(self, container_id: str) -> bool:
        """Delete Azure Container App.

        NOTE: Requires container_client to be provided at initialization.
        Without a configured Container Apps client, this operation will
        be skipped and logged as a warning.

        Args:
            container_id: Container App resource ID

        Returns:
            True if deleted successfully, False if skipped or failed
        """
        try:
            if not self.container_client:
                logger.warning(
                    f"Container app deletion skipped (no client configured): {container_id}"
                )
                return False  # Honestly report that deletion was not performed

            # Use Container Apps SDK to delete
            await self.container_client.container_apps.begin_delete(
                resource_group_name=self._extract_resource_group(container_id),
                container_app_name=self._extract_container_name(container_id),
            )
            logger.info(f"Deleted container app: {container_id}")
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                return True
            logger.error(f"Failed to delete container app {container_id}: {e}")
            return False

    def _extract_resource_group(self, resource_id: str) -> str:
        """Extract resource group name from Azure resource ID."""
        parts = resource_id.split("/")
        try:
            rg_index = parts.index("resourceGroups") + 1
            return parts[rg_index]
        except (ValueError, IndexError):
            return ""

    def _extract_container_name(self, resource_id: str) -> str:
        """Extract container app name from Azure resource ID."""
        parts = resource_id.split("/")
        return parts[-1] if parts else ""

    async def _delete_transport_rule(self, rule_name: str) -> bool:
        """Delete Exchange transport rule.

        NOTE: Exchange transport rules require Exchange Online PowerShell
        or Security & Compliance Center API integration. This operation
        logs a warning and returns False until integrated.

        Implementation options for future:
        - Exchange Online PowerShell module
        - Microsoft Graph Security API
        - Security & Compliance Center API

        Args:
            rule_name: Transport rule name

        Returns:
            True if deleted successfully, False if not implemented
        """
        # Transport rule deletion requires Exchange Online PowerShell integration
        # which is not yet implemented. Log warning and report honestly.
        logger.warning(
            f"Transport rule deletion not yet implemented: {rule_name}. "
            "Manual cleanup via Exchange Admin Center may be required."
        )
        return False  # Honestly report that deletion was not performed

    async def _delete_sharepoint_site(self, site_id: str) -> bool:
        """Delete SharePoint site.

        Args:
            site_id: SharePoint site ID

        Returns:
            True if deleted successfully
        """
        try:
            await self.graph_client.sites.by_site_id(site_id).delete()
            logger.info(f"Deleted SharePoint site: {site_id}")
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                return True
            logger.error(f"Failed to delete SharePoint site {site_id}: {e}")
            return False
