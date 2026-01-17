"""Cost query module for Azure HayMaker orchestrator.

This module queries Azure Cost Management API to retrieve cost data
for specific execution runs filtered by tags.

Azure Cost Management has approximately a 24-hour delay before cost data
becomes available, so recent runs may return empty or partial data.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import (
    ExportType,
    GranularityType,
    QueryAggregation,
    QueryDataset,
    QueryDefinition,
    QueryFilter,
    QueryGrouping,
    QueryTimePeriod,
    TimeframeType,
)
from pydantic import BaseModel, Field

from azure_haymaker.exceptions import CostQueryError

logger = logging.getLogger(__name__)

# Default cost query period in days
DEFAULT_QUERY_PERIOD_DAYS = 30


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


async def _query_tenant_costs(
    cost_client: CostManagementClient,
    scope: str,
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
) -> dict[str, dict[str, float]]:
    """Query costs for a specific tenant filtered by TenantId tag.

    Internal helper that queries Azure Cost Management for costs grouped by
    resource type, scenario, and execution ID.

    Args:
        cost_client: Azure Cost Management client
        scope: Azure scope (subscription)
        tenant_id: Tenant ID to filter by
        period_start: Query period start
        period_end: Query period end

    Returns:
        Dictionary with 'by_type', 'by_scenario', 'by_execution' cost breakdowns
    """
    # Query costs grouped by resource type with TenantId filter
    cost_by_type = await _query_costs_by_tenant_grouped_by(
        cost_client=cost_client,
        scope=scope,
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        group_by="ResourceType",
    )

    # Query costs grouped by scenario tag
    cost_by_scenario = await _query_costs_by_tenant_grouped_by(
        cost_client=cost_client,
        scope=scope,
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        group_by="TagValue",
        tag_name="Scenario",
    )

    # Query costs grouped by execution ID tag
    cost_by_execution = await _query_costs_by_tenant_grouped_by(
        cost_client=cost_client,
        scope=scope,
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        group_by="TagValue",
        tag_name="ExecutionId",
    )

    return {
        "by_type": cost_by_type,
        "by_scenario": cost_by_scenario,
        "by_execution": cost_by_execution,
    }


async def _query_costs_by_tenant_grouped_by(
    cost_client: CostManagementClient,
    scope: str,
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
    group_by: str,
    tag_name: str | None = None,
) -> dict[str, float]:
    """Execute a cost query for a tenant grouped by a specific dimension.

    Args:
        cost_client: Azure Cost Management client
        scope: Azure scope (subscription)
        tenant_id: Tenant ID for tag filter
        period_start: Query period start
        period_end: Query period end
        group_by: Dimension to group by (ResourceType or TagValue)
        tag_name: Optional tag name when grouping by TagValue

    Returns:
        Dictionary mapping group names to costs
    """
    # Build filter for AzureHayMaker-managed resources with specific TenantId
    tag_filter = QueryFilter(
        and_property=[
            QueryFilter(
                tags={"name": "AzureHayMaker-managed", "operator": "In", "values": ["true"]}
            ),
            QueryFilter(tags={"name": "TenantId", "operator": "In", "values": [tenant_id]}),
        ]
    )

    # Build grouping
    if tag_name:
        grouping = [QueryGrouping(type="TagKey", name=tag_name)]
    else:
        grouping = [QueryGrouping(type="Dimension", name=group_by)]

    # Build query definition
    query_definition = QueryDefinition(
        type=ExportType.ACTUAL_COST,
        timeframe=TimeframeType.CUSTOM,
        time_period=QueryTimePeriod(
            from_property=period_start,
            to=period_end,
        ),
        dataset=QueryDataset(
            granularity=GranularityType.NONE,
            aggregation={
                "totalCost": QueryAggregation(name="Cost", function="Sum"),
            },
            grouping=grouping,
            filter=tag_filter,
        ),
    )

    # Execute query (sync API, run in thread pool)
    try:
        result = await asyncio.to_thread(
            cost_client.query.usage,
            scope=scope,
            parameters=query_definition,
        )
    except HttpResponseError as e:
        # Handle case where Cost Management API returns no data
        if "No data available" in str(e) or e.status_code == 404:
            logger.info(f"No cost data available for tenant {tenant_id}")
            return {}
        raise

    # Parse results
    costs: dict[str, float] = {}

    if result and result.rows:
        # Result columns are typically: [Cost, GroupName, Currency]
        for row in result.rows:
            if len(row) >= 2:
                cost_value = float(row[0]) if row[0] is not None else 0.0
                group_name = str(row[1]) if row[1] is not None else "Unknown"
                costs[group_name] = costs.get(group_name, 0.0) + cost_value

    return costs


async def get_tenant_cost_summary(
    subscription_id: str,
    tenant_id: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> TenantCostSummary:
    """Query Azure Cost Management for costs associated with a tenant.

    Queries costs filtered by AzureHayMaker-managed=true and TenantId={tenant_id} tags,
    grouped by resource type, scenario, and execution ID.

    Note: Azure Cost Management has ~24 hour delay. Recent runs will return
    empty or partial cost data.

    Args:
        subscription_id: Azure subscription ID to query
        tenant_id: Tenant ID to filter costs
        period_start: Optional start of cost period (defaults to 30 days ago)
        period_end: Optional end of cost period (defaults to now)

    Returns:
        TenantCostSummary with cost breakdown

    Raises:
        ValueError: If tenant_id or subscription_id is empty
        CostQueryError: If cost query fails
    """
    # Validate required parameters
    if not tenant_id or (isinstance(tenant_id, str) and not tenant_id.strip()):
        raise ValueError("tenant_id cannot be empty")
    if not subscription_id or (isinstance(subscription_id, str) and not subscription_id.strip()):
        raise ValueError("subscription_id cannot be empty")

    # Set default period if not provided
    now = datetime.now(UTC)
    if period_end is None:
        period_end = now
    if period_start is None:
        period_start = now - timedelta(days=DEFAULT_QUERY_PERIOD_DAYS)

    try:
        credential = DefaultAzureCredential()
        cost_client = CostManagementClient(credential)

        # Build scope for subscription-level query
        scope = f"/subscriptions/{subscription_id}"

        # Query tenant costs
        cost_data = await _query_tenant_costs(
            cost_client=cost_client,
            scope=scope,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        # Calculate total cost from resource type breakdown
        total_cost = sum(cost_data["by_type"].values())

        # Calculate execution count
        execution_count = len(cost_data["by_execution"])

        logger.info(
            f"Cost query for tenant {tenant_id}: total={total_cost:.2f} USD, "
            f"{len(cost_data['by_type'])} resource types, "
            f"{len(cost_data['by_scenario'])} scenarios, "
            f"{execution_count} executions"
        )

        return TenantCostSummary(
            tenant_id=tenant_id,
            total_cost=total_cost,
            currency="USD",
            period_start=period_start,
            period_end=period_end,
            cost_by_resource_type=cost_data["by_type"],
            cost_by_scenario=cost_data["by_scenario"],
            cost_by_execution=cost_data["by_execution"],
            execution_count=execution_count,
        )

    except ClientAuthenticationError as e:
        logger.error(f"Authentication failed querying costs for tenant {tenant_id}: {e}")
        raise CostQueryError(
            f"Authentication failed querying costs: {e}",
            run_id=tenant_id,
        ) from e
    except ResourceNotFoundError:
        logger.warning(f"No cost data found for tenant {tenant_id}")
        # Return empty summary for tenants with no cost data yet
        return TenantCostSummary(
            tenant_id=tenant_id,
            total_cost=0.0,
            currency="USD",
            period_start=period_start,
            period_end=period_end,
            cost_by_resource_type={},
            cost_by_scenario={},
            cost_by_execution={},
            execution_count=0,
        )
    except HttpResponseError as e:
        logger.error(f"HTTP error querying costs for tenant {tenant_id}: {e}")
        raise CostQueryError(
            f"Failed to query costs: {e}",
            run_id=tenant_id,
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error querying costs for tenant {tenant_id}: {e}")
        raise CostQueryError(
            f"Unexpected error querying costs: {e}",
            run_id=tenant_id,
        ) from e


async def get_cost_summary(
    subscription_id: str,
    run_id: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> CostSummary:
    """Query Azure Cost Management for costs associated with a run.

    Queries costs filtered by AzureHayMaker-managed=true and RunId={run_id} tags,
    grouped by resource type and scenario.

    Note: Azure Cost Management has ~24 hour delay. Recent runs will return
    empty or partial cost data.

    Args:
        subscription_id: Azure subscription ID to query
        run_id: Execution run ID to filter costs
        period_start: Optional start of cost period (defaults to 30 days ago)
        period_end: Optional end of cost period (defaults to now)

    Returns:
        CostSummary with cost breakdown

    Raises:
        CostQueryError: If cost query fails
    """
    # Set default period if not provided
    now = datetime.now(UTC)
    if period_end is None:
        period_end = now
    if period_start is None:
        # Default to 30 days ago to capture most scenarios
        period_start = now - timedelta(days=30)

    try:
        credential = DefaultAzureCredential()
        cost_client = CostManagementClient(credential)

        # Build scope for subscription-level query
        scope = f"/subscriptions/{subscription_id}"

        # Query for costs grouped by resource type
        cost_by_type = await _query_costs_grouped_by(
            cost_client=cost_client,
            scope=scope,
            run_id=run_id,
            period_start=period_start,
            period_end=period_end,
            group_by="ResourceType",
        )

        # Query for costs grouped by scenario tag
        cost_by_scenario = await _query_costs_grouped_by(
            cost_client=cost_client,
            scope=scope,
            run_id=run_id,
            period_start=period_start,
            period_end=period_end,
            group_by="TagValue",
            tag_name="Scenario",
        )

        # Calculate total cost
        total_cost = sum(cost_by_type.values())

        logger.info(
            f"Cost query for run {run_id}: total={total_cost:.2f} USD, "
            f"{len(cost_by_type)} resource types, {len(cost_by_scenario)} scenarios"
        )

        return CostSummary(
            run_id=run_id,
            total_cost=total_cost,
            currency="USD",
            period_start=period_start,
            period_end=period_end,
            cost_by_resource_type=cost_by_type,
            cost_by_scenario=cost_by_scenario,
        )

    except ClientAuthenticationError as e:
        logger.error(f"Authentication failed querying costs for run {run_id}: {e}")
        raise CostQueryError(
            f"Authentication failed querying costs: {e}",
            run_id=run_id,
        ) from e
    except ResourceNotFoundError as e:
        logger.warning(f"No cost data found for run {run_id}: {e}")
        # Return empty summary for runs with no cost data yet
        return CostSummary(
            run_id=run_id,
            total_cost=0.0,
            currency="USD",
            period_start=period_start,
            period_end=period_end,
            cost_by_resource_type={},
            cost_by_scenario={},
        )
    except HttpResponseError as e:
        logger.error(f"HTTP error querying costs for run {run_id}: {e}")
        raise CostQueryError(
            f"Failed to query costs: {e}",
            run_id=run_id,
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error querying costs for run {run_id}: {e}")
        raise CostQueryError(
            f"Unexpected error querying costs: {e}",
            run_id=run_id,
        ) from e


async def _query_costs_grouped_by(
    cost_client: CostManagementClient,
    scope: str,
    run_id: str,
    period_start: datetime,
    period_end: datetime,
    group_by: str,
    tag_name: str | None = None,
) -> dict[str, float]:
    """Execute a cost query grouped by a specific dimension.

    Args:
        cost_client: Azure Cost Management client
        scope: Azure scope (subscription/resource group)
        run_id: Execution run ID for tag filter
        period_start: Query period start
        period_end: Query period end
        group_by: Dimension to group by (ResourceType or TagValue)
        tag_name: Optional tag name when grouping by TagValue

    Returns:
        Dictionary mapping group names to costs
    """

    # Build filter for AzureHayMaker-managed resources with specific RunId
    # Filter by tags: AzureHayMaker-managed=true AND RunId={run_id}
    tag_filter = QueryFilter(
        and_property=[
            QueryFilter(
                tags={"name": "AzureHayMaker-managed", "operator": "In", "values": ["true"]}
            ),
            QueryFilter(tags={"name": "RunId", "operator": "In", "values": [run_id]}),
        ]
    )

    # Build grouping
    if tag_name:
        grouping = [QueryGrouping(type="TagKey", name=tag_name)]
    else:
        grouping = [QueryGrouping(type="Dimension", name=group_by)]

    # Build query definition
    query_definition = QueryDefinition(
        type=ExportType.ACTUAL_COST,
        timeframe=TimeframeType.CUSTOM,
        time_period=QueryTimePeriod(
            from_property=period_start,
            to=period_end,
        ),
        dataset=QueryDataset(
            granularity=GranularityType.NONE,
            aggregation={
                "totalCost": QueryAggregation(name="Cost", function="Sum"),
            },
            grouping=grouping,
            filter=tag_filter,
        ),
    )

    # Execute query (sync API, run in thread pool)
    try:
        result = await asyncio.to_thread(
            cost_client.query.usage,
            scope=scope,
            parameters=query_definition,
        )
    except HttpResponseError as e:
        # Handle case where Cost Management API is not available or returns error
        if "No data available" in str(e) or e.status_code == 404:
            logger.info(f"No cost data available for scope {scope}")
            return {}
        raise

    # Parse results
    costs: dict[str, float] = {}

    if result and result.rows:
        # Result columns are typically: [Cost, GroupName, Currency]
        for row in result.rows:
            if len(row) >= 2:
                cost_value = float(row[0]) if row[0] is not None else 0.0
                group_name = str(row[1]) if row[1] is not None else "Unknown"
                costs[group_name] = costs.get(group_name, 0.0) + cost_value

    return costs


__all__ = [
    "CostSummary",
    "TenantCostSummary",
    "get_cost_summary",
    "get_tenant_cost_summary",
]
