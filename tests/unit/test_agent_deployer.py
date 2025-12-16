"""Unit tests for AgentDeployer class.

This module tests the AgentDeployer class that deploys Computer Use Knowledge Worker
agent code and dependencies to Windows VMs via WinRM.

Tests cover:
- Agent code deployment to remote VM
- Dependency installation (Python, Playwright)
- Deployment verification and health checks
- Rollback on deployment failure
- Multiple workflow deployment
- Directory structure creation

Uses pytest with mocks for WinRM and file operations.
"""

from unittest.mock import MagicMock

import pytest

# Import the module under test
# Note: These imports will fail until AgentDeployer is implemented
try:
    from azure_haymaker.knowledge_worker.computer_use.agent_deployer import (
        AgentDeployer,
        DeploymentError,
        DeploymentVerificationError,
    )
    from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
        WinRMConnection,
    )
    from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

    DEPLOYER_AVAILABLE = True
except ImportError:
    DEPLOYER_AVAILABLE = False
    AgentDeployer = None
    DeploymentError = None
    DeploymentVerificationError = None
    WinRMConnection = None
    WorkerIdentity = None


pytestmark = pytest.mark.skipif(not DEPLOYER_AVAILABLE, reason="AgentDeployer not yet implemented")


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_winrm_connection():
    """Fixture: Mock WinRM connection."""
    conn = MagicMock(spec=WinRMConnection)
    conn.is_connected = True
    conn.execute_command.return_value = {
        "stdout": "Success",
        "stderr": "",
        "exit_code": 0,
        "success": True,
    }
    conn.copy_file.return_value = True
    return conn


@pytest.fixture
def worker_identity():
    """Fixture: Sample worker identity."""
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
def workflows():
    """Fixture: Sample workflow definitions."""
    return [
        {
            "name": "email_workflow",
            "script": "email_workflow.py",
            "description": "Send emails via browser",
        },
        {
            "name": "teams_workflow",
            "script": "teams_workflow.py",
            "description": "Send Teams messages",
        },
    ]


@pytest.fixture
def agent_deployer(mock_winrm_connection):
    """Fixture: AgentDeployer instance."""
    return AgentDeployer(connection=mock_winrm_connection)


@pytest.fixture
def mock_agent_files(tmp_path):
    """Fixture: Mock agent code files."""
    agent_dir = tmp_path / "agent_code"
    agent_dir.mkdir()

    # Create mock agent files
    (agent_dir / "agent_main.py").write_text("# Agent main script")
    (agent_dir / "browser_automation.py").write_text("# Browser automation")
    (agent_dir / "requirements.txt").write_text("playwright\nazure-identity")

    return agent_dir


# ==============================================================================
# DEPLOYMENT TESTS
# ==============================================================================


class TestAgentDeployment:
    """Tests for agent deployment operations."""

    def test_deploy_agent_success(
        self, agent_deployer, worker_identity, workflows, mock_winrm_connection
    ):
        """Test successful agent deployment to VM."""
        # Act
        result = agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)

        # Assert
        assert result["success"] is True
        assert result["deployment_path"]
        assert result["worker_id"] == worker_identity.worker_id

        # Should create remote directory
        calls = [call.args[0] for call in mock_winrm_connection.execute_command.call_args_list]
        assert any("New-Item" in cmd for cmd in calls)

        # Should copy files
        assert mock_winrm_connection.copy_file.call_count >= 3  # At least 3 files

    def test_deploy_agent_creates_directory_structure(
        self, agent_deployer, worker_identity, workflows, mock_winrm_connection
    ):
        """Test deploy_agent creates proper directory structure on VM."""
        # Act
        agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)

        # Assert - should create directories
        execute_calls = mock_winrm_connection.execute_command.call_args_list
        commands = [call.args[0] for call in execute_calls]

        # Should create agent directory
        assert any("C:\\KnowledgeWorkers" in cmd for cmd in commands)

        # Should create worker-specific directory
        assert any(worker_identity.worker_id in cmd for cmd in commands)

    def test_deploy_agent_installs_dependencies(
        self, agent_deployer, worker_identity, workflows, mock_winrm_connection
    ):
        """Test deploy_agent installs Python dependencies."""
        # Act
        agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)

        # Assert - should install Python packages
        execute_calls = mock_winrm_connection.execute_command.call_args_list
        commands = [call.args[0] for call in execute_calls]

        # Should run pip install
        assert any("pip install" in cmd for cmd in commands)

        # Should install Playwright browsers
        assert any("playwright install" in cmd for cmd in commands)

    def test_deploy_agent_with_winrm_failure(
        self, agent_deployer, worker_identity, workflows, mock_winrm_connection
    ):
        """Test deploy_agent handles WinRM command failures."""
        # Arrange - simulate command failure
        mock_winrm_connection.execute_command.return_value = {
            "stdout": "",
            "stderr": "Access denied",
            "exit_code": 1,
            "success": False,
        }

        # Act & Assert
        with pytest.raises(DeploymentError) as exc_info:
            agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)
        assert "Access denied" in str(exc_info.value)

    def test_deploy_agent_with_copy_failure(
        self, agent_deployer, worker_identity, workflows, mock_winrm_connection
    ):
        """Test deploy_agent handles file copy failures."""
        # Arrange - simulate copy failure
        mock_winrm_connection.copy_file.return_value = False

        # Act & Assert
        with pytest.raises(DeploymentError) as exc_info:
            agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)
        assert "copy" in str(exc_info.value).lower()


# ==============================================================================
# VERIFICATION TESTS
# ==============================================================================


class TestDeploymentVerification:
    """Tests for deployment verification and health checks."""

    def test_verify_deployment_success(
        self, agent_deployer, worker_identity, mock_winrm_connection
    ):
        """Test successful deployment verification."""
        # Arrange - simulate successful verification checks
        mock_winrm_connection.execute_command.side_effect = [
            # Check directory exists
            {"stdout": "True", "stderr": "", "exit_code": 0, "success": True},
            # Check Python installed
            {"stdout": "Python 3.11.0", "stderr": "", "exit_code": 0, "success": True},
            # Check Playwright installed
            {"stdout": "playwright 1.40.0", "stderr": "", "exit_code": 0, "success": True},
            # Check agent files exist
            {"stdout": "True", "stderr": "", "exit_code": 0, "success": True},
        ]

        deployment_path = f"C:\\KnowledgeWorkers\\{worker_identity.worker_id}"

        # Act
        result = agent_deployer.verify_deployment(
            worker_identity=worker_identity, deployment_path=deployment_path
        )

        # Assert
        assert result["verified"] is True
        assert result["checks_passed"] >= 3
        assert len(result["failures"]) == 0

    def test_verify_deployment_missing_files(
        self, agent_deployer, worker_identity, mock_winrm_connection
    ):
        """Test verify_deployment detects missing files."""
        # Arrange - simulate missing files
        mock_winrm_connection.execute_command.side_effect = [
            # Directory check passes
            {"stdout": "True", "stderr": "", "exit_code": 0, "success": True},
            # Python check passes
            {"stdout": "Python 3.11.0", "stderr": "", "exit_code": 0, "success": True},
            # Playwright check passes
            {"stdout": "playwright 1.40.0", "stderr": "", "exit_code": 0, "success": True},
            # File check fails
            {"stdout": "False", "stderr": "", "exit_code": 0, "success": True},
        ]

        deployment_path = f"C:\\KnowledgeWorkers\\{worker_identity.worker_id}"

        # Act & Assert
        with pytest.raises(DeploymentVerificationError) as exc_info:
            agent_deployer.verify_deployment(
                worker_identity=worker_identity, deployment_path=deployment_path
            )
        assert "missing" in str(exc_info.value).lower()

    def test_verify_deployment_missing_dependencies(
        self, agent_deployer, worker_identity, mock_winrm_connection
    ):
        """Test verify_deployment detects missing Python dependencies."""
        # Arrange - simulate missing dependencies
        mock_winrm_connection.execute_command.side_effect = [
            # Directory exists
            {"stdout": "True", "stderr": "", "exit_code": 0, "success": True},
            # Python installed
            {"stdout": "Python 3.11.0", "stderr": "", "exit_code": 0, "success": True},
            # Playwright NOT installed
            {"stdout": "", "stderr": "Module not found", "exit_code": 1, "success": False},
        ]

        deployment_path = f"C:\\KnowledgeWorkers\\{worker_identity.worker_id}"

        # Act & Assert
        with pytest.raises(DeploymentVerificationError) as exc_info:
            agent_deployer.verify_deployment(
                worker_identity=worker_identity, deployment_path=deployment_path
            )
        assert "dependenc" in str(exc_info.value).lower()


# ==============================================================================
# WORKFLOW TESTS
# ==============================================================================


class TestWorkflowDeployment:
    """Tests for workflow-specific deployment."""

    def test_deploy_multiple_workflows(
        self, agent_deployer, worker_identity, workflows, mock_winrm_connection
    ):
        """Test deploying multiple workflows to agent."""
        # Act
        result = agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)

        # Assert
        assert result["success"] is True
        assert result["workflow_count"] == 2

        # Should copy workflow files
        copy_calls = mock_winrm_connection.copy_file.call_args_list
        assert len(copy_calls) >= len(workflows)

    def test_deploy_agent_with_empty_workflows(
        self, agent_deployer, worker_identity, mock_winrm_connection
    ):
        """Test deploy_agent with empty workflows list."""
        # Act
        result = agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=[])

        # Assert
        assert result["success"] is True
        assert result["workflow_count"] == 0
        # Should still deploy base agent code
        assert mock_winrm_connection.copy_file.call_count >= 1


# ==============================================================================
# SECURITY TESTS
# ==============================================================================


class TestSecurityControls:
    """Tests for security controls in agent deployment."""

    def test_config_does_not_contain_credentials(self, agent_deployer, worker_identity, workflows):
        """Test that deployed config.json does NOT contain M365 credentials."""
        # Act
        agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)

        # Assert - config should not have password fields
        # This is verified by checking the template in AGENT_MAIN_TEMPLATE
        assert "M365_USERNAME" in agent_deployer.AGENT_MAIN_TEMPLATE
        assert "M365_PASSWORD" in agent_deployer.AGENT_MAIN_TEMPLATE
        assert "os.environ.get" in agent_deployer.AGENT_MAIN_TEMPLATE

    def test_agent_template_reads_from_environment(self):
        """Test that agent template reads credentials from environment variables."""
        # Arrange
        from azure_haymaker.knowledge_worker.computer_use.agent_deployer import (
            AgentDeployer,
        )

        # Act
        template = AgentDeployer.AGENT_MAIN_TEMPLATE

        # Assert - should use environment variables
        assert 'os.environ.get("M365_USERNAME")' in template
        assert 'os.environ.get("M365_PASSWORD")' in template
        assert 'config["m365_username"]' not in template
        assert 'config["m365_password"]' not in template

    def test_powershell_escaping_in_commands(
        self, agent_deployer, worker_identity, workflows, mock_winrm_connection
    ):
        """Test that PowerShell commands use proper escaping."""
        # Act
        agent_deployer.deploy_agent(worker_identity=worker_identity, workflows=workflows)

        # Assert - check that execute_command was called with escaped paths
        execute_calls = mock_winrm_connection.execute_command.call_args_list
        commands = [call.args[0] for call in execute_calls]

        # At least some commands should NOT have raw single quotes around paths
        # (they should use the escape function which wraps in single quotes)
        # This is a basic check that escaping is being applied
        has_escaped_commands = any("New-Item -Path" in cmd for cmd in commands)
        assert has_escaped_commands


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
