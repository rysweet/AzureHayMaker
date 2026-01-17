# Application Insights Custom Metrics

## Overview

Azure HayMaker emits custom metrics to Azure Application Insights for operational visibility and monitoring. These metrics track orchestrator execution performance, scenario activity, cleanup operations, and resource management.

## Available Metrics

### 1. Execution Duration (`haymaker.execution.duration_seconds`)

**Type:** Histogram (float)
**Unit:** Seconds
**Description:** Total duration of orchestrator execution from timer trigger start to completion.

**Dimensions:**
- `run_id`: Unique identifier for the orchestration run
- `status`: Execution status (`success`, `failure`, `timeout`)

**Example Query (KQL):**
```kusto
customMetrics
| where name == "haymaker.execution.duration_seconds"
| summarize avg(value), percentile(value, 95), percentile(value, 99) by bin(timestamp, 1h)
```

### 2. Scenarios Executed (`haymaker.scenarios.executed_count`)

**Type:** Counter (int)
**Unit:** Count
**Description:** Number of automation scenarios executed in each orchestration run.

**Dimensions:**
- `run_id`: Unique identifier for the orchestration run
- `scenario_type`: Type of scenario executed

**Example Query (KQL):**
```kusto
customMetrics
| where name == "haymaker.scenarios.executed_count"
| summarize sum(value) by bin(timestamp, 1h), scenario_type
```

### 3. Cleanup Success (`haymaker.cleanup.success`)

**Type:** Gauge (0 or 1)
**Unit:** Boolean (0=failure, 1=success)
**Description:** Indicates whether resource cleanup completed successfully after scenario execution.

**Dimensions:**
- `run_id`: Unique identifier for the orchestration run
- `cleanup_phase`: Phase of cleanup (`resources`, `storage`, `network`)

**Example Query (KQL):**
```kusto
customMetrics
| where name == "haymaker.cleanup.success"
| summarize success_rate = avg(value) by bin(timestamp, 1h)
```

### 4. Resources Created (`haymaker.resources.created_count`)

**Type:** Counter (int)
**Unit:** Count
**Description:** Number of Azure resources created during scenario execution.

**Dimensions:**
- `run_id`: Unique identifier for the orchestration run
- `resource_type`: Type of Azure resource (`vm`, `storage`, `network`, etc.)

**Example Query (KQL):**
```kusto
customMetrics
| where name == "haymaker.resources.created_count"
| summarize sum(value) by bin(timestamp, 1h), resource_type
```

## Configuration

Custom metrics are automatically enabled when Application Insights is configured. No additional configuration is required.

**Environment Variables:**
- `APPLICATIONINSIGHTS_CONNECTION_STRING`: Application Insights connection string (required)

**Behavior:**
- If connection string is not set, metrics are silently dropped (no-op behavior)
- If connection string is invalid, metrics fail gracefully with warning logs
- Metrics are batched and sent asynchronously to minimize performance impact

## Usage

### Programmatic Access

```python
from azure_haymaker.observability.metrics import get_metrics_client

# Get metrics client (singleton)
metrics = get_metrics_client()

# Record execution duration
metrics.record_execution_duration(
    run_id="abc-123",
    duration_seconds=245.5,
    status="success"
)

# Increment scenario counter
metrics.increment_scenarios_executed(
    run_id="abc-123",
    scenario_type="compute-vm-creation"
)

# Record cleanup success
metrics.record_cleanup_success(
    run_id="abc-123",
    success=True,
    cleanup_phase="resources"
)

# Increment resource counter
metrics.increment_resources_created(
    run_id="abc-123",
    resource_type="vm",
    count=3
)
```

### Viewing Metrics in Azure Portal

1. Navigate to your Application Insights resource
2. Click "Metrics" in the left sidebar
3. Select "Custom Metrics" namespace
4. Choose one of the available metrics:
   - `haymaker.execution.duration_seconds`
   - `haymaker.scenarios.executed_count`
   - `haymaker.cleanup.success`
   - `haymaker.resources.created_count`
5. Apply filters using dimensions (run_id, status, resource_type, etc.)

## Performance Impact

**Overhead:** < 1% CPU, < 5MB memory
**Latency:** Metrics are sent asynchronously, no blocking operations
**Batching:** Metrics are batched every 10 seconds or 100 metrics, whichever comes first

## Troubleshooting

### Metrics Not Appearing in Portal

**Check connection string:**
```bash
echo $APPLICATIONINSIGHTS_CONNECTION_STRING
```

**Check logs for errors:**
```kusto
traces
| where message contains "metrics" or message contains "telemetry"
| order by timestamp desc
```

**Verify metrics client initialization:**
```kusto
traces
| where message contains "Metrics client initialized"
| order by timestamp desc
```

### High Latency

If metrics cause performance issues:
1. Check batch size configuration
2. Verify network connectivity to Application Insights endpoint
3. Review error logs for failed metric uploads

### Missing Dimensions

If dimension values are missing:
1. Verify dimension values are passed correctly when recording metrics
2. Check for null/empty string values
3. Review dimension cardinality (max 10 dimensions per metric)

## Architecture

**Module:** `src/azure_haymaker/observability/metrics.py`

**Design Principles:**
- Single responsibility: Metrics emission only
- Zero external dependencies beyond Azure Monitor SDK
- Graceful degradation if App Insights unavailable
- Minimal performance overhead

**Integration Points:**
- `src/azure_haymaker/orchestrator/timer_trigger.py` - Execution duration
- `src/azure_haymaker/orchestrator/workflow_orchestrator.py` - Scenario counts
- Resource creation handlers - Resource counts
- Cleanup handlers - Cleanup success

## Related Documentation

- [Azure Monitor Metrics Overview](https://learn.microsoft.com/azure/azure-monitor/essentials/data-platform-metrics)
- [Application Insights Custom Metrics](https://learn.microsoft.com/azure/azure-monitor/app/api-custom-events-metrics)
- [OpenTelemetry Metrics API](https://opentelemetry.io/docs/specs/otel/metrics/api/)
