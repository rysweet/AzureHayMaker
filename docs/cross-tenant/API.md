# Cross-Tenant API Reference

This document describes the API endpoints for cross-tenant orchestration.

## Authentication

All API endpoints require authentication. Set the `Authorization` header:

```bash
curl -H "Authorization: Bearer <access_token>" https://your-orchestrator/api/...
```

Obtain tokens via Azure AD app registration or managed identity.

## Base URL

```
https://haymaker-fastapi-app.azurewebsites.net
```

Or your custom orchestrator deployment URL.

## Endpoints

### Single-Tenant Execution

#### POST /api/execute

Trigger scenario execution in the configured target tenant.

**Request:**

```bash
curl -X POST https://your-orchestrator/api/execute \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "skip_validation": false
  }'
```

**Request Body (optional):**

| Field | Type | Default | Description |
|:------|:-----|:--------|:------------|
| `skip_validation` | boolean | `false` | Skip environment validation |

**Response:**

```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "started_at": "2024-01-15T10:30:00Z",
  "trace_id": "abc123def456"
}
```

**Status Codes:**

| Code | Description |
|:-----|:------------|
| 200 | Execution started |
| 401 | Authentication required |
| 500 | Server error |

---

### Multi-Tenant Execution

#### POST /api/execute/multi-tenant

Trigger scenario execution across all enabled tenants in the registry.

**Request:**

```bash
curl -X POST https://your-orchestrator/api/execute/multi-tenant \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_ids": ["tenant-id-1", "tenant-id-2"],
    "scenarios": ["compute-01-linux-vm-web-server"],
    "scenario_count": 5
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `tenant_ids` | string[] | No | Specific tenants to target (default: all enabled) |
| `scenarios` | string[] | No | Specific scenarios to run (default: random selection) |
| `scenario_count` | integer | No | Number of scenarios per tenant (default: config value) |
| `skip_validation` | boolean | No | Skip environment validation (default: false) |

**Response:**

```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "started_at": "2024-01-15T10:30:00Z",
  "tenants": [
    {
      "tenant_id": "tenant-id-1",
      "display_name": "Customer A",
      "status": "pending"
    },
    {
      "tenant_id": "tenant-id-2",
      "display_name": "Customer B",
      "status": "pending"
    }
  ]
}
```

---

### Execution Status

#### GET /api/executions/{execution_id}

Get status of an execution.

**Request:**

```bash
curl https://your-orchestrator/api/executions/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>"
```

**Response:**

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2024-01-15T10:30:00Z",
  "status": "running",
  "phases": {
    "validation": {
      "status": "passed",
      "checks": [...]
    },
    "selection": {
      "status": "completed",
      "scenario_count": 5,
      "scenarios": ["compute-01-linux-vm-web-server", "databases-02-cosmos-db", ...]
    },
    "provisioning": {
      "status": "completed",
      "service_principals": {
        "requested": 5,
        "created": 5,
        "failed": 0
      },
      "container_apps": {
        "requested": 5,
        "deployed": 5,
        "failed": 0
      }
    },
    "monitoring": {
      "status_checks": [...],
      "log_messages": 1250,
      "resource_count": 23
    }
  },
  "trace_id": "abc123def456"
}
```

---

#### GET /api/executions/{execution_id}/tenants

Get per-tenant status for a multi-tenant execution.

**Request:**

```bash
curl https://your-orchestrator/api/executions/550e8400-e29b-41d4-a716-446655440000/tenants \
  -H "Authorization: Bearer <token>"
```

**Response:**

```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenants": [
    {
      "tenant_id": "12345678-1234-1234-1234-123456789abc",
      "display_name": "Customer A",
      "status": "completed",
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T18:45:00Z",
      "scenarios_completed": 5,
      "scenarios_failed": 0,
      "resources_created": 15,
      "resources_cleaned": 15
    },
    {
      "tenant_id": "87654321-4321-4321-4321-cba987654321",
      "display_name": "Customer B",
      "status": "running",
      "started_at": "2024-01-15T10:30:05Z",
      "scenarios_completed": 3,
      "scenarios_failed": 0,
      "resources_created": 12
    }
  ]
}
```

---

### Tenant Management

#### GET /api/tenants

List all configured tenants.

**Request:**

```bash
curl https://your-orchestrator/api/tenants \
  -H "Authorization: Bearer <token>"
```

**Response:**

```json
{
  "tenants": [
    {
      "tenant_id": "12345678-1234-1234-1234-123456789abc",
      "display_name": "Customer A",
      "subscription_id": "sub-id-1",
      "enabled": true,
      "resource_group": "rg-haymaker-customerA"
    },
    {
      "tenant_id": "87654321-4321-4321-4321-cba987654321",
      "display_name": "Customer B",
      "subscription_id": "sub-id-2",
      "enabled": true,
      "resource_group": null
    }
  ],
  "count": 2
}
```

---

### Cost and Resources

#### GET /api/executions/{run_id}/cost

Get cost summary for an execution.

**Request:**

```bash
curl https://your-orchestrator/api/executions/550e8400-e29b-41d4-a716-446655440000/cost \
  -H "Authorization: Bearer <token>"
```

**Response:**

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_cost_usd": 45.67,
  "currency": "USD",
  "period": {
    "start": "2024-01-15T10:30:00Z",
    "end": "2024-01-15T18:45:00Z"
  },
  "by_resource_type": {
    "Microsoft.Compute/virtualMachines": 25.00,
    "Microsoft.ContainerService/managedClusters": 15.00,
    "Microsoft.Storage/storageAccounts": 5.67
  },
  "by_scenario": {
    "compute-01-linux-vm-web-server": 12.50,
    "containers-02-aks-cluster": 15.00,
    "databases-02-cosmos-db": 18.17
  },
  "note": "Cost data may be delayed up to 24 hours"
}
```

---

#### GET /api/resources

List HayMaker-managed resources.

**Request:**

```bash
curl "https://your-orchestrator/api/resources?execution_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <token>"
```

**Query Parameters:**

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `execution_id` | string | Filter by execution ID |
| `scenario` | string | Filter by scenario name |
| `limit` | integer | Maximum results (default: 100) |

**Response:**

```json
{
  "resources": [
    {
      "id": "/subscriptions/.../resourceGroups/.../providers/Microsoft.Compute/virtualMachines/vm-haymaker-001",
      "name": "vm-haymaker-001",
      "type": "Microsoft.Compute/virtualMachines",
      "resourceGroup": "rg-haymaker-scenario-001",
      "location": "eastus",
      "tags": {
        "AzureHayMaker-managed": "true",
        "RunId": "550e8400-e29b-41d4-a716-446655440000",
        "Scenario": "compute-01-linux-vm-web-server"
      }
    }
  ],
  "count": 1,
  "total_found": 23
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing the problem"
}
```

**Common Error Codes:**

| Code | Description |
|:-----|:------------|
| 400 | Bad request (invalid parameters) |
| 401 | Authentication required |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 500 | Internal server error |

**Example Error:**

```json
{
  "detail": "Schedule not found: invalid-schedule-id"
}
```

---

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default limit**: 100 requests per minute per client
- **Execution endpoints**: 10 requests per minute

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705323600
```

---

## Webhooks

Configure webhooks to receive execution notifications.

### Webhook Events

| Event | Description |
|:------|:------------|
| `execution.started` | Execution has started |
| `execution.completed` | Execution completed successfully |
| `execution.failed` | Execution failed |

### Webhook Payload

```json
{
  "event": "execution.completed",
  "timestamp": "2024-01-15T18:45:00Z",
  "data": {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "duration_hours": 8.25,
    "scenarios_count": 5
  }
}
```

### Configure Webhooks

Set the `WEBHOOK_URL` environment variable:

```bash
export WEBHOOK_URL="https://your-endpoint/webhooks/haymaker"
```

---

## Related Documentation

- [Architecture](./ARCHITECTURE.md) - System architecture
- [Configuration](./CONFIGURATION.md) - Environment setup
- [General API Reference](/AzureHayMaker/api) - Complete API documentation
