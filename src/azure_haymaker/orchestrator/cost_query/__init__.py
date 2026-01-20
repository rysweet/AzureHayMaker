"""Cost query module for Azure HayMaker orchestrator.

This module queries Azure Cost Management API to retrieve cost data
for specific execution runs filtered by tags.

Azure Cost Management has approximately a 24-hour delay before cost data
becomes available, so recent runs may return empty or partial data.

This module has been refactored into 3 sub-modules for better organization:
- models: Pydantic data models (CostSummary, TenantCostSummary)
- aggregation: Internal cost aggregation logic
- queries: Public API functions

The public API remains unchanged for backward compatibility.
"""

from .models import CostSummary, TenantCostSummary
from .queries import (
    DEFAULT_QUERY_PERIOD_DAYS,
    get_cost_summary,
    get_tenant_cost_summary,
)

__all__ = [
    "CostSummary",
    "TenantCostSummary",
    "get_cost_summary",
    "get_tenant_cost_summary",
    "DEFAULT_QUERY_PERIOD_DAYS",
]
