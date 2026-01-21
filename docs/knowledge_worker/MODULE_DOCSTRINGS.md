# Module Docstrings for Refactored Agent Modules

This document contains the module-level docstrings fer each of the three refactored agent modules. These will be placed at the top of each module file.

## config.py Module Docstring

```python
"""Configuration module for knowledge worker agents.

This module provides configuration management and worker identity construction
followin' the Bricks & Studs pattern. It be self-contained with no external
dependencies beyond the standard library.

Philosophy:
- Single responsibility: Configuration and identity management
- Standard library only (dataclasses, logging, no M365 dependencies)
- Self-contained and regeneratable
- No business logic - pure data structures and simple transformations

Public API (the "studs"):
    KnowledgeWorkerConfig: Configuration dataclass extending AgentConfig
    build_worker_identity: Factory function to construct WorkerIdentity from config

Usage:
    >>> from azure_haymaker.knowledge_worker.agent.config import (
    ...     KnowledgeWorkerConfig,
    ...     build_worker_identity,
    ... )
    >>> config = KnowledgeWorkerConfig(
    ...     worker_id="kw-abc12345-engi-001",
    ...     display_name="Alex Developer",
    ...     department="engineering",
    ...     persona="engineering",
    ...     tenant_domain="tenant.onmicrosoft.com",
    ... )
    >>> identity = build_worker_identity(config)
    >>> print(f"Worker: {identity.display_name}")
    Worker: Alex Developer

Module Structure:
    - KnowledgeWorkerConfig: Extends AgentConfig with worker-specific fields
    - build_worker_identity(): Converts config to WorkerIdentity model
    - Auto-generation of name/goal from worker_id/display_name
    - Enum mapping fer persona and endpoint_type

Dependencies:
    - dataclasses (standard library)
    - logging (standard library)
    - azure_haymaker.agent_base.AgentConfig (parent config)
    - azure_haymaker.knowledge_worker.models.worker (data models)

See Also:
    - core.py: Core agent lifecycle management
    - m365_integration.py: M365 API integration
    - README.md: Module overview and quick start
"""
```

## core.py Module Docstring

```python
"""Core knowledge worker agent implementation.

This module provides the main KnowledgeWorkerAgent class that coordinates
agent lifecycle, recipient management, and M365 operations. It delegates
M365 client initialization to m365_integration.py and operation execution
to the operations modules.

Philosophy:
- Single responsibility: Agent lifecycle coordination
- Delegates M365 operations to m365_integration module
- Coordinates validator and operations modules
- Pure business logic - no direct M365 SDK imports
- Async-first design fer M365 operations

Public API (the "studs"):
    KnowledgeWorkerAgent: Main agent class extending AgentBase

Usage:
    >>> from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
    >>> from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
    >>>
    >>> config = KnowledgeWorkerConfig(
    ...     worker_id="kw-abc12345-engi-001",
    ...     display_name="Alex Developer",
    ...     department="engineering",
    ...     persona="engineering",
    ...     tenant_domain="tenant.onmicrosoft.com",
    ... )
    >>>
    >>> agent = KnowledgeWorkerAgent(config)
    >>> agent.add_allowed_recipients([
    ...     "user1@tenant.onmicrosoft.com",
    ...     "user2@tenant.onmicrosoft.com",
    ... ])
    >>> exit_code = agent.run()

Lifecycle:
    1. on_start() - Initialize M365 client and load allowed recipients
    2. on_execute() - Execute scheduled activities (default implementation)
    3. on_cleanup() - Disconnect M365 client and report metrics

Key Responsibilities:
    - Agent lifecycle management (start, execute, cleanup)
    - Recipient validation and management
    - M365 client initialization coordination
    - Communication validator setup
    - Stats collection and reporting
    - Async M365 operations (email, calendar)

Module Structure:
    - KnowledgeWorkerAgent: Main agent class
    - Lifecycle methods: on_start(), on_execute(), on_cleanup()
    - Recipient methods: add_allowed_recipient(), validate_recipient()
    - M365 operations: send_email(), create_calendar_event()
    - State inspection: get_worker_stats(), get_allowed_recipients()

Dependencies:
    - azure_haymaker.agent_base.AgentBase (parent class)
    - .config: KnowledgeWorkerConfig, build_worker_identity
    - .m365_integration: M365 client initialization
    - operations.validators: CommunicationValidator
    - operations: EmailOperations, CalendarOperations (imported on use)

See Also:
    - config.py: Configuration and identity management
    - m365_integration.py: M365 client factory
    - operations/: Email, calendar, teams operations
    - README.md: Module overview and quick start
"""
```

## m365_integration.py Module Docstring

```python
"""Microsoft 365 integration module for knowledge worker agents.

This module provides M365 Graph API client initialization and factory methods.
It isolates all M365 SDK dependencies and provides graceful degradation when
the SDK be not installed.

Philosophy:
- Single responsibility: M365 API client creation
- Isolates all M365 SDK dependencies (msgraph-sdk, azure-identity)
- Factory pattern fer client creation
- Graceful degradation when SDK not installed
- Environment variable support fer credentials

Public API (the "studs"):
    M365ClientFactory: Factory class fer creatin' Graph clients
    initialize_m365_client: Helper function with error handlin'

Usage:
    >>> from azure_haymaker.knowledge_worker.agent.m365_integration import (
    ...     M365ClientFactory,
    ...     initialize_m365_client,
    ... )
    >>>
    >>> # Option 1: Factory with explicit credentials
    >>> client = M365ClientFactory.create(
    ...     app_id="app-123",
    ...     client_secret="secret-456",
    ...     tenant_id="tenant-789",
    ... )
    >>>
    >>> # Option 2: Helper with environment variables
    >>> client = initialize_m365_client(
    ...     worker_id="kw-abc12345-engi-001"
    ... )
    >>>
    >>> # Option 3: Graceful degradation
    >>> if client is None:
    ...     print("M365 client not available")

Environment Variables:
    KW_APP_ID: M365 application client ID
    KW_CLIENT_SECRET: Client secret fer authentication
    KW_TENANT_ID: Azure tenant ID

Module Structure:
    - M365ClientFactory: Static factory fer client creation
    - initialize_m365_client(): Helper with error handlin' and loggin'
    - Credential fallback: Parameters → Environment variables
    - Error handlin': ImportError, ValueError, generic exceptions

Security:
    Credentials be loaded from environment variables (KW_APP_ID, KW_CLIENT_SECRET,
    KW_TENANT_ID) and NEVER stored in config files or plaintext. The factory
    connects to Microsoft Graph using client secret credentials.

Dependencies:
    - logging (standard library)
    - os (standard library)
    - azure.identity.ClientSecretCredential (optional)
    - msgraph.GraphServiceClient (optional)

Error Handling:
    - ImportError: Logs warning if Graph SDK not installed
    - ValueError: Logs debug if credentials missin'
    - Exception: Logs error fer unexpected failures
    - Returns None on any error (graceful degradation)

See Also:
    - config.py: Configuration management
    - core.py: Agent lifecycle that uses this module
    - README.md: Module overview and quick start
"""
```

## __init__.py Facade Docstring

```python
"""Knowledge Worker Agent - Backward compatible facade.

This module re-exports all public APIs from the refactored modules to maintain
backward compatibility with existing code. It serves as a facade that preserves
the original import paths while delegatin' to the new modular structure.

Public API (the "studs"):
    KnowledgeWorkerConfig: Configuration dataclass (from config.py)
    KnowledgeWorkerAgent: Main agent class (from core.py)
    build_worker_identity: Identity factory function (from config.py)
    M365ClientFactory: M365 client factory (from m365_integration.py)
    initialize_m365_client: M365 client helper (from m365_integration.py)

Backward Compatibility:
    Old imports continue to work unchanged:
    >>> from azure_haymaker.knowledge_worker.agent import (
    ...     KnowledgeWorkerAgent,
    ...     KnowledgeWorkerConfig,
    ... )

New Module-Specific Imports (Recommended):
    Fer better code clarity and faster imports, use module-specific imports:
    >>> from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
    >>> from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
    >>> from azure_haymaker.knowledge_worker.agent.m365_integration import M365ClientFactory

Migration:
    No changes be required to existing code. The facade maintains full backward
    compatibility. New code should prefer module-specific imports fer clarity.

Module Structure:
    agent/
    ├── __init__.py          # This facade
    ├── config.py            # Configuration brick
    ├── core.py              # Core agent brick
    └── m365_integration.py  # M365 integration brick

See Also:
    - README.md: Module overview and quick start
    - config.py: Configuration documentation
    - core.py: Agent lifecycle documentation
    - m365_integration.py: M365 integration documentation
"""
```

## Usage in Module Files

These docstrings should be placed at the very top of each module file, right after any copyright headers and before any imports.

Example fer config.py:

```python
"""Configuration module for knowledge worker agents.

This module provides configuration management and worker identity construction
followin' the Bricks & Studs pattern...
[full docstring as above]
"""

import logging
from dataclasses import dataclass, field
from azure_haymaker.agent_base import AgentConfig
# ... rest of imports

# ... module code
```

## Docstring Standards

All module docstrings follow these standards:

1. **First line**: Brief one-sentence summary
2. **Philosophy section**: Core design principles
3. **Public API section**: What gets exported via `__all__`
4. **Usage section**: Realistic code examples with output
5. **Module Structure section**: Key classes/functions
6. **Dependencies section**: What this module imports
7. **See Also section**: Links to related documentation

This ensures each module be self-documentin' and follows the Diataxis framework (reference documentation type).
