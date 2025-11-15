"""Execution tracker for on-demand execution requests.

This module tracks on-demand execution status in Azure Table Storage.
Provides create, update, and query operations for execution records.
"""

import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableClient

from azure_haymaker.models.execution import (
    ExecutionRecord,
    ExecutionStatusResponse,
    OnDemandExecutionStatus,
)

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """Track on-demand execution requests in Table Storage.

    Stores execution state with PartitionKey=execution_id and RowKey=timestamp.
    Supports create, update, query, and status retrieval operations.

    Example:
        >>> table_client = TableClient.from_connection_string(conn_str, "Executions")
        >>> tracker = ExecutionTracker(table_client)
        >>> execution_id = await tracker.create_execution(
        ...     scenarios=["compute-01"],
        ...     duration_hours=2,
        ... )
    """

    def __init__(self, table_client: TableClient):
        """Initialize execution tracker.

        Args:
            table_client: Azure Table Storage client for execution tracking
        """
        self.table = table_client

    async def create_execution(
        self,
        scenarios: list[str],
        duration_hours: int = 8,
        tags: dict[str, str] | None = None,
    ) -> str:
        """Create new execution record.

        Args:
            scenarios: List of scenario names to execute
            duration_hours: Execution duration in hours
            tags: Optional tags for tracking

        Returns:
            Unique execution ID

        Raises:
            Exception: If table storage operation fails

        Example:
            >>> execution_id = await tracker.create_execution(
            ...     scenarios=["compute-01", "networking-01"],
            ...     duration_hours=2,
            ...     tags={"requester": "admin@example.com"},
            ... )
        """
        execution_id = f"exec-{datetime.now(UTC).strftime('%Y%m%d')}-{str(uuid4())[:8]}"
        now = datetime.now(UTC)

        record = ExecutionRecord(
            execution_id=execution_id,
            timestamp=now,
            status=OnDemandExecutionStatus.QUEUED,
            scenarios=scenarios,
            duration_hours=duration_hours,
            tags=tags or {},
            container_ids=[],
            resources_created=0,
        )

        entity = {
            "PartitionKey": execution_id,
            "RowKey": now.isoformat(),
            "Status": record.status if isinstance(record.status, str) else record.status.value,
            "Scenarios": json.dumps(record.scenarios),
            "DurationHours": record.duration_hours,
            "Tags": json.dumps(record.tags),
            "ContainerIds": json.dumps(record.container_ids),
            "ResourcesCreated": record.resources_created,
            "CreatedAt": now.isoformat(),
        }

        try:
            await self.table.create_entity(entity=entity)
            logger.info(f"Created execution record: {execution_id}")
            return execution_id
        except Exception as e:
            logger.error(f"Failed to create execution record: {e}")
            raise

    async def update_status(
        self,
        execution_id: str,
        status: OnDemandExecutionStatus,
        container_ids: list[str] | None = None,
        resources_created: int | None = None,
        error_message: str | None = None,
        report_url: str | None = None,
    ) -> None:
        """Update execution status.

        Creates a new row with current timestamp to maintain history.

        Args:
            execution_id: Execution ID to update
            status: New execution status
            container_ids: Optional list of container IDs
            resources_created: Optional count of resources created
            error_message: Optional error message
            report_url: Optional report URL

        Raises:
            Exception: If table storage operation fails

        Example:
            >>> await tracker.update_status(
            ...     execution_id="exec-20251115-abc123",
            ...     status=OnDemandExecutionStatus.RUNNING,
            ...     container_ids=["container-01", "container-02"],
            ... )
        """
        now = datetime.now(UTC)

        # Get latest record to preserve fields
        try:
            latest = await self.get_latest_record(execution_id)
            scenarios = latest.get("Scenarios", "[]")
            duration_hours = latest.get("DurationHours", 8)
            tags = latest.get("Tags", "{}")
            created_at = latest.get("CreatedAt", now.isoformat())
        except ResourceNotFoundError:
            logger.warning(f"Execution not found, creating new: {execution_id}")
            scenarios = "[]"
            duration_hours = 8
            tags = "{}"
            created_at = now.isoformat()

        entity = {
            "PartitionKey": execution_id,
            "RowKey": now.isoformat(),
            "Status": status if isinstance(status, str) else status.value,
            "Scenarios": scenarios,
            "DurationHours": duration_hours,
            "Tags": tags,
            "CreatedAt": created_at,
            "UpdatedAt": now.isoformat(),
        }

        # Add optional fields if provided
        if container_ids is not None:
            entity["ContainerIds"] = json.dumps(container_ids)
        elif latest:
            entity["ContainerIds"] = latest.get("ContainerIds", "[]")

        if resources_created is not None:
            entity["ResourcesCreated"] = resources_created
        elif latest:
            entity["ResourcesCreated"] = latest.get("ResourcesCreated", 0)

        if error_message:
            entity["ErrorMessage"] = error_message

        if report_url:
            entity["ReportUrl"] = report_url

        # Add timestamp fields based on status
        if status == OnDemandExecutionStatus.RUNNING:
            entity["StartedAt"] = now.isoformat()
        elif status in [OnDemandExecutionStatus.COMPLETED, OnDemandExecutionStatus.FAILED]:
            entity["CompletedAt"] = now.isoformat()

        try:
            await self.table.create_entity(entity=entity)
            logger.info(f"Updated execution {execution_id} to status: {status.value}")
        except Exception as e:
            logger.error(f"Failed to update execution status: {e}")
            raise

    async def get_latest_record(self, execution_id: str) -> dict:
        """Get latest record for execution.

        Args:
            execution_id: Execution ID to query

        Returns:
            Latest entity as dictionary

        Raises:
            ResourceNotFoundError: If execution not found

        Example:
            >>> record = await tracker.get_latest_record("exec-20251115-abc123")
            >>> print(record["Status"])
        """
        # Query all records for this execution, sorted by RowKey (timestamp) descending
        query = f"PartitionKey eq '{execution_id}'"

        try:
            entities = []
            async for entity in self.table.query_entities(query):
                entities.append(entity)

            if not entities:
                raise ResourceNotFoundError(f"Execution not found: {execution_id}")

            # Sort by RowKey (timestamp) descending and return latest
            entities.sort(key=lambda e: e.get("RowKey", ""), reverse=True)
            return entities[0]

        except Exception as e:
            logger.error(f"Failed to get execution record: {e}")
            raise

    async def get_execution_status(self, execution_id: str) -> ExecutionStatusResponse:
        """Get detailed execution status.

        Args:
            execution_id: Execution ID to query

        Returns:
            ExecutionStatusResponse with full execution details

        Raises:
            ResourceNotFoundError: If execution not found

        Example:
            >>> status = await tracker.get_execution_status("exec-20251115-abc123")
            >>> print(f"Status: {status.status}, Progress: {status.progress}")
        """
        try:
            record = await self.get_latest_record(execution_id)

            # Parse JSON fields
            scenarios = json.loads(record.get("Scenarios", "[]"))
            container_ids = json.loads(record.get("ContainerIds", "[]"))
            # tags = json.loads(record.get("Tags", "{}"))  # Not currently used in response

            # Parse timestamps
            created_at = datetime.fromisoformat(
                record.get("CreatedAt", "").replace("Z", "+00:00")
            )
            started_at = None
            if "StartedAt" in record:
                started_at = datetime.fromisoformat(
                    record.get("StartedAt", "").replace("Z", "+00:00")
                )
            completed_at = None
            if "CompletedAt" in record:
                completed_at = datetime.fromisoformat(
                    record.get("CompletedAt", "").replace("Z", "+00:00")
                )

            # Calculate progress if running
            progress = None
            if record.get("Status") == OnDemandExecutionStatus.RUNNING.value:
                # This is simplified - real progress would query container status
                progress = {
                    "completed": 0,
                    "running": len(container_ids),
                    "failed": 0,
                    "total": len(scenarios),
                }

            return ExecutionStatusResponse(
                execution_id=execution_id,
                status=OnDemandExecutionStatus(record.get("Status", "queued")),
                scenarios=scenarios,
                created_at=created_at,
                started_at=started_at,
                completed_at=completed_at,
                progress=progress,
                resources_created=record.get("ResourcesCreated", 0),
                container_ids=container_ids,
                report_url=record.get("ReportUrl"),
                error=record.get("ErrorMessage"),
            )

        except ResourceNotFoundError:
            logger.error(f"Execution not found: {execution_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to get execution status: {e}")
            raise

    async def list_executions(
        self,
        status: OnDemandExecutionStatus | None = None,
        limit: int = 100,
    ) -> list[ExecutionStatusResponse]:
        """List recent executions.

        Args:
            status: Optional filter by status
            limit: Maximum number of executions to return

        Returns:
            List of ExecutionStatusResponse objects

        Example:
            >>> executions = await tracker.list_executions(
            ...     status=OnDemandExecutionStatus.RUNNING,
            ...     limit=10,
            ... )
        """
        results = []
        seen_execution_ids = set()

        try:
            # Query all entities, filter and deduplicate
            query = f"Status eq '{status.value}'" if status else None

            async for entity in self.table.query_entities(query):
                execution_id = entity.get("PartitionKey")

                # Only include latest record per execution
                if execution_id not in seen_execution_ids:
                    seen_execution_ids.add(execution_id)

                    try:
                        status_response = await self.get_execution_status(execution_id)
                        results.append(status_response)

                        if len(results) >= limit:
                            break
                    except Exception as e:
                        logger.warning(f"Failed to get status for {execution_id}: {e}")
                        continue

            # Sort by created_at descending
            results.sort(key=lambda x: x.created_at, reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"Failed to list executions: {e}")
            raise

    async def delete_execution(self, execution_id: str) -> None:
        """Delete all records for an execution.

        Args:
            execution_id: Execution ID to delete

        Example:
            >>> await tracker.delete_execution("exec-20251115-abc123")
        """
        query = f"PartitionKey eq '{execution_id}'"

        try:
            entities_to_delete = []
            async for entity in self.table.query_entities(query):
                entities_to_delete.append(entity)

            for entity in entities_to_delete:
                await self.table.delete_entity(
                    partition_key=entity["PartitionKey"],
                    row_key=entity["RowKey"],
                )

            logger.info(f"Deleted {len(entities_to_delete)} records for {execution_id}")

        except Exception as e:
            logger.error(f"Failed to delete execution: {e}")
            raise
