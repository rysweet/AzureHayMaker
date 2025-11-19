"""
Data access layer for monitoring API.

This repository handles all Azure Blob Storage operations for the monitoring API,
providing a clean abstraction over the Azure Storage SDK. It reads JSON blobs and
returns dictionaries without applying any business logic or validation.

Responsibilities:
- Read JSON blobs from Azure Storage
- Handle Azure SDK exceptions
- Parse JSON into dictionaries
- No business logic or validation
"""

import json
import logging
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


class MonitoringRepository:
    """
    Repository for accessing monitoring data from Azure Blob Storage.

    This class encapsulates all blob storage access for the monitoring API,
    providing methods to read status files, run reports, and resource lists.
    """

    def __init__(self, blob_client: BlobServiceClient):
        """
        Initialize repository with blob storage client.

        Args:
            blob_client: Azure Blob Service client for storage operations
        """
        self.blob_client = blob_client

    async def get_status(self) -> dict[str, Any] | None:
        """
        Read current orchestrator status from storage.

        Returns:
            Status data dictionary from storage, or None if not found.
            The dictionary contains fields like status, health, current_run_id, etc.

        Raises:
            Exception: For storage errors other than ResourceNotFoundError
        """
        try:
            return await self._read_blob_json(
                container="execution-state", blob_name="current_status.json"
            )
        except ResourceNotFoundError:
            # Return None when status file doesn't exist yet
            # Caller will interpret this as idle state
            return None

    async def get_run_report(self, run_id: str) -> dict[str, Any]:
        """
        Read run report from storage.

        Args:
            run_id: Run UUID to retrieve

        Returns:
            Run report data dictionary containing run details, scenarios,
            resource counts, and cleanup verification results

        Raises:
            ResourceNotFoundError: If run doesn't exist in storage
            Exception: For other storage or parsing errors
        """
        return await self._read_blob_json(
            container="execution-reports", blob_name=f"{run_id}/report.json"
        )

    async def get_run_resources(self, run_id: str) -> dict[str, Any]:
        """
        Read resources list from storage.

        Args:
            run_id: Run UUID to retrieve resources for

        Returns:
            Resources data dictionary containing a list of all resources
            created during the run with their lifecycle tracking information

        Raises:
            ResourceNotFoundError: If run doesn't exist in storage
            Exception: For other storage or parsing errors
        """
        return await self._read_blob_json(
            container="execution-reports", blob_name=f"{run_id}/resources.json"
        )

    async def _read_blob_json(self, container: str, blob_name: str) -> dict[str, Any]:
        """
        Read and parse JSON from blob storage.

        This method handles both sync and async Azure SDK APIs and provides
        consistent JSON parsing with proper error handling.

        Args:
            container: Azure storage container name
            blob_name: Blob name (path) within the container

        Returns:
            Parsed JSON as dictionary

        Raises:
            ResourceNotFoundError: If blob doesn't exist
            Exception: For other storage errors or corrupted JSON
        """
        try:
            blob = self.blob_client.get_blob_client(container=container, blob=blob_name)
            download_stream = blob.download_blob()

            # Handle both sync and async download APIs
            # The Azure SDK may return either sync or async download streams
            if hasattr(download_stream, "readall") and callable(download_stream.readall):
                data_result = download_stream.readall()

                # Check if it's a coroutine (async API)
                import inspect

                if inspect.iscoroutine(data_result):
                    data = await data_result  # type: ignore[misc]
                else:
                    data = data_result
            else:
                # Fallback for sync API
                data = download_stream.readall()

            # Parse JSON from string or bytes
            if isinstance(data, str):
                return json.loads(data)
            elif isinstance(data, bytes):
                return json.loads(data.decode("utf-8"))
            else:
                raise TypeError(f"Unexpected data type from blob storage: {type(data)}")

        except ResourceNotFoundError:
            # Re-raise ResourceNotFoundError so caller can handle it
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from blob {blob_name}: {e}")
            raise Exception(f"Corrupted data in storage: {blob_name}") from e
        except Exception as e:
            logger.error(f"Failed to read blob {blob_name}: {e}")
            raise


__all__ = ["MonitoringRepository"]
