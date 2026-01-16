# Cost Management Guide

This document describes Azure HayMaker's cost management strategy, including resource cleanup and budget enforcement.

## Current State vs Target State

### Problem: Duplicate Resources ($3,164/month waste)

Due to deployment iterations, the infrastructure accumulated duplicate resources:

| Resource Type     | Current Count | Target | Monthly Cost | Waste      |
|-------------------|---------------|--------|--------------|------------|
| Key Vaults        | 21            | 1      | $0.63        | $0.60      |
| Service Bus       | 21            | 1      | $210         | $200       |
| Function Apps     | 21            | 1      | $1,533       | $1,460     |
| Storage Accounts  | 21            | 1      | $420         | $400       |
| **Total**         |               |        | **$3,164**   | **$2,060** |

### Target State (Post-Cleanup)

- **1 Key Vault**: `haymaker-dev-yow3ex-kv`
- **1 Service Bus**: `haymaker-dev-yow3ex-bus`
- **1 Storage Account**: `haymakerdevelopment`
- **1 VM**: 64GB orchestrator VM
- **Monthly Cost**: ~$500

### Expected Savings

- **Monthly Savings**: $2,664 (84%)
- **Annual Savings**: ~$32,000

## Cleanup Tools

### Resource Cleanup Script

The primary cleanup tool is `scripts/resource-cleanup.py`:

```bash
# Show current resource status
python scripts/resource-cleanup.py --status

# Preview what would be deleted (dry run)
python scripts/resource-cleanup.py --dry-run

# Execute cleanup (destructive!)
python scripts/resource-cleanup.py --execute

# Custom resource group and keep pattern
python scripts/resource-cleanup.py --resource-group mygroup --keep-pattern latest --dry-run
```

### Legacy Scripts

The following legacy scripts are also available:

- `scripts/cleanup-old-function-apps.sh` - Delete old Function Apps only
- `scripts/complete-cleanup.sh` - Interactive cleanup (bash)
- `scripts/estimate-costs.sh` - Quick cost estimation
- `scripts/check-infrastructure.sh` - List current resources

## Budget Enforcement

### BudgetEnforcer Service

The `BudgetEnforcer` service prevents runaway costs by:

1. **Budget Thresholds**: Configurable limits per day/week/month
2. **Automatic Throttling**: Pauses deployments when budget exceeded
3. **Predictive Alerts**: Warns when on track to exceed budget
4. **Dry Run Mode**: Estimates costs before deployment

### Configuration

Budget configuration is stored per schedule/tenant:

```python
from azure_haymaker.orchestrator.services.budget_enforcer import (
    BudgetEnforcer,
    BudgetConfig,
)

# Create budget configuration
config = BudgetConfig(
    daily_limit=100.0,      # $100/day
    weekly_limit=500.0,     # $500/week
    monthly_limit=1500.0,   # $1500/month
    alert_threshold=0.8,    # Alert at 80% of limit
    auto_throttle=True,     # Pause deployments when exceeded
)

# Initialize enforcer
enforcer = BudgetEnforcer(
    subscription_id="your-subscription-id",
    config=config,
)

# Check if deployment is allowed
allowed, reason = await enforcer.can_deploy(estimated_cost=50.0)
if not allowed:
    print(f"Deployment blocked: {reason}")

# Get current spend
spend = await enforcer.get_current_spend()
print(f"Today: ${spend.daily:.2f}, Week: ${spend.weekly:.2f}, Month: ${spend.monthly:.2f}")
```

### Dry Run Mode

Estimate costs before deployment:

```python
# Estimate deployment cost
estimate = await enforcer.estimate_deployment_cost(
    vm_count=5,
    vm_size="Standard_D4s_v3",
    duration_hours=4,
)

print(f"Estimated cost: ${estimate.total:.2f}")
print(f"VM cost: ${estimate.compute:.2f}")
print(f"Storage cost: ${estimate.storage:.2f}")
print(f"Network cost: ${estimate.network:.2f}")
```

### Integration with Orchestrator

The BudgetEnforcer integrates with the orchestrator's deployment flow:

1. Before deployment, check `can_deploy()` with estimated cost
2. If blocked, return appropriate error to caller
3. Track actual spend after deployment completes
4. Send alerts via webhook when thresholds approached

## Azure Cost Management API

### Query Current Costs

```python
from azure_haymaker.orchestrator.cost_query import get_cost_summary

# Get costs for a specific run
summary = await get_cost_summary(
    subscription_id="your-subscription-id",
    run_id="run-uuid-here",
)

print(f"Total cost: ${summary.total_cost:.2f}")
for resource_type, cost in summary.cost_by_resource_type.items():
    print(f"  {resource_type}: ${cost:.2f}")
```

### Important: 24-Hour Delay

Azure Cost Management has approximately a 24-hour delay before cost data becomes available. For real-time cost tracking, use resource-based estimation:

```python
# Real-time estimation (no delay)
estimate = await enforcer.estimate_current_resources()

# Azure Cost Management (24hr delay, accurate)
actual = await get_cost_summary(subscription_id, run_id)
```

## Best Practices

### 1. Regular Cleanup

Run the cleanup script monthly or after major deployments:

```bash
# Add to cron or CI/CD
python scripts/resource-cleanup.py --dry-run
```

### 2. Budget Alerts

Set up Azure Budget alerts in addition to the BudgetEnforcer:

```bash
az consumption budget create \
  --budget-name "HayMaker-Monthly" \
  --resource-group haymaker-dev-rg \
  --amount 1500 \
  --time-grain Monthly \
  --category Cost
```

### 3. Resource Tagging

All HayMaker resources should be tagged for tracking:

- `AzureHayMaker-managed: true`
- `Environment: dev|staging|prod`
- `RunId: <uuid>`
- `Scenario: <scenario-name>`

### 4. Monitor Trends

Use the metrics API to track cost trends:

```bash
# Get cost trends
curl http://localhost:8000/api/v1/metrics/costs?period=30d
```

## Troubleshooting

### Cleanup Fails for Key Vault

Key Vaults have soft delete enabled. If delete fails:

```bash
# Check soft-deleted vaults
az keyvault list-deleted

# Purge if needed (only in non-prod!)
az keyvault purge --name vault-name
```

### Budget Enforcer Not Blocking

Check the configuration and current spend:

```python
# Debug budget status
status = await enforcer.get_status()
print(f"Config: {status.config}")
print(f"Current spend: {status.current_spend}")
print(f"Remaining budget: {status.remaining}")
```

### Cost Data Missing

Azure Cost Management delay means recent costs won't appear:

1. Wait 24-48 hours for accurate data
2. Use resource estimation for immediate feedback
3. Check that resources have proper tags

## Related Issues

- #14 - URGENT: Cost Cleanup - $3,164/month in duplicate resources
- #128 - Cost Budget Enforcement and Alerts
- #126 - Multi-Tenant Resource Isolation (budget per tenant)

## References

- [Azure Cost Management API](https://docs.microsoft.com/en-us/azure/cost-management-billing/costs/)
- [Azure Budgets](https://docs.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)
- [Resource Tagging Best Practices](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/tag-resources)
