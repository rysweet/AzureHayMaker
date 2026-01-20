"""Cost query data models for Azure HayMaker orchestrator.

This module defines Pydantic models for cost summaries returned by
Azure Cost Management API queries.

Philosophy:
- Single responsibility: Data models only
- Standard library + Pydantic
- Self-contained and regeneratable

Public API (the "studs"):
    CostSummary: Summary of costs for an execution run
    TenantCostSummary: Summary of costs for a specific tenant
"""

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = ["CostSummary", "TenantCostSummary"]


class CostSummary(BaseModel):
    """Summary of costs for an execution run.

    Attributes:
        run_id: The execution run identifier
        total_cost: Total cost in the specified currency
        currency: Currency code (default USD)
        period_start: Start of the cost query period
        period_end: End of the cost query period
        cost_by_resource_type: Cost breakdown by Azure resource type
        cost_by_scenario: Cost breakdown by scenario tag
    """

    run_id: str = Field(..., description="Execution run ID")
    total_cost: float = Field(default=0.0, description="Total cost for the run")
    currency: str = Field(default="USD", description="Currency code")
    period_start: datetime = Field(..., description="Cost period start")
    period_end: datetime = Field(..., description="Cost period end")
    cost_by_resource_type: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by Azure resource type (e.g., Microsoft.Compute/virtualMachines)",
    )
    cost_by_scenario: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by scenario tag",
    )


class TenantCostSummary(BaseModel):
    """Summary of costs for a specific tenant.

    Extends cost tracking with tenant-specific fields for multi-tenant
    resource isolation and cost attribution per Issue #126.

    Attributes:
        tenant_id: The tenant identifier for cost attribution
        total_cost: Total cost in the specified currency
        currency: Currency code (default USD)
        period_start: Start of the cost query period
        period_end: End of the cost query period
        cost_by_resource_type: Cost breakdown by Azure resource type
        cost_by_scenario: Cost breakdown by scenario tag
        cost_by_execution: Cost breakdown by execution ID
        execution_count: Number of unique executions in the period
    """

    tenant_id: str = Field(..., description="Tenant ID for cost attribution")
    total_cost: float = Field(default=0.0, description="Total cost for the tenant")
    currency: str = Field(default="USD", description="Currency code")
    period_start: datetime = Field(..., description="Cost period start")
    period_end: datetime = Field(..., description="Cost period end")
    cost_by_resource_type: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by Azure resource type",
    )
    cost_by_scenario: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by scenario tag",
    )
    cost_by_execution: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by execution ID",
    )
    execution_count: int = Field(
        default=0,
        description="Number of unique executions in the period",
    )
