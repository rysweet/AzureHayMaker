# Tenant Resource Isolation

Per-tenant resource tagging and cost tracking for Azure HayMaker multi-tenant deployments.

---

## Contents

- [Overview](#overview)
- [Resource Tagging](#resource-tagging)
- [Cost Tracking](#cost-tracking)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

Tenant Resource Isolation enables per-tenant cost allocation and resource tracking in Azure HayMaker. When enabled, all Azure resources deployed by the orchestrator are tagged with tenant and execution identifiers, enabling:

- **Cost Attribution**: Track Azure spend per tenant for accurate billing
- **Resource Visibility**: Query and filter resources by tenant
- **Audit Compliance**: Maintain clear ownership records for all provisioned resources
- **Cleanup Safety**: Delete resources by tenant without affecting other tenants

### How It Works

1. **Tagging at Deployment**: When a container or resource is deployed, the system automatically applies tenant-specific tags
2. **Cost Aggregation**: Azure Cost Management data is queried and grouped by tenant tags
3. **API Access**: Tenants can retrieve their cost summaries via the cost endpoint

---

## Resource Tagging

### Standard Tags Applied

Every Azure resource deployed by Azure HayMaker receives these tags:

| Tag Name | Description | Example Value |
|:---------|:------------|:--------------|
| `TenantId` | Unique tenant identifier | `tenant-acme-corp` |
| `ExecutionId` | Unique execution/run identifier | `exec-3e598ac3-7b1b` |
| `AzureHayMaker-managed` | Marks resource as HayMaker-managed | `true` |
| `CreatedAt` | ISO 8601 timestamp of creation | `2026-01-15T10:30:00Z` |
| `Scenario` | Scenario that created this resource | `compute-01-linux-vm-web-server` |

Custom tags (like `Environment`) can be added via the `additional_tags` parameter.

### Using the Resource Tagging Module

The `resource_tagging` module provides centralized tag generation:

```python
from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

# Generate tags for a deployment
tags = generate_resource_tags(
    tenant_id="tenant-acme-corp",
    execution_id="exec-3e598ac3-7b1b",
    scenario_name="compute-01-linux-vm-web-server",
    additional_tags={"Environment": "prod"}
)

# Result:
# {
#     "TenantId": "tenant-acme-corp",
#     "ExecutionId": "exec-3e598ac3-7b1b",
#     "AzureHayMaker-managed": "true",
#     "CreatedAt": "2026-01-15T10:30:00Z",
#     "Scenario": "compute-01-linux-vm-web-server",
#     "Environment": "prod"
# }
```

### Container Deployment Integration

The container deployer automatically applies tenant tags to all Container Apps:

```python
from azure_haymaker.orchestrator.container_deployer import ContainerDeployer

deployer = ContainerDeployer(
    subscription_id="your-subscription-id",
    resource_group="haymaker-rg"
)

# Tags are applied automatically when tenant_id is provided
result = await deployer.deploy_container(
    container_name="scenario-agent",
    image="haymaker.azurecr.io/agent:latest",
    tenant_id="tenant-acme-corp",  # Enables tenant tagging
    execution_id="exec-3e598ac3-7b1b"
)
```

### Querying Tagged Resources

Use Azure CLI to find resources by tenant:

```bash
# List all resources for a specific tenant
az resource list \
  --tag TenantId=tenant-acme-corp \
  --output table

# List Container Apps for a tenant
az containerapp list \
  --resource-group haymaker-rg \
  --query "[?tags.TenantId=='tenant-acme-corp']" \
  --output table

# Count resources by tenant
az resource list \
  --tag AzureHayMaker-managed=true \
  --query "[].tags.TenantId" \
  --output tsv | sort | uniq -c
```

---

## Cost Tracking

### Per-Tenant Cost Queries

The `cost_query` module provides tenant-scoped cost summaries:

```python
from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

# Get cost summary for a tenant
summary = await get_tenant_cost_summary(
    subscription_id="your-subscription-id",
    tenant_id="tenant-acme-corp",
    start_date="2026-01-01",
    end_date="2026-01-31"
)

print(f"Total cost: ${summary.total_cost:.2f}")
print(f"Compute: ${summary.cost_by_service.get('Microsoft.App', 0):.2f}")
print(f"Storage: ${summary.cost_by_service.get('Microsoft.Storage', 0):.2f}")

# Output:
# Total cost: $234.56
# Compute: $198.23
# Storage: $36.33
```

### Cost Summary Response Structure

```python
@dataclass
class TenantCostSummary:
    tenant_id: str
    start_date: str
    end_date: str
    total_cost: float
    currency: str  # "USD"
    cost_by_service: dict[str, float]
    cost_by_execution: dict[str, float]
    resource_count: int
    last_updated: str  # ISO 8601 timestamp
```

### Cost Breakdown by Execution

Track costs per execution run:

```python
summary = await get_tenant_cost_summary(
    subscription_id="your-subscription-id",
    tenant_id="tenant-acme-corp",
    start_date="2026-01-15",
    end_date="2026-01-16"
)

for execution_id, cost in summary.cost_by_execution.items():
    print(f"Execution {execution_id}: ${cost:.2f}")

# Output:
# Execution exec-3e598ac3-7b1b: $45.23
# Execution exec-8f2a1bc4-9d3e: $67.89
```

---

## API Reference

### GET /api/v1/tenants/{tenant_id}/costs

Retrieve cost summary for a specific tenant.

**Endpoint**: `GET /api/v1/tenants/{tenant_id}/costs`

**Path Parameters**:

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `tenant_id` | string | Unique tenant identifier |

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|:----------|:-----|:---------|:--------|:------------|
| `start_date` | string | No | 30 days ago | Start date (YYYY-MM-DD) |
| `end_date` | string | No | Today | End date (YYYY-MM-DD) |
| `group_by` | string | No | `service` | Group costs by: `service`, `execution`, `day` |

**Response** (200 OK):

```json
{
  "tenant_id": "tenant-acme-corp",
  "start_date": "2026-01-01",
  "end_date": "2026-01-31",
  "total_cost": 234.56,
  "currency": "USD",
  "cost_by_service": {
    "Microsoft.App": 198.23,
    "Microsoft.Storage": 36.33
  },
  "cost_by_execution": {
    "exec-3e598ac3-7b1b": 112.34,
    "exec-8f2a1bc4-9d3e": 122.22
  },
  "resource_count": 15,
  "last_updated": "2026-01-17T14:30:00Z"
}
```

**Example Request**:

```bash
# Get costs for last 30 days (default)
curl https://haymaker-fastapi-app.azurewebsites.net/api/v1/tenants/tenant-acme-corp/costs

# Get costs for specific date range
curl "https://haymaker-fastapi-app.azurewebsites.net/api/v1/tenants/tenant-acme-corp/costs?start_date=2026-01-01&end_date=2026-01-15"

# Get costs grouped by day
curl "https://haymaker-fastapi-app.azurewebsites.net/api/v1/tenants/tenant-acme-corp/costs?group_by=day"
```

**Python Example**:

```python
import requests

BASE_URL = "https://haymaker-fastapi-app.azurewebsites.net"
tenant_id = "tenant-acme-corp"

# Get tenant costs
response = requests.get(
    f"{BASE_URL}/api/v1/tenants/{tenant_id}/costs",
    params={
        "start_date": "2026-01-01",
        "end_date": "2026-01-31"
    }
)

costs = response.json()
print(f"Tenant {costs['tenant_id']} total: ${costs['total_cost']:.2f}")
```

**Error Responses**:

| Status | Error Code | Description |
|:-------|:-----------|:------------|
| 400 | `INVALID_DATE_RANGE` | Invalid date format or end_date before start_date |
| 404 | `TENANT_NOT_FOUND` | Tenant does not exist or has no resources |
| 503 | `COST_DATA_UNAVAILABLE` | Azure Cost Management API temporarily unavailable |

---

## Configuration

### Environment Variables

Configure tenant isolation behavior via environment variables:

| Variable | Default | Description |
|:---------|:--------|:------------|
| `HAYMAKER_ENABLE_TENANT_TAGGING` | `true` | Enable/disable tenant tagging |
| `HAYMAKER_DEFAULT_TENANT_ID` | `default` | Tenant ID when none specified |
| `HAYMAKER_COST_QUERY_CACHE_TTL` | `3600` | Cost data cache TTL in seconds |

### Tenant Registration

Register tenants before use:

```python
from azure_haymaker.orchestrator.tenant_registry import TenantRegistry

registry = TenantRegistry()

# Register a new tenant
registry.register_tenant(
    tenant_id="tenant-acme-corp",
    tenant_name="Acme Corporation",
    azure_subscription_id="sub-12345",
    resource_group_prefix="acme",
    budget_limit_monthly=1500.00
)
```

### Budget Limits

Set per-tenant budget limits:

```python
from azure_haymaker.orchestrator.services.budget_enforcer import BudgetConfig

config = BudgetConfig(
    daily_limit=50.0,
    weekly_limit=250.0,
    monthly_limit=1000.0,
    alert_threshold=0.8  # Alert at 80%
)
```

---

## Troubleshooting

### Cost Data Shows $0 or Missing Data

**Cause**: Azure Cost Management has a 24-48 hour delay before cost data becomes available.

**Solution**:
- Wait 24-48 hours after resource deployment for accurate costs
- Use the `last_updated` field to verify data freshness
- For immediate estimates, use resource-based estimation instead

```python
# Check when cost data was last updated
summary = await get_tenant_cost_summary(...)
print(f"Data as of: {summary.last_updated}")

# If data is stale, costs may be incomplete
from datetime import datetime, timedelta
last_update = datetime.fromisoformat(summary.last_updated.replace('Z', '+00:00'))
if datetime.now(last_update.tzinfo) - last_update > timedelta(hours=48):
    print("Warning: Cost data may be incomplete")
```

### Resources Not Tagged

**Cause**: Deployment occurred before tenant tagging was enabled, or `tenant_id` was not provided.

**Solution**:
1. Verify `HAYMAKER_ENABLE_TENANT_TAGGING=true` is set
2. Ensure `tenant_id` is passed to deployment functions
3. Manually tag existing resources:

```bash
# Tag existing resources
az resource tag \
  --ids /subscriptions/.../resourceGroups/haymaker-rg/providers/... \
  --tags TenantId=tenant-acme-corp
```

### Cost Query Returns 503 Error

**Cause**: Azure Cost Management API is rate-limited or temporarily unavailable.

**Solution**:
- Implement exponential backoff retry logic
- Check Azure service health status
- Use cached cost data when available

```python
import time

max_retries = 3
for attempt in range(max_retries):
    try:
        summary = await get_tenant_cost_summary(...)
        break
    except CostDataUnavailableError:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
        else:
            raise
```

### Tenant Not Found Error

**Cause**: Querying costs for an unregistered tenant or tenant with no deployed resources.

**Solution**:
1. Verify tenant is registered in the tenant registry
2. Confirm the tenant has deployed resources with proper tags
3. Check that the date range includes deployments

```bash
# Verify tenant has tagged resources
az resource list \
  --tag TenantId=tenant-acme-corp \
  --query "length(@)"

# Output: 0 means no resources exist for this tenant
```

---

## Related Documentation

- [Cost Management Guide](./COST_MANAGEMENT.md) - Budget enforcement and cleanup
- [Multi-Tenant Getting Started](./GETTING_STARTED_126_MULTI_TENANT.md) - Full multi-tenant setup
- [API Reference](./api.md) - Complete API documentation

## Source Code References

- [`resource_tagging.py`](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/resource_tagging.py) - Tag generation module
- [`container_deployer.py`](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/container_deployer.py) - Container deployment with tagging
- [`cost_query.py`](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/cost_query.py) - Cost query functions

---

**Version**: 1.0.0 | **Last Updated**: 2026-01-17 | **Issue**: [#126](https://github.com/rysweet/AzureHayMaker/issues/126)
