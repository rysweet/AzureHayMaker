"""
Unit tests for monitoring_service module.

Tests cover:
- MonitoringService initialization
- Status retrieval with idle state handling
- Run details retrieval with validation
- Run resources retrieval with filtering and pagination
- Input validation (run_id, pagination, filters)

Testing approach:
- Mock MonitoringRepository
- Test business logic and validation rules
- Focus on filtering, pagination, and error handling
"""

from unittest.mock import AsyncMock, Mock

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.orchestrator.models.api_errors import (
    InvalidParameterError,
    RunNotFoundError,
)
from azure_haymaker.orchestrator.services.monitoring_service import MonitoringService


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_repository():
    """Create a mock MonitoringRepository."""
    return Mock()


@pytest.fixture
def sample_status_data():
    """Sample status data from repository."""
    return {
        "status": "running",
        "health": "healthy",
        "current_run_id": "550e8400-e29b-41d4-a716-446655440000",
        "started_at": "2025-11-25T10:00:00Z",
        "scenarios_count": 10,
    }


@pytest.fixture
def sample_run_data():
    """Sample run data from repository."""
    return {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "started_at": "2025-11-25T10:00:00Z",
        "ended_at": "2025-11-25T18:00:00Z",
        "status": "completed",
        "scenarios": [],
        "total_resources": 50,
    }


@pytest.fixture
def sample_resources_data():
    """Sample resources data from repository."""
    return {
        "resources": [
            {
                "id": "res-001",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "scenario_name": "compute-01",
                "status": "created",
            },
            {
                "id": "res-002",
                "resource_type": "Microsoft.Storage/storageAccounts",
                "scenario_name": "storage-01",
                "status": "deleted",
            },
        ]
    }


# ==============================================================================
# TESTS: Initialization
# ==============================================================================


def test_monitoring_service_init(mock_repository):
    """Test MonitoringService initialization."""
    service = MonitoringService(mock_repository)

    assert service.repository == mock_repository


# ==============================================================================
# TESTS: get_status
# ==============================================================================


@pytest.mark.asyncio
async def test_get_status_happy_path(mock_repository, sample_status_data):
    """Test getting status with data from repository."""
    mock_repository.get_status = AsyncMock(return_value=sample_status_data)

    service = MonitoringService(mock_repository)
    result = await service.get_status()

    assert result["status"] == "running"
    assert result["health"] == "healthy"
    assert result["current_run_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert result["scenarios_count"] == 10


@pytest.mark.asyncio
async def test_get_status_idle_when_no_file(mock_repository):
    """Test get_status returns idle state when no status file exists."""
    mock_repository.get_status = AsyncMock(return_value=None)

    service = MonitoringService(mock_repository)
    result = await service.get_status()

    assert result["status"] == "idle"
    assert result["health"] == "healthy"
    assert result["current_run_id"] is None


# ==============================================================================
# TESTS: get_run_details
# ==============================================================================


@pytest.mark.asyncio
async def test_get_run_details_happy_path(mock_repository, sample_run_data):
    """Test getting run details with valid UUID."""
    mock_repository.get_run_report = AsyncMock(return_value=sample_run_data)

    service = MonitoringService(mock_repository)
    result = await service.get_run_details("550e8400-e29b-41d4-a716-446655440000")

    assert result["run_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert result["status"] == "completed"
    assert result["total_resources"] == 50


@pytest.mark.asyncio
async def test_get_run_details_invalid_uuid(mock_repository):
    """Test error when run_id is not a valid UUID."""
    service = MonitoringService(mock_repository)

    with pytest.raises(InvalidParameterError, match="Must be a valid UUID"):
        await service.get_run_details("not-a-uuid")


@pytest.mark.asyncio
async def test_get_run_details_not_found(mock_repository):
    """Test error when run doesn't exist."""
    mock_repository.get_run_report = AsyncMock(side_effect=ResourceNotFoundError("Not found"))

    service = MonitoringService(mock_repository)

    with pytest.raises(RunNotFoundError):
        await service.get_run_details("550e8400-e29b-41d4-a716-446655440000")


# ==============================================================================
# TESTS: get_run_resources
# ==============================================================================


@pytest.mark.asyncio
async def test_get_run_resources_happy_path(mock_repository, sample_resources_data):
    """Test getting run resources without filters."""
    mock_repository.get_run_resources = AsyncMock(return_value=sample_resources_data)

    service = MonitoringService(mock_repository)
    result = await service.get_run_resources("550e8400-e29b-41d4-a716-446655440000")

    assert result["run_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert len(result["resources"]) == 2
    assert result["pagination"]["total_items"] == 2
    assert result["pagination"]["page"] == 1


@pytest.mark.asyncio
async def test_get_run_resources_with_scenario_filter(mock_repository, sample_resources_data):
    """Test filtering resources by scenario_name."""
    mock_repository.get_run_resources = AsyncMock(return_value=sample_resources_data)

    service = MonitoringService(mock_repository)
    result = await service.get_run_resources(
        "550e8400-e29b-41d4-a716-446655440000", scenario_name="compute-01"
    )

    assert len(result["resources"]) == 1
    assert result["resources"][0]["scenario_name"] == "compute-01"


@pytest.mark.asyncio
async def test_get_run_resources_with_status_filter(mock_repository, sample_resources_data):
    """Test filtering resources by status."""
    mock_repository.get_run_resources = AsyncMock(return_value=sample_resources_data)

    service = MonitoringService(mock_repository)
    result = await service.get_run_resources(
        "550e8400-e29b-41d4-a716-446655440000", status="created"
    )

    assert len(result["resources"]) == 1
    assert result["resources"][0]["status"] == "created"


@pytest.mark.asyncio
async def test_get_run_resources_with_pagination(mock_repository, sample_resources_data):
    """Test pagination of resources."""
    mock_repository.get_run_resources = AsyncMock(return_value=sample_resources_data)

    service = MonitoringService(mock_repository)
    result = await service.get_run_resources(
        "550e8400-e29b-41d4-a716-446655440000", page=1, page_size=1
    )

    assert len(result["resources"]) == 1
    assert result["pagination"]["page"] == 1
    assert result["pagination"]["page_size"] == 1
    assert result["pagination"]["total_pages"] == 2
    assert result["pagination"]["has_next"] is True
    assert result["pagination"]["has_previous"] is False


@pytest.mark.asyncio
async def test_get_run_resources_invalid_run_id(mock_repository):
    """Test error when run_id is not a valid UUID."""
    service = MonitoringService(mock_repository)

    with pytest.raises(InvalidParameterError, match="Must be a valid UUID"):
        await service.get_run_resources("not-a-uuid")


@pytest.mark.asyncio
async def test_get_run_resources_invalid_page(mock_repository):
    """Test error when page number is invalid."""
    service = MonitoringService(mock_repository)

    with pytest.raises(InvalidParameterError, match="page must be >= 1"):
        await service.get_run_resources("550e8400-e29b-41d4-a716-446655440000", page=0)


@pytest.mark.asyncio
async def test_get_run_resources_invalid_page_size(mock_repository):
    """Test error when page_size is invalid."""
    service = MonitoringService(mock_repository)

    with pytest.raises(InvalidParameterError, match="page_size must be between 1 and 500"):
        await service.get_run_resources("550e8400-e29b-41d4-a716-446655440000", page_size=0)

    with pytest.raises(InvalidParameterError, match="page_size must be between 1 and 500"):
        await service.get_run_resources("550e8400-e29b-41d4-a716-446655440000", page_size=600)


@pytest.mark.asyncio
async def test_get_run_resources_invalid_status(mock_repository):
    """Test error when status filter is invalid."""
    service = MonitoringService(mock_repository)

    with pytest.raises(InvalidParameterError, match="Must be one of"):
        await service.get_run_resources("550e8400-e29b-41d4-a716-446655440000", status="invalid")


@pytest.mark.asyncio
async def test_get_run_resources_page_exceeds_total(mock_repository, sample_resources_data):
    """Test error when page number exceeds total pages."""
    mock_repository.get_run_resources = AsyncMock(return_value=sample_resources_data)

    service = MonitoringService(mock_repository)

    with pytest.raises(InvalidParameterError, match="exceeds total pages"):
        await service.get_run_resources("550e8400-e29b-41d4-a716-446655440000", page=10)
