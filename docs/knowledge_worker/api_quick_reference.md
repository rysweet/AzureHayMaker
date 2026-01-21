# Knowledge Worker Agent - API Quick Reference

Quick reference fer the refactored knowledge_worker agent modules. All examples assume the refactorin' be complete.

## Import Paths

### Backward Compatible (Old Imports)

```python
from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerConfig,
    KnowledgeWorkerAgent,
    M365ClientFactory,
    build_worker_identity,
    initialize_m365_client,
)
```

### Module-Specific (Recommended)

```python
from azure_haymaker.knowledge_worker.agent.config import (
    KnowledgeWorkerConfig,
    build_worker_identity,
)

from azure_haymaker.knowledge_worker.agent.core import (
    KnowledgeWorkerAgent,
)

from azure_haymaker.knowledge_worker.agent.m365_integration import (
    M365ClientFactory,
    initialize_m365_client,
)
```

## config.py API

### KnowledgeWorkerConfig

**Purpose:** Configuration dataclass fer knowledge worker agents.

**Required Fields:**
```python
config = KnowledgeWorkerConfig(
    worker_id="kw-abc12345-engi-001",
    display_name="Alex Developer",
    department="engineering",
    persona="engineering",
    tenant_domain="tenant.onmicrosoft.com",
)
```

**Optional Fields:**
```python
config = KnowledgeWorkerConfig(
    # ... required fields ...
    team_id="team-123",
    team_name="Platform Team",
    activity_types=["email", "calendar", "teams"],
    activity_frequency_minutes=30,
    endpoint_type="cli_container",  # or "cloud_pc"
    endpoint_id="endpoint-456",
    m365_app_id="app-123",
    m365_cert_thumbprint="cert-789",
)
```

**Auto-Generated Fields:**
- `name`: Defaults to `f"knowledge-worker-{worker_id}"`
- `goal`: Defaults to `f"Perform M365 activities as {display_name}"`

### build_worker_identity()

**Purpose:** Factory function to construct WorkerIdentity from config.

**Signature:**
```python
def build_worker_identity(config: KnowledgeWorkerConfig) -> WorkerIdentity
```

**Usage:**
```python
identity = build_worker_identity(config)
print(identity.display_name)  # "Alex Developer"
print(identity.persona)       # WorkerPersona.ENGINEERING
```

## core.py API

### KnowledgeWorkerAgent

**Purpose:** Main agent class fer knowledge worker simulation.

**Constructor:**
```python
def __init__(
    self,
    worker_config: KnowledgeWorkerConfig,
    worker_identity: WorkerIdentity | None = None,
    activity_config: WorkerConfig | None = None,
    prompt_path: Path | None = None,
)
```

**Basic Usage:**
```python
agent = KnowledgeWorkerAgent(config)
exit_code = agent.run()
```

### Lifecycle Methods

**on_start()**
```python
def on_start(self) -> None
```
- Initializes M365 client
- Creates communication validator
- Loads allowed recipients
- Called automatically by `run()`

**on_execute()**
```python
def on_execute(self) -> int
```
- Executes scheduled activities
- Returns exit code (0 = success)
- Override fer custom activity patterns

**on_cleanup()**
```python
def on_cleanup(self, exit_code: int) -> None
```
- Disconnects M365 client
- Reports metrics
- Called automatically by `run()`

### Recipient Management

**add_allowed_recipient()**
```python
def add_allowed_recipient(self, recipient: str) -> None
```
```python
agent.add_allowed_recipient("user@tenant.onmicrosoft.com")
```

**add_allowed_recipients()**
```python
def add_allowed_recipients(self, recipients: list[str]) -> None
```
```python
agent.add_allowed_recipients([
    "user1@tenant.onmicrosoft.com",
    "user2@tenant.onmicrosoft.com",
])
```

**validate_recipient()**
```python
def validate_recipient(self, recipient: str) -> bool
```
```python
is_allowed = agent.validate_recipient("user@tenant.onmicrosoft.com")
```

**get_allowed_recipients()**
```python
def get_allowed_recipients(self) -> list[str]
```
```python
recipients = agent.get_allowed_recipients()
print(f"Allowed recipients: {len(recipients)}")
```

### M365 Operations (Async)

**send_email()**
```python
async def send_email(
    self,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
) -> str | None
```
```python
message_id = await agent.send_email(
    to=["team@tenant.onmicrosoft.com"],
    subject="Sprint Planning Update",
    body="<p>Meeting scheduled fer tomorrow at 10 AM.</p>",
    cc=["manager@tenant.onmicrosoft.com"],
)
```

**create_calendar_event()**
```python
async def create_calendar_event(
    self,
    subject: str,
    start_time: str,
    end_time: str,
    attendees: list[str] | None = None,
    body: str = "",
    is_online_meeting: bool = False,
) -> str | None
```
```python
event_id = await agent.create_calendar_event(
    subject="Sprint Planning",
    start_time="2026-01-21T10:00:00Z",
    end_time="2026-01-21T11:00:00Z",
    attendees=["team@tenant.onmicrosoft.com"],
    body="Sprint planning fer Q1 roadmap",
    is_online_meeting=True,
)
```

### State Inspection

**get_worker_stats()**
```python
def get_worker_stats(self) -> dict[str, Any]
```
```python
stats = agent.get_worker_stats()
# Returns:
# {
#     "worker_id": "kw-abc12345-engi-001",
#     "display_name": "Alex Developer",
#     "department": "engineering",
#     "persona": "engineering",
#     "endpoint_type": "cli_container",
#     "allowed_recipients_count": 10,
#     "m365_client_initialized": True,
#     "validator_initialized": True,
# }
```

**Properties:**
```python
# Get M365 client (raises RuntimeError if not initialized)
client = agent.m365_client

# Get validator (raises RuntimeError if not initialized)
validator = agent.validator

# Get config
config = agent.get_config()
```

## m365_integration.py API

### M365ClientFactory

**Purpose:** Factory class fer creatin' Microsoft Graph API clients.

**create() - Static Method**
```python
@staticmethod
def create(
    app_id: str | None = None,
    client_secret: str | None = None,
    tenant_id: str | None = None,
) -> Any
```

**Usage:**
```python
# Option 1: Explicit credentials
client = M365ClientFactory.create(
    app_id="app-123",
    client_secret="secret-456",
    tenant_id="tenant-789",
)

# Option 2: Environment variables (KW_APP_ID, KW_CLIENT_SECRET, KW_TENANT_ID)
client = M365ClientFactory.create()
```

### initialize_m365_client()

**Purpose:** Helper function with error handlin' and graceful degradation.

**Signature:**
```python
def initialize_m365_client(
    worker_id: str,
    app_id: str | None = None,
    client_secret: str | None = None,
    tenant_id: str | None = None,
) -> Any | None
```

**Usage:**
```python
# Returns client or None on error
client = initialize_m365_client(
    worker_id="kw-abc12345-engi-001"
)

if client is None:
    print("M365 client not available")
else:
    print("M365 client ready")
```

## Environment Variables

### M365 Credentials

```bash
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-client-secret"
export KW_TENANT_ID="your-tenant-id"
```

These be used when credentials not be provided to `M365ClientFactory.create()`.

## Complete Example

```python
import asyncio
from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent

# Create configuration
config = KnowledgeWorkerConfig(
    worker_id="kw-abc12345-engi-001",
    display_name="Alex Developer",
    department="engineering",
    persona="engineering",
    team_id="team-123",
    team_name="Platform Team",
    tenant_domain="tenant.onmicrosoft.com",
)

# Create agent
agent = KnowledgeWorkerAgent(config)

# Add allowed recipients
agent.add_allowed_recipients([
    "user1@tenant.onmicrosoft.com",
    "user2@tenant.onmicrosoft.com",
])

# Run agent lifecycle (synchronous)
exit_code = agent.run()

# Or use async operations directly
async def send_update():
    # Manual lifecycle if needed
    agent.on_start()

    # Send email
    message_id = await agent.send_email(
        to=["team@tenant.onmicrosoft.com"],
        subject="Status Update",
        body="<p>All systems operational.</p>",
    )

    # Create meeting
    event_id = await agent.create_calendar_event(
        subject="Team Sync",
        start_time="2026-01-21T10:00:00Z",
        end_time="2026-01-21T10:30:00Z",
        attendees=["team@tenant.onmicrosoft.com"],
        is_online_meeting=True,
    )

    # Cleanup
    agent.on_cleanup(0)

asyncio.run(send_update())

# Check stats
stats = agent.get_worker_stats()
print(f"Worker: {stats['display_name']}")
print(f"Recipients: {stats['allowed_recipients_count']}")
```

## Error Handling

### RuntimeError: M365 client not initialized

```python
try:
    client = agent.m365_client
except RuntimeError:
    print("Call agent.on_start() first")
```

### RuntimeError: Validator not initialized

```python
try:
    validator = agent.validator
except RuntimeError:
    print("Call agent.on_start() first")
```

### ValueError: Missing credentials

```python
from azure_haymaker.knowledge_worker.agent.m365_integration import M365ClientFactory

try:
    client = M365ClientFactory.create()
except ValueError as e:
    print(f"Credentials missing: {e}")
```

## Testing

### Mock M365 Client

```python
from unittest.mock import Mock, AsyncMock

# Create agent with mocked client
agent = KnowledgeWorkerAgent(config)
agent._m365_client = Mock()

# Mock async operations
agent.send_email = AsyncMock(return_value="message-123")

# Test
message_id = await agent.send_email(
    to=["test@tenant.com"],
    subject="Test",
    body="Test body",
)
assert message_id == "message-123"
```

## Migration Checklist

- [ ] Old imports still work (backward compatibility verified)
- [ ] New module-specific imports available
- [ ] All public APIs accessible from facade
- [ ] Tests pass fer all modules
- [ ] Documentation updated
- [ ] Examples updated

---

**API Version:** 1.0.0
**Last Updated:** 2026-01-20
**Module Count:** 3 (config, core, m365_integration)
