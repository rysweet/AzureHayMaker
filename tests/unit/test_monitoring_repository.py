"""
Unit tests for monitoring_repository module.

Tests cover:
- MonitoringRepository initialization
- Status file retrieval (get_status)
- Run report retrieval (get_run_report)
- Run resources retrieval (get_run_resources)
- Blob storage operations and error handling

Testing approach:
- Mock Azure Blob Storage SDK
- Test data access layer without business logic
- Focus on error handling (ResourceNotFoundError, JSON parsing)
"""

import json
from unittest.mock import Mock

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.orchestrator.repositories.monitoring_repository import (
    MonitoringRepository,
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_blob_client():
    """Create a mock Azure Blob Service client."""
    return Mock()


@pytest.fixture
def sample_status_data():
    """Sample status data from blob storage."""
    return {
        "status": "running",
        "health": "healthy",
        "current_run_id": "run-123",
        "started_at": "2025-11-25T10:00:00Z",
    }


@pytest.fixture
def sample_run_data():
    """Sample run report data."""
    return {
        "run_id": "run-123",
        "started_at": "2025-11-25T10:00:00Z",
        "status": "completed",
        "scenarios": [],
        "total_resources": 50,
    }


# ==============================================================================
# TESTS: Initialization
# ==============================================================================


def test_monitoring_repository_init(mock_blob_client):
    """Test MonitoringRepository initialization."""
    repo = MonitoringRepository(mock_blob_client)

    assert repo.blob_client == mock_blob_client


# ==============================================================================
# TESTS: get_status
# ==============================================================================


@pytest.mark.asyncio
async def test_get_status_happy_path(mock_blob_client, sample_status_data):
    """Test retrieving status file from storage."""
    mock_blob = Mock()
    mock_download = Mock()
    mock_download.readall = Mock(return_value=json.dumps(sample_status_data).encode())
    mock_blob.download_blob = Mock(return_value=mock_download)
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)
    result = await repo.get_status()

    assert result == sample_status_data
    mock_blob_client.get_blob_client.assert_called_once_with(
        container="execution-state", blob="current_status.json"
    )


@pytest.mark.asyncio
async def test_get_status_not_found(mock_blob_client):
    """Test get_status returns None when file doesn't exist."""
    mock_blob = Mock()
    mock_blob.download_blob = Mock(side_effect=ResourceNotFoundError("Not found"))
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)
    result = await repo.get_status()

    assert result is None


# ==============================================================================
# TESTS: get_run_report
# ==============================================================================


@pytest.mark.asyncio
async def test_get_run_report_happy_path(mock_blob_client, sample_run_data):
    """Test retrieving run report from storage."""
    mock_blob = Mock()
    mock_download = Mock()
    mock_download.readall = Mock(return_value=json.dumps(sample_run_data).encode())
    mock_blob.download_blob = Mock(return_value=mock_download)
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)
    result = await repo.get_run_report("run-123")

    assert result == sample_run_data
    mock_blob_client.get_blob_client.assert_called_once_with(
        container="execution-reports", blob="run-123/report.json"
    )


@pytest.mark.asyncio
async def test_get_run_report_not_found(mock_blob_client):
    """Test error when run report doesn't exist."""
    mock_blob = Mock()
    mock_blob.download_blob = Mock(side_effect=ResourceNotFoundError("Not found"))
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)

    with pytest.raises(ResourceNotFoundError):
        await repo.get_run_report("nonexistent-run")


# ==============================================================================
# TESTS: get_run_resources
# ==============================================================================


@pytest.mark.asyncio
async def test_get_run_resources_happy_path(mock_blob_client):
    """Test retrieving run resources from storage."""
    resources_data = {"resources": [{"id": "res-001", "type": "VM"}]}

    mock_blob = Mock()
    mock_download = Mock()
    mock_download.readall = Mock(return_value=json.dumps(resources_data).encode())
    mock_blob.download_blob = Mock(return_value=mock_download)
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)
    result = await repo.get_run_resources("run-123")

    assert result == resources_data
    mock_blob_client.get_blob_client.assert_called_once_with(
        container="execution-reports", blob="run-123/resources.json"
    )


@pytest.mark.asyncio
async def test_get_run_resources_not_found(mock_blob_client):
    """Test error when resources file doesn't exist."""
    mock_blob = Mock()
    mock_blob.download_blob = Mock(side_effect=ResourceNotFoundError("Not found"))
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)

    with pytest.raises(ResourceNotFoundError):
        await repo.get_run_resources("nonexistent-run")


# ==============================================================================
# TESTS: _read_blob_json (Internal Method)
# ==============================================================================


@pytest.mark.asyncio
async def test_read_blob_json_string_data(mock_blob_client):
    """Test reading blob with string data."""
    mock_blob = Mock()
    mock_download = Mock()
    mock_download.readall = Mock(return_value='{"key": "value"}')
    mock_blob.download_blob = Mock(return_value=mock_download)
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)
    result = await repo._read_blob_json("test-container", "test-blob.json")

    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_read_blob_json_bytes_data(mock_blob_client):
    """Test reading blob with bytes data."""
    mock_blob = Mock()
    mock_download = Mock()
    mock_download.readall = Mock(return_value=b'{"key": "value"}')
    mock_blob.download_blob = Mock(return_value=mock_download)
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)
    result = await repo._read_blob_json("test-container", "test-blob.json")

    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_read_blob_json_invalid_json(mock_blob_client):
    """Test error handling for corrupted JSON data."""
    mock_blob = Mock()
    mock_download = Mock()
    mock_download.readall = Mock(return_value=b'not valid json')
    mock_blob.download_blob = Mock(return_value=mock_download)
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)

    with pytest.raises(Exception, match="Corrupted data in storage"):
        await repo._read_blob_json("test-container", "test-blob.json")


@pytest.mark.asyncio
async def test_read_blob_json_storage_error(mock_blob_client):
    """Test error handling for storage failures."""
    mock_blob = Mock()
    mock_blob.download_blob = Mock(side_effect=Exception("Connection timeout"))
    mock_blob_client.get_blob_client = Mock(return_value=mock_blob)

    repo = MonitoringRepository(mock_blob_client)

    with pytest.raises(Exception):
        await repo._read_blob_json("test-container", "test-blob.json")
