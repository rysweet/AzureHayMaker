"""M365 Operations for Knowledge Worker Activity Framework.

Provides modules for performing M365 activities with built-in
communication safety controls.
"""

from azure_haymaker.knowledge_worker.operations.base import M365OperationBase
from azure_haymaker.knowledge_worker.operations.validators import (
    CommunicationValidator,
    ExternalRecipientError,
)

__all__ = [
    "CommunicationValidator",
    "ExternalRecipientError",
    "M365OperationBase",
]
