"""Service principal models for Azure HayMaker."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class ServicePrincipalStatus(str, Enum):
    """Status of service principal lifecycle."""

    CREATED = "created"
    EXISTS = "exists"
    DELETED = "deleted"
    DELETION_FAILED = "deletion_failed"


class SecretExpirationStatus(str, Enum):
    """Status of secret expiration."""

    VALID = "valid"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


class ServicePrincipalDetails(BaseModel):
    """Details of a created service principal."""

    sp_name: str = Field(..., description="Service principal name")
    client_id: str = Field(..., description="Application (client) ID")
    principal_id: str = Field(..., description="Object ID in Entra ID")
    secret_reference: str = Field(..., description="Key Vault secret name")
    created_at: datetime = Field(..., description="Creation timestamp")
    scenario_name: str = Field(..., description="Associated scenario")

    # Secret expiration tracking
    secret_expires_at: datetime | None = Field(default=None, description="When the secret expires")
    secret_rotation_threshold_days: int = Field(
        default=7, description="Days before expiration to trigger rotation warning"
    )

    # Role assignments
    roles_assigned: list[str] = Field(default_factory=list, description="Roles assigned to this SP")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def secret_expiration_status(self) -> SecretExpirationStatus:
        """Get the current expiration status of the secret."""
        if self.secret_expires_at is None:
            return SecretExpirationStatus.VALID

        now = datetime.now(UTC)
        if now >= self.secret_expires_at:
            return SecretExpirationStatus.EXPIRED

        days_until_expiry = (self.secret_expires_at - now).days
        if days_until_expiry <= self.secret_rotation_threshold_days:
            return SecretExpirationStatus.EXPIRING_SOON

        return SecretExpirationStatus.VALID

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_until_expiration(self) -> int | None:
        """Get the number of days until secret expiration."""
        if self.secret_expires_at is None:
            return None
        now = datetime.now(UTC)
        return max(0, (self.secret_expires_at - now).days)

    def needs_rotation(self) -> bool:
        """Check if the secret needs to be rotated."""
        return self.secret_expiration_status in (
            SecretExpirationStatus.EXPIRING_SOON,
            SecretExpirationStatus.EXPIRED,
        )

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

    # Secret expiration tracking
    secret_expires_at: datetime | None = Field(default=None, description="When the secret expires")
    secret_last_rotated_at: datetime | None = Field(
        default=None, description="When the secret was last rotated"
    )
    secret_rotation_count: int = Field(
        default=0, description="Number of times the secret has been rotated"
    )

    # Scoping
    scope_resource_group: str | None = Field(
        default=None, description="Resource group scope (for security)"
    )

    # Default rotation threshold for this model
    secret_rotation_threshold_days: int = Field(
        default=7, description="Days before expiration to trigger rotation warning"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def secret_expiration_status(self) -> SecretExpirationStatus:
        """Get the current expiration status of the secret."""
        if self.secret_expires_at is None:
            return SecretExpirationStatus.VALID

        now = datetime.now(UTC)
        if now >= self.secret_expires_at:
            return SecretExpirationStatus.EXPIRED

        days_until_expiry = (self.secret_expires_at - now).days
        if days_until_expiry <= self.secret_rotation_threshold_days:
            return SecretExpirationStatus.EXPIRING_SOON

        return SecretExpirationStatus.VALID

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_until_expiration(self) -> int | None:
        """Get the number of days until secret expiration."""
        if self.secret_expires_at is None:
            return None
        now = datetime.now(UTC)
        return max(0, (self.secret_expires_at - now).days)

    def needs_rotation(self) -> bool:
        """Check if the secret needs to be rotated."""
        return self.secret_expiration_status in (
            SecretExpirationStatus.EXPIRING_SOON,
            SecretExpirationStatus.EXPIRED,
        )

    class Config:
        """Pydantic configuration."""

        use_enum_values = False
        validate_assignment = True
