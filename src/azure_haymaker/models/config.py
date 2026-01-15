"""Configuration models for Azure HayMaker orchestration service."""

import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, SecretStr, computed_field


class SimulationSize(str, Enum):
    """Simulation size determines how many scenarios to execute."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

    def scenario_count(self) -> int:
        """Get the number of scenarios for this simulation size."""
        mapping = {
            SimulationSize.SMALL: 5,
            SimulationSize.MEDIUM: 15,
            SimulationSize.LARGE: 30,
        }
        return mapping[self]


class StorageConfig(BaseModel):
    """Azure Blob Storage configuration."""

    account_name: str = Field(..., description="Storage account name")
    container_logs: str = Field(..., description="Container for execution logs")
    container_state: str = Field(..., description="Container for execution state")
    container_reports: str = Field(..., description="Container for execution reports")
    container_scenarios: str = Field(..., description="Container for scenario documents")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def account_url(self) -> str:
        """Get the storage account URL."""
        return f"https://{self.account_name}.blob.core.windows.net"


class TableStorageConfig(BaseModel):
    """Azure Table Storage configuration for execution state tracking."""

    account_name: str = Field(..., description="Table storage account name")
    table_execution_runs: str = Field(..., description="Table for execution run metadata")
    table_scenario_status: str = Field(..., description="Table for scenario status tracking")
    table_resource_inventory: str = Field(..., description="Table for resource inventory")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def account_url(self) -> str:
        """Get the table storage account URL."""
        return f"https://{self.account_name}.table.core.windows.net"


class CosmosDBConfig(BaseModel):
    """Azure Cosmos DB configuration for real-time metrics."""

    endpoint: str = Field(..., description="Cosmos DB endpoint URL")
    database_name: str = Field(..., description="Database name")
    container_metrics: str = Field(..., description="Container for real-time metrics")


class LogAnalyticsConfig(BaseModel):
    """Azure Log Analytics configuration for dual-write logging."""

    workspace_id: str = Field(..., description="Log Analytics workspace ID")
    workspace_key: SecretStr = Field(..., description="Log Analytics workspace key")


class OrchestratorConfig(BaseModel):
    """Complete orchestrator configuration."""

    # Target Azure environment
    target_tenant_id: str = Field(..., description="Target Azure tenant ID")
    target_subscription_id: str = Field(..., description="Target Azure subscription ID")

    # Main service principal credentials
    main_sp_client_id: str = Field(..., description="Main orchestrator SP client ID")
    main_sp_client_secret: SecretStr = Field(..., description="Main orchestrator SP secret")

    # Cross-tenant credentials (optional - for deploying to different tenant)
    target_tenant_sp_client_id: str | None = Field(
        default=None,
        description="Target tenant SP client ID (for cross-tenant deployment, optional)"
    )
    target_tenant_sp_client_secret: SecretStr | None = Field(
        default=None,
        description="Target tenant SP secret (for cross-tenant deployment, optional)"
    )

    # External API keys
    anthropic_api_key: SecretStr = Field(..., description="Anthropic API key for Claude")

    # Azure service configuration
    service_bus_namespace: str = Field(..., description="Service Bus namespace")
    service_bus_topic: str = Field(default="agent-logs", description="Service Bus topic name")

    container_registry: str = Field(..., description="Container registry URL")
    container_image: str = Field(..., description="Agent container image name")

    key_vault_url: str = Field(..., description="Key Vault URL")

    # Simulation configuration
    simulation_size: SimulationSize = Field(..., description="Simulation size")

    # Storage configuration
    storage: StorageConfig = Field(..., description="Blob storage configuration")
    table_storage: TableStorageConfig = Field(..., description="Table storage configuration")
    cosmosdb: CosmosDBConfig = Field(..., description="Cosmos DB configuration")
    log_analytics: LogAnalyticsConfig = Field(..., description="Log Analytics configuration")

    # Resource group configuration
    resource_group_name: str = Field(
        default="azure-haymaker-rg", description="Resource group for orchestrator resources"
    )

    # Container App configuration
    container_memory_gb: int = Field(default=64, description="Container memory in GB", ge=1)
    container_cpu_cores: int = Field(default=2, description="Container CPU cores", ge=1)
    container_timeout_hours: int = Field(default=10, description="Container timeout in hours", ge=1)

    # Execution configuration
    execution_duration_hours: int = Field(
        default=8, description="Scenario execution duration in hours", ge=1
    )

    # VNet configuration for security (MANDATORY - default True per security review)
    vnet_integration_enabled: bool = Field(
        default=True, description="Enable VNet integration for containers (mandatory for security)"
    )
    vnet_resource_group: str | None = Field(default=None, description="VNet resource group name")
    vnet_name: str | None = Field(default=None, description="VNet name")
    subnet_name: str | None = Field(default=None, description="Subnet name for containers")

    # Credential rotation configuration
    sp_secret_rotation_days: int = Field(
        default=30, description="Service principal secret rotation period in days", ge=1
    )
    sp_secret_expiration_warning_days: int = Field(
        default=7, description="Days before expiration to trigger rotation warning", ge=1
    )
    sp_secret_auto_rotate: bool = Field(
        default=True, description="Automatically rotate secrets before expiration"
    )
    sp_secret_max_age_days: int = Field(
        default=90, description="Maximum age of secrets before forced rotation", ge=1
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def scenario_count(self) -> int:
        """Get the number of scenarios to execute based on simulation size."""
        return self.simulation_size.scenario_count()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_cross_tenant(self) -> bool:
        """Check if configured for cross-tenant deployment.

        Returns True if:
        - target_tenant_id differs from orchestrator tenant (AZURE_TENANT_ID env var)
        - target_tenant_sp_client_id is provided

        Returns:
            True if cross-tenant mode, False for single-tenant mode
        """
        orchestrator_tenant = os.getenv("AZURE_TENANT_ID", "")
        return (
            self.target_tenant_id != orchestrator_tenant and
            self.target_tenant_sp_client_id is not None
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def target_tenant_display(self) -> str:
        """Get display name for target tenant (for logging).

        Returns:
            Human-readable tenant description with mode indicator
        """
        if self.is_cross_tenant:
            return f"{self.target_tenant_id[:8]}... (cross-tenant)"
        return f"{self.target_tenant_id[:8]}... (same as orchestrator)"

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation."""
        # Validate VNet configuration if enabled
        if self.vnet_integration_enabled and not all(
            [self.vnet_resource_group, self.vnet_name, self.subnet_name]
        ):
            raise ValueError(
                "VNet integration enabled but vnet_resource_group, vnet_name, "
                "or subnet_name not provided"
            )

    class Config:
        """Pydantic configuration."""

        # Use enum values for JSON serialization
        use_enum_values = False
        # Validate on assignment
        validate_assignment = True
