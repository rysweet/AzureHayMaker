"""Automatic Graph API permission granting for Knowledge Worker deployments."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PermissionGranter:
    """Grant required Graph API permissions automatically."""

    # Mail.ReadWrite app role ID (from Microsoft Graph)
    MAIL_READWRITE_ROLE_ID = "e2a3a72e-5f79-4c64-b1b1-878b674786c9"

    # Microsoft Graph resource app ID
    GRAPH_RESOURCE_APP_ID = "00000003-0000-0000-c000-000000000000"

    def __init__(self, graph_client: Any, app_id: str):
        """Initialize permission granter.

        Args:
            graph_client: Microsoft Graph API client
            app_id: Application (client) ID
        """
        self.graph_client = graph_client
        self.app_id = app_id

    async def ensure_mail_permission(self) -> bool:
        """Ensure Mail.ReadWrite permission is granted.

        Idempotent - safe to call multiple times.

        Returns:
            True if permission granted or already exists
        """
        try:
            # Get our service principal object ID
            sp = await self._get_service_principal(self.app_id)
            if not sp:
                logger.error(f"Service principal not found for app {self.app_id}")
                return False

            sp_object_id = sp.id

            # Get Microsoft Graph service principal
            graph_sp = await self._get_service_principal(self.GRAPH_RESOURCE_APP_ID)
            if not graph_sp:
                logger.error("Microsoft Graph service principal not found")
                return False

            graph_sp_id = graph_sp.id

            # Check if Mail.ReadWrite already granted
            if await self._has_permission(sp_object_id, self.MAIL_READWRITE_ROLE_ID):
                logger.info("Mail.ReadWrite permission already granted")
                return True

            # Grant Mail.ReadWrite
            logger.info(f"Granting Mail.ReadWrite permission to {self.app_id}")

            return await self._grant_app_role(
                sp_object_id, graph_sp_id, self.MAIL_READWRITE_ROLE_ID
            )

        except Exception as e:
            logger.error(f"Failed to ensure Mail permission: {e}")
            return False

    async def _get_service_principal(self, app_id: str) -> Any:
        """Get service principal by app ID."""
        try:
            result = await self.graph_client.service_principals.get(
                request_configuration={"query_parameters": {"filter": f"appId eq '{app_id}'"}}
            )

            if result and result.value and len(result.value) > 0:
                return result.value[0]

            return None

        except Exception as e:
            logger.warning(f"Failed to get service principal {app_id}: {e}")
            return None

    async def _has_permission(self, sp_object_id: str, app_role_id: str) -> bool:
        """Check if permission already granted."""
        try:
            assignments = await self.graph_client.service_principals.by_service_principal_id(
                sp_object_id
            ).app_role_assignments.get()

            if not assignments or not assignments.value:
                return False

            for assignment in assignments.value:
                # Compare UUIDs properly - app_role_id is UUID object, parameter is string
                if str(assignment.app_role_id) == str(app_role_id):
                    return True

            return False

        except Exception as e:
            logger.warning(f"Failed to check permissions: {e}")
            return False

    async def _grant_app_role(self, principal_id: str, resource_id: str, app_role_id: str) -> bool:
        """Grant app role assignment."""
        try:
            from msgraph.generated.models.app_role_assignment import AppRoleAssignment

            assignment = AppRoleAssignment()
            assignment.principal_id = principal_id
            assignment.resource_id = resource_id
            assignment.app_role_id = app_role_id

            await self.graph_client.service_principals.by_service_principal_id(
                resource_id
            ).app_role_assigned_to.post(assignment)

            logger.info(f"Granted app role {app_role_id}")
            return True

        except Exception as e:
            error_str = str(e)
            if "already exists" in error_str.lower():
                logger.info("Permission already granted")
                return True
            else:
                logger.error(f"Failed to grant app role: {e}")
                return False


__all__ = ["PermissionGranter"]
