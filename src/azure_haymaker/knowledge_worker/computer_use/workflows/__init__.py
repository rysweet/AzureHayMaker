"""Computer Use Workflows.

Browser-based workflow implementations for M365 operations.
"""

from azure_haymaker.knowledge_worker.computer_use.workflows.base import (
    BaseWorkflow,
    WorkflowError,
    WorkflowValidationError,
)
from azure_haymaker.knowledge_worker.computer_use.workflows.calendar_workflow import (
    CalendarWorkflow,
)
from azure_haymaker.knowledge_worker.computer_use.workflows.email_workflow import (
    EmailWorkflow,
)
from azure_haymaker.knowledge_worker.computer_use.workflows.teams_workflow import (
    TeamsMessageWorkflow,
)

__all__ = [
    "BaseWorkflow",
    "WorkflowError",
    "WorkflowValidationError",
    "EmailWorkflow",
    "TeamsMessageWorkflow",
    "CalendarWorkflow",
]
