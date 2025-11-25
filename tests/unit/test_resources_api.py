"""
Unit tests for resources_api module.

Tests cover:
- GET /resources - List all resources with filtering (execution_id, scenario, status)
- GET /resources/{resource_id} - Get specific resource details
- Query parameter validation
- Error handling (authentication, storage failures, invalid inputs)

Testing approach:
- Test behavior at API boundaries
- Mock Azure SDK clients (TableServiceClient)
- Focus on happy path + error cases + boundary conditions
"""

import json
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import azure.functions as func
import pytest

from azure_haymaker.orchestrator.resources_api import (
    ResourceInfo,
    get_resource,
    list_resources,
    query_resources_from_table,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_request():
    """Create a mock Azure Functions HTTP request."""
    request = Mock(spec=func.HttpRequest)
    request.method = "GET"
    request.url = "http://localhost:7071/api/v1/resources"
    request.params = {}
    request.route_params = {}
    return request


@pytest.fixture
def mock_table_client():
    """Create a mock Azure Table client."""
    return Mock()


@pytest.fixture
def sample_resource_entities():
    """Sample resource entities from Table Storage."""
    return [
        {
            "PartitionKey": "resources",
            "RowKey": "resource-001",
            "resource_id": "resource-001",
            "resource_name": "test-vm",
            "resource_type": "Microsoft.Compute/virtualMachines",
            "scenario": "compute-01",
            "execution_id": "exec-123",
            "created_at": datetime(2025, 11, 25, 10, 0, 0, tzinfo=UTC),
            "status": "created",
            "tag_environment": "test",
            "tag_owner": "haymaker",
        },
        {
            "PartitionKey": "resources",
            "RowKey": "resource-002",
            "resource_id": "resource-002",
            "resource_name": "test-storage",
            "resource_type": "Microsoft.Storage/storageAccounts",
            "scenario": "storage-01",
            "execution_id": "exec-123",
            "created_at": datetime(2025, 11, 25, 10, 5, 0, tzinfo=UTC),
            "deleted_at": datetime(2025, 11, 25, 11, 0, 0, tzinfo=UTC),
            "status": "deleted",
        },
    ]


# ==============================================================================
# TESTS: query_resources_from_table
# ==============================================================================


@pytest.mark.asyncio
async def test_query_resources_from_table_no_filter(
    mock_table_client, sample_resource_entities
):
    """Test querying resources without filters."""
    mock_table_client.query_entities = Mock(return_value=sample_resource_entities)

    resources = await query_resources_from_table(mock_table_client)

    assert len(resources) == 2
    assert resources[0].id == "resource-001"
    assert resources[0].name == "test-vm"
    assert resources[0].status == "created"
    assert resources[1].id == "resource-002"
    assert resources[1].status == "deleted"

    # Verify query was called with no filter
    mock_table_client.query_entities.assert_called_once()
    call_kwargs = mock_table_client.query_entities.call_args[1]
    assert call_kwargs["query_filter"] is None


@pytest.mark.asyncio
async def test_query_resources_from_table_execution_id_filter(
    mock_table_client, sample_resource_entities
):
    """Test querying resources by execution_id."""
    mock_table_client.query_entities = Mock(return_value=sample_resource_entities)

    resources = await query_resources_from_table(
        mock_table_client, execution_id="exec-123"
    )

    assert len(resources) == 2

    # Verify filter was applied
    mock_table_client.query_entities.assert_called_once()
    call_kwargs = mock_table_client.query_entities.call_args[1]
    assert "execution_id eq 'exec-123'" in call_kwargs["query_filter"]


@pytest.mark.asyncio
async def test_query_resources_from_table_scenario_filter(
    mock_table_client, sample_resource_entities
):
    """Test querying resources by scenario."""
    compute_entities = [e for e in sample_resource_entities if e["scenario"] == "compute-01"]
    mock_table_client.query_entities = Mock(return_value=compute_entities)

    resources = await query_resources_from_table(mock_table_client, scenario="compute-01")

    assert len(resources) == 1
    assert resources[0].scenario == "compute-01"

    # Verify filter was applied
    call_kwargs = mock_table_client.query_entities.call_args[1]
    assert "scenario eq 'compute-01'" in call_kwargs["query_filter"]


@pytest.mark.asyncio
async def test_query_resources_from_table_status_filter(
    mock_table_client, sample_resource_entities
):
    """Test querying resources by status."""
    created_entities = [e for e in sample_resource_entities if e["status"] == "created"]
    mock_table_client.query_entities = Mock(return_value=created_entities)

    resources = await query_resources_from_table(mock_table_client, status="created")

    assert len(resources) == 1
    assert resources[0].status == "created"

    # Verify filter was applied
    call_kwargs = mock_table_client.query_entities.call_args[1]
    assert "status eq 'created'" in call_kwargs["query_filter"]


@pytest.mark.asyncio
async def test_query_resources_from_table_multiple_filters(
    mock_table_client, sample_resource_entities
):
    """Test querying resources with multiple filters combined."""
    mock_table_client.query_entities = Mock(return_value=[sample_resource_entities[0]])

    resources = await query_resources_from_table(
        mock_table_client, execution_id="exec-123", scenario="compute-01", status="created"
    )

    # Verify all filters were combined with 'and'
    call_kwargs = mock_table_client.query_entities.call_args[1]
    filter_str = call_kwargs["query_filter"]
    assert "execution_id eq 'exec-123'" in filter_str
    assert "scenario eq 'compute-01'" in filter_str
    assert "status eq 'created'" in filter_str
    assert " and " in filter_str


@pytest.mark.asyncio
async def test_query_resources_from_table_with_tags(mock_table_client, sample_resource_entities):
    """Test that resource tags are parsed correctly."""
    mock_table_client.query_entities = Mock(return_value=[sample_resource_entities[0]])

    resources = await query_resources_from_table(mock_table_client)

    assert len(resources) == 1
    assert resources[0].tags == {"environment": "test", "owner": "haymaker"}


@pytest.mark.asyncio
async def test_query_resources_from_table_with_limit(
    mock_table_client, sample_resource_entities
):
    """Test limit parameter restricts results."""
    mock_table_client.query_entities = Mock(return_value=sample_resource_entities)

    resources = await query_resources_from_table(mock_table_client, limit=1)

    assert len(resources) == 1


@pytest.mark.asyncio
async def test_query_resources_from_table_empty_results(mock_table_client):
    """Test handling empty result set."""
    mock_table_client.query_entities = Mock(return_value=[])

    resources = await query_resources_from_table(mock_table_client)

    assert len(resources) == 0


@pytest.mark.asyncio
async def test_query_resources_from_table_malformed_entity(mock_table_client):
    """Test handling of malformed entities (should skip and log warning)."""
    malformed_entities = [
        {"PartitionKey": "resources", "RowKey": "bad-resource"}  # Missing required fields
    ]
    mock_table_client.query_entities = Mock(return_value=malformed_entities)

    resources = await query_resources_from_table(mock_table_client)

    # Should skip malformed entity and return empty list
    assert len(resources) == 0


@pytest.mark.asyncio
async def test_query_resources_from_table_storage_error(mock_table_client):
    """Test error handling when Table Storage fails."""
    mock_table_client.query_entities = Mock(side_effect=Exception("Storage error"))

    with pytest.raises(Exception, match="Storage error"):
        await query_resources_from_table(mock_table_client)


# ==============================================================================
# TESTS: list_resources endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test_list_resources_happy_path(mock_request):
    """Test listing resources without filters."""
    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch(
            "azure_haymaker.orchestrator.resources_api.query_resources_from_table"
        ) as mock_query:
            mock_resources = [
                ResourceInfo(
                    id="resource-001",
                    name="test-vm",
                    type="Microsoft.Compute/virtualMachines",
                    scenario="compute-01",
                    execution_id="exec-123",
                    created_at=datetime(2025, 11, 25, 10, 0, 0, tzinfo=UTC),
                    status="created",
                )
            ]
            mock_query.return_value = mock_resources

            response = await list_resources(mock_request)

            assert response.status_code == 200
            assert response.mimetype == "application/json"


@pytest.mark.asyncio
async def test_list_resources_with_execution_id_filter(mock_request):
    """Test listing resources with execution_id filter."""
    mock_request.params = {"execution_id": "exec-123"}

    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch(
            "azure_haymaker.orchestrator.resources_api.query_resources_from_table"
        ) as mock_query:
            mock_query.return_value = []

            response = await list_resources(mock_request)

            # Verify query was called with execution_id filter
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs["execution_id"] == "exec-123"


@pytest.mark.asyncio
async def test_list_resources_with_scenario_filter(mock_request):
    """Test listing resources with scenario filter."""
    mock_request.params = {"scenario": "compute-01"}

    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch(
            "azure_haymaker.orchestrator.resources_api.query_resources_from_table"
        ) as mock_query:
            mock_query.return_value = []

            response = await list_resources(mock_request)

            # Verify query was called with scenario filter
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs["scenario"] == "compute-01"


@pytest.mark.asyncio
async def test_list_resources_with_status_filter(mock_request):
    """Test listing resources with status filter."""
    mock_request.params = {"status": "created"}

    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch(
            "azure_haymaker.orchestrator.resources_api.query_resources_from_table"
        ) as mock_query:
            mock_query.return_value = []

            response = await list_resources(mock_request)

            # Verify query was called with status filter
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs["status"] == "created"


@pytest.mark.asyncio
async def test_list_resources_with_limit(mock_request):
    """Test listing resources with limit parameter."""
    mock_request.params = {"limit": "50"}

    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch(
            "azure_haymaker.orchestrator.resources_api.query_resources_from_table"
        ) as mock_query:
            mock_query.return_value = []

            response = await list_resources(mock_request)

            # Verify query was called with limit
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs["limit"] == 50


@pytest.mark.asyncio
async def test_list_resources_invalid_limit(mock_request):
    """Test error handling for invalid limit parameter."""
    mock_request.params = {"limit": "invalid"}

    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        response = await list_resources(mock_request)

        assert response.status_code == 400
        body = json.loads(response.body)
        assert "error" in body


@pytest.mark.asyncio
async def test_list_resources_missing_config(mock_request):
    """Test error handling when storage not configured."""
    with patch.dict("os.environ", {}, clear=True):
        response = await list_resources(mock_request)

        assert response.status_code == 500
        body = json.loads(response.body)
        assert "Resources storage not configured" in body["error"]


@pytest.mark.asyncio
async def test_list_resources_storage_error(mock_request):
    """Test error handling when Table Storage fails."""
    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch(
            "azure_haymaker.orchestrator.resources_api.query_resources_from_table"
        ) as mock_query:
            mock_query.side_effect = Exception("Storage failure")

            response = await list_resources(mock_request)

            assert response.status_code == 500
            body = json.loads(response.body)
            assert "error" in body


# ==============================================================================
# TESTS: get_resource endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test_get_resource_happy_path(mock_request):
    """Test getting specific resource details."""
    mock_request.route_params = {"resource_id": "resource-001"}

    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch("azure_haymaker.orchestrator.resources_api.TableServiceClient") as mock_client:
            # Setup mock entity
            mock_entity = {
                "PartitionKey": "resources",
                "RowKey": "resource-001",
                "resource_id": "resource-001",
                "resource_name": "test-vm",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "scenario": "compute-01",
                "execution_id": "exec-123",
                "created_at": datetime(2025, 11, 25, 10, 0, 0, tzinfo=UTC),
                "status": "created",
                "tag_environment": "test",
            }

            mock_table = Mock()
            mock_table.get_entity = Mock(return_value=mock_entity)
            mock_service = Mock()
            mock_service.get_table_client = Mock(return_value=mock_table)
            mock_client.return_value = mock_service

            response = await get_resource(mock_request)

            assert response.status_code == 200
            body = json.loads(response.body)
            assert body["id"] == "resource-001"
            assert body["name"] == "test-vm"
            assert body["tags"]["environment"] == "test"


@pytest.mark.asyncio
async def test_get_resource_missing_resource_id(mock_request):
    """Test error handling when resource_id is missing."""
    mock_request.route_params = {}

    response = await get_resource(mock_request)

    assert response.status_code == 400
    body = json.loads(response.body)
    assert "resource_id is required" in body["error"]


@pytest.mark.asyncio
async def test_get_resource_not_found(mock_request):
    """Test error handling when resource doesn't exist."""
    mock_request.route_params = {"resource_id": "nonexistent"}

    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch("azure_haymaker.orchestrator.resources_api.TableServiceClient") as mock_client:
            mock_table = Mock()
            mock_table.get_entity = Mock(side_effect=Exception("Not found"))
            mock_service = Mock()
            mock_service.get_table_client = Mock(return_value=mock_table)
            mock_client.return_value = mock_service

            response = await get_resource(mock_request)

            assert response.status_code == 404
            body = json.loads(response.body)
            assert "Resource not found" in body["error"]


@pytest.mark.asyncio
async def test_get_resource_missing_config(mock_request):
    """Test error handling when storage not configured."""
    mock_request.route_params = {"resource_id": "resource-001"}

    with patch.dict("os.environ", {}, clear=True):
        response = await get_resource(mock_request)

        assert response.status_code == 500
        body = json.loads(response.body)
        assert "Resources storage not configured" in body["error"]


@pytest.mark.asyncio
async def test_get_resource_storage_error(mock_request):
    """Test error handling when Table Storage fails."""
    mock_request.route_params = {"resource_id": "resource-001"}

    with patch.dict(
        "os.environ",
        {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "RESOURCES_TABLE_NAME": "resources"},
    ):
        with patch("azure_haymaker.orchestrator.resources_api.TableServiceClient") as mock_client:
            mock_client.side_effect = Exception("Connection error")

            response = await get_resource(mock_request)

            assert response.status_code == 500
            body = json.loads(response.body)
            assert "error" in body
