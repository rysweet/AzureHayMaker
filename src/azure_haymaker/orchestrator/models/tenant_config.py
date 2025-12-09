"""Multi-tenant configuration models for cross-tenant orchestration.

This module provides configuration models for the meta-orchestrator pattern,
enabling orchestration across multiple Azure tenants with tenant isolation.

Phase 1 (MVP) - Foundation: Cross-tenant authentication and configuration.
"""

import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


def validate_uuid_format(value: str, field_name: str) -> str:
    """Validate that a string is a valid UUID format.

    Args:
        value: String to validate
        field_name: Name of the field for error messages

    Returns:
        The validated UUID string

    Raises:
        ValueError: If the value is not a valid UUID
    """
    try:
        # Attempt to parse as UUID to validate format
        UUID(value)
        return value
    except (ValueError, AttributeError) as e:
        raise ValueError(f"{field_name} must be a valid UUID format") from e


def validate_cron_expression(value: str) -> str:
    """Validate cron expression format.

    Basic validation - ensures 5 or 6 fields with allowed characters.
    Does not validate complex cron logic.

    Args:
        value: Cron expression to validate

    Returns:
        The validated cron expression

    Raises:
        ValueError: If the cron expression is invalid
    """
    # Allow empty/None for optional schedules
    if not value:
        return value

    # Basic cron pattern: 5-6 fields with allowed characters
    # Fields: minute hour day month day-of-week [year]
    cron_pattern = r'^(\S+\s+){4,5}\S+$'

    if not re.match(cron_pattern, value):
        raise ValueError(
            f"Invalid cron expression format. Expected 5-6 space-separated fields. "
            f"Example: '0 */6 * * *' (every 6 hours). Got: '{value}'"
        )

    return value


class TenantContext(BaseModel):
    """Tenant-specific context for activity execution.

    Provides tenant isolation context including credentials, storage prefixes,
    and configuration for executing scenarios in a target tenant.

    Attributes:
        tenant_id: Target tenant UUID (validated format)
        tenant_name: Human-readable tenant name
        subscription_id: Target subscription UUID (validated format)
        region: Azure region for resource deployment
    """

    tenant_id: str = Field(..., description="Target tenant UUID")
    tenant_name: str = Field(..., description="Human-readable tenant name")
    subscription_id: str = Field(..., description="Target subscription UUID")
    region: str = Field(..., description="Azure region for deployment")

    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Validate tenant_id is valid UUID format."""
        return validate_uuid_format(v, "tenant_id")

    @field_validator('subscription_id')
    @classmethod
    def validate_subscription_id(cls, v: str) -> str:
        """Validate subscription_id is valid UUID format."""
        return validate_uuid_format(v, "subscription_id")

    def get_storage_prefix(self) -> str:
        """Get storage path prefix for tenant isolation.

        Returns:
            Storage prefix string (tenant_id for path-based isolation)
        """
        return self.tenant_id


class TargetTenantConfig(BaseModel):
    """Configuration for a single target tenant.

    Defines all settings for orchestrating scenarios in a target tenant,
    including credentials, resource limits, and scheduling.

    Attributes:
        name: Unique tenant identifier (alphanumeric + hyphens)
        display_name: Human-readable display name
        description: Optional tenant description
        tenant_id: Azure tenant UUID
        subscription_id: Azure subscription UUID
        region: Azure region for deployment
        credentials: Key Vault credential configuration
        enabled: Whether tenant is enabled for orchestration
        scenarios: List of scenario identifiers to execute
        schedule: Optional cron-based scheduling configuration
        limits: Resource limits for cost control
        monitoring: Monitoring and alerting configuration
        cleanup: Resource cleanup configuration
    """

    name: str = Field(..., description="Unique tenant identifier")
    display_name: str = Field(..., description="Human-readable display name")
    description: str | None = Field(default=None, description="Tenant description")

    tenant_id: str = Field(..., description="Azure tenant UUID")
    subscription_id: str = Field(..., description="Azure subscription UUID")
    region: str = Field(..., description="Azure region for deployment")

    credentials: dict = Field(..., description="Key Vault credential configuration")

    enabled: bool = Field(default=True, description="Enable tenant orchestration")

    scenarios: list[str] = Field(..., min_length=1, description="Scenario identifiers to execute")
    scenario_selection_mode: str = Field(default="all", description="Scenario selection mode")
    max_scenarios_per_execution: int = Field(default=10, ge=1, description="Max scenarios per execution")

    schedule: dict | None = Field(default=None, description="Cron-based schedule configuration")

    resource_tags: dict[str, str] = Field(default_factory=dict, description="Resource tags")
    resource_naming: dict = Field(default_factory=dict, description="Resource naming configuration")

    limits: dict = Field(default_factory=dict, description="Resource limits")
    monitoring: dict = Field(default_factory=dict, description="Monitoring configuration")
    cleanup: dict = Field(default_factory=dict, description="Cleanup configuration")

    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Validate tenant_id is valid UUID format."""
        return validate_uuid_format(v, "tenant_id")

    @field_validator('subscription_id')
    @classmethod
    def validate_subscription_id(cls, v: str) -> str:
        """Validate subscription_id is valid UUID format."""
        return validate_uuid_format(v, "subscription_id")

    @field_validator('credentials')
    @classmethod
    def validate_credentials(cls, v: dict) -> dict:
        """Validate credentials contain keyvault_secret_prefix."""
        if 'keyvault_secret_prefix' not in v:
            raise ValueError("credentials must contain 'keyvault_secret_prefix'")
        return v

    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v: dict | None) -> dict | None:
        """Validate schedule configuration contains valid cron expression."""
        if v is None:
            return v

        if 'cron' in v:
            # Validate cron expression format
            validate_cron_expression(v['cron'])

        return v

    @field_validator('limits')
    @classmethod
    def validate_limits(cls, v: dict) -> dict:
        """Validate that limits don't have negative values."""
        for key, value in v.items():
            if isinstance(value, (int, float)) and value < 0:
                raise ValueError(f"Limit '{key}' cannot be negative: {value}")
        return v


class MetaOrchestratorConfig(BaseModel):
    """Configuration for multi-tenant meta-orchestrator.

    Top-level configuration for the meta-orchestrator that manages
    orchestration across multiple target tenants.

    This model has two usage patterns:
    1. Flat structure: Pass meta_orchestrator fields directly plus target_tenants list
    2. Nested structure: Pass {meta_orchestrator: {...}, target_tenants: [...]}

    Attributes:
        name: Orchestrator instance name
        infrastructure_tenant_id: Infrastructure tenant UUID (where orchestrator runs)
        max_concurrent_tenants: Maximum concurrent tenant orchestrations (1-20)
        max_concurrent_scenarios_per_tenant: Max concurrent scenarios per tenant
        target_tenants: List of target tenant configurations
        enable_tenant_isolation: Enable strict tenant isolation
    """

    # Allow both nested and flat structure via model_validate
    meta_orchestrator: dict | None = Field(default=None, exclude=True)

    name: str | None = Field(default=None, description="Orchestrator instance name")

    infrastructure_tenant_id: str | None = Field(
        default=None,
        description="Infrastructure tenant UUID (where orchestrator runs)"
    )

    max_concurrent_tenants: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent tenant orchestrations"
    )

    max_concurrent_scenarios_per_tenant: int = Field(
        default=10,
        ge=1,
        description="Maximum concurrent scenarios per tenant"
    )

    polling_interval_seconds: int = Field(
        default=30,
        ge=10,
        description="Orchestrator polling interval in seconds"
    )

    health_check_interval_seconds: int = Field(
        default=60,
        ge=30,
        description="Health check interval in seconds"
    )

    execution_timeout_hours: int = Field(
        default=24,
        ge=1,
        description="Execution timeout in hours"
    )

    max_retry_attempts: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for failed operations"
    )

    retry_delay_seconds: int = Field(
        default=60,
        ge=1,
        description="Delay between retry attempts in seconds"
    )

    enable_circuit_breaker: bool = Field(
        default=True,
        description="Enable circuit breaker for fault tolerance"
    )

    circuit_breaker_threshold: int = Field(
        default=5,
        ge=1,
        description="Circuit breaker failure threshold"
    )

    storage_account_name: str | None = Field(
        default=None,
        description="Infrastructure storage account name"
    )

    application_insights_key: str | None = Field(
        default=None,
        description="Application Insights instrumentation key"
    )

    log_level: str = Field(
        default="info",
        description="Logging level (debug, info, warning, error)"
    )

    enable_tenant_isolation: bool = Field(
        default=True,
        description="Enable strict tenant isolation"
    )

    enable_cost_tracking: bool = Field(
        default=True,
        description="Enable cost tracking per tenant"
    )

    enable_distributed_tracing: bool = Field(
        default=True,
        description="Enable distributed tracing across tenants"
    )

    target_tenants: list[TargetTenantConfig] = Field(
        default_factory=list,
        description="List of target tenant configurations"
    )

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to handle nested structure and validation."""
        # Handle nested meta_orchestrator structure
        if self.meta_orchestrator is not None:
            # Flatten meta_orchestrator fields into main model
            for key, value in self.meta_orchestrator.items():
                if hasattr(self, key):
                    setattr(self, key, value)

        # Validate required fields are present
        if self.name is None:
            raise ValueError("name is required")
        if self.infrastructure_tenant_id is None:
            raise ValueError("infrastructure_tenant_id is required")
        if self.storage_account_name is None:
            raise ValueError("storage_account_name is required")

    @field_validator('infrastructure_tenant_id')
    @classmethod
    def validate_infrastructure_tenant_id(cls, v: str | None) -> str | None:
        """Validate infrastructure_tenant_id is valid UUID format."""
        if v is None:
            return v
        return validate_uuid_format(v, "infrastructure_tenant_id")

    @model_validator(mode='after')
    def validate_unique_tenant_ids_and_names(self) -> 'MetaOrchestratorConfig':
        """Validate that tenant_ids and names are unique across all target tenants."""
        if not self.target_tenants:
            # Empty list is valid (single-tenant mode)
            return self

        # Check for duplicate tenant_ids
        tenant_ids = [t.tenant_id for t in self.target_tenants]
        if len(tenant_ids) != len(set(tenant_ids)):
            raise ValueError("Duplicate tenant_id detected across target tenants")

        # Check for duplicate tenant names
        tenant_names = [t.name for t in self.target_tenants]
        if len(tenant_names) != len(set(tenant_names)):
            raise ValueError("Duplicate tenant name detected across target tenants")

        return self

    def is_multi_tenant_mode(self) -> bool:
        """Check if configuration is in multi-tenant mode.

        Returns:
            True if multiple target tenants configured, False otherwise
        """
        return len(self.target_tenants) > 1

    def is_single_tenant_mode(self) -> bool:
        """Check if configuration is in single-tenant mode.

        Returns:
            True if zero or one target tenant configured, False otherwise
        """
        return len(self.target_tenants) <= 1

    def get_tenant_by_name(self, tenant_name: str) -> TargetTenantConfig | None:
        """Get target tenant configuration by name.

        Args:
            tenant_name: Tenant name to search for

        Returns:
            TargetTenantConfig if found, None otherwise
        """
        for tenant in self.target_tenants:
            if tenant.name == tenant_name:
                return tenant
        return None

    def get_tenant_by_id(self, tenant_id: str) -> TargetTenantConfig | None:
        """Get target tenant configuration by ID.

        Args:
            tenant_id: Tenant UUID to search for

        Returns:
            TargetTenantConfig if found, None otherwise
        """
        for tenant in self.target_tenants:
            if tenant.tenant_id == tenant_id:
                return tenant
        return None

    def model_dump(self, **kwargs) -> dict:
        """Override model_dump to restore nested structure for backward compatibility.

        Returns:
            Dictionary with meta_orchestrator nested structure
        """
        # Get base serialization (excludes meta_orchestrator due to exclude=True)
        data = super().model_dump(**kwargs)

        # Reconstruct nested structure
        meta_orchestrator_fields = {
            "name": self.name,
            "infrastructure_tenant_id": self.infrastructure_tenant_id,
            "max_concurrent_tenants": self.max_concurrent_tenants,
            "max_concurrent_scenarios_per_tenant": self.max_concurrent_scenarios_per_tenant,
            "polling_interval_seconds": self.polling_interval_seconds,
            "health_check_interval_seconds": self.health_check_interval_seconds,
            "execution_timeout_hours": self.execution_timeout_hours,
            "max_retry_attempts": self.max_retry_attempts,
            "retry_delay_seconds": self.retry_delay_seconds,
            "enable_circuit_breaker": self.enable_circuit_breaker,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "storage_account_name": self.storage_account_name,
            "application_insights_key": self.application_insights_key,
            "log_level": self.log_level,
            "enable_tenant_isolation": self.enable_tenant_isolation,
            "enable_cost_tracking": self.enable_cost_tracking,
            "enable_distributed_tracing": self.enable_distributed_tracing,
        }

        # Remove these from top level
        for key in meta_orchestrator_fields:
            data.pop(key, None)

        # Return nested structure
        return {
            "meta_orchestrator": meta_orchestrator_fields,
            "target_tenants": data["target_tenants"],
        }
