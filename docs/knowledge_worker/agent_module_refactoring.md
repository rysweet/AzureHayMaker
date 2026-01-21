# Knowledge Worker Agent Module Refactoring

Comprehensive reference fer the refactored knowledge_worker agent modules followin' the Bricks & Studs pattern.

## Overview

The knowledge_worker agent has been refactored from a single monolithic file (529 LOC) into three self-contained modules:

- **config.py** (~85 LOC): Configuration and identity management
- **core.py** (~250 LOC): Agent lifecycle and operations
- **m365_integration.py** (~193 LOC): Microsoft 365 API integration

This refactorin' follows the **Bricks & Studs** philosophy where each module be a self-contained brick with clear public contracts (studs).

## Module Architecture

```
knowledge_worker/agent/
├── __init__.py          # Facade for backward compatibility
├── config.py            # Configuration brick
├── core.py              # Core agent brick
├── m365_integration.py  # M365 integration brick
└── README.md            # This documentation
```

### Dependency Flow

```
config.py (no dependencies)
    ↓
core.py (depends on config)
    ↓
m365_integration.py (depends on config, used by core)
```

## Module: config.py

### Responsibility

Configuration management and worker identity construction.

### Philosophy

- Single responsibility: Configuration and identity
- Standard library only (dataclasses, logging)
- Self-contained and regeneratable
- No M365 dependencies

### Public API

```python
"""Configuration module for knowledge worker agents.

Philosophy:
- Single responsibility: Configuration and identity
- Standard library only (dataclasses, logging)
- Self-contained and regeneratable
- No M365 dependencies

Public API (the "studs"):
    KnowledgeWorkerConfig: Configuration dataclass
    build_worker_identity: Identity factory function
"""

__all__ = ["KnowledgeWorkerConfig", "build_worker_identity"]
```

### KnowledgeWorkerConfig

Configuration dataclass extendin' AgentConfig with knowledge worker-specific settings.

**Key Attributes:**
- `worker_id`: Unique worker identifier
- `display_name`: Display name in Entra
- `department`: Department/team name
- `persona`: Worker persona type
- `team_id`, `team_name`: Team membership
- `activity_types`, `activity_frequency_minutes`: Activity configuration
- `endpoint_type`, `endpoint_id`: Endpoint configuration
- `m365_app_id`, `m365_cert_thumbprint`, `tenant_domain`: M365 credentials

**Auto-generated Fields:**
- `name`: Auto-generated from worker_id if empty
- `goal`: Auto-generated from display_name if empty

### build_worker_identity()

Factory function to construct WorkerIdentity from configuration.

**Signature:**
```python
def build_worker_identity(config: KnowledgeWorkerConfig) -> WorkerIdentity:
    """Build WorkerIdentity from configuration.

    Args:
        config: Knowledge worker configuration

    Returns:
        WorkerIdentity model populated from config
    """
```

**Behavior:**
- Maps persona string to enum (defaults to ENGINEERING on unknown)
- Maps endpoint type string to enum (defaults to CLI_CONTAINER)
- Handles team_ids list conversion
- Logs warnings on invalid persona

### Usage Example

```python
from azure_haymaker.knowledge_worker.agent.config import (
    KnowledgeWorkerConfig,
    build_worker_identity,
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

# Build identity from config
identity = build_worker_identity(config)

print(f"Worker: {identity.display_name}")
print(f"Persona: {identity.persona}")
# Output:
# Worker: Alex Developer
# Persona: WorkerPersona.ENGINEERING
```

## Module: core.py

### Responsibility

Core agent lifecycle management and operation coordination.

### Philosophy

- Single responsibility: Agent lifecycle
- Delegates M365 operations to m365_integration
- Coordinates validator and operations modules
- Pure business logic - no M365 SDK imports

### Public API

```python
"""Core knowledge worker agent implementation.

Philosophy:
- Single responsibility: Agent lifecycle
- Delegates M365 operations to m365_integration
- Coordinates validator and operations modules
- Pure business logic - no M365 SDK imports

Public API (the "studs"):
    KnowledgeWorkerAgent: Main agent class
"""

__all__ = ["KnowledgeWorkerAgent"]
```

### KnowledgeWorkerAgent

Base class fer knowledge worker activity agents extendin' AgentBase.

**Lifecycle Methods:**
1. `on_start()`: Initialize M365 client and load allowed recipients
2. `on_execute()`: Execute scheduled activities
3. `on_cleanup()`: Disconnect M365 client and report metrics

**Key Methods:**

**Initialization:**
```python
def __init__(
    self,
    worker_config: KnowledgeWorkerConfig,
    worker_identity: WorkerIdentity | None = None,
    activity_config: WorkerConfig | None = None,
    prompt_path: Path | None = None,
)
```

**Recipient Management:**
```python
def add_allowed_recipient(self, recipient: str) -> None
def add_allowed_recipients(self, recipients: list[str]) -> None
def get_allowed_recipients(self) -> list[str]
def validate_recipient(self, recipient: str) -> bool
```

**M365 Operations (async):**
```python
async def send_email(
    self,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
) -> str | None

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

**State Inspection:**
```python
def get_worker_stats(self) -> dict[str, Any]
```

### Usage Example

```python
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig

# Create and configure agent
config = KnowledgeWorkerConfig(
    worker_id="kw-abc12345-engi-001",
    display_name="Alex Developer",
    department="engineering",
    persona="engineering",
    tenant_domain="tenant.onmicrosoft.com",
)

agent = KnowledgeWorkerAgent(config)

# Add allowed recipients (orchestrator typically does this)
agent.add_allowed_recipients([
    "user1@tenant.onmicrosoft.com",
    "user2@tenant.onmicrosoft.com",
])

# Run agent lifecycle
exit_code = agent.run()

# Check stats
stats = agent.get_worker_stats()
print(f"Recipients: {stats['allowed_recipients_count']}")
# Output: Recipients: 2
```

## Module: m365_integration.py

### Responsibility

Microsoft 365 Graph API client initialization and async operations.

### Philosophy

- Single responsibility: M365 API integration
- Isolates all M365 SDK dependencies
- Factory pattern fer client creation
- Async-first API design

### Public API

```python
"""Microsoft 365 integration module.

Philosophy:
- Single responsibility: M365 API integration
- Isolates all M365 SDK dependencies
- Factory pattern fer client creation
- Async-first API design

Public API (the "studs"):
    M365ClientFactory: Client factory class
    initialize_m365_client: Client initialization function
"""

__all__ = ["M365ClientFactory", "initialize_m365_client"]
```

### M365ClientFactory

Factory class fer creatin' Microsoft Graph API clients.

**Methods:**
```python
@staticmethod
def create(
    app_id: str | None = None,
    client_secret: str | None = None,
    tenant_id: str | None = None,
) -> Any
```

**Environment Variables:**
- `KW_APP_ID`: M365 application client ID
- `KW_CLIENT_SECRET`: Client secret fer authentication
- `KW_TENANT_ID`: Azure tenant ID

**Behavior:**
- Falls back to environment variables if parameters not provided
- Raises ValueError if credentials missin'
- Returns configured Graph client

### initialize_m365_client()

Helper function to initialize M365 client with error handlin'.

**Signature:**
```python
def initialize_m365_client(
    worker_id: str,
    app_id: str | None = None,
    client_secret: str | None = None,
    tenant_id: str | None = None,
) -> Any | None
```

**Returns:**
- Configured M365 client on success
- None if SDK not installed or credentials missin'

**Error Handling:**
- Logs ImportError if Graph SDK not installed
- Logs ValueError if credentials missin'
- Logs generic exceptions

### Usage Example

```python
from azure_haymaker.knowledge_worker.agent.m365_integration import (
    M365ClientFactory,
    initialize_m365_client,
)

# Option 1: Factory with explicit credentials
client = M365ClientFactory.create(
    app_id="app-123",
    client_secret="secret-456",
    tenant_id="tenant-789",
)

# Option 2: Helper with environment variables
client = initialize_m365_client(
    worker_id="kw-abc12345-engi-001"
)

# Option 3: None if credentials missing (graceful degradation)
if client is None:
    print("M365 client not available")
```

## Backward Compatibility

The `agent.py` file now serves as a **facade** that re-exports all public APIs from the refactored modules.

### agent/__init__.py

```python
"""Knowledge Worker Agent - Backward compatible facade.

This module re-exports all public APIs from the refactored modules
to maintain backward compatibility with existing code.

For new code, import from specific modules:
- config: KnowledgeWorkerConfig, build_worker_identity
- core: KnowledgeWorkerAgent
- m365_integration: M365ClientFactory, initialize_m365_client
"""

from .config import KnowledgeWorkerConfig, build_worker_identity
from .core import KnowledgeWorkerAgent
from .m365_integration import M365ClientFactory, initialize_m365_client

__all__ = [
    "KnowledgeWorkerConfig",
    "KnowledgeWorkerAgent",
    "build_worker_identity",
    "M365ClientFactory",
    "initialize_m365_client",
]
```

### Old Import (still works)

```python
from azure_haymaker.knowledge_worker.agent import KnowledgeWorkerAgent, KnowledgeWorkerConfig
```

### New Import (recommended)

```python
from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
```

## Migration Guide

### No Changes Required

If ye be importin' from `knowledge_worker.agent`, no changes be needed. The facade maintains full backward compatibility.

### Optional: Migrate to Module-Specific Imports

Fer better code clarity and faster imports, migrate to module-specific imports:

**Before:**
```python
from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerAgent,
    KnowledgeWorkerConfig,
)
```

**After:**
```python
from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
```

**Benefits:**
- Faster imports (only load modules ye need)
- Clearer dependencies
- Better IDE autocomplete

## Testing

Each module has its own test file followin' the same structure:

```
tests/knowledge_worker/agent/
├── test_config.py           # Tests fer config.py
├── test_core.py             # Tests fer core.py
└── test_m365_integration.py # Tests fer m365_integration.py
```

### Test Strategy

- **config.py**: Unit tests fer identity construction and validation
- **core.py**: Integration tests with mocked M365 client
- **m365_integration.py**: Unit tests with mocked Graph SDK

## Benefits of Refactorin'

### Modularity
- Each module has one clear responsibility
- Easy to understand and maintain
- Can be regenerated independently

### Testability
- Smaller modules be easier to test
- Clear boundaries fer mockin'
- Isolated test failures

### Maintainability
- Changes be localized to specific modules
- Easier to review and debug
- Clear dependency flow

### Regeneratability
- Each module can be rebuilt from this specification
- Standard public APIs (studs) remain stable
- Internal implementation can change

## Related Documentation

- [Bricks & Studs Pattern](../../.claude/context/PATTERNS.md#bricks--studs-module-design)
- [Knowledge Worker Models](../reference/knowledge_worker_models.md)
- [M365 Operations](../reference/m365_operations.md)

---

**Last Updated:** 2026-01-20
**Refactoring Issue:** #287
**Module Count:** 3 (config, core, m365_integration)
**Total LOC Reduction:** 529 → 528 (improved organization, same functionality)
