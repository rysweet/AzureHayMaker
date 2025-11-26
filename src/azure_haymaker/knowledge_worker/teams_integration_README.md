# Teams Integration Module

## Overview

The Teams integration module provides comprehensive Teams team creation and management for the Knowledge Worker Activity Framework. It integrates with Microsoft Graph API to create Teams teams from M365 unified groups, manage team members, create channels, and post messages.

## Key Features

- **Team Creation**: Create Teams teams from existing M365 unified groups
- **Member Management**: Add users with role assignment (owner/member)
- **Channel Setup**: Create standard channels (General, Projects) and additional channels
- **Messaging**: Post welcome messages and notifications to channels
- **Error Handling**: Comprehensive error handling and logging
- **Orchestrator Integration**: Activity functions for Durable Functions workflows

## Architecture

### Core Components

```
TeamsIntegration
├── create_team_from_group()      # Create team from M365 group
├── add_team_members()            # Add users with roles
├── create_standard_channels()    # Create default channels
├── post_welcome_message()        # Post to channel
└── setup_team()                  # Orchestration method (combines all)
```

### Error Handling

```python
TeamsIntegrationError           # Custom exception for Teams operations
```

## Usage

### Basic Setup

```python
from azure.identity import DefaultAzureCredential
from msgraph import GraphServiceClient
from azure_haymaker.knowledge_worker import TeamsIntegration

# Initialize
credential = DefaultAzureCredential()
graph_client = GraphServiceClient(credential)
teams_integration = TeamsIntegration(graph_client, run_id="abc12345")

# Setup complete team
result = await teams_integration.setup_team(
    m365_group_id="group-uuid",
    department="engineering",
    team_num=1,
    member_configs=[
        {"user_id": "user-id-1", "role": "owner"},
        {"user_id": "user-id-2", "role": "member"},
    ],
    post_welcome_message=True,
)

# Result structure:
# {
#     "team_id": "team-uuid",
#     "team_name": "KW-ABC12345-Engineering-Team1",
#     "m365_group_id": "group-uuid",
#     "members": {"success": 2, "failed": 0},
#     "channels": {"Projects": "channel-uuid", ...},
#     "welcome_message_id": "message-uuid",
#     "status": "success"
# }
```

### Step-by-Step Operations

```python
# 1. Create team from existing M365 group
team_id = await teams_integration.create_team_from_group(
    m365_group_id="group-uuid",
    team_name="KW-ABC12345-Engineering-Team1",
    department="engineering",
    team_num=1,
)

# 2. Add members with roles
results = await teams_integration.add_team_members(
    team_id=team_id,
    member_configs=[
        {"user_id": "user-id-1", "role": "owner"},
        {"user_id": "user-id-2", "role": "member"},
        {"user_id": "user-id-3", "role": "member"},
    ],
)
# returns: {"success": 3, "failed": 0}

# 3. Create channels
channels = await teams_integration.create_standard_channels(
    team_id=team_id,
    channels=["Projects", "Planning", "Retrospectives"],
)
# returns: {"Projects": "channel-uuid", "Planning": "channel-uuid", ...}

# 4. Post message to channel
message_id = await teams_integration.post_welcome_message(
    team_id=team_id,
    channel_name="General",
    custom_message="Custom welcome message",
)
```

## Orchestrator Integration

### Activity Functions

The module provides two activity functions for Azure Durable Functions:

#### 1. `create_teams_for_teams_activity`

Creates Teams teams from M365 groups and populates with members.

```python
from azure_haymaker.orchestrator.activities.teams_setup import (
    create_teams_for_teams_activity,
)

# In orchestrator function:
params = {
    "run_id": "abc12345",
    "teams_config": [
        {
            "m365_group_id": "group-uuid-1",
            "department": "engineering",
            "team_num": 1,
            "members": [
                {"user_id": "user-id-1", "role": "owner"},
                {"user_id": "user-id-2", "role": "member"},
            ],
        },
        {
            "m365_group_id": "group-uuid-2",
            "department": "sales",
            "team_num": 1,
            "members": [
                {"user_id": "user-id-3", "role": "owner"},
            ],
        },
    ],
}

result = await context.call_activity("create_teams_for_teams_activity", params)

# Result structure:
# {
#     "status": "success",  # or "partial", "failed"
#     "teams_created": 2,
#     "total_teams": 2,
#     "teams": [
#         {
#             "team_id": "team-uuid-1",
#             "team_name": "KW-ABC12345-Engineering-Team1",
#             "m365_group_id": "group-uuid-1",
#             "status": "success",
#             "members_added": 2,
#             "channels_created": 1,  # Default channels
#         },
#         ...
#     ]
# }
```

#### 2. `setup_team_channels_and_messages_activity`

Configures channels and posts messages for existing teams (for retry/separation).

```python
params = {
    "run_id": "abc12345",
    "teams_channels_config": [
        {
            "team_id": "team-uuid-1",
            "team_name": "KW-ABC12345-Engineering-Team1",
            "channels": ["Projects", "Planning"],
            "post_welcome_message": True,
            "welcome_message": "Custom welcome for team",
        },
    ],
}

result = await context.call_activity(
    "setup_team_channels_and_messages_activity",
    params,
)
```

### Integration into Orchestrator Workflow

```python
@app.orchestration_trigger(context_name="context")
async def orchestrator_with_teams(context):
    """Example orchestrator with Teams setup."""

    # ... existing setup code ...

    # Phase 1: Create M365 groups (via EntraGroupManager)
    m365_groups = [
        {
            "id": group_id_1,
            "name": "KW-ABC12345-Engineering-Team1",
            "department": "engineering",
        },
        # ...
    ]

    # Phase 2: Create Teams teams (NEW)
    teams_config = []
    for group in m365_groups:
        teams_config.append({
            "m365_group_id": group["id"],
            "department": group["department"],
            "team_num": 1,
            "members": [
                {"user_id": worker_id, "role": "member"}
                for worker_id in team_member_ids
            ],
        })

    # Call Teams setup activity
    teams_result = await context.call_activity(
        "create_teams_for_teams_activity",
        {
            "run_id": run_id,
            "teams_config": teams_config,
        },
    )

    if teams_result["status"] == "failed":
        raise Exception("Teams setup failed")

    # Store team IDs for later use (e.g., messaging activities)
    team_ids = {
        team["team_name"]: team["team_id"]
        for team in teams_result["teams"]
        if team["status"] == "success"
    }

    # ... continue with execution ...
```

## Default Channels

By default, the following channels are created for each team:

- **General**: Automatically created by Teams (no action needed)
- **Projects**: For project-specific discussions

To create additional channels:

```python
channels = await teams_integration.create_standard_channels(
    team_id=team_id,
    channels=["Projects", "Planning", "Retrospectives", "Social"],
)
```

## Welcome Message

A default welcome message is provided:

```
Welcome to the {team_name} team!

This team has been set up for the Knowledge Worker Activity Framework
and is ready for collaboration. Use the channels below to organize
your work:

- **General**: General team announcements and discussions
- **Projects**: Project-specific discussions and updates

Looking forward to productive collaboration!
```

To use a custom message:

```python
message_id = await teams_integration.post_welcome_message(
    team_id=team_id,
    channel_name="General",
    custom_message="<p>Custom welcome message</p>",
)
```

## Naming Conventions

Teams team names follow the M365 group naming convention:

```
KW-{RunId[:8]}-{Dept}-Team{N}
```

Examples:
- `KW-ABC12345-Engineering-Team1`
- `KW-ABC12345-Sales-Team1`
- `KW-ABC12345-Marketing-Team2`

## Error Handling

The module provides comprehensive error handling:

```python
from azure_haymaker.knowledge_worker import TeamsIntegrationError

try:
    result = await teams_integration.setup_team(...)
except TeamsIntegrationError as e:
    logger.error(f"Teams setup failed: {e}")
    # Handle specific Teams integration errors
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle other errors
```

## Security Considerations

1. **Graph API Permissions**: Requires `Team.Create` and `TeamMember.ReadWrite.All` permissions
2. **Role Assignment**: Only designated users should be team owners
3. **Channel Access**: All team members have access to all channels by default
4. **Message Monitoring**: Welcome messages are posted from the service principal account

## Testing

### Unit Tests

```python
import pytest
from azure_haymaker.knowledge_worker import TeamsIntegration, TeamsIntegrationError


@pytest.mark.asyncio
async def test_setup_team_success(mock_graph_client):
    """Test successful team setup."""
    teams_integration = TeamsIntegration(mock_graph_client, "test-run")

    result = await teams_integration.setup_team(
        m365_group_id="group-id",
        department="engineering",
        team_num=1,
        member_configs=[{"user_id": "user-1", "role": "owner"}],
    )

    assert result["status"] == "success"
    assert result["team_id"] is not None
    assert result["members"]["success"] == 1


@pytest.mark.asyncio
async def test_setup_team_missing_group_id():
    """Test team setup with missing group ID."""
    teams_integration = TeamsIntegration(mock_graph_client, "test-run")

    with pytest.raises(TeamsIntegrationError):
        await teams_integration.create_team_from_group(
            m365_group_id="",
            team_name="test",
            department="test",
            team_num=1,
        )
```

### Integration Tests

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_team_setup(real_graph_client, test_group_id):
    """End-to-end team setup with real Graph API."""
    teams_integration = TeamsIntegration(real_graph_client, "int-test")

    try:
        result = await teams_integration.setup_team(
            m365_group_id=test_group_id,
            department="testing",
            team_num=1,
            member_configs=[],  # No members for test
            post_welcome_message=False,  # Skip message for quick test
        )

        assert result["status"] == "success"
        # Verify team was created in Teams

    finally:
        # Cleanup: Delete created team
        pass
```

## Logging

The module provides detailed logging at multiple levels:

```python
# DEBUG: Detailed operation information
logger.debug(f"Added member {user_id} to team {team_id} with role {role}")

# INFO: Successful operations
logger.info(f"Created Teams team: {team_name} ({team_id})")

# WARNING: Recoverable issues
logger.warning(f"Channel {channel_name} not found in team {team_id}")

# ERROR: Operation failures
logger.error(f"Failed to create Teams team {team_name}: {e}")
```

## Troubleshooting

### Common Issues

1. **"Failed to extract team ID from response"**
   - M365 group may not exist
   - Group may not be Teams-enabled
   - Insufficient permissions on group

2. **"Member already exists"**
   - Not an error - user is already a team member
   - Logged as debug message and operation continues

3. **"Channel not found"**
   - Channel may not have been created yet
   - Verify channel name (case-sensitive)
   - Wait for channel creation to complete

### Permission Requirements

Required Microsoft Graph permissions:
- `Team.Create`
- `TeamMember.ReadWrite.All`
- `Channel.Create`
- `ChatMessage.Send`
- `Group.Read.All`

## Performance

- **Team Creation**: ~2-5 seconds per team
- **Member Addition**: ~200-500ms per member (can be parallelized)
- **Channel Creation**: ~1-2 seconds per channel
- **Message Posting**: ~500-1000ms per message

## Related Classes

- `EntraGroupManager`: Creates M365 unified groups that Teams teams are built on
- `TeamsOperations`: Handles ongoing Teams messaging and interactions
- `Team`: Data model for team metadata

## See Also

- [Microsoft Teams API Documentation](https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview)
- [Microsoft Graph Teams SDK](https://github.com/microsoftgraph/msgraph-sdk-python)
- [Knowledge Worker Agent](../agent.py)
- [Team Model](../models/team.py)
