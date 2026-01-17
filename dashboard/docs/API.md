# Dashboard API Reference

This document describes the REST and WebSocket APIs used by the Analytics Dashboard to communicate with the AzureHayMaker orchestrator.

## Base Configuration

### Endpoints

```
REST API Base URL: https://your-orchestrator.azurecontainerapps.io
WebSocket URL: wss://your-orchestrator.azurecontainerapps.io/ws/metrics
```

### Authentication

All API endpoints require authentication via Azure AD B2C bearer token:

```http
Authorization: Bearer <your-token>
```

## REST API Endpoints

### GET /metrics

Get current metrics snapshot.

**Request:**
```http
GET /metrics HTTP/1.1
Host: your-orchestrator.azurecontainerapps.io
Authorization: Bearer <token>
```

**Response:**
```json
{
  "timestamp": "2026-01-17T21:45:00Z",
  "concurrent_executions": 5,
  "total_executions_today": 127,
  "active_agents": 12,
  "total_cost_today": 45.67,
  "telemetry_volume_mb": 1234.56
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Missing or invalid token
- `500 Internal Server Error` - Server error

---

### GET /analytics

Get analytics data for specified period.

**Request:**
```http
GET /analytics?period=30d HTTP/1.1
Host: your-orchestrator.azurecontainerapps.io
Authorization: Bearer <token>
```

**Query Parameters:**
- `period` (required): One of `7d`, `30d`, `90d`

**Response:**
```json
{
  "period": "30d",
  "start_date": "2025-12-18T00:00:00Z",
  "end_date": "2026-01-17T23:59:59Z",
  "total_executions": 3845,
  "success_rate": 0.987,
  "average_duration_seconds": 12.3,
  "peak_concurrent_executions": 15,
  "total_cost": 1234.56,
  "cost_per_execution": 0.32
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid period parameter
- `401 Unauthorized` - Missing or invalid token

---

### GET /cost/breakdown

Get cost breakdown by service type.

**Request:**
```http
GET /cost/breakdown?period=30d HTTP/1.1
Host: your-orchestrator.azurecontainerapps.io
Authorization: Bearer <token>
```

**Query Parameters:**
- `period` (optional): One of `7d`, `30d`, `90d`. Default: `30d`

**Response:**
```json
{
  "period": "30d",
  "total_cost": 1234.56,
  "budget": 2000.00,
  "budget_percentage": 61.7,
  "breakdown": {
    "compute": 845.32,
    "storage": 123.45,
    "telemetry": 234.56,
    "other": 31.23
  },
  "trend": [
    {
      "timestamp": "2025-12-18T00:00:00Z",
      "cost": 35.67
    },
    {
      "timestamp": "2025-12-19T00:00:00Z",
      "cost": 38.92
    }
    // ... more data points
  ]
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid period parameter
- `401 Unauthorized` - Missing or invalid token

---

### GET /agents/status

Get current status of all agents.

**Request:**
```http
GET /agents/status HTTP/1.1
Host: your-orchestrator.azurecontainerapps.io
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "agent_id": "agent-001",
    "agent_name": "knowledge-worker-1",
    "status": "running",
    "last_execution_at": "2026-01-17T21:40:15Z",
    "last_duration_seconds": 45.2,
    "error_message": null
  },
  {
    "agent_id": "agent-002",
    "agent_name": "knowledge-worker-2",
    "status": "idle",
    "last_execution_at": "2026-01-17T21:30:00Z",
    "last_duration_seconds": 120.5,
    "error_message": null
  },
  {
    "agent_id": "agent-003",
    "agent_name": "knowledge-worker-3",
    "status": "failed",
    "last_execution_at": "2026-01-17T21:35:22Z",
    "last_duration_seconds": 5.1,
    "error_message": "Connection timeout to external service"
  }
]
```

**Status Values:**
- `running` - Agent is currently executing
- `idle` - Agent is waiting for work
- `failed` - Agent's last execution failed
- `queued` - Agent has work queued but not started

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Missing or invalid token

---

### GET /telemetry/volume

Get telemetry volume statistics.

**Request:**
```http
GET /telemetry/volume?period=30d HTTP/1.1
Host: your-orchestrator.azurecontainerapps.io
Authorization: Bearer <token>
```

**Query Parameters:**
- `period` (optional): One of `7d`, `30d`, `90d`. Default: `30d`

**Response:**
```json
{
  "period": "30d",
  "logs": {
    "volume_bytes": 12345678900,
    "rate_per_second": 142.5
  },
  "metrics": {
    "volume_bytes": 2345678900,
    "rate_per_second": 28.3
  },
  "traces": {
    "volume_bytes": 5678900123,
    "rate_per_second": 67.2
  },
  "anomaly_detected": false,
  "anomaly_details": null
}
```

**Anomaly Detection:**
When `anomaly_detected` is `true`, the `anomaly_details` field contains:
```json
{
  "anomaly_type": "rate_spike",
  "telemetry_type": "logs",
  "detected_at": "2026-01-17T21:30:00Z",
  "severity": "warning",
  "description": "Log volume exceeded 3x normal rate"
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid period parameter
- `401 Unauthorized` - Missing or invalid token

---

### GET /analytics/executions/timeline

Get execution timeline data.

**Request:**
```http
GET /analytics/executions/timeline?period=7d&interval=1h HTTP/1.1
Host: your-orchestrator.azurecontainerapps.io
Authorization: Bearer <token>
```

**Query Parameters:**
- `period` (optional): One of `7d`, `30d`, `90d`. Default: `7d`
- `interval` (optional): One of `5m`, `15m`, `1h`, `1d`. Default: `1h`

**Response:**
```json
{
  "period": "7d",
  "interval": "1h",
  "data_points": [
    {
      "timestamp": "2026-01-17T21:00:00Z",
      "concurrent_executions": 5,
      "completed_count": 23,
      "failed_count": 1
    },
    {
      "timestamp": "2026-01-17T22:00:00Z",
      "concurrent_executions": 7,
      "completed_count": 28,
      "failed_count": 0
    }
    // ... more data points
  ]
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Missing or invalid token

---

## WebSocket API

### Connection

**Endpoint:** `wss://your-orchestrator.azurecontainerapps.io/ws/metrics`

**Authentication:**
Include token as query parameter:
```
wss://your-orchestrator.azurecontainerapps.io/ws/metrics?token=<your-token>
```

### Connection Lifecycle

**Client Connection:**
```javascript
const ws = new WebSocket('wss://your-orchestrator.azurecontainerapps.io/ws/metrics?token=<token>');

ws.onopen = () => {
  console.log('Connected to metrics stream');
};

ws.onclose = () => {
  console.log('Disconnected from metrics stream');
  // Implement reconnection logic
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### Message Format

All WebSocket messages follow this structure:

```json
{
  "type": "metric_update",
  "timestamp": "2026-01-17T21:45:30Z",
  "data": { /* metric-specific data */ }
}
```

### Message Types

#### 1. Execution Started

Sent when an agent execution begins.

```json
{
  "type": "metric_update",
  "timestamp": "2026-01-17T21:45:30Z",
  "data": {
    "metric_name": "execution.started",
    "execution_id": "exec-12345",
    "agent_id": "agent-001",
    "agent_name": "knowledge-worker-1",
    "task_description": "Process user request"
  }
}
```

#### 2. Execution Completed

Sent when an agent execution completes successfully.

```json
{
  "type": "metric_update",
  "timestamp": "2026-01-17T21:46:15Z",
  "data": {
    "metric_name": "execution.completed",
    "execution_id": "exec-12345",
    "agent_id": "agent-001",
    "duration_seconds": 45.2,
    "status": "success"
  }
}
```

#### 3. Execution Failed

Sent when an agent execution fails.

```json
{
  "type": "metric_update",
  "timestamp": "2026-01-17T21:46:20Z",
  "data": {
    "metric_name": "execution.failed",
    "execution_id": "exec-12346",
    "agent_id": "agent-002",
    "duration_seconds": 5.1,
    "error_message": "Connection timeout",
    "error_type": "TimeoutError"
  }
}
```

#### 4. Cost Update

Sent when cost metrics are updated (typically every 5 minutes).

```json
{
  "type": "metric_update",
  "timestamp": "2026-01-17T21:50:00Z",
  "data": {
    "metric_name": "cost.updated",
    "total_cost": 1245.67,
    "cost_delta": 11.11,
    "breakdown": {
      "compute": 850.00,
      "storage": 125.00,
      "telemetry": 239.00,
      "other": 31.67
    }
  }
}
```

#### 5. Telemetry Volume Update

Sent when telemetry volume changes significantly (>10% increase).

```json
{
  "type": "metric_update",
  "timestamp": "2026-01-17T21:47:00Z",
  "data": {
    "metric_name": "telemetry.volume",
    "telemetry_type": "logs",
    "volume_bytes": 12456789000,
    "rate_per_second": 145.2,
    "anomaly_detected": false
  }
}
```

#### 6. Agent Status Change

Sent when agent status changes (running → idle, idle → running, etc.).

```json
{
  "type": "metric_update",
  "timestamp": "2026-01-17T21:48:00Z",
  "data": {
    "metric_name": "agent.status_changed",
    "agent_id": "agent-003",
    "agent_name": "knowledge-worker-3",
    "old_status": "idle",
    "new_status": "running",
    "execution_id": "exec-12347"
  }
}
```

### Heartbeat

Server sends heartbeat every 30 seconds to keep connection alive:

```json
{
  "type": "heartbeat",
  "timestamp": "2026-01-17T21:49:00Z",
  "data": {
    "connected_clients": 5,
    "uptime_seconds": 86400
  }
}
```

**Client Response:**
Clients should respond with a pong message:

```json
{
  "type": "pong",
  "timestamp": "2026-01-17T21:49:00Z"
}
```

### Error Messages

Server sends error messages when issues occur:

```json
{
  "type": "error",
  "timestamp": "2026-01-17T21:50:00Z",
  "data": {
    "error_code": "RATE_LIMIT_EXCEEDED",
    "error_message": "Too many requests, please reconnect after 60 seconds",
    "retry_after_seconds": 60
  }
}
```

**Error Codes:**
- `RATE_LIMIT_EXCEEDED` - Client exceeded message rate limit
- `AUTHENTICATION_FAILED` - Invalid or expired token
- `INTERNAL_ERROR` - Server-side error
- `CONNECTION_LIMIT` - Too many concurrent connections

### Reconnection Strategy

Recommended reconnection strategy with exponential backoff:

```javascript
let reconnectDelay = 1000; // Start with 1 second
const maxDelay = 30000; // Max 30 seconds

function connect() {
  const ws = new WebSocket('wss://your-orchestrator.azurecontainerapps.io/ws/metrics?token=<token>');

  ws.onopen = () => {
    reconnectDelay = 1000; // Reset delay on successful connection
  };

  ws.onclose = (event) => {
    if (event.code !== 1000) { // Not a normal closure
      setTimeout(() => {
        reconnectDelay = Math.min(reconnectDelay * 2, maxDelay);
        connect();
      }, reconnectDelay);
    }
  };
}
```

## Rate Limits

### REST API
- **Global**: 1000 requests/hour per IP
- **Per Endpoint**: 100 requests/minute per endpoint per IP

### WebSocket
- **Connections**: 100 concurrent connections per IP
- **Messages**: 60 pong messages/minute (heartbeat rate)

Rate limit headers included in REST responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642453200
```

## Error Handling

### REST API Error Format

```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Period must be one of: 7d, 30d, 90d",
    "details": {
      "parameter": "period",
      "value": "invalid"
    }
  }
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `INVALID_PARAMETER` | Invalid query parameter value |
| `MISSING_PARAMETER` | Required parameter not provided |
| `AUTHENTICATION_FAILED` | Invalid or expired token |
| `AUTHORIZATION_FAILED` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Server-side error |

## Examples

### Fetch Cost Breakdown (TypeScript)

```typescript
async function fetchCostBreakdown(period: '7d' | '30d' | '90d' = '30d') {
  const response = await fetch(
    `https://your-orchestrator.azurecontainerapps.io/cost/breakdown?period=${period}`,
    {
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error.message);
  }

  return await response.json();
}
```

### WebSocket Client (TypeScript)

```typescript
class MetricsWebSocket {
  private ws: WebSocket | null = null;
  private callbacks: Set<(data: MetricUpdate) => void> = new Set();

  connect(token: string): void {
    this.ws = new WebSocket(
      `wss://your-orchestrator.azurecontainerapps.io/ws/metrics?token=${token}`
    );

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'metric_update') {
        this.callbacks.forEach(callback => callback(message.data));
      } else if (message.type === 'heartbeat') {
        this.ws?.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
      }
    };
  }

  onMetricUpdate(callback: (data: MetricUpdate) => void): () => void {
    this.callbacks.add(callback);
    return () => this.callbacks.delete(callback);
  }

  disconnect(): void {
    this.ws?.close(1000);
    this.ws = null;
  }
}
```

## Versioning

API version is included in response headers:

```http
X-API-Version: 1.0.0
```

Breaking changes will increment the major version. The dashboard should check this header and warn users if versions are incompatible.

## Support

For API issues:
- GitHub Issues: https://github.com/rysweet/AzureHayMaker/issues
- Documentation: https://github.com/rysweet/AzureHayMaker/tree/main/docs
