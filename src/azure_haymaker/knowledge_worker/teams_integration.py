"""Teams integration module for Knowledge Worker Activity Framework.

Provides team creation, member management, channel setup, and messaging
via Microsoft Graph API. Integrates with orchestrator for Teams deployment
during setup phase.

Key Responsibilities:
- Create Teams teams from M365 unified groups
- Add KW users as team members with role assignment
- Create standard channels (General, Projects)
- Post welcome messages to channels
- Maintain team metadata in Team model
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TeamsIntegrationError(Exception):
    """Raised when Teams integration operations fail."""

    pass


class TeamsIntegration:
    """Teams integration manager for knowledge worker teams.

    Handles creation and configuration of Microsoft Teams teams for
    knowledge worker collaboration, including member management,
    channel setup, and initial messaging.

    Naming Convention:
        Teams team name format: KW-{RunId[:8]}-{Dept}-Team{N}
        (matches M365 group naming from EntraGroupManager)

    Attributes:
        graph_client: Microsoft Graph API client
        run_id: HayMaker run ID for resource tagging
        default_channels: Default channels to create for each team
    """

    # Default channels created for each team
    DEFAULT_CHANNELS = ["General", "Projects"]

    # Default welcome message
    WELCOME_MESSAGE_TEMPLATE = """
    Welcome to the {team_name} team!

    This team has been set up for the Knowledge Worker Activity Framework
    and is ready for collaboration. Use the channels below to organize
    your work:

    - **General**: General team announcements and discussions
    - **Projects**: Project-specific discussions and updates

    Looking forward to productive collaboration!
    """

    def __init__(
        self,
        graph_client: Any,
        run_id: str,
    ):
        """Initialize TeamsIntegration.

        Args:
            graph_client: Microsoft Graph API client
            run_id: HayMaker run ID for resource tagging

        Raises:
            ValueError: If required parameters are missing
        """
        if not graph_client:
            raise ValueError("graph_client is required")
        if not run_id:
            raise ValueError("run_id is required")

        self.graph_client = graph_client
        self.run_id = run_id

    def _build_team_name(self, department: str, team_num: int) -> str:
        """Build Teams team name from department and number.

        Args:
            department: Department name
            team_num: Team number within department

        Returns:
            Formatted team name
        """
        # Match M365 group naming convention
        return f"KW-{self.run_id[:8].upper()}-{department.capitalize()}-Team{team_num}"

    async def create_team_from_group(
        self,
        m365_group_id: str,
        team_name: str,
        department: str,
        team_num: int,
    ) -> str:
        """Create a Teams team from an M365 unified group.

        The team is created as a group team, automatically getting
        a SharePoint site, shared mailbox, and team chat capabilities.

        Args:
            m365_group_id: ID of existing M365 unified group
            team_name: Display name for the team
            department: Department name (for logging)
            team_num: Team number within department (for logging)

        Returns:
            Teams team ID of created team

        Raises:
            TeamsIntegrationError: If team creation fails
        """
        try:
            # Create team from group
            team_data = {
                "memberSettings": {
                    "allowCreateUpdateChannels": True,
                    "allowDeleteChannels": True,
                },
                "messagingSettings": {
                    "allowUserEditMessages": True,
                    "allowUserDeleteMessages": True,
                },
                "funSettings": {
                    "allowGiphy": True,
                    "giphyContentRating": "strict",
                },
                "discoverySettings": {
                    "showInTeamsSearchAndSuggestions": True,
                },
            }

            result = await self.graph_client.groups.by_group_id(m365_group_id).team.put(
                body=team_data
            )

            team_id = result.id if result else None

            if not team_id:
                raise TeamsIntegrationError(
                    f"Failed to extract team ID from response for {team_name}"
                )

            logger.info(
                f"Created Teams team: {team_name} ({team_id}) for {department} team {team_num}"
            )
            return team_id

        except Exception as e:
            logger.error(f"Failed to create Teams team {team_name} from group {m365_group_id}: {e}")
            raise TeamsIntegrationError(f"Failed to create Teams team: {str(e)}") from e

    async def add_team_members(
        self,
        team_id: str,
        member_configs: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Add members to a team with specified roles.

        Args:
            team_id: Teams team ID
            member_configs: List of dicts with 'user_id' and 'role' keys
                           Role should be 'owner' or 'member'

        Returns:
            Dictionary with success/failure counts

        Raises:
            TeamsIntegrationError: If all members fail to be added
        """
        if not member_configs:
            return {"success": 0, "failed": 0}

        results = {"success": 0, "failed": 0}

        for config in member_configs:
            user_id = config.get("user_id")
            role = config.get("role", "member")

            if not user_id:
                logger.warning("Skipping member config without user_id")
                results["failed"] += 1
                continue

            try:
                await self._add_team_member(team_id, user_id, role)
                results["success"] += 1
            except Exception as e:
                logger.warning(f"Failed to add member {user_id} to team {team_id}: {e}")
                results["failed"] += 1

        if results["success"] == 0 and results["failed"] > 0:
            raise TeamsIntegrationError(f"Failed to add any members to team {team_id}")

        logger.info(
            f"Added {results['success']} members to team {team_id} ({results['failed']} failed)"
        )

        return results

    async def _add_team_member(
        self,
        team_id: str,
        user_id: str,
        role: str = "member",
    ) -> None:
        """Add a single member to a team.

        Args:
            team_id: Teams team ID
            user_id: Entra user ID to add
            role: Role for the user ('owner' or 'member')

        Raises:
            Exception: If member cannot be added
        """
        valid_roles = {"owner", "member"}
        if role not in valid_roles:
            role = "member"

        member_data = {
            "@odata.type": "#microsoft.graph.aadUserConversationMember",
            "roles": [role],
            "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{user_id}",
        }

        await self.graph_client.teams.by_team_id(team_id).members.post(body=member_data)

        logger.debug(f"Added member {user_id} to team {team_id} with role {role}")

    async def create_standard_channels(
        self,
        team_id: str,
        channels: list[str] | None = None,
    ) -> dict[str, str]:
        """Create standard channels in a team.

        Note: The 'General' channel is created automatically when the team
        is created, so this method focuses on additional channels.

        Args:
            team_id: Teams team ID
            channels: List of channel names to create
                     (defaults to DEFAULT_CHANNELS minus General)

        Returns:
            Dictionary mapping channel names to channel IDs

        Raises:
            TeamsIntegrationError: If channel creation fails
        """
        if channels is None:
            # Skip 'General' as it's created automatically
            channels = [ch for ch in self.DEFAULT_CHANNELS if ch != "General"]

        channel_ids = {}

        for channel_name in channels:
            try:
                channel_id = await self._create_channel(team_id, channel_name)
                channel_ids[channel_name] = channel_id
                logger.info(f"Created channel {channel_name} ({channel_id}) in team {team_id}")
            except Exception as e:
                logger.warning(f"Failed to create channel {channel_name} in team {team_id}: {e}")

        return channel_ids

    async def _create_channel(
        self,
        team_id: str,
        channel_name: str,
        description: str = "",
    ) -> str:
        """Create a single channel in a team.

        Args:
            team_id: Teams team ID
            channel_name: Display name for the channel
            description: Optional channel description

        Returns:
            Channel ID

        Raises:
            Exception: If channel cannot be created
        """
        channel_data = {
            "displayName": channel_name,
            "description": description or f"Channel for {channel_name}",
        }

        result = await self.graph_client.teams.by_team_id(team_id).channels.post(body=channel_data)

        if not result or not result.id:
            raise TeamsIntegrationError(f"Failed to extract channel ID for {channel_name}")

        return result.id

    async def post_welcome_message(
        self,
        team_id: str,
        channel_name: str = "General",
        custom_message: str = "",
    ) -> str | None:
        """Post a welcome message to a channel.

        Args:
            team_id: Teams team ID
            channel_name: Channel to post to (default: General)
            custom_message: Optional custom message (uses template if not provided)

        Returns:
            Message ID if posted successfully, None if channel not found

        Raises:
            TeamsIntegrationError: If posting fails
        """
        try:
            # Get channel ID by name
            channel_id = await self._get_channel_id_by_name(team_id, channel_name)

            if not channel_id:
                logger.warning(f"Channel {channel_name} not found in team {team_id}")
                return None

            # Build message content
            if custom_message:
                message_content = custom_message
            else:
                # Get team name from team ID for personalization
                team_info = await self._get_team_info(team_id)
                team_display_name = team_info.get("display_name", "Team") if team_info else "Team"
                message_content = self.WELCOME_MESSAGE_TEMPLATE.format(team_name=team_display_name)

            message_body = {
                "body": {
                    "contentType": "html",
                    "content": message_content,
                }
            }

            result = (
                await self.graph_client.teams.by_team_id(team_id)
                .channels.by_channel_id(channel_id)
                .messages.post(body=message_body)
            )

            message_id = result.id if result else None

            if message_id:
                logger.info(f"Posted welcome message to {channel_name} in team {team_id}")

            return message_id

        except Exception as e:
            logger.error(f"Failed to post welcome message to {team_id}: {e}")
            raise TeamsIntegrationError(f"Failed to post message: {str(e)}") from e

    async def _get_channel_id_by_name(
        self,
        team_id: str,
        channel_name: str,
    ) -> str | None:
        """Get channel ID by name.

        Args:
            team_id: Teams team ID
            channel_name: Display name of the channel

        Returns:
            Channel ID if found, None otherwise
        """
        try:
            channels = await self.graph_client.teams.by_team_id(team_id).channels.get(
                request_configuration={
                    "query_parameters": {
                        "filter": f"displayName eq '{channel_name}'",
                        "select": "id,displayName",
                    }
                }
            )

            if channels and channels.value:
                return channels.value[0].id

            return None

        except Exception as e:
            logger.debug(f"Failed to get channel {channel_name} in team {team_id}: {e}")
            return None

    async def _get_team_info(self, team_id: str) -> dict[str, Any] | None:
        """Get basic team information.

        Args:
            team_id: Teams team ID

        Returns:
            Dictionary with team info or None if not found
        """
        try:
            team = await self.graph_client.teams.by_team_id(team_id).get(
                request_configuration={
                    "query_parameters": {
                        "select": "id,displayName,description",
                    }
                }
            )

            if team:
                return {
                    "id": team.id,
                    "display_name": team.display_name,
                    "description": team.description,
                }

            return None

        except Exception as e:
            logger.debug(f"Failed to get team info for {team_id}: {e}")
            return None

    async def setup_team(
        self,
        m365_group_id: str,
        department: str,
        team_num: int,
        member_configs: list[dict[str, Any]],
        post_welcome_message: bool = True,
    ) -> dict[str, Any]:
        """Complete team setup: create team, add members, create channels, post message.

        This is the primary orchestration method that combines all steps
        into a single operation.

        Args:
            m365_group_id: ID of existing M365 unified group
            department: Department name
            team_num: Team number within department
            member_configs: List of member configs with user_id and role
            post_welcome_message: Whether to post welcome message (default: True)

        Returns:
            Dictionary with setup results including team_id, channels, and members

        Raises:
            TeamsIntegrationError: If any critical step fails
        """
        team_name = self._build_team_name(department, team_num)

        try:
            # Step 1: Create team
            logger.info(f"Setting up Teams team: {team_name}")
            team_id = await self.create_team_from_group(
                m365_group_id=m365_group_id,
                team_name=team_name,
                department=department,
                team_num=team_num,
            )

            # Step 2: Add members
            logger.info(f"Adding {len(member_configs)} members to team {team_id}")
            member_results = await self.add_team_members(team_id, member_configs)

            # Step 3: Create channels
            logger.info(f"Creating channels in team {team_id}")
            channel_ids = await self.create_standard_channels(team_id)

            # Step 4: Post welcome message
            message_id = None
            if post_welcome_message:
                logger.info(f"Posting welcome message to team {team_id}")
                message_id = await self.post_welcome_message(team_id)

            result = {
                "team_id": team_id,
                "team_name": team_name,
                "m365_group_id": m365_group_id,
                "members": member_results,
                "channels": channel_ids,
                "welcome_message_id": message_id,
                "status": "success",
            }

            logger.info(
                f"Successfully set up team {team_name} ({team_id}) "
                f"with {member_results['success']} members "
                f"and {len(channel_ids)} channels"
            )

            return result

        except TeamsIntegrationError as e:
            logger.error(f"Teams setup failed for {team_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Teams setup for {team_name}: {e}")
            raise TeamsIntegrationError(f"Teams setup failed: {str(e)}") from e
