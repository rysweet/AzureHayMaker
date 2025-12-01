"""Unit tests for WinRMConnection class.

This module tests the WinRMConnection class that establishes and manages
WinRM connections to Windows VMs for Computer Use Knowledge Worker Agents.

Tests cover:
- Connection establishment and authentication
- Command execution via PowerShell
- File transfer to remote VM
- Connection cleanup and error handling
- Retry logic for transient failures
- Timeout handling

Uses pytest with mocks for WinRM protocol interactions.
"""

from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
# Note: These imports will fail until WinRMConnection is implemented
try:
    from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
        WinRMConnection,
        WinRMConnectionError,
        WinRMTimeoutError,
    )

    WINRM_AVAILABLE = True
except ImportError:
    WINRM_AVAILABLE = False
    WinRMConnection = None
    WinRMConnectionError = None
    WinRMTimeoutError = None


pytestmark = pytest.mark.skipif(
    not WINRM_AVAILABLE, reason="WinRMConnection not yet implemented"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def vm_config():
    """Fixture: Windows VM configuration."""
    return {
        "hostname": "test-vm.westus2.cloudapp.azure.com",
        "username": "kwadmin",
        "password": "SecureP@ssw0rd123!",
        "port": 5986,
        "transport": "ssl",
    }


@pytest.fixture
def mock_winrm_protocol():
    """Fixture: Mock WinRM protocol instance."""
    with patch("azure_haymaker.knowledge_worker.computer_use.winrm_connection.Protocol") as mock:
        protocol = MagicMock()
        mock.return_value = protocol

        # Mock shell operations
        shell_id = "shell-12345"
        protocol.open_shell.return_value = shell_id
        protocol.close_shell.return_value = None

        # Mock command execution
        command_id = "command-67890"
        protocol.run_command.return_value = command_id
        protocol.get_command_output.return_value = (b"Command output", b"", 0)
        protocol.cleanup_command.return_value = None

        yield protocol


@pytest.fixture
def winrm_connection(vm_config):
    """Fixture: WinRMConnection instance."""
    return WinRMConnection(
        hostname=vm_config["hostname"],
        username=vm_config["username"],
        password=vm_config["password"],
        port=vm_config["port"],
        transport=vm_config["transport"],
    )


# ==============================================================================
# CONNECTION TESTS
# ==============================================================================


class TestWinRMConnectionEstablishment:
    """Tests for WinRM connection establishment."""

    def test_connect_success(self, winrm_connection, mock_winrm_protocol):
        """Test successful WinRM connection establishment."""
        # Act
        winrm_connection.connect()

        # Assert
        assert winrm_connection.is_connected is True
        mock_winrm_protocol.open_shell.assert_called_once()

    def test_connect_with_invalid_credentials(self, vm_config, mock_winrm_protocol):
        """Test connection fails with invalid credentials."""
        # Arrange
        mock_winrm_protocol.open_shell.side_effect = Exception("401 Unauthorized")
        conn = WinRMConnection(
            hostname=vm_config["hostname"],
            username="invalid_user",
            password="wrong_password",
        )

        # Act & Assert
        with pytest.raises(WinRMConnectionError) as exc_info:
            conn.connect()
        assert "Unauthorized" in str(exc_info.value)
        assert conn.is_connected is False

    def test_connect_with_unreachable_host(self, mock_winrm_protocol):
        """Test connection fails with unreachable host."""
        # Arrange
        mock_winrm_protocol.open_shell.side_effect = Exception("Connection timeout")
        conn = WinRMConnection(
            hostname="unreachable.example.com",
            username="user",
            password="pass",
        )

        # Act & Assert
        with pytest.raises(WinRMConnectionError) as exc_info:
            conn.connect()
        assert "timeout" in str(exc_info.value).lower()

    def test_connect_idempotent(self, winrm_connection, mock_winrm_protocol):
        """Test connect is idempotent - calling twice doesn't error."""
        # Act
        winrm_connection.connect()
        winrm_connection.connect()  # Second call should be safe

        # Assert
        assert winrm_connection.is_connected is True
        # Should only open shell once
        assert mock_winrm_protocol.open_shell.call_count == 1


# ==============================================================================
# COMMAND EXECUTION TESTS
# ==============================================================================


class TestCommandExecution:
    """Tests for PowerShell command execution."""

    def test_execute_command_simple(self, winrm_connection, mock_winrm_protocol):
        """Test execute simple PowerShell command."""
        # Arrange
        winrm_connection.connect()
        mock_winrm_protocol.get_command_output.return_value = (
            b"Hello World\r\n",
            b"",
            0,
        )

        # Act
        result = winrm_connection.execute_command("Write-Host 'Hello World'")

        # Assert
        assert result["stdout"] == "Hello World"
        assert result["stderr"] == ""
        assert result["exit_code"] == 0
        assert result["success"] is True

    def test_execute_command_with_error(self, winrm_connection, mock_winrm_protocol):
        """Test execute command that returns error."""
        # Arrange
        winrm_connection.connect()
        mock_winrm_protocol.get_command_output.return_value = (
            b"",
            b"Error: File not found\r\n",
            1,
        )

        # Act
        result = winrm_connection.execute_command("Get-Item C:\\nonexistent.txt")

        # Assert
        assert result["stdout"] == ""
        assert "File not found" in result["stderr"]
        assert result["exit_code"] == 1
        assert result["success"] is False

    def test_execute_command_without_connection(self, winrm_connection):
        """Test execute_command fails if not connected."""
        # Act & Assert
        with pytest.raises(WinRMConnectionError) as exc_info:
            winrm_connection.execute_command("Get-Process")
        assert "not connected" in str(exc_info.value).lower()

    def test_execute_command_with_timeout(self, winrm_connection, mock_winrm_protocol):
        """Test execute_command respects timeout parameter."""
        # Arrange
        winrm_connection.connect()
        mock_winrm_protocol.get_command_output.side_effect = TimeoutError(
            "Command exceeded timeout"
        )

        # Act & Assert
        with pytest.raises(WinRMTimeoutError) as exc_info:
            winrm_connection.execute_command("Start-Sleep -Seconds 300", timeout=5)
        assert "timeout" in str(exc_info.value).lower()


# ==============================================================================
# FILE TRANSFER TESTS
# ==============================================================================


class TestFileTransfer:
    """Tests for file copy operations."""

    def test_copy_file_success(self, winrm_connection, mock_winrm_protocol, tmp_path):
        """Test successful file copy to remote VM."""
        # Arrange
        winrm_connection.connect()
        local_file = tmp_path / "test_script.ps1"
        local_file.write_text("Write-Host 'Test'")
        remote_path = "C:\\Temp\\test_script.ps1"

        mock_winrm_protocol.get_command_output.return_value = (b"File copied", b"", 0)

        # Act
        result = winrm_connection.copy_file(str(local_file), remote_path)

        # Assert
        assert result is True
        # Should execute base64 copy commands
        assert mock_winrm_protocol.run_command.call_count >= 1

    def test_copy_file_nonexistent_local(self, winrm_connection, mock_winrm_protocol):
        """Test copy_file fails with nonexistent local file."""
        # Arrange
        winrm_connection.connect()
        local_path = "/nonexistent/file.txt"
        remote_path = "C:\\Temp\\file.txt"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            winrm_connection.copy_file(local_path, remote_path)

    def test_copy_file_without_connection(self, winrm_connection, tmp_path):
        """Test copy_file fails if not connected."""
        # Arrange
        local_file = tmp_path / "test.txt"
        local_file.write_text("content")

        # Act & Assert
        with pytest.raises(WinRMConnectionError) as exc_info:
            winrm_connection.copy_file(str(local_file), "C:\\Temp\\test.txt")
        assert "not connected" in str(exc_info.value).lower()


# ==============================================================================
# CLEANUP TESTS
# ==============================================================================


class TestConnectionCleanup:
    """Tests for connection cleanup and disconnection."""

    def test_disconnect_success(self, winrm_connection, mock_winrm_protocol):
        """Test successful disconnection."""
        # Arrange
        winrm_connection.connect()
        assert winrm_connection.is_connected is True

        # Act
        winrm_connection.disconnect()

        # Assert
        assert winrm_connection.is_connected is False
        mock_winrm_protocol.close_shell.assert_called_once()

    def test_disconnect_idempotent(self, winrm_connection, mock_winrm_protocol):
        """Test disconnect is idempotent - safe to call multiple times."""
        # Arrange
        winrm_connection.connect()

        # Act
        winrm_connection.disconnect()
        winrm_connection.disconnect()  # Second call should be safe

        # Assert
        assert winrm_connection.is_connected is False
        # Should only close shell once
        assert mock_winrm_protocol.close_shell.call_count == 1

    def test_context_manager_cleanup(self, vm_config, mock_winrm_protocol):
        """Test WinRMConnection works as context manager with automatic cleanup."""
        # Act
        with WinRMConnection(
            hostname=vm_config["hostname"],
            username=vm_config["username"],
            password=vm_config["password"],
        ) as conn:
            conn.connect()
            assert conn.is_connected is True

        # Assert - connection closed automatically
        mock_winrm_protocol.close_shell.assert_called_once()


# ==============================================================================
# SECURITY TESTS
# ==============================================================================


class TestSecurityControls:
    """Tests for security controls and validations."""

    def test_certificate_validation_enabled(self, vm_config, mock_winrm_protocol):
        """Test that certificate validation is enabled by default."""
        # Arrange
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import Protocol

        # Act
        conn = WinRMConnection(
            hostname=vm_config["hostname"],
            username=vm_config["username"],
            password=vm_config["password"],
        )
        conn.connect()

        # Assert - Protocol should be called with validation enabled
        protocol_call = Protocol.call_args
        assert protocol_call is not None
        assert protocol_call.kwargs["server_cert_validation"] == "validate"

    def test_path_traversal_validation(self, tmp_path, mock_winrm_protocol):
        """Test that path traversal attempts are blocked."""
        # Arrange
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
            WinRMConnection,
        )

        # Create connection but don't call connect() to avoid Protocol issues
        conn = WinRMConnection(
            hostname="test-vm.example.com",
            username="test",
            password="test",
        )
        # Manually set connected state for testing
        conn.is_connected = True
        conn._protocol = mock_winrm_protocol
        conn._shell_id = "test-shell"

        local_file = tmp_path / "test.txt"
        local_file.write_text("content")

        # Act & Assert - should reject path traversal
        with pytest.raises(ValueError, match=".") as exc_info:
            conn.copy_file(str(local_file), "C:\\..\\..\\etc\\passwd")
        assert "dangerous pattern" in str(exc_info.value)

    def test_powershell_injection_protection(self):
        """Test that PowerShell arguments are properly escaped."""
        # Act
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
            WinRMConnection,
        )

        malicious_input = "test'; Remove-Item C:\\* -Recurse; '"
        escaped = WinRMConnection._escape_powershell_arg(malicious_input)

        # Assert - single quotes should be doubled and wrapped
        assert "''" in escaped  # Single quotes doubled
        assert escaped.startswith("'")
        assert escaped.endswith("'")

    def test_null_byte_in_path_rejected(self, tmp_path, mock_winrm_protocol):
        """Test that paths with null bytes are rejected."""
        # Arrange
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
            WinRMConnection,
        )

        conn = WinRMConnection(
            hostname="test-vm.example.com",
            username="test",
            password="test",
        )
        # Manually set connected state for testing
        conn.is_connected = True
        conn._protocol = mock_winrm_protocol
        conn._shell_id = "test-shell"

        local_file = tmp_path / "test.txt"
        local_file.write_text("content")

        # Act & Assert
        with pytest.raises(ValueError, match=".") as exc_info:
            conn.copy_file(str(local_file), "C:\\test\0.txt")
        assert "null byte" in str(exc_info.value)

    def test_invalid_windows_path_format_rejected(self, tmp_path, mock_winrm_protocol):
        """Test that invalid Windows path formats are rejected."""
        # Arrange
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
            WinRMConnection,
        )

        conn = WinRMConnection(
            hostname="test-vm.example.com",
            username="test",
            password="test",
        )
        # Manually set connected state for testing
        conn.is_connected = True
        conn._protocol = mock_winrm_protocol
        conn._shell_id = "test-shell"

        local_file = tmp_path / "test.txt"
        local_file.write_text("content")

        # Act & Assert - Unix-style path should be rejected
        with pytest.raises(ValueError, match=".") as exc_info:
            conn.copy_file(str(local_file), "/etc/passwd")
        assert "Invalid Windows path format" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
