---
layout: default
title: API Reference
nav_order: 7
description: "Azure HayMaker REST API documentation"
permalink: /api/
---

# API Reference
{: .no_toc }

Complete REST API documentation for Azure HayMaker orchestrator service.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The Azure HayMaker orchestrator provides a REST API for managing scenario execution, monitoring status, and querying metrics. The API is implemented in [orchestrator_server.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/orchestrator_server.py).

**Base URL**: `https://haymaker-fastapi-app.azurewebsites.net`

**Source Files**:
- [orchestrator_server.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/orchestrator_server.py) - Main FastAPI application
- [execute_api.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/execute_api.py) - Execution endpoints
- [metrics_api.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/metrics_api.py) - Metrics endpoints
- [monitoring_api.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/monitoring_api.py) - Monitoring endpoints

## Authentication

Currently, the API does not require authentication for read operations. Write operations (execute, cleanup) may require API key authentication in production deployments.

{: .note }
> For production deployments, configure Azure AD authentication on the Container App or Function App hosting the API.

---

## Endpoints

### Health Check

Check if the orchestrator service is running.

**Endpoint**: `GET /`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "azure-haymaker-orchestrator",
  "timestamp": "2025-11-25T04:52:18.754691+00:00"
}
```

**Example**:
```bash
curl https://haymaker-fastapi-app.azurewebsites.net/
```

---

### List Scenarios

Get all available scenarios that can be executed.

**Endpoint**: `GET /api/scenarios`

**Response** (200 OK):
```json
{
  "scenarios": [
    {
      "scenario_name": "compute-01-linux-vm-web-server",
      "technology_area": "Compute",
      "scenario_doc_path": "/docs/scenarios/compute-01-linux-vm-web-server.md"
    },
    {
      "scenario_name": "security-01-key-vault-secrets",
      "technology_area": "Security",
      "scenario_doc_path": "/docs/scenarios/security-01-key-vault-secrets.md"
    }
    // ... more scenarios
  ]
}
```

**Example**:
```bash
curl https://haymaker-fastapi-app.azurewebsites.net/api/scenarios | jq
```

---

### Execute Scenarios

Submit scenarios for execution.

**Endpoint**: `POST /api/execute`

**Request Body**:
```json
{
  "scenarios": ["compute-01-linux-vm-web-server", "security-01-key-vault-secrets"],
  "duration_hours": 1
}
```

| Parameter | Type | Required | Description |
|:----------|:-----|:---------|:------------|
| `scenarios` | array | Yes | List of scenario names to execute (1-5) |
| `duration_hours` | integer | No | Execution duration in hours (default: 8) |

**Response** (200 OK):
```json
{
  "execution_id": "3e598ac3-7b1b-46a6-8ddc-5986734e13fc",
  "status": "started",
  "started_at": "2025-11-25T04:52:29.217706+00:00"
}
```

**Example - Single Scenario**:
```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{"scenarios":["compute-01-linux-vm-web-server"],"duration_hours":1}'
```

**Example - Multiple Scenarios**:
```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": [
      "databases-01-mysql-wordpress",
      "security-01-key-vault-secrets",
      "ai-ml-01-cognitive-services-vision",
      "networking-01-virtual-network",
      "webapps-01-static-website"
    ],
    "duration_hours": 2
  }'
```

---

### List Executions

Get all executions and their status.

**Endpoint**: `GET /api/executions`

**Response** (200 OK):
```json
{
  "executions": [
    {
      "run_id": "3e598ac3-7b1b-46a6-8ddc-5986734e13fc",
      "started_at": "2025-11-25T04:52:29.217706+00:00",
      "status": "running",
      "scenario_count": 3
    }
  ]
}
```

**Example**:
```bash
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions | jq
```

---

### Get Execution Details

Get detailed status for a specific execution.

**Endpoint**: `GET /api/executions/{execution_id}`

**Path Parameters**:

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `execution_id` | string | The unique execution identifier |

**Response** (200 OK):
```json
{
  "run_id": "3e598ac3-7b1b-46a6-8ddc-5986734e13fc",
  "started_at": "2025-11-25T04:52:29.217706+00:00",
  "status": "running",
  "phases": {
    "validation": {"status": "skipped"},
    "selection": {
      "status": "completed",
      "scenario_count": 5,
      "scenarios": [
        "compute-01-linux-vm-web-server",
        "security-01-key-vault-secrets"
      ]
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
      "status": "running",
      "started_at": "2025-11-25T04:55:00.000000+00:00"
    }
  }
}
```

**Status Values**:
- `pending` - Execution queued, waiting to start
- `running` - Execution in progress
- `completed` - Execution finished successfully
- `failed` - Execution failed with errors

**Example**:
```bash
EXEC_ID="3e598ac3-7b1b-46a6-8ddc-5986734e13fc"
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions/$EXEC_ID | jq
```

---

### Get Metrics

Get execution statistics and metrics.

**Endpoint**: `GET /api/metrics`

**Response** (200 OK):
```json
{
  "executions_total": 7,
  "executions_running": 2,
  "executions_completed": 5,
  "executions_failed": 0
}
```

**Example**:
```bash
curl https://haymaker-fastapi-app.azurewebsites.net/api/metrics | jq
```

---

### Validate Environment

Validate the orchestrator environment configuration.

**Endpoint**: `POST /api/validate`

**Response** (200 OK):
```json
{
  "status": "valid",
  "checks": {
    "azure_subscription": "ok",
    "key_vault_access": "ok",
    "container_registry": "ok",
    "scenario_docs": "ok"
  }
}
```

**Example**:
```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/validate | jq
```

---

## Error Responses

All endpoints return standard HTTP error codes with JSON error details.

### 400 Bad Request

Invalid request parameters.

```json
{
  "detail": "Invalid scenario name: unknown-scenario",
  "error_code": "INVALID_SCENARIO"
}
```

### 404 Not Found

Resource not found.

```json
{
  "detail": "Execution not found: invalid-id",
  "error_code": "EXECUTION_NOT_FOUND"
}
```

### 500 Internal Server Error

Server-side error.

```json
{
  "detail": "Internal server error",
  "error_code": "INTERNAL_ERROR"
}
```

---

## Rate Limiting

{: .warning }
> Rate limiting is enforced in production environments.

| Limit Type | Limit |
|:-----------|:------|
| Global | 100 executions/hour |
| Per-Scenario | 10 executions/hour per scenario |
| Per-User | 20 executions/hour (if auth enabled) |

When rate limited, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## Code Examples

### Python

```python
import requests

BASE_URL = "https://haymaker-fastapi-app.azurewebsites.net"

# List scenarios
scenarios = requests.get(f"{BASE_URL}/api/scenarios").json()
print(f"Available scenarios: {len(scenarios['scenarios'])}")

# Execute a scenario
response = requests.post(
    f"{BASE_URL}/api/execute",
    json={
        "scenarios": ["compute-01-linux-vm-web-server"],
        "duration_hours": 1
    }
)
execution = response.json()
print(f"Execution started: {execution['execution_id']}")

# Check status
status = requests.get(
    f"{BASE_URL}/api/executions/{execution['execution_id']}"
).json()
print(f"Status: {status['status']}")
```

### JavaScript/Node.js

```javascript
const BASE_URL = "https://haymaker-fastapi-app.azurewebsites.net";

// List scenarios
const scenarios = await fetch(`${BASE_URL}/api/scenarios`).then(r => r.json());
console.log(`Available scenarios: ${scenarios.scenarios.length}`);

// Execute a scenario
const execution = await fetch(`${BASE_URL}/api/execute`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    scenarios: ["compute-01-linux-vm-web-server"],
    duration_hours: 1
  })
}).then(r => r.json());

console.log(`Execution started: ${execution.execution_id}`);
```

---

## Related Documentation

- [CLI Guide](/AzureHayMaker/cli/) - Command-line interface for API operations
- [Scenarios](/AzureHayMaker/scenarios/) - Available scenarios for execution
- [Architecture](/AzureHayMaker/architecture/) - System design and data flow

## Source Code References

- [orchestrator_server.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/orchestrator_server.py) - Main FastAPI application
- [execute_api.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/execute_api.py) - Execution API implementation
- [execution_tracker.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/execution_tracker.py) - Status tracking
- [rate_limiter.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/rate_limiter.py) - Rate limiting implementation
- [API tests](https://github.com/rysweet/AzureHayMaker/tree/main/tests/unit) - Unit tests for API endpoints
