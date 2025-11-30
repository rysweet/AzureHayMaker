"""Unit tests for ComputerUseKnowledgeWorkerAgent class.

This module tests the ComputerUseKnowledgeWorkerAgent class that extends
KnowledgeWorkerAgent to execute workflows via browser automation on Windows VMs.

Tests cover:
- Agent initialization and configuration
- Lifecycle hooks (on_start, on_execute, on_cleanup)
- Workflow execution via browser
- Browser session management
- Error handling and recovery
- Telemetry logging
- Integration with base KnowledgeWorkerAgent

Uses pytest with mocks for browser automation and WinRM.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the module under test
# Note: These imports will fail until ComputerUseKnowledgeWorkerAgent is implemented
try:
    from azure_haymaker.knowledge_worker.agent import KnowledgeWorkerConfig
    from azure_haymaker.knowledge_worker.computer_use.agent import (
        ComputerUseConfig,
        ComputerUseKnowledgeWorkerAgent,
    )
    from azure_haymaker.knowledge_worker.computer_use.browser_automation import (
        BrowserAutomation,
    )
    from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

    COMPUTER_USE_AVAILABLE = True
except ImportError:
    COMPUTER_USE_AVAILABLE = False
    ComputerUseKnowledgeWorkerAgent = None
    ComputerUseConfig = None
    KnowledgeWorkerConfig = None
    BrowserAutomation = None
    WorkerIdentity = None


pytestmark = pytest.mark.skipif(
    not COMPUTER_USE_AVAILABLE, reason="ComputerUseKnowledgeWorkerAgent not yet implemented"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def worker_config():
    """Fixture: Computer use worker configuration."""
    return ComputerUseConfig(
        worker_id="kw-test-001",
        display_name="Test Computer Use Worker",
        department="engineering",
        persona="engineering",
        team_id="team-001",
        team_name="Engineering Team",
        endpoint_type="cloud_pc",
        endpoint_id="cloudpc-abc123",
        m365_username="test.worker@tenant.onmicrosoft.com",
        m365_password="SecureP@ssw0rd123!",
        tenant_domain="tenant.onmicrosoft.com",
        vm_hostname="test-vm.westus2.cloudapp.azure.com",
        vm_username="kwadmin",
        vm_password="VmP@ssw0rd!",
    )


@pytest.fixture
def worker_identity():
    """Fixture: Worker identity."""
    return WorkerIdentity(
        worker_id="kw-test-001",
        display_name="Test Worker",
        user_principal_name="test.worker@tenant.onmicrosoft.com",
        entra_object_id="user-obj-123",
        department="engineering",
        persona="engineering",
        endpoint_type="cloud_pc",
        endpoint_id="cloudpc-abc123",
        team_ids=["team-001"],
    )


@pytest.fixture
def mock_browser_automation():
    """Fixture: Mock BrowserAutomation instance."""
    browser = MagicMock(spec=BrowserAutomation)
    browser.is_browser_running = False
    browser.is_authenticated = False
    browser.launch_browser = AsyncMock()
    browser.login_m365 = AsyncMock()
    browser.navigate_to_outlook_web = AsyncMock()
    browser.navigate_to_teams_web = AsyncMock()
    browser.send_email_via_browser = AsyncMock(return_value={"success": True})
    browser.send_teams_message_via_browser = AsyncMock(return_value={"success": True})
    browser.close_browser = AsyncMock()
    return browser


@pytest.fixture
def mock_telemetry_collector():
    """Fixture: Mock telemetry collector."""
    collector = MagicMock()
    collector.log_operation = MagicMock()
    return collector


@pytest.fixture
def computer_use_agent(worker_config, worker_identity, mock_browser_automation):
    """Fixture: ComputerUseKnowledgeWorkerAgent instance."""
    with patch(
        "azure_haymaker.knowledge_worker.computer_use.agent.BrowserAutomation",
        return_value=mock_browser_automation,
    ):
        agent = ComputerUseKnowledgeWorkerAgent(
            worker_config=worker_config, worker_identity=worker_identity
        )
        return agent


# ==============================================================================
# INITIALIZATION TESTS
# ==============================================================================


class TestAgentInitialization:
    """Tests for agent initialization."""

    def test_agent_initialization_success(self, worker_config, worker_identity):
        """Test successful agent initialization."""
        # Act
        agent = ComputerUseKnowledgeWorkerAgent(
            worker_config=worker_config, worker_identity=worker_identity
        )

        # Assert
        assert agent.worker_config == worker_config
        assert agent.worker_identity == worker_identity
        assert agent.config_type == "computer_use"

    def test_agent_extends_knowledge_worker_agent(
        self, worker_config, worker_identity
    ):
        """Test ComputerUseKnowledgeWorkerAgent extends KnowledgeWorkerAgent."""
        # Act
        agent = ComputerUseKnowledgeWorkerAgent(
            worker_config=worker_config, worker_identity=worker_identity
        )

        # Assert
        # Should have base agent methods
        assert hasattr(agent, "on_start")
        assert hasattr(agent, "on_execute")
        assert hasattr(agent, "on_cleanup")
        assert hasattr(agent, "get_worker_stats")

    def test_agent_initialization_without_vm_credentials(self, worker_identity):
        """Test agent initialization fails without VM credentials."""
        # Arrange
        config = ComputerUseConfig(
            worker_id="kw-test-001",
            display_name="Test Worker",
            vm_hostname="",  # Missing VM credentials
            vm_username="",
            vm_password="",
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ComputerUseKnowledgeWorkerAgent(
                worker_config=config, worker_identity=worker_identity
            )
        assert "credential" in str(exc_info.value).lower()


# ==============================================================================
# LIFECYCLE TESTS
# ==============================================================================


class TestAgentLifecycle:
    """Tests for agent lifecycle hooks."""

    def test_on_start_launches_browser(
        self, computer_use_agent, mock_browser_automation
    ):
        """Test on_start launches browser and authenticates."""
        # Act
        computer_use_agent.on_start()

        # Assert
        mock_browser_automation.launch_browser.assert_called_once()
        mock_browser_automation.login_m365.assert_called_once()

    def test_on_start_handles_browser_launch_failure(
        self, computer_use_agent, mock_browser_automation
    ):
        """Test on_start handles browser launch failures."""
        # Arrange
        mock_browser_automation.launch_browser.side_effect = Exception("Browser launch failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            computer_use_agent.on_start()
        assert "launch" in str(exc_info.value).lower()

    def test_on_start_handles_login_failure(
        self, computer_use_agent, mock_browser_automation
    ):
        """Test on_start handles M365 login failures."""
        # Arrange
        mock_browser_automation.login_m365.side_effect = Exception("Invalid credentials")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            computer_use_agent.on_start()
        assert "credential" in str(exc_info.value).lower()

    def test_on_cleanup_closes_browser(
        self, computer_use_agent, mock_browser_automation
    ):
        """Test on_cleanup closes browser session."""
        # Arrange
        computer_use_agent.on_start()

        # Act
        computer_use_agent.on_cleanup(exit_code=0)

        # Assert
        mock_browser_automation.close_browser.assert_called_once()

    def test_on_cleanup_handles_browser_close_error(
        self, computer_use_agent, mock_browser_automation
    ):
        """Test on_cleanup handles browser close errors gracefully."""
        # Arrange
        computer_use_agent.on_start()
        mock_browser_automation.close_browser.side_effect = Exception("Close failed")

        # Act - should not raise
        computer_use_agent.on_cleanup(exit_code=0)

        # Assert - error logged but cleanup completes
        mock_browser_automation.close_browser.assert_called_once()


# ==============================================================================
# WORKFLOW EXECUTION TESTS
# ==============================================================================


class TestWorkflowExecution:
    """Tests for workflow execution via browser."""

    @pytest.mark.asyncio
    async def test_execute_workflow_email(
        self, computer_use_agent, mock_browser_automation
    ):
        """Test execute email workflow."""
        # Arrange
        computer_use_agent.on_start()
        workflow_params = {
            "to": "recipient@tenant.com",
            "subject": "Test Email",
            "body": "This is a test.",
        }

        # Act
        result = await computer_use_agent.execute_workflow(
            workflow_name="email_workflow", params=workflow_params
        )

        # Assert
        assert result["success"] is True
        mock_browser_automation.navigate_to_outlook_web.assert_called_once()
        mock_browser_automation.send_email_via_browser.assert_called_once_with(
            to=workflow_params["to"],
            subject=workflow_params["subject"],
            body=workflow_params["body"],
        )

    @pytest.mark.asyncio
    async def test_execute_workflow_teams_message(
        self, computer_use_agent, mock_browser_automation
    ):
        """Test execute Teams message workflow."""
        # Arrange
        computer_use_agent.on_start()
        workflow_params = {
            "channel": "General",
            "message": "Hello team!",
        }

        # Act
        result = await computer_use_agent.execute_workflow(
            workflow_name="teams_workflow", params=workflow_params
        )

        # Assert
        assert result["success"] is True
        mock_browser_automation.navigate_to_teams_web.assert_called_once()
        mock_browser_automation.send_teams_message_via_browser.assert_called_once_with(
            channel=workflow_params["channel"], message=workflow_params["message"]
        )

    @pytest.mark.asyncio
    async def test_execute_workflow_unknown(self, computer_use_agent):
        """Test execute_workflow with unknown workflow name."""
        # Arrange
        computer_use_agent.on_start()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await computer_use_agent.execute_workflow(
                workflow_name="unknown_workflow", params={}
            )
        assert "unknown" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_workflow_without_browser(self, computer_use_agent):
        """Test execute_workflow fails if browser not started."""
        # Act & Assert - on_start not called
        with pytest.raises(RuntimeError) as exc_info:
            await computer_use_agent.execute_workflow(
                workflow_name="email_workflow", params={}
            )
        assert "browser" in str(exc_info.value).lower()


# ==============================================================================
# TELEMETRY TESTS
# ==============================================================================


class TestTelemetryLogging:
    """Tests for telemetry and operation logging."""

    @pytest.mark.asyncio
    async def test_workflow_execution_logs_telemetry(
        self, computer_use_agent, mock_browser_automation, mock_telemetry_collector
    ):
        """Test workflow execution logs telemetry."""
        # Arrange
        computer_use_agent.telemetry_collector = mock_telemetry_collector
        computer_use_agent.on_start()

        # Act
        await computer_use_agent.execute_workflow(
            workflow_name="email_workflow",
            params={"to": "test@tenant.com", "subject": "Test", "body": "Test"},
        )

        # Assert - should log operation
        mock_telemetry_collector.log_operation.assert_called()
        call_args = mock_telemetry_collector.log_operation.call_args
        assert call_args.kwargs["operation"] == "email_workflow"
        assert call_args.kwargs["status"] == "success"

    @pytest.mark.asyncio
    async def test_workflow_failure_logs_error(
        self, computer_use_agent, mock_browser_automation, mock_telemetry_collector
    ):
        """Test workflow failure logs error telemetry."""
        # Arrange
        computer_use_agent.telemetry_collector = mock_telemetry_collector
        computer_use_agent.on_start()
        mock_browser_automation.send_email_via_browser.side_effect = Exception(
            "Send failed"
        )

        # Act
        with pytest.raises(Exception):
            await computer_use_agent.execute_workflow(
                workflow_name="email_workflow",
                params={"to": "test@tenant.com", "subject": "Test", "body": "Test"},
            )

        # Assert - should log error
        mock_telemetry_collector.log_operation.assert_called()
        call_args = mock_telemetry_collector.log_operation.call_args
        assert call_args.kwargs["status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
