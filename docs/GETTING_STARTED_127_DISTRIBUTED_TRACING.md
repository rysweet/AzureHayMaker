# Getting Started: Distributed Tracing (Issue #127)

**Your complete guide to implementing Issue #127**

**Priority**: P1-High | **Effort**: 2 weeks | **ROI**: 36%

---

## What You're Building

OpenTelemetry-based distributed tracing across orchestrator, agents, and infrastructure to reduce MTTR from 4 hours to 30 minutes.

**Why It Matters**: Currently can't correlate requests across service boundaries. Debugging failures requires manual log correlation.

---

## Before You Start (30 minutes)

### Install Dependencies

```bash
# Add to pyproject.toml
[project.dependencies]
opentelemetry-api = "^1.21.0"
opentelemetry-sdk = "^1.21.0"
opentelemetry-instrumentation-fastapi = "^0.42b0"
opentelemetry-exporter-azure-monitor = "^1.0.0"

# Sync dependencies
uv sync
```

### Read OpenTelemetry Basics

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Azure Monitor Integration](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable)

---

## Phase 1: Instrument FastAPI Orchestrator (Days 1-2)

### Configure OpenTelemetry

**File**: `src/orchestrator_server.py`

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add Azure Monitor exporter
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
span_processor = BatchSpanProcessor(
    AzureMonitorTraceExporter(connection_string=connection_string)
)
trace.get_tracer_provider().add_span_processor(span_processor)

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
```

### Add Manual Spans for Critical Operations

```python
@app.post("/api/execute")
async def execute(request: ExecutionRequest):
    with tracer.start_as_current_span("execute_scenarios") as span:
        span.set_attribute("scenario_count", len(request.scenarios))
        span.set_attribute("duration_hours", request.duration_hours)

        # Your execution logic
        result = await orchestrate_execution(request)

        span.set_attribute("execution_id", result.execution_id)
        return result
```

**Test**: Run orchestrator, verify traces appear in Application Insights

---

## Phase 2: Propagate Trace Context to Agents (Days 3-5)

### Inject Trace Context into Container Apps

**File**: `src/azure_haymaker/orchestrator/container_manager.py`

```python
def deploy_container_app(self, scenario: str, run_id: str):
    # Get current trace context
    from opentelemetry import trace
    span = trace.get_current_span()
    trace_id = format(span.get_span_context().trace_id, '032x')
    span_id = format(span.get_span_context().span_id, '016x')

    # Inject into container environment
    environment_vars = [
        {"name": "TRACE_ID", "value": trace_id},
        {"name": "SPAN_ID", "value": span_id},
        {"name": "RUN_ID", "value": run_id},
        # Existing vars...
    ]

    # Deploy container with trace context
```

### Update Agent Base to Propagate Context

**File**: `src/azure_haymaker/agent_base.py`

```python
class AgentBase:
    def run(self):
        # Read trace context from environment
        trace_id = os.getenv("TRACE_ID")
        parent_span_id = os.getenv("SPAN_ID")

        # Create child span
        with tracer.start_as_current_span(
            f"agent_{self.config.name}",
            context=create_context_from_ids(trace_id, parent_span_id)
        ) as span:
            span.set_attribute("agent.name", self.config.name)
            span.set_attribute("run.id", os.getenv("RUN_ID"))

            # Agent execution
            self.on_start()
            self.on_execute()
            self.on_cleanup()
```

---

## Phase 3: Add Spans for Azure SDK Calls (Days 6-8)

### Instrument Azure SDK Operations

**Use OpenTelemetry auto-instrumentation**:

```python
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Auto-instrument all HTTP libraries (including Azure SDK)
RequestsInstrumentor().instrument()
```

**Or manual spans for critical operations**:

```python
async def create_container_app(self, name: str):
    with tracer.start_as_current_span("azure.containerapp.create") as span:
        span.set_attribute("container.name", name)
        span.set_attribute("azure.resource_group", self.resource_group)

        # Azure SDK call
        result = await self.container_client.create(...)

        span.set_attribute("container.id", result.id)
        return result
```

---

## Phase 4: Query and Visualize Traces (Days 9-10)

### Application Insights Queries

**Kusto query for end-to-end trace**:

```kusto
// Find all spans for a trace ID
dependencies
| union requests
| union traces
| where operation_Id == "YOUR_TRACE_ID"
| project timestamp, name, duration, success, operation_Id, id
| order by timestamp asc
```

**Query for slowest operations**:

```kusto
dependencies
| where timestamp > ago(1d)
| summarize avg(duration), max(duration), count() by name
| order by max_duration desc
| take 10
```

### Add to Monitoring Dashboard

**File**: `src/orchestrator_server.py` - Add /api/tracing endpoint

```python
@app.get("/api/tracing/slow-operations")
async def get_slow_operations(hours: int = 24):
    """Return slowest operations from last N hours."""
    # Query Application Insights
    # Return top 10 slowest operations
```

---

## Phase 5: Testing (Days 11-14)

### Unit Tests

```python
# tests/unit/test_tracing.py

def test_trace_context_propagated_to_container():
    """Verify trace context injected into container env vars."""
    manager = ContainerManager(...)
    env_vars = manager._get_container_environment(run_id="test", trace_id="abc123")

    assert any(e["name"] == "TRACE_ID" for e in env_vars)
    assert any(e["name"] == "SPAN_ID" for e in env_vars)

def test_agent_creates_child_span():
    """Verify agent creates child span from parent context."""
    # Mock trace context in environment
    os.environ["TRACE_ID"] = "parent_trace_id"
    os.environ["SPAN_ID"] = "parent_span_id"

    agent = TestAgent()
    # Run agent
    # Verify child span created
```

### Integration Tests

```python
@pytest.mark.integration
async def test_end_to_end_trace():
    """Test full trace from API → Orchestrator → Agent → Azure."""

    # Start trace
    with tracer.start_as_current_span("test_e2e") as span:
        trace_id = format(span.get_span_context().trace_id, '032x')

        # Make API request
        response = client.post("/api/execute", json={...})

        # Wait for execution
        await asyncio.sleep(60)

    # Query Application Insights for this trace_id
    spans = query_app_insights_traces(trace_id)

    # Verify spans exist for:
    assert any(s.name == "execute_scenarios" for s in spans)  # API
    assert any(s.name.startswith("agent_") for s in spans)  # Agent
    assert any(s.name.startswith("azure.") for s in spans)  # Azure calls

    # Verify parent-child relationships
    assert all_spans_have_correct_parent(spans)
```

---

## Success Criteria

- [ ] 100% of API requests have traces
- [ ] Trace context propagates to all agents
- [ ] Azure SDK calls visible in traces
- [ ] Can query end-to-end traces in Application Insights
- [ ] MTTR demonstrably reduced (measure after deployment)
- [ ] Performance impact <5%

---

## Common Issues

**Issue**: Traces not appearing in Application Insights
**Solution**: Verify connection string, check span processor flush, wait 2-3 minutes for ingestion

**Issue**: Broken trace chains (orphaned spans)
**Solution**: Verify trace context properly propagated via headers/environment

**Issue**: Too many spans (performance impact)
**Solution**: Use sampling (e.g., 10% of traces for high-volume endpoints)

---

**Issue**: [#127](https://github.com/rysweet/AzureHayMaker/issues/127)

**Milestone**: [Q2 2026](https://github.com/rysweet/AzureHayMaker/milestone/2)

🔍 **Ready to add observability? Follow Phase 1 above!**
