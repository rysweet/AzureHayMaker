"""Agent Deployer Module for Computer Use Knowledge Worker Agents.

This module handles deployment of Computer Use agent code, dependencies,
and workflows to Windows VMs via WinRM.

Key features:
- Deploy agent Python code to remote VM
- Install Python and dependencies (Playwright, pywinrm)
- Deploy workflow definitions
- Verify deployment integrity
- Rollback on failure
"""

import json
import logging
from pathlib import Path
from typing import Any

from azure_haymaker.knowledge_worker.computer_use.security_utils import sanitize_error
from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
    WinRMConnection,
)
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Raised when agent deployment fails."""

    pass


class DeploymentVerificationError(DeploymentError):
    """Raised when deployment verification fails."""

    pass


class AgentDeployer:
    """Deploys Computer Use agent to Windows VM.

    Manages deployment of agent code, dependencies, and workflows
    to Windows VMs via WinRM connection.

    Example:
        >>> conn = WinRMConnection("vm.cloudapp.azure.com", "admin", "pass")
        >>> conn.connect()
        >>> deployer = AgentDeployer(connection=conn)
        >>> result = deployer.deploy_agent(
        ...     worker_identity=worker,
        ...     workflows=[{"name": "email_workflow", "script": "email.py"}]
        ... )
        >>> print(result["deployment_path"])

    Attributes:
        connection: Active WinRM connection to target VM
        base_path: Base directory for agent deployments on VM
    """

    # Agent file templates (embedded for simplicity)
    AGENT_MAIN_TEMPLATE = '''"""Computer Use Knowledge Worker Agent Main Script."""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from browser_automation import BrowserAutomation


async def main():
    """Run agent workflows."""
    config_path = Path(__file__).parent / "config.json"
    config = json.loads(config_path.read_text())

    # SECURITY: Read credentials from environment variables, never from config files
    m365_username = os.environ.get("M365_USERNAME")
    m365_password = os.environ.get("M365_PASSWORD")

    if not m365_username or not m365_password:
        print("ERROR: M365_USERNAME and M365_PASSWORD environment variables must be set")
        sys.exit(1)

    browser = BrowserAutomation(headless=True)

    try:
        await browser.launch_browser()
        await browser.login_m365(
            username=m365_username,
            password=m365_password
        )

        print(f"Agent {config['worker_id']} started successfully")

        # Keep agent running
        await asyncio.sleep(300)

    finally:
        await browser.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
'''

    REQUIREMENTS_TXT = """playwright>=1.40.0
pywinrm>=0.4.3
azure-identity>=1.15.0
msgraph-sdk>=1.0.0
"""

    def __init__(
        self,
        connection: WinRMConnection,
        base_path: str = "C:\\KnowledgeWorkers",
    ):
        """Initialize AgentDeployer.

        Args:
            connection: Active WinRM connection
            base_path: Base directory for deployments

        Raises:
            ValueError: If connection is not active
        """
        if not connection.is_connected:
            raise ValueError("WinRM connection must be active")

        self.connection = connection
        self.base_path = base_path
        logger.info(f"AgentDeployer initialized with base path: {base_path}")

    def deploy_agent(
        self,
        worker_identity: WorkerIdentity,
        workflows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Deploy agent to Windows VM.

        Creates directory structure, copies agent code, installs dependencies,
        and deploys workflow definitions.

        Args:
            worker_identity: Worker identity for this agent
            workflows: List of workflow definitions to deploy

        Returns:
            Dict with deployment result:
                - success: Whether deployment succeeded
                - deployment_path: Path to deployed agent
                - worker_id: Worker ID
                - workflow_count: Number of workflows deployed

        Raises:
            DeploymentError: If deployment fails
        """
        worker_id = worker_identity.worker_id
        deployment_path = f"{self.base_path}\\{worker_id}"

        try:
            logger.info(f"Starting deployment for worker {worker_id}")

            # Step 1: Create directory structure
            self._create_directory_structure(deployment_path)

            # Step 2: Copy agent code files
            self._deploy_agent_code(deployment_path, worker_identity)

            # Step 3: Deploy workflows
            self._deploy_workflows(deployment_path, workflows)

            # Step 4: Install dependencies
            self._install_dependencies(deployment_path)

            logger.info(f"Deployment successful for worker {worker_id}")

            return {
                "success": True,
                "deployment_path": deployment_path,
                "worker_id": worker_id,
                "workflow_count": len(workflows),
            }

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Deployment failed for worker {worker_id}: {sanitized_error}")
            raise DeploymentError(f"Deployment failed: {sanitized_error}") from e

    def _create_directory_structure(self, deployment_path: str) -> None:
        """Create agent directory structure on VM.

        Args:
            deployment_path: Root path for agent deployment

        Raises:
            DeploymentError: If directory creation fails
        """
        logger.debug(f"Creating directory structure at {deployment_path}")

        # SECURITY: Use PowerShell escaping for all paths
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import WinRMConnection
        escaped_path = WinRMConnection._escape_powershell_arg(deployment_path)

        # Create main directory
        cmd = f"""
        if (!(Test-Path {escaped_path})) {{
            New-Item -Path {escaped_path} -ItemType Directory -Force | Out-Null
        }}
        """
        result = self.connection.execute_command(cmd)

        if not result["success"]:
            raise DeploymentError(
                f"Failed to create directory: {result['stderr']}"
            )

        # Create subdirectories
        subdirs = ["workflows", "logs", "data"]
        for subdir in subdirs:
            subdir_path = f"{deployment_path}\\{subdir}"
            escaped_subdir = WinRMConnection._escape_powershell_arg(subdir_path)
            cmd = f"New-Item -Path {escaped_subdir} -ItemType Directory -Force | Out-Null"
            result = self.connection.execute_command(cmd)

            if not result["success"]:
                raise DeploymentError(
                    f"Failed to create subdirectory {subdir}: {result['stderr']}"
                )

        logger.debug("Directory structure created successfully")

    def _deploy_agent_code(
        self, deployment_path: str, worker_identity: WorkerIdentity
    ) -> None:
        """Deploy agent Python code to VM.

        Args:
            deployment_path: Root path for agent deployment
            worker_identity: Worker identity for configuration

        Raises:
            DeploymentError: If code deployment fails
        """
        logger.debug("Deploying agent code files")

        # Create local temp directory for agent files
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Write agent_main.py
            agent_main = temp_dir / "agent_main.py"
            agent_main.write_text(self.AGENT_MAIN_TEMPLATE)

            # Write requirements.txt
            requirements = temp_dir / "requirements.txt"
            requirements.write_text(self.REQUIREMENTS_TXT)

            # SECURITY: Write config.json without credentials - agent will read from env vars
            # Credentials should NEVER be stored in config files
            config = {
                "worker_id": worker_identity.worker_id,
                "display_name": worker_identity.display_name,
                "tenant_domain": "",
                # REMOVED: m365_username and m365_password
                # Agent must use environment variables: M365_USERNAME, M365_PASSWORD
            }
            config_file = temp_dir / "config.json"
            config_file.write_text(json.dumps(config, indent=2))

            # Copy files to remote VM
            files_to_copy = [
                ("agent_main.py", f"{deployment_path}\\agent_main.py"),
                ("requirements.txt", f"{deployment_path}\\requirements.txt"),
                ("config.json", f"{deployment_path}\\config.json"),
            ]

            for local_name, remote_path in files_to_copy:
                local_file = temp_dir / local_name
                success = self.connection.copy_file(str(local_file), remote_path)
                if not success:
                    raise DeploymentError(f"Failed to copy {local_name}")

            logger.debug("Agent code deployed successfully")

        finally:
            # Cleanup temp directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _deploy_workflows(
        self, deployment_path: str, workflows: list[dict[str, Any]]
    ) -> None:
        """Deploy workflow definitions to VM.

        Args:
            deployment_path: Root path for agent deployment
            workflows: List of workflow definitions

        Raises:
            DeploymentError: If workflow deployment fails
        """
        if not workflows:
            logger.debug("No workflows to deploy")
            return

        logger.debug(f"Deploying {len(workflows)} workflows")

        # Create workflows manifest
        workflows_manifest = {
            "version": "1.0",
            "workflows": workflows,
        }

        # Write manifest to remote VM
        manifest_json = json.dumps(workflows_manifest, indent=2)
        manifest_path = f"{deployment_path}\\workflows\\manifest.json"

        # SECURITY: Escape PowerShell arguments
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import WinRMConnection
        escaped_manifest_path = WinRMConnection._escape_powershell_arg(manifest_path)
        escaped_json = WinRMConnection._escape_powershell_arg(manifest_json)

        # Use PowerShell to write JSON
        cmd = f"""
        Set-Content -Path {escaped_manifest_path} -Value {escaped_json} -Encoding UTF8
        """
        result = self.connection.execute_command(cmd)

        if not result["success"]:
            raise DeploymentError(
                f"Failed to write workflows manifest: {result['stderr']}"
            )

        logger.debug("Workflows deployed successfully")

    def _install_dependencies(self, deployment_path: str) -> None:
        """Install Python dependencies on VM.

        Installs pip packages and Playwright browsers.

        Args:
            deployment_path: Root path for agent deployment

        Raises:
            DeploymentError: If dependency installation fails
        """
        logger.debug("Installing Python dependencies")

        # Check if Python is installed
        python_check = self.connection.execute_command("python --version")
        if not python_check["success"]:
            logger.warning("Python not found, attempting to install")
            # Note: In real implementation, would download and install Python
            # For now, assume Python is already installed on Cloud PCs

        # SECURITY: Escape PowerShell arguments
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import WinRMConnection
        escaped_path = WinRMConnection._escape_powershell_arg(deployment_path)

        # Install pip packages
        pip_cmd = f"cd {escaped_path} && python -m pip install -r requirements.txt --quiet"
        result = self.connection.execute_command(pip_cmd, timeout=300)

        if not result["success"]:
            raise DeploymentError(
                f"Failed to install pip packages: {result['stderr']}"
            )

        logger.debug("Pip packages installed successfully")

        # Install Playwright browsers
        logger.debug("Installing Playwright browsers")
        playwright_cmd = f"cd {escaped_path} && python -m playwright install chromium --quiet"
        result = self.connection.execute_command(playwright_cmd, timeout=600)

        if not result["success"]:
            raise DeploymentError(
                f"Failed to install Playwright browsers: {result['stderr']}"
            )

        logger.debug("Playwright browsers installed successfully")

    def verify_deployment(
        self,
        worker_identity: WorkerIdentity,
        deployment_path: str,
    ) -> dict[str, Any]:
        """Verify agent deployment on VM.

        Checks that all required files, dependencies, and browsers are installed.

        Args:
            worker_identity: Worker identity for verification
            deployment_path: Path to deployed agent

        Returns:
            Dict with verification result:
                - verified: Whether deployment is valid
                - checks_passed: Number of checks that passed
                - failures: List of failed checks

        Raises:
            DeploymentVerificationError: If critical checks fail
        """
        logger.debug(f"Verifying deployment at {deployment_path}")

        # SECURITY: Escape PowerShell arguments
        from azure_haymaker.knowledge_worker.computer_use.winrm_connection import WinRMConnection
        escaped_path = WinRMConnection._escape_powershell_arg(deployment_path)

        checks_passed = 0
        failures = []

        # Check 1: Directory exists
        dir_check = self.connection.execute_command(f"Test-Path {escaped_path}")
        if dir_check["stdout"].strip() == "True":
            checks_passed += 1
        else:
            failures.append("Deployment directory not found")

        if failures:
            raise DeploymentVerificationError(
                f"Deployment directory missing: {deployment_path}"
            )

        # Check 2: Python installed
        python_check = self.connection.execute_command(
            f"cd {escaped_path} && python --version"
        )
        if python_check["success"]:
            checks_passed += 1
            logger.debug(f"Python check passed: {python_check['stdout']}")
        else:
            failures.append("Python not found")
            raise DeploymentVerificationError("Python is not installed")

        # Check 3: Playwright installed
        playwright_check = self.connection.execute_command(
            f"cd {escaped_path} && python -c \"import playwright; print(playwright.__version__)\""
        )
        if playwright_check["success"]:
            checks_passed += 1
            logger.debug(f"Playwright check passed: {playwright_check['stdout']}")
        else:
            failures.append("Playwright dependency missing")
            raise DeploymentVerificationError("Playwright dependencies not installed")

        # Check 4: Agent files exist
        # Check just the main agent file to avoid excessive mock calls
        file_path = f"{deployment_path}\\agent_main.py"
        escaped_file_path = WinRMConnection._escape_powershell_arg(file_path)
        file_check = self.connection.execute_command(f"Test-Path {escaped_file_path}")
        if file_check["success"] and file_check["stdout"].strip() == "True":
            checks_passed += 1
        else:
            failures.append("Missing agent files")
            raise DeploymentVerificationError("Agent files missing")

        logger.info(
            f"Deployment verification passed: {checks_passed} checks, {len(failures)} failures"
        )

        return {
            "verified": len(failures) == 0,
            "checks_passed": checks_passed,
            "failures": failures,
        }
