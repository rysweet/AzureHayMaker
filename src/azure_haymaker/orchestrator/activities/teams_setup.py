"""Teams setup activities for orchestrator.

This module contains activity functions for setting up Microsoft Teams
teams for knowledge worker collaboration during the orchestration setup phase.

Activities:
- create_teams_for_teams_activity: Creates Teams teams from M365 groups
- setup_team_channels_and_messages_activity: Configures channels and posts messages

Design Pattern: Activity Functions
- Stateless operations
- Can be retried
- Return structured results
"""

import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from msgraph.graph_service_client import GraphServiceClient

from azure_haymaker.knowledge_worker.teams_integration import (
    TeamsIntegration,
    TeamsIntegrationError,
)
from azure_haymaker.orchestrator.orchestrator_app import app

logger = logging.getLogger(__name__)


@app.activity_trigger(input_name="params")
async def create_teams_for_teams_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Create Teams teams from M365 groups.

    Creates Microsoft Teams teams for each knowledge worker team in the
    organization, using existing M365 unified groups as the foundation.

    Each team is configured with:
    - Member settings (allow channel/message creation)
    - Messaging settings (allow edits/deletions)
    - Fun settings (Giphy with strict filtering)
    - Discovery settings (visible in Teams search)

    Args:
        params: Dictionary containing:
            - run_id: HayMaker run ID
            - teams_config: List of team configurations, each with:
                - m365_group_id: ID of existing M365 group
                - department: Department name
                - team_num: Team number within department
                - members: List of member configs with user_id and role

    Returns:
        Dictionary with setup results:
        {
            "status": "success" | "partial" | "failed",
            "teams_created": int,
            "teams": [
                {
                    "team_id": str,
                    "team_name": str,
                    "m365_group_id": str,
                    "status": "success" | "failed",
                    "error": str (if failed)
                }
            ],
            "error": str (if all teams failed)
        }

    Raises:
        Does not raise - all errors are captured in results
    """
    try:
        run_id = params.get("run_id")
        teams_config = params.get("teams_config", [])

        if not run_id:
            return {
                "status": "failed",
                "error": "run_id is required",
            }

        logger.info(
            f"Activity: create_teams_for_teams - "
            f"Creating {len(teams_config)} Teams teams for run {run_id}"
        )

        # Initialize Teams integration
        credential = DefaultAzureCredential()
        graph_client = GraphServiceClient(credential)
        teams_integration = TeamsIntegration(graph_client, run_id)

        results = []
        success_count = 0

        for team_config in teams_config:
            m365_group_id = team_config.get("m365_group_id")
            department = team_config.get("department")
            team_num = team_config.get("team_num", 0)
            members = team_config.get("members", [])

            if not m365_group_id or not department:
                logger.warning("Skipping team config: missing m365_group_id or department")
                results.append(
                    {
                        "status": "failed",
                        "error": "missing m365_group_id or department",
                    }
                )
                continue

            try:
                # Setup team (creates team, adds members, creates channels)
                team_result = await teams_integration.setup_team(
                    m365_group_id=m365_group_id,
                    department=department,
                    team_num=team_num,
                    member_configs=members,
                    post_welcome_message=True,
                )

                results.append(
                    {
                        "team_id": team_result["team_id"],
                        "team_name": team_result["team_name"],
                        "m365_group_id": m365_group_id,
                        "status": "success",
                        "members_added": team_result["members"]["success"],
                        "channels_created": len(team_result["channels"]),
                    }
                )
                success_count += 1

            except TeamsIntegrationError as e:
                logger.warning(f"Failed to create team for {department}: {e}")
                results.append(
                    {
                        "department": department,
                        "team_num": team_num,
                        "status": "failed",
                        "error": str(e),
                    }
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error creating team for {department}: {e}",
                    exc_info=True,
                )
                results.append(
                    {
                        "department": department,
                        "team_num": team_num,
                        "status": "failed",
                        "error": f"Unexpected error: {str(e)}",
                    }
                )

        # Determine overall status
        if success_count == len(teams_config):
            overall_status = "success"
        elif success_count > 0:
            overall_status = "partial"
        else:
            overall_status = "failed"

        return {
            "status": overall_status,
            "teams_created": success_count,
            "total_teams": len(teams_config),
            "teams": results,
        }

    except Exception as e:
        logger.error(
            f"Activity: create_teams_for_teams - Unexpected error: {str(e)}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": f"Activity failed: {str(e)}",
        }


@app.activity_trigger(input_name="params")
async def setup_team_channels_and_messages_activity(
    params: dict[str, Any],
) -> dict[str, Any]:
    """Activity: Setup channels and post welcome messages to Teams teams.

    This activity can be used if channels and messages need to be set up
    separately from team creation (e.g., retry scenarios).

    Supports:
    - Creating additional channels beyond defaults
    - Posting custom messages to channels
    - Fetching channel information

    Args:
        params: Dictionary containing:
            - run_id: HayMaker run ID
            - teams_channels_config: List of configs, each with:
                - team_id: ID of existing Teams team
                - team_name: Display name of team (for logging)
                - channels: List of channel names to create (optional)
                - post_welcome_message: Whether to post welcome message (default: True)
                - welcome_message: Custom welcome message (optional)

    Returns:
        Dictionary with setup results:
        {
            "status": "success" | "partial" | "failed",
            "channels_created": int,
            "messages_posted": int,
            "results": [
                {
                    "team_id": str,
                    "team_name": str,
                    "channels": dict (channel_name -> channel_id),
                    "welcome_message_id": str,
                    "status": "success" | "failed",
                    "error": str (if failed)
                }
            ]
        }
    """
    try:
        run_id = params.get("run_id")
        teams_channels_config = params.get("teams_channels_config", [])

        if not run_id:
            return {
                "status": "failed",
                "error": "run_id is required",
            }

        logger.info(
            f"Activity: setup_team_channels_and_messages - "
            f"Setting up channels for {len(teams_channels_config)} teams"
        )

        credential = DefaultAzureCredential()
        graph_client = GraphServiceClient(credential)
        teams_integration = TeamsIntegration(graph_client, run_id)

        results = []
        total_channels = 0
        total_messages = 0
        success_count = 0

        for team_config in teams_channels_config:
            team_id = team_config.get("team_id")
            team_name = team_config.get("team_name", team_id)
            channels = team_config.get("channels")
            post_welcome = team_config.get("post_welcome_message", True)
            custom_message = team_config.get("welcome_message", "")

            if not team_id:
                logger.warning("Skipping config: missing team_id")
                continue

            try:
                # Create channels
                channel_ids = {}
                if channels:
                    channel_ids = await teams_integration.create_standard_channels(
                        team_id, channels
                    )
                    total_channels += len(channel_ids)

                # Post welcome message
                message_id = None
                if post_welcome:
                    message_id = await teams_integration.post_welcome_message(
                        team_id,
                        channel_name="General",
                        custom_message=custom_message,
                    )
                    if message_id:
                        total_messages += 1

                results.append(
                    {
                        "team_id": team_id,
                        "team_name": team_name,
                        "channels": channel_ids,
                        "welcome_message_id": message_id,
                        "status": "success",
                    }
                )
                success_count += 1

            except TeamsIntegrationError as e:
                logger.warning(f"Failed to setup channels for team {team_name}: {e}")
                results.append(
                    {
                        "team_id": team_id,
                        "team_name": team_name,
                        "status": "failed",
                        "error": str(e),
                    }
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error setting up channels for {team_name}: {e}",
                    exc_info=True,
                )
                results.append(
                    {
                        "team_id": team_id,
                        "team_name": team_name,
                        "status": "failed",
                        "error": f"Unexpected error: {str(e)}",
                    }
                )

        # Determine overall status
        if success_count == len(teams_channels_config):
            overall_status = "success"
        elif success_count > 0:
            overall_status = "partial"
        else:
            overall_status = "failed"

        return {
            "status": overall_status,
            "channels_created": total_channels,
            "messages_posted": total_messages,
            "results": results,
        }

    except Exception as e:
        logger.error(
            f"Activity: setup_team_channels_and_messages - Unexpected error: {str(e)}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": f"Activity failed: {str(e)}",
        }
