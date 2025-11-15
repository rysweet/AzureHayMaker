"""Data models for HayMaker CLI."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class OrchestratorStatus(BaseModel):
    """Orchestrator status response."""

    status: Literal["running", "idle", "error"]
    current_run_id: str | None = None
    phase: str | None = None
    active_agents: int = 0
    next_run: datetime | None = None


class MetricsSummary(BaseModel):
    """Execution metrics summary."""

    total_executions: int
    active_agents: int
    total_resources: int
    last_execution: datetime | None = None
    success_rate: float
    period: str = "7d"
    scenarios: list["ScenarioMetrics"] = Field(default_factory=list)


class ScenarioMetrics(BaseModel):
    """Per-scenario metrics."""

    scenario_name: str
    run_count: int
    success_count: int
    fail_count: int
    avg_duration_hours: float | None = None


class AgentInfo(BaseModel):
    """Agent information."""

    agent_id: str
    scenario: str
    status: Literal["running", "completed", "failed"]
    started_at: datetime
    completed_at: datetime | None = None
    progress: str | None = None
    error: str | None = None


class ResourceInfo(BaseModel):
    """Resource information."""

    id: str
    name: str
    type: str
    scenario: str
    execution_id: str
    created_at: datetime
    deleted_at: datetime | None = None
    status: Literal["created", "deleted", "error"]
    tags: dict[str, str] = Field(default_factory=dict)


class ExecutionRequest(BaseModel):
    """Execution request."""

    scenario_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExecutionResponse(BaseModel):
    """Execution response."""

    execution_id: str
    status: Literal["queued"]
    status_url: str
    created_at: datetime


class ExecutionStatus(BaseModel):
    """Execution status."""

    execution_id: str
    scenario_name: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    agent_id: str | None = None
    report_url: str | None = None
    error: str | None = None


class CleanupRequest(BaseModel):
    """Cleanup request."""

    execution_id: str | None = None
    scenario: str | None = None
    dry_run: bool = False


class CleanupResponse(BaseModel):
    """Cleanup response."""

    cleanup_id: str
    status: Literal["queued", "running", "completed", "failed"]
    resources_found: int
    resources_deleted: int = 0
    errors: list[str] = Field(default_factory=list)


class LogEntry(BaseModel):
    """Log entry."""

    timestamp: datetime
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str
    agent_id: str
    scenario: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response."""

    error: "ErrorDetail"


class ErrorDetail(BaseModel):
    """Error detail."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
