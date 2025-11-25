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
        description="Cron expression for scheduling (6 fields: second minute hour day month weekday)",
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
        description="Cron expression for scheduling (6 fields: second minute hour day month weekday)",
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
            }
        }
