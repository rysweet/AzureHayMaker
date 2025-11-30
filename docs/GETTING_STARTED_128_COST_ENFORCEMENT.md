# Getting Started: Cost Budget Enforcement (Issue #128)

**Your complete guide to implementing Issue #128**

**Priority**: P1-High | **Effort**: 1.5 weeks | **ROI**: 184%

---

## What You're Building

Automatic cost budget enforcement with throttling, alerts, and forecasting to prevent runaway costs.

**Why It Matters**: Misconfigured schedules can cause $500K+ cloud bill. Prevents financial disasters.

**Business Value**: $98K/year (risk mitigation + manual monitoring elimination + optimization)

---

## Before You Start (15 minutes)

### Understand Azure Cost Management API

**Resources**:
- [Azure Cost Management API](https://learn.microsoft.com/en-us/rest/api/cost-management/)
- Current implementation: `src/azure_haymaker/orchestrator/cost_query.py` (has 24-hour delay limitation)

### Key Challenge: Real-Time Cost Estimation

**Problem**: Azure Cost Management API has 24-hour delay
**Solution**: Estimate costs in real-time based on resource usage + Azure pricing API

---

## Phase 1: Budget Configuration (Days 1-2)

### Create Budget Config Model

**File**: `src/azure_haymaker/models/budget.py` (NEW)

```python
from pydantic import BaseModel
from typing import Literal

class BudgetConfig(BaseModel):
    """Budget configuration per schedule or tenant."""

    schedule_id: str
    tenant_id: str | None = None

    # Budget limits
    daily_limit_usd: float = 100.0
    weekly_limit_usd: float = 500.0
    monthly_limit_usd: float = 2000.0

    # Thresholds for alerts (percentage of limit)
    warning_threshold: float = 0.80  # 80%
    critical_threshold: float = 0.95  # 95%

    # Actions when threshold exceeded
    throttle_at_warning: bool = False
    throttle_at_critical: bool = True
    pause_at_limit: bool = True

class BudgetStatus(BaseModel):
    """Current budget utilization status."""

    period: Literal["daily", "weekly", "monthly"]
    limit_usd: float
    spent_usd: float
    remaining_usd: float
    utilization_percent: float
    forecast_end_of_period_usd: float
    is_over_budget: bool
    throttled: bool
```

### Store Budget Configs

**File**: `src/azure_haymaker/orchestrator/budget_storage.py` (NEW)

```python
# Store in Cosmos DB or Table Storage
# Key: schedule_id or tenant_id
# Value: BudgetConfig
```

---

## Phase 2: Cost Estimator (Days 3-5)

**Challenge**: Estimate costs WITHOUT 24-hour delay

### Approach: Pre-Execution Cost Estimation

**File**: `src/azure_haymaker/orchestrator/cost_estimator.py` (NEW)

```python
class CostEstimator:
    """Estimates Azure resource costs before deployment."""

    # Azure pricing (approximate, update periodically)
    PRICING = {
        "container_app": {
            "vCPU_hour": 0.000024,  # Per vCPU-second
            "memory_gb_hour": 0.000003,  # Per GB-second
        },
        "storage": {
            "transaction": 0.0004,  # Per 10K transactions
            "data_gb": 0.02,  # Per GB/month
        },
        "m365_api_calls": 0.0,  # Graph API is free
    }

    def estimate_scenario_cost(
        self,
        scenario: str,
        duration_hours: int
    ) -> float:
        """Estimate cost for running a scenario."""

        # Get scenario resource requirements
        resources = self.get_scenario_resources(scenario)

        cost = 0.0

        # Container Apps cost
        vcpu = resources.get("vcpu", 0.25)
        memory_gb = resources.get("memory_gb", 0.5)
        cost += duration_hours * (
            vcpu * self.PRICING["container_app"]["vCPU_hour"] +
            memory_gb * self.PRICING["container_app"]["memory_gb_hour"]
        )

        # Storage cost (minimal for short runs)
        # API call costs (usually free)

        return cost

    def estimate_execution_cost(self, request: ExecutionRequest) -> float:
        """Estimate total cost for execution request."""
        total = 0.0
        for scenario in request.scenarios:
            total += self.estimate_scenario_cost(scenario, request.duration_hours)
        return total
```

---

## Phase 3: Budget Enforcer Service (Days 6-8)

**File**: `src/azure_haymaker/orchestrator/budget_enforcer.py` (NEW)

```python
class BudgetEnforcer:
    """Enforces budget limits with automatic throttling."""

    def __init__(self):
        self.cost_estimator = CostEstimator()
        self.budget_storage = BudgetStorage()

    async def check_budget_before_execution(
        self,
        schedule_id: str,
        request: ExecutionRequest
    ) -> tuple[bool, BudgetStatus]:
        """Check if execution would exceed budget.

        Returns:
            (allowed, budget_status)
        """

        # Get budget config
        config = await self.budget_storage.get_budget(schedule_id)

        # Estimate cost of this execution
        estimated_cost = self.cost_estimator.estimate_execution_cost(request)

        # Get current spending (from Cost Management API)
        current_spent = await self.get_current_spending(schedule_id, period="daily")

        # Check if would exceed limit
        projected_total = current_spent + estimated_cost

        if projected_total > config.daily_limit_usd:
            # Budget would be exceeded
            return False, BudgetStatus(
                period="daily",
                limit_usd=config.daily_limit_usd,
                spent_usd=current_spent,
                remaining_usd=config.daily_limit_usd - current_spent,
                utilization_percent=(current_spent / config.daily_limit_usd) * 100,
                forecast_end_of_period_usd=projected_total,
                is_over_budget=True,
                throttled=True
            )

        # Budget OK
        return True, BudgetStatus(...)

    async def get_current_spending(self, schedule_id: str, period: str) -> float:
        """Get actual spending from Azure Cost Management."""
        # Query Cost Management API
        # Filter by tags: schedule_id, date range
        # Return total cost
```

---

## Phase 4: Integrate with Orchestrator (Days 9-10)

### Add Budget Check to Execution Endpoint

**File**: `src/orchestrator_server.py`

```python
from azure_haymaker.orchestrator.budget_enforcer import BudgetEnforcer

budget_enforcer = BudgetEnforcer()

@app.post("/api/execute")
async def execute(request: ExecutionRequest):
    # Check budget BEFORE execution
    allowed, budget_status = await budget_enforcer.check_budget_before_execution(
        schedule_id=request.schedule_id,  # Assuming schedule_id in request
        request=request
    )

    if not allowed:
        # Budget would be exceeded - reject request
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Budget limit would be exceeded",
                "budget_status": budget_status.model_dump(),
                "message": f"Daily budget: ${budget_status.limit_usd}, "
                          f"current spend: ${budget_status.spent_usd}, "
                          f"would exceed by: ${budget_status.spent_usd + estimated_cost - budget_status.limit_usd}"
            }
        )

    # Budget OK - proceed with execution
    result = await orchestrate_execution(request)
    return result
```

### Add Budget Status Endpoint

```python
@app.get("/api/budgets/{schedule_id}/status")
async def get_budget_status(schedule_id: str, period: str = "daily"):
    """Get current budget utilization."""
    status = await budget_enforcer.get_budget_status(schedule_id, period)
    return status
```

---

## Phase 5: Alerts & Webhooks (Days 11-12)

### Budget Alert System

**File**: `src/azure_haymaker/orchestrator/budget_alerts.py` (NEW)

```python
async def check_and_alert():
    """Check all budgets and send alerts if thresholds exceeded."""

    for schedule in get_all_schedules():
        config = get_budget(schedule.id)
        status = await budget_enforcer.get_budget_status(schedule.id, "daily")

        # Check warning threshold (80%)
        if status.utilization_percent >= config.warning_threshold * 100:
            await send_alert(
                level="warning",
                message=f"Budget {status.utilization_percent:.1f}% utilized for {schedule.id}",
                budget_status=status
            )

        # Check critical threshold (95%)
        if status.utilization_percent >= config.critical_threshold * 100:
            await send_alert(
                level="critical",
                message=f"Budget {status.utilization_percent:.1f}% utilized - throttling enabled",
                budget_status=status
            )

            # Enable throttling if configured
            if config.throttle_at_critical:
                await enable_throttling(schedule.id)
```

### Integrate with Webhook System

Use existing webhook system (`src/azure_haymaker/orchestrator/webhooks.py`):

```python
async def notify_budget_alert(level: str, schedule_id: str, budget_status: BudgetStatus):
    """Send budget alert via webhook."""
    payload = {
        "event_type": "budget_alert",
        "level": level,
        "schedule_id": schedule_id,
        "budget_status": budget_status.model_dump()
    }
    # Send to configured webhook URL
```

---

## Phase 6: Forecasting (Days 13-14)

### Cost Forecast Engine

**File**: `src/azure_haymaker/orchestrator/cost_forecaster.py` (NEW)

```python
def forecast_end_of_month_cost(schedule_id: str) -> float:
    """Forecast end-of-month cost based on current spend rate."""

    # Get spending history (last 7 days)
    daily_costs = get_daily_costs(schedule_id, days=7)

    # Calculate average daily spend
    avg_daily = sum(daily_costs) / len(daily_costs)

    # Days remaining in month
    days_in_month = 30
    days_elapsed = get_days_elapsed_this_month()
    days_remaining = days_in_month - days_elapsed

    # Forecast
    spent_so_far = sum(daily_costs)
    projected_additional = avg_daily * days_remaining
    forecast_total = spent_so_far + projected_additional

    return forecast_total
```

---

## Testing

### Unit Tests

```python
def test_budget_enforcer_rejects_over_budget():
    """Verify enforcer blocks execution when budget exceeded."""
    enforcer = BudgetEnforcer()

    # Set low budget
    config = BudgetConfig(daily_limit_usd=10.0)

    # Mock current spending at $9
    # Request would cost $5 (total $14, over limit)
    allowed, status = enforcer.check_budget_before_execution(...)

    assert allowed is False
    assert status.is_over_budget is True

def test_forecast_accuracy():
    """Verify cost forecast within 20% of actual."""
    # Use historical data
    # Compare forecast vs. actual
    # Assert error <20%
```

### E2E Testing (MANDATORY)

```bash
# Configure low budget for testing
export DAILY_BUDGET_USD=50

# Start orchestrator
uvicorn orchestrator_server:app

# Execute scenarios until budget hit
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/execute \
    -H "Content-Type: application/json" \
    -d '{"scenarios":["compute-01-linux-vm-web-server"],"duration_hours":1}'
  sleep 5
done

# Verify:
# - Eventually get 429 error (budget exceeded)
# - Alert webhook fired
# - No scenarios executed after budget limit
# - Budget status API shows correct utilization
```

---

## Success Criteria

- [ ] Budget enforcement working (blocks over-budget requests)
- [ ] Alerts fire at 80% and 95% thresholds
- [ ] Cost estimation within 30% of actual (challenging given pricing complexity)
- [ ] Forecasting within 20% accuracy
- [ ] Zero manual cost overrun interventions after deployment
- [ ] Webhook notifications working

---

**Issue**: [#128](https://github.com/rysweet/AzureHayMaker/issues/128)

**Milestone**: [Q2 2026](https://github.com/rysweet/AzureHayMaker/milestone/2)

💰 **Ready to enforce those budgets? Follow Phase 1 above!**
