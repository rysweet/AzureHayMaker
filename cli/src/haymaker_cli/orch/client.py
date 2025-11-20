"""Azure Container Apps client wrapper for orchestrator CLI commands."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from azure.core.exceptions import (
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.identity import DefaultAzureCredential

from haymaker_cli.orch.models import (
    ApiError,
    ContainerAppInfo,
    HealthCheckResult,
    NetworkError,
    ReplicaInfo,
    RevisionInfo,
    ServerError,
)

# Configure logging
logger = logging.getLogger(__name__)


class ContainerAppsClient:
    """Wrapper for Azure Container Apps API client.

    Provides high-level operations for Container Apps with automatic retry logic,
    error handling, and conversion to our data models.

    Example:
        >>> client = ContainerAppsClient("my-sub-id", "my-rg")
        >>> app_info = client.get_container_app("my-app")  # doctest: +SKIP
        >>> print(app_info.name)  # doctest: +SKIP
        'my-app'
    """

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize Container Apps client.

        Args:
            subscription_id: Azure subscription ID
            resource_group: Azure resource group name
            retry_count: Number of retries for failed requests (default: 3)
            retry_delay: Base delay in seconds for exponential backoff (default: 1.0)

        Example:
            >>> client = ContainerAppsClient("sub-id", "rg-name")
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._credential: DefaultAzureCredential | None = None
        self._client: Any = None  # azure.mgmt.appcontainers.ContainerAppsAPIClient

    def _get_credential(self) -> DefaultAzureCredential:
        """Get or create Azure credential.

        Returns:
            Azure credential instance
        """
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential

    def _get_client(self) -> Any:
        """Get or create Azure Container Apps API client.

        Returns:
            ContainerAppsAPIClient instance
        """
        if self._client is None:
            # Lazy import to avoid loading uninstalled package during testing
            from azure.mgmt.app import ContainerAppsAPIClient

            credential = self._get_credential()
            self._client = ContainerAppsAPIClient(
                credential=credential,
                subscription_id=self.subscription_id,
            )

        return self._client

    async def _retry_operation(self, operation, *args, **kwargs) -> Any:
        """Execute operation with retry logic and error handling.

        Args:
            operation: Function to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Operation result

        Raises:
            NetworkError: If network connectivity fails
            ApiError: If Azure API returns error
            ServerError: If Azure service returns 5xx error
        """
        last_error = None

        for attempt in range(self.retry_count):
            try:
                # Execute operation in thread pool to avoid blocking
                result = await asyncio.to_thread(operation, *args, **kwargs)
                return result

            except ServiceRequestError as e:
                # Network/connectivity errors - retry with backoff
                last_error = e
                if attempt < self.retry_count - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Network error on attempt {attempt + 1}/{self.retry_count}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise NetworkError(
                        f"Network error after {self.retry_count} attempts: {e}",
                        details={"attempts": str(self.retry_count), "error": str(e)},
                    ) from e

            except HttpResponseError as e:
                # HTTP errors from Azure API
                status_code = e.status_code if hasattr(e, "status_code") else None

                # 5xx errors are retriable
                if status_code and 500 <= status_code < 600:
                    last_error = e
                    if attempt < self.retry_count - 1:
                        delay = self.retry_delay * (2**attempt)
                        logger.warning(
                            f"Server error {status_code} on attempt {attempt + 1}/{self.retry_count}, "
                            f"retrying in {delay}s: {e}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise ServerError(
                            f"Azure server error after {self.retry_count} attempts: {e}",
                            details={
                                "status_code": str(status_code),
                                "attempts": str(self.retry_count),
                            },
                        ) from e

                # 4xx errors are not retriable (client errors)
                error_msg = str(e)
                if hasattr(e, "message"):
                    error_msg = e.message

                raise ApiError(
                    f"Azure API error: {error_msg}",
                    details={"status_code": str(status_code) if status_code else "unknown"},
                ) from e

            except ResourceNotFoundError as e:
                # Resource not found - not retriable
                raise ApiError(
                    f"Resource not found: {e}",
                    details={"error_type": "ResourceNotFoundError"},
                ) from e

            except Exception as e:
                # Unexpected errors
                raise ApiError(
                    f"Unexpected error: {e}",
                    details={"error_type": type(e).__name__},
                ) from e

        # Should not reach here, but just in case
        raise ApiError(
            f"Operation failed after {self.retry_count} attempts",
            details={"last_error": str(last_error) if last_error else "unknown"},
        )

    def _convert_to_container_app_info(self, app: Any) -> ContainerAppInfo:
        """Convert Azure SDK ContainerApp to our model.

        Args:
            app: Azure SDK ContainerApp object

        Returns:
            ContainerAppInfo model
        """
        # Extract configuration with safe defaults
        configuration = getattr(app, "configuration", None) or {}
        ingress = getattr(configuration, "ingress", None)

        # Extract scale configuration
        scale = {}
        template = getattr(configuration, "active_revisions_mode", None)
        if template:
            template_obj = getattr(configuration, "template", None)
            if template_obj:
                scale_obj = getattr(template_obj, "scale", None)
                if scale_obj:
                    scale = {
                        "min_replicas": getattr(scale_obj, "min_replicas", 0),
                        "max_replicas": getattr(scale_obj, "max_replicas", 10),
                    }

        # Extract latest revision info
        latest_revision_name = getattr(app, "latest_revision_name", None)
        latest_revision_fqdn = getattr(app, "latest_revision_fqdn", None)

        # Get provisioning state
        provisioning_state = getattr(app, "provisioning_state", "Unknown")

        # Extract running status
        running_status = None
        if hasattr(app, "running_status"):
            running_status = getattr(app, "running_status", None)

        # Extract location and tags
        location = getattr(app, "location", "unknown")
        tags = getattr(app, "tags", None) or {}

        # Parse creation timestamp
        created_at = None
        system_data = getattr(app, "system_data", None)
        if system_data and hasattr(system_data, "created_at"):
            created_at = system_data.created_at

        return ContainerAppInfo(
            name=app.name,
            resource_group=self.resource_group,
            location=location,
            provisioning_state=provisioning_state,
            running_status=running_status,
            latest_revision_name=latest_revision_name,
            latest_revision_fqdn=latest_revision_fqdn,
            active_revisions_count=len(
                getattr(app, "custom_domain_verification_id", [])
            ) if hasattr(app, "custom_domain_verification_id") else 0,
            min_replicas=scale.get("min_replicas", 0),
            max_replicas=scale.get("max_replicas", 10),
            ingress_enabled=ingress is not None,
            external_ingress=getattr(ingress, "external", False) if ingress else False,
            target_port=getattr(ingress, "target_port", None) if ingress else None,
            created_at=created_at,
            tags=tags,
        )

    def _convert_to_replica_info(self, replica: Any) -> ReplicaInfo:
        """Convert Azure SDK Replica to our model.

        Args:
            replica: Azure SDK Replica object

        Returns:
            ReplicaInfo model
        """
        name = getattr(replica, "name", "unknown")
        created_at = getattr(replica, "created_time", None)

        # Extract running state
        running_state = None
        running_state_details = None
        if hasattr(replica, "running_state"):
            running_state = getattr(replica, "running_state", None)
        if hasattr(replica, "running_state_details"):
            running_state_details = getattr(replica, "running_state_details", None)

        return ReplicaInfo(
            name=name,
            created_at=created_at,
            running_state=running_state,
            running_state_details=running_state_details,
        )

    def _convert_to_revision_info(self, revision: Any, traffic_weight: int = 0) -> RevisionInfo:
        """Convert Azure SDK Revision to our model.

        Args:
            revision: Azure SDK Revision object
            traffic_weight: Traffic weight percentage (0-100)

        Returns:
            RevisionInfo model
        """
        name = getattr(revision, "name", "unknown")
        active = getattr(revision, "active", False)
        created_at = getattr(revision, "created_time", None)
        provisioning_state = getattr(revision, "provisioning_state", None)
        health_state = getattr(revision, "health_state", None)

        # Extract replica count
        replicas_count = 0
        if hasattr(revision, "replicas"):
            replicas_count = getattr(revision, "replicas", 0)

        return RevisionInfo(
            name=name,
            active=active,
            created_at=created_at,
            traffic_weight=traffic_weight,
            provisioning_state=provisioning_state,
            health_state=health_state,
            replicas=[],  # Will be populated separately if needed
            replicas_count=replicas_count,
        )

    async def get_container_app(self, app_name: str) -> ContainerAppInfo:
        """Get Container App information.

        Args:
            app_name: Container app name

        Returns:
            Container app information

        Raises:
            NetworkError: If network connectivity fails
            ApiError: If Azure API returns error
            ServerError: If Azure service returns 5xx error

        Example:
            >>> client = ContainerAppsClient("sub-id", "rg")
            >>> app = await client.get_container_app("my-app")  # doctest: +SKIP
            >>> print(app.name)  # doctest: +SKIP
            'my-app'
        """
        logger.info(f"Getting container app: {app_name}")

        client = self._get_client()
        app = await self._retry_operation(
            client.container_apps.get,
            resource_group_name=self.resource_group,
            name=app_name,
        )

        return self._convert_to_container_app_info(app)

    async def list_container_apps(self) -> list[ContainerAppInfo]:
        """List all Container Apps in the resource group.

        Returns:
            List of container app information

        Raises:
            NetworkError: If network connectivity fails
            ApiError: If Azure API returns error
            ServerError: If Azure service returns 5xx error

        Example:
            >>> client = ContainerAppsClient("sub-id", "rg")
            >>> apps = await client.list_container_apps()  # doctest: +SKIP
            >>> print(len(apps))  # doctest: +SKIP
            3
        """
        logger.info(f"Listing container apps in resource group: {self.resource_group}")

        client = self._get_client()
        apps_iterator = await self._retry_operation(
            client.container_apps.list_by_resource_group,
            resource_group_name=self.resource_group,
        )

        # Convert iterator to list and transform
        apps = []
        for app in apps_iterator:
            apps.append(self._convert_to_container_app_info(app))

        return apps

    async def list_revisions(self, app_name: str) -> list[RevisionInfo]:
        """List all revisions for a Container App.

        Args:
            app_name: Container app name

        Returns:
            List of revision information

        Raises:
            NetworkError: If network connectivity fails
            ApiError: If Azure API returns error
            ServerError: If Azure service returns 5xx error

        Example:
            >>> client = ContainerAppsClient("sub-id", "rg")
            >>> revisions = await client.list_revisions("my-app")  # doctest: +SKIP
            >>> print(len(revisions))  # doctest: +SKIP
            2
        """
        logger.info(f"Listing revisions for container app: {app_name}")

        client = self._get_client()
        revisions_iterator = await self._retry_operation(
            client.container_apps_revisions.list_revisions,
            resource_group_name=self.resource_group,
            container_app_name=app_name,
        )

        # Convert iterator to list and transform
        revisions = []
        for revision in revisions_iterator:
            # Traffic weight will be determined from the app's traffic configuration
            revisions.append(self._convert_to_revision_info(revision, traffic_weight=0))

        return revisions

    async def list_replicas(self, app_name: str, revision_name: str) -> list[ReplicaInfo]:
        """List all replicas for a specific revision.

        Args:
            app_name: Container app name
            revision_name: Revision name

        Returns:
            List of replica information

        Raises:
            NetworkError: If network connectivity fails
            ApiError: If Azure API returns error
            ServerError: If Azure service returns 5xx error

        Example:
            >>> client = ContainerAppsClient("sub-id", "rg")
            >>> replicas = await client.list_replicas("my-app", "my-app--rev1")  # doctest: +SKIP
            >>> print(len(replicas))  # doctest: +SKIP
            3
        """
        logger.info(f"Listing replicas for revision: {revision_name}")

        client = self._get_client()
        replicas_iterator = await self._retry_operation(
            client.container_apps_revision_replicas.list_replicas,
            resource_group_name=self.resource_group,
            container_app_name=app_name,
            revision_name=revision_name,
        )

        # Convert iterator to list and transform
        replicas = []
        for replica in replicas_iterator:
            replicas.append(self._convert_to_replica_info(replica))

        return replicas

    async def get_health(self, app_name: str) -> HealthCheckResult:
        """Get comprehensive health check for a Container App.

        Aggregates information from app, revisions, and replicas to determine
        overall health status.

        Args:
            app_name: Container app name

        Returns:
            Health check result

        Raises:
            NetworkError: If network connectivity fails
            ApiError: If Azure API returns error
            ServerError: If Azure service returns 5xx error

        Example:
            >>> client = ContainerAppsClient("sub-id", "rg")
            >>> health = await client.get_health("my-app")  # doctest: +SKIP
            >>> print(health.status)  # doctest: +SKIP
            'healthy'
        """
        logger.info(f"Performing health check for container app: {app_name}")

        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, str] = {}

        # Get app info
        try:
            app = await self.get_container_app(app_name)
        except Exception as e:
            return HealthCheckResult(
                app_name=app_name,
                status="unknown",
                provisioning_state="Unknown",
                errors=[f"Failed to get app info: {e}"],
                checked_at=datetime.utcnow(),
            )

        # Get revisions
        try:
            revisions = await self.list_revisions(app_name)
            active_revisions = [r for r in revisions if r.active]
        except Exception as e:
            errors.append(f"Failed to get revisions: {e}")
            active_revisions = []

        # Count replicas across active revisions
        total_replicas = 0
        healthy_replicas = 0

        for revision in active_revisions:
            try:
                replicas = await self.list_replicas(app_name, revision.name)
                total_replicas += len(replicas)
                healthy_replicas += sum(
                    1 for r in replicas if r.running_state == "Running"
                )
            except Exception as e:
                warnings.append(f"Failed to get replicas for {revision.name}: {e}")

        # Determine overall health status
        status = "unknown"

        if app.provisioning_state == "Succeeded":
            if app.running_status == "Running":
                if total_replicas == 0:
                    status = "unhealthy"
                    warnings.append("No replicas found")
                elif healthy_replicas == total_replicas:
                    status = "healthy"
                elif healthy_replicas > 0:
                    status = "degraded"
                    warnings.append(f"Only {healthy_replicas}/{total_replicas} replicas healthy")
                else:
                    status = "unhealthy"
                    errors.append("No healthy replicas")
            else:
                status = "unhealthy"
                errors.append(f"App not running: {app.running_status}")
        elif app.provisioning_state == "Failed":
            status = "unhealthy"
            errors.append("Provisioning failed")
        else:
            status = "degraded"
            warnings.append(f"Provisioning state: {app.provisioning_state}")

        # Add details
        details["provisioning_state"] = app.provisioning_state
        if app.running_status:
            details["running_status"] = app.running_status
        details["active_revisions"] = str(len(active_revisions))
        details["total_replicas"] = str(total_replicas)
        details["healthy_replicas"] = str(healthy_replicas)

        return HealthCheckResult(
            app_name=app_name,
            status=status,
            provisioning_state=app.provisioning_state,
            running_status=app.running_status,
            total_replicas=total_replicas,
            healthy_replicas=healthy_replicas,
            active_revisions=len(active_revisions),
            latest_revision=app.latest_revision_name,
            fqdn=app.latest_revision_fqdn,
            checked_at=datetime.utcnow(),
            errors=errors,
            warnings=warnings,
            details=details,
        )

    def close(self) -> None:
        """Close client and cleanup resources.

        Example:
            >>> client = ContainerAppsClient("sub-id", "rg")
            >>> client.close()  # doctest: +SKIP
        """
        # DefaultAzureCredential doesn't need explicit cleanup
        self._credential = None
        self._client = None
