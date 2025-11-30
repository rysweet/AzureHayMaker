"""Teams Message Workflow for Computer Use Knowledge Worker Agents.

Sends Teams messages via Teams Web browser automation.
"""

import logging
from typing import Any

from azure_haymaker.knowledge_worker.computer_use.browser_automation import (
    BrowserAutomation,
)
from azure_haymaker.knowledge_worker.computer_use.workflows.base import (
    BaseWorkflow,
)

logger = logging.getLogger(__name__)


class TeamsMessageWorkflow(BaseWorkflow):
    """Send Teams message via Teams Web.

    Workflow for sending messages to Teams channels through
    browser automation of Teams Web interface.

    Example:
        >>> browser = BrowserAutomation()
        >>> await browser.launch_browser()
        >>> await browser.login_m365("user@tenant.com", "password")
        >>> workflow = TeamsMessageWorkflow(browser=browser)
        >>> result = await workflow.execute(
        ...     channel="General",
        ...     message="Hello team!"
        ... )

    Attributes:
        browser: BrowserAutomation instance
        workflow_name: Always "teams_message"
    """

    def __init__(self, browser: BrowserAutomation):
        """Initialize Teams message workflow.

        Args:
            browser: BrowserAutomation instance
        """
        super().__init__(browser=browser, workflow_name="teams_message")

    async def execute(
        self,
        channel: str,
        message: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute Teams message sending workflow.

        Args:
            channel: Teams channel name
            message: Message text to send
            **kwargs: Additional parameters (ignored)

        Returns:
            Dict with keys:
                - success: Whether message was sent
                - workflow: "teams_message"
                - message: Status message

        Raises:
            WorkflowValidationError: If required parameters are invalid
            WorkflowError: If message sending fails
        """
        # Validate parameters
        self._validate_required_params(
            params={"channel": channel, "message": message},
            required=["channel", "message"],
        )

        try:
            logger.info(f"TeamsMessageWorkflow: Sending message to channel '{channel}'")

            # Navigate to Teams Web
            await self.browser.navigate_to_teams_web()

            # Send message via browser
            result = await self.browser.send_teams_message_via_browser(
                channel=channel,
                message=message,
            )

            logger.info(f"TeamsMessageWorkflow: Message sent successfully to '{channel}'")

            return {
                "success": result.get("success", True),
                "workflow": "teams_message",
                "message": result.get("message", "Teams message sent successfully"),
            }

        except Exception as e:
            await self._handle_workflow_error(e, "Teams message sending")
