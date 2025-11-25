"""Identity management for Knowledge Worker Activity Framework.

Provides Entra ID user and group management for provisioning
simulated knowledge workers.
"""

from azure_haymaker.knowledge_worker.identity.user_manager import EntraUserManager
from azure_haymaker.knowledge_worker.identity.group_manager import EntraGroupManager
from azure_haymaker.knowledge_worker.identity.transport_rules import (
    TransportRuleManager,
)

__all__ = [
    "EntraUserManager",
    "EntraGroupManager",
    "TransportRuleManager",
]
