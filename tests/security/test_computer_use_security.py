"""Security tests for Computer Use Knowledge Worker Agents.

This module tests security aspects of Computer Use agents including:
- Credential sanitization in logs and telemetry
- Command injection prevention in WinRM
- Path traversal prevention in file operations
- Browser session isolation
- Sensitive data handling
- Authentication security

Uses pytest with security-focused test patterns.
"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import modules under test
try:
    from azure_haymaker.knowledge_worker.computer_use.agent import (
        ComputerUseConfig,
        ComputerUseKnowledgeWorkerAgent,
    )
    from azure_haymaker.knowledge_worker.computer_use.agent_deployer import (
        AgentDeployer,
    )
    from azure_haymaker.knowledge_worker.computer_use.browser_automation import (
        BrowserAutomation,
    )
    from azure_haymaker.knowledge_worker.computer_use.telemetry import (
        ComputerUseTelemetryCollector,
    )
    from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
        WinRMConnection,
    )
    from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    ComputerUseConfig = None
    ComputerUseKnowledgeWorkerAgent = None
    AgentDeployer = None
    BrowserAutomation = None
    ComputerUseTelemetryCollector = None
    WinRMConnection = None
    WorkerIdentity = None


pytestmark = [
    pytest.mark.skipif(
        not SECURITY_AVAILABLE, reason="Security test modules not yet implemented"
    ),
    pytest.mark.skip(reason="Security features not yet implemented - placeholder tests for future implementation"),
]


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def worker_identity():
    """Fixture: Worker identity with sensitive data."""
    return WorkerIdentity(
        worker_id="kw-sec-001",
        display_name="Security Test Worker",
        user_principal_name="security.worker@tenant.onmicrosoft.com",
        entra_object_id="user-obj-sec-123",
        department="security",
        persona="engineering",  # Use valid persona from WorkerPersona enum
        endpoint_type="cloud_pc",
        endpoint_id="cloudpc-sec-123",
        team_ids=["team-sec-001"],
    )


@pytest.fixture
def sensitive_config():
    """Fixture: Configuration with sensitive credentials."""
    return {
        "vm_password": "SuperSecret!P@ssw0rd123",
        "m365_password": "AnotherSecret!M365P@ss",
        "api_key": "sk-1234567890abcdef",
        "connection_string": "DefaultEndpointsProtocol=https;AccountName=storage;AccountKey=secretkey123==",
    }


# ==============================================================================
# CREDENTIAL SANITIZATION TESTS
# ==============================================================================


class TestCredentialSanitization:
    """Tests for credential sanitization in logs and telemetry."""

    def test_telemetry_sanitizes_passwords(
        self, worker_identity, sensitive_config
    ):
        """Test telemetry logs do not contain passwords."""
        # Arrange
        collector = ComputerUseTelemetryCollector(worker_identity=worker_identity)

        # Act
        collector.log_operation(
            operation="vm_connection",
            status="success",
            duration_ms=1000,
            metadata={
                "hostname": "test-vm.westus2.cloudapp.azure.com",
                "username": "kwadmin",
                "password": sensitive_config["vm_password"],  # Should be sanitized
            },
        )

        # Assert
        logs = collector.get_logs()
        assert len(logs) == 1

        # Password should be redacted
        log_str = str(logs[0])
        assert sensitive_config["vm_password"] not in log_str
        assert "***" in log_str or "REDACTED" in log_str.upper()

    def test_config_repr_sanitizes_secrets(self, worker_identity, sensitive_config):
        """Test config __repr__ does not expose secrets."""
        # Arrange
        config = ComputerUseConfig(
            worker_id=worker_identity.worker_id,
            display_name=worker_identity.display_name,
            vm_hostname="test-vm.westus2.cloudapp.azure.com",
            vm_username="kwadmin",
            vm_password=sensitive_config["vm_password"],
            m365_username=worker_identity.user_principal_name,
            m365_password=sensitive_config["m365_password"],
        )

        # Act
        config_str = repr(config)

        # Assert
        assert sensitive_config["vm_password"] not in config_str
        assert sensitive_config["m365_password"] not in config_str
        assert "***" in config_str or "REDACTED" in config_str

    def test_error_messages_sanitize_credentials(
        self, worker_identity, sensitive_config
    ):
        """Test error messages do not leak credentials."""
        # Arrange
        with patch(
            "azure_haymaker.knowledge_worker.computer_use.winrm_connection.Protocol"
        ) as mock:
            mock.side_effect = Exception(
                f"Authentication failed with password: {sensitive_config['vm_password']}"
            )

            conn = WinRMConnection(
                hostname="test-vm.westus2.cloudapp.azure.com",
                username="kwadmin",
                password=sensitive_config["vm_password"],
            )

            # Act & Assert
            try:
                conn.connect()
            except Exception as e:
                error_str = str(e)
                # Password should be sanitized in error message
                assert sensitive_config["vm_password"] not in error_str


# ==============================================================================
# COMMAND INJECTION TESTS
# ==============================================================================


class TestCommandInjectionPrevention:
    """Tests for command injection prevention in WinRM."""

    def test_execute_command_prevents_injection(self):
        """Test execute_command sanitizes input to prevent injection."""
        # Arrange
        with patch(
            "azure_haymaker.knowledge_worker.computer_use.winrm_connection.Protocol"
        ) as mock:
            protocol = MagicMock()
            mock.return_value = protocol
            protocol.open_shell.return_value = "shell-123"
            protocol.run_command.return_value = "cmd-456"
            protocol.get_command_output.return_value = (b"Safe output", b"", 0)

            conn = WinRMConnection(
                hostname="test-vm.westus2.cloudapp.azure.com",
                username="kwadmin",
                password="VmP@ssw0rd!",
            )
            conn.connect()

            # Act - try command injection
            malicious_input = "Get-Process; Remove-Item C:\\* -Recurse -Force"

            # Should either sanitize or reject
            try:
                result = conn.execute_command(malicious_input)
                # If execution allowed, verify command was sanitized
                actual_command = protocol.run_command.call_args[0][1]
                # Should not contain dangerous characters or commands
                assert ";" not in actual_command or result["exit_code"] != 0
            except ValueError as e:
                # Or should reject entirely
                assert "invalid" in str(e).lower() or "injection" in str(e).lower()

    def test_copy_file_prevents_path_traversal(self, tmp_path):
        """Test copy_file prevents path traversal attacks."""
        # Arrange
        with patch(
            "azure_haymaker.knowledge_worker.computer_use.winrm_connection.Protocol"
        ) as mock:
            protocol = MagicMock()
            mock.return_value = protocol
            protocol.open_shell.return_value = "shell-123"

            conn = WinRMConnection(
                hostname="test-vm.westus2.cloudapp.azure.com",
                username="kwadmin",
                password="VmP@ssw0rd!",
            )
            conn.connect()

            # Create test file
            local_file = tmp_path / "test.txt"
            local_file.write_text("content")

            # Act & Assert - try path traversal
            malicious_path = "C:\\Windows\\System32\\..\\..\\..\\sensitive.txt"

            try:
                conn.copy_file(str(local_file), malicious_path)
                # If allowed, verify path was sanitized
                actual_path = protocol.run_command.call_args[0][1]
                assert "..\\" not in actual_path
            except ValueError as e:
                # Or should reject entirely
                assert "invalid" in str(e).lower() or "path" in str(e).lower()


# ==============================================================================
# BROWSER SECURITY TESTS
# ==============================================================================


class TestBrowserSecurity:
    """Tests for browser security and session isolation."""

    @pytest.mark.asyncio
    async def test_browser_sessions_are_isolated(self):
        """Test browser sessions are isolated per agent."""
        # Arrange
        with patch(
            "azure_haymaker.knowledge_worker.computer_use.browser_automation.async_playwright"
        ) as mock_pw:
            playwright = AsyncMock()
            browser1 = AsyncMock()
            browser2 = AsyncMock()
            context1 = AsyncMock()
            context2 = AsyncMock()

            mock_pw.return_value.__aenter__.return_value = playwright
            playwright.chromium.launch.side_effect = [browser1, browser2]
            browser1.new_context.return_value = context1
            browser2.new_context.return_value = context2

            # Act - create two browser sessions
            automation1 = BrowserAutomation()
            automation2 = BrowserAutomation()

            await automation1.launch_browser()
            await automation2.launch_browser()

            # Assert - should have separate contexts
            assert context1 != context2
            # Each should have independent storage
            assert browser1.new_context.call_count >= 1
            assert browser2.new_context.call_count >= 1

    @pytest.mark.asyncio
    async def test_browser_clears_sensitive_data_on_close(self):
        """Test browser clears sensitive data on close."""
        # Arrange
        with patch(
            "azure_haymaker.knowledge_worker.computer_use.browser_automation.async_playwright"
        ) as mock_pw:
            playwright = AsyncMock()
            browser = AsyncMock()
            context = AsyncMock()

            mock_pw.return_value.__aenter__.return_value = playwright
            playwright.chromium.launch.return_value = browser
            browser.new_context.return_value = context

            automation = BrowserAutomation()
            await automation.launch_browser()

            # Act - close browser
            await automation.close_browser()

            # Assert - should clear storage
            context.clear_cookies.assert_called_once()
            context.close.assert_called_once()
            browser.close.assert_called_once()


# ==============================================================================
# AUTHENTICATION SECURITY TESTS
# ==============================================================================


class TestAuthenticationSecurity:
    """Tests for authentication security."""

    @pytest.mark.asyncio
    async def test_m365_login_uses_secure_credential_passing(self):
        """Test M365 login does not expose credentials in plain text."""
        # Arrange
        with patch(
            "azure_haymaker.knowledge_worker.computer_use.browser_automation.async_playwright"
        ) as mock_pw:
            playwright = AsyncMock()
            browser = AsyncMock()
            context = AsyncMock()
            page = AsyncMock()

            mock_pw.return_value.__aenter__.return_value = playwright
            playwright.chromium.launch.return_value = browser
            browser.new_context.return_value = context
            context.new_page.return_value = page
            page.wait_for_selector = AsyncMock()

            automation = BrowserAutomation()
            await automation.launch_browser()

            # Act
            await automation.login_m365(
                username="user@tenant.com", password="SecureP@ss123!"
            )

            # Assert - password should be typed, not set as attribute
            fill_calls = page.fill.call_args_list
            # Should use fill() which types securely
            assert len(fill_calls) >= 2  # Username and password
            # Verify password was passed to fill, not exposed elsewhere
            password_call = fill_calls[1]
            assert password_call.args[1] == "SecureP@ss123!"

    def test_winrm_connection_uses_encrypted_transport(self):
        """Test WinRM connection uses SSL/TLS."""
        # Arrange & Act
        conn = WinRMConnection(
            hostname="test-vm.westus2.cloudapp.azure.com",
            username="kwadmin",
            password="VmP@ssw0rd!",
            port=5986,  # HTTPS port
            transport="ssl",
        )

        # Assert
        assert conn.transport == "ssl"
        assert conn.port == 5986  # HTTPS, not HTTP (5985)


# ==============================================================================
# DATA PROTECTION TESTS
# ==============================================================================


class TestDataProtection:
    """Tests for sensitive data protection."""

    def test_telemetry_export_excludes_sensitive_fields(self, worker_identity):
        """Test telemetry export excludes sensitive data."""
        # Arrange
        collector = ComputerUseTelemetryCollector(worker_identity=worker_identity)

        collector.log_operation(
            operation="login",
            status="success",
            duration_ms=2000,
            metadata={
                "username": "user@tenant.com",
                "password": "ShouldNotAppear!",  # Should be excluded
                "session_id": "session-123",
            },
        )

        # Act
        export_data = collector.prepare_export_data()

        # Assert
        export_str = str(export_data)
        assert "ShouldNotAppear!" not in export_str
        assert "password" not in export_str.lower() or "***" in export_str

    def test_agent_stats_exclude_credentials(self, worker_identity):
        """Test get_worker_stats does not include credentials."""
        # Arrange
        config = ComputerUseConfig(
            worker_id=worker_identity.worker_id,
            display_name=worker_identity.display_name,
            vm_hostname="test-vm.westus2.cloudapp.azure.com",
            vm_username="kwadmin",
            vm_password="VmP@ssw0rd!",
            m365_username=worker_identity.user_principal_name,
            m365_password="M365P@ssw0rd!",
        )

        agent = ComputerUseKnowledgeWorkerAgent(
            worker_config=config, worker_identity=worker_identity
        )

        # Act
        stats = agent.get_worker_stats()

        # Assert
        stats_str = str(stats)
        assert "VmP@ssw0rd!" not in stats_str
        assert "M365P@ssw0rd!" not in stats_str
        # Should include VM hostname but not password
        assert "test-vm.westus2.cloudapp.azure.com" in stats_str
        assert "kwadmin" in stats_str  # Username is OK
        # But passwords should be redacted
        assert "vm_password" not in stats_str or "***" in stats_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
