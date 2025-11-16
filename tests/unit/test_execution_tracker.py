"""Unit tests for execution tracker module."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.models.execution import OnDemandExecutionStatus
from azure_haymaker.orchestrator.execution_tracker import ExecutionTracker


def async_iterator(items):
    """Helper to create an async iterator from a list."""

    class AsyncIterator:
        def __init__(self, items):
            self.items = items
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index >= len(self.items):
                raise StopAsyncIteration
            item = self.items[self.index]
            self.index += 1
            return item

    return AsyncIterator(items)


@pytest.fixture
def mock_table_client():
    """Create mock Table Storage client."""
    return AsyncMock()


@pytest.fixture
def execution_tracker(mock_table_client):
    """Create execution tracker instance."""
    return ExecutionTracker(mock_table_client)


@pytest.mark.asyncio
async def test_create_execution(execution_tracker, mock_table_client):
    """Test creating new execution record."""
    mock_table_client.create_entity = AsyncMock()

    execution_id = await execution_tracker.create_execution(
        scenarios=["compute-01", "networking-01"],
        duration_hours=2,
        tags={"requester": "admin@example.com"},
    )

    assert execution_id.startswith("exec-")
    assert len(execution_id) > 20

    # Verify entity was created
    mock_table_client.create_entity.assert_called_once()
    call_args = mock_table_client.create_entity.call_args
    entity = call_args[1]["entity"]

    assert entity["PartitionKey"] == execution_id
    assert entity["Status"] == "queued"
    assert json.loads(entity["Scenarios"]) == ["compute-01", "networking-01"]
    assert entity["DurationHours"] == 2
    assert json.loads(entity["Tags"]) == {"requester": "admin@example.com"}


@pytest.mark.asyncio
async def test_create_execution_defaults(execution_tracker, mock_table_client):
    """Test creating execution with default values."""
    mock_table_client.create_entity = AsyncMock()

    await execution_tracker.create_execution(
        scenarios=["compute-01"],
    )

    call_args = mock_table_client.create_entity.call_args
    entity = call_args[1]["entity"]

    assert entity["DurationHours"] == 8  # Default
    assert json.loads(entity["Tags"]) == {}  # Empty tags


@pytest.mark.asyncio
async def test_update_status_to_running(execution_tracker, mock_table_client):
    """Test updating execution status to RUNNING."""
    execution_id = "exec-20251115-abc123"
    now = datetime.now(UTC)

    # Mock get_latest_record
    mock_table_client.query_entities = MagicMock(
        return_value=async_iterator(
            [
                {
                    "PartitionKey": execution_id,
                    "RowKey": now.isoformat(),
                    "Status": "queued",
                    "Scenarios": json.dumps(["compute-01"]),
                    "DurationHours": 8,
                    "Tags": json.dumps({}),
                    "CreatedAt": now.isoformat(),
                }
            ]
        )
    )
    mock_table_client.create_entity = AsyncMock()

    await execution_tracker.update_status(
        execution_id=execution_id,
        status=OnDemandExecutionStatus.RUNNING,
        container_ids=["container-01"],
    )

    # Verify entity was created with RUNNING status
    call_args = mock_table_client.create_entity.call_args
    entity = call_args[1]["entity"]

    assert entity["Status"] == "running"
    assert json.loads(entity["ContainerIds"]) == ["container-01"]
    assert "StartedAt" in entity


@pytest.mark.asyncio
async def test_update_status_to_completed(execution_tracker, mock_table_client):
    """Test updating execution status to COMPLETED."""
    execution_id = "exec-20251115-abc123"
    now = datetime.now(UTC)

    mock_table_client.query_entities = MagicMock(
        return_value=async_iterator(
            [
                {
                    "PartitionKey": execution_id,
                    "RowKey": now.isoformat(),
                    "Status": "running",
                    "Scenarios": json.dumps(["compute-01"]),
                    "DurationHours": 8,
                    "Tags": json.dumps({}),
                    "CreatedAt": now.isoformat(),
                }
            ]
        )
    )
    mock_table_client.create_entity = AsyncMock()

    await execution_tracker.update_status(
        execution_id=execution_id,
        status=OnDemandExecutionStatus.COMPLETED,
        resources_created=25,
        report_url="https://storage.blob.core.windows.net/reports/exec-123.json",
    )

    call_args = mock_table_client.create_entity.call_args
    entity = call_args[1]["entity"]

    assert entity["Status"] == "completed"
    assert entity["ResourcesCreated"] == 25
    assert entity["ReportUrl"] == "https://storage.blob.core.windows.net/reports/exec-123.json"
    assert "CompletedAt" in entity


@pytest.mark.asyncio
async def test_update_status_to_failed(execution_tracker, mock_table_client):
    """Test updating execution status to FAILED with error."""
    execution_id = "exec-20251115-abc123"
    now = datetime.now(UTC)

    mock_table_client.query_entities = MagicMock(
        return_value=async_iterator(
            [
                {
                    "PartitionKey": execution_id,
                    "RowKey": now.isoformat(),
                    "Status": "running",
                    "Scenarios": json.dumps(["compute-01"]),
                    "DurationHours": 8,
                    "Tags": json.dumps({}),
                    "CreatedAt": now.isoformat(),
                }
            ]
        )
    )
    mock_table_client.create_entity = AsyncMock()

    await execution_tracker.update_status(
        execution_id=execution_id,
        status=OnDemandExecutionStatus.FAILED,
        error_message="Container deployment failed",
    )

    call_args = mock_table_client.create_entity.call_args
    entity = call_args[1]["entity"]

    assert entity["Status"] == "failed"
    assert entity["ErrorMessage"] == "Container deployment failed"
    assert "CompletedAt" in entity


@pytest.mark.asyncio
async def test_get_latest_record(execution_tracker, mock_table_client):
    """Test getting latest record for execution."""
    execution_id = "exec-20251115-abc123"
    now = datetime.now(UTC)
    old_time = datetime(2025, 11, 14, 12, 0, 0, tzinfo=UTC)

    # Mock multiple records (older and newer)
    mock_entities = [
        {
            "PartitionKey": execution_id,
            "RowKey": old_time.isoformat(),
            "Status": "queued",
        },
        {
            "PartitionKey": execution_id,
            "RowKey": now.isoformat(),
            "Status": "running",
        },
    ]

    mock_table_client.query_entities = MagicMock(return_value=async_iterator(mock_entities))

    record = await execution_tracker.get_latest_record(execution_id)

    # Should return the newest record (running)
    assert record["Status"] == "running"
    assert record["RowKey"] == now.isoformat()


@pytest.mark.asyncio
async def test_get_latest_record_not_found(execution_tracker, mock_table_client):
    """Test getting record that doesn't exist."""

    mock_table_client.query_entities = MagicMock(return_value=async_iterator([]))

    with pytest.raises(ResourceNotFoundError):
        await execution_tracker.get_latest_record("exec-nonexistent")


@pytest.mark.asyncio
async def test_get_execution_status(execution_tracker, mock_table_client):
    """Test getting full execution status."""
    execution_id = "exec-20251115-abc123"
    now = datetime.now(UTC)

    mock_entity = {
        "PartitionKey": execution_id,
        "RowKey": now.isoformat(),
        "Status": "running",
        "Scenarios": json.dumps(["compute-01", "networking-01"]),
        "ContainerIds": json.dumps(["container-01", "container-02"]),
        "Tags": json.dumps({"requester": "admin"}),
        "ResourcesCreated": 15,
        "CreatedAt": now.isoformat(),
        "StartedAt": now.isoformat(),
    }

    mock_table_client.query_entities = MagicMock(return_value=async_iterator([mock_entity]))

    status = await execution_tracker.get_execution_status(execution_id)

    assert status.execution_id == execution_id
    assert status.status == OnDemandExecutionStatus.RUNNING
    assert status.scenarios == ["compute-01", "networking-01"]
    assert status.container_ids == ["container-01", "container-02"]
    assert status.resources_created == 15
    assert status.progress is not None
    assert status.progress["total"] == 2


@pytest.mark.asyncio
async def test_get_execution_status_completed(execution_tracker, mock_table_client):
    """Test getting status of completed execution."""
    execution_id = "exec-20251115-abc123"
    now = datetime.now(UTC)

    mock_entity = {
        "PartitionKey": execution_id,
        "RowKey": now.isoformat(),
        "Status": "completed",
        "Scenarios": json.dumps(["compute-01"]),
        "ContainerIds": json.dumps(["container-01"]),
        "Tags": json.dumps({}),
        "ResourcesCreated": 25,
        "CreatedAt": now.isoformat(),
        "StartedAt": now.isoformat(),
        "CompletedAt": now.isoformat(),
        "ReportUrl": "https://storage/report.json",
    }

    mock_table_client.query_entities = MagicMock(return_value=async_iterator([mock_entity]))

    status = await execution_tracker.get_execution_status(execution_id)

    assert status.status == OnDemandExecutionStatus.COMPLETED
    assert status.completed_at is not None
    assert status.report_url == "https://storage/report.json"
    assert status.progress is None  # No progress for completed


@pytest.mark.asyncio
async def test_list_executions(execution_tracker, mock_table_client):
    """Test listing executions."""
    now = datetime.now(UTC)

    mock_entities = [
        {
            "PartitionKey": "exec-20251115-abc123",
            "RowKey": now.isoformat(),
            "Status": "running",
            "Scenarios": json.dumps(["compute-01"]),
            "ContainerIds": json.dumps([]),
            "Tags": json.dumps({}),
            "CreatedAt": now.isoformat(),
        },
        {
            "PartitionKey": "exec-20251115-def456",
            "RowKey": now.isoformat(),
            "Status": "completed",
            "Scenarios": json.dumps(["networking-01"]),
            "ContainerIds": json.dumps([]),
            "Tags": json.dumps({}),
            "CreatedAt": now.isoformat(),
        },
    ]

    mock_table_client.query_entities = MagicMock(return_value=async_iterator(mock_entities))

    # Mock get_execution_status to return simple responses
    async def mock_get_status(execution_id):
        return MagicMock(
            execution_id=execution_id,
            created_at=now,
        )

    execution_tracker.get_execution_status = mock_get_status

    executions = await execution_tracker.list_executions(limit=10)

    assert len(executions) == 2


@pytest.mark.asyncio
async def test_list_executions_filter_by_status(execution_tracker, mock_table_client):
    """Test listing executions filtered by status."""
    now = datetime.now(UTC)

    mock_entities = [
        {
            "PartitionKey": "exec-20251115-abc123",
            "RowKey": now.isoformat(),
            "Status": "running",
            "Scenarios": json.dumps(["compute-01"]),
            "ContainerIds": json.dumps([]),
            "Tags": json.dumps({}),
            "CreatedAt": now.isoformat(),
        },
    ]

    def mock_query_entities(**kwargs):
        query = kwargs.get("query_filter", "")
        assert "Status eq 'running'" in query
        return async_iterator(mock_entities)

    mock_table_client.query_entities = MagicMock(side_effect=mock_query_entities)

    async def mock_get_status(execution_id):
        return MagicMock(execution_id=execution_id, created_at=now)

    execution_tracker.get_execution_status = mock_get_status

    executions = await execution_tracker.list_executions(
        status=OnDemandExecutionStatus.RUNNING,
        limit=10,
    )

    assert len(executions) == 1


@pytest.mark.asyncio
async def test_delete_execution(execution_tracker, mock_table_client):
    """Test deleting execution records."""
    execution_id = "exec-20251115-abc123"
    datetime.now(UTC)

    mock_entities = [
        {
            "PartitionKey": execution_id,
            "RowKey": "2025-11-15T08:00:00+00:00",
        },
        {
            "PartitionKey": execution_id,
            "RowKey": "2025-11-15T09:00:00+00:00",
        },
    ]

    mock_table_client.query_entities = MagicMock(return_value=async_iterator(mock_entities))
    mock_table_client.delete_entity = AsyncMock()

    await execution_tracker.delete_execution(execution_id)

    # Should delete both records
    assert mock_table_client.delete_entity.call_count == 2
