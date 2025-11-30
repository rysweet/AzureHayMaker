"""Example: Integrating Teams setup into orchestrator workflow.

This example demonstrates how to integrate the Teams integration module
into an Azure Durable Functions orchestrator workflow for knowledge worker
team provisioning.

This shows:
1. Creating M365 groups (EntraGroupManager)
2. Creating Teams teams (TeamsIntegration)
3. Adding members to teams
4. Creating channels and posting messages
5. Storing team metadata

The orchestrator uses Durable Functions for long-running workflows with
checkpointing and automatic retry.
"""

from typing import Any
from azure.functions import DurableOrchestrationContext
from azure_haymaker.orchestrator.orchestrator_app import app


@app.orchestration_trigger(context_name="context")
async def orchestrator_with_teams_setup(
    context: DurableOrchestrationContext,
) -> dict[str, Any]:
    """Orchestrator workflow with Teams setup phase.

    Workflow phases:
    1. Validation: Check prerequisites
    2. Entra Setup: Create Entra security groups
    3. M365 Setup: Create M365 unified groups
    4. Teams Setup: Create Teams teams (NEW)
    5. Execution: Deploy workers to containers
    6. Monitoring: Track execution (8 hours)
    7. Cleanup: Delete ephemeral resources

    Args:
        context: Durable Functions orchestration context

    Returns:
        Dictionary with orchestration results
    """
    orchestrator_input = context.get_input()
    run_id = orchestrator_input.get("run_id", "unknown")

    # Phase 1: Validation
    validation_result = await context.call_activity(
        "validate_environment_activity",
        {"run_id": run_id},
    )

    if validation_result.get("status") != "success":
        return {
            "status": "failed",
            "phase": "validation",
            "error": validation_result.get("error"),
        }

    # Phase 2: Create Entra security groups
    entra_groups = await context.call_activity(
        "create_entra_security_groups_activity",
        {
            "run_id": run_id,
            "departments": ["engineering", "sales", "marketing"],
        },
    )

    # Phase 3: Create M365 unified groups
    m365_groups = await context.call_activity(
        "create_m365_groups_activity",
        {
            "run_id": run_id,
            "entra_groups": entra_groups.get("groups", []),
        },
    )

    if m365_groups.get("status") != "success":
        return {
            "status": "failed",
            "phase": "m365_setup",
            "error": m365_groups.get("error"),
        }

    # Phase 4: Create Teams teams (NEW)
    # Build team configurations from M365 groups
    teams_config = []
    for m365_group in m365_groups.get("groups", []):
        # Get department and team number from group metadata
        group_name = m365_group.get("display_name", "")
        department = m365_group.get("department", "unknown")
        team_num = m365_group.get("team_num", 1)

        # Get member IDs for this team (from your worker provisioning)
        member_ids = await context.call_activity(
            "get_team_member_ids_activity",
            {"group_id": m365_group.get("id"), "run_id": run_id},
        )

        # Build member configurations with roles
        member_configs = []
        for i, member_id in enumerate(member_ids.get("ids", [])):
            # First member is owner, others are members
            role = "owner" if i == 0 else "member"
            member_configs.append({"user_id": member_id, "role": role})

        teams_config.append({
            "m365_group_id": m365_group.get("id"),
            "department": department,
            "team_num": team_num,
            "members": member_configs,
        })

    # Create Teams teams (all in parallel with fan-out pattern)
    teams_result = await context.call_activity(
        "create_teams_for_teams_activity",
        {
            "run_id": run_id,
            "teams_config": teams_config,
        },
    )

    if teams_result.get("status") == "failed":
        return {
            "status": "failed",
            "phase": "teams_setup",
            "error": teams_result.get("error"),
        }

    # Extract created team IDs for later use
    created_teams = {
        team["team_name"]: team["team_id"]
        for team in teams_result.get("teams", [])
        if team.get("status") == "success"
    }

    # Phase 5: Store team metadata
    # This would be stored in your database for worker agents to use
    metadata_result = await context.call_activity(
        "store_team_metadata_activity",
        {
            "run_id": run_id,
            "teams": created_teams,
            "m365_groups": m365_groups.get("groups", []),
        },
    )

    # Phase 6: Create container apps for workers
    # ... existing container provisioning code ...

    # Phase 7: Post initial messages to team channels
    channels_config = [
        {
            "team_id": team_id,
            "team_name": team_name,
            "channels": ["Projects"],
            "post_welcome_message": True,
            "welcome_message": f"Welcome to {team_name}! This team has been set up for the Knowledge Worker Activity Framework.",
        }
        for team_name, team_id in created_teams.items()
    ]

    channels_result = await context.call_activity(
        "setup_team_channels_and_messages_activity",
        {
            "run_id": run_id,
            "teams_channels_config": channels_config,
        },
    )

    # Return success with full orchestration summary
    return {
        "status": "success",
        "run_id": run_id,
        "validation": validation_result,
        "m365_groups": len(m365_groups.get("groups", [])),
        "teams_created": teams_result.get("teams_created"),
        "teams": created_teams,
        "channels_created": channels_result.get("channels_created"),
        "messages_posted": channels_result.get("messages_posted"),
    }


# ==============================================================================
# Example Activity Functions (for reference)
# ==============================================================================


@app.activity_trigger(input_name="params")
async def get_team_member_ids_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Get member IDs for a team.

    In a real implementation, this would query your database or
    provisioning system to get the list of workers assigned to a team.

    Args:
        params: Dictionary with:
            - group_id: M365 group ID
            - run_id: HayMaker run ID

    Returns:
        Dictionary with member IDs list
    """
    # In real implementation:
    # 1. Query database for workers assigned to this team
    # 2. Get their Entra user IDs
    # 3. Return as list

    # Example implementation:
    group_id = params.get("group_id")
    run_id = params.get("run_id")

    # Placeholder: In real code, query your provisioning system
    member_ids = [
        f"user-{i}" for i in range(1, 4)  # 3 team members
    ]

    return {
        "status": "success",
        "group_id": group_id,
        "ids": member_ids,
    }


@app.activity_trigger(input_name="params")
async def store_team_metadata_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Store team metadata for worker access.

    Stores team IDs and metadata in a persistent store (database, storage, etc.)
    so that workers can reference their team during execution.

    Args:
        params: Dictionary with:
            - run_id: HayMaker run ID
            - teams: Dictionary of team_name -> team_id
            - m365_groups: List of M365 group information

    Returns:
        Dictionary with storage result
    """
    run_id = params.get("run_id")
    teams = params.get("teams", {})

    # In real implementation:
    # 1. Store to database (Cosmos DB, SQL, etc.)
    # 2. Store to blob storage as JSON
    # 3. Make available to workers via key vault or config

    # Example: Store as JSON
    metadata = {
        "run_id": run_id,
        "teams": teams,
        "created_at": context.current_utc_datetime.isoformat(),
    }

    # In real code:
    # await blob_client.upload_blob(
    #     name=f"teams-metadata-{run_id}.json",
    #     data=json.dumps(metadata),
    # )

    return {
        "status": "success",
        "teams_stored": len(teams),
        "metadata_location": f"blob:teams-metadata-{run_id}.json",
    }


# ==============================================================================
# Usage in Worker Agent
# ==============================================================================

"""
After teams are created, knowledge workers can use the team information:

from azure_haymaker.knowledge_worker import (
    KnowledgeWorkerAgent,
    KnowledgeWorkerConfig,
)
from azure_haymaker.knowledge_worker.operations.teams import TeamsOperations

# Load team metadata for this worker
config = KnowledgeWorkerConfig(
    worker_id="kw-abc12345-engi-001",
    display_name="Alex Developer",
    department="engineering",
    team_id="team-uuid-from-metadata",  # From stored team metadata
    # ... other config ...
)

agent = KnowledgeWorkerAgent(config)

# In activities, worker can perform Teams operations
async def execute_team_activity():
    teams_ops = TeamsOperations(
        worker_identity=agent.worker_identity,
        m365_client=agent.m365_client,
        validator=agent.validator,
    )

    # Post message to team channel
    message_id = await teams_ops.post_to_channel(
        team_id=agent.worker_identity.team_ids[0],
        channel_id="projects-channel-id",
        content="Great progress on the project!",
    )

    # Send direct message to colleague
    chat_id = await teams_ops.send_chat_message(
        recipient_upn="colleague@tenant.onmicrosoft.com",
        content="Let's sync up on the status",
    )
"""

# ==============================================================================
# Configuration Example
# ==============================================================================

"""
Example configuration for the orchestrator:

{
    "run_id": "kw-abc12345-prod-001",
    "departments": [
        {
            "name": "engineering",
            "team_count": 2,
            "workers_per_team": 5,
        },
        {
            "name": "sales",
            "team_count": 1,
            "workers_per_team": 3,
        },
    ],
    "orchestrator": {
        "timeout_minutes": 480,  # 8 hours
        "max_parallel_teams": 5,
        "post_welcome_messages": True,
    }
}
"""
