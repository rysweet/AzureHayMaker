"""Schedule models for orchestration runs.

Defines the Schedule model for configuring recurring orchestration executions
using cron expressions. Schedules are persisted in Azure Table Storage.
"""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Schedule(BaseModel):
    """Configuration for a scheduled orchestration run.

    Schedules define when and how orchestration runs should execute automatically.
    Uses cron expressions for flexible timing configuration.

    Example:
        >>> schedule = Schedule(
        ...     name="Daily Morning Run",
        ...     cron_expression="0 0 0,6,12,18 * * *",
        ...     scenario_count=5,
        ... )
        >>> print(schedule.id)  # Auto-generated UUID
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique schedule identifier",
    )
    name: str = Field(
        ...,
        description="Human-readable schedule name",
        min_length=1,
        max_length=100,
    )
    cron_expression: str = Field(
        ...,
        description="Cron expression for scheduling (5 or 6 fields supported)",
    )
    scenarios: list[str] | None = Field(
        default=None,
        description="Specific scenarios to run (None = random selection based on simulation size)",
    )
    scenario_count: int = Field(
        default=5,
        description="Number of scenarios to run when using random selection",
        ge=1,
        le=30,
    )
    enabled: bool = Field(
        default=True,
        description="Whether the schedule is active",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Schedule creation timestamp",
    )

    # Health check and quarantine fields (Milestone 1: Issue #129)
    quarantined: bool = Field(
        default=False,
        description="Whether the schedule is quarantined due to failures",
    )
    quarantined_at: datetime | None = Field(
        default=None,
        description="Timestamp when schedule was quarantined",
    )
    quarantine_reason: str | None = Field(
        default=None,
        description="Reason for quarantine (e.g., 'Exceeded failure threshold')",
    )
    failure_count_24h: int = Field(
        default=0,
        description="Number of failures in the last 24 hours",
        ge=0,
    )
    last_failure_at: datetime | None = Field(
        default=None,
        description="Timestamp of most recent failure",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Daily 4x Run",
                "cron_expression": "0 0 0,6,12,18 * * *",
                "scenarios": None,
                "scenario_count": 5,
                "enabled": True,
                "created_at": "2025-11-25T00:00:00+00:00",
                "quarantined": False,
                "quarantined_at": None,
                "quarantine_reason": None,
                "failure_count_24h": 0,
                "last_failure_at": None,
            }
        }


class ScheduleCreate(BaseModel):
    """Request model for creating a new schedule.

    Example:
        >>> create_req = ScheduleCreate(
        ...     name="Hourly Check",
        ...     cron_expression="0 0 * * * *",
        ...     scenario_count=3,
        ... )
    """

    name: str = Field(
        ...,
        description="Human-readable schedule name",
        min_length=1,
        max_length=100,
    )
    cron_expression: str = Field(
        ...,
        description="Cron expression for scheduling (5 or 6 fields supported)",
    )
    scenarios: list[str] | None = Field(
        default=None,
        description="Specific scenarios to run (None = random selection)",
    )
    scenario_count: int = Field(
        default=5,
        description="Number of scenarios to run when using random selection",
        ge=1,
        le=30,
    )
    enabled: bool = Field(
        default=True,
        description="Whether the schedule is active",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "Daily 4x Run",
                "cron_expression": "0 0 0,6,12,18 * * *",
                "scenario_count": 5,
                "enabled": True,
            }
        }


class ScheduleUpdate(BaseModel):
    """Request model for updating an existing schedule.

    All fields are optional to allow partial updates.

    Example:
        >>> update_req = ScheduleUpdate(
        ...     name="Updated Name",
        ...     enabled=False,
        ... )
    """

    name: str | None = Field(
        default=None,
        description="Human-readable schedule name",
        min_length=1,
        max_length=100,
    )
    cron_expression: str | None = Field(
        default=None,
        description="Cron expression for scheduling (5 or 6 fields supported)",
    )
    scenarios: list[str] | None = Field(
        default=None,
        description="Specific scenarios to run (None = keep existing)",
    )
    scenario_count: int | None = Field(
        default=None,
        description="Number of scenarios to run when using random selection",
        ge=1,
        le=30,
    )
    enabled: bool | None = Field(
        default=None,
        description="Whether the schedule is active",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "Updated Schedule Name",
                "enabled": False,
            }
        }


class ScheduleResponse(BaseModel):
    """Response model for schedule operations.

    Example:
        >>> response = ScheduleResponse(
        ...     id="550e8400-e29b-41d4-a716-446655440000",
        ...     name="Daily Run",
        ...     cron_expression="0 0 0,6,12,18 * * *",
        ...     scenario_count=5,
        ...     enabled=True,
        ...     created_at=datetime.now(UTC),
        ...     next_run="2025-11-25T06:00:00+00:00",
        ... )
    """

    id: str = Field(..., description="Unique schedule identifier")
    name: str = Field(..., description="Human-readable schedule name")
    cron_expression: str = Field(..., description="Cron expression for scheduling")
    scenarios: list[str] | None = Field(default=None, description="Specific scenarios to run")
    scenario_count: int = Field(..., description="Number of scenarios to run")
    enabled: bool = Field(..., description="Whether the schedule is active")
    created_at: datetime = Field(..., description="Schedule creation timestamp")
    next_run: str | None = Field(default=None, description="Next scheduled run time (ISO format)")

    # Health check and quarantine fields (Milestone 1: Issue #129)
    quarantined: bool = Field(
        default=False,
        description="Whether the schedule is quarantined due to failures",
    )
    quarantined_at: datetime | None = Field(
        default=None,
        description="Timestamp when schedule was quarantined",
    )
    quarantine_reason: str | None = Field(
        default=None,
        description="Reason for quarantine",
    )
    failure_count_24h: int = Field(
        default=0,
        description="Number of failures in the last 24 hours",
    )
    last_failure_at: datetime | None = Field(
        default=None,
        description="Timestamp of most recent failure",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Daily 4x Run",
                "cron_expression": "0 0 0,6,12,18 * * *",
                "scenarios": None,
                "scenario_count": 5,
                "enabled": True,
                "created_at": "2025-11-25T00:00:00+00:00",
                "next_run": "2025-11-25T06:00:00+00:00",
                "quarantined": False,
                "quarantined_at": None,
                "quarantine_reason": None,
                "failure_count_24h": 0,
                "last_failure_at": None,
            }
        }

__all__ = [
    "Schedule",
    "ScheduleCreate",
    "ScheduleResponse",
    "ScheduleUpdate",
]
