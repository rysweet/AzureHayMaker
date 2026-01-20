"""Public API for Azure Cost Management queries.

This module provides the public API for querying cost data from
Azure Cost Management, filtered by tags and grouped by various dimensions.

Azure Cost Management has approximately a 24-hour delay before cost data
becomes available, so recent runs may return empty or partial data.

Philosophy:
- Single responsibility: Public API for cost queries
- Clear error handling and logging
- Self-contained and regeneratable

Public API (the "studs"):
    get_cost_summary: Query costs for an execution run
    get_tenant_cost_summary: Query costs for a tenant
    DEFAULT_QUERY_PERIOD_DAYS: Default query period constant
"""

import logging
from datetime import UTC, datetime, timedelta

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient

from azure_haymaker.exceptions import CostQueryError

from .aggregation import _query_costs_grouped_by, _query_tenant_costs
from .models import CostSummary, TenantCostSummary

logger = logging.getLogger(__name__)

# Default cost query period in days
DEFAULT_QUERY_PERIOD_DAYS = 30

__all__ = [
    "get_cost_summary",
    "get_tenant_cost_summary",
    "DEFAULT_QUERY_PERIOD_DAYS",
]


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
