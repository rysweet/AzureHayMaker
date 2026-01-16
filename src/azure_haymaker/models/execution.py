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


# ==============================================================================
# ON-DEMAND EXECUTION MODELS
# ==============================================================================


class OnDemandExecutionStatus(str, Enum):
    """Status of on-demand execution request."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionRequest(BaseModel):
    """Request to execute scenarios on-demand."""

    scenarios: list[str] = Field(
        ...,
        description="List of scenario names to execute (1-5 scenarios)",
        min_length=1,
        max_length=5,
    )
    duration_hours: int = Field(
        default=8,
        description="Execution duration in hours",
        ge=1,
        le=24,
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Optional tags for tracking",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "scenarios": ["compute-01-linux-vm-web-server", "networking-01-virtual-network"],
                "duration_hours": 2,
                "tags": {"requester": "user@example.com"},
            }
        }


class ExecutionResponse(BaseModel):
    """Response for execution request."""

    execution_id: str = Field(..., description="Unique execution ID")
    status: OnDemandExecutionStatus = Field(..., description="Current execution status")
    scenarios: list[str] = Field(..., description="Scenarios queued for execution")
    estimated_completion: datetime = Field(..., description="Estimated completion time")
    created_at: datetime = Field(..., description="Request creation time")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ExecutionStatusResponse(BaseModel):
    """Detailed execution status response."""

    execution_id: str = Field(..., description="Unique execution ID")
    status: OnDemandExecutionStatus = Field(..., description="Current execution status")
    scenarios: list[str] = Field(..., description="Scenarios in execution")
    created_at: datetime = Field(..., description="Request creation time")
    started_at: datetime | None = Field(default=None, description="Execution start time")
    completed_at: datetime | None = Field(default=None, description="Execution completion time")
    progress: dict[str, int] | None = Field(
        default=None,
        description="Execution progress (completed, running, failed, total)",
    )
    resources_created: int = Field(default=0, description="Total resources created")
    container_ids: list[str] = Field(default_factory=list, description="Container App IDs")
    report_url: str | None = Field(default=None, description="Execution report URL")
    error: str | None = Field(default=None, description="Error message if failed")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ExecutionRecord(BaseModel):
    """Internal execution record stored in Table Storage."""

    execution_id: str = Field(..., description="Unique execution ID (PartitionKey)")
    timestamp: datetime = Field(..., description="Record timestamp (RowKey)")
    status: OnDemandExecutionStatus = Field(..., description="Current status")
    scenarios: list[str] = Field(..., description="Scenarios to execute")
    duration_hours: int = Field(..., description="Execution duration")
    tags: dict[str, str] = Field(default_factory=dict, description="User tags")
    container_ids: list[str] = Field(default_factory=list, description="Container App IDs")
    resources_created: int = Field(default=0, description="Total resources created")
    error_message: str | None = Field(default=None, description="Error message if failed")
    report_url: str | None = Field(default=None, description="Report URL when complete")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


# ==============================================================================
# ANALYTICS MODELS
# ==============================================================================


class ScenarioStats(BaseModel):
    """Statistics for a single scenario."""

    name: str = Field(..., description="Scenario name")
    count: int = Field(..., description="Execution count")
    success_rate: float = Field(..., description="Success rate (0.0-1.0)")


class ExecutionCounts(BaseModel):
    """Execution counts by status."""

    total: int = Field(..., description="Total executions")
    succeeded: int = Field(..., description="Successful executions")
    failed: int = Field(..., description="Failed executions")


class AnalyticsSummary(BaseModel):
    """Analytics summary for dashboard display."""

    period: str = Field(..., description="Time period (e.g., '7d', '30d', '90d')")
    executions: ExecutionCounts = Field(..., description="Execution counts by status")
    success_rate: float = Field(..., description="Overall success rate (0.0-1.0)")
    avg_duration_hours: float = Field(..., description="Average execution duration in hours")
    top_scenarios: list[ScenarioStats] = Field(
        default_factory=list, description="Top 10 scenarios by execution count"
    )


# ==============================================================================
# MULTI-TENANT EXECUTION MODELS (Phase 3)
# ==============================================================================


class MultiTenantFailureMode(str, Enum):
    """Controls behavior when a tenant execution fails."""

    CONTINUE = "continue"  # Continue with remaining tenants
    FAIL_FAST = "fail_fast"  # Stop on first failure


class MultiTenantExecutionRequest(BaseModel):
    """Request to execute orchestration across multiple tenants.

    Example:
        >>> request = MultiTenantExecutionRequest(
        ...     tenant_ids=["tenant-1", "tenant-2"],
        ...     scenarios=["compute-01-linux-vm"],
        ...     max_parallelism=5,
        ... )
    """

    tenant_ids: list[str] = Field(
        ...,
        description="List of tenant IDs to execute on (must be in registry)",
        min_length=1,
    )
    scenarios: list[str] | None = Field(
        default=None,
        description="Specific scenarios to run (None = use default selection)",
    )
    scenario_count: int | None = Field(
        default=None,
        description="Number of scenarios to select if scenarios not specified",
        ge=1,
        le=30,
    )
    duration_hours: int = Field(
        default=8,
        description="Execution duration in hours per tenant",
        ge=1,
        le=24,
    )
    max_parallelism: int = Field(
        default=10,
        description="Maximum number of tenants to execute in parallel",
        ge=1,
        le=50,
    )
    failure_mode: MultiTenantFailureMode = Field(
        default=MultiTenantFailureMode.CONTINUE,
        description="How to handle tenant execution failures",
    )
    skip_validation: bool = Field(
        default=False,
        description="Skip environment validation for each tenant",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Optional tags for tracking",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_schema_extra = {
            "example": {
                "tenant_ids": ["tenant-abc-123", "tenant-def-456"],
                "scenarios": ["compute-01-linux-vm-web-server"],
                "duration_hours": 8,
                "max_parallelism": 10,
                "failure_mode": "continue",
            }
        }


class TenantExecutionStatusEnum(str, Enum):
    """State of execution for a single tenant."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TenantExecutionDetail(BaseModel):
    """Execution status for a single tenant within a multi-tenant execution."""

    tenant_id: str = Field(..., description="Azure tenant ID")
    tenant_display_name: str | None = Field(
        default=None, description="Human-readable tenant name"
    )
    status: TenantExecutionStatusEnum = Field(
        default=TenantExecutionStatusEnum.PENDING,
        description="Current execution state",
    )
    execution_id: str | None = Field(
        default=None, description="Per-tenant execution ID"
    )
    started_at: datetime | None = Field(default=None, description="Execution start time")
    completed_at: datetime | None = Field(default=None, description="Execution end time")
    error_message: str | None = Field(
        default=None, description="Error message if execution failed"
    )
    scenarios_completed: int = Field(default=0, description="Scenarios completed")
    scenarios_failed: int = Field(default=0, description="Scenarios that failed")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class MultiTenantExecutionResponse(BaseModel):
    """Response for multi-tenant execution request.

    Example:
        >>> response = MultiTenantExecutionResponse(
        ...     meta_execution_id="abc-123",
        ...     status="running",
        ...     total_tenants=5,
        ...     tenant_statuses=[...],
        ... )
    """

    meta_execution_id: str = Field(..., description="Unique ID for this meta-execution")
    status: str = Field(..., description="Overall execution status")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: datetime | None = Field(default=None, description="Execution end time")
    total_tenants: int = Field(..., description="Total number of tenants")
    succeeded_count: int = Field(default=0, description="Tenants that succeeded")
    failed_count: int = Field(default=0, description="Tenants that failed")
    skipped_count: int = Field(default=0, description="Tenants skipped")
    tenant_statuses: list[TenantExecutionDetail] = Field(
        default_factory=list,
        description="Status for each tenant",
    )
    failure_mode: MultiTenantFailureMode = Field(
        default=MultiTenantFailureMode.CONTINUE,
        description="Failure mode used",
    )
    aborted_early: bool = Field(
        default=False,
        description="True if stopped early due to FAIL_FAST",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
