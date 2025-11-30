"""Unit tests for BrowserAutomation class.

This module tests the BrowserAutomation class that controls Playwright browser
sessions for Computer Use Knowledge Worker Agents on Windows VMs.

Tests cover:
- Browser launch and configuration
- Azure AD / M365 authentication
- Navigation to M365 services (Outlook, Teams)
- Email sending via browser
- Teams messaging via browser
- Error handling and retry logic
- Browser cleanup and session management
- Screenshot capture for debugging

Uses pytest with mocks for Playwright interactions.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import the module under test
# Note: These imports will fail until BrowserAutomation is implemented
try:
    from azure_haymaker.knowledge_worker.computer_use.browser_automation import (
        BrowserAutomation,
        BrowserAutomationError,
        LoginError,
        NavigationError,
    )

    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False
    BrowserAutomation = None
    BrowserAutomationError = None
    LoginError = None
    NavigationError = None


pytestmark = pytest.mark.skipif(
    not BROWSER_AVAILABLE, reason="BrowserAutomation not yet implemented"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_playwright():
    """Fixture: Mock Playwright instance with browser."""
    with patch("azure_haymaker.knowledge_worker.computer_use.browser_automation.async_playwright") as mock:
        playwright = AsyncMock()
        browser = AsyncMock()
        context = AsyncMock()
        page = AsyncMock()

        # Setup Playwright hierarchy
        mock.return_value.__aenter__.return_value = playwright
        playwright.chromium.launch.return_value = browser
        browser.new_context.return_value = context
        context.new_page.return_value = page

        # Mock page methods
        page.goto = AsyncMock()
        page.fill = AsyncMock()
        page.click = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.screenshot = AsyncMock()
        page.title.return_value = "Microsoft 365"

        yield {
            "playwright": playwright,
            "browser": browser,
            "context": context,
            "page": page,
        }


@pytest.fixture
def credentials():
    """Fixture: M365 credentials."""
    return {
        "username": "test.worker@tenant.onmicrosoft.com",
        "password": "SecureP@ssw0rd123!",
        "tenant_id": "tenant-123",
    }


@pytest.fixture
def browser_automation():
    """Fixture: BrowserAutomation instance."""
    return BrowserAutomation(headless=True, screenshot_on_error=True)


# ==============================================================================
# BROWSER LAUNCH TESTS
# ==============================================================================


class TestBrowserLaunch:
    """Tests for browser launch and initialization."""

    @pytest.mark.asyncio
    async def test_launch_browser_success(self, browser_automation, mock_playwright):
        """Test successful browser launch."""
        # Act
        await browser_automation.launch_browser()

        # Assert
        assert browser_automation.is_browser_running is True
        mock_playwright["playwright"].chromium.launch.assert_called_once()
        mock_playwright["browser"].new_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_launch_browser_with_custom_options(self, mock_playwright):
        """Test browser launch with custom configuration."""
        # Arrange
        browser = BrowserAutomation(
            headless=False,
            viewport_width=1920,
            viewport_height=1080,
            user_agent="CustomAgent/1.0",
        )

        # Act
        await browser.launch_browser()

        # Assert
        launch_call = mock_playwright["playwright"].chromium.launch.call_args
        assert launch_call.kwargs["headless"] is False

        context_call = mock_playwright["browser"].new_context.call_args
        assert context_call.kwargs["viewport"]["width"] == 1920
        assert context_call.kwargs["viewport"]["height"] == 1080
        assert "CustomAgent" in context_call.kwargs.get("user_agent", "")

    @pytest.mark.asyncio
    async def test_launch_browser_failure(self, browser_automation, mock_playwright):
        """Test browser launch handles Playwright errors."""
        # Arrange
        mock_playwright["playwright"].chromium.launch.side_effect = Exception(
            "Failed to launch browser"
        )

        # Act & Assert
        with pytest.raises(BrowserAutomationError) as exc_info:
            await browser_automation.launch_browser()
        assert "launch" in str(exc_info.value).lower()
        assert browser_automation.is_browser_running is False

    @pytest.mark.asyncio
    async def test_launch_browser_idempotent(self, browser_automation, mock_playwright):
        """Test launch_browser is idempotent."""
        # Act
        await browser_automation.launch_browser()
        await browser_automation.launch_browser()  # Second call

        # Assert - should only launch once
        assert mock_playwright["playwright"].chromium.launch.call_count == 1


# ==============================================================================
# AUTHENTICATION TESTS
# ==============================================================================


class TestM365Authentication:
    """Tests for M365 authentication."""

    @pytest.mark.asyncio
    async def test_login_m365_success(
        self, browser_automation, credentials, mock_playwright
    ):
        """Test successful M365 login."""
        # Arrange
        await browser_automation.launch_browser()
        page = mock_playwright["page"]

        # Mock successful login flow
        page.wait_for_selector.side_effect = [
            AsyncMock(),  # Username field
            AsyncMock(),  # Password field
            AsyncMock(),  # Stay signed in
            AsyncMock(),  # Login success indicator
        ]

        # Act
        await browser_automation.login_m365(
            username=credentials["username"], password=credentials["password"]
        )

        # Assert
        assert browser_automation.is_authenticated is True
        page.fill.assert_any_call('input[type="email"]', credentials["username"])
        page.fill.assert_any_call('input[type="password"]', credentials["password"])
        page.click.assert_called()  # Submit button clicked

    @pytest.mark.asyncio
    async def test_login_m365_invalid_credentials(
        self, browser_automation, credentials, mock_playwright
    ):
        """Test M365 login with invalid credentials."""
        # Arrange
        await browser_automation.launch_browser()
        page = mock_playwright["page"]

        # Mock login failure - error message appears
        page.wait_for_selector.side_effect = Exception("Error: Invalid credentials")

        # Act & Assert
        with pytest.raises(LoginError) as exc_info:
            await browser_automation.login_m365(
                username="invalid@tenant.com", password="wrongpass"
            )
        assert "credential" in str(exc_info.value).lower()
        assert browser_automation.is_authenticated is False

    @pytest.mark.asyncio
    async def test_login_m365_without_browser(self, browser_automation, credentials):
        """Test login_m365 fails if browser not launched."""
        # Act & Assert
        with pytest.raises(BrowserAutomationError) as exc_info:
            await browser_automation.login_m365(
                username=credentials["username"], password=credentials["password"]
            )
        assert "browser" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_login_m365_with_mfa(
        self, browser_automation, credentials, mock_playwright
    ):
        """Test M365 login handles MFA prompts."""
        # Arrange
        await browser_automation.launch_browser()
        page = mock_playwright["page"]

        # Mock MFA flow
        page.wait_for_selector.side_effect = [
            AsyncMock(),  # Username
            AsyncMock(),  # Password
            AsyncMock(),  # MFA prompt
            AsyncMock(),  # MFA code input
            AsyncMock(),  # Success
        ]

        # Act
        await browser_automation.login_m365(
            username=credentials["username"],
            password=credentials["password"],
            mfa_code="123456",
        )

        # Assert
        assert browser_automation.is_authenticated is True
        # Should handle MFA input
        assert page.fill.call_count >= 3  # Username, password, MFA code


# ==============================================================================
# NAVIGATION TESTS
# ==============================================================================


class TestM365Navigation:
    """Tests for navigation to M365 services."""

    @pytest.mark.asyncio
    async def test_navigate_to_outlook_web(
        self, browser_automation, credentials, mock_playwright
    ):
        """Test navigation to Outlook Web."""
        # Arrange
        await browser_automation.launch_browser()
        await browser_automation.login_m365(
            username=credentials["username"], password=credentials["password"]
        )
        page = mock_playwright["page"]
        page.title.return_value = "Outlook"

        # Act
        await browser_automation.navigate_to_outlook_web()

        # Assert
        page.goto.assert_called_with(
            "https://outlook.office.com/mail/", wait_until="networkidle"
        )
        assert browser_automation.current_service == "outlook"

    @pytest.mark.asyncio
    async def test_navigate_to_teams_web(
        self, browser_automation, credentials, mock_playwright
    ):
        """Test navigation to Teams Web."""
        # Arrange
        await browser_automation.launch_browser()
        await browser_automation.login_m365(
            username=credentials["username"], password=credentials["password"]
        )
        page = mock_playwright["page"]
        page.title.return_value = "Microsoft Teams"

        # Act
        await browser_automation.navigate_to_teams_web()

        # Assert
        page.goto.assert_called_with(
            "https://teams.microsoft.com", wait_until="networkidle"
        )
        assert browser_automation.current_service == "teams"

    @pytest.mark.asyncio
    async def test_navigate_without_authentication(
        self, browser_automation, mock_playwright
    ):
        """Test navigation fails without authentication."""
        # Arrange
        await browser_automation.launch_browser()

        # Act & Assert
        with pytest.raises(BrowserAutomationError) as exc_info:
            await browser_automation.navigate_to_outlook_web()
        assert "authenticat" in str(exc_info.value).lower()


# ==============================================================================
# EMAIL OPERATION TESTS
# ==============================================================================


class TestEmailOperations:
    """Tests for email sending via browser."""

    @pytest.mark.asyncio
    async def test_send_email_via_browser_success(
        self, browser_automation, credentials, mock_playwright
    ):
        """Test successful email send via Outlook Web."""
        # Arrange
        await browser_automation.launch_browser()
        await browser_automation.login_m365(
            username=credentials["username"], password=credentials["password"]
        )
        await browser_automation.navigate_to_outlook_web()

        page = mock_playwright["page"]
        page.wait_for_selector.return_value = AsyncMock()

        # Act
        result = await browser_automation.send_email_via_browser(
            to="recipient@tenant.com",
            subject="Test Email",
            body="This is a test email.",
        )

        # Assert
        assert result["success"] is True
        # Check New mail button was clicked (with timeout parameter)
        new_mail_calls = [call for call in page.click.call_args_list if "New mail" in str(call)]
        assert len(new_mail_calls) >= 1
        page.fill.assert_any_call('[aria-label="To"]', "recipient@tenant.com")
        page.fill.assert_any_call('[aria-label="Subject"]', "Test Email")
        # Send button clicked
        send_calls = [call for call in page.click.call_args_list if "Send" in str(call)]
        assert len(send_calls) >= 1

    @pytest.mark.asyncio
    async def test_send_email_with_timeout(
        self, browser_automation, credentials, mock_playwright
    ):
        """Test send_email_via_browser respects timeout."""
        # Arrange
        await browser_automation.launch_browser()
        await browser_automation.login_m365(
            username=credentials["username"], password=credentials["password"]
        )
        await browser_automation.navigate_to_outlook_web()

        page = mock_playwright["page"]
        page.wait_for_selector.side_effect = TimeoutError("Selector timeout")

        # Act & Assert
        with pytest.raises(BrowserAutomationError) as exc_info:
            await browser_automation.send_email_via_browser(
                to="recipient@tenant.com",
                subject="Test",
                body="Test",
                timeout=5,
            )
        assert "timeout" in str(exc_info.value).lower()


# ==============================================================================
# TEAMS OPERATION TESTS
# ==============================================================================


class TestTeamsOperations:
    """Tests for Teams messaging via browser."""

    @pytest.mark.asyncio
    async def test_send_teams_message_via_browser_success(
        self, browser_automation, credentials, mock_playwright
    ):
        """Test successful Teams message send."""
        # Arrange
        await browser_automation.launch_browser()
        await browser_automation.login_m365(
            username=credentials["username"], password=credentials["password"]
        )
        await browser_automation.navigate_to_teams_web()

        page = mock_playwright["page"]
        page.wait_for_selector.return_value = AsyncMock()

        # Act
        result = await browser_automation.send_teams_message_via_browser(
            channel="General", message="Hello team!"
        )

        # Assert
        assert result["success"] is True
        # Should navigate to channel
        page.click.assert_any_call(f'[aria-label*="General"]')
        # Should type and send message
        page.fill.assert_called()
        assert page.click.call_count >= 2  # Channel + Send


# ==============================================================================
# CLEANUP TESTS
# ==============================================================================


class TestBrowserCleanup:
    """Tests for browser cleanup and session management."""

    @pytest.mark.asyncio
    async def test_close_browser_success(self, browser_automation, mock_playwright):
        """Test successful browser close."""
        # Arrange
        await browser_automation.launch_browser()

        # Act
        await browser_automation.close_browser()

        # Assert
        assert browser_automation.is_browser_running is False
        mock_playwright["browser"].close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_browser_idempotent(self, browser_automation, mock_playwright):
        """Test close_browser is safe to call multiple times."""
        # Arrange
        await browser_automation.launch_browser()

        # Act
        await browser_automation.close_browser()
        await browser_automation.close_browser()  # Second call

        # Assert - should only close once
        assert mock_playwright["browser"].close.call_count == 1

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, mock_playwright):
        """Test BrowserAutomation works as async context manager."""
        # Act
        async with BrowserAutomation() as browser:
            await browser.launch_browser()
            assert browser.is_browser_running is True

        # Assert - browser closed automatically
        mock_playwright["browser"].close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
