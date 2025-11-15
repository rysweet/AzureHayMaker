"""Azure resource models for tracking created resources."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ResourceStatus(str, Enum):
    """Status of Azure resource lifecycle."""

    CREATED = "created"
    EXISTS = "exists"
    DELETED = "deleted"
    DELETION_FAILED = "deletion_failed"


class Resource(BaseModel):
    """Azure resource with lifecycle tracking."""

    resource_id: str = Field(..., description="Full Azure resource ID")
    resource_type: str = Field(..., description="Azure resource type")
    resource_name: str = Field(..., description="Resource name")

    scenario_name: str = Field(..., description="Scenario that created this resource")
    run_id: str = Field(..., description="Execution run ID")

    created_at: datetime = Field(..., description="Resource creation timestamp")
    deleted_at: datetime | None = Field(default=None, description="Resource deletion timestamp")

    status: ResourceStatus = Field(default=ResourceStatus.CREATED, description="Current status")

    deletion_attempts: int = Field(default=0, description="Number of deletion attempts", ge=0)
    deletion_error: str | None = Field(default=None, description="Last deletion error message")

    tags: dict[str, str] = Field(default_factory=dict, description="Resource tags")

    class Config:
        """Pydantic configuration."""

        use_enum_values = False
        validate_assignment = True
