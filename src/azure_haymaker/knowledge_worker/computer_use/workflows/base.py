"""Base Workflow for Computer Use Knowledge Worker Agents.

Provides abstract base class for browser-based M365 workflows.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from azure_haymaker.knowledge_worker.computer_use.security_utils import sanitize_error

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Raised when workflow execution fails."""

    pass


class WorkflowValidationError(WorkflowError):
    """Raised when workflow parameters are invalid."""

    pass


class BaseWorkflow(ABC):
    """Abstract base class for browser-based workflows.

    All Computer Use workflows extend this class and implement
    the execute() method for their specific M365 operation.

    Attributes:
        browser: BrowserAutomation instance for M365 operations
        workflow_name: Name of the workflow
    """

    def __init__(self, browser: Any, workflow_name: str = "base"):
        """Initialize base workflow.

        Args:
            browser: BrowserAutomation instance
            workflow_name: Name of this workflow
        """
        self.browser = browser
        self.workflow_name = workflow_name
        logger.debug(f"Workflow '{workflow_name}' initialized")

    @abstractmethod
    async def execute(self, **params: Any) -> dict[str, Any]:
        """Execute the workflow.

        Subclasses must implement this method to perform their
        specific M365 operation via browser automation.

        Args:
            **params: Workflow-specific parameters

        Returns:
            Dict with execution result containing at least:
                - success: Whether workflow succeeded
                - workflow: Workflow name

        Raises:
            WorkflowValidationError: If parameters are invalid
            WorkflowError: If workflow execution fails
        """
        pass

    def _validate_required_params(self, params: dict[str, Any], required: list[str]) -> None:
        """Validate required parameters are present and non-empty.

        Args:
            params: Parameter dictionary to validate
            required: List of required parameter names

        Raises:
            WorkflowValidationError: If any required parameter is missing or empty
        """
        # Map technical param names to user-friendly names
        param_display_names = {
            "to": "recipient",
            "channel": "channel",
            "message": "message",
            "subject": "subject",
            "body": "body",
            "start_time": "start_time",
            "end_time": "end_time",
        }

        for param_name in required:
            value = params.get(param_name)
            if not value or (isinstance(value, str) and not value.strip()):
                display_name = param_display_names.get(param_name, param_name)
                raise WorkflowValidationError(
                    f"Required parameter '{display_name}' is missing or empty"
                )

    async def _handle_workflow_error(self, error: Exception, operation: str) -> None:
        """Handle workflow errors with logging.

        Args:
            error: The error that occurred
            operation: Operation that failed

        Raises:
            WorkflowError: Always raises with context
        """
        sanitized_error = sanitize_error(str(error))
        logger.error(f"{self.workflow_name} - {operation} failed: {sanitized_error}")
        raise WorkflowError(f"{operation} failed: {error}") from error
