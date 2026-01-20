"""Cost aggregation logic for Azure Cost Management queries.

This module contains internal helper functions for querying and aggregating
cost data from Azure Cost Management API.

Philosophy:
- Single responsibility: Cost aggregation and query execution
- Internal implementation details (no public API)
- Self-contained and regeneratable

Public API (the "studs"):
    (None - all functions are internal helpers)
"""

import asyncio
import logging
from datetime import datetime

from azure.core.exceptions import HttpResponseError
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import (
    ExportType,
    QueryAggregation,
    QueryDataset,
    QueryDefinition,
    QueryFilter,
    QueryGrouping,
    QueryTimePeriod,
    TimeframeType,
)

logger = logging.getLogger(__name__)

__all__: list[str] = []


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
            granularity=None,
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
            granularity=None,
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
