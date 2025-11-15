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

### POST /api/v1/execute

Submit an on-demand execution request.

**Request**:
```json
{
  "scenarios": ["compute-01-linux-vm-web-server", "networking-01-virtual-network"],
  "duration_hours": 2,
  "tags": {"requester": "admin@example.com"}
}
```

**Parameters**:
- `scenarios` (required): List of scenario names (1-5 scenarios)
- `duration_hours` (optional): Execution duration in hours (default: 8, max: 24)
- `tags` (optional): Key-value pairs for tracking

**Response** (202 Accepted):
```json
{
  "execution_id": "exec-20251115-abc123",
  "status": "queued",
  "scenarios": ["compute-01-linux-vm-web-server", "networking-01-virtual-network"],
  "estimated_completion": "2025-11-15T10:00:00Z",
  "created_at": "2025-11-15T08:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request format or parameters
- `404 Not Found`: One or more scenarios don't exist
- `429 Too Many Requests`: Rate limit exceeded (see Retry-After header)
- `500 Internal Server Error`: Server error

### GET /api/v1/executions/{execution_id}

Query the status of an execution.

**Request**:
```
GET /api/v1/executions/exec-20251115-abc123
```

**Response** (200 OK):
```json
{
  "execution_id": "exec-20251115-abc123",
  "status": "running",
  "scenarios": ["compute-01-linux-vm-web-server"],
  "created_at": "2025-11-15T08:00:00Z",
  "started_at": "2025-11-15T08:05:00Z",
  "completed_at": null,
  "progress": {
    "completed": 0,
    "running": 1,
    "failed": 0,
    "total": 1
  },
  "resources_created": 5,
  "container_ids": ["haymaker-compute-01-abc123"],
  "report_url": null,
  "error": null
}
```

**Status Values**:
- `queued`: Request queued, waiting for processing
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
curl -X POST https://your-function-app.azurewebsites.net/api/v1/execute \
  -H "x-functions-key: YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scenarios": ["compute-01"]}'
```

### Azure AD (Future)

OAuth 2.0 bearer tokens for user-level authentication will be supported in a future release.

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
curl -X POST https://your-function-app.azurewebsites.net/api/v1/execute \
  -H "x-functions-key: YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": ["compute-01-linux-vm-web-server"],
    "duration_hours": 2,
    "tags": {"requester": "admin"}
  }'
```

**Query execution status**:
```bash
curl -X GET https://your-function-app.azurewebsites.net/api/v1/executions/exec-20251115-abc123 \
  -H "x-functions-key: YOUR_FUNCTION_KEY"
```

### Using Python

```python
import httpx
import asyncio

async def execute_scenario():
    async with httpx.AsyncClient() as client:
        # Submit execution
        response = await client.post(
            "https://your-function-app.azurewebsites.net/api/v1/execute",
            headers={
                "x-functions-key": "YOUR_FUNCTION_KEY",
                "Content-Type": "application/json",
            },
            json={
                "scenarios": ["compute-01-linux-vm-web-server"],
                "duration_hours": 2,
            },
        )

        if response.status_code == 202:
            data = response.json()
            execution_id = data["execution_id"]
            print(f"Execution started: {execution_id}")

            # Poll for status
            while True:
                status_response = await client.get(
                    f"https://your-function-app.azurewebsites.net/api/v1/executions/{execution_id}",
                    headers={"x-functions-key": "YOUR_FUNCTION_KEY"},
                )

                status_data = status_response.json()
                print(f"Status: {status_data['status']}")

                if status_data["status"] in ["completed", "failed"]:
                    break

                await asyncio.sleep(60)  # Wait 1 minute

            print(f"Execution finished: {status_data['status']}")
            if status_data.get("report_url"):
                print(f"Report: {status_data['report_url']}")

asyncio.run(execute_scenario())
```

### Using PowerShell

```powershell
# Submit execution
$body = @{
    scenarios = @("compute-01-linux-vm-web-server")
    duration_hours = 2
} | ConvertTo-Json

$response = Invoke-RestMethod -Method Post `
    -Uri "https://your-function-app.azurewebsites.net/api/v1/execute" `
    -Headers @{"x-functions-key" = "YOUR_FUNCTION_KEY"} `
    -ContentType "application/json" `
    -Body $body

$executionId = $response.execution_id
Write-Host "Execution started: $executionId"

# Query status
do {
    Start-Sleep -Seconds 60
    $status = Invoke-RestMethod -Method Get `
        -Uri "https://your-function-app.azurewebsites.net/api/v1/executions/$executionId" `
        -Headers @{"x-functions-key" = "YOUR_FUNCTION_KEY"}

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

1. Client submits POST /api/v1/execute
2. API validates request and scenarios
3. API checks rate limits (global, per-scenario)
4. API creates execution record (status=queued)
5. API enqueues message to Service Bus
6. API returns 202 with execution_id
7. Queue processor picks up message
8. Processor creates service principals
9. Processor deploys Container Apps
10. Processor updates status (status=running)
11. Processor monitors execution for duration
12. Processor performs cleanup verification
13. Processor updates status (status=completed/failed)
14. Processor stores execution report

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
