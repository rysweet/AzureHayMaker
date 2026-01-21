# Knowledge Worker Module

Simulate M365 knowledge worker activities fer Azure infrastructure testin' and validation.

## Overview

The Knowledge Worker module simulates realistic M365 user activities including email, calendar events, Teams messages, and document collaboration. It enables infrastructure teams to generate authentic workload patterns fer testin' Azure Virtual Desktop, Microsoft 365, and network infrastructure.

## Architecture

```
knowledge_worker/
├── agent/               # Agent implementation (Bricks & Studs pattern)
│   ├── config.py        # Configuration brick
│   ├── core.py          # Core agent brick
│   └── m365_integration.py  # M365 integration brick
├── models/              # Data models
│   └── worker.py        # Worker identity and configuration models
├── operations/          # M365 operations
│   ├── email.py         # Email send/receive/organize
│   ├── calendar.py      # Calendar event management
│   ├── teams.py         # Teams messaging and channels
│   └── validators.py    # Communication validation
└── README.md            # This file
```

## Quick Start

### Basic Usage

```python
from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerConfig,
    KnowledgeWorkerAgent,
)

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

# Create and run agent
agent = KnowledgeWorkerAgent(config)

# Add allowed recipients (typically done by orchestrator)
agent.add_allowed_recipients([
    "user1@tenant.onmicrosoft.com",
    "user2@tenant.onmicrosoft.com",
])

# Run agent lifecycle
exit_code = agent.run()
```

### Async M365 Operations

```python
import asyncio
from azure_haymaker.knowledge_worker.agent import KnowledgeWorkerAgent

async def send_team_update(agent: KnowledgeWorkerAgent):
    """Send a team update email."""
    message_id = await agent.send_email(
        to=["team@tenant.onmicrosoft.com"],
        subject="Sprint Planning Update",
        body="<p>Team meeting scheduled for tomorrow at 10 AM.</p>",
    )
    print(f"Sent email: {message_id}")

# Run async operation
asyncio.run(send_team_update(agent))
```

## Agent Module Refactoring (New Structure)

The agent module has been refactored into three self-contained modules followin' the Bricks & Studs pattern:

### Module Structure

**config.py** (~85 LOC)
- Configuration management
- Worker identity construction
- No external dependencies

**core.py** (~250 LOC)
- Agent lifecycle coordination
- Recipient management
- M365 operation delegation

**m365_integration.py** (~193 LOC)
- M365 Graph API client factory
- Async client initialization
- Credential management

### Benefits

✅ **Modular**: Each module has one clear responsibility
✅ **Testable**: Smaller modules be easier to test in isolation
✅ **Maintainable**: Changes be localized to specific modules
✅ **Regeneratable**: Each module can be rebuilt from specification
✅ **Backward Compatible**: Old imports still work via facade

### Migration

**No changes required!** The facade in `agent/__init__.py` maintains backward compatibility:

```python
# Old imports (still work)
from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerAgent,
    KnowledgeWorkerConfig,
)

# New imports (recommended)
from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
```

See [agent/README.md](agent/README.md) fer detailed module documentation.

## Worker Personas

Knowledge workers simulate different roles with specific activity patterns:

| Persona | Description | Typical Activities |
|---------|-------------|-------------------|
| ENGINEERING | Software developers | Code reviews, sprint planning, technical discussions |
| SALES | Sales representatives | Customer calls, proposals, pipeline updates |
| MARKETING | Marketing team | Campaign planning, content reviews, analytics |
| EXECUTIVE | Leadership team | Strategic planning, approvals, cross-team coordination |
| SUPPORT | Customer support | Ticket management, customer communication, escalations |

### Activity Patterns

Each persona has realistic activity frequencies and types:
- **Engineering**: Heavy email, calendar meetings, Teams channels
- **Sales**: CRM updates, customer calls, proposal emails
- **Marketing**: Document collaboration, email campaigns, calendar planning
- **Executive**: Strategic emails, high-priority meetings, cross-team communication
- **Support**: Rapid email responses, ticket tracking, knowledge base updates

## M365 Integration

### Prerequisites

Install Microsoft Graph SDK dependencies:

```bash
pip install msgraph-sdk azure-identity
```

### Authentication

The module uses client secret authentication with environment variables:

```bash
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-client-secret"
export KW_TENANT_ID="your-tenant-id"
```

**Security Note:** Credentials be NEVER stored in config files or code. They be loaded from environment variables at runtime.

### Graceful Degradation

If M365 SDK not be installed or credentials be missin', the agent gracefully degrades:
- Logs warnings about missin' dependencies
- Returns None fer M365 operations
- Continues runnin' without crashin'

This allows testin' and development without full M365 setup.

## Communication Safety

### Internal-Only Validation

All communication be validated to ensure it stays within the tenant boundary:

```python
from azure_haymaker.knowledge_worker.operations.validators import CommunicationValidator

validator = CommunicationValidator(
    tenant_domain="tenant.onmicrosoft.com",
    allowed_upns={"user1@tenant.com", "user2@tenant.com"},
)

# Validate recipient
if validator.is_internal("user@tenant.onmicrosoft.com"):
    print("✅ Internal recipient - allowed")
else:
    print("❌ External recipient - blocked")
```

### Orchestrator Integration

The orchestrator typically manages allowed recipients:

```python
# Orchestrator discovers all workers
all_workers = orchestrator.get_all_workers()

# Add them as allowed recipients fer each agent
for agent in agents:
    agent.add_allowed_recipients([w.email for w in all_workers])
```

This ensures workers can only communicate with other workers in the same deployment.

## Worker Configuration

### Required Fields

```python
KnowledgeWorkerConfig(
    worker_id="kw-abc12345-engi-001",      # Unique identifier
    display_name="Alex Developer",          # Display name in M365
    department="engineering",               # Department name
    persona="engineering",                  # Worker persona type
    tenant_domain="tenant.onmicrosoft.com", # M365 tenant domain
)
```

### Optional Fields

```python
KnowledgeWorkerConfig(
    # ... required fields ...
    team_id="team-123",                     # Team ID
    team_name="Platform Team",              # Team name
    activity_types=["email", "calendar"],   # Activity types to perform
    activity_frequency_minutes=30,          # Minutes between activities
    endpoint_type="cli_container",          # "cli_container" or "cloud_pc"
    endpoint_id="endpoint-456",             # Endpoint identifier
    m365_app_id="app-123",                  # M365 app ID (or use env var)
    m365_cert_thumbprint="cert-789",        # Cert thumbprint
)
```

### Auto-Generated Fields

- `name`: Auto-generated as `"knowledge-worker-{worker_id}"` if not provided
- `goal`: Auto-generated from display_name if not provided

## Operations

### Email Operations

```python
# Send email
message_id = await agent.send_email(
    to=["recipient@tenant.com"],
    subject="Project Update",
    body="<p>Project on track fer Q1 delivery.</p>",
    cc=["manager@tenant.com"],
)
```

### Calendar Operations

```python
# Create calendar event
event_id = await agent.create_calendar_event(
    subject="Sprint Planning",
    start_time="2026-01-21T10:00:00Z",
    end_time="2026-01-21T11:00:00Z",
    attendees=["team@tenant.com"],
    body="Sprint planning fer Q1 roadmap",
    is_online_meeting=True,  # Creates Teams meeting
)
```

## Testing

### Run Tests

```bash
# Run all knowledge worker tests
pytest tests/knowledge_worker/

# Run specific module tests
pytest tests/knowledge_worker/agent/test_config.py
pytest tests/knowledge_worker/agent/test_core.py
pytest tests/knowledge_worker/agent/test_m365_integration.py
```

### Test Structure

```
tests/knowledge_worker/
├── agent/
│   ├── test_config.py           # Configuration tests
│   ├── test_core.py             # Agent lifecycle tests
│   └── test_m365_integration.py # M365 client tests
├── models/
│   └── test_worker.py           # Model tests
└── operations/
    ├── test_email.py            # Email operation tests
    ├── test_calendar.py         # Calendar operation tests
    └── test_validators.py       # Validator tests
```

## Agent Statistics

Get agent state and statistics:

```python
stats = agent.get_worker_stats()
print(stats)
# Output:
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

## Documentation

### Module Documentation

- [Agent Module README](agent/README.md) - Module structure and quick start
- [Agent Module Refactoring Guide](../../docs/knowledge_worker/agent_module_refactoring.md) - Detailed refactorin' documentation
- [Module Docstrings](../../docs/knowledge_worker/MODULE_DOCSTRINGS.md) - Module-level documentation

### API Reference

- [KnowledgeWorkerConfig API](../../docs/reference/knowledge_worker_config.md)
- [KnowledgeWorkerAgent API](../../docs/reference/knowledge_worker_agent.md)
- [M365 Operations API](../../docs/reference/m365_operations.md)

### Patterns

- [Bricks & Studs Pattern](../../.claude/context/PATTERNS.md#bricks--studs-module-design)
- [Zero-BS Implementation](../../.claude/context/PATTERNS.md#zero-bs-implementation)

## Examples

See [examples/](../../examples/knowledge_worker/) fer complete examples:

- `basic_agent.py` - Basic agent setup and execution
- `email_workflow.py` - Email send/receive workflow
- `calendar_workflow.py` - Calendar event management
- `multi_worker_simulation.py` - Multiple workers interactin'

## Troubleshooting

### M365 Client Not Initialized

```python
RuntimeError: M365 client not initialized. Call on_start() first.
```

**Solution:** Ensure `agent.run()` be called, or manually call `agent.on_start()` before operations.

### Missing Credentials

```
M365 client not initialized: Missing credentials
```

**Solution:** Set environment variables:
```bash
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-client-secret"
export KW_TENANT_ID="your-tenant-id"
```

### External Recipient Blocked

```
Email blocked: Recipient external@example.com not in allowed list
```

**Solution:** Add recipients to allowed list:
```python
agent.add_allowed_recipient("external@example.com")
```

Or verify recipient be internal to tenant.

## Contributing

When contributin' to the knowledge_worker module:

1. Follow the Bricks & Studs pattern
2. Keep modules self-contained
3. Add tests fer new functionality
4. Update documentation
5. Ensure backward compatibility

See [CONTRIBUTING.md](../../CONTRIBUTING.md) fer detailed guidelines.

---

**Module Version:** 1.0.0
**Refactoring Date:** 2026-01-20
**Pattern:** Bricks & Studs
**Python Version:** 3.11+
