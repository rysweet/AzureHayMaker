"""Container App lifecycle management for Azure HayMaker.

This module manages Container App deletion and cleanup operations
on Azure using the repository pattern for clean abstraction.
"""

import logging

from azure_haymaker.exceptions import ContainerError

from .repositories.base_repository import RepositoryError
from .repositories.container_repository import ContainerAppRepository

# Configure logging
logger = logging.getLogger(__name__)

# Backward compatibility alias - use ContainerError from central exceptions
ContainerAppError = ContainerError


class ContainerLifecycle:
    """Manages Container App lifecycle and cleanup operations.

    This class provides deletion and cleanup capabilities for deployed
    Container Apps on Azure, using the repository pattern for data access.
    """

    def __init__(
        self,
        resource_group_name: str,
        subscription_id: str,
        repository: ContainerAppRepository | None = None,
    ):
        """Initialize ContainerLifecycle with Azure resource identifiers.

        Args:
            resource_group_name: Azure resource group name
            subscription_id: Azure subscription ID
            repository: Optional ContainerAppRepository for dependency injection.
                       If not provided, a default repository is created.

        Raises:
            ValueError: If parameters are invalid
        """
        if not resource_group_name or not subscription_id:
            raise ValueError("resource_group_name and subscription_id are required")

        self.resource_group_name = resource_group_name
        self.subscription_id = subscription_id

        # Use injected repository or create default
        self._repository = repository or ContainerAppRepository(
            subscription_id=subscription_id,
            resource_group=resource_group_name,
        )

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
            logger.info(f"Deleting container app {app_name}")

            result = await self._repository.delete(app_name)

            if result:
                logger.info(f"Container app {app_name} deleted successfully")
            else:
                logger.warning(f"Container app {app_name} not found for deletion")

            return result

        except RepositoryError as e:
            logger.error(f"Failed to delete container app {app_name}: {e}")
            raise ContainerAppError(f"Failed to delete container app: {e}") from e

    async def exists(self, app_name: str) -> bool:
        """Check if a container app exists.

        Args:
            app_name: Name of the container app to check

        Returns:
            True if the app exists, False otherwise

        Raises:
            ValueError: If app_name is empty
            ContainerAppError: If the check fails
        """
        if not app_name:
            raise ValueError("App name is required")

        try:
            return await self._repository.exists(app_name)
        except RepositoryError as e:
            logger.error(f"Failed to check container app {app_name}: {e}")
            raise ContainerAppError(f"Failed to check container app: {e}") from e

    async def get_status(self, app_name: str) -> str | None:
        """Get the status of a container app.

        Args:
            app_name: Name of the container app

        Returns:
            Status string or None if not found

        Raises:
            ValueError: If app_name is empty
            ContainerAppError: If status check fails
        """
        if not app_name:
            raise ValueError("App name is required")

        try:
            return await self._repository.get_status(app_name)
        except RepositoryError as e:
            logger.error(f"Failed to get status for {app_name}: {e}")
            raise ContainerAppError(f"Failed to get container app status: {e}") from e


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
