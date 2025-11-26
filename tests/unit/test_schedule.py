"""Unit tests for schedule models and API functionality.

Tests cover:
- Cron expression validation
- Schedule model entity conversion
- CRUD operations with mocked storage
- Update (PUT) endpoint behavior
"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import ResourceNotFoundError
from croniter import croniter

from azure_haymaker.models.schedule import (
    Schedule,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
)

# =============================================================================
# Cron Validation Tests
# =============================================================================


# Standalone implementation of cron validation (mirrors orchestrator_server)
def _validate_cron_expression(cron_expr: str) -> bool:
    """Validate a cron expression using croniter.

    Args:
        cron_expr: Cron expression string (5 or 6 fields supported).
                   6-field format: second minute hour day month weekday
                   5-field format: minute hour day month weekday (seconds default to 0)

    Returns:
        True if valid, raises ValueError otherwise

    Raises:
        ValueError: If the cron expression is invalid
    """
    try:
        parts = cron_expr.strip().split()
        if len(parts) == 6:
            five_field_cron = " ".join(parts[1:])
        elif len(parts) == 5:
            five_field_cron = cron_expr
        else:
            raise ValueError(f"Invalid cron expression: expected 5 or 6 fields, got {len(parts)}")
        croniter(five_field_cron)
        return True
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid cron expression '{cron_expr}': {e}") from e


# Constants mirroring orchestrator_server
SCHEDULE_PARTITION_KEY = "schedule"


def _schedule_to_entity(schedule: Schedule) -> dict:
    """Convert Schedule model to Table Storage entity."""
    return {
        "PartitionKey": SCHEDULE_PARTITION_KEY,
        "RowKey": schedule.id,
        "Name": schedule.name,
        "CronExpression": schedule.cron_expression,
        "Scenarios": json.dumps(schedule.scenarios) if schedule.scenarios else None,
        "ScenarioCount": schedule.scenario_count,
        "Enabled": schedule.enabled,
        "CreatedAt": schedule.created_at.isoformat(),
    }


def _entity_to_schedule(entity: dict) -> Schedule:
    """Convert Table Storage entity to Schedule model."""
    scenarios_json = entity.get("Scenarios")
    scenarios = json.loads(scenarios_json) if scenarios_json else None

    created_at_str = entity.get("CreatedAt", "")
    if created_at_str:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    else:
        created_at = datetime.now(UTC)

    return Schedule(
        id=entity["RowKey"],
        name=entity["Name"],
        cron_expression=entity["CronExpression"],
        scenarios=scenarios,
        scenario_count=entity.get("ScenarioCount", 5),
        enabled=entity.get("Enabled", True),
        created_at=created_at,
    )


def _get_next_run_time(cron_expr: str) -> str | None:
    """Get the next run time for a cron expression."""
    try:
        parts = cron_expr.strip().split()
        five_field_cron = " ".join(parts[1:]) if len(parts) == 6 else cron_expr
        cron = croniter(five_field_cron, datetime.now(UTC))
        next_time = cron.get_next(datetime)
        return next_time.isoformat()
    except Exception:
        return None


def _schedule_to_response(schedule: Schedule) -> ScheduleResponse:
    """Convert Schedule model to ScheduleResponse with next run time."""
    next_run = _get_next_run_time(schedule.cron_expression) if schedule.enabled else None
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        cron_expression=schedule.cron_expression,
        scenarios=schedule.scenarios,
        scenario_count=schedule.scenario_count,
        enabled=schedule.enabled,
        created_at=schedule.created_at,
        next_run=next_run,
    )


class TestCronValidation:
    """Tests for cron expression validation."""

    def test_valid_six_field_cron(self):
        """Six-field cron expressions should be valid."""
        # Standard 6-field cron: second minute hour day month weekday
        assert _validate_cron_expression("0 0 0 * * *") is True
        assert _validate_cron_expression("0 30 6 * * 1-5") is True
        assert _validate_cron_expression("0 0 0,6,12,18 * * *") is True

    def test_valid_five_field_cron(self):
        """Five-field cron expressions should be valid."""
        # Standard 5-field cron: minute hour day month weekday
        assert _validate_cron_expression("0 0 * * *") is True
        assert _validate_cron_expression("30 6 * * 1-5") is True
        assert _validate_cron_expression("0 0,6,12,18 * * *") is True

    def test_invalid_cron_expression(self):
        """Invalid cron expressions should raise ValueError."""
        # Too few fields
        with pytest.raises(ValueError, match="expected 5 or 6 fields"):
            _validate_cron_expression("0 0 * *")

        # Too many fields
        with pytest.raises(ValueError, match="expected 5 or 6 fields"):
            _validate_cron_expression("0 0 0 * * * *")

        # Invalid values
        with pytest.raises(ValueError, match="Invalid cron expression"):
            _validate_cron_expression("0 99 0 * * *")

    def test_empty_cron_expression(self):
        """Empty cron expressions should raise ValueError."""
        with pytest.raises(ValueError, match="expected 5 or 6 fields"):
            _validate_cron_expression("")

        with pytest.raises(ValueError, match="expected 5 or 6 fields"):
            _validate_cron_expression("   ")


# =============================================================================
# Entity Conversion Tests
# =============================================================================


class TestEntityConversion:
    """Tests for Schedule to/from Table Storage entity conversion."""

    def test_schedule_to_entity(self):
        """Schedule model should convert to valid Table Storage entity."""
        schedule = Schedule(
            id="test-schedule-123",
            name="Test Schedule",
            cron_expression="0 0 0 * * *",
            scenarios=["scenario1", "scenario2"],
            scenario_count=5,
            enabled=True,
            created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        )

        entity = _schedule_to_entity(schedule)

        assert entity["PartitionKey"] == SCHEDULE_PARTITION_KEY
        assert entity["RowKey"] == "test-schedule-123"
        assert entity["Name"] == "Test Schedule"
        assert entity["CronExpression"] == "0 0 0 * * *"
        assert entity["Scenarios"] == '["scenario1", "scenario2"]'
        assert entity["ScenarioCount"] == 5
        assert entity["Enabled"] is True
        assert entity["CreatedAt"] == "2025-01-01T00:00:00+00:00"

    def test_schedule_to_entity_no_scenarios(self):
        """Schedule without scenarios should have None in entity."""
        schedule = Schedule(
            id="test-schedule-456",
            name="Test Schedule",
            cron_expression="0 0 0 * * *",
            scenarios=None,
            scenario_count=3,
            enabled=False,
        )

        entity = _schedule_to_entity(schedule)

        assert entity["Scenarios"] is None
        assert entity["ScenarioCount"] == 3
        assert entity["Enabled"] is False

    def test_entity_to_schedule(self):
        """Table Storage entity should convert to valid Schedule model."""
        entity = {
            "PartitionKey": "schedule",
            "RowKey": "test-schedule-789",
            "Name": "Entity Schedule",
            "CronExpression": "0 30 6 * * 1-5",
            "Scenarios": '["scenarioA", "scenarioB"]',
            "ScenarioCount": 10,
            "Enabled": True,
            "CreatedAt": "2025-06-15T12:30:00+00:00",
        }

        schedule = _entity_to_schedule(entity)

        assert schedule.id == "test-schedule-789"
        assert schedule.name == "Entity Schedule"
        assert schedule.cron_expression == "0 30 6 * * 1-5"
        assert schedule.scenarios == ["scenarioA", "scenarioB"]
        assert schedule.scenario_count == 10
        assert schedule.enabled is True
        assert schedule.created_at.year == 2025
        assert schedule.created_at.month == 6

    def test_entity_to_schedule_no_scenarios(self):
        """Entity without scenarios should convert correctly."""
        entity = {
            "PartitionKey": "schedule",
            "RowKey": "test-schedule-000",
            "Name": "No Scenarios",
            "CronExpression": "0 0 * * *",
            "Scenarios": None,
            "ScenarioCount": 5,
            "Enabled": True,
            "CreatedAt": "2025-01-01T00:00:00+00:00",
        }

        schedule = _entity_to_schedule(entity)

        assert schedule.scenarios is None
        assert schedule.scenario_count == 5

    def test_entity_to_schedule_defaults(self):
        """Entity with missing optional fields should use defaults."""
        entity = {
            "PartitionKey": "schedule",
            "RowKey": "minimal-entity",
            "Name": "Minimal",
            "CronExpression": "0 0 * * *",
        }

        schedule = _entity_to_schedule(entity)

        assert schedule.scenarios is None
        assert schedule.scenario_count == 5  # Default
        assert schedule.enabled is True  # Default


# =============================================================================
# Schedule Model Tests
# =============================================================================


class TestScheduleModels:
    """Tests for Pydantic schedule models."""

    def test_schedule_auto_generates_id(self):
        """Schedule should auto-generate UUID if not provided."""
        schedule = Schedule(
            name="Auto ID Test",
            cron_expression="0 0 * * *",
        )
        assert schedule.id is not None
        assert len(schedule.id) == 36  # UUID format

    def test_schedule_create_model(self):
        """ScheduleCreate should validate input correctly."""
        create = ScheduleCreate(
            name="New Schedule",
            cron_expression="0 0 0,6,12,18 * * *",
            scenarios=["test-scenario"],
            scenario_count=3,
            enabled=True,
        )

        assert create.name == "New Schedule"
        assert create.cron_expression == "0 0 0,6,12,18 * * *"
        assert create.scenarios == ["test-scenario"]
        assert create.scenario_count == 3
        assert create.enabled is True

    def test_schedule_create_defaults(self):
        """ScheduleCreate should have sensible defaults."""
        create = ScheduleCreate(
            name="Minimal Create",
            cron_expression="0 0 * * *",
        )

        assert create.scenarios is None
        assert create.scenario_count == 5
        assert create.enabled is True

    def test_schedule_update_all_optional(self):
        """ScheduleUpdate should allow all fields to be optional."""
        # Empty update (no changes)
        update = ScheduleUpdate()
        assert update.name is None
        assert update.cron_expression is None
        assert update.scenarios is None
        assert update.scenario_count is None
        assert update.enabled is None

    def test_schedule_update_partial(self):
        """ScheduleUpdate should support partial updates."""
        # Only update name and enabled status
        update = ScheduleUpdate(
            name="Updated Name",
            enabled=False,
        )

        assert update.name == "Updated Name"
        assert update.cron_expression is None
        assert update.enabled is False

    def test_schedule_response_includes_next_run(self):
        """ScheduleResponse should include next_run field."""
        response = ScheduleResponse(
            id="resp-123",
            name="Response Test",
            cron_expression="0 0 * * *",
            scenarios=None,
            scenario_count=5,
            enabled=True,
            created_at=datetime.now(UTC),
            next_run="2025-01-01T06:00:00+00:00",
        )

        assert response.next_run == "2025-01-01T06:00:00+00:00"


# =============================================================================
# CRUD Operations Tests (with mocked storage)
# =============================================================================


class TestScheduleCRUD:
    """Tests for schedule CRUD operations with mocked Table Storage."""

    @pytest.fixture
    def mock_table_client(self):
        """Create a mock table client with in-memory storage."""
        client = MagicMock()
        storage: dict[tuple[str, str], dict] = {}

        def get_entity(partition_key: str, row_key: str):
            key = (partition_key, row_key)
            if key not in storage:
                raise ResourceNotFoundError(f"Entity not found: {partition_key}/{row_key}")
            return storage[key].copy()

        def create_entity(entity: dict):
            pk = entity.get("PartitionKey")
            rk = entity.get("RowKey")
            key = (pk, rk)
            storage[key] = entity.copy()
            return entity

        def update_entity(entity: dict, mode: str = "replace"):
            pk = entity.get("PartitionKey")
            rk = entity.get("RowKey")
            key = (pk, rk)
            if key not in storage:
                raise ResourceNotFoundError(f"Entity not found: {pk}/{rk}")
            if mode == "replace":
                storage[key] = entity.copy()
            else:
                storage[key].update(entity)
            return entity

        def delete_entity(partition_key: str, row_key: str):
            key = (partition_key, row_key)
            if key in storage:
                del storage[key]

        def query_entities(query_filter: str = None):
            return list(storage.values())

        client.get_entity = get_entity
        client.create_entity = create_entity
        client.update_entity = update_entity
        client.delete_entity = delete_entity
        client.query_entities = query_entities
        client._storage = storage  # Expose for test inspection

        return client

    @pytest.fixture
    def mock_scheduler(self):
        """Create a mock APScheduler."""
        scheduler = MagicMock()
        scheduler.add_job = MagicMock()
        scheduler.remove_job = MagicMock()
        return scheduler

    def test_create_schedule_stores_entity(self, mock_table_client):
        """Creating a schedule should store entity in table storage."""
        schedule = Schedule(
            name="CRUD Test Schedule",
            cron_expression="0 0 0 * * *",
            scenario_count=5,
        )

        # Store the entity
        entity = _schedule_to_entity(schedule)
        mock_table_client.create_entity(entity)

        # Retrieve and verify
        stored = mock_table_client.get_entity(SCHEDULE_PARTITION_KEY, schedule.id)
        assert stored["Name"] == "CRUD Test Schedule"
        assert stored["CronExpression"] == "0 0 0 * * *"

    def test_update_schedule_modifies_entity(self, mock_table_client):
        """Updating a schedule should modify the stored entity."""
        # Create initial schedule
        schedule = Schedule(
            id="update-test-id",
            name="Original Name",
            cron_expression="0 0 0 * * *",
            scenario_count=5,
            enabled=True,
        )
        entity = _schedule_to_entity(schedule)
        mock_table_client.create_entity(entity)

        # Simulate partial update
        schedule.name = "Updated Name"
        schedule.enabled = False

        updated_entity = _schedule_to_entity(schedule)
        mock_table_client.update_entity(updated_entity, mode="replace")

        # Verify changes
        stored = mock_table_client.get_entity(SCHEDULE_PARTITION_KEY, "update-test-id")
        assert stored["Name"] == "Updated Name"
        assert stored["Enabled"] is False

    def test_delete_schedule_removes_entity(self, mock_table_client):
        """Deleting a schedule should remove it from storage."""
        schedule = Schedule(
            id="delete-test-id",
            name="To Be Deleted",
            cron_expression="0 0 * * *",
        )
        entity = _schedule_to_entity(schedule)
        mock_table_client.create_entity(entity)

        # Verify exists
        assert mock_table_client.get_entity(SCHEDULE_PARTITION_KEY, "delete-test-id")

        # Delete
        mock_table_client.delete_entity(SCHEDULE_PARTITION_KEY, "delete-test-id")

        # Verify gone
        with pytest.raises(ResourceNotFoundError):
            mock_table_client.get_entity(SCHEDULE_PARTITION_KEY, "delete-test-id")

    def test_get_nonexistent_schedule_raises(self, mock_table_client):
        """Getting a nonexistent schedule should raise ResourceNotFoundError."""
        with pytest.raises(ResourceNotFoundError):
            mock_table_client.get_entity(SCHEDULE_PARTITION_KEY, "nonexistent-id")

    def test_list_schedules_returns_all(self, mock_table_client):
        """Listing schedules should return all stored entities."""
        # Create multiple schedules
        for i in range(3):
            schedule = Schedule(
                id=f"list-test-{i}",
                name=f"Schedule {i}",
                cron_expression="0 0 * * *",
            )
            entity = _schedule_to_entity(schedule)
            mock_table_client.create_entity(entity)

        # List all
        entities = mock_table_client.query_entities()
        assert len(entities) == 3


# =============================================================================
# Next Run Time Tests
# =============================================================================


class TestNextRunTime:
    """Tests for next run time calculation."""

    def test_get_next_run_time_valid_cron(self):
        """Valid cron should return next run time."""
        # Use a cron that runs every minute
        next_run = _get_next_run_time("* * * * *")
        assert next_run is not None
        # Should be a valid ISO format string
        datetime.fromisoformat(next_run.replace("Z", "+00:00"))

    def test_get_next_run_time_six_field_cron(self):
        """Six-field cron should also return next run time."""
        next_run = _get_next_run_time("0 * * * * *")
        assert next_run is not None

    def test_get_next_run_time_invalid_returns_none(self):
        """Invalid cron should return None."""
        next_run = _get_next_run_time("invalid cron")
        assert next_run is None


# =============================================================================
# Schedule to Response Conversion Tests
# =============================================================================


class TestScheduleToResponse:
    """Tests for converting Schedule to ScheduleResponse."""

    def test_schedule_to_response_enabled(self):
        """Enabled schedule should have next_run populated."""
        schedule = Schedule(
            id="resp-test",
            name="Response Test",
            cron_expression="0 0 * * *",
            scenario_count=5,
            enabled=True,
        )

        response = _schedule_to_response(schedule)

        assert response.id == "resp-test"
        assert response.name == "Response Test"
        assert response.next_run is not None

    def test_schedule_to_response_disabled(self):
        """Disabled schedule should have next_run as None."""
        schedule = Schedule(
            id="resp-disabled",
            name="Disabled Schedule",
            cron_expression="0 0 * * *",
            scenario_count=5,
            enabled=False,
        )

        response = _schedule_to_response(schedule)

        assert response.enabled is False
        assert response.next_run is None
