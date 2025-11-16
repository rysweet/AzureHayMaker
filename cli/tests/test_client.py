"""Unit tests for HayMaker client SDK."""

import httpx
import pytest
from respx import MockRouter

from haymaker_cli.auth import ApiKeyAuthProvider
from haymaker_cli.client import HayMakerClient, HayMakerClientError, SyncHayMakerClient
from haymaker_cli.models import (
    AgentInfo,
    ExecutionResponse,
    ExecutionStatus,
    MetricsSummary,
    OrchestratorStatus,
    ResourceInfo,
)


@pytest.fixture
def auth_provider():
    """Create test auth provider."""
    return ApiKeyAuthProvider("test-api-key")


@pytest.fixture
def async_client(auth_provider):
    """Create async test client."""
    return HayMakerClient("https://api.example.com", auth_provider)


@pytest.fixture
def sync_client(auth_provider):
    """Create sync test client."""
    return SyncHayMakerClient("https://api.example.com", auth_provider)


@pytest.mark.asyncio
async def test_get_status_success(async_client, respx_mock: MockRouter):
    """Test successful status retrieval."""
    respx_mock.get("https://api.example.com/api/v1/status").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "running",
                "current_run_id": "run-123",
                "phase": "monitoring",
                "active_agents": 5,
                "next_run": "2025-11-15T18:00:00Z",
            },
        )
    )

    status = await async_client.get_status()

    assert isinstance(status, OrchestratorStatus)
    assert status.status == "running"
    assert status.current_run_id == "run-123"
    assert status.active_agents == 5


@pytest.mark.asyncio
async def test_get_status_error(async_client, respx_mock: MockRouter):
    """Test error handling for status retrieval."""
    respx_mock.get("https://api.example.com/api/v1/status").mock(
        return_value=httpx.Response(
            500,
            json={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Database unavailable",
                    "details": {},
                }
            },
        )
    )

    with pytest.raises(HayMakerClientError) as exc_info:
        await async_client.get_status()

    assert exc_info.value.status_code == 500
    assert "Database unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_metrics_success(async_client, respx_mock: MockRouter):
    """Test successful metrics retrieval."""
    respx_mock.get("https://api.example.com/api/v1/metrics").mock(
        return_value=httpx.Response(
            200,
            json={
                "total_executions": 100,
                "active_agents": 5,
                "total_resources": 250,
                "last_execution": "2025-11-15T10:00:00Z",
                "success_rate": 0.95,
                "period": "7d",
                "scenarios": [
                    {
                        "scenario_name": "compute-01",
                        "run_count": 50,
                        "success_count": 48,
                        "fail_count": 2,
                        "avg_duration_hours": 8.5,
                    }
                ],
            },
        )
    )

    metrics = await async_client.get_metrics(period="7d")

    assert isinstance(metrics, MetricsSummary)
    assert metrics.total_executions == 100
    assert metrics.success_rate == 0.95
    assert len(metrics.scenarios) == 1
    assert metrics.scenarios[0].scenario_name == "compute-01"


@pytest.mark.asyncio
async def test_execute_scenario_success(async_client, respx_mock: MockRouter):
    """Test successful scenario execution."""
    respx_mock.post("https://api.example.com/api/v1/execute").mock(
        return_value=httpx.Response(
            202,
            json={
                "execution_id": "exec-123",
                "status": "queued",
                "status_url": "https://api.example.com/api/v1/executions/exec-123",
                "created_at": "2025-11-15T10:00:00Z",
            },
        )
    )

    execution = await async_client.execute_scenario("compute-01")

    assert isinstance(execution, ExecutionResponse)
    assert execution.execution_id == "exec-123"
    assert execution.status == "queued"


@pytest.mark.asyncio
async def test_get_execution_status_success(async_client, respx_mock: MockRouter):
    """Test successful execution status retrieval."""
    respx_mock.get("https://api.example.com/api/v1/executions/exec-123").mock(
        return_value=httpx.Response(
            200,
            json={
                "execution_id": "exec-123",
                "scenario_name": "compute-01",
                "status": "running",
                "created_at": "2025-11-15T10:00:00Z",
                "started_at": "2025-11-15T10:05:00Z",
                "completed_at": None,
                "agent_id": "agent-456",
                "report_url": None,
                "error": None,
            },
        )
    )

    status = await async_client.get_execution_status("exec-123")

    assert isinstance(status, ExecutionStatus)
    assert status.execution_id == "exec-123"
    assert status.status == "running"
    assert status.agent_id == "agent-456"


@pytest.mark.asyncio
async def test_list_agents_success(async_client, respx_mock: MockRouter):
    """Test successful agents listing."""
    respx_mock.get("https://api.example.com/api/v1/agents").mock(
        return_value=httpx.Response(
            200,
            json={
                "agents": [
                    {
                        "agent_id": "agent-123",
                        "scenario": "compute-01",
                        "status": "running",
                        "started_at": "2025-11-15T10:00:00Z",
                        "completed_at": None,
                        "progress": "Phase 2: Operations",
                        "error": None,
                    }
                ]
            },
        )
    )

    agents = await async_client.list_agents()

    assert isinstance(agents, list)
    assert len(agents) == 1
    assert isinstance(agents[0], AgentInfo)
    assert agents[0].agent_id == "agent-123"
    assert agents[0].status == "running"


@pytest.mark.asyncio
async def test_list_resources_success(async_client, respx_mock: MockRouter):
    """Test successful resources listing."""
    respx_mock.get("https://api.example.com/api/v1/resources").mock(
        return_value=httpx.Response(
            200,
            json={
                "resources": [
                    {
                        "id": "/subscriptions/sub-123/resourceGroups/rg-123",
                        "name": "rg-haymaker-compute-01",
                        "type": "Microsoft.Resources/resourceGroups",
                        "scenario": "compute-01",
                        "execution_id": "exec-123",
                        "created_at": "2025-11-15T10:00:00Z",
                        "deleted_at": None,
                        "status": "created",
                        "tags": {
                            "AzureHayMaker-managed": "true",
                            "execution_id": "exec-123",
                        },
                    }
                ]
            },
        )
    )

    resources = await async_client.list_resources()

    assert isinstance(resources, list)
    assert len(resources) == 1
    assert isinstance(resources[0], ResourceInfo)
    assert resources[0].name == "rg-haymaker-compute-01"
    assert resources[0].status == "created"


@pytest.mark.asyncio
async def test_request_timeout(async_client, respx_mock: MockRouter):
    """Test request timeout handling."""
    respx_mock.get("https://api.example.com/api/v1/status").mock(
        side_effect=httpx.TimeoutException("Request timeout")
    )

    with pytest.raises(HayMakerClientError, match="Request timeout"):
        await async_client.get_status()


@pytest.mark.asyncio
async def test_network_error(async_client, respx_mock: MockRouter):
    """Test network error handling."""
    respx_mock.get("https://api.example.com/api/v1/status").mock(
        side_effect=httpx.NetworkError("Network unreachable")
    )

    with pytest.raises(HayMakerClientError, match="Network error"):
        await async_client.get_status()


def test_sync_client_get_status(sync_client, respx_mock: MockRouter):
    """Test sync client status retrieval."""
    respx_mock.get("https://api.example.com/api/v1/status").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "running",
                "current_run_id": None,
                "phase": None,
                "active_agents": 3,
                "next_run": None,
            },
        )
    )

    status = sync_client.get_status()

    assert isinstance(status, OrchestratorStatus)
    assert status.status == "running"
    assert status.active_agents == 3


def test_sync_client_error_handling(sync_client, respx_mock: MockRouter):
    """Test sync client error handling."""
    respx_mock.get("https://api.example.com/api/v1/status").mock(
        return_value=httpx.Response(
            404,
            json={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Resource not found",
                    "details": {},
                }
            },
        )
    )

    with pytest.raises(HayMakerClientError) as exc_info:
        sync_client.get_status()

    assert exc_info.value.status_code == 404
    assert "Resource not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_client_context_manager(auth_provider, respx_mock: MockRouter):
    """Test client as async context manager."""
    respx_mock.get("https://api.example.com/api/v1/status").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "idle",
                "current_run_id": None,
                "phase": None,
                "active_agents": 0,
                "next_run": None,
            },
        )
    )

    async with HayMakerClient("https://api.example.com", auth_provider) as client:
        status = await client.get_status()
        assert status.status == "idle"

    # Client should be closed after context manager exits
    assert client._client is None
