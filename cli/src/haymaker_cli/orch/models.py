"""Data models for orchestrator CLI commands."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ContainerAppInfo(BaseModel):
    """Container App information from Azure Container Apps.

    Represents the state and configuration of a deployed Container App,
    including provisioning status, running state, and revision details.
    """

    name: str = Field(description="Container app name")
    resource_group: str = Field(description="Resource group name")
    location: str = Field(description="Azure region")
    provisioning_state: str = Field(description="Provisioning state (Succeeded, Failed, etc.)")
    running_status: str | None = Field(
        default=None, description="Running status (Running, Stopped, etc.)"
    )
    latest_revision_name: str | None = Field(default=None, description="Latest revision name")
    latest_revision_fqdn: str | None = Field(
        default=None, description="Fully qualified domain name"
    )
    active_revisions_count: int = Field(default=0, description="Number of active revisions")
    min_replicas: int = Field(default=0, description="Minimum replica count")
    max_replicas: int = Field(default=10, description="Maximum replica count")
    ingress_enabled: bool = Field(default=False, description="Whether ingress is enabled")
    external_ingress: bool = Field(default=False, description="Whether external ingress is enabled")
    target_port: int | None = Field(default=None, description="Target port for ingress")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    tags: dict[str, str] = Field(default_factory=dict, description="Resource tags")


class ReplicaInfo(BaseModel):
    """Container App replica information.

    Represents a single running instance (replica) of a Container App revision,
    including its current state and creation time.
    """

    name: str = Field(description="Replica name")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    running_state: str | None = Field(
        default=None, description="Running state (Running, NotRunning, Unknown)"
    )
    running_state_details: str | None = Field(
        default=None, description="Additional state details"
    )


class RevisionInfo(BaseModel):
    """Container App revision information.

    Represents a specific version/revision of a Container App,
    including traffic weight, replica information, and health status.
    """

    name: str = Field(description="Revision name")
    active: bool = Field(description="Whether revision is active")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    traffic_weight: int = Field(default=0, description="Traffic weight percentage (0-100)")
    provisioning_state: str | None = Field(
        default=None, description="Provisioning state (Provisioned, Failed, etc.)"
    )
    health_state: str | None = Field(
        default=None, description="Health state (Healthy, Unhealthy, None)"
    )
    replicas: list[ReplicaInfo] = Field(default_factory=list, description="List of replicas")
    replicas_count: int = Field(default=0, description="Total replica count")


class HealthCheckResult(BaseModel):
    """Health check result for Container App.

    Aggregates health information for a Container App, including
    overall status, active revisions, and detailed health checks.
    """

    app_name: str = Field(description="Container app name")
    status: Literal["healthy", "unhealthy", "degraded", "unknown"] = Field(
        description="Overall health status"
    )
    provisioning_state: str = Field(description="Provisioning state")
    running_status: str | None = Field(default=None, description="Running status")
    total_replicas: int = Field(default=0, description="Total number of replicas")
    healthy_replicas: int = Field(default=0, description="Number of healthy replicas")
    active_revisions: int = Field(default=0, description="Number of active revisions")
    latest_revision: str | None = Field(default=None, description="Latest revision name")
    fqdn: str | None = Field(default=None, description="Fully qualified domain name")
    checked_at: datetime = Field(
        default_factory=datetime.utcnow, description="Time of health check"
    )
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: list[str] = Field(default_factory=list, description="Any warnings")
    details: dict[str, str] = Field(default_factory=dict, description="Additional details")


class OrchClientError(Exception):
    """Base exception for orchestrator client errors.

    Provides structured error information with exit codes for CLI commands:
    - 1: Configuration error (missing/invalid config)
    - 2: Network error (connectivity issues)
    - 3: API error (Azure API failures)
    - 4: Server error (5xx responses)
    """

    def __init__(
        self,
        message: str,
        exit_code: int = 1,
        details: dict[str, str] | None = None,
    ):
        """Initialize client error.

        Args:
            message: Error message
            exit_code: CLI exit code (1=config, 2=network, 3=api, 4=server)
            details: Additional error details
        """
        super().__init__(message)
        self.exit_code = exit_code
        self.details = details or {}


class ConfigError(OrchClientError):
    """Configuration error (exit code 1)."""

    def __init__(self, message: str, details: dict[str, str] | None = None):
        super().__init__(message, exit_code=1, details=details)


class NetworkError(OrchClientError):
    """Network connectivity error (exit code 2)."""

    def __init__(self, message: str, details: dict[str, str] | None = None):
        super().__init__(message, exit_code=2, details=details)


class ApiError(OrchClientError):
    """Azure API error (exit code 3)."""

    def __init__(self, message: str, details: dict[str, str] | None = None):
        super().__init__(message, exit_code=3, details=details)


class ServerError(OrchClientError):
    """Azure server error (exit code 4)."""

    def __init__(self, message: str, details: dict[str, str] | None = None):
        super().__init__(message, exit_code=4, details=details)
