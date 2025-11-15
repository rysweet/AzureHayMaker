"""Scenario models for Azure HayMaker."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class ScenarioStatus(str, Enum):
    """Status of scenario execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CLEANUP_COMPLETE = "cleanup_complete"


class ScenarioMetadata(BaseModel):
    """Metadata for an Azure scenario."""

    scenario_name: str = Field(..., description="Unique scenario identifier")
    scenario_doc_path: str = Field(..., description="Path to scenario document in storage")
    agent_path: str = Field(..., description="Path to goal-seeking agent code")
    technology_area: str = Field(..., description="Azure technology area (e.g., AI/ML, Networking)")

    # Execution tracking
    status: ScenarioStatus = Field(default=ScenarioStatus.PENDING, description="Current status")
    started_at: datetime | None = Field(default=None, description="Scenario start time")
    ended_at: datetime | None = Field(default=None, description="Scenario end time")

    # Agent details (populated after deployment)
    agent_id: str | None = Field(default=None, description="Container App identifier")
    container_app_resource_id: str | None = Field(
        default=None, description="Container App resource ID"
    )

    # Service principal details (populated after SP creation)
    sp_name: str | None = Field(default=None, description="Service principal name")
    sp_id: str | None = Field(default=None, description="Service principal application ID")

    # Metrics
    resources_created: int = Field(default=0, description="Number of resources created")
    operations_performed: int = Field(default=0, description="Number of operations performed")

    # Error tracking
    error_message: str | None = Field(default=None, description="Error message if failed")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_seconds(self) -> int | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return None

    class Config:
        """Pydantic configuration."""

        use_enum_values = False
        validate_assignment = True
