"""Activity models for Knowledge Worker Activity Framework.

Defines data structures for activity specifications and results,
tracking what workers do and the outcomes of their activities.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    """Types of M365 activities workers can perform."""

    # Email activities
    EMAIL_SEND = "email_send"
    EMAIL_READ = "email_read"
    EMAIL_REPLY = "email_reply"
    EMAIL_FORWARD = "email_forward"
    EMAIL_ORGANIZE = "email_organize"

    # Teams activities
    TEAMS_CHANNEL_POST = "teams_channel_post"
    TEAMS_CHAT_MESSAGE = "teams_chat_message"
    TEAMS_REPLY = "teams_reply"
    TEAMS_REACT = "teams_react"

    # Document activities
    DOCUMENT_CREATE = "document_create"
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_SHARE = "document_share"
    DOCUMENT_DOWNLOAD = "document_download"

    # Calendar activities
    CALENDAR_CREATE_EVENT = "calendar_create_event"
    CALENDAR_RESPOND = "calendar_respond"
    CALENDAR_UPDATE = "calendar_update"
    CALENDAR_CANCEL = "calendar_cancel"


class ActivityStatus(str, Enum):
    """Status of an activity execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # e.g., external recipient blocked


class ActivitySpec(BaseModel):
    """Specification for a planned activity.

    Describes what activity to perform and when.

    Attributes:
        activity_id: Unique identifier for this activity
        activity_type: Type of M365 activity
        worker_id: Worker who will perform the activity
        scheduled_at: When the activity is scheduled to execute
        parameters: Activity-specific parameters
        priority: Activity priority (0-10, higher = more important)
    """

    activity_id: str = Field(default="", description="Unique activity identifier")
    activity_type: ActivityType = Field(..., description="Type of activity")
    worker_id: str = Field(..., description="Worker performing the activity")
    scheduled_at: datetime | None = Field(default=None, description="Scheduled execution time")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Activity-specific parameters"
    )
    priority: int = Field(default=5, ge=0, le=10, description="Activity priority")

    model_config = {
        "use_enum_values": False,
        "validate_assignment": True,
    }


class ActivityResult(BaseModel):
    """Result of an executed activity.

    Records the outcome of an activity execution including
    success/failure status, timing, and any output.

    Attributes:
        activity_id: ID of the activity that was executed
        activity_type: Type of activity that was executed
        worker_id: Worker who performed the activity
        status: Execution status
        started_at: When execution started
        completed_at: When execution completed
        duration_ms: Execution duration in milliseconds
        output: Activity-specific output data
        error_message: Error message if activity failed
        blocked_reason: Reason if activity was blocked
    """

    activity_id: str = Field(..., description="Activity identifier")
    activity_type: ActivityType = Field(..., description="Type of activity")
    worker_id: str = Field(..., description="Worker who performed activity")
    status: ActivityStatus = Field(..., description="Execution status")

    started_at: datetime = Field(..., description="Execution start time")
    completed_at: datetime | None = Field(default=None, description="Execution completion time")
    duration_ms: int = Field(default=0, ge=0, description="Duration in milliseconds")

    output: dict[str, Any] = Field(default_factory=dict, description="Activity output data")
    error_message: str | None = Field(default=None, description="Error message if failed")
    blocked_reason: str | None = Field(default=None, description="Reason if blocked")

    model_config = {
        "use_enum_values": False,
        "validate_assignment": True,
    }

    @property
    def is_success(self) -> bool:
        """Check if the activity completed successfully."""
        return self.status == ActivityStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        """Check if the activity failed."""
        return self.status == ActivityStatus.FAILED

    @property
    def is_blocked(self) -> bool:
        """Check if the activity was blocked."""
        return self.status == ActivityStatus.BLOCKED


class ActivityReport(BaseModel):
    """Aggregated report of worker activities.

    Summarizes activities performed by a worker over a time period.

    Attributes:
        worker_id: Worker this report is for
        start_time: Report period start
        end_time: Report period end
        total_activities: Total number of activities attempted
        successful_count: Number of successful activities
        failed_count: Number of failed activities
        blocked_count: Number of blocked activities
        activities_by_type: Count of activities by type
        results: List of individual activity results
    """

    worker_id: str = Field(..., description="Worker identifier")
    start_time: datetime = Field(..., description="Report period start")
    end_time: datetime | None = Field(default=None, description="Report period end")

    total_activities: int = Field(default=0, ge=0)
    successful_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    blocked_count: int = Field(default=0, ge=0)

    activities_by_type: dict[str, int] = Field(default_factory=dict)
    results: list[ActivityResult] = Field(default_factory=list)

    model_config = {
        "validate_assignment": True,
    }

    def record_result(self, result: ActivityResult) -> None:
        """Record an activity result in the report.

        Args:
            result: Activity result to record
        """
        self.results.append(result)
        self.total_activities += 1

        # Update status counts
        if result.is_success:
            self.successful_count += 1
        elif result.is_failure:
            self.failed_count += 1
        elif result.is_blocked:
            self.blocked_count += 1

        # Update type counts
        activity_type_str = result.activity_type.value
        self.activities_by_type[activity_type_str] = (
            self.activities_by_type.get(activity_type_str, 0) + 1
        )

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of activities."""
        if self.total_activities == 0:
            return 0.0
        return self.successful_count / self.total_activities
