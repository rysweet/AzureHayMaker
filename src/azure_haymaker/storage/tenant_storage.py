"""Tenant-isolated storage manager for cross-tenant orchestration.

Provides tenant-scoped blob operations with path isolation:
- Storage path format: {tenant_id}/{execution_id}/{artifact_name}
- Backward compatible: Single-tenant mode uses {execution_id}/{artifact_name}

This enables complete tenant isolation in multi-tenant deployments,
ensuring each tenant's execution artifacts are stored separately.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure.storage.blob import BlobServiceClient, ContainerClient

logger = logging.getLogger(__name__)


def get_tenant_blob_path(
    execution_id: str,
    artifact_name: str,
    tenant_id: str | None = None,
) -> str:
    """Build tenant-prefixed blob path.

    Creates storage paths that isolate tenant data:
    - With tenant_id: {tenant_id}/{execution_id}/{artifact_name}
    - Without tenant_id: {execution_id}/{artifact_name} (backward compatible)

    Args:
        execution_id: Unique execution run identifier
        artifact_name: Name of the artifact (e.g., "results.json", "logs.txt")
        tenant_id: Optional Azure tenant ID for cross-tenant isolation

    Returns:
        Blob path string suitable for Azure Blob Storage

    Example:
        >>> get_tenant_blob_path("exec-123", "report.json", "tenant-abc")
        'tenant-abc/exec-123/report.json'
        >>> get_tenant_blob_path("exec-123", "report.json")
        'exec-123/report.json'
    """
    if tenant_id:
        return f"{tenant_id}/{execution_id}/{artifact_name}"
    return f"{execution_id}/{artifact_name}"


@dataclass
class TenantStorageConfig:
    """Configuration for tenant storage operations.

    Attributes:
        container_logs: Container name for execution logs
        container_state: Container name for execution state
        container_reports: Container name for execution reports
        container_scenarios: Container name for scenario documents
    """

    container_logs: str = "execution-logs"
    container_state: str = "execution-state"
    container_reports: str = "execution-reports"
    container_scenarios: str = "scenarios"


class TenantStorageManager:
    """Manages tenant-scoped blob operations.

    Provides methods for uploading and downloading data with tenant isolation.
    All operations use the path format: {tenant_id}/{execution_id}/{artifact_name}

    Example:
        >>> from azure.storage.blob import BlobServiceClient
        >>> from azure.identity import DefaultAzureCredential
        >>> blob_client = BlobServiceClient(account_url, DefaultAzureCredential())
        >>> manager = TenantStorageManager(blob_client)
        >>> await manager.upload_tenant_data(
        ...     tenant_id="tenant-123",
        ...     execution_id="exec-456",
        ...     artifact_name="results.json",
        ...     data=b'{"status": "success"}',
        ...     container_name="execution-reports",
        ... )
    """

    def __init__(
        self,
        blob_service_client: BlobServiceClient,
        config: TenantStorageConfig | None = None,
    ):
        """Initialize tenant storage manager.

        Args:
            blob_service_client: Azure Blob Service client with credentials
            config: Optional storage configuration (uses defaults if not provided)
        """
        self._client = blob_service_client
        self._config = config or TenantStorageConfig()

    def get_tenant_container_client(
        self,
        container_name: str,
    ) -> ContainerClient:
        """Get container client for blob operations.

        Args:
            container_name: Name of the storage container

        Returns:
            ContainerClient for the specified container

        Example:
            >>> container = manager.get_tenant_container_client("execution-reports")
            >>> blob_client = container.get_blob_client("tenant-123/exec-456/report.json")
        """
        return self._client.get_container_client(container_name)

    async def upload_tenant_data(
        self,
        execution_id: str,
        artifact_name: str,
        data: bytes | str,
        container_name: str | None = None,
        tenant_id: str | None = None,
        content_type: str | None = None,
        overwrite: bool = True,
    ) -> str:
        """Upload data to tenant-isolated storage path.

        Args:
            execution_id: Unique execution run identifier
            artifact_name: Name of the artifact to store
            data: Data to upload (bytes or string)
            container_name: Storage container name (defaults to execution-reports)
            tenant_id: Optional tenant ID for cross-tenant isolation
            content_type: Optional MIME content type
            overwrite: Whether to overwrite existing blob (default True)

        Returns:
            URL of the uploaded blob

        Example:
            >>> url = await manager.upload_tenant_data(
            ...     tenant_id="tenant-abc",
            ...     execution_id="exec-123",
            ...     artifact_name="report.json",
            ...     data='{"status": "success"}',
            ...     content_type="application/json",
            ... )
            >>> print(url)
            'https://storage.blob.core.windows.net/.../tenant-abc/exec-123/report.json'
        """
        container = container_name or self._config.container_reports
        blob_path = get_tenant_blob_path(execution_id, artifact_name, tenant_id)

        container_client = self.get_tenant_container_client(container)
        blob_client = container_client.get_blob_client(blob_path)

        # Convert string to bytes if needed
        upload_data = data.encode("utf-8") if isinstance(data, str) else data

        # Prepare upload kwargs
        upload_kwargs: dict = {"overwrite": overwrite}
        if content_type:
            upload_kwargs["content_type"] = content_type

        try:
            await blob_client.upload_blob(upload_data, **upload_kwargs)  # type: ignore[misc]
            logger.info(f"Uploaded tenant data to {blob_path} in {container}")
            return str(blob_client.url)
        except Exception as e:
            logger.error(f"Failed to upload tenant data to {blob_path}: {e}")
            raise

    async def download_tenant_data(
        self,
        execution_id: str,
        artifact_name: str,
        container_name: str | None = None,
        tenant_id: str | None = None,
    ) -> bytes:
        """Download data from tenant-isolated storage path.

        Args:
            execution_id: Unique execution run identifier
            artifact_name: Name of the artifact to download
            container_name: Storage container name (defaults to execution-reports)
            tenant_id: Optional tenant ID for cross-tenant isolation

        Returns:
            Downloaded blob data as bytes

        Raises:
            azure.core.exceptions.ResourceNotFoundError: If blob does not exist

        Example:
            >>> data = await manager.download_tenant_data(
            ...     tenant_id="tenant-abc",
            ...     execution_id="exec-123",
            ...     artifact_name="report.json",
            ... )
            >>> report = json.loads(data.decode("utf-8"))
        """
        container = container_name or self._config.container_reports
        blob_path = get_tenant_blob_path(execution_id, artifact_name, tenant_id)

        container_client = self.get_tenant_container_client(container)
        blob_client = container_client.get_blob_client(blob_path)

        try:
            download = await blob_client.download_blob()  # type: ignore[misc]
            data = await download.readall()  # type: ignore[misc]
            logger.debug(f"Downloaded tenant data from {blob_path} in {container}")
            return data  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to download tenant data from {blob_path}: {e}")
            raise

    async def delete_tenant_data(
        self,
        execution_id: str,
        artifact_name: str,
        container_name: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Delete data from tenant-isolated storage path.

        Args:
            execution_id: Unique execution run identifier
            artifact_name: Name of the artifact to delete
            container_name: Storage container name (defaults to execution-reports)
            tenant_id: Optional tenant ID for cross-tenant isolation

        Example:
            >>> await manager.delete_tenant_data(
            ...     tenant_id="tenant-abc",
            ...     execution_id="exec-123",
            ...     artifact_name="report.json",
            ... )
        """
        container = container_name or self._config.container_reports
        blob_path = get_tenant_blob_path(execution_id, artifact_name, tenant_id)

        container_client = self.get_tenant_container_client(container)
        blob_client = container_client.get_blob_client(blob_path)

        try:
            await blob_client.delete_blob()  # type: ignore[misc]
            logger.info(f"Deleted tenant data at {blob_path} in {container}")
        except Exception as e:
            logger.error(f"Failed to delete tenant data at {blob_path}: {e}")
            raise

    async def list_tenant_artifacts(
        self,
        execution_id: str,
        container_name: str | None = None,
        tenant_id: str | None = None,
    ) -> list[str]:
        """List all artifacts for a tenant execution.

        Args:
            execution_id: Unique execution run identifier
            container_name: Storage container name (defaults to execution-reports)
            tenant_id: Optional tenant ID for cross-tenant isolation

        Returns:
            List of artifact names (without the path prefix)

        Example:
            >>> artifacts = await manager.list_tenant_artifacts(
            ...     tenant_id="tenant-abc",
            ...     execution_id="exec-123",
            ... )
            >>> print(artifacts)
            ['report.json', 'logs.txt', 'metrics.json']
        """
        container = container_name or self._config.container_reports
        prefix = get_tenant_blob_path(execution_id, "", tenant_id).rstrip("/") + "/"

        container_client = self.get_tenant_container_client(container)

        artifacts = []
        try:
            async for blob in container_client.list_blobs(name_starts_with=prefix):  # type: ignore[misc]
                # Extract artifact name from full path
                artifact_name = blob.name[len(prefix) :]
                if artifact_name:  # Skip empty names (directory markers)
                    artifacts.append(artifact_name)
            logger.debug(f"Listed {len(artifacts)} artifacts for {prefix} in {container}")
            return artifacts
        except Exception as e:
            logger.error(f"Failed to list tenant artifacts for {prefix}: {e}")
            raise

    async def cleanup_tenant_execution(
        self,
        execution_id: str,
        container_name: str | None = None,
        tenant_id: str | None = None,
    ) -> int:
        """Delete all artifacts for a tenant execution.

        Args:
            execution_id: Unique execution run identifier
            container_name: Storage container name (defaults to execution-reports)
            tenant_id: Optional tenant ID for cross-tenant isolation

        Returns:
            Number of artifacts deleted

        Example:
            >>> deleted = await manager.cleanup_tenant_execution(
            ...     tenant_id="tenant-abc",
            ...     execution_id="exec-123",
            ... )
            >>> print(f"Deleted {deleted} artifacts")
        """
        artifacts = await self.list_tenant_artifacts(
            execution_id=execution_id,
            container_name=container_name,
            tenant_id=tenant_id,
        )

        deleted_count = 0
        for artifact in artifacts:
            try:
                await self.delete_tenant_data(
                    execution_id=execution_id,
                    artifact_name=artifact,
                    container_name=container_name,
                    tenant_id=tenant_id,
                )
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete artifact {artifact}: {e}")
                continue

        logger.info(
            f"Cleaned up {deleted_count}/{len(artifacts)} artifacts for "
            f"execution {execution_id}" + (f" in tenant {tenant_id}" if tenant_id else "")
        )
        return deleted_count
