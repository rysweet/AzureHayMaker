"""Tests for WorkflowScheduler - realistic timing and work hours.

This module tests the WorkflowScheduler which:
- Enforces work hours (9 AM - 6 PM by default)
- Skips weekends (Mon-Fri only by default)
- Calculates valid time slots
- Schedules workflows with random distribution
- Handles edge cases (more workflows than time slots)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


class TestWorkflowSchedulerBasics:
    """Tests for WorkflowScheduler basic functionality."""

    def test_scheduler_creation(self):
        """Test creating a WorkflowScheduler."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_42",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),  # Monday 9 AM
        )

        scheduler = WorkflowScheduler(sprint_config)

        assert scheduler.sprint_config == sprint_config
        assert scheduler.work_hours_start == 9
        assert scheduler.work_hours_end == 18

    def test_scheduler_custom_work_hours(self):
        """Test scheduler with custom work hours."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_43",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 8, 0, 0),
            work_hours_start=8,
            work_hours_end=17,
        )

        scheduler = WorkflowScheduler(sprint_config)

        assert scheduler.work_hours_start == 8
        assert scheduler.work_hours_end == 17


class TestWorkHoursEnforcement:
    """Tests for work hours enforcement (9 AM - 6 PM)."""

    def test_is_work_hour_valid(self):
        """Test checking if a time falls within work hours."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_44",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # Valid work hours
        assert scheduler.is_work_hour(datetime(2025, 12, 8, 9, 0, 0)) is True
        assert scheduler.is_work_hour(datetime(2025, 12, 8, 12, 0, 0)) is True
        assert scheduler.is_work_hour(datetime(2025, 12, 8, 17, 59, 0)) is True

        # Invalid work hours
        assert scheduler.is_work_hour(datetime(2025, 12, 8, 8, 59, 0)) is False
        assert scheduler.is_work_hour(datetime(2025, 12, 8, 18, 0, 0)) is False
        assert scheduler.is_work_hour(datetime(2025, 12, 8, 23, 0, 0)) is False

    def test_next_work_hour_same_day(self):
        """Test finding next work hour on same day."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_45",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # Before work hours -> should return 9 AM same day
        result = scheduler.next_work_hour(datetime(2025, 12, 8, 7, 0, 0))
        assert result == datetime(2025, 12, 8, 9, 0, 0)

        # During work hours -> should return same time
        result = scheduler.next_work_hour(datetime(2025, 12, 8, 14, 30, 0))
        assert result == datetime(2025, 12, 8, 14, 30, 0)

    def test_next_work_hour_next_day(self):
        """Test finding next work hour on next day."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_46",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # After work hours -> should return 9 AM next work day
        result = scheduler.next_work_hour(datetime(2025, 12, 8, 19, 0, 0))
        assert result == datetime(2025, 12, 9, 9, 0, 0)  # Tuesday 9 AM


class TestWeekendSkipping:
    """Tests for weekend skipping (Mon-Fri only)."""

    def test_is_work_day_weekdays(self):
        """Test checking if a date is a work day (Mon-Fri)."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_47",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # Weekdays (Mon-Fri)
        assert scheduler.is_work_day(datetime(2025, 12, 8)) is True  # Monday
        assert scheduler.is_work_day(datetime(2025, 12, 9)) is True  # Tuesday
        assert scheduler.is_work_day(datetime(2025, 12, 10)) is True  # Wednesday
        assert scheduler.is_work_day(datetime(2025, 12, 11)) is True  # Thursday
        assert scheduler.is_work_day(datetime(2025, 12, 12)) is True  # Friday

    def test_is_work_day_weekends(self):
        """Test checking if a date is a weekend."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_48",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # Weekend
        assert scheduler.is_work_day(datetime(2025, 12, 13)) is False  # Saturday
        assert scheduler.is_work_day(datetime(2025, 12, 14)) is False  # Sunday

    def test_next_work_day_skip_weekend(self):
        """Test finding next work day skips weekend."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_49",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # Friday evening -> should skip to Monday
        result = scheduler.next_work_hour(datetime(2025, 12, 12, 19, 0, 0))
        assert result == datetime(2025, 12, 15, 9, 0, 0)  # Monday 9 AM

        # Saturday -> should skip to Monday
        result = scheduler.next_work_hour(datetime(2025, 12, 13, 10, 0, 0))
        assert result == datetime(2025, 12, 15, 9, 0, 0)  # Monday 9 AM

        # Sunday -> should skip to Monday
        result = scheduler.next_work_hour(datetime(2025, 12, 14, 10, 0, 0))
        assert result == datetime(2025, 12, 15, 9, 0, 0)  # Monday 9 AM


class TestTimeSlotCalculation:
    """Tests for valid time slot calculation."""

    def test_calculate_time_slots_single_day(self):
        """Test calculating time slots for a single day."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_50",
            duration_days=1,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # 1 day, 9 hours (9 AM - 6 PM), slot duration 1 hour
        time_slots = scheduler.calculate_time_slots(slot_duration_minutes=60)

        assert len(time_slots) == 9  # 9 one-hour slots
        assert time_slots[0] == datetime(2025, 12, 8, 9, 0, 0)
        assert time_slots[-1] == datetime(2025, 12, 8, 17, 0, 0)

    def test_calculate_time_slots_full_week(self):
        """Test calculating time slots for a full work week."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_51",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),  # Monday
        )

        scheduler = WorkflowScheduler(sprint_config)

        # 5 days, 9 hours per day, slot duration 1 hour
        time_slots = scheduler.calculate_time_slots(slot_duration_minutes=60)

        assert len(time_slots) == 45  # 5 days * 9 hours

        # First slot should be Monday 9 AM
        assert time_slots[0] == datetime(2025, 12, 8, 9, 0, 0)

        # Last slot should be Friday 5 PM
        assert time_slots[-1] == datetime(2025, 12, 12, 17, 0, 0)

    def test_calculate_time_slots_with_weekend(self):
        """Test calculating time slots over a weekend (should skip)."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_52",
            duration_days=10,  # 2 calendar weeks
            start_date=datetime(2025, 12, 8, 9, 0, 0),  # Monday
        )

        scheduler = WorkflowScheduler(sprint_config)

        # 10 work days (2 weeks minus weekends), 9 hours per day
        time_slots = scheduler.calculate_time_slots(slot_duration_minutes=60)

        assert len(time_slots) == 90  # 10 days * 9 hours

        # Verify no weekend slots
        for slot in time_slots:
            assert slot.weekday() < 5  # Mon=0, Fri=4

    def test_calculate_time_slots_30_minute_intervals(self):
        """Test calculating time slots with 30-minute intervals."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_53",
            duration_days=1,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # 1 day, 9 hours, 30-minute slots
        time_slots = scheduler.calculate_time_slots(slot_duration_minutes=30)

        assert len(time_slots) == 18  # 9 hours * 2 slots per hour


class TestWorkflowScheduling:
    """Tests for workflow scheduling with random distribution."""

    def test_schedule_workflows_basic(self):
        """Test scheduling workflows within time slots."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig
        from azure_haymaker.engineering_sim.workflow import Workflow

        sprint_config = SprintConfig(
            sprint_id="sprint_54",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # Create mock workflows
        workflows = [
            Mock(spec=Workflow, name=f"workflow_{i}", estimate_duration=Mock(return_value=300.0))
            for i in range(5)
        ]

        scheduled = scheduler.schedule_workflows(workflows)

        assert len(scheduled) == 5
        for item in scheduled:
            assert hasattr(item, "workflow")
            assert hasattr(item, "scheduled_time")
            assert item.scheduled_time.hour >= 9
            assert item.scheduled_time.hour < 18
            assert item.scheduled_time.weekday() < 5  # Mon-Fri

    def test_schedule_workflows_random_distribution(self):
        """Test workflows are randomly distributed across time slots."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig
        from azure_haymaker.engineering_sim.workflow import Workflow

        sprint_config = SprintConfig(
            sprint_id="sprint_55",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # Create many workflows
        workflows = [
            Mock(spec=Workflow, name=f"workflow_{i}", estimate_duration=Mock(return_value=300.0))
            for i in range(20)
        ]

        scheduled = scheduler.schedule_workflows(workflows)

        # Extract scheduled times
        scheduled_times = [item.scheduled_time for item in scheduled]

        # Verify some distribution (not all at same time)
        unique_times = set(scheduled_times)
        assert len(unique_times) > 1

        # Verify all times are in work hours
        for time in scheduled_times:
            assert time.hour >= 9
            assert time.hour < 18

    def test_schedule_workflows_respects_order(self):
        """Test scheduled workflows maintain relative order."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig
        from azure_haymaker.engineering_sim.workflow import Workflow

        sprint_config = SprintConfig(
            sprint_id="sprint_56",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        workflows = [
            Mock(spec=Workflow, name=f"workflow_{i}", estimate_duration=Mock(return_value=300.0))
            for i in range(5)
        ]

        scheduled = scheduler.schedule_workflows(workflows)

        # Verify workflows are scheduled in chronological order
        scheduled_times = [item.scheduled_time for item in scheduled]
        assert scheduled_times == sorted(scheduled_times)


class TestWorkflowSchedulingEdgeCases:
    """Tests for edge cases in workflow scheduling."""

    def test_schedule_more_workflows_than_time_slots(self):
        """Test scheduling when there are more workflows than time slots."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig
        from azure_haymaker.engineering_sim.workflow import Workflow

        sprint_config = SprintConfig(
            sprint_id="sprint_57",
            duration_days=1,  # Only 1 day
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        # Try to schedule 20 workflows in 1 day (only 9 hours available)
        workflows = [
            Mock(spec=Workflow, name=f"workflow_{i}", estimate_duration=Mock(return_value=300.0))
            for i in range(20)
        ]

        scheduled = scheduler.schedule_workflows(workflows)

        # Should schedule all workflows (may reuse time slots)
        assert len(scheduled) == 20

        # All should be on the same day
        for item in scheduled:
            assert item.scheduled_time.date() == datetime(2025, 12, 8).date()

    def test_schedule_zero_workflows(self):
        """Test scheduling with zero workflows."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        sprint_config = SprintConfig(
            sprint_id="sprint_58",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        scheduled = scheduler.schedule_workflows([])

        assert len(scheduled) == 0

    def test_schedule_workflows_single_workflow(self):
        """Test scheduling a single workflow."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig
        from azure_haymaker.engineering_sim.workflow import Workflow

        sprint_config = SprintConfig(
            sprint_id="sprint_59",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        workflows = [
            Mock(spec=Workflow, name="single_workflow", estimate_duration=Mock(return_value=300.0))
        ]

        scheduled = scheduler.schedule_workflows(workflows)

        assert len(scheduled) == 1
        assert scheduled[0].workflow.name == "single_workflow"
        # Should be scheduled during work hours
        assert 9 <= scheduled[0].scheduled_time.hour < 18


class TestSchedulingWithPhases:
    """Tests for scheduling workflows across sprint phases."""

    def test_schedule_by_phase_planning(self):
        """Test scheduling planning phase (10% of time)."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_60",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        phase_time_slots = scheduler.calculate_phase_time_slots(SprintPhase.PLANNING)

        # Planning is 10% of 10 days = 1 day = 9 hours
        assert len(phase_time_slots) == 9  # Assuming 1-hour slots

    def test_schedule_by_phase_development(self):
        """Test scheduling development phase (70% of time)."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_61",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        phase_time_slots = scheduler.calculate_phase_time_slots(SprintPhase.DEVELOPMENT)

        # Development is 70% of 10 days = 7 days = 63 hours
        assert len(phase_time_slots) == 63  # Assuming 1-hour slots

    def test_schedule_by_phase_code_freeze(self):
        """Test scheduling code freeze phase (15% of time)."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_62",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        phase_time_slots = scheduler.calculate_phase_time_slots(SprintPhase.CODE_FREEZE)

        # Code freeze is 15% of 10 days = 1.5 days = ~13.5 hours
        assert 13 <= len(phase_time_slots) <= 14  # Rounding variance

    def test_schedule_by_phase_retrospective(self):
        """Test scheduling retrospective phase (5% of time)."""
        from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
            WorkflowScheduler,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_63",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        scheduler = WorkflowScheduler(sprint_config)

        phase_time_slots = scheduler.calculate_phase_time_slots(SprintPhase.RETROSPECTIVE)

        # Retrospective is 5% of 10 days = 0.5 days = ~4.5 hours
        assert 4 <= len(phase_time_slots) <= 5  # Rounding variance
