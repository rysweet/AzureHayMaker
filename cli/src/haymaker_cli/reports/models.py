"""Report data models for Azure HayMaker CLI."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ReportFilters(BaseModel):
    """Report filter criteria.

    Defines filters for selecting data in reports.
    """

    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    scenario_ids: Optional[List[str]] = Field(None, description="List of scenario IDs to include")
    status: Optional[List[str]] = Field(None, description="List of statuses to include")
    min_duration_seconds: Optional[float] = Field(None, ge=0, description="Minimum duration")
    max_duration_seconds: Optional[float] = Field(None, ge=0, description="Maximum duration")
    regions: Optional[List[str]] = Field(None, description="List of regions to include")

    @model_validator(mode="after")
    def validate_date_range(self) -> "ReportFilters":
        """Validate that end_date is after start_date."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

    @model_validator(mode="after")
    def validate_duration_range(self) -> "ReportFilters":
        """Validate that max_duration is greater than min_duration."""
        if (
            self.min_duration_seconds is not None
            and self.max_duration_seconds is not None
            and self.max_duration_seconds < self.min_duration_seconds
        ):
            raise ValueError("max_duration_seconds must be greater than min_duration_seconds")
        return self

    @field_validator("status")
    @classmethod
    def validate_status_values(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate status values."""
        if v is None:
            return v
        valid_statuses = {"running", "completed", "failed", "cancelled"}
        for status in v:
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        return v

    # Note: Use .model_dump() directly in calling code instead of this wrapper
    # This method is kept for backwards compatibility but will be removed in future versions


class ReportMetadata(BaseModel):
    """Report metadata.

    Contains information about the report itself.
    """

    title: str = Field(..., description="Report title")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Report generation timestamp"
    )
    generated_by: Optional[str] = Field(None, description="User who generated the report")
    report_type: str = Field(..., description="Type of report: summary, detailed, scenario, error")
    date_range: Optional[str] = Field(None, description="Human-readable date range")
    total_records: Optional[int] = Field(None, ge=0, description="Total number of records")
    filters: Optional[ReportFilters] = Field(None, description="Applied filters")

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """Validate report type."""
        valid_types = {"summary", "detailed", "scenario", "error", "custom"}
        if v not in valid_types:
            raise ValueError(f"Invalid report type: {v}. Must be one of {valid_types}")
        return v


class KPIData(BaseModel):
    """Key Performance Indicator data.

    Contains calculated KPI metrics for reports.
    """

    # Execution metrics
    total_executions: int = Field(..., ge=0, description="Total number of executions")
    successful_executions: Optional[int] = Field(None, ge=0, description="Number of successful")
    failed_executions: Optional[int] = Field(None, ge=0, description="Number of failed")
    running_executions: Optional[int] = Field(None, ge=0, description="Number still running")
    cancelled_executions: Optional[int] = Field(None, ge=0, description="Number cancelled")
    success_rate: Optional[float] = Field(None, ge=0.0, le=100.0, description="Success rate %")

    # Duration metrics
    avg_duration_seconds: Optional[float] = Field(None, ge=0, description="Average duration")
    min_duration_seconds: Optional[float] = Field(None, ge=0, description="Minimum duration")
    max_duration_seconds: Optional[float] = Field(None, ge=0, description="Maximum duration")
    median_duration_seconds: Optional[float] = Field(None, ge=0, description="Median duration")

    # Agent metrics
    total_agents: Optional[int] = Field(None, ge=0, description="Total number of agents")
    successful_agents: Optional[int] = Field(None, ge=0, description="Successful agents")
    failed_agents: Optional[int] = Field(None, ge=0, description="Failed agents")
    agent_success_rate: Optional[float] = Field(None, ge=0.0, le=100.0, description="Agent success rate %")
    avg_agents_per_execution: Optional[float] = Field(None, ge=0, description="Avg agents per execution")

    # Cost metrics
    total_cost_usd: Optional[float] = Field(None, ge=0, description="Total cost in USD")
    avg_cost_per_execution: Optional[float] = Field(None, ge=0, description="Avg cost per execution")
    avg_cost_per_agent: Optional[float] = Field(None, ge=0, description="Avg cost per agent")

    # Top items
    top_regions: Optional[List[Dict[str, Any]]] = Field(None, description="Top regions by count")
    top_scenarios: Optional[List[Dict[str, Any]]] = Field(None, description="Top scenarios")
    error_distribution: Optional[List[Dict[str, Any]]] = Field(None, description="Error distribution")

    @model_validator(mode="after")
    def calculate_success_rate(self) -> "KPIData":
        """Calculate success rate if not provided."""
        if self.success_rate is None and self.total_executions > 0:
            if self.successful_executions is not None:
                self.success_rate = (
                    self.successful_executions / self.total_executions
                ) * 100.0
        elif self.total_executions == 0:
            self.success_rate = 0.0
        return self


class ReportData(BaseModel):
    """Complete report data structure.

    Contains metadata, KPIs, and detailed data for report generation.
    """

    metadata: ReportMetadata = Field(..., description="Report metadata")
    kpi: KPIData = Field(..., description="KPI metrics")
    executions: Optional[List[Dict[str, Any]]] = Field(None, description="Execution records")
    agents: Optional[List[Dict[str, Any]]] = Field(None, description="Agent records")
    resources: Optional[List[Dict[str, Any]]] = Field(None, description="Resource records")
    charts: Optional[Dict[str, Any]] = Field(None, description="Chart configuration data")
    summary_tables: Optional[List[Dict[str, Any]]] = Field(None, description="Summary tables")

    # Note: Use .model_dump() directly in calling code instead of this wrapper
    # This method is kept for backwards compatibility but will be removed in future versions


class ScenarioReport(BaseModel):
    """Scenario-specific report data.

    Contains execution metrics for a specific scenario.
    """

    scenario_id: str = Field(..., description="Scenario identifier")
    scenario_name: str = Field(..., description="Scenario display name")
    total_executions: int = Field(..., ge=0, description="Total executions")
    successful_executions: Optional[int] = Field(None, ge=0, description="Successful executions")
    failed_executions: Optional[int] = Field(None, ge=0, description="Failed executions")
    running_executions: Optional[int] = Field(None, ge=0, description="Running executions")
    success_rate: Optional[float] = Field(None, ge=0.0, le=100.0, description="Success rate %")
    avg_duration_seconds: Optional[float] = Field(None, ge=0, description="Average duration")
    min_duration_seconds: Optional[float] = Field(None, ge=0, description="Minimum duration")
    max_duration_seconds: Optional[float] = Field(None, ge=0, description="Maximum duration")
    total_agents: Optional[int] = Field(None, ge=0, description="Total agents used")
    avg_agents_per_execution: Optional[float] = Field(None, ge=0, description="Avg agents per execution")

    @model_validator(mode="after")
    def calculate_success_rate(self) -> "ScenarioReport":
        """Calculate success rate if not provided."""
        if self.success_rate is None and self.total_executions > 0:
            if self.successful_executions is not None:
                self.success_rate = (
                    self.successful_executions / self.total_executions
                ) * 100.0
        elif self.total_executions == 0:
            self.success_rate = 0.0
        return self


class ErrorSummary(BaseModel):
    """Error summary data.

    Contains aggregated information about errors.
    """

    error_message: str = Field(..., description="Error message text")
    count: int = Field(..., ge=0, description="Number of occurrences")
    affected_executions: Optional[List[str]] = Field(None, description="List of execution IDs")
    affected_agents: Optional[List[str]] = Field(None, description="List of agent IDs")
    first_occurrence: Optional[datetime] = Field(None, description="First time error occurred")
    last_occurrence: Optional[datetime] = Field(None, description="Last time error occurred")
    regions: Optional[List[str]] = Field(None, description="Regions where error occurred")
    scenarios: Optional[List[str]] = Field(None, description="Scenarios where error occurred")
