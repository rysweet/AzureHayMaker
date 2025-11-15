"""
Unit tests for monitoring_api module using TDD approach.

Tests cover the 3 core endpoints:
- GET /status - Get current orchestrator status
- GET /runs/{run_id} - Get detailed run information
- GET /runs/{run_id}/resources - Get resources created in a run

Tests prioritize contract verification over implementation details.
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from azure.core.exceptions import ResourceNotFoundError
import azure.functions as func

# Import the module to test
from azure_haymaker.orchestrator.monitoring_api import (
    get_status,
    get_run_details,
    get_run_resources,
    APIError,
    RunNotFoundError,
    InvalidParameterError,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def mock_request():
    """Create a mock Azure Functions HTTP request."""
    request = Mock(spec=func.HttpRequest)
    request.method = "GET"
    request.url = "http://localhost:7071/api/v1/status"
    request.get_json = Mock(return_value={})
    request.params = {}
    request.headers = {}
    return request


@pytest.fixture
def mock_blob_service_client():
    """Create a mock Azure Blob Service client."""
    client = Mock()
    return client


def create_download_mock(data):
    """Helper to create a download mock with proper readall return."""
    download_mock = Mock()
    if isinstance(data, dict):
        download_mock.readall = Mock(return_value=json.dumps(data).encode())
    elif isinstance(data, bytes):
        download_mock.readall = Mock(return_value=data)
    else:
        download_mock.readall = Mock(return_value=data)
    return download_mock


@pytest.fixture
def sample_status_data():
    """Sample orchestrator status data from storage."""
    return {
        "status": "running",
        "health": "healthy",
        "current_run_id": "550e8400-e29b-41d4-a716-446655440000",
        "started_at": "2025-11-14T12:00:00Z",
        "scheduled_end_at": "2025-11-14T20:00:00Z",
        "phase": "monitoring",
        "scenarios_count": 15,
        "scenarios_completed": 8,
        "scenarios_running": 6,
        "scenarios_failed": 1,
    }


@pytest.fixture
def sample_run_data():
    """Sample execution run data."""
    return {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "started_at": "2025-11-14T12:00:00Z",
        "ended_at": "2025-11-14T20:05:23Z",
        "status": "completed",
        "phase": "completed",
        "simulation_size": "medium",
        "scenarios": [
            {
                "scenario_name": "ai-ml-01-cognitive-services-vision",
                "status": "cleanup_complete",
                "started_at": "2025-11-14T12:05:00Z",
                "ended_at": "2025-11-14T20:02:15Z",
                "resources_created": 25,
                "cleanup_status": "complete",
            }
        ],
        "total_resources": 287,
        "total_service_principals": 15,
        "cleanup_verification": {
            "expected_deleted": 287,
            "actually_deleted": 287,
            "forced_deletions": 3,
            "deletion_failures": 0,
        },
        "errors": [],
    }


@pytest.fixture
def sample_resources_data():
    """Sample resources list."""
    return [
        {
            "resource_id": "/subscriptions/12345/resourceGroups/haymaker-vision-rg",
            "resource_type": "Microsoft.Resources/resourceGroups",
            "resource_name": "haymaker-vision-rg",
            "scenario_name": "ai-ml-01-cognitive-services-vision",
            "created_at": "2025-11-14T12:05:30Z",
            "deleted_at": "2025-11-14T20:02:00Z",
            "status": "deleted",
            "deletion_attempts": 1,
            "tags": {
                "AzureHayMaker-managed": "true",
                "RunId": "550e8400-e29b-41d4-a716-446655440000",
            },
        },
        {
            "resource_id": "/subscriptions/12345/resourceGroups/haymaker-vision-rg/providers/Microsoft.CognitiveServices/accounts/haymaker-vision-cs",
            "resource_type": "Microsoft.CognitiveServices/accounts",
            "resource_name": "haymaker-vision-cs",
            "scenario_name": "ai-ml-01-cognitive-services-vision",
            "created_at": "2025-11-14T12:08:15Z",
            "deleted_at": "2025-11-14T20:01:30Z",
            "status": "deleted",
            "deletion_attempts": 1,
            "tags": {
                "AzureHayMaker-managed": "true",
                "RunId": "550e8400-e29b-41d4-a716-446655440000",
            },
        },
    ]


# ==============================================================================
# TEST: get_status() - GET /status
# ==============================================================================

@pytest.mark.asyncio
async def test_get_status_returns_200_with_status(mock_request, sample_status_data, mock_blob_service_client):
    """Test get_status returns 200 and status JSON."""
    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(sample_status_data))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_status(mock_request, mock_blob_service_client)

    assert response.status_code == 200
    response_data = json.loads(response.get_body())
    assert response_data["status"] == "running"
    assert response_data["current_run_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert response_data["phase"] == "monitoring"


@pytest.mark.asyncio
async def test_get_status_returns_idle_when_no_run_active(mock_request, mock_blob_service_client):
    """Test get_status returns idle status when no run is active."""
    # Simulate blob not found - will return idle
    blob_client = Mock()
    blob_client.download_blob = Mock(side_effect=ResourceNotFoundError("Not found"))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_status(mock_request, mock_blob_service_client)

    assert response.status_code == 200
    response_data = json.loads(response.get_body())
    assert response_data["status"] == "idle"


@pytest.mark.asyncio
async def test_get_status_handles_storage_error(mock_request, mock_blob_service_client):
    """Test get_status returns 500 when storage fails."""
    blob_client = Mock()
    blob_client.download_blob = Mock(side_effect=Exception("Storage error"))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_status(mock_request, mock_blob_service_client)

    assert response.status_code == 500
    response_data = json.loads(response.get_body())
    assert "error" in response_data


@pytest.mark.asyncio
async def test_get_status_response_has_required_fields(mock_request, sample_status_data, mock_blob_service_client):
    """Test get_status response includes all required OpenAPI fields."""
    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(sample_status_data))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_status(mock_request, mock_blob_service_client)
    response_data = json.loads(response.get_body())

    required_fields = ["status", "health"]
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"

    if response_data["status"] == "running":
        assert "current_run_id" in response_data
        assert "started_at" in response_data
        assert "phase" in response_data


# ==============================================================================
# TEST: get_run_details() - GET /runs/{run_id}
# ==============================================================================

@pytest.mark.asyncio
async def test_get_run_details_returns_200_with_run_data(mock_request, sample_run_data, mock_blob_service_client):
    """Test get_run_details returns 200 and run details JSON."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id}

    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(sample_run_data))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_details(mock_request, mock_blob_service_client)

    assert response.status_code == 200
    response_data = json.loads(response.get_body())
    assert response_data["run_id"] == run_id
    assert response_data["status"] == "completed"
    assert response_data["total_resources"] == 287


@pytest.mark.asyncio
async def test_get_run_details_returns_404_for_nonexistent_run(mock_request, mock_blob_service_client):
    """Test get_run_details returns 404 when run doesn't exist."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id}

    blob_client = Mock()
    blob_client.download_blob = Mock(side_effect=ResourceNotFoundError("Not found"))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_details(mock_request, mock_blob_service_client)

    assert response.status_code == 404
    response_data = json.loads(response.get_body())
    assert "error" in response_data
    assert "RUN_NOT_FOUND" in response_data.get("error", {}).get("code", "")


@pytest.mark.asyncio
async def test_get_run_details_validates_run_id_format(mock_request, mock_blob_service_client):
    """Test get_run_details validates UUID format."""
    mock_request.params = {"run_id": "not-a-valid-uuid"}

    response = await get_run_details(mock_request, mock_blob_service_client)

    assert response.status_code == 400
    response_data = json.loads(response.get_body())
    assert "error" in response_data


@pytest.mark.asyncio
async def test_get_run_details_response_has_required_fields(mock_request, sample_run_data, mock_blob_service_client):
    """Test get_run_details response includes required OpenAPI fields."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id}

    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(sample_run_data))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_details(mock_request, mock_blob_service_client)
    response_data = json.loads(response.get_body())

    required_fields = ["run_id", "started_at", "status", "scenarios", "cleanup_verification"]
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"


@pytest.mark.asyncio
async def test_get_run_details_handles_corrupted_data(mock_request, mock_blob_service_client):
    """Test get_run_details handles corrupted JSON in storage."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id}

    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(b"invalid json{"))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_details(mock_request, mock_blob_service_client)

    assert response.status_code == 500
    response_data = json.loads(response.get_body())
    assert "error" in response_data


# ==============================================================================
# TEST: get_run_resources() - GET /runs/{run_id}/resources
# ==============================================================================

@pytest.mark.asyncio
async def test_get_run_resources_returns_200_with_resources(mock_request, sample_resources_data, mock_blob_service_client):
    """Test get_run_resources returns 200 and resources list."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id, "page": "1", "page_size": "10"}

    resources_response = {
        "run_id": run_id,
        "resources": sample_resources_data,
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total_items": 2,
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        },
    }
    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(resources_response))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_resources(mock_request, mock_blob_service_client)

    assert response.status_code == 200
    response_data = json.loads(response.get_body())
    assert response_data["run_id"] == run_id
    assert len(response_data["resources"]) == 2
    assert "pagination" in response_data


@pytest.mark.asyncio
async def test_get_run_resources_returns_404_for_nonexistent_run(mock_request, mock_blob_service_client):
    """Test get_run_resources returns 404 when run doesn't exist."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id, "page": "1", "page_size": "10"}

    blob_client = Mock()
    blob_client.download_blob = Mock(side_effect=ResourceNotFoundError("Not found"))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_resources(mock_request, mock_blob_service_client)

    assert response.status_code == 404
    response_data = json.loads(response.get_body())
    assert "error" in response_data


@pytest.mark.asyncio
async def test_get_run_resources_validates_run_id_format(mock_request, mock_blob_service_client):
    """Test get_run_resources validates UUID format."""
    mock_request.params = {"run_id": "invalid-uuid", "page": "1", "page_size": "10"}

    response = await get_run_resources(mock_request, mock_blob_service_client)

    assert response.status_code == 400
    response_data = json.loads(response.get_body())
    assert "error" in response_data


@pytest.mark.asyncio
async def test_get_run_resources_validates_page_size(mock_request, mock_blob_service_client):
    """Test get_run_resources validates page_size <= 500."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id, "page": "1", "page_size": "1000"}

    response = await get_run_resources(mock_request, mock_blob_service_client)

    assert response.status_code == 400
    response_data = json.loads(response.get_body())
    assert "error" in response_data


@pytest.mark.asyncio
async def test_get_run_resources_supports_pagination(mock_request, mock_blob_service_client):
    """Test get_run_resources supports pagination."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id, "page": "2", "page_size": "10"}

    resources_response = {
        "run_id": run_id,
        "resources": [],
        "pagination": {
            "page": 2,
            "page_size": 10,
            "total_items": 25,
            "total_pages": 3,
            "has_next": True,
            "has_previous": True,
        },
    }
    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(resources_response))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_resources(mock_request, mock_blob_service_client)

    assert response.status_code == 200
    response_data = json.loads(response.get_body())
    assert response_data["pagination"]["page"] == 2
    assert response_data["pagination"]["has_previous"] is True


@pytest.mark.asyncio
async def test_get_run_resources_filters_by_scenario(mock_request, sample_resources_data, mock_blob_service_client):
    """Test get_run_resources filters by scenario_name."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    scenario_name = "ai-ml-01-cognitive-services-vision"
    mock_request.params = {
        "run_id": run_id,
        "page": "1",
        "page_size": "10",
        "scenario_name": scenario_name,
    }

    resources_response = {
        "run_id": run_id,
        "resources": sample_resources_data,
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total_items": 2,
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        },
    }
    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(resources_response))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_resources(mock_request, mock_blob_service_client)

    assert response.status_code == 200
    response_data = json.loads(response.get_body())
    for resource in response_data["resources"]:
        assert resource["scenario_name"] == scenario_name


@pytest.mark.asyncio
async def test_get_run_resources_response_has_required_fields(mock_request, sample_resources_data, mock_blob_service_client):
    """Test get_run_resources response includes required OpenAPI fields."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id, "page": "1", "page_size": "10"}

    resources_response = {
        "run_id": run_id,
        "resources": sample_resources_data,
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total_items": 2,
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        },
    }
    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(resources_response))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_resources(mock_request, mock_blob_service_client)
    response_data = json.loads(response.get_body())

    required_fields = ["run_id", "resources", "pagination"]
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"

    pagination_fields = ["page", "page_size", "total_items", "total_pages", "has_next", "has_previous"]
    for field in pagination_fields:
        assert field in response_data["pagination"], f"Missing pagination field: {field}"


# ==============================================================================
# TEST: Error Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_error_responses_have_standard_format(mock_request, mock_blob_service_client):
    """Test all error responses follow standard error format."""
    run_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_request.params = {"run_id": run_id}

    blob_client = Mock()
    blob_client.download_blob = Mock(side_effect=ResourceNotFoundError("Not found"))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_run_details(mock_request, mock_blob_service_client)

    assert response.status_code == 404
    response_data = json.loads(response.get_body())

    assert "error" in response_data
    assert "code" in response_data["error"]
    assert "message" in response_data["error"]


@pytest.mark.asyncio
async def test_validation_errors_return_400(mock_request, mock_blob_service_client):
    """Test validation errors return 400 status code."""
    mock_request.params = {"run_id": "invalid"}

    response = await get_run_details(mock_request, mock_blob_service_client)

    assert response.status_code == 400
    response_data = json.loads(response.get_body())
    assert "error" in response_data


# ==============================================================================
# TEST: Content-Type and Headers
# ==============================================================================

@pytest.mark.asyncio
async def test_response_content_type_is_json(mock_request, sample_status_data, mock_blob_service_client):
    """Test all responses have application/json content type."""
    blob_client = Mock()
    blob_client.download_blob = Mock(return_value=create_download_mock(sample_status_data))
    mock_blob_service_client.get_blob_client = Mock(return_value=blob_client)

    response = await get_status(mock_request, mock_blob_service_client)

    assert "application/json" in response.headers.get("Content-Type", "")


# ==============================================================================
# TEST: Exception Classes
# ==============================================================================

def test_api_error_exception():
    """Test APIError exception class."""
    error = APIError("Test error", 500)
    assert str(error) == "Test error"
    assert error.status_code == 500


def test_run_not_found_error_exception():
    """Test RunNotFoundError exception class."""
    run_id = "test-id"
    error = RunNotFoundError(run_id)
    assert run_id in str(error)
    assert error.status_code == 404


def test_invalid_parameter_error_exception():
    """Test InvalidParameterError exception class."""
    error = InvalidParameterError("page_size", "Invalid value")
    assert "page_size" in str(error)
    assert error.status_code == 400
