# Knowledge Worker Agent Modules

Self-contained modules fer knowledge worker agent functionality followin' the Bricks & Studs pattern.

## Architecture

This directory contains three independent modules that work together:

```
agent/
├── __init__.py          # Backward-compatible facade
├── config.py            # Configuration brick (~85 LOC)
├── core.py              # Core agent brick (~250 LOC)
└── m365_integration.py  # M365 integration brick (~193 LOC)
```

## Module Responsibilities

### config.py - Configuration & Identity

**What it does:** Configuration management and worker identity construction.

**Key classes:**
- `KnowledgeWorkerConfig`: Configuration dataclass
- `build_worker_identity()`: Factory function fer identity creation

**Dependencies:** Standard library only (dataclasses, logging)

**Use when:** Ye need to create or configure a knowledge worker agent

```python
from azure_haymaker.knowledge_worker.agent.config import (
    KnowledgeWorkerConfig,
    build_worker_identity,
)

config = KnowledgeWorkerConfig(
    worker_id="kw-abc12345-engi-001",
    display_name="Alex Developer",
    department="engineering",
    persona="engineering",
    tenant_domain="tenant.onmicrosoft.com",
)
```

### core.py - Agent Lifecycle

**What it does:** Core agent lifecycle management and operation coordination.

**Key classes:**
- `KnowledgeWorkerAgent`: Main agent class with lifecycle methods

**Dependencies:** config.py, operations modules, validators

**Use when:** Ye be runnin' a knowledge worker agent

```python
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent

agent = KnowledgeWorkerAgent(config)
agent.add_allowed_recipients(["user@tenant.com"])
exit_code = agent.run()
```

### m365_integration.py - Microsoft 365 Integration

**What it does:** M365 Graph API client initialization and factory.

**Key classes:**
- `M365ClientFactory`: Factory fer creatin' Graph clients
- `initialize_m365_client()`: Helper with error handlin'

**Dependencies:** azure-identity, msgraph-sdk (optional)

**Use when:** Ye need direct access to M365 Graph client

```python
from azure_haymaker.knowledge_worker.agent.m365_integration import (
    M365ClientFactory,
)

client = M365ClientFactory.create()
```

## Dependency Flow

```
config.py (standalone)
    ↓
core.py (uses config)
    ↓
m365_integration.py (uses config, called by core)
```

Each module be independent and can be regenerated from its specification without breakin' the others.

## Quick Start

### Basic Usage

```python
# Import from facade (backward compatible)
from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerConfig,
    KnowledgeWorkerAgent,
)

# Create config
config = KnowledgeWorkerConfig(
    worker_id="kw-test-001",
    display_name="Test Worker",
    department="engineering",
    persona="engineering",
    tenant_domain="tenant.onmicrosoft.com",
)

# Create and run agent
agent = KnowledgeWorkerAgent(config)
exit_code = agent.run()
```

### Module-Specific Imports (Recommended)

```python
# Import from specific modules fer better clarity
from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
from azure_haymaker.knowledge_worker.agent.m365_integration import M365ClientFactory

# Use as before
config = KnowledgeWorkerConfig(...)
agent = KnowledgeWorkerAgent(config)
```

## Public APIs (The Studs)

Each module exports specific public APIs via `__all__`:

**config.py:**
- `KnowledgeWorkerConfig`
- `build_worker_identity`

**core.py:**
- `KnowledgeWorkerAgent`

**m365_integration.py:**
- `M365ClientFactory`
- `initialize_m365_client`

## Backward Compatibility

The `__init__.py` file re-exports all public APIs, maintainin' full backward compatibility:

```python
# Old imports still work
from azure_haymaker.knowledge_worker.agent import KnowledgeWorkerAgent

# New module-specific imports also work
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
```

## Testing

Each module has dedicated tests:

```
tests/knowledge_worker/agent/
├── test_config.py
├── test_core.py
└── test_m365_integration.py
```

Run tests:
```bash
pytest tests/knowledge_worker/agent/
```

## Philosophy

These modules follow the **Bricks & Studs** pattern:

- **Brick**: Self-contained module with ONE responsibility
- **Stud**: Public contract (`__all__` exports) others connect to
- **Regeneratable**: Can be rebuilt from spec without breakin' connections

Key principles:
- Single responsibility per module
- Standard library when possible (config.py)
- Clear public APIs via `__all__`
- No circular dependencies
- Isolated tests

## Related Documentation

- [Module Refactoring Guide](../../../docs/knowledge_worker/agent_module_refactoring.md)
- [Bricks & Studs Pattern](../../../.claude/context/PATTERNS.md)
- [Knowledge Worker Overview](../README.md)

---

**Module Count:** 3
**Total LOC:** ~528 (was 529 in monolithic file)
**Pattern:** Bricks & Studs
**Backward Compatible:** Yes
