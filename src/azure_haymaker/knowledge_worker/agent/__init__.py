"""Knowledge Worker Agent - Backward compatible facade.

This module re-exports all public APIs from the refactored modules to maintain
backward compatibility with existing code. It serves as a facade that preserves
the original import paths while delegating to the new modular structure.

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
    For better code clarity and faster imports, use module-specific imports:
    >>> from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
    >>> from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
    >>> from azure_haymaker.knowledge_worker.agent.m365_integration import M365ClientFactory

Migration:
    No changes are required to existing code. The facade maintains full backward
    compatibility. New code should prefer module-specific imports for clarity.

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
