"""
Unit tests for agents_api module.

Tests cover:
- GET /agents - List all agents with status filtering
- GET /agents/{agent_id}/logs - Get logs for an agent
- Query parameter validation
- Error handling (authentication, storage failures, invalid inputs)

Testing approach:
- Test behavior at API boundaries
- Mock Azure SDK clients (TableServiceClient, CosmosClient)
- Focus on happy path + error cases + boundary conditions
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import azure.functions as func
import pytest

from azure_haymaker.orchestrator.agents_api import (
    AgentInfo,
    LogEntry,
    get_agent_logs,
    list_agents,
    query_agents_from_table,
    query_logs_from_cosmosdb,
    sanitize_odata_value,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_request():
    """Create a mock Azure Functions HTTP request."""
    request = Mock(spec=func.HttpRequest)
    request.method = "GET"
    request.url = "http://localhost:7071/api/v1/agents"
    request.params = {}
    request.route_params = {}
    return request


@pytest.fixture
def mock_table_client():
    """Create a mock Azure Table client."""
    return Mock()


@pytest.fixture
def sample_agent_entities():
    """Sample agent entities from Table Storage."""
    return [
        {
            "PartitionKey": "agents",
            "RowKey": "agent-001",
            "agent_id": "agent-001",
            "scenario": "compute-01",
            "status": "running",
            "started_at": datetime(2025, 11, 25, 10, 0, 0, tzinfo=UTC),
            "progress": "50%",
        },
        {
            "PartitionKey": "agents",
            "RowKey": "agent-002",
            "agent_id": "agent-002",
            "scenario": "storage-01",
            "status": "completed",
            "started_at": datetime(2025, 11, 25, 9, 0, 0, tzinfo=UTC),
            "completed_at": datetime(2025, 11, 25, 9, 30, 0, tzinfo=UTC),
        },
    ]


@pytest.fixture
def sample_log_items():
    """Sample log items from Cosmos DB."""
    return [
        {
            "id": "log-001",
            "agent_id": "agent-001",
            "timestamp": "2025-11-25T10:00:00Z",
            "level": "INFO",
            "message": "Agent started",
            "source": "agent",
        },
        {
            "id": "log-002",
            "agent_id": "agent-001",
            "timestamp": "2025-11-25T10:05:00Z",
            "level": "INFO",
            "message": "Processing scenario",
            "source": "agent",
        },
    ]


# ==============================================================================
# TESTS: sanitize_odata_value
# ==============================================================================


def test_sanitize_odata_value_happy_path():
    """Test OData value sanitization with normal input."""
    result = sanitize_odata_value("running")
    assert result == "running"


def test_sanitize_odata_value_single_quote():
    """Test that single quotes are escaped for OData filters."""
    result = sanitize_odata_value("O'Brien")
    assert result == "O''Brien"


def test_sanitize_odata_value_multiple_quotes():
    """Test multiple single quotes are all escaped."""
    result = sanitize_odata_value("It's Bob's data")
    assert result == "It''s Bob''s data"


def test_sanitize_odata_value_empty_string():
    """Test empty string handling."""
    result = sanitize_odata_value("")
    assert result == ""


def test_sanitize_odata_value_numeric():
    """Test numeric values are converted to strings."""
    result = sanitize_odata_value(123)
    assert result == "123"


# ==============================================================================
# TESTS: query_agents_from_table
# ==============================================================================


@pytest.mark.asyncio
async def test_query_agents_from_table_no_filter(mock_table_client, sample_agent_entities):
    """Test querying agents without status filter."""
    mock_table_client.query_entities = Mock(return_value=sample_agent_entities)

    agents = await query_agents_from_table(mock_table_client)

    assert len(agents) == 2
    assert agents[0].agent_id == "agent-001"
    assert agents[0].status == "running"
    assert agents[1].agent_id == "agent-002"
    assert agents[1].status == "completed"

    # Verify query was called with no filter
    mock_table_client.query_entities.assert_called_once()
    call_kwargs = mock_table_client.query_entities.call_args[1]
    assert call_kwargs["query_filter"] is None


@pytest.mark.asyncio
async def test_query_agents_from_table_with_status_filter(
    mock_table_client, sample_agent_entities
):
    """Test querying agents with status filter."""
    # Return only running agents
    running_entities = [e for e in sample_agent_entities if e["status"] == "running"]
    mock_table_client.query_entities = Mock(return_value=running_entities)

    agents = await query_agents_from_table(mock_table_client, status_filter="running")

    assert len(agents) == 1
    assert agents[0].status == "running"

    # Verify filter was applied with sanitization
    mock_table_client.query_entities.assert_called_once()
    call_kwargs = mock_table_client.query_entities.call_args[1]
    assert "status eq 'running'" in call_kwargs["query_filter"]


@pytest.mark.asyncio
async def test_query_agents_from_table_with_limit(mock_table_client, sample_agent_entities):
    """Test limit parameter restricts results."""
    mock_table_client.query_entities = Mock(return_value=sample_agent_entities)

    agents = await query_agents_from_table(mock_table_client, limit=1)

    assert len(agents) == 1
    assert agents[0].agent_id == "agent-001"


@pytest.mark.asyncio
async def test_query_agents_from_table_empty_results(mock_table_client):
    """Test handling empty result set."""
    mock_table_client.query_entities = Mock(return_value=[])

    agents = await query_agents_from_table(mock_table_client)

    assert len(agents) == 0


@pytest.mark.asyncio
async def test_query_agents_from_table_malformed_entity(mock_table_client):
    """Test handling of malformed entities (uses default values for missing fields)."""
    malformed_entities = [
        {"PartitionKey": "agents", "RowKey": "bad-agent"}  # Missing required fields
    ]
    mock_table_client.query_entities = Mock(return_value=malformed_entities)

    agents = await query_agents_from_table(mock_table_client)

    # Implementation provides defaults for missing fields
    assert len(agents) == 1
    assert agents[0].agent_id == "bad-agent"  # Falls back to RowKey
    assert agents[0].scenario == "unknown"
    assert agents[0].status == "unknown"


@pytest.mark.asyncio
async def test_query_agents_from_table_storage_error(mock_table_client):
    """Test error handling when Table Storage fails."""
    mock_table_client.query_entities = Mock(side_effect=Exception("Storage error"))

    with pytest.raises(Exception, match="Storage error"):
        await query_agents_from_table(mock_table_client)


# ==============================================================================
# TESTS: query_logs_from_cosmosdb
# ==============================================================================


@pytest.mark.asyncio
async def test_query_logs_from_cosmosdb_happy_path(sample_log_items):
    """Test querying logs from Cosmos DB."""
    with patch.dict("os.environ", {"COSMOSDB_ENDPOINT": "https://test.cosmos.azure.com"}):
        with patch("azure_haymaker.orchestrator.agents_api.CosmosClient") as mock_cosmos:
            # Setup mock chain
            mock_container = Mock()
            mock_container.query_items = Mock(return_value=sample_log_items)
            mock_database = Mock()
            mock_database.get_container_client = Mock(return_value=mock_container)
            mock_client = Mock()
            mock_client.get_database_client = Mock(return_value=mock_database)
            mock_cosmos.return_value = mock_client

            logs = await query_logs_from_cosmosdb(agent_id="agent-001", tail=100)

            assert len(logs) == 2
            assert logs[0].agent_id == "agent-001"
            assert logs[0].message == "Agent started"
            assert logs[1].message == "Processing scenario"


@pytest.mark.asyncio
async def test_query_logs_from_cosmosdb_with_since_timestamp(sample_log_items):
    """Test querying logs with since timestamp filter."""
    with patch.dict("os.environ", {"COSMOSDB_ENDPOINT": "https://test.cosmos.azure.com"}):
        with patch("azure_haymaker.orchestrator.agents_api.CosmosClient") as mock_cosmos:
            mock_container = Mock()
            mock_container.query_items = Mock(return_value=[sample_log_items[1]])
            mock_database = Mock()
            mock_database.get_container_client = Mock(return_value=mock_container)
            mock_client = Mock()
            mock_client.get_database_client = Mock(return_value=mock_database)
            mock_cosmos.return_value = mock_client

            logs = await query_logs_from_cosmosdb(
                agent_id="agent-001", since_timestamp="2025-11-25T10:03:00Z"
            )

            assert len(logs) == 1
            assert logs[0].message == "Processing scenario"

            # Verify query uses since_timestamp parameter
            call_kwargs = mock_container.query_items.call_args[1]
            assert "since_timestamp" in str(call_kwargs.get("parameters", []))


@pytest.mark.asyncio
async def test_query_logs_from_cosmosdb_no_endpoint():
    """Test error handling when COSMOSDB_ENDPOINT not configured."""
    with patch.dict("os.environ", {}, clear=True):
        logs = await query_logs_from_cosmosdb(agent_id="agent-001")

        # Should return empty list when endpoint not configured
        assert len(logs) == 0


@pytest.mark.asyncio
async def test_query_logs_from_cosmosdb_cosmos_error():
    """Test error handling when Cosmos DB query fails."""
    with patch.dict("os.environ", {"COSMOSDB_ENDPOINT": "https://test.cosmos.azure.com"}):
        with patch("azure_haymaker.orchestrator.agents_api.CosmosClient") as mock_cosmos:
            mock_cosmos.side_effect = Exception("Cosmos error")

            with pytest.raises(Exception, match="Cosmos error"):
                await query_logs_from_cosmosdb(agent_id="agent-001")


# ==============================================================================
# TESTS: list_agents endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test_list_agents_happy_path(mock_request, sample_agent_entities):
    """Test listing agents without filters."""
    with patch.dict(
        "os.environ", {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "AGENTS_TABLE_NAME": "agents"}
    ):
        with patch(
            "azure_haymaker.orchestrator.agents_api.query_agents_from_table"
        ) as mock_query:
            # Setup mock agents
            mock_agents = [
                AgentInfo(
                    agent_id="agent-001",
                    scenario="compute-01",
                    status="running",
                    started_at=datetime(2025, 11, 25, 10, 0, 0, tzinfo=UTC),
                    progress="50%",
                )
            ]
            mock_query.return_value = mock_agents

            response = await list_agents(mock_request)

            assert response.status_code == 200
            assert response.mimetype == "application/json"


@pytest.mark.asyncio
async def test_list_agents_with_status_filter(mock_request):
    """Test listing agents with status filter."""
    mock_request.params = {"status": "running"}

    with patch.dict(
        "os.environ", {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "AGENTS_TABLE_NAME": "agents"}
    ):
        with patch(
            "azure_haymaker.orchestrator.agents_api.query_agents_from_table"
        ) as mock_query:
            mock_query.return_value = []

            response = await list_agents(mock_request)

            # Verify query was called with status filter
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs["status_filter"] == "running"


@pytest.mark.asyncio
async def test_list_agents_with_limit(mock_request):
    """Test listing agents with limit parameter."""
    mock_request.params = {"limit": "50"}

    with patch.dict(
        "os.environ", {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "AGENTS_TABLE_NAME": "agents"}
    ):
        with patch(
            "azure_haymaker.orchestrator.agents_api.query_agents_from_table"
        ) as mock_query:
            mock_query.return_value = []

            response = await list_agents(mock_request)

            # Verify query was called with limit
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs["limit"] == 50


@pytest.mark.asyncio
async def test_list_agents_invalid_limit(mock_request):
    """Test error handling for invalid limit parameter."""
    mock_request.params = {"limit": "invalid"}

    with patch.dict(
        "os.environ", {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "AGENTS_TABLE_NAME": "agents"}
    ):
        response = await list_agents(mock_request)

        assert response.status_code == 400
        body = json.loads(response.get_body())
        assert "error" in body
        assert "INVALID_PARAMETER" in body["error"]["code"]


@pytest.mark.asyncio
async def test_list_agents_missing_config(mock_request):
    """Test error handling when storage not configured."""
    with patch.dict("os.environ", {}, clear=True):
        response = await list_agents(mock_request)

        assert response.status_code == 500
        body = json.loads(response.get_body())
        assert "Agents storage not configured" in body["error"]


@pytest.mark.asyncio
async def test_list_agents_storage_error(mock_request):
    """Test error handling when Table Storage fails."""
    with patch.dict(
        "os.environ", {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount", "AGENTS_TABLE_NAME": "agents"}
    ):
        with patch(
            "azure_haymaker.orchestrator.agents_api.query_agents_from_table"
        ) as mock_query:
            mock_query.side_effect = Exception("Storage failure")

            response = await list_agents(mock_request)

            assert response.status_code == 500
            body = json.loads(response.get_body())
            assert "error" in body


# ==============================================================================
# TESTS: get_agent_logs endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test_get_agent_logs_happy_path(mock_request):
    """Test getting agent logs."""
    mock_request.route_params = {"agent_id": "agent-001"}
    mock_request.params = {}

    with patch(
        "azure_haymaker.orchestrator.agents_api.query_logs_from_cosmosdb"
    ) as mock_query:
        mock_logs = [
            LogEntry(
                timestamp="2025-11-25T10:00:00Z",
                level="INFO",
                message="Test log",
                agent_id="agent-001",
            )
        ]
        mock_query.return_value = mock_logs

        response = await get_agent_logs(mock_request)

        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "logs" in body
        assert len(body["logs"]) == 1
        assert body["logs"][0]["message"] == "Test log"


@pytest.mark.asyncio
async def test_get_agent_logs_missing_agent_id(mock_request):
    """Test error handling when agent_id is missing."""
    mock_request.route_params = {}

    response = await get_agent_logs(mock_request)

    assert response.status_code == 400
    body = json.loads(response.get_body())
    assert "agent_id is required" in body["error"]


@pytest.mark.asyncio
async def test_get_agent_logs_with_tail(mock_request):
    """Test getting agent logs with tail parameter."""
    mock_request.route_params = {"agent_id": "agent-001"}
    mock_request.params = {"tail": "50"}

    with patch(
        "azure_haymaker.orchestrator.agents_api.query_logs_from_cosmosdb"
    ) as mock_query:
        mock_query.return_value = []

        response = await get_agent_logs(mock_request)

        # Verify query was called with tail parameter
        call_kwargs = mock_query.call_args[1]
        assert call_kwargs["tail"] == 50


@pytest.mark.asyncio
async def test_get_agent_logs_with_since(mock_request):
    """Test getting agent logs with since parameter."""
    mock_request.route_params = {"agent_id": "agent-001"}
    mock_request.params = {"since": "2025-11-25T10:00:00Z"}

    with patch(
        "azure_haymaker.orchestrator.agents_api.query_logs_from_cosmosdb"
    ) as mock_query:
        mock_query.return_value = []

        response = await get_agent_logs(mock_request)

        # Verify query was called with since parameter
        call_kwargs = mock_query.call_args[1]
        assert call_kwargs["since_timestamp"] == "2025-11-25T10:00:00Z"


@pytest.mark.asyncio
async def test_get_agent_logs_invalid_tail(mock_request):
    """Test error handling for invalid tail parameter."""
    mock_request.route_params = {"agent_id": "agent-001"}
    mock_request.params = {"tail": "invalid"}

    response = await get_agent_logs(mock_request)

    assert response.status_code == 400
    body = json.loads(response.get_body())
    assert "error" in body


@pytest.mark.asyncio
async def test_get_agent_logs_cosmos_error(mock_request):
    """Test error handling when Cosmos DB fails."""
    mock_request.route_params = {"agent_id": "agent-001"}
    mock_request.params = {}

    with patch(
        "azure_haymaker.orchestrator.agents_api.query_logs_from_cosmosdb"
    ) as mock_query:
        mock_query.side_effect = Exception("Cosmos failure")

        response = await get_agent_logs(mock_request)

        assert response.status_code == 500
        body = json.loads(response.get_body())
        assert "error" in body
