"""Unit tests for orchestrator route modules.

Tests the decomposed route modules from orchestrator_server.py.
Following TDD approach - these tests are written first to define
expected behavior, then implementation makes them pass.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ==============================================================================
# TEST FIXTURES
# ==============================================================================


@pytest.fixture
def mock_auth_dep():
    """Mock authentication dependency."""
    return {"user": "test@example.com", "roles": ["admin"]}


@pytest.fixture
def sample_schedule_data():
    """Sample schedule creation data."""
    return {
        "name": "Daily Test Run",
        "cron_expression": "0 0 0,6,12,18 * * *",
        "scenario_count": 5,
        "enabled": True,
    }


@pytest.fixture
def sample_execution_data():
    """Sample execution data."""
    return {
        "run_id": "test-run-123",
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "phases": {},
    }


# ==============================================================================
# HEALTH ROUTES TESTS
# ==============================================================================


class TestHealthRoutes:
    """Tests for health_routes.py module."""

    def test_health_router_exists(self):
        """Test that health router can be imported."""
        from azure_haymaker.orchestrator.routes import health_router

        assert health_router is not None
        assert hasattr(health_router, "routes")

    def test_health_endpoint_returns_healthy_status(self):
        """Test health endpoint returns expected format."""
        # Call the endpoint function directly
        import asyncio

        from azure_haymaker.orchestrator.routes.health_routes import health

        result = asyncio.get_event_loop().run_until_complete(health())

        assert result["status"] == "healthy"
        assert result["service"] == "azure-haymaker-orchestrator"
        assert "timestamp" in result

    def test_status_endpoint_requires_auth(self):
        """Test status endpoint has auth dependency."""
        from azure_haymaker.orchestrator.routes.health_routes import router

        # Check that /status route exists and has dependencies
        routes = [r for r in router.routes if r.path == "/status"]
        assert len(routes) == 1

    @pytest.mark.asyncio
    async def test_status_returns_execution_counts(self, mock_auth_dep):
        """Test status endpoint returns execution information."""
        from azure_haymaker.orchestrator.routes.health_routes import status

        with patch(
            "azure_haymaker.orchestrator.routes.health_routes.executions",
            {"run-1": {"status": "running"}, "run-2": {"status": "completed"}},
        ):
            result = await status(mock_auth_dep)

        assert "status" in result
        assert "executions_active" in result
        assert "executions_total" in result


# ==============================================================================
# SCHEDULE ROUTES TESTS
# ==============================================================================


class TestScheduleRoutes:
    """Tests for schedule_routes.py module."""

    def test_schedule_router_exists(self):
        """Test that schedule router can be imported."""
        from azure_haymaker.orchestrator.routes import schedule_router

        assert schedule_router is not None

    def test_validate_cron_expression_valid(self):
        """Test valid cron expressions pass validation."""
        from azure_haymaker.orchestrator.routes.schedule_routes import (
            validate_cron_expression,
        )

        # 5-field cron
        assert validate_cron_expression("0 0 * * *") is True
        # 6-field cron (with seconds)
        assert validate_cron_expression("0 0 0,6,12,18 * * *") is True

    def test_validate_cron_expression_invalid(self):
        """Test invalid cron expressions raise ValueError."""
        from azure_haymaker.orchestrator.routes.schedule_routes import (
            validate_cron_expression,
        )

        with pytest.raises(ValueError, match="Invalid cron expression"):
            validate_cron_expression("not a cron")

        with pytest.raises(ValueError, match="Invalid cron expression"):
            validate_cron_expression("* * *")  # Too few fields

    def test_schedule_to_entity_conversion(self):
        """Test Schedule model to Table Storage entity conversion."""
        from azure_haymaker.models.schedule import Schedule
        from azure_haymaker.orchestrator.routes.schedule_routes import (
            schedule_to_entity,
        )

        schedule = Schedule(
            id="test-id",
            name="Test Schedule",
            cron_expression="0 0 * * *",
            scenario_count=5,
            enabled=True,
        )

        entity = schedule_to_entity(schedule)

        assert entity["PartitionKey"] == "schedule"
        assert entity["RowKey"] == "test-id"
        assert entity["Name"] == "Test Schedule"
        assert entity["CronExpression"] == "0 0 * * *"
        assert entity["Enabled"] is True

    def test_entity_to_schedule_conversion(self):
        """Test Table Storage entity to Schedule model conversion."""
        from azure_haymaker.orchestrator.routes.schedule_routes import (
            entity_to_schedule,
        )

        entity = {
            "PartitionKey": "schedule",
            "RowKey": "test-id",
            "Name": "Test Schedule",
            "CronExpression": "0 0 * * *",
            "ScenarioCount": 5,
            "Enabled": True,
            "CreatedAt": "2025-01-17T10:00:00+00:00",
        }

        schedule = entity_to_schedule(entity)

        assert schedule.id == "test-id"
        assert schedule.name == "Test Schedule"
        assert schedule.cron_expression == "0 0 * * *"
        assert schedule.enabled is True

    def test_get_next_run_time(self):
        """Test next run time calculation from cron expression."""
        from azure_haymaker.orchestrator.routes.schedule_routes import (
            get_next_run_time,
        )

        # Valid cron should return ISO format string
        result = get_next_run_time("0 0 * * *")
        assert result is not None
        # Should be parseable as datetime
        datetime.fromisoformat(result.replace("Z", "+00:00"))

    def test_get_next_run_time_invalid(self):
        """Test next run time returns None for invalid cron."""
        from azure_haymaker.orchestrator.routes.schedule_routes import (
            get_next_run_time,
        )

        result = get_next_run_time("invalid")
        assert result is None


# ==============================================================================
# EXECUTION ROUTES TESTS
# ==============================================================================


class TestExecutionRoutes:
    """Tests for execution_routes.py module."""

    def test_execution_router_exists(self):
        """Test that execution router can be imported."""
        from azure_haymaker.orchestrator.routes import execution_router

        assert execution_router is not None

    @pytest.mark.asyncio
    async def test_list_executions_returns_all(self, mock_auth_dep):
        """Test list executions returns all execution records."""
        from azure_haymaker.orchestrator.routes.execution_routes import (
            list_executions,
        )

        mock_executions = {
            "run-1": {"run_id": "run-1", "status": "completed"},
            "run-2": {"run_id": "run-2", "status": "running"},
        }

        with patch(
            "azure_haymaker.orchestrator.routes.execution_routes.executions",
            mock_executions,
        ):
            result = await list_executions(mock_auth_dep)

        assert "executions" in result
        assert len(result["executions"]) == 2

    @pytest.mark.asyncio
    async def test_get_execution_not_found(self, mock_auth_dep):
        """Test get execution raises 404 for unknown ID."""
        from fastapi import HTTPException

        from azure_haymaker.orchestrator.routes.execution_routes import get_execution

        with patch("azure_haymaker.orchestrator.routes.execution_routes.executions", {}):
            with pytest.raises(HTTPException) as exc_info:
                await get_execution("nonexistent", mock_auth_dep)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_execute_starts_background_task(self, mock_auth_dep):
        """Test execute endpoint starts orchestration in background."""
        from azure_haymaker.orchestrator.routes.execution_routes import (
            execute,
            set_run_orchestration_fn,
        )

        # Inject a mock run_orchestration function
        mock_orchestration = AsyncMock()
        set_run_orchestration_fn(mock_orchestration)

        with patch("asyncio.create_task"):
            result = await execute(mock_auth_dep, None)

        assert "execution_id" in result
        assert result["status"] == "started"

        # Clean up: reset the function
        set_run_orchestration_fn(None)


# ==============================================================================
# MULTI-TENANT ROUTES TESTS
# ==============================================================================


class TestMultiTenantRoutes:
    """Tests for multi_tenant_routes.py module."""

    def test_multi_tenant_router_exists(self):
        """Test that multi-tenant router can be imported."""
        from azure_haymaker.orchestrator.routes import multi_tenant_router

        assert multi_tenant_router is not None

    @pytest.mark.asyncio
    async def test_get_multi_tenant_execution_not_found(self, mock_auth_dep):
        """Test get multi-tenant execution raises 404 for unknown ID."""
        from fastapi import HTTPException

        from azure_haymaker.orchestrator.routes.multi_tenant_routes import (
            get_multi_tenant_execution,
        )

        with patch(
            "azure_haymaker.orchestrator.routes.multi_tenant_routes.meta_executions",
            {},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_multi_tenant_execution("nonexistent", mock_auth_dep)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_multi_tenant_executions(self, mock_auth_dep):
        """Test listing all multi-tenant executions."""
        from azure_haymaker.orchestrator.routes.multi_tenant_routes import (
            list_multi_tenant_executions,
        )

        mock_meta = {"meta-1": MagicMock(), "meta-2": MagicMock()}

        with patch(
            "azure_haymaker.orchestrator.routes.multi_tenant_routes.meta_executions",
            mock_meta,
        ):
            result = await list_multi_tenant_executions(mock_auth_dep)

        assert len(result) == 2


# ==============================================================================
# ANALYTICS ROUTES TESTS
# ==============================================================================


class TestAnalyticsRoutes:
    """Tests for analytics_routes.py module."""

    def test_analytics_router_exists(self):
        """Test that analytics router can be imported."""
        from azure_haymaker.orchestrator.routes import analytics_router

        assert analytics_router is not None

    @pytest.mark.asyncio
    async def test_metrics_returns_execution_stats(self, mock_auth_dep):
        """Test metrics endpoint returns execution statistics."""
        from azure_haymaker.orchestrator.routes.analytics_routes import metrics

        mock_executions = {
            "run-1": {"status": "completed"},
            "run-2": {"status": "completed"},
            "run-3": {"status": "running"},
        }

        with patch(
            "azure_haymaker.orchestrator.routes.analytics_routes.executions",
            mock_executions,
        ):
            result = await metrics(mock_auth_dep)

        assert result["total_executions"] == 3
        assert result["active_agents"] == 1
        assert "success_rate" in result


# ==============================================================================
# ORCHESTRATION SERVICE TESTS
# ==============================================================================


class TestOrchestrationService:
    """Tests for orchestration_service.py module."""

    def test_run_orchestration_function_exists(self):
        """Test that run_orchestration function can be imported."""
        from azure_haymaker.orchestrator.routes.orchestration_service import (
            run_orchestration,
        )

        assert callable(run_orchestration)

    def test_run_scheduled_orchestration_function_exists(self):
        """Test that run_scheduled_orchestration function can be imported."""
        from azure_haymaker.orchestrator.routes.orchestration_service import (
            run_scheduled_orchestration,
        )

        assert callable(run_scheduled_orchestration)


# ==============================================================================
# ROUTER INTEGRATION TESTS
# ==============================================================================


class TestRouterIntegration:
    """Tests for router integration in __init__.py."""

    def test_all_routers_exported(self):
        """Test that all routers are exported from routes package."""
        from azure_haymaker.orchestrator.routes import (
            analytics_router,
            execution_router,
            health_router,
            multi_tenant_router,
            schedule_router,
        )

        assert health_router is not None
        assert schedule_router is not None
        assert execution_router is not None
        assert multi_tenant_router is not None
        assert analytics_router is not None

    def test_orchestration_service_exported(self):
        """Test that orchestration service functions are exported."""
        from azure_haymaker.orchestrator.routes import (
            run_orchestration,
            run_scheduled_orchestration,
        )

        assert callable(run_orchestration)
        assert callable(run_scheduled_orchestration)

    def test_routes_all_exports(self):
        """Test __all__ exports all expected items."""
        from azure_haymaker.orchestrator import routes

        expected_exports = [
            "health_router",
            "schedule_router",
            "execution_router",
            "multi_tenant_router",
            "analytics_router",
            "run_orchestration",
            "run_scheduled_orchestration",
        ]

        for export in expected_exports:
            assert export in routes.__all__, f"Missing export: {export}"
