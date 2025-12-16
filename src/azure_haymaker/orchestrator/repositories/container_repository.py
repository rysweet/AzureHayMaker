"""Repository for Azure Container Apps operations.

This module implements the repository pattern for Container Apps,
abstracting Azure SDK calls behind a clean interface. It handles:
- Container App lifecycle operations (get, create, delete)
- Status checking and existence verification
- Consistent error handling and logging
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

from .base_repository import IRepository, RepositoryError

logger = logging.getLogger(__name__)


@dataclass
class ContainerAppResource:
    """Data class representing a Container App resource.

    Attributes:
        name: Container App name
        resource_id: Full Azure resource ID
        resource_group: Resource group containing the app
        subscription_id: Azure subscription ID
        status: Current provisioning state
        location: Azure region
        properties: Additional properties from Azure
    """

    name: str
    resource_id: str
    resource_group: str
    subscription_id: str
    status: str | None = None
    location: str | None = None
    properties: dict[str, Any] | None = None


class ContainerAppRepository(IRepository[ContainerAppResource]):
    """Repository for Container App operations.

    Implements IRepository interface for Azure Container Apps, providing
    a clean abstraction over the Azure Management SDK. All Azure SDK
    calls are encapsulated here, keeping business logic separate.

    Example:
        >>> repo = ContainerAppRepository(
        ...     subscription_id="sub-123",
        ...     resource_group="rg-haymaker"
        ... )
        >>> app = await repo.get("my-container-app")
        >>> if app:
        ...     print(f"Status: {app.status}")
    """

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        credential: DefaultAzureCredential | None = None,
    ):
        """Initialize ContainerAppRepository.

        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group for container operations
            credential: Azure credential (defaults to DefaultAzureCredential)

        Raises:
            ValueError: If subscription_id or resource_group is empty
        """
        if not subscription_id:
            raise ValueError("subscription_id is required")
        if not resource_group:
            raise ValueError("resource_group is required")

        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self._credential = credential

    def _get_credential(self) -> DefaultAzureCredential:
        """Get or create Azure credential.

        Returns:
            Azure credential for authentication
        """
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential

    def _get_client(self):
        """Get Container Apps API client.

        Lazily imports the SDK to avoid load-time failures
        when the package is not installed.

        Returns:
            ContainerAppsAPIClient instance
        """
        from azure.mgmt.appcontainers import ContainerAppsAPIClient

        return ContainerAppsAPIClient(
            credential=self._get_credential(),
            subscription_id=self.subscription_id,
        )

    async def get(self, resource_id: str) -> ContainerAppResource | None:
        """Retrieve a Container App by name.

        Args:
            resource_id: Container App name

        Returns:
            ContainerAppResource if found, None if not found

        Raises:
            RepositoryError: If the operation fails (other than not found)
        """
        try:
            client = self._get_client()
            app = await asyncio.to_thread(
                client.container_apps.get,
                resource_group_name=self.resource_group,
                container_app_name=resource_id,
            )

            return ContainerAppResource(
                name=app.name,
                resource_id=app.id,
                resource_group=self.resource_group,
                subscription_id=self.subscription_id,
                status=app.provisioning_state,
                location=app.location,
                properties={
                    "configuration": app.configuration,
                    "template": app.template,
                }
                if app.configuration or app.template
                else None,
            )

        except ResourceNotFoundError:
            logger.debug(f"Container app {resource_id} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to get container app {resource_id}: {e}")
            raise RepositoryError(
                f"Failed to retrieve container app: {e}",
                operation="get",
                resource_id=resource_id,
            ) from e

    async def create(self, resource: ContainerAppResource) -> ContainerAppResource:
        """Create a new Container App.

        Note: For full deployment with configuration, use ContainerDeployer.
        This method provides basic creation for simple use cases.

        Args:
            resource: ContainerAppResource with required fields

        Returns:
            Created ContainerAppResource with updated fields

        Raises:
            RepositoryError: If creation fails
            ValueError: If resource configuration is invalid
        """
        if not resource.name:
            raise ValueError("Container app name is required")

        try:
            client = self._get_client()

            # Build minimal container app definition
            container_app_envelope = {
                "location": resource.location or "eastus",
                "properties": resource.properties or {},
            }

            poller = await asyncio.to_thread(
                client.container_apps.begin_create_or_update,
                resource_group_name=self.resource_group,
                container_app_name=resource.name,
                container_app_envelope=container_app_envelope,
            )

            result = await asyncio.to_thread(poller.result)

            logger.info(f"Container app {resource.name} created successfully")

            return ContainerAppResource(
                name=result.name,
                resource_id=result.id,
                resource_group=self.resource_group,
                subscription_id=self.subscription_id,
                status=result.provisioning_state,
                location=result.location,
            )

        except Exception as e:
            logger.error(f"Failed to create container app {resource.name}: {e}")
            raise RepositoryError(
                f"Failed to create container app: {e}",
                operation="create",
                resource_id=resource.name,
            ) from e

    async def delete(self, resource_id: str) -> bool:
        """Delete a Container App by name.

        Args:
            resource_id: Container App name to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            RepositoryError: If deletion fails (other than not found)
        """
        try:
            client = self._get_client()

            poller = await asyncio.to_thread(
                client.container_apps.begin_delete,
                resource_group_name=self.resource_group,
                container_app_name=resource_id,
            )

            await asyncio.to_thread(poller.result)

            logger.info(f"Container app {resource_id} deleted successfully")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Container app {resource_id} not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Failed to delete container app {resource_id}: {e}")
            raise RepositoryError(
                f"Failed to delete container app: {e}",
                operation="delete",
                resource_id=resource_id,
            ) from e

    async def exists(self, resource_id: str) -> bool:
        """Check if a Container App exists.

        Args:
            resource_id: Container App name

        Returns:
            True if the app exists, False otherwise

        Raises:
            RepositoryError: If the check fails
        """
        app = await self.get(resource_id)
        return app is not None

    async def get_status(self, resource_id: str) -> str | None:
        """Get the provisioning status of a Container App.

        Convenience method for status checking without retrieving
        the full resource details.

        Args:
            resource_id: Container App name

        Returns:
            Status string (Running, Provisioning, Failed, etc.) or None if not found

        Raises:
            RepositoryError: If status check fails
        """
        app = await self.get(resource_id)
        return app.status if app else None

    async def list_by_resource_group(self) -> list[ContainerAppResource]:
        """List all Container Apps in the resource group.

        Returns:
            List of ContainerAppResource objects

        Raises:
            RepositoryError: If listing fails
        """
        try:
            client = self._get_client()

            apps = await asyncio.to_thread(
                lambda: list(
                    client.container_apps.list_by_resource_group(
                        resource_group_name=self.resource_group
                    )
                )
            )

            return [
                ContainerAppResource(
                    name=app.name,
                    resource_id=app.id,
                    resource_group=self.resource_group,
                    subscription_id=self.subscription_id,
                    status=app.provisioning_state,
                    location=app.location,
                )
                for app in apps
            ]

        except Exception as e:
            logger.error(f"Failed to list container apps: {e}")
            raise RepositoryError(
                f"Failed to list container apps: {e}",
                operation="list",
            ) from e


__all__ = ["ContainerAppRepository", "ContainerAppResource"]
