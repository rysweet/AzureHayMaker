"""Unit tests for Computer Use Workflows.

This module tests the workflow classes that define browser-based M365 operations
for Computer Use Knowledge Worker Agents.

Tests cover:
- EmailWorkflow: Sending emails via Outlook Web
- TeamsMessageWorkflow: Sending Teams messages
- CalendarWorkflow: Creating calendar events
- Workflow validation and parameter checking
- Error handling and retries
- Workflow composition and chaining

Uses pytest with mocks for browser automation.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

# Import the module under test
# Note: These imports will fail until workflows are implemented
try:
    from azure_haymaker.knowledge_worker.computer_use.workflows import (
        CalendarWorkflow,
        EmailWorkflow,
        TeamsMessageWorkflow,
        WorkflowError,
        WorkflowValidationError,
    )
    from azure_haymaker.knowledge_worker.computer_use.browser_automation import (
        BrowserAutomation,
    )

    WORKFLOWS_AVAILABLE = True
except ImportError:
    WORKFLOWS_AVAILABLE = False
    EmailWorkflow = None
    TeamsMessageWorkflow = None
    CalendarWorkflow = None
    WorkflowError = None
    WorkflowValidationError = None
    BrowserAutomation = None


pytestmark = pytest.mark.skipif(
    not WORKFLOWS_AVAILABLE, reason="Workflows not yet implemented"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_browser():
    """Fixture: Mock browser automation."""
    browser = MagicMock(spec=BrowserAutomation)
    browser.is_authenticated = True
    browser.navigate_to_outlook_web = AsyncMock()
    browser.navigate_to_teams_web = AsyncMock()
    browser.send_email_via_browser = AsyncMock(return_value={"success": True})
    browser.send_teams_message_via_browser = AsyncMock(return_value={"success": True})
    browser.create_calendar_event_via_browser = AsyncMock(
        return_value={"success": True}
    )
    return browser


@pytest.fixture
def email_workflow(mock_browser):
    """Fixture: EmailWorkflow instance."""
    return EmailWorkflow(browser=mock_browser)


@pytest.fixture
def teams_workflow(mock_browser):
    """Fixture: TeamsMessageWorkflow instance."""
    return TeamsMessageWorkflow(browser=mock_browser)


@pytest.fixture
def calendar_workflow(mock_browser):
    """Fixture: CalendarWorkflow instance."""
    return CalendarWorkflow(browser=mock_browser)


# ==============================================================================
# EMAIL WORKFLOW TESTS
# ==============================================================================


class TestEmailWorkflow:
    """Tests for EmailWorkflow."""

    @pytest.mark.asyncio
    async def test_execute_email_workflow_success(self, email_workflow, mock_browser):
        """Test successful email workflow execution."""
        # Arrange
        params = {
            "to": "recipient@tenant.com",
            "subject": "Test Email",
            "body": "This is a test email.",
        }

        # Act
        result = await email_workflow.execute(**params)

        # Assert
        assert result["success"] is True
        assert result["workflow"] == "email"
        mock_browser.navigate_to_outlook_web.assert_called_once()
        mock_browser.send_email_via_browser.assert_called_once_with(
            to=params["to"], subject=params["subject"], body=params["body"]
        )

    @pytest.mark.asyncio
    async def test_execute_email_workflow_missing_recipient(self, email_workflow):
        """Test email workflow fails with missing recipient."""
        # Arrange
        params = {
            "to": "",  # Missing recipient
            "subject": "Test",
            "body": "Test",
        }

        # Act & Assert
        with pytest.raises(WorkflowValidationError) as exc_info:
            await email_workflow.execute(**params)
        assert "recipient" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_email_workflow_missing_subject(self, email_workflow):
        """Test email workflow fails with missing subject."""
        # Arrange
        params = {
            "to": "recipient@tenant.com",
            "subject": "",  # Missing subject
            "body": "Test",
        }

        # Act & Assert
        with pytest.raises(WorkflowValidationError) as exc_info:
            await email_workflow.execute(**params)
        assert "subject" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_email_workflow_with_browser_error(
        self, email_workflow, mock_browser
    ):
        """Test email workflow handles browser errors."""
        # Arrange
        mock_browser.send_email_via_browser.side_effect = Exception("Browser error")
        params = {
            "to": "recipient@tenant.com",
            "subject": "Test",
            "body": "Test",
        }

        # Act & Assert
        with pytest.raises(WorkflowError) as exc_info:
            await email_workflow.execute(**params)
        assert "browser" in str(exc_info.value).lower()


# ==============================================================================
# TEAMS WORKFLOW TESTS
# ==============================================================================


class TestTeamsMessageWorkflow:
    """Tests for TeamsMessageWorkflow."""

    @pytest.mark.asyncio
    async def test_execute_teams_workflow_success(self, teams_workflow, mock_browser):
        """Test successful Teams message workflow execution."""
        # Arrange
        params = {
            "channel": "General",
            "message": "Hello team!",
        }

        # Act
        result = await teams_workflow.execute(**params)

        # Assert
        assert result["success"] is True
        assert result["workflow"] == "teams_message"
        mock_browser.navigate_to_teams_web.assert_called_once()
        mock_browser.send_teams_message_via_browser.assert_called_once_with(
            channel=params["channel"], message=params["message"]
        )

    @pytest.mark.asyncio
    async def test_execute_teams_workflow_missing_channel(self, teams_workflow):
        """Test Teams workflow fails with missing channel."""
        # Arrange
        params = {
            "channel": "",  # Missing channel
            "message": "Test message",
        }

        # Act & Assert
        with pytest.raises(WorkflowValidationError) as exc_info:
            await teams_workflow.execute(**params)
        assert "channel" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_teams_workflow_missing_message(self, teams_workflow):
        """Test Teams workflow fails with missing message."""
        # Arrange
        params = {
            "channel": "General",
            "message": "",  # Missing message
        }

        # Act & Assert
        with pytest.raises(WorkflowValidationError) as exc_info:
            await teams_workflow.execute(**params)
        assert "message" in str(exc_info.value).lower()


# ==============================================================================
# CALENDAR WORKFLOW TESTS
# ==============================================================================


class TestCalendarWorkflow:
    """Tests for CalendarWorkflow."""

    @pytest.mark.asyncio
    async def test_execute_calendar_workflow_success(
        self, calendar_workflow, mock_browser
    ):
        """Test successful calendar event creation workflow."""
        # Arrange
        params = {
            "subject": "Team Meeting",
            "start_time": "2024-12-01T10:00:00Z",
            "end_time": "2024-12-01T11:00:00Z",
            "attendees": ["attendee1@tenant.com", "attendee2@tenant.com"],
        }

        # Act
        result = await calendar_workflow.execute(**params)

        # Assert
        assert result["success"] is True
        assert result["workflow"] == "calendar"
        mock_browser.navigate_to_outlook_web.assert_called_once()
        mock_browser.create_calendar_event_via_browser.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_calendar_workflow_missing_subject(self, calendar_workflow):
        """Test calendar workflow fails with missing subject."""
        # Arrange
        params = {
            "subject": "",  # Missing subject
            "start_time": "2024-12-01T10:00:00Z",
            "end_time": "2024-12-01T11:00:00Z",
        }

        # Act & Assert
        with pytest.raises(WorkflowValidationError) as exc_info:
            await calendar_workflow.execute(**params)
        assert "subject" in str(exc_info.value).lower()


# ==============================================================================
# WORKFLOW COMPOSITION TESTS
# ==============================================================================


class TestWorkflowComposition:
    """Tests for workflow composition and chaining."""

    @pytest.mark.asyncio
    async def test_execute_multiple_workflows_sequence(
        self, email_workflow, teams_workflow, mock_browser
    ):
        """Test executing multiple workflows in sequence."""
        # Act
        email_result = await email_workflow.execute(
            to="recipient@tenant.com", subject="Test", body="Test"
        )
        teams_result = await teams_workflow.execute(
            channel="General", message="Email sent!"
        )

        # Assert
        assert email_result["success"] is True
        assert teams_result["success"] is True
        # Should navigate to each service
        mock_browser.navigate_to_outlook_web.assert_called()
        mock_browser.navigate_to_teams_web.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
