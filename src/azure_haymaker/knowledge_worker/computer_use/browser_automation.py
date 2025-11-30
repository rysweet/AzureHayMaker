"""Browser Automation Module for Computer Use Knowledge Worker Agents.

This module provides Playwright-based browser automation for M365 web applications
including Outlook, Teams, and Calendar.

Key features:
- Chromium browser control via Playwright
- Azure AD / M365 authentication handling
- Email sending via Outlook Web
- Teams messaging via Teams Web
- Calendar event creation
- Screenshot capture for debugging
"""

import logging
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .security_utils import sanitize_error

logger = logging.getLogger(__name__)


class BrowserAutomationError(Exception):
    """Raised when browser automation fails."""

    pass


class LoginError(BrowserAutomationError):
    """Raised when M365 login fails."""

    pass


class NavigationError(BrowserAutomationError):
    """Raised when navigation to M365 service fails."""

    pass


class BrowserAutomation:
    """Browser automation for M365 web applications.

    Manages Playwright browser sessions for Computer Use agents to interact
    with M365 services via web interfaces.

    Example:
        >>> browser = BrowserAutomation(headless=True)
        >>> await browser.launch_browser()
        >>> await browser.login_m365("user@tenant.com", "password")
        >>> await browser.navigate_to_outlook_web()
        >>> result = await browser.send_email_via_browser(
        ...     to="recipient@tenant.com",
        ...     subject="Test",
        ...     body="Hello!"
        ... )
        >>> await browser.close_browser()

    Or use as async context manager:
        >>> async with BrowserAutomation() as browser:
        ...     await browser.launch_browser()
        ...     await browser.login_m365("user@tenant.com", "password")

    Attributes:
        headless: Whether to run browser in headless mode
        is_browser_running: Whether browser is currently running
        is_authenticated: Whether user is authenticated to M365
        current_service: Current M365 service name (outlook, teams, etc)
    """

    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        user_agent: str | None = None,
        screenshot_on_error: bool = False,
        timeout: int = 30000,
    ):
        """Initialize BrowserAutomation.

        Args:
            headless: Run browser in headless mode
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            user_agent: Custom user agent string
            screenshot_on_error: Capture screenshots on errors
            timeout: Default timeout in milliseconds
        """
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.screenshot_on_error = screenshot_on_error
        self.timeout = timeout

        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        self.is_browser_running = False
        self.is_authenticated = False
        self.current_service: str | None = None

        logger.info(
            f"BrowserAutomation initialized (headless={headless}, viewport={viewport_width}x{viewport_height})"
        )

    async def launch_browser(self) -> None:
        """Launch Playwright browser.

        Starts Chromium browser with configured settings.

        Raises:
            BrowserAutomationError: If browser launch fails
        """
        if self.is_browser_running:
            logger.debug("Browser already running, skipping launch")
            return

        try:
            logger.info("Launching Chromium browser")

            # Start Playwright
            playwright_context = async_playwright()
            self._playwright = await playwright_context.__aenter__()

            # Launch browser
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )

            # Create context
            self._context = await self._browser.new_context(
                viewport={
                    "width": self.viewport_width,
                    "height": self.viewport_height,
                },
                user_agent=self.user_agent,
                locale="en-US",
            )

            # Create page
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self.timeout)

            self.is_browser_running = True
            logger.info("Browser launched successfully")

        except Exception as e:
            self.is_browser_running = False
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Failed to launch browser: {sanitized_error}")
            raise BrowserAutomationError(f"Browser launch failed: {sanitized_error}") from e

    async def login_m365(
        self,
        username: str,
        password: str,
        mfa_code: str | None = None,
    ) -> None:
        """Login to Microsoft 365.

        Handles Azure AD authentication flow including optional MFA.

        Args:
            username: M365 username (UPN)
            password: M365 password
            mfa_code: Optional MFA code for 2FA

        Raises:
            BrowserAutomationError: If browser not running
            LoginError: If authentication fails
        """
        if not self.is_browser_running or not self._page:
            raise BrowserAutomationError("Browser not running. Call launch_browser() first.")

        try:
            logger.info(f"Logging in to M365 as {username[:3]}***")

            # Navigate to M365 portal
            await self._page.goto("https://portal.office.com", wait_until="networkidle")

            # Wait for and fill username
            await self._page.wait_for_selector('input[type="email"]', timeout=10000)
            await self._page.fill('input[type="email"]', username)
            await self._page.click('input[type="submit"]')

            # Wait for and fill password
            await self._page.wait_for_selector('input[type="password"]', timeout=10000)
            await self._page.fill('input[type="password"]', password)
            await self._page.click('input[type="submit"]')

            # Handle "Stay signed in?" prompt
            try:
                await self._page.wait_for_selector('input[type="submit"]', timeout=5000)
                await self._page.click('input[type="submit"]')
            except TimeoutError:
                logger.debug("No 'Stay signed in' prompt (timeout)")

            # Handle MFA if needed
            if mfa_code:
                logger.debug("Handling MFA")
                try:
                    await self._page.wait_for_selector('input[name="otc"]', timeout=5000)
                    await self._page.fill('input[name="otc"]', mfa_code)
                    await self._page.click('input[type="submit"]')
                except Exception as e:
                    sanitized_error = sanitize_error(str(e))
                    logger.warning(f"MFA not required or failed: {sanitized_error}")

            # Wait for successful login (portal loads)
            await self._page.wait_for_selector('[data-automationid="AppLauncher"]', timeout=15000)

            self.is_authenticated = True
            logger.info("M365 login successful")

        except Exception as e:
            self.is_authenticated = False
            sanitized_error = sanitize_error(str(e))
            logger.error(f"M365 login failed: {sanitized_error}")

            if "timeout" in str(e).lower():
                raise LoginError("Login timeout - check credentials or MFA") from e
            elif "credential" in str(e).lower() or "password" in str(e).lower():
                raise LoginError("Invalid credentials") from e
            else:
                raise LoginError(f"Login failed: {sanitized_error}") from e

    async def navigate_to_outlook_web(self) -> None:
        """Navigate to Outlook Web (OWA).

        Raises:
            BrowserAutomationError: If not authenticated
            NavigationError: If navigation fails
        """
        if not self.is_authenticated:
            raise BrowserAutomationError("Not authenticated. Call login_m365() first.")

        try:
            logger.info("Navigating to Outlook Web")
            await self._page.goto(
                "https://outlook.office.com/mail/", wait_until="networkidle"
            )

            # Wait for mail interface to load
            await self._page.wait_for_selector('[role="main"]', timeout=15000)

            self.current_service = "outlook"
            logger.info("Navigation to Outlook Web successful")

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Failed to navigate to Outlook Web: {sanitized_error}")
            raise NavigationError(f"Outlook navigation failed: {sanitized_error}") from e

    async def navigate_to_teams_web(self) -> None:
        """Navigate to Microsoft Teams Web.

        Raises:
            BrowserAutomationError: If not authenticated
            NavigationError: If navigation fails
        """
        if not self.is_authenticated:
            raise BrowserAutomationError("Not authenticated. Call login_m365() first.")

        try:
            logger.info("Navigating to Teams Web")
            await self._page.goto("https://teams.microsoft.com", wait_until="networkidle")

            # Wait for Teams interface to load
            await self._page.wait_for_selector('[data-tid="team-channel-list"]', timeout=15000)

            self.current_service = "teams"
            logger.info("Navigation to Teams Web successful")

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Failed to navigate to Teams Web: {sanitized_error}")
            raise NavigationError(f"Teams navigation failed: {sanitized_error}") from e

    async def send_email_via_browser(
        self,
        to: str,
        subject: str,
        body: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Send email via Outlook Web.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            timeout: Optional timeout override in ms

        Returns:
            Dict with keys:
                - success: Whether email was sent
                - message: Status message

        Raises:
            BrowserAutomationError: If current service is not Outlook
        """
        if self.current_service != "outlook":
            raise BrowserAutomationError(
                "Not on Outlook Web. Call navigate_to_outlook_web() first."
            )

        timeout_ms = timeout or self.timeout

        try:
            logger.info(f"Sending email to {to}")

            # Click "New mail" button
            await self._page.click('[aria-label="New mail"]', timeout=timeout_ms)

            # Fill recipient, subject, and body
            await self._page.fill('[aria-label="To"]', to)
            await self._page.fill('[aria-label="Subject"]', subject)

            # Fill body and send
            body_selector = '[role="textbox"][aria-label*="message"]'
            await self._page.wait_for_selector(body_selector, timeout=timeout_ms)
            await self._page.fill(body_selector, body)
            await self._page.click('[aria-label="Send"]')

            # Wait for send to complete (message compose window closes)
            try:
                await self._page.wait_for_selector(
                    '[aria-label="New mail"]',
                    state="visible",
                    timeout=5000
                )
            except TimeoutError:
                logger.debug("Send confirmation not detected, continuing")

            logger.info(f"Email sent successfully to {to}")

            return {
                "success": True,
                "message": f"Email sent to {to}",
            }

        except TimeoutError as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Email send timeout: {sanitized_error}")
            raise BrowserAutomationError(f"Email send timeout: {sanitized_error}") from e
        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Failed to send email: {sanitized_error}")
            raise BrowserAutomationError(f"Email send failed: {sanitized_error}") from e

    async def send_teams_message_via_browser(
        self,
        channel: str,
        message: str,
    ) -> dict[str, Any]:
        """Send message to Teams channel.

        Args:
            channel: Channel name
            message: Message text

        Returns:
            Dict with keys:
                - success: Whether message was sent
                - message: Status message

        Raises:
            BrowserAutomationError: If current service is not Teams
        """
        if self.current_service != "teams":
            raise BrowserAutomationError(
                "Not on Teams Web. Call navigate_to_teams_web() first."
            )

        try:
            logger.info(f"Sending Teams message to channel: {channel}")

            # Click on channel and send message
            channel_selector = f'[aria-label*="{channel}"]'
            await self._page.click(channel_selector)

            # Find message compose box and send
            compose_selector = '[role="textbox"][data-tid="ckeditor"]'
            await self._page.wait_for_selector(compose_selector, timeout=10000)
            await self._page.fill(compose_selector, message)
            await self._page.click('[data-tid="send-message-button"]')

            # Wait for message to appear in channel (send complete)
            await self._page.wait_for_load_state("networkidle", timeout=5000)

            logger.info(f"Teams message sent to {channel}")

            return {
                "success": True,
                "message": f"Message sent to {channel}",
            }

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Failed to send Teams message: {sanitized_error}")
            raise BrowserAutomationError(f"Teams message send failed: {sanitized_error}") from e

    async def create_calendar_event_via_browser(
        self,
        subject: str,
        start_time: str,
        end_time: str,
        attendees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create calendar event via Outlook Web.

        Args:
            subject: Event subject
            start_time: Event start time (ISO format)
            end_time: Event end time (ISO format)
            attendees: Optional list of attendee emails

        Returns:
            Dict with keys:
                - success: Whether event was created
                - message: Status message
        """
        # Navigate to Calendar if not already there
        if self.current_service != "outlook":
            await self.navigate_to_outlook_web()

        try:
            logger.info(f"Creating calendar event: {subject}")

            # Click Calendar tab and create event
            await self._page.click('[aria-label="Calendar"]')
            await self._page.click('[aria-label="New event"]')

            # Fill event details and save
            await self._page.fill('[aria-label="Add a title"]', subject)

            if attendees:
                attendees_str = "; ".join(attendees)
                await self._page.fill('[aria-label="Invite attendees"]', attendees_str)

            await self._page.click('[aria-label="Save"]')

            # Wait for event to be saved and dialog to close
            await self._page.wait_for_load_state("networkidle", timeout=5000)

            logger.info("Calendar event created successfully")

            return {
                "success": True,
                "message": f"Event '{subject}' created",
            }

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Failed to create calendar event: {sanitized_error}")
            raise BrowserAutomationError(f"Calendar event creation failed: {sanitized_error}") from e

    async def close_browser(self) -> None:
        """Close browser and cleanup resources.

        Safe to call multiple times (idempotent).
        """
        if not self.is_browser_running:
            logger.debug("Browser not running, skipping close")
            return

        try:
            logger.info("Closing browser")

            if self._context:
                await self._context.close()
                self._context = None

            if self._browser:
                await self._browser.close()
                self._browser = None

            if self._playwright:
                # Playwright doesn't have a stop() method when used as context manager
                # It's cleaned up automatically
                self._playwright = None

            self._page = None
            self.is_browser_running = False
            self.is_authenticated = False
            self.current_service = None

            logger.info("Browser closed successfully")

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.warning(f"Error during browser close: {sanitized_error}", exc_info=True)
            self.is_browser_running = False
            # Reset state but allow cleanup to continue
            self._context = None
            self._browser = None
            self._playwright = None
            self._page = None

    async def __aenter__(self) -> "BrowserAutomation":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - automatic cleanup."""
        await self.close_browser()
