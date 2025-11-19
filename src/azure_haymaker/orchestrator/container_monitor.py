"""Container App status monitoring for Azure HayMaker.

This module provides status checking and health monitoring for deployed
Container Apps on Azure.
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


class ContainerMonitor:
    """Monitors Container App status and health.

    This class provides status checking capabilities for deployed Container Apps,
    querying Azure to determine running status and provisioning state.
    """

    def __init__(
        self,
        resource_group_name: str,
        subscription_id: str,
    ):
        """Initialize ContainerMonitor with Azure resource identifiers.

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

    async def get_status(self, app_name: str) -> str:
        """Get current status of container app.

        Queries Azure Container Apps API to determine the current status
        of the specified container app.

        Args:
            app_name: Name of the container app

        Returns:
            Status string (Running, Provisioning, Failed, etc.)

        Raises:
            ValueError: If app_name is empty
            ContainerAppError: If status check fails
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

            logger.info(f"Checking status of container app {app_name}")

            app = await asyncio.to_thread(
                client.container_apps.get,
                resource_group_name=self.resource_group_name,
                container_app_name=app_name,
            )

            # Determine status from provisioning_state and running_status
            if hasattr(app, "running_status") and app.running_status:
                status = app.running_status
            elif hasattr(app, "provisioning_state") and app.provisioning_state:
                status = app.provisioning_state
            else:
                status = "Unknown"

            logger.info(f"Container app {app_name} status: {status}")
            return status

        except ResourceNotFoundError as e:
            logger.error(f"Container app {app_name} not found")
            raise ContainerAppError(f"Container app {app_name} not found: {e}") from e
        except Exception as e:
            logger.error(f"Failed to get container status for {app_name}: {e}")
            raise ContainerAppError(f"Failed to get container status: {e}") from e


# Standalone async function for backward compatibility


async def get_container_status(
    app_name: str,
    resource_group_name: str,
    subscription_id: str,
) -> str:
    """Get current status of container app.

    This is a standalone convenience function that wraps ContainerMonitor.

    Args:
        app_name: Name of the container app
        resource_group_name: Resource group containing the app
        subscription_id: Azure subscription ID

    Returns:
        Status string (Running, Provisioning, Failed, etc.)

    Raises:
        ValueError: If required parameters are missing
        ContainerAppError: If status check fails
    """
    if not app_name or not resource_group_name or not subscription_id:
        raise ValueError("app_name, resource_group_name, and subscription_id are required")

    monitor = ContainerMonitor(
        resource_group_name=resource_group_name,
        subscription_id=subscription_id,
    )
    return await monitor.get_status(app_name)
