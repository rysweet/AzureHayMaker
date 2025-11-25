"""Entra group management for Knowledge Worker Activity Framework.

Provides security group and M365 unified group management for
organizing knowledge workers into teams.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EntraGroupManager:
    """Manages Entra ID security groups for knowledge worker teams.

    Handles creation, membership, and deletion of security groups
    used to organize workers and control access.

    Naming Convention:
        - Security group: kw-{run_id[:8]}-{dept}-team-{n}
        - All workers group: kw-{run_id[:8]}-all-workers
        - M365 group: KW-{RunId[:8]}-{Dept}-Team{N}

    Attributes:
        graph_client: Microsoft Graph API client
        run_id: HayMaker run ID for this deployment
    """

    SECURITY_GROUP_PATTERN = "kw-{run_id}-{dept}-team-{team_num}"
    ALL_WORKERS_GROUP_PATTERN = "kw-{run_id}-all-workers"
    M365_GROUP_PATTERN = "KW-{run_id}-{dept}-Team{team_num}"

    def __init__(
        self,
        graph_client: Any,
        run_id: str,
    ):
        """Initialize EntraGroupManager.

        Args:
            graph_client: Microsoft Graph API client
            run_id: HayMaker run ID for resource tagging
        """
        self.graph_client = graph_client
        self.run_id = run_id

    async def create_security_group(
        self,
        department: str,
        team_num: int,
        description: str = "",
    ) -> str:
        """Create a security group for a team.

        Args:
            department: Department name
            team_num: Team number within department
            description: Optional group description

        Returns:
            Group ID of created security group
        """
        group_name = self.SECURITY_GROUP_PATTERN.format(
            run_id=self.run_id[:8],
            dept=department.lower(),
            team_num=team_num,
        )

        try:
            group_data = {
                "displayName": group_name,
                "description": description or f"HayMaker Knowledge Worker Team - {department} #{team_num}",
                "mailEnabled": False,
                "mailNickname": group_name.replace("-", ""),
                "securityEnabled": True,
            }

            result = await self.graph_client.groups.post(body=group_data)

            logger.info(f"Created security group: {group_name} ({result.id})")
            return result.id

        except Exception as e:
            logger.error(f"Failed to create security group {group_name}: {e}")
            raise

    async def create_all_workers_group(
        self,
        description: str = "",
    ) -> str:
        """Create the all-workers security group.

        This group contains all knowledge workers for the run
        and is used for transport rules.

        Args:
            description: Optional group description

        Returns:
            Group ID of created security group
        """
        group_name = self.ALL_WORKERS_GROUP_PATTERN.format(
            run_id=self.run_id[:8],
        )

        try:
            group_data = {
                "displayName": group_name,
                "description": description or f"All HayMaker Knowledge Workers - Run {self.run_id[:8]}",
                "mailEnabled": False,
                "mailNickname": group_name.replace("-", ""),
                "securityEnabled": True,
            }

            result = await self.graph_client.groups.post(body=group_data)

            logger.info(f"Created all-workers group: {group_name} ({result.id})")
            return result.id

        except Exception as e:
            logger.error(f"Failed to create all-workers group: {e}")
            raise

    async def create_m365_group(
        self,
        department: str,
        team_num: int,
        description: str = "",
        owners: list[str] | None = None,
    ) -> str:
        """Create an M365 unified group for a team.

        This creates a group with Teams-enabled capabilities
        including SharePoint site and shared mailbox.

        Args:
            department: Department name
            team_num: Team number within department
            description: Optional group description
            owners: List of owner user IDs

        Returns:
            Group ID of created M365 group
        """
        group_name = self.M365_GROUP_PATTERN.format(
            run_id=self.run_id[:8].upper(),
            dept=department.capitalize(),
            team_num=team_num,
        )

        try:
            group_data = {
                "displayName": group_name,
                "description": description or f"HayMaker Knowledge Worker Team - {department} #{team_num}",
                "mailEnabled": True,
                "mailNickname": group_name.replace("-", "").lower(),
                "securityEnabled": True,
                "groupTypes": ["Unified"],
                "visibility": "Private",
            }

            if owners:
                group_data["owners@odata.bind"] = [
                    f"https://graph.microsoft.com/v1.0/users/{uid}"
                    for uid in owners
                ]

            result = await self.graph_client.groups.post(body=group_data)

            logger.info(f"Created M365 group: {group_name} ({result.id})")
            return result.id

        except Exception as e:
            logger.error(f"Failed to create M365 group {group_name}: {e}")
            raise

    async def add_member(
        self,
        group_id: str,
        user_id: str,
    ) -> bool:
        """Add a user to a group.

        Args:
            group_id: Entra group ID
            user_id: Entra user ID to add

        Returns:
            True if added successfully
        """
        try:
            await self.graph_client.groups.by_group_id(
                group_id
            ).members.ref.post(
                body={
                    "@odata.id": f"https://graph.microsoft.com/v1.0/users/{user_id}"
                }
            )

            logger.debug(f"Added member {user_id} to group {group_id}")
            return True

        except Exception as e:
            # Check if member already exists
            if "already exist" in str(e).lower():
                logger.debug(f"Member {user_id} already in group {group_id}")
                return True
            logger.error(f"Failed to add member {user_id} to group {group_id}: {e}")
            return False

    async def add_members_batch(
        self,
        group_id: str,
        user_ids: list[str],
    ) -> int:
        """Add multiple users to a group.

        Args:
            group_id: Entra group ID
            user_ids: List of user IDs to add

        Returns:
            Number of successfully added members
        """
        success_count = 0
        for user_id in user_ids:
            if await self.add_member(group_id, user_id):
                success_count += 1
        return success_count

    async def remove_member(
        self,
        group_id: str,
        user_id: str,
    ) -> bool:
        """Remove a user from a group.

        Args:
            group_id: Entra group ID
            user_id: Entra user ID to remove

        Returns:
            True if removed successfully
        """
        try:
            await self.graph_client.groups.by_group_id(
                group_id
            ).members.by_directory_object_id(
                user_id
            ).ref.delete()

            logger.debug(f"Removed member {user_id} from group {group_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove member {user_id} from group {group_id}: {e}")
            return False

    async def list_members(
        self,
        group_id: str,
    ) -> list[str]:
        """List all members of a group.

        Args:
            group_id: Entra group ID

        Returns:
            List of member user IDs
        """
        try:
            members = await self.graph_client.groups.by_group_id(
                group_id
            ).members.get(
                request_configuration={
                    "query_parameters": {"select": "id"}
                }
            )

            return [m.id for m in (members.value or [])]

        except Exception as e:
            logger.error(f"Failed to list members of group {group_id}: {e}")
            return []

    async def delete_group(
        self,
        group_id: str,
    ) -> bool:
        """Delete a group.

        Args:
            group_id: Entra group ID

        Returns:
            True if deleted successfully
        """
        try:
            await self.graph_client.groups.by_group_id(group_id).delete()
            logger.info(f"Deleted group: {group_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete group {group_id}: {e}")
            return False

    async def list_groups_for_run(
        self,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all groups for a run.

        Args:
            run_id: Run ID to filter by (uses instance run_id if not specified)

        Returns:
            List of group info dictionaries
        """
        target_run_id = run_id or self.run_id

        try:
            # Security groups
            security_filter = f"startswith(displayName, 'kw-{target_run_id[:8]}')"
            security_groups = await self.graph_client.groups.get(
                request_configuration={
                    "query_parameters": {
                        "filter": security_filter,
                        "select": "id,displayName,description,securityEnabled,mailEnabled",
                    }
                }
            )

            # M365 groups
            m365_filter = f"startswith(displayName, 'KW-{target_run_id[:8].upper()}')"
            m365_groups = await self.graph_client.groups.get(
                request_configuration={
                    "query_parameters": {
                        "filter": m365_filter,
                        "select": "id,displayName,description,securityEnabled,mailEnabled,groupTypes",
                    }
                }
            )

            groups = []
            for g in (security_groups.value or []):
                groups.append({
                    "id": g.id,
                    "display_name": g.display_name,
                    "description": g.description,
                    "type": "security",
                })
            for g in (m365_groups.value or []):
                groups.append({
                    "id": g.id,
                    "display_name": g.display_name,
                    "description": g.description,
                    "type": "m365",
                })

            return groups

        except Exception as e:
            logger.error(f"Failed to list groups for run {target_run_id}: {e}")
            return []
