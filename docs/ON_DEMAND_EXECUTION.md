# On-Demand Execution API

Azure HayMaker supports on-demand execution of scenarios via HTTP API, allowing operators to trigger specific scenarios without waiting for the scheduled runs (4x daily).

## Table of Contents

- [Overview](#overview)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)
- [Implementation Details](#implementation-details)

## Overview

The on-demand execution feature provides:

- **HTTP API** for submitting execution requests
- **Rate limiting** to prevent abuse
- **Status tracking** via execution IDs
- **Asynchronous processing** using Service Bus queues
- **Progress monitoring** with status endpoints

### Architecture

```
Client Request → HTTP API → Rate Limiter → Execution Tracker
                                ↓
                          Service Bus Queue
                                ↓
                         Queue Processor
                                ↓
                    Container App Deployment
                                ↓
                         Status Updates
```

## API Endpoints

{: .note }
> The orchestrator uses a FastAPI-based REST API. See [API Reference](/AzureHayMaker/api/) for complete endpoint documentation.

### POST /api/execute

Submit an on-demand execution request.

**Request**:
```json
{
  "skip_validation": false
}
```

**Parameters**:
- `skip_validation` (optional): Skip environment validation (default: false)

**Response** (200 OK):
```json
{
  "execution_id": "3e598ac3-7b1b-46a6-8ddc-5986734e13fc",
  "status": "started",
  "started_at": "2025-11-25T04:52:29.217706+00:00"
}
```

**Error Responses**:
- `500 Internal Server Error`: Server error

### GET /api/executions/{execution_id}

Query the status of an execution.

**Request**:
```
GET /api/executions/3e598ac3-7b1b-46a6-8ddc-5986734e13fc
```

**Response** (200 OK):
```json
{
  "run_id": "3e598ac3-7b1b-46a6-8ddc-5986734e13fc",
  "started_at": "2025-11-25T04:52:29.217706+00:00",
  "status": "running",
  "phases": {
    "validation": {"status": "passed"},
    "selection": {"status": "completed", "scenario_count": 5},
    "provisioning": {"status": "completed"},
    "monitoring": {"status": "running"}
  }
}
```

**Status Values**:
- `running`: Execution in progress
- `completed`: Execution finished successfully
- `failed`: Execution failed with errors

**Error Responses**:
- `404 Not Found`: Execution ID doesn't exist
- `500 Internal Server Error`: Server error

## Authentication

The on-demand execution API uses Azure Functions authentication.

### API Key (Default)

Include the function key in the request header:

```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Azure AD

The current implementation uses API key authentication. For Azure AD integration, configure the Function App with Azure AD authentication and use OAuth 2.0 bearer tokens.

## Rate Limiting

Azure HayMaker implements token bucket rate limiting with the following limits:

- **Global**: 100 executions/hour across all users
- **Per-Scenario**: 10 executions/hour per scenario
- **Per-User**: 20 executions/hour per user (if auth enabled)

### Rate Limit Response

When rate limit is exceeded, the API returns:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 3600 seconds."
  },
  "retry_after": 3600
}
```

Status code: `429 Too Many Requests`
Header: `Retry-After: 3600`

### Rate Limit Reset

Rate limits use a sliding window algorithm and reset automatically. The `retry_after` field indicates when you can retry.

## Usage Examples

### Using cURL

**Submit execution request**:
```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Query execution status**:
```bash
EXEC_ID="3e598ac3-7b1b-46a6-8ddc-5986734e13fc"
curl -X GET "https://haymaker-fastapi-app.azurewebsites.net/api/executions/$EXEC_ID"
```

### Using Python

```python
import httpx
import asyncio

BASE_URL = "https://haymaker-fastapi-app.azurewebsites.net"

async def execute_scenario():
    async with httpx.AsyncClient() as client:
        # Submit execution
        response = await client.post(
            f"{BASE_URL}/api/execute",
            headers={"Content-Type": "application/json"},
            json={},
        )

        if response.status_code == 200:
            data = response.json()
            execution_id = data["execution_id"]
            print(f"Execution started: {execution_id}")

            # Poll for status
            while True:
                status_response = await client.get(
                    f"{BASE_URL}/api/executions/{execution_id}",
                )

                status_data = status_response.json()
                print(f"Status: {status_data['status']}")

                if status_data["status"] in ["completed", "failed"]:
                    break

                await asyncio.sleep(60)  # Wait 1 minute

            print(f"Execution finished: {status_data['status']}")

asyncio.run(execute_scenario())
```

### Using PowerShell

```powershell
$baseUrl = "https://haymaker-fastapi-app.azurewebsites.net"

# Submit execution
$response = Invoke-RestMethod -Method Post `
    -Uri "$baseUrl/api/execute" `
    -ContentType "application/json" `
    -Body "{}"

$executionId = $response.execution_id
Write-Host "Execution started: $executionId"

# Query status
do {
    Start-Sleep -Seconds 60
    $status = Invoke-RestMethod -Method Get `
        -Uri "$baseUrl/api/executions/$executionId"

    Write-Host "Status: $($status.status)"
} while ($status.status -notin @("completed", "failed"))

Write-Host "Execution finished: $($status.status)"
```

## Error Handling

### Invalid Scenario

```json
{
  "error": {
    "code": "SCENARIO_NOT_FOUND",
    "message": "Scenarios not found: invalid-scenario"
  }
}
```

**Status**: 404 Not Found

### Invalid Request Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Request validation failed",
    "details": [
      {
        "loc": ["scenarios"],
        "msg": "ensure this value has at least 1 items",
        "type": "value_error.list.min_items"
      }
    ]
  }
}
```

**Status**: 400 Bad Request

### Execution Failed

When querying status of a failed execution:

```json
{
  "execution_id": "exec-20251115-abc123",
  "status": "failed",
  "error": "Container deployment failed: insufficient quota",
  ...
}
```

**Status**: 200 OK (status endpoint returns 200 even for failed executions)

## Implementation Details

### Key Components

1. **execute_api.py**: HTTP trigger functions
   - Validates requests
   - Checks rate limits
   - Enqueues execution requests
   - Returns status

2. **execute_processor.py**: Service Bus queue processor
   - Processes queued execution requests
   - Creates service principals
   - Deploys Container Apps
   - Monitors execution
   - Performs cleanup

3. **execution_tracker.py**: Status tracking
   - Stores execution records in Table Storage
   - Tracks status transitions
   - Maintains history

4. **rate_limiter.py**: Rate limiting
   - Token bucket algorithm
   - Table Storage persistence
   - Sliding window

### Storage

- **Table Storage (Executions)**: Execution status records
  - PartitionKey: execution_id
  - RowKey: timestamp (for history)
  - Contains: status, scenarios, container IDs, etc.

- **Table Storage (RateLimits)**: Rate limit counters
  - PartitionKey: limit_type (global, scenario, user)
  - RowKey: identifier
  - Contains: count, window_start, last_request

- **Service Bus (execution-requests)**: Queued execution requests
  - Message body: execution_id, scenarios, duration, tags

- **Blob Storage (execution-reports)**: Execution reports
  - Container: execution-reports
  - Path: {execution_id}/report.json

### Execution Flow

1. Client submits POST /api/execute
2. API validates environment configuration
3. API selects scenarios based on simulation size
4. API returns 200 with execution_id
5. Background task creates service principals
6. Background task deploys Container Apps
7. Background task updates status (status=running)
8. Background task monitors execution (8 hours, 15-minute checks)
9. Background task performs cleanup verification
10. Background task updates status (status=completed/failed)
11. Background task stores execution report to blob storage

### Monitoring

All operations are logged to Azure Log Analytics and can be queried:

```kusto
traces
| where message contains "execution_id"
| project timestamp, message, severityLevel
| order by timestamp desc
```

## Troubleshooting

### Execution Stuck in "queued"

Check Service Bus queue for messages:
```bash
az servicebus queue show \
  --resource-group haymaker-rg \
  --namespace-name haymaker-sb \
  --name execution-requests
```

### Rate Limit Not Resetting

Verify Table Storage rate limit records:
```bash
az storage entity show \
  --account-name haymakerstorage \
  --table-name RateLimits \
  --partition-key global \
  --row-key default
```

### Execution Status Not Found

Check if execution_id is valid and exists in Table Storage:
```bash
az storage entity query \
  --account-name haymakerstorage \
  --table-name Executions \
  --filter "PartitionKey eq 'exec-20251115-abc123'"
```

## See Also

- [Architecture Documentation](ARCHITECTURE.md)
- [Scenario Management](SCENARIO_MANAGEMENT.md)
- [Getting Started](GETTING_STARTED.md)
