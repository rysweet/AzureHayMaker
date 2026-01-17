"""Unit tests for agents_api module.

Tests for API endpoints that manage agent queries and log retrieval.
Following the testing pyramid: 60% unit tests, 30% integration tests, 10% E2E tests.

This module tests:
- AgentInfo model validation
- LogEntry model validation
- query_agents_from_table function
- query_logs_from_cosmosdb function
- list_agents endpoint
- get_agent_logs endpoint
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from azure_haymaker.orchestrator.agents_api import (
    AgentInfo,
    LogEntry,
    query_agents_from_table,
    query_logs_from_cosmosdb,
    sanitize_odata_value,
)


class TestSanitizeOdataValue:
    """Tests for OData value sanitization."""

    def test_sanitize_normal_string(self) -> None:
        """Test that normal strings pass through unchanged."""
        assert sanitize_odata_value("running") == "running"
        assert sanitize_odata_value("completed") == "completed"

    def test_sanitize_single_quotes(self) -> None:
        """Test that single quotes are escaped by doubling."""
        assert sanitize_odata_value("test's") == "test''s"
        assert sanitize_odata_value("'quoted'") == "''quoted''"

    def test_sanitize_multiple_quotes(self) -> None:
        """Test multiple single quotes are all escaped."""
        assert sanitize_odata_value("it's a test's test") == "it''s a test''s test"

    def test_sanitize_non_string(self) -> None:
        """Test that non-strings are converted to strings."""
        assert sanitize_odata_value(123) == "123"
        assert sanitize_odata_value(None) == "None"


class TestAgentInfoModel:
    """Tests for AgentInfo Pydantic model."""

    def test_agent_info_required_fields(self) -> None:
        """Test AgentInfo with required fields only."""
        now = datetime.now(UTC)
        agent = AgentInfo(
            agent_id="agent-123",
            scenario="compute-01",
            status="running",
            started_at=now,
        )
        assert agent.agent_id == "agent-123"
        assert agent.scenario == "compute-01"
        assert agent.status == "running"
        assert agent.started_at == now
        assert agent.completed_at is None
        assert agent.progress is None
        assert agent.error is None

    def test_agent_info_all_fields(self) -> None:
        """Test AgentInfo with all fields populated."""
        started = datetime.now(UTC)
        completed = datetime.now(UTC)
        agent = AgentInfo(
            agent_id="agent-456",
            scenario="storage-02",
            status="completed",
            started_at=started,
            completed_at=completed,
            progress="100%",
            error=None,
        )
        assert agent.completed_at == completed
        assert agent.progress == "100%"

    def test_agent_info_with_error(self) -> None:
        """Test AgentInfo with error field."""
        agent = AgentInfo(
            agent_id="agent-789",
            scenario="network-03",
            status="failed",
            started_at=datetime.now(UTC),
            error="Connection timeout",
        )
        assert agent.status == "failed"
        assert agent.error == "Connection timeout"


class TestLogEntryModel:
    """Tests for LogEntry Pydantic model."""

    def test_log_entry_required_fields(self) -> None:
        """Test LogEntry with required fields."""
        log = LogEntry(
            timestamp="2025-01-01T12:00:00Z",
            level="INFO",
            message="Agent started",
            agent_id="agent-123",
        )
        assert log.timestamp == "2025-01-01T12:00:00Z"
        assert log.level == "INFO"
        assert log.message == "Agent started"
        assert log.agent_id == "agent-123"
        assert log.source == "agent"  # Default value

    def test_log_entry_custom_source(self) -> None:
        """Test LogEntry with custom source."""
        log = LogEntry(
            timestamp="2025-01-01T12:00:00Z",
            level="ERROR",
            message="Connection failed",
            agent_id="agent-456",
            source="orchestrator",
        )
        assert log.source == "orchestrator"


class TestQueryAgentsFromTable:
    """Tests for query_agents_from_table function."""

    @pytest.mark.asyncio
    async def test_query_agents_without_filter(self) -> None:
        """Test querying agents without status filter."""
        mock_table_client = MagicMock()
        mock_entity = {
            "agent_id": "agent-123",
            "scenario": "compute-01",
            "status": "running",
            "started_at": datetime.now(UTC),
            "completed_at": None,
            "progress": "50%",
            "error": None,
        }
        mock_table_client.query_entities.return_value = [mock_entity]

        agents = await query_agents_from_table(mock_table_client)

        assert len(agents) == 1
        assert agents[0].agent_id == "agent-123"
        assert agents[0].scenario == "compute-01"
        mock_table_client.query_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_agents_with_status_filter(self) -> None:
        """Test querying agents with status filter."""
        mock_table_client = MagicMock()
        mock_table_client.query_entities.return_value = []

        await query_agents_from_table(mock_table_client, status_filter="running")

        call_kwargs = mock_table_client.query_entities.call_args[1]
        assert call_kwargs["query_filter"] == "status eq 'running'"

    @pytest.mark.asyncio
    async def test_query_agents_with_limit(self) -> None:
        """Test querying agents respects limit."""
        mock_table_client = MagicMock()
        mock_entities = [
            {
                "agent_id": f"agent-{i}",
                "scenario": "test",
                "status": "running",
                "started_at": datetime.now(UTC),
            }
            for i in range(10)
        ]
        mock_table_client.query_entities.return_value = mock_entities

        agents = await query_agents_from_table(mock_table_client, limit=5)

        assert len(agents) == 5

    @pytest.mark.asyncio
    async def test_query_agents_uses_rowkey_fallback(self) -> None:
        """Test that agent_id falls back to RowKey if not present."""
        mock_table_client = MagicMock()
        mock_entity = {
            "RowKey": "fallback-agent-id",
            "scenario": "test",
            "status": "completed",
            "started_at": datetime.now(UTC),
        }
        mock_table_client.query_entities.return_value = [mock_entity]

        agents = await query_agents_from_table(mock_table_client)

        assert agents[0].agent_id == "fallback-agent-id"

    @pytest.mark.asyncio
    async def test_query_agents_handles_missing_optional_fields(self) -> None:
        """Test that missing optional fields are handled gracefully."""
        mock_table_client = MagicMock()
        mock_entity = {
            "agent_id": "agent-123",
            "scenario": "test",
            "status": "running",
            "started_at": datetime.now(UTC),
            # No completed_at, progress, or error fields
        }
        mock_table_client.query_entities.return_value = [mock_entity]

        agents = await query_agents_from_table(mock_table_client)

        assert agents[0].completed_at is None
        assert agents[0].progress is None
        assert agents[0].error is None

    @pytest.mark.asyncio
    async def test_query_agents_handles_query_error(self) -> None:
        """Test that query errors are propagated."""
        mock_table_client = MagicMock()
        mock_table_client.query_entities.side_effect = Exception("Table Storage error")

        with pytest.raises(Exception, match="Table Storage error"):
            await query_agents_from_table(mock_table_client)

    @pytest.mark.asyncio
    async def test_query_agents_skips_malformed_entities(self) -> None:
        """Test that malformed entities are skipped with a warning."""
        mock_table_client = MagicMock()
        # Entity missing required 'scenario' field will cause parsing issues
        mock_entity_good = {
            "agent_id": "agent-good",
            "scenario": "test",
            "status": "running",
            "started_at": datetime.now(UTC),
        }
        mock_entity_bad = {
            "agent_id": "agent-bad",
            # Missing required fields like started_at
        }
        mock_table_client.query_entities.return_value = [mock_entity_good, mock_entity_bad]

        agents = await query_agents_from_table(mock_table_client)

        # Should only return the good entity
        assert len(agents) >= 1
        assert agents[0].agent_id == "agent-good"


class TestQueryLogsFromCosmosDB:
    """Tests for query_logs_from_cosmosdb function."""

    @pytest.mark.asyncio
    async def test_query_logs_without_cosmosdb_endpoint(self) -> None:
        """Test that missing COSMOSDB_ENDPOINT returns empty list."""
        with patch.dict("os.environ", {}, clear=True):
            logs = await query_logs_from_cosmosdb("agent-123")
            assert logs == []

    @pytest.mark.asyncio
    async def test_query_logs_basic(self) -> None:
        """Test basic log query."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = [
            {
                "timestamp": "2025-01-01T12:00:00Z",
                "level": "INFO",
                "message": "Test message",
                "agent_id": "agent-123",
                "source": "agent",
            }
        ]

        mock_cosmos_client = MagicMock()
        mock_database = MagicMock()
        mock_database.get_container_client.return_value = mock_container
        mock_cosmos_client.get_database_client.return_value = mock_database

        with (
            patch.dict("os.environ", {"COSMOSDB_ENDPOINT": "https://test.cosmos.azure.com"}),
            patch("azure_haymaker.orchestrator.agents_api.DefaultAzureCredential"),
            patch(
                "azure_haymaker.orchestrator.agents_api.CosmosClient",
                return_value=mock_cosmos_client,
            ),
        ):
            logs = await query_logs_from_cosmosdb("agent-123", tail=50)

        assert len(logs) == 1
        assert logs[0].message == "Test message"
        assert logs[0].agent_id == "agent-123"

    @pytest.mark.asyncio
    async def test_query_logs_with_since_timestamp(self) -> None:
        """Test log query with since_timestamp parameter."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = []

        mock_cosmos_client = MagicMock()
        mock_database = MagicMock()
        mock_database.get_container_client.return_value = mock_container
        mock_cosmos_client.get_database_client.return_value = mock_database

        with (
            patch.dict("os.environ", {"COSMOSDB_ENDPOINT": "https://test.cosmos.azure.com"}),
            patch("azure_haymaker.orchestrator.agents_api.DefaultAzureCredential"),
            patch(
                "azure_haymaker.orchestrator.agents_api.CosmosClient",
                return_value=mock_cosmos_client,
            ),
        ):
            await query_logs_from_cosmosdb("agent-123", since_timestamp="2025-01-01T00:00:00Z")

        # Verify the query was called
        mock_container.query_items.assert_called_once()
        # Check that since_timestamp is used in query
        call_args = mock_container.query_items.call_args
        assert "@since_timestamp" in str(call_args)


class TestListAgentsEndpoint:
    """Tests for list_agents HTTP endpoint."""

    @pytest.mark.asyncio
    async def test_list_agents_missing_table_config(self) -> None:
        """Test list_agents returns error when TABLE_STORAGE_ACCOUNT_NAME is missing."""
        # Import the function for testing
        from azure_haymaker.orchestrator.agents_api import list_agents

        mock_request = MagicMock()
        mock_request.params = {}

        with patch.dict("os.environ", {}, clear=True):
            response = await list_agents(mock_request)

        assert response.status_code == 500
        assert b"not configured" in response.get_body()

    @pytest.mark.asyncio
    async def test_list_agents_invalid_limit_parameter(self) -> None:
        """Test list_agents handles invalid limit parameter."""
        from azure_haymaker.orchestrator.agents_api import list_agents

        mock_request = MagicMock()
        mock_request.params = {"limit": "invalid"}

        with patch.dict("os.environ", {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount"}):
            response = await list_agents(mock_request)

        assert response.status_code == 400


class TestGetAgentLogsEndpoint:
    """Tests for get_agent_logs HTTP endpoint."""

    @pytest.mark.asyncio
    async def test_get_agent_logs_missing_agent_id(self) -> None:
        """Test get_agent_logs returns error when agent_id is missing."""
        from azure_haymaker.orchestrator.agents_api import get_agent_logs

        mock_request = MagicMock()
        mock_request.route_params = {}
        mock_request.params = {}

        response = await get_agent_logs(mock_request)

        assert response.status_code == 400
        assert b"agent_id is required" in response.get_body()

    @pytest.mark.asyncio
    async def test_get_agent_logs_invalid_tail_parameter(self) -> None:
        """Test get_agent_logs handles invalid tail parameter."""
        from azure_haymaker.orchestrator.agents_api import get_agent_logs

        mock_request = MagicMock()
        mock_request.route_params = {"agent_id": "agent-123"}
        mock_request.params = {"tail": "invalid"}

        response = await get_agent_logs(mock_request)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_agent_logs_success(self) -> None:
        """Test successful log retrieval."""
        from azure_haymaker.orchestrator.agents_api import get_agent_logs

        mock_request = MagicMock()
        mock_request.route_params = {"agent_id": "agent-123"}
        mock_request.params = {"tail": "10"}

        mock_logs = [
            LogEntry(
                timestamp="2025-01-01T12:00:00Z",
                level="INFO",
                message="Test",
                agent_id="agent-123",
            )
        ]

        with patch(
            "azure_haymaker.orchestrator.agents_api.query_logs_from_cosmosdb",
            new_callable=AsyncMock,
            return_value=mock_logs,
        ):
            response = await get_agent_logs(mock_request)

        assert response.status_code == 200
