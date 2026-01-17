"""Unit tests for monitoring_service module.

Tests for the business logic layer of the monitoring API, including validation,
filtering, and data transformation.

This module tests:
- MonitoringService initialization
- get_status method
- get_run_details method
- get_run_resources method with filtering and pagination
- Validation methods
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.orchestrator.models.api_errors import (
    InvalidParameterError,
    RunNotFoundError,
)
from azure_haymaker.orchestrator.services.monitoring_service import MonitoringService


def create_mock_repository() -> MagicMock:
    """Create a mock MonitoringRepository."""
    return MagicMock()


class TestMonitoringServiceInit:
    """Tests for MonitoringService initialization."""

    def test_init_with_repository(self) -> None:
        """Test successful initialization with repository."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        assert service.repository == mock_repo


class TestMonitoringServiceGetStatus:
    """Tests for the get_status method."""

    @pytest.mark.asyncio
    async def test_get_status_returns_idle_when_no_status(self) -> None:
        """Test that get_status returns idle state when no status file exists."""
        mock_repo = create_mock_repository()
        mock_repo.get_status = AsyncMock(return_value=None)

        service = MonitoringService(repository=mock_repo)
        status = await service.get_status()

        assert status["status"] == "idle"
        assert status["health"] == "healthy"
        assert status["current_run_id"] is None
        assert status["started_at"] is None
        assert status["phase"] is None

    @pytest.mark.asyncio
    async def test_get_status_returns_stored_status(self) -> None:
        """Test that get_status returns stored status data."""
        mock_repo = create_mock_repository()
        mock_repo.get_status = AsyncMock(
            return_value={
                "status": "running",
                "health": "healthy",
                "current_run_id": "run-123",
                "started_at": "2025-01-01T12:00:00Z",
                "scheduled_end_at": "2025-01-01T20:00:00Z",
                "phase": "monitoring",
                "scenarios_count": 10,
                "scenarios_completed": 5,
                "scenarios_running": 3,
                "scenarios_failed": 2,
                "next_scheduled_run": "2025-01-02T12:00:00Z",
            }
        )

        service = MonitoringService(repository=mock_repo)
        status = await service.get_status()

        assert status["status"] == "running"
        assert status["current_run_id"] == "run-123"
        assert status["phase"] == "monitoring"
        assert status["scenarios_count"] == 10
        assert status["scenarios_completed"] == 5

    @pytest.mark.asyncio
    async def test_get_status_handles_partial_data(self) -> None:
        """Test that get_status handles missing fields gracefully."""
        mock_repo = create_mock_repository()
        mock_repo.get_status = AsyncMock(
            return_value={
                "status": "running",
                # Missing most fields
            }
        )

        service = MonitoringService(repository=mock_repo)
        status = await service.get_status()

        assert status["status"] == "running"
        assert status["health"] == "healthy"  # Default
        assert status["current_run_id"] is None


class TestMonitoringServiceGetRunDetails:
    """Tests for the get_run_details method."""

    @pytest.mark.asyncio
    async def test_get_run_details_with_valid_uuid(self) -> None:
        """Test get_run_details with valid UUID."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_report = AsyncMock(
            return_value={
                "run_id": run_id,
                "started_at": "2025-01-01T12:00:00Z",
                "ended_at": "2025-01-01T20:00:00Z",
                "status": "completed",
                "phase": "reporting",
                "simulation_size": "medium",
                "scenarios": [{"name": "compute-01", "status": "completed"}],
                "total_resources": 50,
                "total_service_principals": 10,
                "cleanup_verification": {"verified": True},
                "errors": [],
            }
        )

        service = MonitoringService(repository=mock_repo)
        details = await service.get_run_details(run_id)

        assert details["run_id"] == run_id
        assert details["status"] == "completed"
        assert details["total_resources"] == 50
        mock_repo.get_run_report.assert_called_once_with(run_id)

    @pytest.mark.asyncio
    async def test_get_run_details_invalid_uuid_raises_error(self) -> None:
        """Test that invalid UUID raises InvalidParameterError."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError) as exc_info:
            await service.get_run_details("invalid-not-uuid")

        assert "run_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_run_details_not_found_raises_error(self) -> None:
        """Test that missing run raises RunNotFoundError."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_report = AsyncMock(side_effect=ResourceNotFoundError("Not found"))

        service = MonitoringService(repository=mock_repo)

        with pytest.raises(RunNotFoundError):
            await service.get_run_details(run_id)

    @pytest.mark.asyncio
    async def test_get_run_details_handles_missing_optional_fields(self) -> None:
        """Test that missing optional fields are handled."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_report = AsyncMock(
            return_value={
                "run_id": run_id,
                "started_at": "2025-01-01T12:00:00Z",
                "status": "running",
                # Missing optional fields
            }
        )

        service = MonitoringService(repository=mock_repo)
        details = await service.get_run_details(run_id)

        assert details["run_id"] == run_id
        assert details["ended_at"] is None
        assert details["scenarios"] == []
        assert details["total_resources"] == 0


class TestMonitoringServiceGetRunResources:
    """Tests for the get_run_resources method."""

    @pytest.mark.asyncio
    async def test_get_run_resources_basic(self) -> None:
        """Test basic resource retrieval."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(
            return_value={
                "resources": [
                    {
                        "resource_id": "res-1",
                        "scenario_name": "compute-01",
                        "resource_type": "VM",
                        "status": "created",
                    },
                    {
                        "resource_id": "res-2",
                        "scenario_name": "storage-01",
                        "resource_type": "StorageAccount",
                        "status": "created",
                    },
                ]
            }
        )

        service = MonitoringService(repository=mock_repo)
        result = await service.get_run_resources(run_id)

        assert result["run_id"] == run_id
        assert len(result["resources"]) == 2
        assert result["pagination"]["total_items"] == 2

    @pytest.mark.asyncio
    async def test_get_run_resources_invalid_run_id(self) -> None:
        """Test that invalid run_id raises InvalidParameterError."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError):
            await service.get_run_resources("not-a-uuid")

    @pytest.mark.asyncio
    async def test_get_run_resources_with_scenario_filter(self) -> None:
        """Test resource filtering by scenario name."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(
            return_value={
                "resources": [
                    {"resource_id": "res-1", "scenario_name": "compute-01", "status": "created"},
                    {"resource_id": "res-2", "scenario_name": "storage-01", "status": "created"},
                    {"resource_id": "res-3", "scenario_name": "compute-01", "status": "created"},
                ]
            }
        )

        service = MonitoringService(repository=mock_repo)
        result = await service.get_run_resources(run_id, scenario_name="compute-01")

        assert len(result["resources"]) == 2
        assert all(r["scenario_name"] == "compute-01" for r in result["resources"])

    @pytest.mark.asyncio
    async def test_get_run_resources_with_status_filter(self) -> None:
        """Test resource filtering by status."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(
            return_value={
                "resources": [
                    {"resource_id": "res-1", "status": "created"},
                    {"resource_id": "res-2", "status": "deleted"},
                    {"resource_id": "res-3", "status": "created"},
                ]
            }
        )

        service = MonitoringService(repository=mock_repo)
        result = await service.get_run_resources(run_id, status="deleted")

        assert len(result["resources"]) == 1
        assert result["resources"][0]["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_get_run_resources_with_resource_type_filter(self) -> None:
        """Test resource filtering by resource type."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(
            return_value={
                "resources": [
                    {"resource_id": "res-1", "resource_type": "VM", "status": "created"},
                    {"resource_id": "res-2", "resource_type": "Storage", "status": "created"},
                    {"resource_id": "res-3", "resource_type": "VM", "status": "created"},
                ]
            }
        )

        service = MonitoringService(repository=mock_repo)
        result = await service.get_run_resources(run_id, resource_type="VM")

        assert len(result["resources"]) == 2

    @pytest.mark.asyncio
    async def test_get_run_resources_invalid_status(self) -> None:
        """Test that invalid status raises InvalidParameterError."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError) as exc_info:
            await service.get_run_resources(run_id, status="invalid_status")

        assert "status" in str(exc_info.value)


class TestMonitoringServicePagination:
    """Tests for pagination in get_run_resources."""

    @pytest.mark.asyncio
    async def test_pagination_first_page(self) -> None:
        """Test pagination returns first page correctly."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(
            return_value={"resources": [{"resource_id": f"res-{i}"} for i in range(25)]}
        )

        service = MonitoringService(repository=mock_repo)
        result = await service.get_run_resources(run_id, page=1, page_size=10)

        assert len(result["resources"]) == 10
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 10
        assert result["pagination"]["total_items"] == 25
        assert result["pagination"]["total_pages"] == 3
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_previous"] is False

    @pytest.mark.asyncio
    async def test_pagination_middle_page(self) -> None:
        """Test pagination returns middle page correctly."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(
            return_value={"resources": [{"resource_id": f"res-{i}"} for i in range(25)]}
        )

        service = MonitoringService(repository=mock_repo)
        result = await service.get_run_resources(run_id, page=2, page_size=10)

        assert len(result["resources"]) == 10
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_previous"] is True

    @pytest.mark.asyncio
    async def test_pagination_last_page(self) -> None:
        """Test pagination returns last page correctly."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(
            return_value={"resources": [{"resource_id": f"res-{i}"} for i in range(25)]}
        )

        service = MonitoringService(repository=mock_repo)
        result = await service.get_run_resources(run_id, page=3, page_size=10)

        assert len(result["resources"]) == 5  # Only 5 items on last page
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_previous"] is True

    @pytest.mark.asyncio
    async def test_pagination_invalid_page(self) -> None:
        """Test that page < 1 raises InvalidParameterError."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError) as exc_info:
            await service.get_run_resources(run_id, page=0)

        assert "page" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pagination_invalid_page_size_too_small(self) -> None:
        """Test that page_size < 1 raises InvalidParameterError."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError) as exc_info:
            await service.get_run_resources(run_id, page_size=0)

        assert "page_size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pagination_invalid_page_size_too_large(self) -> None:
        """Test that page_size > 500 raises InvalidParameterError."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError) as exc_info:
            await service.get_run_resources(run_id, page_size=501)

        assert "page_size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pagination_page_exceeds_total(self) -> None:
        """Test that requesting page beyond total raises InvalidParameterError."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(
            return_value={"resources": [{"resource_id": f"res-{i}"} for i in range(5)]}
        )

        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError) as exc_info:
            await service.get_run_resources(run_id, page=10, page_size=10)

        assert "exceeds total pages" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pagination_empty_result(self) -> None:
        """Test pagination with empty result set."""
        run_id = str(uuid.uuid4())
        mock_repo = create_mock_repository()
        mock_repo.get_run_resources = AsyncMock(return_value={"resources": []})

        service = MonitoringService(repository=mock_repo)
        result = await service.get_run_resources(run_id)

        assert len(result["resources"]) == 0
        assert result["pagination"]["total_items"] == 0
        assert result["pagination"]["total_pages"] == 0


class TestMonitoringServiceValidation:
    """Tests for validation helper methods."""

    def test_validate_run_id_valid_uuid(self) -> None:
        """Test that valid UUID passes validation."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        # Should not raise
        service._validate_run_id(str(uuid.uuid4()))

    def test_validate_run_id_invalid_raises(self) -> None:
        """Test that invalid UUID raises InvalidParameterError."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError):
            service._validate_run_id("not-a-valid-uuid")

    def test_validate_pagination_valid(self) -> None:
        """Test that valid pagination passes validation."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        # Should not raise
        service._validate_pagination(1, 100)
        service._validate_pagination(10, 500)

    def test_validate_resource_status_valid(self) -> None:
        """Test that valid status passes validation."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        # Should not raise
        for status in ["created", "exists", "deleted", "deletion_failed"]:
            service._validate_resource_status(status)

    def test_validate_resource_status_invalid(self) -> None:
        """Test that invalid status raises InvalidParameterError."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)

        with pytest.raises(InvalidParameterError):
            service._validate_resource_status("unknown_status")


class TestMonitoringServiceFilterApplication:
    """Tests for the filter application method."""

    def test_apply_filters_no_filters(self) -> None:
        """Test that no filters returns all resources."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)
        resources: list[dict[str, Any]] = [
            {"scenario_name": "compute", "resource_type": "VM", "status": "created"},
            {"scenario_name": "storage", "resource_type": "Storage", "status": "deleted"},
        ]

        result = service._apply_resource_filters(resources, None, None, None)

        assert len(result) == 2

    def test_apply_filters_multiple(self) -> None:
        """Test applying multiple filters."""
        mock_repo = create_mock_repository()
        service = MonitoringService(repository=mock_repo)
        resources: list[dict[str, Any]] = [
            {"scenario_name": "compute", "resource_type": "VM", "status": "created"},
            {"scenario_name": "compute", "resource_type": "VM", "status": "deleted"},
            {"scenario_name": "storage", "resource_type": "Storage", "status": "created"},
        ]

        result = service._apply_resource_filters(
            resources,
            scenario_name="compute",
            resource_type="VM",
            status="created",
        )

        assert len(result) == 1
        assert result[0]["scenario_name"] == "compute"
        assert result[0]["status"] == "created"
