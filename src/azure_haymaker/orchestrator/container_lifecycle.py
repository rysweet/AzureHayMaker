"""Container App lifecycle management for Azure HayMaker.

This module manages Container App deletion and cleanup operations
on Azure.
"""

import asyncio
import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

# Configure logging
logger = logging.getLogger(__name__)


class ContainerAppError(Exception):
    """Raised when container app operations fail."""

    pass


class ContainerLifecycle:
    """Manages Container App lifecycle and cleanup operations.

    This class provides deletion and cleanup capabilities for deployed
    Container Apps on Azure.
    """

    def __init__(
        self,
        resource_group_name: str,
        subscription_id: str,
    ):
        """Initialize ContainerLifecycle with Azure resource identifiers.

        Args:
            resource_group_name: Azure resource group name
            subscription_id: Azure subscription ID

        Raises:
            ValueError: If parameters are invalid
        """
        if not resource_group_name or not subscription_id:
            raise ValueError("resource_group_name and subscription_id are required")

        self.resource_group_name = resource_group_name
        self.subscription_id = subscription_id

    async def delete(self, app_name: str) -> bool:
        """Delete container app.

        Initiates deletion of the specified Container App from Azure.
        Returns False if the app is not found (already deleted), otherwise
        returns True on successful deletion.

        Args:
            app_name: Name of the container app to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            ValueError: If app_name is empty
            ContainerAppError: If deletion fails (other than not found)
        """
        if not app_name:
            raise ValueError("App name is required")

        try:
            credential = DefaultAzureCredential()
            # Lazy import to avoid loading uninstalled package during testing
            from azure.mgmt.appcontainers import ContainerAppsAPIClient

            client = ContainerAppsAPIClient(
                credential=credential,
                subscription_id=self.subscription_id,
            )

            logger.info(f"Deleting container app {app_name}")

            poller = await asyncio.to_thread(
                client.container_apps.begin_delete,
                resource_group_name=self.resource_group_name,
                container_app_name=app_name,
            )

            await asyncio.to_thread(poller.result)

            logger.info(f"Container app {app_name} deleted successfully")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Container app {app_name} not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Failed to delete container app {app_name}: {e}")
            raise ContainerAppError(f"Failed to delete container app: {e}") from e


# Standalone async function for backward compatibility


async def delete_container_app(
    app_name: str,
    resource_group_name: str,
    subscription_id: str,
) -> bool:
    """Delete container app.

    This is a standalone convenience function that wraps ContainerLifecycle.

    Args:
        app_name: Name of the container app to delete
        resource_group_name: Resource group containing the app
        subscription_id: Azure subscription ID

    Returns:
        True if deleted successfully, False if not found

    Raises:
        ValueError: If required parameters are missing
        ContainerAppError: If deletion fails (other than not found)
    """
    if not app_name or not resource_group_name or not subscription_id:
        raise ValueError("app_name, resource_group_name, and subscription_id are required")

    lifecycle = ContainerLifecycle(
        resource_group_name=resource_group_name,
        subscription_id=subscription_id,
    )
    return await lifecycle.delete(app_name)
