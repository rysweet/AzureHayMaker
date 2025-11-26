"""Telemetry data models for Azure HayMaker CLI."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ExecutionRecord(BaseModel):
    """Execution record data model.

    Represents a single execution of a scenario with agents.
    """

    id: str = Field(..., description="Unique execution identifier")
    scenario_id: str = Field(..., description="ID of the scenario being executed")
    scenario_name: str = Field(..., description="Name of the scenario")
    status: str = Field(..., description="Execution status: running, completed, failed")
    started_at: datetime = Field(..., description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")
    duration_seconds: Optional[float] = Field(None, description="Execution duration in seconds")
    total_agents: int = Field(..., ge=0, description="Total number of agents")
    successful_agents: Optional[int] = Field(None, ge=0, description="Number of successful agents")
    failed_agents: Optional[int] = Field(None, ge=0, description="Number of failed agents")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate execution status."""
        valid_statuses = {"running", "completed", "failed", "cancelled"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {v}")
        return v


class AgentRecord(BaseModel):
    """Agent record data model.

    Represents a single agent instance within an execution.
    """

    id: str = Field(..., description="Unique agent identifier")
    execution_id: str = Field(..., description="Parent execution ID")
    vm_name: str = Field(..., description="VM name where agent runs")
    region: str = Field(..., min_length=1, description="Azure region")
    status: str = Field(..., description="Agent status: running, completed, failed")
    started_at: datetime = Field(..., description="Agent start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Agent completion timestamp")
    duration_seconds: Optional[float] = Field(None, description="Agent duration in seconds")
    exit_code: Optional[int] = Field(None, description="Exit code of agent process")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    stdout_lines: Optional[int] = Field(None, ge=0, description="Number of stdout lines")
    stderr_lines: Optional[int] = Field(None, ge=0, description="Number of stderr lines")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate agent status."""
        valid_statuses = {"running", "completed", "failed", "cancelled"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got: {v}")
        return v


class ResourceRecord(BaseModel):
    """Resource usage record data model.

    Represents resource metrics for an agent at a specific timestamp.
    """

    id: str = Field(..., description="Unique resource record identifier")
    execution_id: str = Field(..., description="Parent execution ID")
    agent_id: str = Field(..., description="Parent agent ID")
    vm_name: str = Field(..., description="VM name")
    timestamp: datetime = Field(..., description="Metric collection timestamp")
    cpu_percent: float = Field(..., ge=0.0, le=100.0, description="CPU usage percentage")
    memory_percent: float = Field(..., ge=0.0, le=100.0, description="Memory usage percentage")
    disk_io_read_mb: Optional[float] = Field(None, ge=0.0, description="Disk I/O read in MB")
    disk_io_write_mb: Optional[float] = Field(None, ge=0.0, description="Disk I/O write in MB")
    network_sent_mb: Optional[float] = Field(None, ge=0.0, description="Network sent in MB")
    network_recv_mb: Optional[float] = Field(None, ge=0.0, description="Network received in MB")


class CollectionResult(BaseModel):
    """Result of a telemetry collection operation.

    Tracks the outcome and statistics of data collection.
    """

    success: bool = Field(..., description="Whether collection succeeded")
    executions_collected: int = Field(..., ge=0, description="Number of executions collected")
    agents_collected: int = Field(..., ge=0, description="Number of agents collected")
    resources_collected: int = Field(..., ge=0, description="Number of resources collected")
    collection_time_seconds: float = Field(..., ge=0.0, description="Time taken to collect")
    error_message: Optional[str] = Field(None, description="Error message if failed")
