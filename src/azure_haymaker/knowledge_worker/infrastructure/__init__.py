"""Infrastructure setup for Knowledge Worker Activity Framework.

Provides utilities for creating and configuring the Azure Entra app
registration required for Knowledge Worker operations.
"""

from azure_haymaker.knowledge_worker.infrastructure.app_setup import (
    KWAppConfig,
    KWAppSetup,
    setup_kw_app,
)

__all__ = [
    "KWAppConfig",
    "KWAppSetup",
    "setup_kw_app",
]
