# Teams Integration Module

**Location**: `azure_haymaker.shared.teams`  
**Purpose**: Microsoft Teams integration utilities shared across Azure HayMaker domains

## Overview

This module provides Microsoft Teams integration capabilities via the Microsoft Graph API. It is designed to be domain-independent and usable by any part of the Azure HayMaker system that needs to create and manage Teams teams, channels, and messages.

### Why `shared.teams`?

Previously located in `azure_haymaker.knowledge_worker.teams_integration`, this module was moved to `shared.teams` to break domain coupling. The `orchestrator` domain needed Teams functionality but shouldn't depend on the `knowledge_worker` domain. By moving to a shared location, both domains can use Teams integration without creating circular dependencies.

**Architectural Decision**: See `docs/architecture/DECISION_283_BREAK_DOMAIN_COUPLING.md`

## Quick Start

```python
from azure_haymaker.shared.teams import TeamsIntegration, TeamsIntegrationError
from azure.identity import DefaultAzureCredential
from msgraph.graph_service_client import GraphServiceClient

# Initialize
credential = DefaultAzureCredential()
graph_client = GraphServiceClient(credential)
teams = TeamsIntegration(graph_client, run_id="haymaker-001")

# Create a team from existing M365 group
try:
    result = await teams.setup_team(
        m365_group_id="group-123",
        department="engineering",
        team_num=1,
        member_configs=[
            {"user_id": "user-1", "role": "owner"},
            {"user_id": "user-2", "role": "member"},
        ],
        post_welcome_message=True
    )
    print(f"Team created: {result['team_id']}")
except TeamsIntegrationError as e:
    print(f"Failed to create team: {e}")
```

## Public API

### Classes

#### `TeamsIntegration`
Main class for Teams operations.

**Constructor**:
```python
TeamsIntegration(graph_client: GraphServiceClient, run_id: str)
```

**Methods**:

##### `setup_team()`
Creates a Teams team from an M365 group with members and channels.

```python
await teams.setup_team(
    m365_group_id: str,
    department: str,
    team_num: int,
    member_configs: list[dict],
    post_welcome_message: bool = True
) -> dict
```

**Returns**:
```python
{
    "team_id": str,
    "team_name": str,
    "members": {
        "success": int,
        "failed": int
    },
    "channels": {
        "channel_name": "channel_id",
        ...
    }
}
```

##### `create_team_from_group()`
Creates a Teams team from an existing M365 unified group.

```python
await teams.create_team_from_group(
    m365_group_id: str,
    team_name: str,
    department: str
) -> dict
```

##### `add_team_members()`
Adds members to an existing Teams team with role assignment.

```python
await teams.add_team_members(
    team_id: str,
    member_configs: list[dict]
) -> dict
```

##### `create_standard_channels()`
Creates standard channels for a team.

```python
await teams.create_standard_channels(
    team_id: str,
    channel_names: list[str] | None = None
) -> dict[str, str]
```

##### `post_welcome_message()`
Posts a welcome message to a team channel.

```python
await teams.post_welcome_message(
    team_id: str,
    channel_name: str = "General",
    custom_message: str | None = None
) -> str | None
```

### Exceptions

#### `TeamsIntegrationError`
Raised when Teams operations fail.

```python
class TeamsIntegrationError(Exception):
    """Raised when Teams integration operations fail."""
```

## Architecture

### Module Structure
```
shared/teams/
├── __init__.py           # Public API exports
├── integration.py        # TeamsIntegration implementation
└── README.md            # This file
```

### Dependencies
```
azure_haymaker.shared.teams
    ↓
msgraph.graph_service_client (external)
logging, typing (stdlib)

NO dependencies on:
- azure_haymaker.orchestrator
- azure_haymaker.knowledge_worker
```

### Design Principles

1. **Domain Independence**: No dependencies on orchestrator or knowledge_worker
2. **Clear Public API**: Explicit `__all__` exports in `__init__.py`
3. **Self-Contained**: All Teams functionality in one module
4. **Regeneratable**: Can be rebuilt from specification
5. **Zero-BS**: No stubs, fully functional, comprehensive error handling

## Usage Examples

### Example 1: Create Team with Custom Configuration
```python
from azure_haymaker.shared.teams import TeamsIntegration

teams = TeamsIntegration(graph_client, "run-123")

result = await teams.setup_team(
    m365_group_id="abc-def-ghi",
    department="security",
    team_num=2,
    member_configs=[
        {"user_id": "user-1", "role": "owner"},
        {"user_id": "user-2", "role": "member"},
        {"user_id": "user-3", "role": "member"},
    ],
    post_welcome_message=True
)

print(f"Created team: {result['team_name']}")
print(f"Members added: {result['members']['success']}")
print(f"Channels: {list(result['channels'].keys())}")
```

### Example 2: Add Members to Existing Team
```python
from azure_haymaker.shared.teams import TeamsIntegration

teams = TeamsIntegration(graph_client, "run-456")

result = await teams.add_team_members(
    team_id="team-123",
    member_configs=[
        {"user_id": "new-user-1", "role": "member"},
        {"user_id": "new-user-2", "role": "owner"},
    ]
)

print(f"Added {result['success']} members")
```

### Example 3: Create Custom Channels
```python
from azure_haymaker.shared.teams import TeamsIntegration

teams = TeamsIntegration(graph_client, "run-789")

channels = await teams.create_standard_channels(
    team_id="team-456",
    channel_names=["Engineering", "DevOps", "Security"]
)

print(f"Created channels: {list(channels.keys())}")
```

### Example 4: Error Handling
```python
from azure_haymaker.shared.teams import TeamsIntegration, TeamsIntegrationError

teams = TeamsIntegration(graph_client, "run-101")

try:
    result = await teams.setup_team(
        m365_group_id="invalid-group",
        department="ops",
        team_num=1,
        member_configs=[]
    )
except TeamsIntegrationError as e:
    print(f"Teams operation failed: {e}")
    # Handle error appropriately
```

## Integration with Other Domains

### Orchestrator Domain
The orchestrator uses Teams integration for setting up collaboration spaces during deployment.

```python
# In orchestrator/activities/teams_setup.py
from azure_haymaker.shared.teams import TeamsIntegration, TeamsIntegrationError

teams_integration = TeamsIntegration(graph_client, run_id)
result = await teams_integration.setup_team(...)
```

### Knowledge Worker Domain
Knowledge workers use Teams integration for M365 activity simulation.

```python
# In knowledge_worker/__init__.py (backward compatibility)
from azure_haymaker.shared.teams import TeamsIntegration, TeamsIntegrationError

__all__ = [
    ...,
    "TeamsIntegration",  # Re-exported for backward compatibility
    "TeamsIntegrationError",
]
```

## Testing

### Unit Tests
Located in `tests/shared/teams/test_integration.py`

```python
import pytest
from azure_haymaker.shared.teams import TeamsIntegration, TeamsIntegrationError

@pytest.mark.asyncio
async def test_setup_team_success(mock_graph_client):
    teams = TeamsIntegration(mock_graph_client, "test-run")
    result = await teams.setup_team(
        m365_group_id="test-group",
        department="eng",
        team_num=1,
        member_configs=[{"user_id": "user-1", "role": "owner"}]
    )
    assert result["team_id"] is not None
    assert result["members"]["success"] == 1
```

### Integration Tests
Verify Teams integration works with real Graph API (requires test tenant).

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_real_team(real_graph_client):
    teams = TeamsIntegration(real_graph_client, "integration-test")
    # Create real team, verify, cleanup
```

## Migration Notes

### For Existing Code
If you have code importing from the old location:

**OLD**:
```python
from azure_haymaker.knowledge_worker.teams_integration import TeamsIntegration
```

**NEW**:
```python
from azure_haymaker.shared.teams import TeamsIntegration
```

### Backward Compatibility
The `knowledge_worker` module re-exports `TeamsIntegration` for backward compatibility, but new code should import from `shared.teams` directly.

## Future Enhancements

Potential future additions to this module:
- Channel message threading support
- File attachment handling
- Teams app installation
- Custom tab configuration
- Meeting scheduling integration

## References

- **Architecture Decision**: `docs/architecture/DECISION_283_BREAK_DOMAIN_COUPLING.md`
- **Microsoft Graph Teams API**: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview
- **Teams SDK Documentation**: https://learn.microsoft.com/en-us/graph/sdks/sdks-overview

---

**Version**: 1.0.0  
**Created**: 2026-01-20  
**Issue**: #283 - Break Bidirectional Domain Coupling
