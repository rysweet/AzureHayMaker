"""Unit tests for execute API module."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import azure.functions as func
import pytest

from azure_haymaker.models.execution import OnDemandExecutionStatus


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return MagicMock(
        table_storage=MagicMock(account_url="https://test.table.core.windows.net"),
        service_bus_namespace="test-servicebus",
    )


@pytest.fixture
def mock_request_factory():
    """Factory for creating mock HTTP requests."""

    def create_request(method="POST", body=None, route_params=None):
        req = MagicMock(spec=func.HttpRequest)
        req.method = method
        req.route_params = route_params or {}

        if body:
            req.get_json.return_value = body
        else:
            req.get_json.side_effect = ValueError("No JSON")

        return req

    return create_request


@pytest.mark.asyncio
@patch("azure_haymaker.orchestrator.execute_api.load_config")
@patch("azure_haymaker.orchestrator.execute_api.DefaultAzureCredential")
@patch("azure_haymaker.orchestrator.execute_api.TableClient")
@patch("azure_haymaker.orchestrator.execute_api.ServiceBusClient")
@patch("azure_haymaker.orchestrator.execute_api.validate_scenarios")
async def test_execute_scenario_success(
    mock_validate,
    mock_sb_client,
    mock_table_client,
    mock_credential,
    mock_load_config,
    mock_request_factory,
    mock_config,
):
    """Test successful execution request."""
    # Setup mocks
    mock_load_config.return_value = mock_config
    mock_validate.return_value = (True, None)

    # Mock rate limiter
    mock_limiter = AsyncMock()
    mock_limiter.check_multiple_limits.return_value = MagicMock(
        allowed=True,
        retry_after=0,
    )

    # Mock execution tracker
    mock_tracker = AsyncMock()
    mock_tracker.create_execution.return_value = "exec-20251115-abc123"

    # Mock Service Bus
    mock_sender = AsyncMock()
    mock_sb_instance = MagicMock()
    mock_sb_instance.get_queue_sender.return_value = mock_sender
    mock_sb_client.return_value = mock_sb_instance

    with (
        patch("azure_haymaker.orchestrator.execute_api.RateLimiter", return_value=mock_limiter),
        patch(
            "azure_haymaker.orchestrator.execute_api.ExecutionTracker", return_value=mock_tracker
        ),
    ):
        from azure_haymaker.orchestrator.execute_api import execute_scenario

        req = mock_request_factory(
            body={
                "scenarios": ["compute-01", "networking-01"],
                "duration_hours": 2,
                "tags": {"requester": "admin"},
            }
        )

        response = await execute_scenario(req)

        assert response.status_code == 202
        body = json.loads(response.get_body())
        assert body["execution_id"] == "exec-20251115-abc123"
        assert body["status"] == "queued"
        assert len(body["scenarios"]) == 2


@pytest.mark.asyncio
@patch("azure_haymaker.orchestrator.execute_api.load_config")
async def test_execute_scenario_invalid_json(mock_load_config, mock_request_factory):
    """Test execution request with invalid JSON."""
    from azure_haymaker.orchestrator.execute_api import execute_scenario

    req = mock_request_factory()  # No body

    response = await execute_scenario(req)

    assert response.status_code == 400
    body = json.loads(response.get_body())
    assert body["error"]["code"] == "INVALID_JSON"


@pytest.mark.asyncio
@patch("azure_haymaker.orchestrator.execute_api.load_config")
async def test_execute_scenario_invalid_request(mock_load_config, mock_request_factory):
    """Test execution request with invalid data."""
    from azure_haymaker.orchestrator.execute_api import execute_scenario

    req = mock_request_factory(
        body={
            "scenarios": [],  # Empty list (invalid)
            "duration_hours": -1,  # Invalid
        }
    )

    response = await execute_scenario(req)

    assert response.status_code == 400
    body = json.loads(response.get_body())
    assert body["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
@patch("azure_haymaker.orchestrator.execute_api.load_config")
@patch("azure_haymaker.orchestrator.execute_api.validate_scenarios")
async def test_execute_scenario_not_found(mock_validate, mock_load_config, mock_request_factory):
    """Test execution request with non-existent scenario."""
    mock_validate.return_value = (False, "Scenarios not found: invalid-scenario")

    from azure_haymaker.orchestrator.execute_api import execute_scenario

    req = mock_request_factory(
        body={
            "scenarios": ["invalid-scenario"],
            "duration_hours": 2,
        }
    )

    response = await execute_scenario(req)

    assert response.status_code == 404
    body = json.loads(response.get_body())
    assert body["error"]["code"] == "SCENARIO_NOT_FOUND"


@pytest.mark.asyncio
@patch("azure_haymaker.orchestrator.execute_api.load_config")
@patch("azure_haymaker.orchestrator.execute_api.DefaultAzureCredential")
@patch("azure_haymaker.orchestrator.execute_api.TableClient")
@patch("azure_haymaker.orchestrator.execute_api.validate_scenarios")
async def test_execute_scenario_rate_limit_exceeded(
    mock_validate,
    mock_table_client,
    mock_credential,
    mock_load_config,
    mock_request_factory,
    mock_config,
):
    """Test execution request when rate limit exceeded."""
    mock_load_config.return_value = mock_config
    mock_validate.return_value = (True, None)

    # Mock rate limiter - limit exceeded
    mock_limiter = AsyncMock()
    mock_limiter.check_multiple_limits.return_value = MagicMock(
        allowed=False,
        retry_after=3600,
    )

    with patch("azure_haymaker.orchestrator.execute_api.RateLimiter", return_value=mock_limiter):
        from azure_haymaker.orchestrator.execute_api import execute_scenario

        req = mock_request_factory(
            body={
                "scenarios": ["compute-01"],
                "duration_hours": 2,
            }
        )

        response = await execute_scenario(req)

        assert response.status_code == 429
        body = json.loads(response.get_body())
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert body["retry_after"] == 3600
        assert "Retry-After" in response.headers


@pytest.mark.asyncio
@patch("azure_haymaker.orchestrator.execute_api.load_config")
async def test_get_execution_status_success(mock_load_config, mock_request_factory, mock_config):
    """Test getting execution status successfully."""
    mock_load_config.return_value = mock_config

    # Mock execution tracker
    mock_tracker = AsyncMock()
    mock_tracker.get_execution_status.return_value = MagicMock(
        execution_id="exec-20251115-abc123",
        status=OnDemandExecutionStatus.RUNNING,
        scenarios=["compute-01"],
        created_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        progress={"completed": 0, "running": 1, "failed": 0, "total": 1},
        resources_created=5,
        model_dump_json=lambda: json.dumps(
            {
                "execution_id": "exec-20251115-abc123",
                "status": "running",
                "scenarios": ["compute-01"],
                "created_at": datetime.now(UTC).isoformat(),
                "progress": {"completed": 0, "running": 1, "failed": 0, "total": 1},
                "resources_created": 5,
            }
        ),
    )

    with (
        patch("azure_haymaker.orchestrator.execute_api.DefaultAzureCredential"),
        patch("azure_haymaker.orchestrator.execute_api.TableClient"),
        patch(
            "azure_haymaker.orchestrator.execute_api.ExecutionTracker", return_value=mock_tracker
        ),
    ):
        from azure_haymaker.orchestrator.execute_api import get_execution_status

        req = mock_request_factory(
            method="GET",
            route_params={"execution_id": "exec-20251115-abc123"},
        )

        response = await get_execution_status(req)

        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert body["execution_id"] == "exec-20251115-abc123"
        assert body["status"] == "running"


@pytest.mark.asyncio
@patch("azure_haymaker.orchestrator.execute_api.load_config")
async def test_get_execution_status_not_found(mock_load_config, mock_request_factory, mock_config):
    """Test getting status of non-existent execution."""
    mock_load_config.return_value = mock_config

    # Mock execution tracker - not found
    mock_tracker = AsyncMock()
    mock_tracker.get_execution_status.side_effect = Exception("Not found")

    with (
        patch("azure_haymaker.orchestrator.execute_api.DefaultAzureCredential"),
        patch("azure_haymaker.orchestrator.execute_api.TableClient"),
        patch(
            "azure_haymaker.orchestrator.execute_api.ExecutionTracker", return_value=mock_tracker
        ),
    ):
        from azure_haymaker.orchestrator.execute_api import get_execution_status

        req = mock_request_factory(
            method="GET",
            route_params={"execution_id": "exec-nonexistent"},
        )

        response = await get_execution_status(req)

        assert response.status_code == 404
        body = json.loads(response.get_body())
        assert body["error"]["code"] == "EXECUTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_execution_status_missing_id(mock_request_factory):
    """Test getting status without execution ID."""
    from azure_haymaker.orchestrator.execute_api import get_execution_status

    req = mock_request_factory(
        method="GET",
        route_params={},  # No execution_id
    )

    response = await get_execution_status(req)

    assert response.status_code == 400
    body = json.loads(response.get_body())
    assert body["error"]["code"] == "MISSING_EXECUTION_ID"


def test_validate_scenarios_all_exist():
    """Test scenario validation when all scenarios exist."""
    with patch("azure_haymaker.orchestrator.execute_api.get_scenario_path") as mock_get_path:
        mock_get_path.return_value = MagicMock(exists=lambda: True)

        from azure_haymaker.orchestrator.execute_api import validate_scenarios

        valid, error = validate_scenarios(["compute-01", "networking-01"])

        assert valid is True
        assert error is None


def test_validate_scenarios_some_missing():
    """Test scenario validation when some scenarios don't exist."""
    with patch("azure_haymaker.orchestrator.execute_api.get_scenario_path") as mock_get_path:

        def get_path_side_effect(name):
            if name == "invalid-scenario":
                return None
            return MagicMock(exists=lambda: True)

        mock_get_path.side_effect = get_path_side_effect

        from azure_haymaker.orchestrator.execute_api import validate_scenarios

        valid, error = validate_scenarios(["compute-01", "invalid-scenario"])

        assert valid is False
        assert "invalid-scenario" in error


def test_get_scenario_path_not_found():
    """Test getting scenario path when it doesn't exist."""
    with patch("azure_haymaker.orchestrator.execute_api.Path") as mock_path:
        mock_scenarios_dir = MagicMock()
        mock_scenarios_dir.exists.return_value = True
        mock_scenarios_dir.glob.return_value = []  # No matching files

        mock_path.return_value.parent.parent.parent.parent = MagicMock()
        mock_path.return_value.parent.parent.parent.parent.__truediv__ = (
            lambda self, x: mock_scenarios_dir if x == "scenarios" else MagicMock()
        )

        from azure_haymaker.orchestrator.execute_api import get_scenario_path

        path = get_scenario_path("nonexistent")

        assert path is None
