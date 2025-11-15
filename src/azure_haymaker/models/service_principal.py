"""Service principal models for Azure HayMaker."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ServicePrincipalStatus(str, Enum):
    """Status of service principal lifecycle."""

    CREATED = "created"
    EXISTS = "exists"
    DELETED = "deleted"
    DELETION_FAILED = "deletion_failed"


class ServicePrincipalDetails(BaseModel):
    """Details of a created service principal."""

    sp_name: str = Field(..., description="Service principal name")
    client_id: str = Field(..., description="Application (client) ID")
    principal_id: str = Field(..., description="Object ID in Entra ID")
    secret_reference: str = Field(..., description="Key Vault secret name")
    created_at: datetime = Field(..., description="Creation timestamp")
    scenario_name: str = Field(..., description="Associated scenario")

    # Role assignments
    roles_assigned: list[str] = Field(default_factory=list, description="Roles assigned to this SP")

    class Config:
        """Pydantic configuration."""

        validate_assignment = True


class ServicePrincipal(BaseModel):
    """Service principal with lifecycle tracking."""

    sp_name: str = Field(..., description="Service principal name")
    sp_id: str = Field(..., description="Application (client) ID")
    principal_id: str = Field(..., description="Object ID in Entra ID")
    scenario_name: str = Field(..., description="Associated scenario")

    created_at: datetime = Field(..., description="Creation timestamp")
    deleted_at: datetime | None = Field(default=None, description="Deletion timestamp")

    status: ServicePrincipalStatus = Field(
        default=ServicePrincipalStatus.CREATED, description="Current status"
    )

    roles_assigned: list[str] = Field(default_factory=list, description="Roles assigned to this SP")

    # Scoping
    scope_resource_group: str | None = Field(
        default=None, description="Resource group scope (for security)"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = False
        validate_assignment = True
