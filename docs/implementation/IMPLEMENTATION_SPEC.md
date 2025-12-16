# Azure HayMaker - Implementation Specification
## Five Critical Improvements (Issue #10)

**Document Version:** 1.0
**Date:** 2025-11-17
**Status:** Ready for Implementation
**Complexity:** Medium (3-5 days)
**Dependencies:** Sequential with parallel opportunities

---

## Executive Summary

This specification provides detailed, actionable implementation plans for 5 critical improvements to Azure HayMaker. Each requirement includes architecture design, specific code changes with line numbers, testing procedures, and security considerations.

**Implementation Priority:**
1. **Req 1**: Service Bus Idempotency (VERIFICATION ONLY - 30 min)
2. **Req 4**: Secret Management (SECURITY CRITICAL - 4-6 hours)
3. **Req 2**: Agent Autostart (SIMPLE - 2 hours)
4. **Req 3**: Agent Output Display (MEDIUM - 3-4 hours)
5. **Req 5**: Presentation (COMPLEX - 1-2 days)

**Key Findings from Investigation:**
- Service Bus is already idempotent (no code changes needed)
- Agent autostart disabled at line 58 of orchestrator.py
- Dev environment has security vulnerability (direct secret injection)
- Staging/prod correctly use Key Vault references

---

## Table of Contents

1. [Requirement 1: Service Bus Idempotency](#requirement-1-service-bus-idempotency)
2. [Requirement 2: Agent Autostart](#requirement-2-agent-autostart)
3. [Requirement 3: Agent Output Display](#requirement-3-agent-output-display)
4. [Requirement 4: Secret Management Consolidation](#requirement-4-secret-management-consolidation)
5. [Requirement 5: Comprehensive Presentation](#requirement-5-comprehensive-presentation)
6. [Execution Order and Dependencies](#execution-order-and-dependencies)
7. [Risk Mitigation](#risk-mitigation)

---

# Requirement 1: Service Bus Idempotency

## Status: NO CODE CHANGES NEEDED

### Investigation Finding

**Conclusion**: Service Bus subscription creation is ALREADY IDEMPOTENT. The Bicep template uses Azure Resource Manager's native idempotency. Recent fixes (commit 2ff08bb, Nov 16) resolved validation scope mismatches.

**Root Cause Analysis:**
- Previous failures were due to validation scope issues (subscription vs resource group)
- Resource naming conflicts (-sb vs -bus) - RESOLVED
- Quota limitations for dev environment - RESOLVED with optional resources

### Architecture Design

```
GitHub Actions Workflow
        ↓
    Bicep Validation (az deployment group validate)
        ↓
    Bicep Deployment (az deployment group create)
        ↓
    ARM Idempotency Check
        ↓
    Service Bus Subscription Creation/Update
        - IF NOT EXISTS: Create new
        - IF EXISTS: Verify configuration matches
        - IF DIFFERS: Update to match template
```

**Idempotency Pattern:**
Bicep templates are declarative and inherently idempotent. ARM automatically:
1. Checks if resource exists
2. Compares current state with desired state
3. Only applies changes if needed

### Implementation Plan

**No code changes required.** Only verification testing.

**Files to Review (No Changes):**
- `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/servicebus.bicep` (lines 59-70)
- `/Users/ryan/src/AzureHayMaker/.github/workflows/deploy-dev.yml` (lines 41-57)

**Verification Steps:**

1. **Clean Deployment Test** (No resources exist):
   ```bash
   # Manual execution
   az group create --name haymaker-dev-test-rg --location eastus2
   az deployment group create \
     --name test-deployment-1 \
     --resource-group haymaker-dev-test-rg \
     --template-file infra/bicep/main.bicep \
     --parameters infra/bicep/parameters/dev.bicepparam
   ```

2. **Idempotency Test** (Resources exist):
   ```bash
   # Re-run same deployment
   az deployment group create \
     --name test-deployment-2 \
     --resource-group haymaker-dev-test-rg \
     --template-file infra/bicep/main.bicep \
     --parameters infra/bicep/parameters/dev.bicepparam
   ```

3. **GitHub Actions Test**:
   - Trigger deploy-dev workflow manually
   - Verify deployment succeeds
   - Re-trigger workflow immediately
   - Verify second deployment succeeds (no conflicts)

### Testing Strategy

**Test Scenarios:**

| Scenario | Expected Result | Validation |
|----------|----------------|------------|
| Clean deployment | Success - all resources created | Check Azure Portal |
| Re-deploy (no changes) | Success - no modifications | ARM shows "no changes" |
| Re-deploy (with changes) | Success - only changed resources updated | ARM shows diff |
| Partial resources exist | Success - missing resources created | ARM creates only missing |

**Acceptance Criteria:**
- [ ] Clean deployment completes successfully
- [ ] Re-deployment completes successfully (no errors)
- [ ] Service Bus subscription exists after both deployments
- [ ] No manual cleanup required between deployments
- [ ] GitHub Actions workflow passes

**Test Environment:** Dev environment (haymaker-dev-rg)

**Test Duration:** 30 minutes

### Rollback Plan

Not applicable - no code changes. If deployment fails, previous working deployment remains active.

### Dependencies

None - this is the first requirement and blocks no other requirements.

### Success Metrics

- Deployment success rate: 100%
- Re-deployment success rate: 100%
- Manual intervention required: 0

---

# Requirement 2: Agent Autostart

## Status: SIMPLE IMPLEMENTATION

### Investigation Finding

**Root Cause**: Line 58 of `orchestrator.py` explicitly sets `run_on_startup=False`, preventing agents from executing on Function App startup.

**Current Code**:
```python
@app.timer_trigger(
    schedule="0 0 0,6,12,18 * * *",
    arg_name="timer_request",
    run_on_startup=False,  # ← Line 58: Disabled
)
```

**Solution**: Change to `run_on_startup=True` and add execution conflict safeguard.

### Architecture Design

**Component Interaction:**

```
Function App Startup
        ↓
    Timer Trigger (run_on_startup=True)
        ↓
    Check Recent Execution (safeguard)
        ↓ (if no recent run)
    Durable Orchestration Start
        ↓
    Scenario Selection
        ↓
    Agent Provisioning
        ↓
    Execution Monitoring
```

**Execution Conflict Prevention:**

```
Startup Trigger Fires
        ↓
    Query Last Execution Timestamp
        ↓
    IF last_run < 5 minutes ago:
        → Skip startup execution (log warning)
    ELSE:
        → Start new orchestration
```

**Data Flow:**

```
orchestrator.py (timer trigger)
    → haymaker_timer() function
        → Check execution history (Table Storage)
            → If safe: durable_client.start_new()
                → orchestrate_haymaker_run()
                    → [Standard orchestration workflow]
```

### Implementation Plan

**Files to Modify:**

1. **`/Users/ryan/src/AzureHayMaker/src/azure_haymaker/orchestrator/orchestrator.py`**
   - **Line 58**: Change `run_on_startup=False` to `run_on_startup=True`
   - **Lines 62-78**: Add execution conflict check

**Detailed Code Changes:**

**Change 1: Enable Startup (Line 58)**

```python
# OLD (Line 58):
run_on_startup=False,

# NEW (Line 58):
run_on_startup=True,
```

**Change 2: Add Safeguard (After Line 78)**

Insert after line 78 (inside `haymaker_timer` function, before orchestration start):

```python
async def haymaker_timer(
    timer_request: Any = None,
    durable_client: Any = None,
) -> dict[str, Any]:
    """Timer trigger for orchestrator execution (4x daily: 00:00, 06:00, 12:00, 18:00 UTC).

    Also runs on startup if run_on_startup=True.
    """
    # Check if triggered by startup vs scheduled timer
    is_startup = timer_request is None or not hasattr(timer_request, 'schedule_status')

    if is_startup:
        logger.info("Startup trigger detected - checking for recent executions")

        # Query for recent orchestration instances (last 5 minutes)
        from datetime import datetime, timedelta, UTC
        from azure.data.tables import TableServiceClient
        from azure.identity import DefaultAzureCredential
        import os

        try:
            # Connect to Table Storage for execution history
            table_account_name = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
            if table_account_name:
                credential = DefaultAzureCredential()
                table_service = TableServiceClient(
                    endpoint=f"https://{table_account_name}.table.core.windows.net",
                    credential=credential
                )

                # Query executions table for recent runs
                table_client = table_service.get_table_client("orchestrationHistory")
                five_minutes_ago = datetime.now(UTC) - timedelta(minutes=5)

                # Check for any executions in last 5 minutes
                query_filter = f"Timestamp ge datetime'{five_minutes_ago.isoformat()}'"
                recent_executions = list(table_client.query_entities(query_filter, top=1))

                if recent_executions:
                    logger.warning(
                        "Skipping startup execution - orchestration ran within last 5 minutes. "
                        f"Last execution: {recent_executions[0].get('Timestamp')}"
                    )
                    return {
                        "status": "skipped",
                        "reason": "recent_execution_detected",
                        "message": "Startup execution skipped to avoid conflict with recent run"
                    }
        except Exception as e:
            logger.warning(f"Could not check recent executions: {e}. Proceeding with startup.")

    # Original timer trigger logic continues...
    if timer_request and timer_request.past_due:
        logger.warning(
            "Timer trigger is running late. Past due time: %s",
            timer_request.past_due,
        )

    # Generate unique run ID for this execution
    run_id = str(uuid4())
    execution_type = "startup" if is_startup else "scheduled"
    logger.info(f"Haymaker {execution_type} trigger fired. Starting orchestration with run_id={run_id}")

    # [Rest of function continues unchanged...]
```

**Change 3: Add Configuration Flag**

Add environment variable to `.env.example`:

**File**: `/Users/ryan/src/AzureHayMaker/.env.example`

Add after line 10:

```bash
# Agent Execution
AUTO_RUN_ON_STARTUP=true  # Enable/disable agent execution on orchestrator startup
```

**Change 4: Update GitHub Actions**

**File**: `/Users/ryan/src/AzureHayMaker/.github/workflows/deploy-dev.yml`

Add environment variable at line 202 (in the appsettings section):

```yaml
SIMULATION_SIZE="${{ secrets.SIMULATION_SIZE }}" \
AUTO_RUN_ON_STARTUP="true" \  # ← ADD THIS LINE
```

**Change 5: Make Configurable (Optional Enhancement)**

If you want to respect the `AUTO_RUN_ON_STARTUP` flag, modify line 58:

```python
import os

# At module level, after imports
AUTO_RUN_ON_STARTUP = os.getenv("AUTO_RUN_ON_STARTUP", "true").lower() == "true"

# In decorator
@app.timer_trigger(
    schedule="0 0 0,6,12,18 * * *",
    arg_name="timer_request",
    run_on_startup=AUTO_RUN_ON_STARTUP,  # ← Configurable
)
```

### Testing Strategy

**Unit Tests:**

Create `/Users/ryan/src/AzureHayMaker/tests/orchestrator/test_startup_trigger.py`:

```python
"""Tests for agent autostart functionality."""
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.asyncio
async def test_startup_trigger_enabled():
    """Test that run_on_startup is enabled."""
    from azure_haymaker.orchestrator import orchestrator

    # Check decorator configuration
    # This would need to inspect the function decorators
    # Implementation depends on testing framework
    assert orchestrator.AUTO_RUN_ON_STARTUP == True

@pytest.mark.asyncio
async def test_startup_skips_recent_execution():
    """Test that startup execution is skipped if recent run exists."""
    from azure_haymaker.orchestrator.orchestrator import haymaker_timer

    # Mock Table Storage with recent execution
    mock_table_client = Mock()
    mock_table_client.query_entities.return_value = [
        {"Timestamp": datetime.now(UTC)}
    ]

    with patch("azure.data.tables.TableServiceClient") as mock_table_service:
        mock_table_service.return_value.get_table_client.return_value = mock_table_client

        # Simulate startup trigger (no timer_request)
        result = await haymaker_timer(timer_request=None, durable_client=Mock())

        assert result["status"] == "skipped"
        assert result["reason"] == "recent_execution_detected"

@pytest.mark.asyncio
async def test_startup_proceeds_no_recent_execution():
    """Test that startup execution proceeds if no recent run."""
    from azure_haymaker.orchestrator.orchestrator import haymaker_timer

    # Mock Table Storage with no recent executions
    mock_table_client = Mock()
    mock_table_client.query_entities.return_value = []

    mock_durable_client = AsyncMock()
    mock_durable_client.start_new = AsyncMock(return_value="test-instance-id")

    with patch("azure.data.tables.TableServiceClient") as mock_table_service:
        mock_table_service.return_value.get_table_client.return_value = mock_table_client

        # Simulate startup trigger
        result = await haymaker_timer(timer_request=None, durable_client=mock_durable_client)

        # Should start new orchestration
        mock_durable_client.start_new.assert_called_once()
```

**Integration Tests:**

1. **Startup Execution Test**:
   ```bash
   # Deploy to dev environment
   az functionapp restart --name <function-app-name> --resource-group haymaker-dev-rg

   # Wait 30 seconds for cold start
   sleep 30

   # Check if agents started running
   haymaker agents list --status running

   # Should show agents executing
   ```

2. **Conflict Prevention Test**:
   ```bash
   # Trigger scheduled execution
   # Then immediately restart Function App
   az functionapp restart --name <function-app-name> --resource-group haymaker-dev-rg

   # Check logs - should see "Skipping startup execution" message
   az functionapp log tail --name <function-app-name> --resource-group haymaker-dev-rg
   ```

3. **Configuration Flag Test**:
   ```bash
   # Set AUTO_RUN_ON_STARTUP=false
   az functionapp config appsettings set \
     --name <function-app-name> \
     --resource-group haymaker-dev-rg \
     --settings AUTO_RUN_ON_STARTUP=false

   # Restart
   az functionapp restart --name <function-app-name> --resource-group haymaker-dev-rg

   # Should NOT start agents
   haymaker agents list --status running
   # Should show empty or only scheduled agents
   ```

**Acceptance Criteria:**
- [ ] `run_on_startup=True` set in orchestrator.py line 58
- [ ] Function App restart triggers agent execution
- [ ] Startup execution skipped if orchestration ran in last 5 minutes
- [ ] `AUTO_RUN_ON_STARTUP` environment variable added to .env.example
- [ ] GitHub Actions workflow includes `AUTO_RUN_ON_STARTUP=true`
- [ ] Startup execution tagged with `execution_type: "startup"` in logs
- [ ] Integration test verifies end-to-end startup flow
- [ ] No duplicate executions when startup coincides with scheduled run

### Rollback Plan

**Immediate Rollback:**
```bash
# Set run_on_startup=False via environment variable
az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group haymaker-dev-rg \
  --settings AUTO_RUN_ON_STARTUP=false

# Restart to apply
az functionapp restart --name <function-app-name> --resource-group haymaker-dev-rg
```

**Code Rollback:**
Revert line 58 to `run_on_startup=False` and redeploy.

### Dependencies

- **Blocks**: Requirement 3 (Agent Output Display) - needs agents running to generate logs
- **Depends On**: Requirement 1 (Service Bus) - must be working for event publishing

### Success Metrics

- Time to first agent execution after deployment: < 60 seconds
- Startup execution success rate: 100%
- Conflict detection accuracy: 100% (no duplicate executions)

### Estimated Effort

2-3 hours (including testing)

---

# Requirement 3: Agent Output Display

## Status: MEDIUM COMPLEXITY

### Investigation Finding

**Current State:**
- Agents API has placeholder log endpoint (lines 115-150 of agents_api.py)
- Comment at line 140: "logs should be queried from Log Analytics or Cosmos DB"
- `query_logs_from_servicebus()` returns empty list (line 150)
- CLI logs command exists but receives no data

**Architecture Gap:**
Logs published to Service Bus (real-time) but NOT stored in queryable database.

### Architecture Design

**Dual-Write Pattern:**

```
Agent Container Execution
        ↓
    Log Generation (stdout/stderr)
        ↓
    Event Bus Client
        ↓
    ├─→ Service Bus Topic (real-time streaming)
    │       └─→ Subscription (live monitoring)
    │
    └─→ Cosmos DB (historical storage)
            └─→ Logs Container
                    └─→ Query by agent_id, timestamp, level
```

**Data Flow:**

```
1. WRITE PATH:
   Agent → EventBus.publish_log()
       → ServiceBusClient.send_message() [real-time]
       → CosmosClient.upsert_item()      [persistent]

2. READ PATH (Historical):
   CLI → API GET /agents/{id}/logs
       → agents_api.query_logs_from_cosmosdb()
           → CosmosClient.query_items()
               → Format & Return

3. READ PATH (Real-time):
   CLI --follow → API (polling)
       → Query Cosmos DB with timestamp filter
           → Return new logs since last poll
```

**Cosmos DB Schema:**

```json
{
  "id": "log-{uuid}",
  "agent_id": "agent-abc123",
  "run_id": "run-xyz789",
  "scenario": "compute-01-linux-vm",
  "timestamp": "2025-11-17T12:00:00Z",
  "level": "INFO|WARNING|ERROR|DEBUG",
  "message": "Resource group created successfully",
  "source": "agent|orchestrator",
  "partition_key": "agent-abc123"  // Partition by agent_id for efficient queries
}
```

**Cosmos DB Container Configuration:**
- Container name: `agent-logs`
- Partition key: `/agent_id`
- TTL: 7 days (604800 seconds)
- Indexing: timestamp, level, run_id

### Implementation Plan

**Files to Modify:**

1. `/Users/ryan/src/AzureHayMaker/src/azure_haymaker/orchestrator/event_bus.py`
2. `/Users/ryan/src/AzureHayMaker/src/azure_haymaker/orchestrator/agents_api.py`
3. `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/cosmosdb.bicep`
4. `/Users/ryan/src/AzureHayMaker/cli/src/haymaker_cli/formatters.py`

**Change 1: Add Cosmos DB Dual-Write to Event Bus**

**File**: `/Users/ryan/src/AzureHayMaker/src/azure_haymaker/orchestrator/event_bus.py`

Locate the `publish_log()` method and add Cosmos DB write:

```python
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from datetime import datetime, UTC
from uuid import uuid4
import os

class EventBus:
    """Event bus for publishing agent events."""

    def __init__(self, servicebus_client, cosmos_client=None):
        self.servicebus_client = servicebus_client
        self.cosmos_client = cosmos_client

        # Initialize Cosmos DB if not provided
        if self.cosmos_client is None:
            cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
            if cosmos_endpoint:
                credential = DefaultAzureCredential()
                self.cosmos_client = CosmosClient(cosmos_endpoint, credential)

        # Get database and container
        if self.cosmos_client:
            self.database = self.cosmos_client.get_database_client("haymaker")
            self.logs_container = self.database.get_container_client("agent-logs")

    async def publish_log(
        self,
        agent_id: str,
        run_id: str,
        scenario: str,
        level: str,
        message: str,
        source: str = "agent"
    ) -> None:
        """Publish log entry to Service Bus and Cosmos DB.

        Args:
            agent_id: Agent identifier
            run_id: Execution run identifier
            scenario: Scenario name
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message content
            source: Log source (agent, orchestrator)
        """
        timestamp = datetime.now(UTC).isoformat()

        log_entry = {
            "agent_id": agent_id,
            "run_id": run_id,
            "scenario": scenario,
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "source": source
        }

        # WRITE 1: Service Bus (real-time streaming)
        try:
            sender = self.servicebus_client.get_topic_sender("agent-logs")
            async with sender:
                service_bus_message = ServiceBusMessage(
                    body=json.dumps(log_entry),
                    content_type="application/json"
                )
                await sender.send_messages(service_bus_message)
                logger.debug(f"Published log to Service Bus: {agent_id}")
        except Exception as e:
            logger.error(f"Failed to publish log to Service Bus: {e}")

        # WRITE 2: Cosmos DB (persistent storage)
        if self.logs_container:
            try:
                cosmos_item = {
                    "id": f"log-{uuid4()}",
                    "agent_id": agent_id,  # Partition key
                    "run_id": run_id,
                    "scenario": scenario,
                    "timestamp": timestamp,
                    "level": level,
                    "message": message,
                    "source": source,
                    "ttl": 604800  # 7 days in seconds
                }
                self.logs_container.upsert_item(cosmos_item)
                logger.debug(f"Stored log to Cosmos DB: {agent_id}")
            except Exception as e:
                logger.error(f"Failed to store log to Cosmos DB: {e}")
                # Non-critical failure - log continues to Service Bus
```

**Change 2: Implement Cosmos DB Log Query**

**File**: `/Users/ryan/src/AzureHayMaker/src/azure_haymaker/orchestrator/agents_api.py`

Replace lines 115-150 (`query_logs_from_servicebus`) with:

```python
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
import os

async def query_logs_from_cosmosdb(
    agent_id: str,
    tail: int = 100,
    since_timestamp: str = None,
) -> list[LogEntry]:
    """Query logs from Cosmos DB.

    Args:
        agent_id: Agent ID to filter logs
        tail: Number of recent entries to return (default: 100)
        since_timestamp: Optional ISO 8601 timestamp to get logs after

    Returns:
        List of log entries, sorted by timestamp (newest first)
    """
    logs = []

    try:
        # Initialize Cosmos DB client
        cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        if not cosmos_endpoint:
            logger.error("COSMOS_DB_ENDPOINT not configured")
            return logs

        credential = DefaultAzureCredential()
        cosmos_client = CosmosClient(cosmos_endpoint, credential)
        database = cosmos_client.get_database_client("haymaker")
        container = database.get_container_client("agent-logs")

        # Build query
        if since_timestamp:
            query = """
                SELECT * FROM c
                WHERE c.agent_id = @agent_id
                AND c.timestamp > @since_timestamp
                ORDER BY c.timestamp DESC
            """
            parameters = [
                {"name": "@agent_id", "value": agent_id},
                {"name": "@since_timestamp", "value": since_timestamp}
            ]
        else:
            query = """
                SELECT TOP @limit * FROM c
                WHERE c.agent_id = @agent_id
                ORDER BY c.timestamp DESC
            """
            parameters = [
                {"name": "@agent_id", "value": agent_id},
                {"name": "@limit", "value": tail}
            ]

        # Execute query
        items = list(container.query_items(
            query=query,
            parameters=parameters,
            partition_key=agent_id,
            enable_cross_partition_query=False
        ))

        # Convert to LogEntry objects
        for item in items:
            log_entry = LogEntry(
                timestamp=item.get("timestamp"),
                level=item.get("level", "INFO"),
                message=item.get("message", ""),
                agent_id=item.get("agent_id"),
                source=item.get("source", "agent")
            )
            logs.append(log_entry)

        logger.info(f"Retrieved {len(logs)} logs for agent {agent_id}")

    except Exception as e:
        logger.error(f"Error querying logs from Cosmos DB: {e}")
        raise

    return logs
```

**Update the HTTP endpoint to use new function (line 280):**

```python
@app.route(route="agents/{agent_id}/logs", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def get_agent_logs(req: func.HttpRequest) -> func.HttpResponse:
    """Get logs for a specific agent.

    Query Parameters:
        tail: Number of recent entries to return (default: 100)
        since: ISO 8601 timestamp to get logs after (for --follow mode)

    Response:
        200 OK: {
            "logs": [
                {
                    "timestamp": str (ISO 8601),
                    "level": str,
                    "message": str,
                    "agent_id": str,
                    "source": str
                }
            ]
        }
    """
    try:
        agent_id = req.route_params.get("agent_id")
        tail = int(req.params.get("tail", "100"))
        since_timestamp = req.params.get("since")

        # Query logs from Cosmos DB
        logs = await query_logs_from_cosmosdb(
            agent_id=agent_id,
            tail=tail,
            since_timestamp=since_timestamp
        )

        # Format response
        response_data = {
            "logs": [
                {
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "message": log.message,
                    "agent_id": log.agent_id,
                    "source": log.source
                }
                for log in logs
            ]
        }

        return func.HttpResponse(
            body=json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
```

**Change 3: Verify Cosmos DB Logs Container**

**File**: `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/cosmosdb.bicep`

Verify or add the agent-logs container:

```bicep
resource logsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'agent-logs'
  properties: {
    resource: {
      id: 'agent-logs'
      partitionKey: {
        paths: ['/agent_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        automatic: true
        indexingMode: 'consistent'
        includedPaths: [
          { path: '/timestamp/?' }
          { path: '/level/?' }
          { path: '/run_id/?' }
          { path: '/scenario/?' }
        ]
      }
      defaultTtl: 604800  // 7 days
    }
  }
}
```

**Change 4: Enhance CLI Formatter**

**File**: `/Users/ryan/src/AzureHayMaker/cli/src/haymaker_cli/formatters.py`

Add rich formatting for logs:

```python
from rich.console import Console
from rich.table import Table
from rich.text import Text
from datetime import datetime

def format_log_entries(logs: list[dict], follow: bool = False) -> str:
    """Format log entries with rich syntax highlighting.

    Args:
        logs: List of log entry dictionaries
        follow: If True, use streaming format (no table borders)

    Returns:
        Formatted log output string
    """
    console = Console()

    if follow:
        # Streaming format (no borders, continuous output)
        for log in logs:
            timestamp = log.get("timestamp", "")
            level = log.get("level", "INFO")
            message = log.get("message", "")

            # Color-code by level
            level_colors = {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red"
            }
            level_color = level_colors.get(level, "white")

            # Format timestamp (convert to local time)
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = timestamp[:8] if len(timestamp) >= 8 else timestamp

            # Print formatted log line
            console.print(
                f"[dim]{time_str}[/dim] [{level_color}]{level:8}[/{level_color}] {message}"
            )
    else:
        # Table format (default for tail mode)
        table = Table(title="Agent Logs", show_header=True, header_style="bold magenta")
        table.add_column("Timestamp", style="dim", width=20)
        table.add_column("Level", width=10)
        table.add_column("Message", width=80)

        for log in logs:
            timestamp = log.get("timestamp", "")
            level = log.get("level", "INFO")
            message = log.get("message", "")

            # Color-code level
            level_colors = {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red"
            }
            level_style = level_colors.get(level, "white")

            table.add_row(
                timestamp[:19],  # Trim milliseconds
                Text(level, style=level_style),
                message
            )

        console.print(table)

    return ""  # Output already printed to console
```

**Change 5: Update CLI Client for Polling**

**File**: `/Users/ryan/src/AzureHayMaker/cli/src/haymaker_cli/client.py`

Add follow mode support:

```python
import time
from datetime import datetime, UTC

def get_agent_logs(
    self,
    agent_id: str,
    tail: int = 100,
    follow: bool = False,
    poll_interval: int = 5
) -> list[dict]:
    """Get agent logs with optional follow mode.

    Args:
        agent_id: Agent identifier
        tail: Number of recent entries
        follow: If True, continuously poll for new logs
        poll_interval: Seconds between polls (default: 5)

    Returns:
        List of log entries
    """
    endpoint = f"{self.base_url}/api/v1/agents/{agent_id}/logs"

    if not follow:
        # Single query
        params = {"tail": tail}
        response = self.session.get(endpoint, params=params)
        response.raise_for_status()
        return response.json().get("logs", [])

    # Follow mode: continuous polling
    last_timestamp = None
    console.print(f"[bold green]Following logs for agent {agent_id}[/bold green] (Ctrl+C to exit)")

    try:
        while True:
            params = {}
            if last_timestamp:
                params["since"] = last_timestamp
            else:
                params["tail"] = tail

            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            logs = response.json().get("logs", [])

            if logs:
                # Display new logs
                format_log_entries(logs, follow=True)

                # Update last timestamp
                last_timestamp = logs[-1]["timestamp"]

            # Wait before next poll
            time.sleep(poll_interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following logs[/yellow]")
        return []
```

### Testing Strategy

**Unit Tests:**

Create `/Users/ryan/src/AzureHayMaker/tests/orchestrator/test_log_storage.py`:

```python
"""Tests for log storage and retrieval."""
import pytest
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.asyncio
async def test_dual_write_to_servicebus_and_cosmos():
    """Test that logs are written to both Service Bus and Cosmos DB."""
    from azure_haymaker.orchestrator.event_bus import EventBus

    mock_servicebus = Mock()
    mock_cosmos = Mock()

    event_bus = EventBus(mock_servicebus, mock_cosmos)

    await event_bus.publish_log(
        agent_id="test-agent",
        run_id="test-run",
        scenario="test-scenario",
        level="INFO",
        message="Test log message"
    )

    # Verify Service Bus write
    assert mock_servicebus.get_topic_sender.called

    # Verify Cosmos DB write
    assert mock_cosmos.get_database_client.called

@pytest.mark.asyncio
async def test_query_logs_from_cosmosdb():
    """Test querying logs from Cosmos DB."""
    from azure_haymaker.orchestrator.agents_api import query_logs_from_cosmosdb

    # Mock Cosmos DB response
    mock_container = Mock()
    mock_container.query_items.return_value = [
        {
            "id": "log-1",
            "agent_id": "test-agent",
            "timestamp": "2025-11-17T12:00:00Z",
            "level": "INFO",
            "message": "Test message",
            "source": "agent"
        }
    ]

    with patch("azure.cosmos.CosmosClient") as mock_cosmos:
        mock_cosmos.return_value.get_database_client.return_value.\
            get_container_client.return_value = mock_container

        logs = await query_logs_from_cosmosdb(agent_id="test-agent", tail=10)

        assert len(logs) == 1
        assert logs[0].message == "Test message"
```

**Integration Tests:**

1. **End-to-End Log Flow Test**:
   ```bash
   # Start agent execution
   haymaker deploy --scenario compute-01-linux-vm --wait &
   AGENT_PID=$!

   # Wait for agent to start
   sleep 30

   # Get agent ID
   AGENT_ID=$(haymaker agents list --status running --format json | jq -r '.agents[0].agent_id')

   # Query logs
   haymaker logs --agent-id "$AGENT_ID" --tail 50

   # Should show log entries
   # Verify logs exist in Cosmos DB
   ```

2. **Follow Mode Test**:
   ```bash
   # Start following logs
   haymaker logs --agent-id "$AGENT_ID" --follow &
   FOLLOW_PID=$!

   # Agent continues to generate logs
   # Verify new logs appear in follow output

   # Stop following
   kill $FOLLOW_PID
   ```

3. **Persistence Test**:
   ```bash
   # Query logs after agent completes
   haymaker logs --agent-id "$AGENT_ID" --tail 100

   # Should still return logs (from Cosmos DB)
   ```

**Acceptance Criteria:**
- [ ] Logs stored in Cosmos DB agent-logs container
- [ ] Logs queryable via API GET /api/v1/agents/{id}/logs
- [ ] CLI command `haymaker logs --agent-id <id>` displays logs
- [ ] CLI command `haymaker logs --agent-id <id> --tail 50` limits output
- [ ] CLI command `haymaker logs --agent-id <id> --follow` streams logs
- [ ] Logs formatted with syntax highlighting (colors for levels)
- [ ] Logs include timestamp, level, message, agent_id
- [ ] Logs retained for 7 days minimum (TTL configured)
- [ ] Integration test verifies end-to-end flow

### Rollback Plan

**Phase 1**: Remove Cosmos DB writes, keep Service Bus only
```python
# In event_bus.py, comment out Cosmos DB write block
# System continues with real-time streaming only
```

**Phase 2**: Revert API changes
```python
# Restore query_logs_from_servicebus() placeholder
# CLI shows empty logs (graceful degradation)
```

### Dependencies

- **Depends On**: Requirement 2 (Agent Autostart) - needs agents running to generate logs
- **Blocks**: Requirement 5 (Presentation) - needs working log display for demo

### Success Metrics

- Log availability latency: < 30 seconds
- Query response time: < 2 seconds for 100 logs
- Log retention: 7 days minimum
- Follow mode update latency: < 5 seconds

### Estimated Effort

3-4 hours (including testing)

---

# Requirement 4: Secret Management Consolidation

## Status: SECURITY CRITICAL

### Investigation Finding

**CRITICAL SECURITY ISSUE IDENTIFIED:**

The dev environment (deploy-dev.yml lines 183-206) directly injects secrets as Function App environment variables, making them visible in Azure Portal. This violates security best practices and creates inconsistency with staging/prod environments.

**Current State Comparison:**

| Environment | Secret Management | Security Level |
|-------------|------------------|----------------|
| **Dev** | Direct injection via `az functionapp config appsettings set` | ❌ INSECURE |
| **Staging** | Key Vault injection + references in Bicep | ✅ SECURE |
| **Production** | Key Vault injection + references in Bicep | ✅ SECURE |

**Evidence:**

**Dev (INSECURE) - deploy-dev.yml lines 183-206:**
```yaml
- name: Configure Function App settings with secrets
  run: |
    az functionapp config appsettings set \
      --name "$FUNCTION_APP_NAME" \
      --resource-group "$RG_NAME" \
      --settings \
        AZURE_CLIENT_SECRET="${{ secrets.MAIN_SP_CLIENT_SECRET }}" \  # ← EXPOSED
        ANTHROPIC_API_KEY="${{ secrets.ANTHROPIC_API_KEY }}" \        # ← EXPOSED
```

**Staging (SECURE) - deploy-staging.yml lines 136-158:**
```yaml
- name: Inject secrets to Key Vault
  run: |
    az keyvault secret set \
      --vault-name ${{ steps.deploy.outputs.keyVaultName }} \
      --name main-sp-client-secret \
      --value "${{ secrets.MAIN_SP_CLIENT_SECRET }}"  # ← SECURE (in KV)
```

**Function App (SECURE) - function-app.bicep lines 152-164:**
```bicep
{
  name: 'ANTHROPIC_API_KEY'
  value: '@Microsoft.KeyVault(VaultName=${split(keyVaultUri, '.')[0]};SecretName=anthropic-api-key)'
}
```

### Architecture Design

**Target Architecture (Standardized Across All Environments):**

```
GitHub Secrets
        ↓
    GitHub Actions Workflow
        ↓
    Azure Key Vault (Secret Injection)
        ├─→ main-sp-client-secret
        ├─→ anthropic-api-key
        └─→ log-analytics-workspace-key
        ↓
    Function App (Key Vault References)
        ├─→ MAIN_SP_CLIENT_SECRET = @Microsoft.KeyVault(...)
        ├─→ ANTHROPIC_API_KEY = @Microsoft.KeyVault(...)
        └─→ LOG_ANALYTICS_WORKSPACE_KEY = @Microsoft.KeyVault(...)
        ↓
    Application Code (reads from env vars)
        → DefaultAzureCredential → Key Vault → Secret Value
```

**Security Flow:**

```
Deployment Time:
    GitHub Secrets → Key Vault (via az keyvault secret set)

Runtime:
    Function App → Managed Identity → Key Vault RBAC
        → Key Vault Secrets User role
            → Read secret value
                → Return to application as env var
```

**RBAC Configuration:**

```
Function App Managed Identity
    → Role: "Key Vault Secrets User" (00482a5a-887f-4fb3-b363-3b7fe8e74483)
        → Scope: Key Vault resource
            → Permissions: Get secret values only (no list, no set)
```

### Implementation Plan

**Files to Modify:**

1. `/Users/ryan/src/AzureHayMaker/.github/workflows/deploy-dev.yml`
2. `/Users/ryan/src/AzureHayMaker/.env.example`
3. `/Users/ryan/src/AzureHayMaker/README.md`
4. `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/function-app.bicep` (verify only)

**Change 1: Replace Direct Secret Injection with Key Vault Pattern**

**File**: `/Users/ryan/src/AzureHayMaker/.github/workflows/deploy-dev.yml`

**REMOVE lines 183-206** and REPLACE with:

```yaml
      - name: Inject secrets to Key Vault
        run: |
          echo "Injecting secrets to Key Vault: ${{ steps.deploy.outputs.keyVaultName }}"

          # Store secrets in Key Vault
          az keyvault secret set \
            --vault-name ${{ steps.deploy.outputs.keyVaultName }} \
            --name main-sp-client-secret \
            --value "${{ secrets.MAIN_SP_CLIENT_SECRET }}" \
            --output none

          az keyvault secret set \
            --vault-name ${{ steps.deploy.outputs.keyVaultName }} \
            --name anthropic-api-key \
            --value "${{ secrets.ANTHROPIC_API_KEY }}" \
            --output none

          az keyvault secret set \
            --vault-name ${{ steps.deploy.outputs.keyVaultName }} \
            --name log-analytics-workspace-key \
            --value "${{ secrets.LOG_ANALYTICS_WORKSPACE_KEY }}" \
            --output none

          echo "✓ Secrets injected to Key Vault successfully"

      - name: Wait for RBAC propagation
        run: |
          echo "Waiting 60 seconds for RBAC role assignments to propagate..."
          sleep 60
          echo "✓ RBAC propagation complete"

      - name: Verify Key Vault access from Function App
        run: |
          echo "Verifying Function App can access Key Vault..."
          FUNCTION_APP_NAME="${{ steps.deploy.outputs.functionAppName }}"

          # Test Key Vault reference resolution
          # Function App should be able to read secrets via Managed Identity
          az functionapp config appsettings list \
            --name "$FUNCTION_APP_NAME" \
            --resource-group "${{ steps.deploy.outputs.resourceGroupName }}" \
            --query "[?name=='ANTHROPIC_API_KEY'].value" \
            --output tsv | grep -q "@Microsoft.KeyVault" && echo "✓ Key Vault references configured" || echo "⚠ Key Vault references not found"
```

**Change 2: Update Configuration Documentation**

**File**: `/Users/ryan/src/AzureHayMaker/.env.example`

Update comments to clarify local vs production usage:

```bash
# ============================================================================
# Azure HayMaker Configuration
# ============================================================================
#
# LOCAL DEVELOPMENT ONLY:
#   - This file is for local development and testing
#   - Copy to .env and fill in your values
#   - .env is gitignored and NEVER committed to version control
#
# PRODUCTION (Azure Function App):
#   - Secrets stored in Azure Key Vault
#   - Function App references secrets via @Microsoft.KeyVault() syntax
#   - GitHub Actions injects secrets to Key Vault during deployment
#
# ============================================================================

# Azure Identity (Required)
AZURE_TENANT_ID=your-tenant-id
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_CLIENT_ID=your-client-id

# Secret (LOCAL DEV ONLY - Production uses Key Vault)
AZURE_CLIENT_SECRET=your-client-secret

# Anthropic API (LOCAL DEV ONLY - Production uses Key Vault)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Log Analytics (LOCAL DEV ONLY - Production uses Key Vault)
LOG_ANALYTICS_WORKSPACE_KEY=your-workspace-key

# Simulation Configuration
SIMULATION_SIZE=small  # Options: small (5), medium (15), large (30)

# Agent Execution
AUTO_RUN_ON_STARTUP=true  # Enable/disable agent execution on orchestrator startup
```

**Change 3: Update README Configuration Section**

**File**: `/Users/ryan/src/AzureHayMaker/README.md`

Replace configuration priority section (around line 47-51):

```markdown
## Configuration

Azure HayMaker uses different secret management approaches for local development vs production:

### Local Development

Secrets are loaded from `.env` file:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your Azure credentials and Anthropic API key

3. Run locally:
   ```bash
   cd src
   uv run func start
   ```

**Important**: The `.env` file is gitignored and must never be committed to version control.

### Production (Azure Function App)

Secrets are managed securely via Azure Key Vault:

1. **Deployment**: GitHub Actions injects secrets to Key Vault
   ```bash
   az keyvault secret set --vault-name <keyvault> --name anthropic-api-key --value "$SECRET"
   ```

2. **Runtime**: Function App uses Key Vault references
   ```bicep
   {
     name: 'ANTHROPIC_API_KEY'
     value: '@Microsoft.KeyVault(VaultName=mykeyvault;SecretName=anthropic-api-key)'
   }
   ```

3. **Access**: Function App Managed Identity has "Key Vault Secrets User" role

**Security Benefits:**
- Secrets never visible in Azure Portal
- Automatic secret rotation support
- Audit logging via Key Vault diagnostics
- RBAC-based access control

### Configuration Priority

The application loads configuration in this order:

1. **Local Development**: `.env` file (gitignored)
2. **Production**: Azure Key Vault (via references)

Environment variables are NOT used in production to avoid accidental secret exposure.
```

**Change 4: Verify Function App Bicep Configuration**

**File**: `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/function-app.bicep`

**No changes needed** - lines 152-164 already correctly configure Key Vault references:

```bicep
// Secrets from Key Vault (referenced)
{
  name: 'MAIN_SP_CLIENT_SECRET'
  value: '@Microsoft.KeyVault(VaultName=${split(keyVaultUri, '.')[0]};SecretName=main-sp-client-secret)'
}
{
  name: 'ANTHROPIC_API_KEY'
  value: '@Microsoft.KeyVault(VaultName=${split(keyVaultUri, '.')[0]};SecretName=anthropic-api-key)'
}
{
  name: 'LOG_ANALYTICS_WORKSPACE_KEY'
  value: '@Microsoft.KeyVault(VaultName=${split(keyVaultUri, '.')[0]};SecretName=log-analytics-workspace-key)'
}
```

**Verification**: Confirm these settings exist for ALL environments (dev, staging, prod).

**Change 5: Verify RBAC Configuration**

**File**: `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/keyvault.bicep`

Ensure Function App has correct RBAC role:

```bicep
// Grant Function App access to Key Vault secrets
resource keyVaultSecretUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, functionAppPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')  // Key Vault Secrets User
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}
```

### Testing Strategy

**Pre-Deployment Verification:**

1. **Verify .env not tracked**:
   ```bash
   git status | grep -q ".env" && echo "ERROR: .env is tracked!" || echo "✓ .env not tracked"
   ```

2. **Verify .gitignore coverage**:
   ```bash
   cat .gitignore | grep -E "^\.env$|^\.env\.local$" && echo "✓ .env patterns covered"
   ```

**Deployment Tests:**

1. **Dev Environment Secret Injection Test**:
   ```bash
   # Trigger deploy-dev workflow
   gh workflow run deploy-dev.yml

   # Wait for completion
   gh run watch

   # Verify secrets in Key Vault
   az keyvault secret list --vault-name <keyvault-name> --query "[].name"
   # Should show: main-sp-client-secret, anthropic-api-key, log-analytics-workspace-key
   ```

2. **Function App Key Vault Access Test**:
   ```bash
   # Get Function App settings
   az functionapp config appsettings list \
     --name <function-app-name> \
     --resource-group haymaker-dev-rg \
     --query "[?name=='ANTHROPIC_API_KEY']"

   # Should show: @Microsoft.KeyVault(VaultName=...) NOT the actual key
   ```

3. **Runtime Secret Access Test**:
   ```bash
   # Check Function App logs
   az functionapp log tail --name <function-app-name> --resource-group haymaker-dev-rg

   # Should show successful startup, no "KeyVault access denied" errors
   ```

4. **RBAC Verification Test**:
   ```bash
   # Get Function App Managed Identity
   FUNCTION_APP_PRINCIPAL_ID=$(az functionapp identity show \
     --name <function-app-name> \
     --resource-group haymaker-dev-rg \
     --query principalId -o tsv)

   # Verify Key Vault role assignment
   az role assignment list \
     --assignee "$FUNCTION_APP_PRINCIPAL_ID" \
     --scope "/subscriptions/<sub-id>/resourceGroups/haymaker-dev-rg/providers/Microsoft.KeyVault/vaults/<keyvault-name>" \
     --query "[?roleDefinitionName=='Key Vault Secrets User']"

   # Should return role assignment
   ```

5. **Secret Visibility Test** (Security Validation):
   ```bash
   # Check Azure Portal
   # Navigate to Function App → Configuration → Application Settings
   # ANTHROPIC_API_KEY value should show: @Microsoft.KeyVault(...)
   # NOT the actual API key

   # Verify GitHub Actions logs
   # Search workflow logs for secret values
   # Should be masked with ***
   ```

6. **Secret Rotation Test**:
   ```bash
   # Update secret in Key Vault
   az keyvault secret set \
     --vault-name <keyvault-name> \
     --name anthropic-api-key \
     --value "new-test-key"

   # Restart Function App
   az functionapp restart --name <function-app-name> --resource-group haymaker-dev-rg

   # Verify new secret picked up (check logs for successful API calls)
   ```

**Acceptance Criteria:**
- [ ] `.env` file not tracked by git
- [ ] `.env` file in .gitignore
- [ ] `.env.example` clearly documents local development usage
- [ ] README.md configuration section updated (local vs production)
- [ ] GitHub Actions deploys secrets to Key Vault (not direct injection)
- [ ] Function App uses Key Vault references (@Microsoft.KeyVault syntax)
- [ ] Function App Managed Identity has "Key Vault Secrets User" role
- [ ] Function App successfully reads secrets from Key Vault at runtime
- [ ] Secrets NOT visible in Azure Portal Function App settings
- [ ] No secrets visible in GitHub Actions logs
- [ ] Secret rotation works without code changes
- [ ] RBAC properly configured with 60-second wait for propagation

### Security Considerations

**Threat Model:**

| Threat | Mitigation |
|--------|------------|
| Secrets in git history | .gitignore + pre-commit hooks |
| Secrets in Azure Portal | Key Vault references (not direct values) |
| Secrets in CI/CD logs | GitHub Actions add-mask |
| Unauthorized secret access | RBAC: Key Vault Secrets User role only |
| Secret rotation | Key Vault automatic rotation support |
| Audit requirements | Key Vault diagnostic logging |

**Security Validations:**

1. **No Secrets in Version Control**:
   ```bash
   git log --all --full-history -- .env
   # Should show: "fatal: ambiguous argument '.env': unknown revision or path"
   ```

2. **GitHub Actions Log Masking**:
   ```yaml
   - name: Inject secrets to Key Vault
     run: |
       # Secrets are automatically masked by GitHub
       # Verify workflow logs show *** instead of actual values
   ```

3. **Key Vault Access Audit**:
   ```bash
   # Enable Key Vault diagnostic logging
   az monitor diagnostic-settings create \
     --resource <keyvault-id> \
     --name audit-logs \
     --logs '[{"category": "AuditEvent", "enabled": true}]' \
     --workspace <log-analytics-workspace-id>
   ```

4. **Least Privilege Verification**:
   ```bash
   # Function App should ONLY have "Key Vault Secrets User" role
   # NOT "Key Vault Administrator" or "Key Vault Secrets Officer"
   az role assignment list --assignee <function-app-principal-id> --all
   ```

### Rollback Plan

**Immediate Rollback** (if Key Vault access fails):

1. **Revert to direct injection temporarily**:
   ```bash
   # Manual override via Azure CLI
   az functionapp config appsettings set \
     --name <function-app-name> \
     --resource-group haymaker-dev-rg \
     --settings \
       ANTHROPIC_API_KEY="${{ secrets.ANTHROPIC_API_KEY }}"
   ```

2. **Diagnose RBAC issue**:
   ```bash
   # Check role assignment
   az role assignment list --assignee <principal-id> --scope <keyvault-id>

   # Wait additional time for RBAC propagation (can take up to 10 minutes)
   ```

3. **Re-enable Key Vault references**:
   ```bash
   # Remove direct settings
   az functionapp config appsettings delete \
     --name <function-app-name> \
     --resource-group haymaker-dev-rg \
     --setting-names ANTHROPIC_API_KEY

   # Bicep references automatically restored on next deployment
   ```

**Code Rollback:**

Revert deploy-dev.yml to previous version:
```bash
git revert <commit-hash>
git push origin develop
```

### Dependencies

- **Depends On**: Requirement 1 (Service Bus) - Key Vault must be deployed
- **Blocks**: None (independent), but should be completed before Requirement 5 (presentation)

### Success Metrics

- Secret visibility in Portal: 0 (should show Key Vault references only)
- RBAC configuration time: < 90 seconds (including propagation wait)
- Secret rotation time: < 2 minutes (update + restart)
- Configuration complexity: 1 location per environment (Key Vault)

### Estimated Effort

4-6 hours (including extensive security testing and validation)

---

# Requirement 5: Comprehensive Presentation

## Status: COMPLEX

### Objective

Create a professional PowerPoint presentation (25-35 slides) demonstrating Azure HayMaker architecture, deployment process, CLI usage, and real agent execution examples.

### Investigation Finding

**Dependencies**: This requirement MUST be completed AFTER all other requirements are working, as it requires real system examples and screenshots.

**Presentation Audience**: Technical stakeholders (developers, architects, management)

### Architecture Design

**Presentation Structure:**

```
Section A: Overview & Architecture (8-12 slides)
    ├─→ Cover slide (hay farm image)
    ├─→ Problem statement
    ├─→ Solution overview
    ├─→ Architecture diagrams
    ├─→ Component breakdown
    ├─→ Technology stack
    ├─→ Security model
    └─→ Execution flow

Section B: Deployment Guide (6-8 slides)
    ├─→ Prerequisites
    ├─→ GitOps workflow
    ├─→ GitHub Actions pipeline
    ├─→ Bicep infrastructure
    ├─→ Environment configuration
    ├─→ Secret management (Key Vault)
    └─→ Troubleshooting

Section C: CLI Usage Guide (6-8 slides)
    ├─→ Installation
    ├─→ Configuration
    ├─→ Core commands (with examples)
    ├─→ Real command outputs
    └─→ Advanced patterns

Section D: Real Agent Execution Demo (4-6 slides)
    ├─→ Scenario selection
    ├─→ Deployment command
    ├─→ Agent execution logs
    ├─→ Resources created (screenshots)
    ├─→ Cleanup verification
    └─→ Metrics dashboard
```

### Implementation Plan

**Prerequisites (MUST be completed first):**

1. ✅ Requirements 1-4 implemented and tested
2. ✅ Dev environment deployed and stable
3. ✅ Agents successfully executing
4. ✅ CLI commands working
5. ✅ Logs displaying correctly

**Phase 1: Content Preparation (2-3 hours)**

**Step 1: Capture Real System Outputs**

```bash
# Deploy agent
haymaker deploy --scenario compute-01-linux-vm-web-server --wait

# Capture CLI outputs
haymaker status > outputs/status.txt
haymaker agents list > outputs/agents_list.txt
haymaker agents list --status running --format json > outputs/agents_running.json

# Get agent ID
AGENT_ID=$(jq -r '.agents[0].agent_id' outputs/agents_running.json)

# Capture logs
haymaker logs --agent-id "$AGENT_ID" --tail 100 > outputs/agent_logs.txt

# Capture resources
haymaker resources list --scenario compute-01-linux-vm > outputs/resources.txt
```

**Step 2: Capture Azure Portal Screenshots**

Required screenshots:
1. Resource Group overview (all resources)
2. Function App overview (running status)
3. Key Vault secrets list (without values)
4. Service Bus topic and subscription
5. Container Apps environment
6. Application Insights dashboard
7. Created agent resources (VM, NSG, VNET, etc.)

**Step 3: Source Content from Documentation**

Files to reference:
- `/Users/ryan/src/AzureHayMaker/specs/architecture.md` (architecture diagrams)
- `/Users/ryan/src/AzureHayMaker/README.md` (quick start)
- `/Users/ryan/src/AzureHayMaker/docs/architecture/orchestrator.md` (orchestrator details)
- `/Users/ryan/src/AzureHayMaker/.github/workflows/deploy-dev.yml` (GitOps pipeline)

**Step 4: Find Hay Farm Image**

Options:
1. Unsplash API: Search for "hay farm" or "haystack"
2. Pexels API: Search for "hay bales field"
3. Local image if available
4. AI-generated image (DALL-E, Midjourney)

**Phase 2: Presentation Creation (4-6 hours)**

**File Output**: `/Users/ryan/src/AzureHayMaker/docs/presentations/Azure_HayMaker_Overview.pptx`

**Slide Outline:**

**Section A: Overview & Architecture (10 slides)**

1. **Cover Slide**
   - Title: "Azure HayMaker: Autonomous Cloud Security Testing"
   - Subtitle: "Architecture, Deployment, and Demo"
   - Background: Hay farm image
   - Date: November 2025

2. **Problem Statement**
   - Challenge: Verifying Azure security configurations at scale
   - Manual testing is error-prone and time-consuming
   - Need for continuous, autonomous security validation
   - Bullet points with icons

3. **Solution Overview**
   - Azure HayMaker: Autonomous AI agents testing cloud security
   - Self-provisioning, self-contained, self-cleaning
   - Parallel execution of multiple scenarios
   - Key metrics: 30+ scenarios, 8-hour execution, automatic cleanup

4. **High-Level Architecture**
   - Architecture diagram from specs/architecture.md
   - Components: Orchestrator, Agents, Event Bus, Storage
   - Flow: Timer → Orchestration → Provisioning → Execution → Cleanup

5. **Orchestrator Component**
   - Azure Durable Functions
   - Timer trigger (4x daily + startup)
   - Scenario selection based on simulation size
   - 8-hour monitoring window
   - Automatic cleanup verification

6. **Agent Execution Layer**
   - Container Apps (ephemeral)
   - Claude Sonnet 4.5 AI agent
   - Scenario-specific instructions
   - Service principal with Contributor role
   - Resource tagging for cleanup

7. **Event System**
   - Service Bus topic: agent-logs
   - Real-time log streaming
   - Cosmos DB: Historical storage (7-day TTL)
   - CLI: Live monitoring with --follow

8. **Technology Stack**
   - Python 3.13 + Azure Functions
   - Azure Durable Functions
   - Container Apps (agent execution)
   - Service Bus (event streaming)
   - Cosmos DB (log storage)
   - Key Vault (secret management)
   - GitHub Actions (GitOps)

9. **Security Model**
   - Ephemeral service principals (scenario-specific)
   - Key Vault references (no direct secrets)
   - RBAC: Contributor + Reader roles
   - Managed Identity for Function App
   - Automatic secret rotation support

10. **Execution Flow**
    - Timer trigger fires (or startup)
    - Scenario selection (random, based on simulation size)
    - Parallel SP creation + Container deployment
    - 8-hour monitoring (15-minute status checks)
    - Cleanup verification + forced deletion
    - Report generation

**Section B: Deployment Guide (7 slides)**

11. **Prerequisites**
    - Azure subscription (with quota)
    - GitHub repository
    - Azure CLI + Bicep
    - Service Principal with OIDC
    - GitHub Secrets configured

12. **GitOps Workflow**
    - Diagram: GitHub → Actions → Bicep → Azure
    - Push to develop → Deploy to dev
    - Push to main → Deploy to staging
    - Release tag → Deploy to prod
    - Fully automated, no manual steps

13. **GitHub Actions Pipeline**
    - Stage 1: Validate (Bicep validation)
    - Stage 2: Test (pytest, ruff)
    - Stage 3: Deploy Infrastructure (Bicep deployment)
    - Stage 4: Deploy Function (Azure Functions Action)
    - Stage 5: Smoke Tests (resource verification)

14. **Bicep Infrastructure-as-Code**
    - Modular design: main.bicep + modules/
    - Parameterized by environment (dev.bicepparam)
    - Idempotent deployments
    - Resource naming convention: haymaker-{env}-{resource}
    - Optional resources for dev (Cosmos, Registry)

15. **Environment Configuration**
    - Dev: Standard SKU (cost-optimized)
    - Staging: Production-like (Elastic Premium)
    - Prod: Elastic Premium + redundancy
    - Simulation size: small/medium/large
    - Auto-run on startup: configurable

16. **Secret Management**
    - Local: .env file (gitignored)
    - Production: Azure Key Vault
    - GitHub Actions: Injects secrets to Key Vault
    - Function App: Key Vault references (@Microsoft.KeyVault)
    - No secrets in Portal or logs

17. **Troubleshooting**
    - Common issues:
      - Quota exceeded: Use S1 plan for dev
      - RBAC propagation: Wait 60 seconds
      - Key Vault access denied: Check Managed Identity role
      - Service Bus already exists: Idempotent (no action needed)
    - Logs: Application Insights, Function App logs
    - CLI: `haymaker status`, `haymaker logs`

**Section C: CLI Usage Guide (8 slides)**

18. **Installation**
    ```bash
    # Install uv package manager
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Clone repository
    git clone https://github.com/your-org/AzureHayMaker.git
    cd AzureHayMaker/cli

    # Install CLI
    uv sync
    uv run haymaker --help
    ```

19. **Configuration**
    ```bash
    # Set API endpoint
    haymaker config set endpoint https://haymaker-dev-func.azurewebsites.net

    # Verify configuration
    haymaker config list

    # Test connection
    haymaker status
    ```

20. **Core Commands: Status**
    ```bash
    $ haymaker status

    ✓ Orchestrator: Running
    ✓ Last execution: 2025-11-17 12:00 UTC
    ✓ Next scheduled: 2025-11-17 18:00 UTC
    ✓ Active agents: 5
    ✓ Pending cleanup: 0 resources
    ```

21. **Core Commands: Agents List**
    ```bash
    $ haymaker agents list --status running

    | Agent ID         | Scenario                  | Status  | Started At       |
    |------------------|---------------------------|---------|------------------|
    | agent-abc123     | compute-01-linux-vm       | Running | 12:05 UTC        |
    | agent-def456     | storage-01-blob-account   | Running | 12:07 UTC        |
    | agent-ghi789     | network-01-vnet-peering   | Running | 12:10 UTC        |
    ```

22. **Core Commands: Logs (Tail)**
    ```bash
    $ haymaker logs --agent-id agent-abc123 --tail 10

    12:05:23 INFO     Starting scenario: compute-01-linux-vm
    12:05:45 INFO     Resource group created: rg-agent-abc123
    12:06:12 INFO     Virtual network created: vnet-web
    12:06:34 INFO     Network security group configured
    12:07:01 INFO     Virtual machine deployed: vm-web-server
    12:07:23 WARNING  Public IP address exposed (expected)
    12:08:45 INFO     Web server accessible at http://40.112.45.67
    12:09:12 INFO     Security validation: PASSED
    12:15:34 INFO     Initiating cleanup...
    12:16:01 INFO     Cleanup completed successfully
    ```

23. **Core Commands: Logs (Follow)**
    ```bash
    $ haymaker logs --agent-id agent-abc123 --follow

    Following logs for agent agent-abc123 (Ctrl+C to exit)

    12:05:23 INFO     Starting scenario: compute-01-linux-vm
    12:05:45 INFO     Resource group created: rg-agent-abc123
    12:06:12 INFO     Virtual network created: vnet-web
    [... logs continue streaming ...]
    ```

24. **Core Commands: Resources**
    ```bash
    $ haymaker resources list --scenario compute-01-linux-vm

    | Resource Type          | Resource Name         | Status    | Tags                    |
    |------------------------|-----------------------|-----------|-------------------------|
    | Resource Group         | rg-agent-abc123       | Active    | Scenario=compute-01     |
    | Virtual Network        | vnet-web              | Active    | Agent=agent-abc123      |
    | Network Security Group | nsg-web               | Active    | RunId=run-xyz789        |
    | Public IP Address      | pip-web               | Active    | ManagedBy=AzureHayMaker |
    | Virtual Machine        | vm-web-server         | Running   | AutoCleanup=true        |
    ```

25. **Advanced Usage: Deploy On-Demand**
    ```bash
    # Deploy specific scenario immediately
    $ haymaker deploy --scenario compute-01-linux-vm --wait

    Deploying scenario: compute-01-linux-vm
    ✓ Service principal created: AzureHayMaker-compute-01-admin
    ✓ Container app deployed: ca-agent-abc123
    ⏳ Waiting for completion (max 2 hours)...
    ✓ Execution completed successfully

    Agent ID: agent-abc123
    Duration: 15m 34s
    Resources: 5 created, 5 cleaned up
    Status: Success
    ```

**Section D: Real Agent Execution Demo (6 slides)**

26. **Demo Scenario: Linux VM Web Server**
    - Scenario: compute-01-linux-vm-web-server
    - Objective: Deploy and test Linux VM with web server
    - Security validations:
      - NSG rules configured correctly
      - Public IP accessible
      - Web server responding
      - Cleanup successful

27. **Demo: Deployment Command**
    - Screenshot: Terminal showing deploy command
    - Output: Service principal creation progress
    - Output: Container app deployment status
    - Time started: 12:05 UTC

28. **Demo: Agent Execution Logs**
    - Screenshot: `haymaker logs --follow` output
    - Highlights:
      - Resource group creation
      - Virtual network setup
      - NSG configuration
      - VM deployment
      - Web server validation
      - Cleanup initiation

29. **Demo: Resources Created (Azure Portal)**
    - Screenshot: Resource group with 5 resources
    - Screenshot: Virtual machine details (running)
    - Screenshot: Network security group rules
    - Screenshot: Public IP address configuration
    - Tags visible: Scenario, Agent, RunId, ManagedBy

30. **Demo: Cleanup Verification**
    ```bash
    $ haymaker resources list --scenario compute-01-linux-vm

    No resources found (cleanup completed)

    $ haymaker agents list --agent-id agent-abc123

    Agent ID: agent-abc123
    Status: Completed
    Duration: 15m 34s
    Resources created: 5
    Resources cleaned: 5
    Cleanup status: Verified
    ```

31. **Demo: Metrics Dashboard**
    - Screenshot: Application Insights dashboard
    - Metrics:
      - Total executions: 120
      - Success rate: 98.3%
      - Average duration: 14m 22s
      - Cleanup success: 100%
      - Resource types tested: 8
    - Chart: Executions over time (last 30 days)

**Closing Slides (2-3 slides)**

32. **Key Takeaways**
    - Autonomous security testing at scale
    - Self-provisioning, self-contained, self-cleaning
    - GitOps-driven deployment
    - Real-time monitoring and logging
    - 30+ scenarios, continuous validation

33. **Future Enhancements**
    - Additional scenario categories (databases, AI services)
    - Multi-region deployments
    - Custom scenario framework
    - Integration with Azure DevOps
    - Advanced security reporting

34. **Q&A / Resources**
    - GitHub Repository: https://github.com/your-org/AzureHayMaker
    - Documentation: https://azurehaymaker.dev/docs
    - Issues: https://github.com/your-org/AzureHayMaker/issues
    - Contact: your-team@company.com
    - Thank you slide

**Phase 3: Presentation Generation (1-2 hours)**

**Use PPTX Skill:**

```bash
# Invoke PPTX skill
# Provide slide outline and content
# Include screenshots and code examples
# Apply professional theme
```

### Testing Strategy

**Quality Checks:**

1. **Content Accuracy**:
   - All code examples are real (from actual system)
   - Screenshots match current system state
   - Architecture diagrams accurate
   - No placeholder content

2. **Visual Quality**:
   - Slides readable on projector (font size ≥ 18pt)
   - Screenshots high-resolution (1920x1080 min)
   - Consistent color scheme
   - Professional layout

3. **Technical Correctness**:
   - Commands work as shown
   - Outputs match examples
   - URLs valid
   - Version numbers current

4. **Presentation Flow**:
   - Logical progression
   - Clear transitions
   - No repetitive content
   - Engaging narrative

**Review Process:**

1. **Technical Review** (by builder):
   - Verify all technical details
   - Test all commands
   - Validate screenshots

2. **Presentation Review** (by stakeholder):
   - Check narrative flow
   - Verify audience appropriateness
   - Suggest improvements

3. **Final Polish**:
   - Apply feedback
   - Proofread all text
   - Check slide numbers
   - Test file opens correctly

**Acceptance Criteria:**
- [ ] Presentation 25-35 slides total
- [ ] Cover slide includes hay farm image
- [ ] Section A: Overview & Architecture (8-12 slides)
- [ ] Section B: Deployment Guide (6-8 slides)
- [ ] Section C: CLI Usage Guide (6-8 slides)
- [ ] Section D: Real Agent Execution Demo (4-6 slides)
- [ ] All code examples properly formatted
- [ ] All screenshots high-resolution and readable
- [ ] Architecture diagrams clear and professional
- [ ] No placeholder content (all real examples)
- [ ] File saved to `docs/presentations/Azure_HayMaker_Overview.pptx`
- [ ] Presentation opens in PowerPoint without errors

### Rollback Plan

Not applicable - this is a documentation deliverable with no runtime impact.

### Dependencies

- **BLOCKS NOTHING** - this is the final deliverable
- **DEPENDS ON**: ALL other requirements (1-4) must be completed and working

### Success Metrics

- Presentation completeness: 100% (all sections present)
- Real examples: 100% (no mock data)
- Visual quality: Professional (consistent theme, readable)
- Technical accuracy: 100% (all commands work)

### Estimated Effort

6-8 hours (including capture, content creation, generation, and review)

---

# Execution Order and Dependencies

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                        Implementation Flow                       │
└─────────────────────────────────────────────────────────────────┘

Phase 1: Quick Wins (Day 1 Morning - 1 hour)
┌──────────────────────┐
│  Req 1: Service Bus  │ ← NO CODE CHANGES (verification only)
│   Idempotency Test   │
└──────────────────────┘
           ↓
           ↓ (verified working)
           ↓
Phase 2: Security Fix (Day 1 Afternoon - 4-6 hours)
┌──────────────────────┐
│ Req 4: Secret Mgmt   │ ← SECURITY CRITICAL (standardize dev)
│ Key Vault Migration  │
└──────────────────────┘
           ↓
           ↓ (can run in parallel with Phase 3)
           ↓
Phase 3: Agent Features (Day 1-2 - 5-6 hours)
┌──────────────────────┐     ┌──────────────────────┐
│ Req 2: Agent Auto-   │ ──→ │ Req 3: Agent Output  │
│   start (2 hours)    │     │   Display (3-4 hrs)  │
└──────────────────────┘     └──────────────────────┘
           ↓                            ↓
           └────────────────────────────┘
                        ↓
           (ALL requirements working)
                        ↓
Phase 4: Documentation (Day 2-3 - 6-8 hours)
┌──────────────────────┐
│ Req 5: Presentation  │ ← DEPENDS ON ALL ABOVE
│   Creation (6-8 hrs) │
└──────────────────────┘
```

## Parallel Execution Opportunities

**Option 1: Two-Builder Approach**

```
Builder Agent 1:
  ├─→ Req 1: Verification (30 min)
  └─→ Req 2: Autostart (2 hours)
      └─→ Req 3: Output (3 hours)

Builder Agent 2 (parallel):
  └─→ Req 4: Secret Management (4-6 hours)

Builder Agent 3 (sequential):
  └─→ Req 5: Presentation (6-8 hours) [after 1 & 2 complete]
```

**Total Time with Parallelism**: 2-3 days

**Option 2: Sequential (Single Builder)**

```
Day 1:
  Morning:   Req 1 (30 min) + Req 4 (4-6 hours)
  Afternoon: Req 2 (2 hours) + start Req 3 (1 hour)

Day 2:
  Morning:   Complete Req 3 (2-3 hours)
  Afternoon: Start Req 5 (3-4 hours)

Day 3:
  Morning:   Complete Req 5 (3-4 hours)
  Afternoon: Final testing and review
```

**Total Time Sequential**: 3-4 days

## Implementation Checklist

### Pre-Implementation Validation

- [ ] Worktree created: `feat/issue-10-five-critical-improvements`
- [ ] Dev environment deployed and accessible
- [ ] CLI installed and configured
- [ ] Azure credentials valid
- [ ] GitHub repository access confirmed

### Requirement 1: Service Bus (30 min)

- [ ] Trigger deploy-dev workflow manually
- [ ] Verify deployment succeeds
- [ ] Re-trigger workflow
- [ ] Verify second deployment succeeds (idempotency confirmed)
- [ ] Document test results

### Requirement 2: Agent Autostart (2-3 hours)

- [ ] Change line 58: `run_on_startup=True`
- [ ] Add execution conflict check (lines 62-78)
- [ ] Add `AUTO_RUN_ON_STARTUP` to .env.example
- [ ] Update deploy-dev.yml (add env var)
- [ ] Deploy to dev environment
- [ ] Test: Restart Function App → agents start
- [ ] Test: Conflict prevention (recent execution)
- [ ] Unit tests added and passing
- [ ] Integration test confirms end-to-end flow

### Requirement 3: Agent Output (3-4 hours)

- [ ] Add Cosmos DB dual-write to event_bus.py
- [ ] Implement `query_logs_from_cosmosdb()` in agents_api.py
- [ ] Update HTTP endpoint to use Cosmos DB query
- [ ] Verify Cosmos DB logs container in cosmosdb.bicep
- [ ] Enhance CLI formatter (formatters.py)
- [ ] Add follow mode polling to CLI client
- [ ] Deploy to dev environment
- [ ] Test: Query logs via API
- [ ] Test: CLI `haymaker logs --agent-id <id>`
- [ ] Test: CLI `haymaker logs --agent-id <id> --follow`
- [ ] Unit tests added and passing
- [ ] Integration test confirms end-to-end log flow

### Requirement 4: Secret Management (4-6 hours)

- [ ] Verify .env not tracked by git
- [ ] Update deploy-dev.yml: Remove direct injection (lines 183-206)
- [ ] Update deploy-dev.yml: Add Key Vault injection step
- [ ] Update deploy-dev.yml: Add RBAC wait step (60 seconds)
- [ ] Update .env.example: Clarify local vs production
- [ ] Update README.md: Simplify configuration section
- [ ] Deploy to dev environment
- [ ] Test: Verify secrets in Key Vault (not Portal)
- [ ] Test: Function App can read secrets
- [ ] Test: RBAC properly configured
- [ ] Test: Secret rotation works
- [ ] Security validation: No secrets in logs
- [ ] Documentation updated

### Requirement 5: Presentation (6-8 hours)

- [ ] Capture CLI outputs from live system
- [ ] Capture Azure Portal screenshots
- [ ] Source content from documentation
- [ ] Find hay farm image
- [ ] Create slide outline (25-35 slides)
- [ ] Section A: Overview & Architecture (8-12 slides)
- [ ] Section B: Deployment Guide (6-8 slides)
- [ ] Section C: CLI Usage Guide (6-8 slides)
- [ ] Section D: Real Demo (4-6 slides)
- [ ] Generate presentation using PPTX skill
- [ ] Technical review (verify accuracy)
- [ ] Presentation review (check flow)
- [ ] Final polish and proofreading
- [ ] Save to `docs/presentations/Azure_HayMaker_Overview.pptx`

### Post-Implementation

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Security validation complete
- [ ] Documentation updated
- [ ] PR created for review
- [ ] Demo prepared for stakeholder

---

# Risk Mitigation

## High-Risk Items

### Risk 1: Secret Management (Req 4)

**Risk**: RBAC propagation delay causes Function App to fail reading secrets from Key Vault.

**Impact**: HIGH (production outage, deployment failure)

**Likelihood**: MEDIUM (Azure RBAC can take 2-10 minutes to propagate)

**Mitigation Strategy**:
1. Add 60-second wait after RBAC assignment in deploy-dev.yml
2. Add retry logic to Function App startup (3 retries, 30-second intervals)
3. Add verification step to workflow (test Key Vault access before function deploy)
4. Document rollback procedure (revert to direct injection)

**Early Warning Signs**:
- Function App logs show "KeyVault access denied"
- Workflow verification step fails
- Function App fails to start

**Rollback Trigger**:
If Function App cannot access Key Vault after 5 minutes, trigger rollback.

### Risk 2: Presentation Dependencies (Req 5)

**Risk**: Requirements 1-4 not fully working, preventing real examples in presentation.

**Impact**: MEDIUM (incomplete presentation, mock data required)

**Likelihood**: LOW (requirements are well-defined)

**Mitigation Strategy**:
1. Start presentation content outline early (before implementation)
2. Use staging environment as backup for screenshots
3. Prepare mock examples as fallback
4. Schedule presentation creation after confirmed testing

**Early Warning Signs**:
- Requirements 1-4 testing failures
- Agents not executing successfully
- Logs not displaying

**Rollback Trigger**:
If requirements not working by end of Day 2, use mock data and note "future state" in slides.

## Medium-Risk Items

### Risk 3: Agent Autostart Conflicts (Req 2)

**Risk**: Startup execution coincides with scheduled run, causing duplicate agent deployments.

**Impact**: MEDIUM (resource waste, potential quota issues)

**Likelihood**: LOW (5-minute conflict window)

**Mitigation Strategy**:
1. Implement execution conflict check (5-minute lookback)
2. Tag executions with `execution_type` (startup vs scheduled)
3. Add execution locking via Table Storage
4. Make autostart configurable (`AUTO_RUN_ON_STARTUP` flag)

**Early Warning Signs**:
- Multiple orchestrations running simultaneously
- Duplicate resource deployments
- Quota exceeded errors

**Rollback Trigger**:
Set `AUTO_RUN_ON_STARTUP=false` via environment variable.

### Risk 4: Cosmos DB Query Performance (Req 3)

**Risk**: High log volume causes slow query response times in CLI.

**Impact**: LOW (CLI slow, but functional)

**Likelihood**: LOW (7-day TTL limits volume)

**Mitigation Strategy**:
1. Partition by agent_id (efficient queries)
2. Index timestamp, level, run_id
3. Implement pagination (limit 100 logs per query)
4. Add query timeout (5 seconds)

**Early Warning Signs**:
- CLI `haymaker logs` takes > 5 seconds
- Cosmos DB RU consumption high
- Users report slow responses

**Rollback Trigger**:
Revert to placeholder implementation (empty logs).

## Low-Risk Items

### Risk 5: Service Bus Validation (Req 1)

**Risk**: Deployment validation reveals underlying issues beyond idempotency.

**Impact**: LOW (blocks deployments, but workaround exists)

**Likelihood**: VERY LOW (recent fixes resolved validation issues)

**Mitigation Strategy**:
1. Manual workaround: Delete Service Bus subscription before deployment
2. Review validation error messages carefully
3. Check Azure subscription quotas

**Early Warning Signs**:
- Validation step fails in workflow
- Error messages about resource conflicts
- Quota errors

**Rollback Trigger**:
Not applicable - no code changes.

## Risk Matrix

| Requirement | Risk Level | Impact | Likelihood | Mitigation Priority |
|-------------|-----------|--------|------------|-------------------|
| Req 1 (Service Bus) | LOW | Low | Very Low | Low |
| Req 2 (Autostart) | MEDIUM | Medium | Low | Medium |
| Req 3 (Output) | LOW | Low | Low | Low |
| Req 4 (Secret Mgmt) | HIGH | High | Medium | CRITICAL |
| Req 5 (Presentation) | MEDIUM | Medium | Low | Medium |

## Contingency Plans

### Plan A: Full Success (Expected)

All requirements implemented and tested successfully. Presentation includes real examples.

**Timeline**: 2-3 days
**Probability**: 80%

### Plan B: Partial Implementation

Requirements 1-3 complete, Requirement 4 (Secret Management) requires additional debugging time. Presentation uses staging environment examples.

**Timeline**: 3-4 days
**Probability**: 15%

### Plan C: Minimal Viable

Requirements 1-2 complete and working. Requirements 3-4 deferred to future sprint. Presentation uses mock examples with architecture focus.

**Timeline**: 2 days
**Probability**: 5%

**Trigger**: Critical blocker discovered (Azure quota issue, RBAC policy restriction, etc.)

---

# Summary

This implementation specification provides complete, detailed instructions for implementing all 5 critical improvements to Azure HayMaker. Each requirement includes:

- **Architecture design** with component interactions and data flows
- **Specific file changes** with line numbers and exact code
- **Testing procedures** with acceptance criteria
- **Security considerations** with threat mitigation
- **Rollback plans** for each requirement
- **Dependency mapping** showing execution order

**Key Decisions:**

1. **Req 1**: No code changes - verification only (30 min)
2. **Req 2**: One-line change + safeguard (2 hours)
3. **Req 3**: Cosmos DB dual-write pattern (3-4 hours)
4. **Req 4**: Standardize dev to Key Vault (SECURITY CRITICAL - 4-6 hours)
5. **Req 5**: Comprehensive presentation with real examples (6-8 hours)

**Total Effort**: 16-21 hours (2-3 days with parallelism)

**Critical Path**: Req 1 → Req 2 → Req 3 → Req 5
**Parallel Path**: Req 4 (can run alongside Req 2-3)

This specification is ready for autonomous implementation by builder agents.

---

**Document Status**: APPROVED FOR IMPLEMENTATION
**Next Step**: Execute implementation in worktree `feat/issue-10-five-critical-improvements`
