"""Unit tests for failure tracking repository and schedule health extensions.

Tests cover:
- Schedule model health/quarantine fields
- FailureTrackingRepository CRUD operations
- Metrics aggregation
- Threshold detection
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from azure_haymaker.models.schedule import Schedule, ScheduleResponse
from azure_haymaker.orchestrator.repositories.failure_tracking_repository import (
    FailureTrackingRepository,
    ScenarioExecutionRecord,
    ScenarioMetrics,
)


# =============================================================================
# Schedule Model Health Extension Tests
# =============================================================================


class TestScheduleHealthFields:
    """Tests for Schedule model health and quarantine fields."""

    def test_schedule_default_not_quarantined(self):
        """New schedules should not be quarantined by default."""
        schedule = Schedule(
            name="Test Schedule",
            cron_expression="0 0 * * *",
        )
        assert schedule.quarantined is False
        assert schedule.quarantined_at is None
        assert schedule.quarantine_reason is None
        assert schedule.failure_count_24h == 0
        assert schedule.last_failure_at is None

    def test_schedule_quarantine_fields(self):
        """Schedule should accept quarantine fields."""
        now = datetime.now(UTC)
        schedule = Schedule(
            name="Quarantined Schedule",
            cron_expression="0 0 * * *",
            quarantined=True,
            quarantined_at=now,
            quarantine_reason="Exceeded failure threshold",
            failure_count_24h=10,
            last_failure_at=now,
        )
        assert schedule.quarantined is True
        assert schedule.quarantined_at == now
        assert schedule.quarantine_reason == "Exceeded failure threshold"
        assert schedule.failure_count_24h == 10
        assert schedule.last_failure_at == now

    def test_schedule_failure_count_validation(self):
        """Failure count should not accept negative values."""
        with pytest.raises(ValueError):
            Schedule(
                name="Invalid Schedule",
                cron_expression="0 0 * * *",
                failure_count_24h=-1,
            )

    def test_schedule_response_includes_health_fields(self):
        """ScheduleResponse should include health fields."""
        now = datetime.now(UTC)
        response = ScheduleResponse(
            id="test-123",
            name="Test Schedule",
            cron_expression="0 0 * * *",
            scenarios=None,
            scenario_count=5,
            enabled=True,
            created_at=now,
            next_run=None,
            quarantined=True,
            quarantined_at=now,
            quarantine_reason="Test reason",
            failure_count_24h=5,
            last_failure_at=now,
        )
        assert response.quarantined is True
        assert response.quarantined_at == now
        assert response.quarantine_reason == "Test reason"
        assert response.failure_count_24h == 5
        assert response.last_failure_at == now

    def test_schedule_response_default_health_fields(self):
        """ScheduleResponse should have default health field values."""
        now = datetime.now(UTC)
        response = ScheduleResponse(
            id="test-123",
            name="Test Schedule",
            cron_expression="0 0 * * *",
            scenarios=None,
            scenario_count=5,
            enabled=True,
            created_at=now,
        )
        assert response.quarantined is False
        assert response.quarantined_at is None
        assert response.quarantine_reason is None
        assert response.failure_count_24h == 0
        assert response.last_failure_at is None


# =============================================================================
# ScenarioExecutionRecord Tests
# =============================================================================


class TestScenarioExecutionRecord:
    """Tests for ScenarioExecutionRecord dataclass."""

    def test_successful_execution_record(self):
        """Create record for successful execution."""
        record = ScenarioExecutionRecord(
            scenario_name="test-scenario",
            success=True,
            duration_seconds=5.5,
        )
        assert record.scenario_name == "test-scenario"
        assert record.success is True
        assert record.duration_seconds == 5.5
        assert record.error_type is None
        assert record.error_message is None
        assert record.timestamp is not None

    def test_failed_execution_record(self):
        """Create record for failed execution."""
        record = ScenarioExecutionRecord(
            scenario_name="test-scenario",
            success=False,
            duration_seconds=2.0,
            error_type="TimeoutError",
            error_message="Operation timed out",
            run_id="run-123",
        )
        assert record.success is False
        assert record.error_type == "TimeoutError"
        assert record.error_message == "Operation timed out"
        assert record.run_id == "run-123"


# =============================================================================
# ScenarioMetrics Tests
# =============================================================================


class TestScenarioMetrics:
    """Tests for ScenarioMetrics dataclass."""

    def test_metrics_with_no_errors(self):
        """Create metrics with no errors."""
        now = datetime.now(UTC)
        metrics = ScenarioMetrics(
            scenario_name="test-scenario",
            total_executions=10,
            successful_executions=10,
            failed_executions=0,
            failure_rate=0.0,
            avg_duration_seconds=5.0,
            last_execution_at=now,
            last_failure_at=None,
            window_hours=24,
        )
        assert metrics.failure_rate == 0.0
        assert metrics.last_failure_at is None
        assert metrics.error_types == {}

    def test_metrics_with_errors(self):
        """Create metrics with errors."""
        now = datetime.now(UTC)
        metrics = ScenarioMetrics(
            scenario_name="test-scenario",
            total_executions=10,
            successful_executions=5,
            failed_executions=5,
            failure_rate=0.5,
            avg_duration_seconds=5.0,
            last_execution_at=now,
            last_failure_at=now,
            window_hours=24,
            error_types={"TimeoutError": 3, "ValueError": 2},
        )
        assert metrics.failure_rate == 0.5
        assert metrics.error_types["TimeoutError"] == 3


# =============================================================================
# FailureTrackingRepository Tests
# =============================================================================


class TestFailureTrackingRepository:
    """Tests for FailureTrackingRepository with mocked storage."""

    @pytest.fixture
    def mock_table_client(self):
        """Create mock table client with in-memory storage."""
        client = MagicMock()
        storage: dict[tuple[str, str], dict] = {}

        def create_entity(entity):
            pk = entity.get("PartitionKey")
            rk = entity.get("RowKey")
            key = (pk, rk)
            storage[key] = entity.copy()
            return entity

        def query_entities(query_filter=None, select=None):
            # Simple filter parsing for tests
            results = []
            for entity in storage.values():
                # Basic matching - real implementation would parse filter
                include = True
                if query_filter:
                    if "ScenarioName eq" in query_filter:
                        # Extract scenario name from filter
                        parts = query_filter.split("ScenarioName eq '")
                        if len(parts) > 1:
                            name = parts[1].split("'")[0]
                            if entity.get("ScenarioName") != name:
                                include = False
                if include:
                    if select:
                        filtered = {k: entity.get(k) for k in select}
                        results.append(filtered)
                    else:
                        results.append(entity.copy())
            return results

        def delete_entity(partition_key, row_key):
            key = (partition_key, row_key)
            if key in storage:
                del storage[key]

        client.create_entity = create_entity
        client.query_entities = query_entities
        client.delete_entity = delete_entity
        client._storage = storage  # Expose for test inspection

        return client

    @pytest.mark.asyncio
    async def test_record_successful_execution(self, mock_table_client):
        """Recording successful execution should create entity."""
        repo = FailureTrackingRepository(mock_table_client)

        record = await repo.record_execution(
            scenario_name="test-scenario",
            success=True,
            duration_seconds=5.5,
        )

        assert record.scenario_name == "test-scenario"
        assert record.success is True
        assert record.duration_seconds == 5.5
        assert len(mock_table_client._storage) == 1

    @pytest.mark.asyncio
    async def test_record_failed_execution(self, mock_table_client):
        """Recording failed execution should include error details."""
        repo = FailureTrackingRepository(mock_table_client)

        record = await repo.record_execution(
            scenario_name="test-scenario",
            success=False,
            duration_seconds=2.0,
            error_type="TimeoutError",
            error_message="Operation timed out",
            run_id="run-123",
        )

        assert record.success is False
        assert record.error_type == "TimeoutError"
        assert record.error_message == "Operation timed out"

        # Verify entity stored correctly
        entity = list(mock_table_client._storage.values())[0]
        assert entity["Success"] is False
        assert entity["ErrorType"] == "TimeoutError"
        assert entity["RunId"] == "run-123"

    @pytest.mark.asyncio
    async def test_get_metrics_empty(self, mock_table_client):
        """Get metrics should return zeros for empty data."""
        repo = FailureTrackingRepository(mock_table_client)

        metrics = await repo.get_metrics("nonexistent-scenario")

        assert metrics.scenario_name == "nonexistent-scenario"
        assert metrics.total_executions == 0
        assert metrics.failure_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_metrics_with_data(self, mock_table_client):
        """Get metrics should calculate correctly from data."""
        repo = FailureTrackingRepository(mock_table_client)

        # Add some executions
        for i in range(10):
            await repo.record_execution(
                scenario_name="test-scenario",
                success=(i < 7),  # 7 success, 3 failure
                duration_seconds=float(i + 1),
            )

        metrics = await repo.get_metrics("test-scenario")

        assert metrics.scenario_name == "test-scenario"
        assert metrics.total_executions == 10
        assert metrics.successful_executions == 7
        assert metrics.failed_executions == 3
        assert metrics.failure_rate == 0.3

    @pytest.mark.asyncio
    async def test_get_all_scenario_names(self, mock_table_client):
        """Get all scenario names should return unique names."""
        repo = FailureTrackingRepository(mock_table_client)

        # Add executions for multiple scenarios
        await repo.record_execution("scenario-1", True, 1.0)
        await repo.record_execution("scenario-2", True, 1.0)
        await repo.record_execution("scenario-1", False, 1.0)  # Duplicate

        names = await repo.get_all_scenario_names()

        assert sorted(names) == ["scenario-1", "scenario-2"]


# =============================================================================
# Threshold Detection Tests
# =============================================================================


class TestThresholdDetection:
    """Tests for scenarios exceeding failure threshold."""

    @pytest.fixture
    def mock_table_client(self):
        """Create mock table client with proper filtering."""
        client = MagicMock()
        storage: dict[tuple[str, str], dict] = {}

        def create_entity(entity):
            pk = entity.get("PartitionKey")
            rk = entity.get("RowKey")
            storage[(pk, rk)] = entity.copy()
            return entity

        def query_entities(query_filter=None, select=None):
            """Filter entities based on query filter."""
            results = []
            for entity in storage.values():
                include = True

                # Parse filter for ScenarioName matching
                if query_filter and "ScenarioName eq" in query_filter:
                    # Extract scenario name from filter
                    parts = query_filter.split("ScenarioName eq '")
                    if len(parts) > 1:
                        name = parts[1].split("'")[0]
                        if entity.get("ScenarioName") != name:
                            include = False

                if include:
                    if select:
                        filtered = {k: entity.get(k) for k in select}
                        results.append(filtered)
                    else:
                        results.append(entity.copy())
            return results

        client.create_entity = create_entity
        client.query_entities = query_entities
        client._storage = storage

        return client

    @pytest.mark.asyncio
    async def test_get_scenarios_exceeding_threshold_empty(self, mock_table_client):
        """No scenarios should be returned if none exceed threshold."""
        repo = FailureTrackingRepository(mock_table_client)

        # Add only successful executions
        for _ in range(5):
            await repo.record_execution("healthy-scenario", True, 1.0)

        exceeding = await repo.get_scenarios_exceeding_threshold(threshold=0.5)

        assert exceeding == []

    @pytest.mark.asyncio
    async def test_get_scenarios_exceeding_threshold_found(self, mock_table_client):
        """Scenarios exceeding threshold should be returned."""
        repo = FailureTrackingRepository(mock_table_client)

        # Add healthy scenario (0% failure)
        for _ in range(5):
            await repo.record_execution("healthy-scenario", True, 1.0)

        # Add unhealthy scenario (100% failure)
        for _ in range(5):
            await repo.record_execution("unhealthy-scenario", False, 1.0)

        exceeding = await repo.get_scenarios_exceeding_threshold(threshold=0.5)

        assert len(exceeding) == 1
        assert exceeding[0].scenario_name == "unhealthy-scenario"
        assert exceeding[0].failure_rate == 1.0

    @pytest.mark.asyncio
    async def test_get_scenarios_sorted_by_failure_rate(self, mock_table_client):
        """Results should be sorted by failure rate descending."""
        repo = FailureTrackingRepository(mock_table_client)

        # Scenario A: 60% failure
        for i in range(10):
            await repo.record_execution("scenario-a", success=(i < 4), duration_seconds=1.0)

        # Scenario B: 80% failure
        for i in range(10):
            await repo.record_execution("scenario-b", success=(i < 2), duration_seconds=1.0)

        exceeding = await repo.get_scenarios_exceeding_threshold(threshold=0.5)

        assert len(exceeding) == 2
        assert exceeding[0].scenario_name == "scenario-b"  # 80% first
        assert exceeding[1].scenario_name == "scenario-a"  # 60% second
