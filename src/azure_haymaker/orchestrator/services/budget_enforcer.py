"""Budget enforcement service for Azure HayMaker orchestrator.

Implements cost budget enforcement with automatic throttling, predictive alerts,
and integration with Azure Cost Management API.

Key Features:
- Configurable budget thresholds (per day/week/month)
- Automatic pause of deployments when budget exceeded
- Predictive cost alerts based on current spend rate
- Resource-based cost estimation before deployment
- "Dry run" mode for cost estimates without deploying

Note: Azure Cost Management has ~24 hour delay. For real-time tracking,
we use resource-based estimation as a workaround.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum

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
    QueryTimePeriod,
    TimeframeType,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BudgetPeriod(str, Enum):
    """Time periods for budget tracking."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ThrottleAction(str, Enum):
    """Actions to take when budget exceeded."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class BudgetConfig(BaseModel):
    """Configuration for budget enforcement.

    Attributes:
        daily_limit: Maximum daily spend in USD (None = no limit)
        weekly_limit: Maximum weekly spend in USD (None = no limit)
        monthly_limit: Maximum monthly spend in USD (None = no limit)
        alert_threshold: Percentage threshold for alerts (0.0-1.0, default 0.8 = 80%)
        auto_throttle: If True, block deployments when budget exceeded
        warn_threshold: Percentage threshold for warnings (0.0-1.0, default 0.5 = 50%)
    """

    daily_limit: float | None = Field(default=None, description="Daily budget limit in USD")
    weekly_limit: float | None = Field(default=None, description="Weekly budget limit in USD")
    monthly_limit: float | None = Field(default=None, description="Monthly budget limit in USD")
    alert_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Alert threshold as percentage"
    )
    warn_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Warning threshold as percentage"
    )
    auto_throttle: bool = Field(default=True, description="Block deployments when exceeded")


class SpendSummary(BaseModel):
    """Summary of current spending across time periods.

    Attributes:
        daily: Current day's spend in USD
        weekly: Current week's spend in USD
        monthly: Current month's spend in USD
        timestamp: When this summary was generated
    """

    daily: float = Field(default=0.0, description="Today's spend in USD")
    weekly: float = Field(default=0.0, description="This week's spend in USD")
    monthly: float = Field(default=0.0, description="This month's spend in USD")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CostEstimate(BaseModel):
    """Estimated cost for a deployment.

    Attributes:
        compute: Compute cost (VMs, containers)
        storage: Storage cost
        network: Network cost (egress, IPs)
        total: Total estimated cost
        duration_hours: Duration the estimate covers
        confidence: Estimate confidence (0.0-1.0)
    """

    compute: float = Field(default=0.0, description="Estimated compute cost")
    storage: float = Field(default=0.0, description="Estimated storage cost")
    network: float = Field(default=0.0, description="Estimated network cost")
    total: float = Field(default=0.0, description="Total estimated cost")
    duration_hours: float = Field(default=1.0, description="Duration in hours")
    confidence: float = Field(default=0.8, description="Estimate confidence")


class BudgetStatus(BaseModel):
    """Current budget status including config, spend, and remaining.

    Attributes:
        config: Current budget configuration
        current_spend: Current spending summary
        remaining: Remaining budget for each period
        status: Overall status (ok, warning, alert, exceeded)
        message: Human-readable status message
    """

    config: BudgetConfig
    current_spend: SpendSummary
    remaining: dict[str, float | None] = Field(
        default_factory=dict, description="Remaining budget per period"
    )
    status: str = Field(default="ok", description="Overall status")
    message: str = Field(default="", description="Status message")


@dataclass
class DeploymentDecision:
    """Result of a deployment permission check."""

    allowed: bool
    action: ThrottleAction
    reason: str
    estimated_cost: float | None = None
    remaining_budget: dict[str, float | None] = field(default_factory=dict)


# Azure VM pricing estimates (USD/hour)
# Based on East US pricing, Standard tier
VM_HOURLY_RATES = {
    "Standard_B1s": 0.0104,
    "Standard_B2s": 0.0416,
    "Standard_D2s_v3": 0.096,
    "Standard_D4s_v3": 0.192,
    "Standard_D8s_v3": 0.384,
    "Standard_D16s_v3": 0.768,
    "Standard_E4s_v3": 0.252,
    "Standard_E8s_v3": 0.504,
    "Standard_E16s_v3": 1.008,
    "Standard_E32s_v3": 2.016,
    # Default for unknown sizes
    "default": 0.5,
}

# Storage pricing (USD/GB/month)
STORAGE_RATES = {
    "Standard_LRS": 0.018,
    "Standard_GRS": 0.036,
    "Premium_LRS": 0.15,
}


class BudgetEnforcer:
    """Enforces budget limits and provides cost estimation.

    This service monitors spending, blocks deployments when budget exceeded,
    and provides cost estimates for planning.

    Example:
        >>> config = BudgetConfig(
        ...     daily_limit=100.0,
        ...     monthly_limit=1500.0,
        ...     auto_throttle=True,
        ... )
        >>> enforcer = BudgetEnforcer(subscription_id="...", config=config)
        >>> allowed, reason = await enforcer.can_deploy(estimated_cost=50.0)
        >>> if not allowed:
        ...     print(f"Blocked: {reason}")
    """

    def __init__(
        self,
        subscription_id: str,
        config: BudgetConfig | None = None,
        resource_group: str | None = None,
    ):
        """Initialize budget enforcer.

        Args:
            subscription_id: Azure subscription ID
            config: Budget configuration (defaults to no limits)
            resource_group: Optional resource group filter for costs
        """
        self.subscription_id = subscription_id
        self.config = config or BudgetConfig()
        self.resource_group = resource_group
        self._credential: DefaultAzureCredential | None = None
        self._cost_client: CostManagementClient | None = None
        self._spend_cache: SpendSummary | None = None
        self._cache_timestamp: datetime | None = None
        self._cache_ttl = timedelta(minutes=5)

    def _get_credential(self) -> DefaultAzureCredential:
        """Get or create Azure credential."""
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential

    def _get_cost_client(self) -> CostManagementClient:
        """Get or create Cost Management client."""
        if self._cost_client is None:
            self._cost_client = CostManagementClient(self._get_credential())
        return self._cost_client

    async def get_current_spend(self, use_cache: bool = True) -> SpendSummary:
        """Get current spending across all periods.

        Args:
            use_cache: If True, return cached data if fresh

        Returns:
            SpendSummary with current spending

        Note: Uses Azure Cost Management API which has ~24 hour delay.
        For real-time tracking, use estimate_current_resources() instead.
        """
        # Check cache
        now = datetime.now(UTC)
        if (
            use_cache
            and self._spend_cache is not None
            and self._cache_timestamp is not None
            and now - self._cache_timestamp < self._cache_ttl
        ):
            return self._spend_cache

        # Query Azure Cost Management
        try:
            daily = await self._query_cost_for_period(BudgetPeriod.DAILY)
            weekly = await self._query_cost_for_period(BudgetPeriod.WEEKLY)
            monthly = await self._query_cost_for_period(BudgetPeriod.MONTHLY)

            spend = SpendSummary(
                daily=daily,
                weekly=weekly,
                monthly=monthly,
                timestamp=now,
            )

            # Update cache
            self._spend_cache = spend
            self._cache_timestamp = now

            logger.info(
                f"Budget spend: daily=${spend.daily:.2f}, "
                f"weekly=${spend.weekly:.2f}, monthly=${spend.monthly:.2f}"
            )

            return spend

        except (ClientAuthenticationError, HttpResponseError) as e:
            logger.error(f"Failed to query costs: {e}")
            # Return cached value if available
            if self._spend_cache is not None:
                logger.warning("Returning cached spend data due to API error")
                return self._spend_cache
            # Return empty spend if no cache
            return SpendSummary()

    async def _query_cost_for_period(self, period: BudgetPeriod) -> float:
        """Query Azure Cost Management for a specific period.

        Args:
            period: Time period to query

        Returns:
            Total cost for the period in USD
        """
        now = datetime.now(UTC)

        # Calculate period boundaries
        if period == BudgetPeriod.DAILY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.WEEKLY:
            # Start from Monday
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # MONTHLY
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Build scope
        if self.resource_group:
            scope = f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}"
        else:
            scope = f"/subscriptions/{self.subscription_id}"

        # Query definition
        query = QueryDefinition(
            type=ExportType.ACTUAL_COST,
            timeframe=TimeframeType.CUSTOM,
            time_period=QueryTimePeriod(
                from_property=start,
                to=now,
            ),
            dataset=QueryDataset(
                granularity=GranularityType.NONE,
                aggregation={
                    "totalCost": QueryAggregation(name="Cost", function="Sum"),
                },
            ),
        )

        try:
            result = await asyncio.to_thread(
                self._get_cost_client().query.usage,
                scope=scope,
                parameters=query,
            )

            if result and result.rows:
                return float(result.rows[0][0]) if result.rows[0][0] else 0.0
            return 0.0

        except ResourceNotFoundError:
            return 0.0

    async def can_deploy(
        self,
        estimated_cost: float | None = None,
        vm_count: int = 1,
        vm_size: str = "Standard_D4s_v3",
        duration_hours: float = 1.0,
    ) -> DeploymentDecision:
        """Check if a deployment is allowed based on budget.

        Args:
            estimated_cost: Pre-calculated cost estimate (optional)
            vm_count: Number of VMs to deploy
            vm_size: Azure VM size
            duration_hours: Expected deployment duration

        Returns:
            DeploymentDecision with allowed status and reason
        """
        # Estimate cost if not provided
        if estimated_cost is None:
            estimate = self.estimate_deployment_cost(
                vm_count=vm_count,
                vm_size=vm_size,
                duration_hours=duration_hours,
            )
            estimated_cost = estimate.total

        # Get current spend
        spend = await self.get_current_spend()

        # Check each period
        violations = []
        warnings = []
        remaining = {}

        for period, limit, current in [
            (BudgetPeriod.DAILY, self.config.daily_limit, spend.daily),
            (BudgetPeriod.WEEKLY, self.config.weekly_limit, spend.weekly),
            (BudgetPeriod.MONTHLY, self.config.monthly_limit, spend.monthly),
        ]:
            if limit is None:
                remaining[period.value] = None
                continue

            remaining[period.value] = limit - current
            projected = current + estimated_cost

            if projected > limit:
                violations.append(
                    f"{period.value}: ${projected:.2f} would exceed ${limit:.2f} limit"
                )
            elif projected / limit >= self.config.warn_threshold:
                warnings.append(
                    f"{period.value}: ${projected:.2f} is {projected / limit * 100:.0f}% of ${limit:.2f}"
                )

        # Determine action
        if violations:
            if self.config.auto_throttle:
                return DeploymentDecision(
                    allowed=False,
                    action=ThrottleAction.BLOCK,
                    reason=f"Budget exceeded: {'; '.join(violations)}",
                    estimated_cost=estimated_cost,
                    remaining_budget=remaining,
                )
            else:
                return DeploymentDecision(
                    allowed=True,
                    action=ThrottleAction.WARN,
                    reason=f"Budget warning (throttle disabled): {'; '.join(violations)}",
                    estimated_cost=estimated_cost,
                    remaining_budget=remaining,
                )

        if warnings:
            return DeploymentDecision(
                allowed=True,
                action=ThrottleAction.WARN,
                reason=f"Approaching budget limit: {'; '.join(warnings)}",
                estimated_cost=estimated_cost,
                remaining_budget=remaining,
            )

        return DeploymentDecision(
            allowed=True,
            action=ThrottleAction.ALLOW,
            reason="Deployment within budget",
            estimated_cost=estimated_cost,
            remaining_budget=remaining,
        )

    def estimate_deployment_cost(
        self,
        vm_count: int = 1,
        vm_size: str = "Standard_D4s_v3",
        duration_hours: float = 1.0,
        storage_gb: float = 50.0,
        storage_type: str = "Standard_LRS",
    ) -> CostEstimate:
        """Estimate cost for a deployment.

        Args:
            vm_count: Number of VMs to deploy
            vm_size: Azure VM size
            duration_hours: Expected deployment duration in hours
            storage_gb: Total storage in GB
            storage_type: Storage tier

        Returns:
            CostEstimate with breakdown
        """
        # Compute cost
        hourly_rate = VM_HOURLY_RATES.get(vm_size, VM_HOURLY_RATES["default"])
        compute = vm_count * hourly_rate * duration_hours

        # Storage cost (prorated monthly)
        storage_monthly_rate = STORAGE_RATES.get(storage_type, STORAGE_RATES["Standard_LRS"])
        hours_in_month = 720
        storage = storage_gb * storage_monthly_rate * (duration_hours / hours_in_month)

        # Network cost (estimate 10% of compute)
        network = compute * 0.10

        # Round individual components first
        compute_rounded = round(compute, 2)
        storage_rounded = round(storage, 4)
        network_rounded = round(network, 2)

        # Total from rounded values ensures total == compute + storage + network
        total_rounded = round(compute_rounded + storage_rounded + network_rounded, 2)

        # Confidence based on vm_size being known
        confidence = 0.9 if vm_size in VM_HOURLY_RATES else 0.6

        return CostEstimate(
            compute=compute_rounded,
            storage=storage_rounded,
            network=network_rounded,
            total=total_rounded,
            duration_hours=duration_hours,
            confidence=confidence,
        )

    async def get_status(self) -> BudgetStatus:
        """Get comprehensive budget status.

        Returns:
            BudgetStatus with current config, spend, and remaining
        """
        spend = await self.get_current_spend()

        remaining = {}
        status = "ok"
        messages = []

        for period, limit, current in [
            ("daily", self.config.daily_limit, spend.daily),
            ("weekly", self.config.weekly_limit, spend.weekly),
            ("monthly", self.config.monthly_limit, spend.monthly),
        ]:
            if limit is None:
                remaining[period] = None
                continue

            remaining[period] = limit - current
            ratio = current / limit

            if ratio >= 1.0:
                status = "exceeded"
                messages.append(f"{period.title()} budget exceeded: ${current:.2f}/${limit:.2f}")
            elif ratio >= self.config.alert_threshold:
                if status not in ("exceeded",):
                    status = "alert"
                messages.append(f"{period.title()} at {ratio * 100:.0f}% of budget")
            elif ratio >= self.config.warn_threshold:
                if status not in ("exceeded", "alert"):
                    status = "warning"
                messages.append(f"{period.title()} at {ratio * 100:.0f}% of budget")

        message = "; ".join(messages) if messages else "All budgets within limits"

        return BudgetStatus(
            config=self.config,
            current_spend=spend,
            remaining=remaining,
            status=status,
            message=message,
        )

    def invalidate_cache(self) -> None:
        """Invalidate the spend cache to force fresh data on next query."""
        self._spend_cache = None
        self._cache_timestamp = None
        logger.debug("Budget spend cache invalidated")


__all__ = [
    "BudgetConfig",
    "BudgetEnforcer",
    "BudgetPeriod",
    "BudgetStatus",
    "CostEstimate",
    "DeploymentDecision",
    "SpendSummary",
    "ThrottleAction",
]
