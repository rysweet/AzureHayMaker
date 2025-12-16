# Module Specification: Teams Integration Manager

## Overview

**File Location**: `/src/azure_haymaker/provisioning/teams_manager.py`

**Responsibility**: Create Microsoft Teams teams/channels and post deployment updates for tracking and coordination.

**Status**: Teams integration component (Phase 3)

---

## 1. Purpose & Scope

### What It Does

The TeamsManager orchestrates Teams operations:

- **Team Management**: Create teams (idempotent), list existing teams
- **Channel Management**: Create standard and private channels
- **Member Management**: Add members (bulk operations)
- **Message Posting**: Send formatted messages with adaptive cards
- **Message Updates**: Update existing messages with status changes
- **Pinning**: Pin important messages to channels

### What It Does NOT Do

- User identity management (orchestrator)
- Permission/role management (handled by Teams)
- Direct chat messaging (only channel messages)
- Teams app installation (out of scope)

---

## 2. Class Design

### TeamsManager

**Principle**: Thin wrapper around Graph API with idempotency.

#### Constructor

```python
def __init__(
    self,
    graph_client: GraphServiceClient,
    run_id: str,
):
    """Initialize Teams manager.

    Args:
        graph_client: Authenticated GraphServiceClient with permissions:
            - Team.Create
            - Team.ReadWrite.All
            - Chat.Create
            - ChatMessage.Send
        run_id: Run ID for team naming/tracking

    Raises:
        ValueError: If graph_client is None
    """
```

#### Instance Variables

```python
self.graph_client: GraphServiceClient
self.run_id: str
self.logger: logging.Logger
self._team_cache: dict[str, str]  # team_name -> team_id
self._channel_cache: dict[tuple[str, str], str]  # (team_id, channel_name) -> channel_id
```

#### Constants

```python
# Team configuration
DEFAULT_TEAM_TEMPLATE = "standard"

# Channel types
CHANNEL_TYPE_STANDARD = "standard"
CHANNEL_TYPE_PRIVATE = "private"

# Default channels
DEFAULT_CHANNELS = [
    {
        "name": "provisioning-status",
        "description": "Cloud PC provisioning and deployment updates",
        "type": CHANNEL_TYPE_STANDARD,
    },
    {
        "name": "agent-testing",
        "description": "Magentic-UI agent E2E test results",
        "type": CHANNEL_TYPE_STANDARD,
    },
    {
        "name": "alerts",
        "description": "Deployment alerts and errors",
        "type": CHANNEL_TYPE_PRIVATE,
    },
]

# Message formatting
MESSAGE_CARD_VERSION = "1.4"
MESSAGE_CARD_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"

# API limits
MAX_MESSAGE_LENGTH = 28000
MAX_BULK_MEMBERS = 20  # Graph API batch limit
MESSAGE_RETRY_MAX = 3
MESSAGE_RETRY_DELAY = 2  # seconds

# Timeouts
TEAM_CREATION_TIMEOUT_SECONDS = 300
CHANNEL_CREATION_TIMEOUT_SECONDS = 60
MESSAGE_POST_TIMEOUT_SECONDS = 30
```

---

## 3. Public Methods

### 1. ensure_team_exists()

**Purpose**: Get existing team or create new team (idempotent).

**Signature**:
```python
async def ensure_team_exists(
    self,
    team_name: str,
    description: str | None = None,
    owner_upns: list[str] | None = None,
) -> str:
    """Get existing or create new Teams team.

    Args:
        team_name: Team display name (must be unique in tenant)
        description: Team description
        owner_upns: List of UPNs to add as team owners

    Returns:
        Team ID (str)

    Raises:
        TeamsError: On permanent failures
        TimeoutError: On timeout

    Flow:
        1. Query existing teams by display name
        2. If found:
           - Log and cache result
           - Return team ID
        3. If not found:
           - Build team request body:
             - displayName: team_name
             - description: description or auto-generated
             - owners: [list of owner UPNs]
             - template: "standard" (most flexible)
           - POST /teams
           - Wait for async team creation (polling)
           - Add members if provided
           - Cache result
           - Return team ID

    Error Handling:
        - Team already exists → Return existing team ID
        - Creation timeout → TimeoutError
        - Permission denied → TeamsError
        - Invalid owner UPN → Log warning, skip owner

    Example:
        >>> team_id = await manager.ensure_team_exists(
        ...     team_name="Engineering-Provisioning",
        ...     description="Cloud PC deployment tracking",
        ...     owner_upns=["admin@tenant.onmicrosoft.com"]
        ... )
        >>> print(f"Team: {team_id}")
    """
```

**Implementation Notes**:

- **Idempotency**: Query by displayName before creating
- **Async Creation**: Team creation is async; may need polling
- **Owner Assignment**: Add owners during team creation
- **Caching**: Cache team_id for subsequent operations
- **Team Template**: Use "standard" template (allows channels, conversations)

---

### 2. create_channel()

**Purpose**: Create a channel in a team.

**Signature**:
```python
async def create_channel(
    self,
    team_id: str,
    channel_name: str,
    description: str | None = None,
    is_private: bool = False,
) -> str:
    """Create a channel in the team.

    Args:
        team_id: Team ID where channel will be created
        channel_name: Channel name (must be unique in team)
        description: Channel description
        is_private: If True, create private channel

    Returns:
        Channel ID (str)

    Raises:
        TeamsError: On failures

    Flow:
        1. Validate inputs (channel_name format)
        2. Check if channel exists:
           - GET /teams/{id}/channels
           - Filter by displayName
        3. If found:
           - Log and cache
           - Return channel ID
        4. If not found:
           - Build channel request:
             - displayName: channel_name
             - description: description
             - membershipType: "standard" or "private"
           - POST /teams/{id}/channels
           - Wait for creation (usually instant)
           - Cache result
           - Return channel ID

    Error Handling:
        - Channel already exists → Return existing ID
        - Team not found → TeamsError
        - Permission denied → TeamsError
        - Invalid channel name → TeamsError

    Example:
        >>> channel_id = await manager.create_channel(
        ...     team_id="team-123",
        ...     channel_name="deployment-logs",
        ...     description="Detailed provisioning logs",
        ...     is_private=True
        ... )
        >>> print(f"Channel: {channel_id}")
    """
```

**Implementation Notes**:

- **Channel Naming**: Teams enforces restrictions (no special chars, max 50 chars)
- **Private Channels**: Require explicit member addition
- **Caching**: Cache for performance

---

### 3. add_team_members()

**Purpose**: Add members to a team in bulk.

**Signature**:
```python
async def add_team_members(
    self,
    team_id: str,
    member_upns: list[str],
    role: str = "member",  # "owner" or "member"
) -> AddMembersResult:
    """Add members to team.

    Performs bulk addition with batching (Graph API limit: 20 per request).

    Args:
        team_id: Team ID
        member_upns: List of user UPNs to add
        role: Role to assign ("owner" or "member")

    Returns:
        AddMembersResult:
            - success: bool
            - added: list[str] (UPNs successfully added)
            - failed: list[tuple[str, str]] (UPN, error reason)
            - already_members: list[str]
            - duration_seconds: float

    Raises:
        TeamsError: On critical failures

    Flow:
        1. Validate inputs (UPN format)
        2. Query existing team members
        3. For each member_upn:
           - If already member:
             - Add to already_members list
           - Else:
             - Add to batch (max 20)
        4. For each batch:
           - POST /teams/{id}/members
           - Retry failed additions (max 3 attempts)
           - Track success/failure
        5. Return AddMembersResult

    Error Handling:
        - Member already in team → Skip
        - Invalid UPN → Log warning, skip
        - Permission denied → Log, continue with others
        - User not found → Log warning, skip

    Example:
        >>> result = await manager.add_team_members(
        ...     team_id="team-123",
        ...     member_upns=["user1@tenant.com", "user2@tenant.com"],
        ...     role="member"
        ... )
        >>> print(f"Added: {len(result.added)}, Failed: {len(result.failed)}")
    """
```

**Implementation Notes**:

- **Batching**: Graph API limits to ~20 members per request
- **Idempotency**: Check for existing members before adding
- **Error Handling**: One member failure doesn't block others
- **Role Assignment**: Map role string to Teams role enum

---

### 4. post_deployment_message()

**Purpose**: Post formatted deployment message to channel.

**Signature**:
```python
async def post_deployment_message(
    self,
    team_id: str,
    channel_id: str,
    deployment_info: DeploymentInfo,
) -> str:
    """Post deployment status message to channel.

    Uses adaptive card formatting for rich display.

    Args:
        team_id: Team ID
        channel_id: Channel ID
        deployment_info: DeploymentInfo with deployment details

    Returns:
        Message ID (str) for future reference/updates

    Raises:
        TeamsError: On posting failures

    Flow:
        1. Validate channel exists
        2. Build adaptive card message:
           - Title: "Cloud PC Deployment - {run_id}"
           - Status: deployment_info.status
           - Summary: worker count, Cloud PC count, agent status
           - Timestamp and duration
           - Call-to-action buttons
        3. Format message body with card
        4. POST /teams/{id}/channels/{id}/messages
        5. Retry on failure (transient errors)
        6. Return message ID

    Error Handling:
        - Channel not found → TeamsError
        - Message too long → Split and post multiple
        - Permission denied → TeamsError
        - Timeout → Retry with backoff

    Example:
        >>> msg_id = await manager.post_deployment_message(
        ...     team_id="team-123",
        ...     channel_id="channel-456",
        ...     deployment_info=DeploymentInfo(...)
        ... )
        >>> print(f"Message posted: {msg_id}")
    """
```

**Implementation Notes**:

- **Card Format**: Use adaptive cards (rich, interactive)
- **Message Formatting**:
  ```json
  {
    "body": [
      {
        "type": "TextBlock",
        "text": "Cloud PC Deployment Status",
        "weight": "bolder",
        "size": "large"
      },
      {
        "type": "FactSet",
        "facts": [
          {"name": "Status", "value": "Provisioning"},
          {"name": "Workers", "value": "10 of 25 ready"}
        ]
      }
    ]
  }
  ```
- **Message Splitting**: If > 28KB, split into multiple messages
- **Retry**: Transient errors (timeout, rate limit) retry with backoff

---

### 5. update_provisioning_status()

**Purpose**: Update existing message with new provisioning status.

**Signature**:
```python
async def update_provisioning_status(
    self,
    team_id: str,
    channel_id: str,
    message_id: str,
    status: str,
    details: dict[str, Any],
) -> bool:
    """Update existing message with new provisioning status.

    Edits message with latest status (success, in-progress, failed).

    Args:
        team_id: Team ID
        channel_id: Channel ID
        message_id: Message ID to update
        status: Status string ("provisioning", "succeeded", "failed")
        details: Details dict with stats

    Returns:
        bool: True if updated, False on error

    Raises:
        TeamsError: On critical failures

    Flow:
        1. Build updated card with new status
        2. PATCH /teams/{id}/channels/{id}/messages/{id}
        3. Return success

    Error Handling:
        - Message not found → Return False
        - Permission denied → TeamsError
        - Timeout → Retry
        - User is not message author → May fail (Teams restriction)

    Example:
        >>> updated = await manager.update_provisioning_status(
        ...     team_id="team-123",
        ...     channel_id="channel-456",
        ...     message_id="msg-789",
        ...     status="succeeded",
        ...     details={"workers_provisioned": 25, "errors": 0}
        ... )
    """
```

**Implementation Notes**:

- **Editing Limitations**: Can only edit own messages
- **Update Pattern**: Build new card with updated values
- **Retry**: Transient failures retry with backoff

---

### 6. pin_message()

**Purpose**: Pin message to channel.

**Signature**:
```python
async def pin_message(
    self,
    team_id: str,
    channel_id: str,
    message_id: str,
) -> bool:
    """Pin message to channel.

    Pins message so it appears at top of channel.

    Args:
        team_id: Team ID
        channel_id: Channel ID
        message_id: Message ID to pin

    Returns:
        bool: True if pinned

    Raises:
        TeamsError: On failures

    Flow:
        1. POST /teams/{id}/channels/{id}/messages/{id}/pin
        2. Return success

    Error Handling:
        - Message not found → Return False
        - Already pinned → Return True (idempotent)
        - Permission denied → TeamsError

    Example:
        >>> pinned = await manager.pin_message(
        ...     team_id="team-123",
        ...     channel_id="channel-456",
        ...     message_id="msg-789"
        ... )
    """
```

**Implementation Notes**:

- **Idempotency**: Pinning already-pinned message is OK
- **Limit**: Teams allows max 50 pinned messages per channel
- **Permissions**: Requires channel owner or higher

---

### 7. post_status_update()

**Purpose**: Post status update with worker counts and Cloud PC status.

**Signature**:
```python
async def post_status_update(
    self,
    team_id: str,
    channel_id: str,
    status_summary: StatusSummary,
) -> str:
    """Post summary status update message.

    Posts brief status update (e.g., "5 Cloud PCs provisioned").

    Args:
        team_id: Team ID
        channel_id: Channel ID
        status_summary: StatusSummary with counts and status

    Returns:
        Message ID

    Raises:
        TeamsError: On failures

    Example:
        >>> msg_id = await manager.post_status_update(
        ...     team_id="team-123",
        ...     channel_id="channel-456",
        ...     status_summary=StatusSummary(
        ...         total_workers=25,
        ...         provisioned_count=15,
        ...         agents_installed=15,
        ...         tests_passed=12,
        ...     )
        ... )
    """
```

**Implementation Notes**:

- **Lightweight**: Brief update, not full deployment info
- **Formatting**: Simple text or card

---

## 4. Data Models

```python
@dataclass
class DeploymentInfo:
    """Deployment information for Teams messages."""
    run_id: str
    total_workers: int
    provisioned_workers: int
    ready_workers: int
    failed_workers: int
    agents_installed: int
    tests_passed: int
    tests_failed: int
    status: str  # "provisioning", "succeeded", "partial", "failed"
    start_time: datetime
    duration_minutes: float | None = None
    errors: list[str] = field(default_factory=list)

@dataclass
class StatusSummary:
    """Brief status summary."""
    total_workers: int
    provisioned_count: int
    agents_installed: int
    tests_passed: int
    status: str = "in-progress"

@dataclass
class AddMembersResult:
    """Result of bulk member addition."""
    success: bool
    added: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    already_members: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

@dataclass
class TeamConfig:
    """Teams team configuration."""
    team_name: str
    description: str
    owner_upns: list[str] = field(default_factory=list)
    member_upns: list[str] = field(default_factory=list)
    channels: list[dict[str, Any]] = field(default_factory=lambda: DEFAULT_CHANNELS)
```

---

## 5. Message Format (Adaptive Card)

```json
{
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "type": "AdaptiveCard",
  "version": "1.4",
  "body": [
    {
      "type": "TextBlock",
      "text": "Cloud PC Deployment Status",
      "weight": "bolder",
      "size": "large",
      "color": "accent"
    },
    {
      "type": "TextBlock",
      "text": "Run: haymaker-001 | Updated: 2025-01-15 14:30:00 UTC",
      "size": "small",
      "isSubtle": true
    },
    {
      "type": "Container",
      "separator": true,
      "items": [
        {
          "type": "ColumnSet",
          "columns": [
            {
              "width": "stretch",
              "items": [
                {
                  "type": "TextBlock",
                  "text": "Status",
                  "weight": "bolder"
                },
                {
                  "type": "TextBlock",
                  "text": "Provisioning",
                  "size": "large",
                  "color": "warning"
                }
              ]
            },
            {
              "width": "stretch",
              "items": [
                {
                  "type": "TextBlock",
                  "text": "Progress",
                  "weight": "bolder"
                },
                {
                  "type": "TextBlock",
                  "text": "12 of 25 workers ready",
                  "size": "large"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "FactSet",
      "facts": [
        {"name": "Cloud PCs Provisioned", "value": "12"},
        {"name": "Agents Installed", "value": "10"},
        {"name": "Tests Passed", "value": "9"},
        {"name": "Errors", "value": "0"},
        {"name": "Duration", "value": "42 minutes"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "View Deployment Report",
      "url": "https://portal.azure.com/..."
    },
    {
      "type": "Action.OpenUrl",
      "title": "Refresh Status",
      "url": "..."
    }
  ]
}
```

---

## 6. Error Handling

### Custom Exceptions

```python
class TeamsError(Exception):
    """Base Teams error."""
    pass

class TeamNotFoundError(TeamsError):
    """Team not found."""
    pass

class ChannelNotFoundError(TeamsError):
    """Channel not found."""
    pass

class MessagePostError(TeamsError):
    """Failed to post message."""
    pass

class MemberAddError(TeamsError):
    """Failed to add member."""
    pass
```

---

## 7. Testing Strategy

```python
# Unit tests
test_ensure_team_exists_creates_new()
test_ensure_team_exists_reuses_existing()
test_ensure_team_exists_with_owners()
test_ensure_team_exists_timeout()

test_create_channel_success()
test_create_channel_private()
test_create_channel_already_exists()
test_create_channel_team_not_found()

test_add_team_members_success()
test_add_team_members_already_members()
test_add_team_members_invalid_upn()
test_add_team_members_batching()

test_post_deployment_message()
test_post_deployment_message_truncate_long()
test_post_status_update()

test_update_provisioning_status()
test_pin_message()
test_pin_message_idempotent()
```

---

## 8. Success Criteria

- [ ] All public methods implemented
- [ ] Idempotent team and channel creation
- [ ] Bulk member addition with batching
- [ ] Rich adaptive card message formatting
- [ ] Message updates and pinning
- [ ] Error handling and retries
- [ ] Unit tests with 90%+ coverage
- [ ] Integration tests against Teams API
- [ ] Complete logging
- [ ] Type hints validated

---

## 9. Dependencies

### Internal
- Data models for deployment info

### External
- `msgraph.core.GraphServiceClient`
- Standard library: `asyncio`, `logging`, `json`, `datetime`

---

## 10. Future Enhancements

- [ ] Thread-based message organization
- [ ] Reactions/emoji support
- [ ] Tab integration (display Cloud PC status)
- [ ] Webhook integration for external alerts
- [ ] Message templates and rendering engine
