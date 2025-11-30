"""Calendar Workflow for Computer Use Knowledge Worker Agents.

Creates calendar events via Outlook Web browser automation.
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


class CalendarWorkflow(BaseWorkflow):
    """Create calendar event via Outlook Web.

    Workflow for creating calendar events through browser automation
    of Outlook Web interface.

    Example:
        >>> browser = BrowserAutomation()
        >>> await browser.launch_browser()
        >>> await browser.login_m365("user@tenant.com", "password")
        >>> workflow = CalendarWorkflow(browser=browser)
        >>> result = await workflow.execute(
        ...     subject="Team Meeting",
        ...     start_time="2024-12-01T10:00:00Z",
        ...     end_time="2024-12-01T11:00:00Z",
        ...     attendees=["user1@tenant.com", "user2@tenant.com"]
        ... )

    Attributes:
        browser: BrowserAutomation instance
        workflow_name: Always "calendar"
    """

    def __init__(self, browser: BrowserAutomation):
        """Initialize calendar workflow.

        Args:
            browser: BrowserAutomation instance
        """
        super().__init__(browser=browser, workflow_name="calendar")

    async def execute(
        self,
        subject: str,
        start_time: str,
        end_time: str,
        attendees: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute calendar event creation workflow.

        Args:
            subject: Event subject/title
            start_time: Event start time (ISO format)
            end_time: Event end time (ISO format)
            attendees: Optional list of attendee email addresses
            **kwargs: Additional parameters (ignored)

        Returns:
            Dict with keys:
                - success: Whether event was created
                - workflow: "calendar"
                - message: Status message

        Raises:
            WorkflowValidationError: If required parameters are invalid
            WorkflowError: If event creation fails
        """
        # Validate parameters
        self._validate_required_params(
            params={"subject": subject, "start_time": start_time, "end_time": end_time},
            required=["subject", "start_time", "end_time"],
        )

        try:
            logger.info(f"CalendarWorkflow: Creating event '{subject}'")

            # Navigate to Outlook Web (calendar access point)
            await self.browser.navigate_to_outlook_web()

            # Create calendar event via browser
            result = await self.browser.create_calendar_event_via_browser(
                subject=subject,
                start_time=start_time,
                end_time=end_time,
                attendees=attendees or [],
            )

            logger.info(f"CalendarWorkflow: Event '{subject}' created successfully")

            return {
                "success": result.get("success", True),
                "workflow": "calendar",
                "message": result.get("message", "Calendar event created successfully"),
            }

        except Exception as e:
            await self._handle_workflow_error(e, "Calendar event creation")
