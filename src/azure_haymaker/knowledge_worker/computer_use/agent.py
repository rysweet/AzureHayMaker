"""Computer Use Knowledge Worker Agent.

Extends KnowledgeWorkerAgent to execute workflows via browser automation
on Windows VMs using Computer Use pattern.
"""

import asyncio
import logging
from dataclasses import dataclass
from time import time
from typing import Any

from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerAgent,
    KnowledgeWorkerConfig,
)
from azure_haymaker.knowledge_worker.computer_use.browser_automation import (
    BrowserAutomation,
)
from azure_haymaker.knowledge_worker.computer_use.security_utils import sanitize_error
from azure_haymaker.knowledge_worker.computer_use.telemetry import (
    ComputerUseTelemetryCollector,
)
from azure_haymaker.knowledge_worker.computer_use.workflows import (
    EmailWorkflow,
    TeamsMessageWorkflow,
)
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

logger = logging.getLogger(__name__)


def _run_async_in_context(coro):
    """Run async code in sync context, handling both running and stopped loops.

    This helper simplifies the common pattern of running async operations
    from sync code, automatically detecting existing event loops and using
    a thread pool when needed.

    Args:
        coro: Coroutine to execute

    Returns:
        Result of the coroutine
    """
    try:
        # Try to get running event loop (we're already in async context)
        loop = asyncio.get_running_loop()
        # Create new loop in separate thread to avoid blocking
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            return executor.submit(run_in_new_loop).result()
    except RuntimeError:
        # No running loop, create and use one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@dataclass
class ComputerUseConfig(KnowledgeWorkerConfig):
    """Configuration for Computer Use Knowledge Worker Agent.

    Extends KnowledgeWorkerConfig with VM and M365 credentials
    for browser automation.

    Attributes:
        m365_username: M365 username for browser login
        m365_password: M365 password for browser login
        vm_hostname: Windows VM hostname
        vm_username: VM WinRM username
        vm_password: VM WinRM password
    """

    # M365 credentials for browser login
    m365_username: str = ""
    m365_password: str = ""

    # VM credentials for WinRM
    vm_hostname: str = ""
    vm_username: str = ""
    vm_password: str = ""

    def __repr__(self) -> str:
        """Return string representation with passwords masked.

        Returns sanitized representation that masks password fields
        to prevent credential leakage in logs and debug output.
        """
        # Get all fields from dataclass
        fields = []
        for field_name, field_value in self.__dict__.items():
            # Mask password fields
            if 'password' in field_name.lower():
                fields.append(f"{field_name}='***'")
            else:
                fields.append(f"{field_name}={repr(field_value)}")

        return f"{self.__class__.__name__}({', '.join(fields)})"


class ComputerUseKnowledgeWorkerAgent(KnowledgeWorkerAgent):
    """Computer Use Knowledge Worker Agent.

    Extends KnowledgeWorkerAgent to execute M365 workflows via browser
    automation instead of Graph API. Runs on Windows VMs and uses
    Playwright to interact with M365 web applications.

    Key differences from base agent:
    - Uses browser automation instead of Graph API
    - Executes workflows via Outlook Web, Teams Web
    - Logs telemetry for all browser operations
    - Manages browser lifecycle (launch on start, close on cleanup)

    Example:
        >>> config = ComputerUseConfig(
        ...     worker_id="kw-test-001",
        ...     display_name="Test Worker",
        ...     m365_username="worker@tenant.onmicrosoft.com",
        ...     m365_password="SecurePass123!",
        ...     vm_hostname="vm.cloudapp.azure.com",
        ...     vm_username="kwadmin",
        ...     vm_password="VmPass123!",
        ... )
        >>> identity = WorkerIdentity(worker_id="kw-test-001", ...)
        >>> agent = ComputerUseKnowledgeWorkerAgent(
        ...     worker_config=config,
        ...     worker_identity=identity
        ... )
        >>> agent.on_start()
        >>> result = await agent.execute_workflow("email_workflow", {...})
        >>> agent.on_cleanup(exit_code=0)

    Attributes:
        worker_config: Computer Use configuration
        worker_identity: Worker identity
        browser: BrowserAutomation instance
        telemetry_collector: Telemetry collector for operations
        config_type: Always "computer_use"
    """

    def __init__(
        self,
        worker_config: ComputerUseConfig,
        worker_identity: WorkerIdentity,
        browser: BrowserAutomation | None = None,
    ):
        """Initialize Computer Use Knowledge Worker Agent.

        Args:
            worker_config: Computer Use configuration
            worker_identity: Worker identity
            browser: Optional BrowserAutomation instance (for testing)

        Raises:
            ValueError: If required VM or M365 credentials are missing
        """
        # Validate credentials
        if not worker_config.vm_hostname or not worker_config.vm_username or not worker_config.vm_password:
            raise ValueError(
                "VM credentials (vm_hostname, vm_username, vm_password) are required"
            )

        # Initialize base agent
        super().__init__(
            worker_config=worker_config,
            worker_identity=worker_identity,
        )

        # Computer Use specific attributes
        self.worker_config: ComputerUseConfig = worker_config
        self.browser = browser or BrowserAutomation(headless=True, screenshot_on_error=True)
        self.telemetry_collector = ComputerUseTelemetryCollector(worker_identity=worker_identity)
        self.config_type = "computer_use"

        self._browser_started = False

        logger.info(
            f"ComputerUseKnowledgeWorkerAgent initialized for {worker_identity.worker_id}"
        )

    def on_start(self) -> None:
        """Agent startup hook.

        Launches browser and authenticates to M365.
        Called before agent begins executing workflows.

        Raises:
            Exception: If browser launch or login fails
        """
        logger.info(f"Starting Computer Use agent {self.worker_identity.worker_id}")

        try:
            # Call parent on_start
            super().on_start()

            # Launch browser and authenticate
            _run_async_in_context(self.browser.launch_browser())
            _run_async_in_context(
                self.browser.login_m365(
                    username=self.worker_config.m365_username,
                    password=self.worker_config.m365_password,
                )
            )

            self._browser_started = True
            logger.info(f"Computer Use agent {self.worker_identity.worker_id} started successfully")

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Failed to start Computer Use agent: {sanitized_error}")
            self._browser_started = False
            raise

    async def execute_workflow(
        self,
        workflow_name: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute workflow via browser automation.

        Args:
            workflow_name: Name of workflow to execute ("email_workflow", "teams_workflow")
            params: Workflow parameters

        Returns:
            Dict with workflow execution result

        Raises:
            RuntimeError: If browser not started
            ValueError: If workflow_name is unknown
            WorkflowError: If workflow execution fails
        """
        if not self._browser_started:
            raise RuntimeError("Browser not started. Call on_start() first.")

        start_time = time()

        try:
            logger.info(f"Executing workflow: {workflow_name}")

            # Map workflow name to workflow class
            if workflow_name == "email_workflow":
                workflow = EmailWorkflow(browser=self.browser)
                result = await workflow.execute(**params)

            elif workflow_name == "teams_workflow":
                workflow = TeamsMessageWorkflow(browser=self.browser)
                result = await workflow.execute(**params)

            else:
                raise ValueError(f"Unknown workflow: {workflow_name}")

            # Log successful execution
            duration_ms = int((time() - start_time) * 1000)
            self.telemetry_collector.log_operation(
                operation=workflow_name,
                status="success",
                duration_ms=duration_ms,
                metadata={"params": params},
            )

            logger.info(f"Workflow {workflow_name} completed successfully")
            return result

        except Exception as e:
            # Log failed execution
            duration_ms = int((time() - start_time) * 1000)
            self.telemetry_collector.log_operation(
                operation=workflow_name,
                status="error",
                duration_ms=duration_ms,
                metadata={"error": str(e), "params": params},
            )

            sanitized_error = sanitize_error(str(e))
            logger.error(f"Workflow {workflow_name} failed: {sanitized_error}")
            raise

    def on_cleanup(self, exit_code: int = 0) -> None:
        """Agent cleanup hook.

        Closes browser and cleans up resources.
        Called when agent is shutting down.

        Args:
            exit_code: Exit code (0=success, non-zero=failure)
        """
        logger.info(f"Cleaning up Computer Use agent {self.worker_identity.worker_id}")

        try:
            # Close browser (async operation)
            if self._browser_started:
                _run_async_in_context(self.browser.close_browser())
                self._browser_started = False

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Error during browser cleanup: {sanitized_error}", exc_info=True)
            # Reset state and continue cleanup even if browser close fails
            self._browser_started = False

        finally:
            # Call parent cleanup
            super().on_cleanup(exit_code=exit_code)

        logger.info(f"Computer Use agent {self.worker_identity.worker_id} cleanup complete")

    def get_worker_stats(self) -> dict[str, Any]:
        """Get worker statistics without exposing credentials.

        SECURITY: Returns safe statistics that exclude all password and credential fields
        to prevent accidental credential leakage in logs or monitoring systems.

        Returns:
            Dict with worker statistics:
                - worker_id: Worker identifier
                - display_name: Worker display name
                - config_type: Configuration type ("computer_use")
                - vm_hostname: VM hostname (safe to expose)
                - vm_username: VM username (safe to expose)
                - m365_username: M365 username (safe to expose)
                - browser_running: Whether browser is currently running
                - is_authenticated: Whether authenticated to M365
                - current_service: Current M365 service (outlook, teams, etc)
                - telemetry_summary: Telemetry metrics summary

        Example:
            >>> agent = ComputerUseKnowledgeWorkerAgent(...)
            >>> stats = agent.get_worker_stats()
            >>> print(stats)
            {
                'worker_id': 'kw-test-001',
                'vm_hostname': 'vm.cloudapp.azure.com',
                'vm_username': 'kwadmin',
                # Note: vm_password and m365_password are NOT included
            }
        """
        # Get telemetry metrics
        telemetry_metrics = self.telemetry_collector.get_metrics_summary()

        # Build stats dict with only safe fields (no passwords)
        stats = {
            # Worker identity (safe)
            "worker_id": self.worker_identity.worker_id,
            "display_name": self.worker_identity.display_name,
            "department": self.worker_identity.department,
            "persona": self.worker_identity.persona,
            # Configuration (safe fields only, NO passwords)
            "config_type": self.config_type,
            "vm_hostname": self.worker_config.vm_hostname,
            "vm_username": self.worker_config.vm_username,
            # Note: vm_password is intentionally excluded
            "m365_username": self.worker_config.m365_username,
            # Note: m365_password is intentionally excluded
            # Browser state (safe)
            "browser_running": self._browser_started,
            "is_authenticated": self.browser.is_authenticated if self._browser_started else False,
            "current_service": self.browser.current_service if self._browser_started else None,
            # Telemetry summary (safe)
            "telemetry_summary": {
                "total_operations": telemetry_metrics.total_operations,
                "successful_operations": telemetry_metrics.successful_operations,
                "failed_operations": telemetry_metrics.failed_operations,
                "average_duration_ms": telemetry_metrics.average_duration_ms,
                "success_rate": telemetry_metrics.success_rate,
            },
        }

        return stats
