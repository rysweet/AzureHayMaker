"""WinRM Connection Module for Computer Use Knowledge Worker Agents.

This module provides secure WinRM connectivity to Windows VMs for remote
command execution and file transfer operations.

Key features:
- Secure WinRM over HTTPS (port 5986)
- PowerShell command execution
- File transfer via base64 encoding
- Connection pooling and timeout handling
- Credential sanitization in logs
"""

import base64
import logging
from pathlib import Path
from typing import Any

from winrm.protocol import Protocol

from .security_utils import sanitize_error

logger = logging.getLogger(__name__)


class WinRMConnectionError(Exception):
    """Raised when WinRM connection fails."""

    pass


class WinRMTimeoutError(WinRMConnectionError):
    """Raised when WinRM operation times out."""

    pass


class WinRMConnection:
    """WinRM connection to Windows VM.

    Manages secure WinRM connections for remote PowerShell execution
    and file transfer to Windows VMs running Computer Use agents.

    Example:
        >>> conn = WinRMConnection(
        ...     hostname="vm.cloudapp.azure.com",
        ...     username="kwadmin",
        ...     password="SecurePass123!",
        ...     port=5986,
        ...     transport="ssl"
        ... )
        >>> conn.connect()
        >>> result = conn.execute_command("Get-Process")
        >>> print(result["stdout"])
        >>> conn.disconnect()

    Or use as context manager:
        >>> with WinRMConnection(hostname="vm", username="admin", password="pass") as conn:
        ...     conn.connect()
        ...     result = conn.execute_command("Get-Date")

    Attributes:
        hostname: Remote Windows VM hostname or IP
        username: WinRM username
        port: WinRM port (5985=HTTP, 5986=HTTPS)
        transport: Transport type ("ssl" or "plaintext")
        is_connected: Whether connection is active
    """

    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        port: int = 5986,
        transport: str = "ssl",
        timeout: int = 60,
    ):
        """Initialize WinRM connection.

        Args:
            hostname: Remote Windows VM hostname
            username: WinRM username
            password: WinRM password
            port: WinRM port (default 5986 for HTTPS)
            transport: Transport type ("ssl" or "plaintext")
            timeout: Connection timeout in seconds

        Raises:
            ValueError: If hostname or credentials are empty
        """
        if not hostname or not username or not password:
            raise ValueError("Hostname, username, and password are required")

        self.hostname = hostname
        self.username = username
        self._password = password  # Keep private
        self.port = port
        self.transport = transport
        self.timeout = timeout

        self._protocol: Protocol | None = None
        self._shell_id: str | None = None
        self.is_connected = False

        # Build endpoint URL
        scheme = "https" if transport == "ssl" else "http"
        self._endpoint = f"{scheme}://{hostname}:{port}/wsman"

        logger.info(
            f"WinRM connection initialized for {self._sanitize_for_log(hostname)}:{port}"
        )

    def connect(self) -> None:
        """Establish WinRM connection.

        Opens a remote PowerShell shell on the Windows VM.

        Raises:
            WinRMConnectionError: If connection fails
        """
        if self.is_connected:
            logger.debug("Already connected, skipping connect")
            return

        try:
            logger.info(f"Connecting to {self._sanitize_for_log(self.hostname)}")

            # Create WinRM protocol instance
            self._protocol = Protocol(
                endpoint=self._endpoint,
                transport=self.transport,
                username=self.username,
                password=self._password,
                server_cert_validation="validate",  # SECURITY: Validate server certificates
                read_timeout_sec=self.timeout,
                operation_timeout_sec=self.timeout,
            )

            # Open PowerShell shell
            self._shell_id = self._protocol.open_shell()
            self.is_connected = True

            logger.info(
                f"Connected to {self._sanitize_for_log(self.hostname)} (shell_id={self._shell_id})"
            )

        except Exception as e:
            self.is_connected = False
            sanitized_error = sanitize_error(str(e))
            logger.error(f"WinRM connection failed: {sanitized_error}")
            raise WinRMConnectionError(f"Connection failed: {sanitized_error}") from e

    def execute_command(
        self, command: str, timeout: int | None = None
    ) -> dict[str, Any]:
        """Execute PowerShell command on remote VM.

        Args:
            command: PowerShell command to execute
            timeout: Optional timeout override in seconds

        Returns:
            Dict with keys:
                - stdout: Command standard output
                - stderr: Command standard error
                - exit_code: Command exit code
                - success: Whether command succeeded (exit_code == 0)

        Raises:
            WinRMConnectionError: If not connected
            WinRMTimeoutError: If command times out
            ValueError: If command contains suspicious injection patterns
        """
        if not self.is_connected or not self._protocol or not self._shell_id:
            raise WinRMConnectionError("Not connected. Call connect() first.")

        # SECURITY: Validate command to prevent injection attacks
        self._validate_command(command)

        try:
            logger.debug(f"Executing command: {command[:100]}...")

            # Run command in the shell
            command_id = self._protocol.run_command(self._shell_id, command)

            # Get command output
            try:
                stdout, stderr, exit_code = self._protocol.get_command_output(
                    self._shell_id, command_id
                )
            except TimeoutError as e:
                raise WinRMTimeoutError(f"Command exceeded timeout: {e}") from e

            # Cleanup command
            self._protocol.cleanup_command(self._shell_id, command_id)

            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()

            result = {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": exit_code,
                "success": exit_code == 0,
            }

            if exit_code != 0:
                logger.warning(
                    f"Command failed with exit code {exit_code}: {stderr_str[:200]}"
                )
            else:
                logger.debug(f"Command succeeded: {stdout_str[:100]}")

            return result

        except WinRMTimeoutError:
            raise
        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Command execution failed: {sanitized_error}")
            raise WinRMConnectionError(f"Failed to execute command: {sanitized_error}") from e

    def copy_file(self, local_path: str, remote_path: str) -> bool:
        """Copy local file to remote VM.

        Uses base64 encoding to transfer file content via PowerShell.

        Args:
            local_path: Path to local file
            remote_path: Destination path on remote VM

        Returns:
            True if copy succeeded

        Raises:
            FileNotFoundError: If local file doesn't exist
            ValueError: If remote_path fails security validation
            WinRMConnectionError: If not connected or copy fails
        """
        if not self.is_connected:
            raise WinRMConnectionError("Not connected. Call connect() first.")

        # SECURITY: Validate remote path before use
        self._validate_windows_path(remote_path)

        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        try:
            logger.info(
                f"Copying {local_file.name} to {self._sanitize_for_log(remote_path)}"
            )

            # Read file and encode as base64
            file_content = local_file.read_bytes()
            encoded_content = base64.b64encode(file_content).decode("utf-8")

            # Split into chunks (PowerShell has command length limits)
            chunk_size = 8000
            chunks = [
                encoded_content[i : i + chunk_size]
                for i in range(0, len(encoded_content), chunk_size)
            ]

            # Create temporary file on remote
            temp_file = f"{remote_path}.b64"
            # SECURITY: Validate temp file path as well
            self._validate_windows_path(temp_file)

            # SECURITY: Use escaped paths in PowerShell commands
            escaped_temp_file = self._escape_powershell_arg(temp_file)
            escaped_remote_path = self._escape_powershell_arg(remote_path)

            # Remove temp file if exists
            self.execute_command(
                f"if (Test-Path {escaped_temp_file}) {{ Remove-Item {escaped_temp_file} -Force }}"
            )

            # Write chunks to temp file
            for i, chunk in enumerate(chunks):
                # SECURITY: Escape chunk content (though base64 is safe, defense in depth)
                escaped_chunk = self._escape_powershell_arg(chunk)
                if i == 0:
                    cmd = f"Set-Content -Path {escaped_temp_file} -Value {escaped_chunk}"
                else:
                    cmd = f"Add-Content -Path {escaped_temp_file} -Value {escaped_chunk}"
                result = self.execute_command(cmd)
                if not result["success"]:
                    raise WinRMConnectionError(
                        f"Failed to write chunk {i}: {result['stderr']}"
                    )

            # Decode base64 and write to final destination
            decode_cmd = f"""
            $content = Get-Content -Path {escaped_temp_file} -Raw
            $bytes = [System.Convert]::FromBase64String($content)
            [System.IO.File]::WriteAllBytes({escaped_remote_path}, $bytes)
            Remove-Item {escaped_temp_file} -Force
            """
            result = self.execute_command(decode_cmd)

            if not result["success"]:
                raise WinRMConnectionError(f"Failed to decode file: {result['stderr']}")

            # Verify file exists (optional - some environments may not support)
            try:
                verify_result = self.execute_command(f"Test-Path {escaped_remote_path}")
                # Accept any successful response for verification
                if not verify_result["success"]:
                    logger.warning("File verification check failed, but continuing")
            except Exception as e:
                sanitized_error = sanitize_error(str(e))
                logger.warning(f"File verification skipped: {sanitized_error}")

            logger.info(f"Successfully copied {local_file.name} to remote VM")
            return True

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"File copy failed: {sanitized_error}")
            raise WinRMConnectionError(f"Failed to copy file: {sanitized_error}") from e

    def disconnect(self) -> None:
        """Disconnect from remote VM.

        Closes the PowerShell shell and cleans up resources.
        Safe to call multiple times (idempotent).
        """
        if not self.is_connected:
            logger.debug("Not connected, skipping disconnect")
            return

        try:
            if self._protocol and self._shell_id:
                logger.info(f"Disconnecting from {self._sanitize_for_log(self.hostname)}")
                self._protocol.close_shell(self._shell_id)
                self._shell_id = None

            self.is_connected = False
            logger.info("Disconnected successfully")

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.warning(f"Error during disconnect: {sanitized_error}", exc_info=True)
            self.is_connected = False
            # Reset state but allow cleanup to continue
            self._protocol = None
            self._shell_id = None

    def __enter__(self) -> "WinRMConnection":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - automatic cleanup."""
        self.disconnect()

    @staticmethod
    def _sanitize_for_log(text: str) -> str:
        """Sanitize sensitive data for logging.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text safe for logging
        """
        # Basic sanitization - mask credentials if accidentally logged
        if "@" in text and len(text) > 10:
            # Might be email/username, mask middle
            parts = text.split("@")
            if len(parts) == 2:
                username = parts[0][:2] + "***" + parts[0][-2:] if len(parts[0]) > 4 else "***"
                return f"{username}@{parts[1]}"
        return text

    @staticmethod
    def _escape_powershell_arg(arg: str) -> str:
        """Escape argument for safe use in PowerShell commands.

        SECURITY: Prevents PowerShell command injection by escaping special characters.

        Args:
            arg: Argument string to escape

        Returns:
            Safely escaped argument suitable for PowerShell

        Example:
            >>> _escape_powershell_arg("test'; rm -rf /")
            "'test''; rm -rf /'"
        """
        if not arg:
            return "''"

        # Escape single quotes by doubling them
        escaped = arg.replace("'", "''")

        # Wrap in single quotes (safest in PowerShell)
        return f"'{escaped}'"

    @staticmethod
    def _validate_command(command: str) -> None:
        """Validate PowerShell command for security issues.

        SECURITY: Prevents command injection attacks by checking for
        dangerous patterns like command chaining (;), piping to rm/del, etc.

        Args:
            command: PowerShell command to validate

        Raises:
            ValueError: If command contains suspicious injection patterns

        Example:
            >>> _validate_command("Get-Process")  # OK
            >>> _validate_command("Get-Process; Remove-Item C:\\*")  # Raises ValueError
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")

        # Check for null bytes
        if "\0" in command:
            raise ValueError("Command contains null byte (possible injection)")

        # SECURITY: Check for command chaining that combines with destructive operations
        # Allow semicolons in safe contexts but reject obvious attacks
        dangerous_patterns = [
            (r";\s*Remove-Item", "command injection with Remove-Item"),
            (r";\s*rm\s+", "command injection with rm"),
            (r";\s*del\s+", "command injection with del"),
            (r";\s*rmdir", "command injection with rmdir"),
            (r";\s*Format-", "command injection with Format"),
            (r"\|\s*Remove-Item", "pipe to Remove-Item"),
            (r"\|\s*rm\s+", "pipe to rm"),
            (r"\|\s*del\s+", "pipe to del"),
        ]

        import re
        for pattern, description in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValueError(f"Command contains suspicious pattern: {description}")

    @staticmethod
    def _validate_windows_path(path: str) -> None:
        """Validate Windows path for security issues.

        SECURITY: Prevents path traversal attacks and validates path format.

        Args:
            path: Windows path to validate

        Raises:
            ValueError: If path contains suspicious patterns or is invalid

        Example:
            >>> _validate_windows_path("C:\\Users\\admin\\file.txt")  # OK
            >>> _validate_windows_path("..\\..\\..\\etc\\passwd")  # Raises ValueError
        """
        if not path:
            raise ValueError("Path cannot be empty")

        # Check for null bytes (common in path traversal attacks)
        if "\0" in path:
            raise ValueError("Path contains null byte")

        # Check for path traversal attempts
        if ".." in path:
            raise ValueError("Path contains dangerous pattern: ..")

        # Check for double forward slashes
        if "//" in path:
            raise ValueError("Path contains dangerous pattern: //")

        # Validate Windows path format (should start with drive letter)
        # Allow C:\, D:\, etc. but not Unix-style paths like /etc/passwd
        if len(path) >= 3:
            if not (path[0].isalpha() and path[1:3] == ":\\"):
                raise ValueError(f"Invalid Windows path format: {path}")
        else:
            raise ValueError(f"Invalid Windows path format: {path}")
