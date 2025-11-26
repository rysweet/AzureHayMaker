"""Azure Entra App Registration Setup for Knowledge Workers.

Provides classes and functions for creating and configuring the
Azure Entra app registration required for Knowledge Worker operations.

Example:
    >>> from azure_haymaker.knowledge_worker.infrastructure import setup_kw_app
    >>> config = setup_kw_app(tenant_id="your-tenant-id")
    >>> print(config.admin_consent_url)  # Open this in browser
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Microsoft Graph API ID
GRAPH_API_ID = "00000003-0000-0000-c000-000000000000"

# Required Microsoft Graph permissions for Knowledge Workers
# Format: {permission_name: (permission_id, type)}
# Type: "Role" for Application, "Scope" for Delegated
KW_PERMISSIONS = {
    "User.ReadWrite.All": ("741f803b-c850-494e-b5df-cde7c675a1ca", "Role"),
    "Mail.ReadWrite": ("e2a3a72e-5f79-4c64-b1b1-878b674786c9", "Role"),
    "Mail.Send": ("b633e1c5-b582-4048-a93e-9f11b44c7e96", "Role"),
    "Team.Create": ("23fc2474-f741-46ce-8465-674744c5c361", "Role"),
    "Calendars.ReadWrite": ("ef54d2bf-783f-4e0f-bca1-3210c0444d99", "Role"),
    "Files.ReadWrite.All": ("75359482-378d-4052-8f01-80520e7db3cd", "Role"),
    "Directory.ReadWrite.All": ("19dbc75e-c2e2-444c-a770-ec69d8559fc7", "Role"),
}


@dataclass
class KWAppConfig:
    """Configuration for the Knowledge Worker app registration.

    Attributes:
        app_id: Azure app (client) ID
        client_secret: Client secret for authentication
        tenant_id: Azure tenant ID
        sp_id: Service principal object ID
        admin_consent_url: URL to grant admin consent
        admin_consent_granted: Whether admin consent has been granted
        created_at: When the config was created
    """

    app_id: str
    client_secret: str
    tenant_id: str
    sp_id: str = ""
    admin_consent_url: str = ""
    admin_consent_granted: bool = False
    created_at: str = ""

    def __post_init__(self) -> None:
        """Generate admin consent URL if not provided."""
        if not self.admin_consent_url and self.tenant_id and self.app_id:
            self.admin_consent_url = (
                f"https://login.microsoftonline.com/{self.tenant_id}/"
                f"adminconsent?client_id={self.app_id}"
            )
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"

    def to_env_dict(self) -> dict[str, str]:
        """Convert to environment variable dictionary.

        Returns:
            Dictionary of environment variable names to values
        """
        return {
            "KW_APP_ID": self.app_id,
            "KW_CLIENT_SECRET": self.client_secret,
            "KW_TENANT_ID": self.tenant_id,
            "KW_SP_ID": self.sp_id,
        }

    def to_env_string(self) -> str:
        """Convert to .env file format string.

        Returns:
            String in .env file format
        """
        lines = [
            "# Knowledge Worker App Configuration",
            f"# Generated: {self.created_at}",
            "",
            f"KW_APP_ID={self.app_id}",
            f"KW_CLIENT_SECRET={self.client_secret}",
            f"KW_TENANT_ID={self.tenant_id}",
            f"KW_SP_ID={self.sp_id}",
            "",
            "# Admin consent URL (open in browser as tenant admin)",
            f"# {self.admin_consent_url}",
        ]
        return "\n".join(lines)


class KWAppSetup:
    """Sets up Azure Entra app registration for Knowledge Workers.

    Uses Azure CLI to create and configure the app registration.
    Requires Azure CLI to be installed and logged in with appropriate
    permissions (Application Administrator or Global Administrator).

    Example:
        >>> setup = KWAppSetup(tenant_id="your-tenant-id")
        >>> config = setup.setup_app()
        >>> print(config.admin_consent_url)
    """

    def __init__(
        self,
        tenant_id: str | None = None,
        app_name: str = "haymaker-knowledge-worker",
    ):
        """Initialize KW app setup.

        Args:
            tenant_id: Azure tenant ID (auto-detected if not provided)
            app_name: Display name for the app registration
        """
        self.tenant_id = tenant_id or self._get_tenant_id()
        self.app_name = app_name

    def _run_az_command(self, args: list[str]) -> dict[str, Any]:
        """Run Azure CLI command and return JSON result.

        Args:
            args: Command arguments (without 'az')

        Returns:
            Parsed JSON response

        Raises:
            RuntimeError: If command fails
        """
        cmd = ["az"] + args + ["-o", "json"]
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout:
                return json.loads(result.stdout)
            return {}
        except subprocess.CalledProcessError as e:
            logger.error(f"Azure CLI error: {e.stderr}")
            raise RuntimeError(f"Azure CLI command failed: {e.stderr}") from e
        except json.JSONDecodeError:
            return {}

    def _get_tenant_id(self) -> str:
        """Get tenant ID from current Azure CLI login.

        Returns:
            Tenant ID

        Raises:
            RuntimeError: If not logged in or can't get tenant ID
        """
        try:
            result = self._run_az_command(["account", "show"])
            return result.get("tenantId", "")
        except RuntimeError:
            raise RuntimeError(
                "Not logged in to Azure CLI. Run 'az login' first."
            )

    def check_existing_app(self) -> str | None:
        """Check if app already exists.

        Returns:
            App ID if exists, None otherwise
        """
        try:
            result = self._run_az_command([
                "ad", "app", "list",
                "--filter", f"displayName eq '{self.app_name}'",
                "--query", "[0].appId",
            ])
            return result if isinstance(result, str) else None
        except RuntimeError:
            return None

    def create_app(self) -> str:
        """Create app registration.

        Returns:
            App ID

        Raises:
            RuntimeError: If creation fails
        """
        result = self._run_az_command([
            "ad", "app", "create",
            "--display-name", self.app_name,
            "--sign-in-audience", "AzureADMyOrg",
            "--query", "appId",
        ])
        return result if isinstance(result, str) else str(result)

    def add_permissions(self, app_id: str) -> None:
        """Add required Microsoft Graph permissions.

        Args:
            app_id: App ID to add permissions to
        """
        for perm_name, (perm_id, perm_type) in KW_PERMISSIONS.items():
            logger.info(f"Adding permission: {perm_name}")
            try:
                self._run_az_command([
                    "ad", "app", "permission", "add",
                    "--id", app_id,
                    "--api", GRAPH_API_ID,
                    "--api-permissions", f"{perm_id}={perm_type}",
                ])
            except RuntimeError as e:
                logger.warning(f"Error adding {perm_name}: {e}")

    def create_service_principal(self, app_id: str) -> str:
        """Create service principal for app.

        Args:
            app_id: App ID

        Returns:
            Service principal object ID
        """
        # Check if SP already exists
        try:
            result = self._run_az_command([
                "ad", "sp", "show",
                "--id", app_id,
                "--query", "id",
            ])
            return result if isinstance(result, str) else str(result)
        except RuntimeError:
            pass

        # Create SP
        result = self._run_az_command([
            "ad", "sp", "create",
            "--id", app_id,
            "--query", "id",
        ])
        return result if isinstance(result, str) else str(result)

    def create_client_secret(self, app_id: str) -> str:
        """Create client secret for app.

        Args:
            app_id: App ID

        Returns:
            Client secret value
        """
        result = self._run_az_command([
            "ad", "app", "credential", "reset",
            "--id", app_id,
            "--display-name", f"kw-secret-{datetime.now().strftime('%Y%m%d')}",
            "--years", "1",
            "--query", "password",
        ])
        return result if isinstance(result, str) else str(result)

    def setup_app(self, reuse_existing: bool = True) -> KWAppConfig:
        """Create and configure Knowledge Worker app registration.

        Args:
            reuse_existing: If True, reuse existing app if found

        Returns:
            KWAppConfig with app credentials and consent URL
        """
        logger.info(f"Setting up Knowledge Worker app in tenant {self.tenant_id}")

        # Check for existing app
        app_id = None
        if reuse_existing:
            app_id = self.check_existing_app()
            if app_id:
                logger.info(f"Found existing app: {app_id}")

        # Create app if needed
        if not app_id:
            logger.info("Creating app registration...")
            app_id = self.create_app()
            logger.info(f"Created app: {app_id}")

        # Add permissions
        logger.info("Adding Microsoft Graph permissions...")
        self.add_permissions(app_id)

        # Create service principal
        logger.info("Creating service principal...")
        sp_id = self.create_service_principal(app_id)
        logger.info(f"Service principal: {sp_id}")

        # Create client secret
        logger.info("Creating client secret...")
        client_secret = self.create_client_secret(app_id)

        # Create config
        config = KWAppConfig(
            app_id=app_id,
            client_secret=client_secret,
            tenant_id=self.tenant_id,
            sp_id=sp_id,
        )

        logger.info("App setup complete!")
        logger.info(f"Admin consent URL: {config.admin_consent_url}")

        return config


def setup_kw_app(
    tenant_id: str | None = None,
    app_name: str = "haymaker-knowledge-worker",
    reuse_existing: bool = True,
) -> KWAppConfig:
    """Create and configure Knowledge Worker app registration.

    Convenience function that creates a KWAppSetup and runs setup.

    Args:
        tenant_id: Azure tenant ID (auto-detected if not provided)
        app_name: Display name for the app registration
        reuse_existing: If True, reuse existing app if found

    Returns:
        KWAppConfig with app credentials and consent URL

    Example:
        >>> config = setup_kw_app()
        >>> print(f"Open this URL to grant consent: {config.admin_consent_url}")
        >>> print(config.to_env_string())
    """
    setup = KWAppSetup(tenant_id=tenant_id, app_name=app_name)
    return setup.setup_app(reuse_existing=reuse_existing)
