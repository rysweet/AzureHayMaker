"""Execution models for orchestration runs."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Status of orchestration execution."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class ExecutionPhase(str, Enum):
    """Phase of orchestration execution."""

    VALIDATION = "validation"
    SELECTION = "selection"
    PROVISIONING = "provisioning"
    MONITORING = "monitoring"
    CLEANUP = "cleanup"
    REPORTING = "reporting"
    COMPLETED = "completed"


class ExecutionError(BaseModel):
    """Error that occurred during execution."""

    timestamp: datetime = Field(..., description="When the error occurred")
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    scenario_name: str | None = Field(default=None, description="Scenario where error occurred")
    phase: ExecutionPhase | None = Field(default=None, description="Phase where error occurred")
    details: dict[str, str] | None = Field(default=None, description="Additional error context")

    class Config:
        """Pydantic configuration."""

        use_enum_values = False


class CleanupVerification(BaseModel):
    """Results of cleanup verification."""

    expected_deleted: int = Field(..., description="Number of resources expected to be deleted")
    actually_deleted: int = Field(..., description="Number of resources confirmed deleted")
    forced_deletions: int = Field(
        ..., description="Number of resources force-deleted by orchestrator"
    )
    deletion_failures: int = Field(..., description="Number of resources that failed to delete")

    @property
    def all_cleaned(self) -> bool:
        """Check if all resources were successfully cleaned up."""
        return self.deletion_failures == 0


class ResourceDeletion(BaseModel):
    """Details of a resource deletion attempt."""

    resource_id: str = Field(..., description="Azure resource ID")
    resource_type: str = Field(..., description="Azure resource type")
    status: str = Field(..., description="Deletion status (deleted or failed)")
    attempts: int = Field(..., description="Number of deletion attempts", ge=1)
    deleted_at: datetime | None = Field(default=None, description="Successful deletion timestamp")
    error: str | None = Field(default=None, description="Error message if failed")


class CleanupReport(BaseModel):
    """Complete cleanup report for an execution run."""

    run_id: str = Field(..., description="Execution run ID")
    total_resources_expected: int = Field(..., description="Total resources that should be deleted")
    total_resources_deleted: int = Field(..., description="Total resources successfully deleted")
    deletions: list[ResourceDeletion] = Field(
        default_factory=list, description="Detailed deletion records"
    )
    service_principals_deleted: list[str] = Field(
        default_factory=list, description="Service principals that were deleted"
    )

    def has_failures(self) -> bool:
        """Check if any deletions failed."""
        return any(d.status == "failed" for d in self.deletions)


class ExecutionRun(BaseModel):
    """Complete execution run metadata."""

    run_id: str = Field(..., description="Unique execution run ID")
    started_at: datetime = Field(..., description="Execution start time")
    ended_at: datetime | None = Field(default=None, description="Execution end time")

    status: ExecutionStatus = Field(default=ExecutionStatus.RUNNING, description="Current status")
    phase: ExecutionPhase = Field(default=ExecutionPhase.VALIDATION, description="Current phase")

    simulation_size: str = Field(..., description="Simulation size (small/medium/large)")
    scenarios_count: int = Field(..., description="Total number of scenarios")
    scenarios_completed: int = Field(default=0, description="Number of completed scenarios")
    scenarios_failed: int = Field(default=0, description="Number of failed scenarios")

    total_resources: int = Field(default=0, description="Total resources created")
    total_service_principals: int = Field(default=0, description="Total service principals created")

    cleanup_verification: CleanupVerification | None = Field(
        default=None, description="Cleanup verification results"
    )

    errors: list[ExecutionError] = Field(default_factory=list, description="Errors encountered")

    class Config:
        """Pydantic configuration."""

        use_enum_values = False
        validate_assignment = True
