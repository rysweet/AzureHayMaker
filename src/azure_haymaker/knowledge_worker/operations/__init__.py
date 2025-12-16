"""M365 Operations for Knowledge Worker Activity Framework.

Provides modules for performing M365 activities with built-in
communication safety controls.
"""

from azure_haymaker.knowledge_worker.operations.base import M365OperationBase
from azure_haymaker.knowledge_worker.operations.calendar import CalendarOperations
from azure_haymaker.knowledge_worker.operations.documents import DocumentOperations
from azure_haymaker.knowledge_worker.operations.email import EmailOperations
from azure_haymaker.knowledge_worker.operations.teams import TeamsOperations
from azure_haymaker.knowledge_worker.operations.validators import (
    CommunicationValidator,
    ExternalRecipientError,
)

__all__ = [
    # Base
    "M365OperationBase",
    # Operations
    "CalendarOperations",
    "DocumentOperations",
    "EmailOperations",
    "TeamsOperations",
    # Validators
    "CommunicationValidator",
    "ExternalRecipientError",
]
