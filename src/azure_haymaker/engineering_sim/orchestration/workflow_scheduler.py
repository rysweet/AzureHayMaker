"""Workflow scheduler with realistic timing and work hours enforcement.

This module provides scheduling logic for workflows within sprints:
- Enforces work hours (9 AM - 6 PM by default)
- Skips weekends (Mon-Fri only by default)
- Calculates valid time slots within work hours
- Schedules workflows with random distribution
- Supports phase-based scheduling with percentage allocation
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from azure_haymaker.engineering_sim.orchestration.types import SprintConfig, SprintPhase
from azure_haymaker.engineering_sim.workflow import Workflow


@dataclass
class ScheduledWorkflow:
    """A workflow scheduled for execution at a specific time.

    Args:
        workflow: The workflow to execute
        scheduled_time: The time when workflow should start
    """
    workflow: Workflow
    scheduled_time: datetime


class WorkflowScheduler:
    """Scheduler for workflows within sprint time constraints.

    This scheduler enforces realistic work hours and weekday constraints,
    and distributes workflows across available time slots.

    Args:
        sprint_config: Sprint configuration with timing constraints
    """

    def __init__(self, sprint_config: SprintConfig):
        self.sprint_config = sprint_config
        self.work_hours_start = sprint_config.work_hours_start
        self.work_hours_end = sprint_config.work_hours_end
        self.work_days = sprint_config.work_days

    def is_work_hour(self, dt: datetime) -> bool:
        """Check if a datetime falls within work hours.

        Args:
            dt: Datetime to check

        Returns:
            True if within work hours, False otherwise
        """
        return self.work_hours_start <= dt.hour < self.work_hours_end

    def is_work_day(self, dt: datetime) -> bool:
        """Check if a date is a work day.

        Args:
            dt: Datetime to check

        Returns:
            True if a work day (Mon-Fri by default), False otherwise
        """
        return dt.weekday() in self.work_days

    def next_work_hour(self, dt: datetime) -> datetime:
        """Find the next work hour from a given datetime.

        Args:
            dt: Starting datetime

        Returns:
            Next datetime that falls within work hours
        """
        # If already in work hours and work day, return as-is
        if self.is_work_day(dt) and self.is_work_hour(dt):
            return dt

        # If before work hours today and is work day, return start of work
        if self.is_work_day(dt) and dt.hour < self.work_hours_start:
            return dt.replace(hour=self.work_hours_start, minute=0, second=0)

        # Otherwise, advance to next work day start
        next_day = dt + timedelta(days=1)
        next_day = next_day.replace(hour=self.work_hours_start, minute=0, second=0)

        # Keep advancing until we find a work day
        while not self.is_work_day(next_day):
            next_day += timedelta(days=1)

        return next_day

    def calculate_time_slots(
        self,
        slot_duration_minutes: int = 60,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[datetime]:
        """Calculate all valid time slots within the sprint.

        Args:
            slot_duration_minutes: Duration of each time slot in minutes
            start_time: Optional custom start time (defaults to sprint start)
            end_time: Optional custom end time (defaults to sprint end)

        Returns:
            List of datetime objects representing available time slots
        """
        slots = []
        current = start_time or self.sprint_config.start_date
        end = end_time or self.sprint_config.end_date

        # Ensure we start in work hours
        current = self.next_work_hour(current)

        while current < end:
            # Add slot if in work hours and work day
            if self.is_work_day(current) and self.is_work_hour(current):
                slots.append(current)

            # Advance by slot duration
            current += timedelta(minutes=slot_duration_minutes)

            # Skip to next work hour if we've gone past work hours
            if not self.is_work_hour(current) or not self.is_work_day(current):
                current = self.next_work_hour(current)

        return slots

    def calculate_phase_time_slots(
        self,
        phase: SprintPhase,
        slot_duration_minutes: int = 60,
    ) -> list[datetime]:
        """Calculate time slots for a specific sprint phase.

        Args:
            phase: Sprint phase
            slot_duration_minutes: Duration of each time slot in minutes

        Returns:
            List of datetime objects for this phase
        """
        # Calculate total sprint hours
        total_slots = self.calculate_time_slots(slot_duration_minutes=slot_duration_minutes)
        total_hours = len(total_slots)

        # Calculate hours for each phase based on percentage (use round for better accuracy)
        planning_hours = round(total_hours * SprintPhase.PLANNING.percentage)
        development_hours = round(total_hours * SprintPhase.DEVELOPMENT.percentage)
        code_freeze_hours = round(total_hours * SprintPhase.CODE_FREEZE.percentage)
        retrospective_hours = round(total_hours * SprintPhase.RETROSPECTIVE.percentage)

        # Determine phase boundaries
        if phase == SprintPhase.PLANNING:
            # First 10%
            return total_slots[:planning_hours]
        elif phase == SprintPhase.DEVELOPMENT:
            # After planning (10%) for 70%
            start_idx = planning_hours
            return total_slots[start_idx:start_idx + development_hours]
        elif phase == SprintPhase.CODE_FREEZE:
            # After planning + development (80% total)
            start_idx = planning_hours + development_hours
            return total_slots[start_idx:start_idx + code_freeze_hours]
        elif phase == SprintPhase.RETROSPECTIVE:
            # Last 5%
            start_idx = planning_hours + development_hours + code_freeze_hours
            return total_slots[start_idx:start_idx + retrospective_hours]

        return []

    def schedule_workflows(
        self,
        workflows: list[Workflow],
        time_slots: list[datetime] | None = None,
    ) -> list[ScheduledWorkflow]:
        """Schedule workflows across available time slots.

        Workflows are randomly distributed across time slots and then
        sorted chronologically.

        Args:
            workflows: List of workflows to schedule
            time_slots: Optional custom time slots (defaults to all sprint slots)

        Returns:
            List of ScheduledWorkflow objects in chronological order
        """
        if not workflows:
            return []

        # Get available time slots
        slots = time_slots or self.calculate_time_slots()

        if not slots:
            # No slots available, schedule all at sprint start
            return [
                ScheduledWorkflow(workflow=wf, scheduled_time=self.sprint_config.start_date)
                for wf in workflows
            ]

        # Randomly assign workflows to time slots
        scheduled = []
        for workflow in workflows:
            # Pick a random slot
            scheduled_time = random.choice(slots)
            scheduled.append(ScheduledWorkflow(workflow=workflow, scheduled_time=scheduled_time))

        # Sort by scheduled time
        scheduled.sort(key=lambda x: x.scheduled_time)

        return scheduled

    def estimate_phase_duration(self, phase: SprintPhase) -> float:
        """Estimate the duration of a phase in seconds.

        Args:
            phase: Sprint phase

        Returns:
            Estimated duration in seconds
        """
        # Calculate total sprint duration in work hours
        total_slots = self.calculate_time_slots(slot_duration_minutes=60)
        total_hours = len(total_slots)

        # Calculate phase hours based on percentage
        phase_hours = total_hours * phase.percentage

        # Convert to seconds
        return phase_hours * 3600.0
