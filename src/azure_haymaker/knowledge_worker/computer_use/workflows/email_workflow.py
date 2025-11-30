"""Email Workflow for Computer Use Knowledge Worker Agents.

Sends emails via Outlook Web browser automation.
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


class EmailWorkflow(BaseWorkflow):
    """Send email via Outlook Web.

    Workflow for sending emails through browser automation of
    Outlook Web interface.

    Example:
        >>> browser = BrowserAutomation()
        >>> await browser.launch_browser()
        >>> await browser.login_m365("user@tenant.com", "password")
        >>> workflow = EmailWorkflow(browser=browser)
        >>> result = await workflow.execute(
        ...     to="recipient@tenant.com",
        ...     subject="Test Email",
        ...     body="Hello from Computer Use agent!"
        ... )

    Attributes:
        browser: BrowserAutomation instance
        workflow_name: Always "email"
    """

    def __init__(self, browser: BrowserAutomation):
        """Initialize email workflow.

        Args:
            browser: BrowserAutomation instance
        """
        super().__init__(browser=browser, workflow_name="email")

    async def execute(
        self,
        to: str,
        subject: str,
        body: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute email sending workflow.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            **kwargs: Additional parameters (ignored)

        Returns:
            Dict with keys:
                - success: Whether email was sent
                - workflow: "email"
                - message: Status message

        Raises:
            WorkflowValidationError: If required parameters are invalid
            WorkflowError: If email sending fails
        """
        # Validate parameters
        self._validate_required_params(
            params={"to": to, "subject": subject, "body": body},
            required=["to", "subject", "body"],
        )

        try:
            logger.info(f"EmailWorkflow: Sending email to {to}")

            # Navigate to Outlook Web
            await self.browser.navigate_to_outlook_web()

            # Send email via browser
            result = await self.browser.send_email_via_browser(
                to=to,
                subject=subject,
                body=body,
            )

            logger.info(f"EmailWorkflow: Email sent successfully to {to}")

            return {
                "success": result.get("success", True),
                "workflow": "email",
                "message": result.get("message", "Email sent successfully"),
            }

        except Exception as e:
            await self._handle_workflow_error(e, "Email sending")
