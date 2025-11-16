"""Integration tests for on-demand execution feature.

These tests verify the full execution flow:
1. Submit execution request via API
2. Verify execution record created
3. Verify message queued to Service Bus
4. Verify status can be queried
5. Verify rate limiting works
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import azure.functions as func
import pytest

from azure_haymaker.models.execution import OnDemandExecutionStatus
from azure_haymaker.orchestrator.execution_tracker import ExecutionTracker
from azure_haymaker.orchestrator.rate_limiter import RateLimiter


@pytest.fixture
def mock_config():
    """Create mock configuration for integration tests."""
    return MagicMock(
        table_storage=MagicMock(account_url="https://test.table.core.windows.net"),
        service_bus_namespace="test-servicebus",
        target_subscription_id="test-subscription",
        key_vault_url="https://test-kv.vault.azure.net",
        storage=MagicMock(account_url="https://test.blob.core.windows.net"),
    )


@pytest.mark.asyncio
@pytest.mark.integration
@patch("azure_haymaker.orchestrator.execute_api.load_config")
@patch("azure_haymaker.orchestrator.execute_api.DefaultAzureCredential")
async def test_full_execution_flow(mock_credential, mock_load_config, mock_config):
    """Test full on-demand execution flow end-to-end."""
    mock_load_config.return_value = mock_config

    # Mock Table Storage
    mock_table_entities = {}

    async def mock_create_entity(entity):
        key = (entity["PartitionKey"], entity["RowKey"])
        mock_table_entities[key] = entity

    async def mock_get_entity(partition_key, row_key):
        key = (partition_key, row_key)
        if key in mock_table_entities:
            return mock_table_entities[key]
        from azure.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("Not found")

    async def mock_query_entities(query):
        for _key, entity in mock_table_entities.items():
            if query and "PartitionKey" in query:
                partition = query.split("'")[1]
                if entity["PartitionKey"] == partition:
                    yield entity
            else:
                yield entity

    async def mock_upsert_entity(entity, mode):
        key = (entity["PartitionKey"], entity["RowKey"])
        mock_table_entities[key] = entity

    mock_table_client = MagicMock()
    mock_table_client.create_entity = mock_create_entity
    mock_table_client.get_entity = mock_get_entity
    mock_table_client.query_entities = mock_query_entities
    mock_table_client.upsert_entity = mock_upsert_entity

    # Mock Service Bus
    mock_messages = []

    async def mock_send_messages(message):
        mock_messages.append(message)

    mock_sender = MagicMock()
    mock_sender.send_messages = mock_send_messages
    mock_sender.__aenter__ = AsyncMock(return_value=mock_sender)
    mock_sender.__aexit__ = AsyncMock()

    mock_sb_client = MagicMock()
    mock_sb_client.get_queue_sender.return_value = mock_sender
    mock_sb_client.__aenter__ = AsyncMock(return_value=mock_sb_client)
    mock_sb_client.__aexit__ = AsyncMock()

    with (
        patch(
            "azure_haymaker.orchestrator.execute_api.TableClient", return_value=mock_table_client
        ),
        patch(
            "azure_haymaker.orchestrator.execute_api.ServiceBusClient",
            return_value=mock_sb_client,
        ),
        patch(
            "azure_haymaker.orchestrator.execute_api.validate_scenarios",
            return_value=(True, None),
        ),
    ):
        # ========================================================================
        # STEP 1: Submit execution request
        # ========================================================================
        from azure_haymaker.orchestrator.execute_api import execute_scenario

        req = MagicMock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "scenarios": ["compute-01"],
            "duration_hours": 2,
            "tags": {"requester": "test@example.com"},
        }

        response = await execute_scenario(req)

        # Verify response
        assert response.status_code == 202
        body = json.loads(response.get_body())
        execution_id = body["execution_id"]
        assert execution_id.startswith("exec-")
        assert body["status"] == "queued"

        # ========================================================================
        # STEP 2: Verify execution record created
        # ========================================================================
        tracker = ExecutionTracker(mock_table_client)

        status = await tracker.get_execution_status(execution_id)
        assert status.execution_id == execution_id
        assert status.status == OnDemandExecutionStatus.QUEUED
        assert status.scenarios == ["compute-01"]

        # ========================================================================
        # STEP 3: Verify message queued to Service Bus
        # ========================================================================
        assert len(mock_messages) == 1
        # ServiceBusMessage.body is a generator that yields bytes
        message_bytes = b"".join(mock_messages[0].body)
        message_body = json.loads(message_bytes.decode())
        assert message_body["execution_id"] == execution_id
        assert message_body["scenarios"] == ["compute-01"]

        # ========================================================================
        # STEP 4: Simulate status update to RUNNING
        # ========================================================================
        await tracker.update_status(
            execution_id=execution_id,
            status=OnDemandExecutionStatus.RUNNING,
            container_ids=["container-01"],
        )

        status = await tracker.get_execution_status(execution_id)
        assert status.status == OnDemandExecutionStatus.RUNNING
        assert status.container_ids == ["container-01"]

        # ========================================================================
        # STEP 5: Query status via API
        # ========================================================================
        from azure_haymaker.orchestrator.execute_api import get_execution_status

        with patch(
            "azure_haymaker.orchestrator.execute_api.TableClient",
            return_value=mock_table_client,
        ):
            status_req = MagicMock(spec=func.HttpRequest)
            status_req.route_params = {"execution_id": execution_id}

            status_response = await get_execution_status(status_req)

            assert status_response.status_code == 200
            status_body = json.loads(status_response.get_body())
            assert status_body["execution_id"] == execution_id
            assert status_body["status"] == "running"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_rate_limiting_integration():
    """Test rate limiting works across multiple requests."""
    mock_table_entities = {}

    async def mock_create_entity(entity):
        key = (entity["PartitionKey"], entity["RowKey"])
        mock_table_entities[key] = entity

    async def mock_get_entity(partition_key, row_key):
        key = (partition_key, row_key)
        if key in mock_table_entities:
            return mock_table_entities[key]
        from azure.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("Not found")

    async def mock_upsert_entity(entity, mode):
        key = (entity["PartitionKey"], entity["RowKey"])
        mock_table_entities[key] = entity

    mock_table_client = MagicMock()
    mock_table_client.create_entity = mock_create_entity
    mock_table_client.get_entity = mock_get_entity
    mock_table_client.upsert_entity = mock_upsert_entity

    limiter = RateLimiter(mock_table_client)

    # First request should succeed
    result1 = await limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=2,  # Low limit for testing
        window_seconds=3600,
    )
    assert result1.allowed is True
    assert result1.current_count == 1

    # Second request should succeed
    result2 = await limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=2,
        window_seconds=3600,
    )
    assert result2.allowed is True
    assert result2.current_count == 2

    # Third request should be blocked
    result3 = await limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=2,
        window_seconds=3600,
    )
    assert result3.allowed is False
    assert result3.retry_after > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_execution_tracker_integration():
    """Test execution tracker with full lifecycle."""
    mock_table_entities = {}

    async def mock_create_entity(entity):
        key = (entity["PartitionKey"], entity["RowKey"])
        mock_table_entities[key] = entity

    async def mock_query_entities(query):
        for _key, entity in mock_table_entities.items():
            if query and "PartitionKey" in query:
                partition = query.split("'")[1]
                if entity["PartitionKey"] == partition:
                    yield entity
            else:
                yield entity

    mock_table_client = MagicMock()
    mock_table_client.create_entity = mock_create_entity
    mock_table_client.query_entities = mock_query_entities

    tracker = ExecutionTracker(mock_table_client)

    # Create execution
    execution_id = await tracker.create_execution(
        scenarios=["compute-01", "networking-01"],
        duration_hours=2,
        tags={"requester": "test@example.com"},
    )

    # Get status - should be QUEUED
    status = await tracker.get_execution_status(execution_id)
    assert status.status == OnDemandExecutionStatus.QUEUED

    # Update to RUNNING
    await tracker.update_status(
        execution_id=execution_id,
        status=OnDemandExecutionStatus.RUNNING,
        container_ids=["container-01", "container-02"],
    )

    status = await tracker.get_execution_status(execution_id)
    assert status.status == OnDemandExecutionStatus.RUNNING
    assert len(status.container_ids) == 2

    # Update to COMPLETED
    await tracker.update_status(
        execution_id=execution_id,
        status=OnDemandExecutionStatus.COMPLETED,
        resources_created=25,
        report_url="https://storage/report.json",
    )

    status = await tracker.get_execution_status(execution_id)
    assert status.status == OnDemandExecutionStatus.COMPLETED
    assert status.resources_created == 25
    assert status.report_url == "https://storage/report.json"


@pytest.mark.asyncio
@pytest.mark.integration
@patch("azure_haymaker.orchestrator.execute_api.load_config")
@patch("azure_haymaker.orchestrator.execute_api.DefaultAzureCredential")
async def test_scenario_validation_integration(mock_credential, mock_load_config, mock_config):
    """Test that invalid scenarios are rejected."""
    mock_load_config.return_value = mock_config

    with patch(
        "azure_haymaker.orchestrator.execute_api.validate_scenarios",
        return_value=(False, "Scenarios not found: invalid-scenario"),
    ):
        from azure_haymaker.orchestrator.execute_api import execute_scenario

        req = MagicMock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "scenarios": ["invalid-scenario"],
            "duration_hours": 2,
        }

        response = await execute_scenario(req)

        assert response.status_code == 404
        body = json.loads(response.get_body())
        assert body["error"]["code"] == "SCENARIO_NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multiple_executions_tracking():
    """Test tracking multiple concurrent executions."""
    mock_table_entities = {}

    async def mock_create_entity(entity):
        key = (entity["PartitionKey"], entity["RowKey"])
        mock_table_entities[key] = entity

    async def mock_query_entities(*args, **kwargs):
        # Accept query_filter kwarg (can be None, empty string, or filter expression)
        # args may include 'self' when called as bound method
        for _key, entity in mock_table_entities.items():
            yield entity

    mock_table_client = MagicMock()
    mock_table_client.create_entity = AsyncMock(side_effect=mock_create_entity)
    # query_entities needs to return the async generator when called
    mock_table_client.query_entities = MagicMock(side_effect=mock_query_entities)

    tracker = ExecutionTracker(mock_table_client)

    # Create multiple executions
    exec_ids = []
    for i in range(3):
        exec_id = await tracker.create_execution(
            scenarios=[f"scenario-{i}"],
            duration_hours=2,
        )
        exec_ids.append(exec_id)

    # List all executions
    executions = await tracker.list_executions(limit=10)

    assert len(executions) == 3
    exec_id_set = {e.execution_id for e in executions}
    for exec_id in exec_ids:
        assert exec_id in exec_id_set
