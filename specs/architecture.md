# Azure HayMaker Orchestration Service - Architecture Specification

## Executive Summary

The Azure HayMaker Orchestration Service is a production-ready system that schedules and manages the execution of benign Azure operational scenarios across a target tenant. The service uses Azure Durable Functions for orchestration, Azure Container Apps for isolated agent execution, and Azure Service Bus for event streaming.

This architecture prioritizes security, reliability, and observability while adhering to the Zero-BS Philosophy: every component performs real work, no stubs, no placeholders, no TODOs.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AZURE HAYMAKER ORCHESTRATION                    │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│  Timer Trigger       │  4x daily (US, Asia, ME, EU)
│  (CRON Schedule)     │
└──────────┬───────────┘
           │
           v
┌──────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Durable Function)                        │
│                                                                           │
│  ┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐      │
│  │  1. Validation  │──>│  2. Selection    │──>│  3. Provisioning│      │
│  │  - Credentials  │   │  - Random N      │   │  - Create SPs   │      │
│  │  - Tools        │   │  - Load agents   │   │  - Assign roles │      │
│  │  - APIs         │   │  - Validate      │   │  - Setup bus    │      │
│  └─────────────────┘   └──────────────────┘   └─────────┬───────┘      │
│                                                           │              │
│  ┌─────────────────┐   ┌──────────────────┐            │              │
│  │  6. Cleanup     │<──│  5. Monitoring   │<───────────┘              │
│  │  - Verify done  │   │  - Track logs    │                            │
│  │  - Force delete │   │  - Resource IDs  │                            │
│  │  - Delete SPs   │   │  - Status API    │                            │
│  └─────────────────┘   └──────────────────┘                            │
│                              ^                                           │
│                              │                                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
                               │ (logs/events)
                               │
┌──────────────────────────────┴───────────────────────────────────────────┐
│                        AZURE SERVICE BUS                                  │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  Topic: agent-logs                                              │     │
│  │  - Agent execution logs                                         │     │
│  │  - Resource creation events                                     │     │
│  │  - Status updates                                               │     │
│  │  - Error notifications                                          │     │
│  └────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
                               ^
                               │ (publish logs)
                               │
┌──────────────────────────────┴───────────────────────────────────────────┐
│                    AGENT EXECUTION LAYER                                  │
│                                                                           │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │ Container App 1   │  │ Container App 2   │  │ Container App N   │   │
│  │                   │  │                   │  │                   │   │
│  │ ┌───────────────┐ │  │ ┌───────────────┐ │  │ ┌───────────────┐ │   │
│  │ │ Goal-Seeking  │ │  │ │ Goal-Seeking  │ │  │ │ Goal-Seeking  │ │   │
│  │ │ Agent         │ │  │ │ Agent         │ │  │ │ Agent         │ │   │
│  │ │               │ │  │ │               │ │  │ │               │ │   │
│  │ │ - Scenario    │ │  │ │ - Scenario    │ │  │ │ - Scenario    │ │   │
│  │ │ - SP Creds    │ │  │ │ - SP Creds    │ │  │ │ - SP Creds    │ │   │
│  │ │ - Tools       │ │  │ │ - Tools       │ │  │ │ - Tools       │ │   │
│  │ │   • az cli    │ │  │ │   • az cli    │ │  │ │   • az cli    │ │   │
│  │ │   • terraform │ │  │ │   • terraform │ │  │ │   • terraform │ │   │
│  │ │   • bicep     │ │  │ │   • bicep     │ │  │ │   • bicep     │ │   │
│  │ │ - Anthropic   │ │  │ │ - Anthropic   │ │  │ │ - Anthropic   │ │   │
│  │ └───────────────┘ │  │ └───────────────┘ │  │ └───────────────┘ │   │
│  │                   │  │                   │  │                   │   │
│  │ 64GB RAM, 2 CPU  │  │ 64GB RAM, 2 CPU  │  │ 64GB RAM, 2 CPU  │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
                               │
                               │ (operates on)
                               v
┌──────────────────────────────────────────────────────────────────────────┐
│                          TARGET AZURE TENANT                              │
│                                                                           │
│  Resources created by agents (all tagged: AzureHayMaker-managed)         │
│  - Storage Accounts, VMs, Networks, Databases, etc.                      │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                     SUPPORTING INFRASTRUCTURE                             │
│                                                                           │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐           │
│  │  Key Vault     │  │  Storage       │  │  Container      │           │
│  │  - SP secrets  │  │  - Logs        │  │  Registry       │           │
│  │  - API keys    │  │  - State       │  │  - Agent images │           │
│  │  - Certs       │  │  - Reports     │  │  - Versions     │           │
│  └────────────────┘  └────────────────┘  └─────────────────┘           │
│                                                                           │
│  ┌────────────────┐  ┌────────────────┐                                 │
│  │  App Insights  │  │  Log Analytics │                                 │
│  │  - Metrics     │  │  - Query logs  │                                 │
│  │  - Traces      │  │  - Alerts      │                                 │
│  └────────────────┘  └────────────────┘                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Orchestrator (Azure Durable Functions)

**Technology**: Azure Durable Functions (Python)

**Responsibilities**:
- Schedule management (CRON-triggered, 4x daily)
- Environment validation pre-flight checks
- Scenario selection and agent coordination
- Service principal lifecycle management
- Container Apps deployment and monitoring
- Event bus management and log aggregation
- Cleanup verification and enforcement
- API endpoint for status queries

**Why Durable Functions**:
- Handles long-running workflows (8+ hours) elegantly
- Built-in checkpointing and retry logic
- Fan-out/fan-in pattern for parallel agent execution
- Native Azure integration
- Cost-effective for scheduled workloads

**Key Activities**:

#### Activity: `validate_environment`
- Verifies main service principal credentials
- Tests Azure API connectivity
- Validates Anthropic API access
- Checks Azure CLI, Terraform, Bicep availability
- Returns validation report

#### Activity: `select_scenarios`
- Reads available scenarios from storage/filesystem
- Calculates N based on simulation_size parameter
- Randomly selects N scenarios
- Validates scenario documents are well-formed
- Returns list of (scenario_doc, agent_path) tuples

#### Activity: `create_service_principal`
- Creates SP with naming convention: `AzureHayMaker-{scenario_name}-admin`
- Assigns required roles (User Access Administrator + Contributor)
- Stores credentials in Key Vault
- Returns SP details (client_id, principal_id, secret_reference)

#### Activity: `deploy_container_app`
- Creates Container App with specified scenario agent
- Passes SP credentials via secure environment variables
- Configures resource limits (64GB RAM, 2 CPU minimum)
- Sets environment variables (ANTHROPIC_API_KEY, SERVICE_BUS_CONNECTION, etc.)
- Returns Container App details (name, resource_id, endpoints)

#### Activity: `monitor_execution`
- Subscribes to Service Bus topic for agent logs
- Aggregates log messages to Storage Account
- Extracts resource IDs from log messages
- Tracks agent status (running, completed, failed, cleanup_done)
- Updates execution state

#### Activity: `verify_cleanup`
- Queries Azure Resource Graph for resources with tag `AzureHayMaker-managed`
- Cross-references with expected resources from logs
- Identifies resources that should have been cleaned up
- Returns cleanup verification report

#### Activity: `force_cleanup`
- Deletes remaining tagged resources
- Retries deletion for resources with dependencies
- Deletes service principals
- Logs all forced deletion actions
- Returns final cleanup status

#### Orchestration Function: `orchestrate_haymaker_run`
- Executes validation activity
- Executes selection activity
- Fan-out: Creates SPs in parallel
- Fan-out: Deploys Container Apps in parallel
- Wait: 8 hours with periodic monitoring
- Executes cleanup verification
- Executes forced cleanup if needed
- Generates execution summary report

### 2. Container Apps (Agent Runtime)

**Technology**: Azure Container Apps

**Image Base**: Custom Docker image with:
- Python 3.11+ runtime
- Azure CLI (latest stable)
- Terraform (latest stable)
- Azure Bicep CLI
- Anthropic Python SDK
- Azure Service Bus SDK
- Azure Identity SDK

**Configuration**:
- CPU: 2 cores minimum
- Memory: 64GB minimum
- Timeout: 10 hours (allows 8 hours + buffer)
- Restart policy: Never (one-time execution)
- Scale: Manual (1 replica per scenario)

**Environment Variables** (injected at runtime):
```
AZURE_TENANT_ID=<target_tenant_id>
AZURE_CLIENT_ID=<scenario_sp_client_id>
AZURE_CLIENT_SECRET=<from_key_vault>
AZURE_SUBSCRIPTION_ID=<target_subscription_id>
ANTHROPIC_API_KEY=<from_key_vault>
SERVICE_BUS_CONNECTION_STRING=<from_key_vault>
SERVICE_BUS_TOPIC=agent-logs
SCENARIO_NAME=<scenario_identifier>
RUN_ID=<unique_execution_id>
LOG_LEVEL=INFO
```

**Security**:
- Managed Identity for Key Vault access
- Secrets mounted as environment variables (not in image)
- No privileged mode
- Network isolation (VNet injection optional)
- Credential scrubbing in stdout/stderr

**Agent Execution Flow**:
1. Agent starts, reads scenario from embedded instructions
2. Authenticates to Azure using SP credentials
3. Publishes "started" event to Service Bus
4. Executes Phase 1: Deployment
5. Publishes resource creation events
6. Executes Phase 2: Operations (loops for 8 hours)
7. Publishes operational events periodically
8. Executes Phase 3: Cleanup
9. Publishes "cleanup_complete" event
10. Agent exits

### 3. Event Bus (Azure Service Bus)

**Technology**: Azure Service Bus (Standard or Premium tier)

**Topology**:
- **Topic**: `agent-logs`
  - Subscription: `orchestrator-monitoring` (used by orchestrator)
  - Subscription: `archival` (auto-forwards to Storage)
  - Max delivery count: 10
  - Lock duration: 5 minutes
  - TTL: 7 days

**Message Schema**:
```json
{
  "event_type": "agent_started|resource_created|operation|cleanup_complete|error",
  "timestamp": "2025-11-14T12:00:00Z",
  "scenario_name": "ai-ml-01-cognitive-services-vision",
  "run_id": "uuid",
  "agent_id": "container_app_name",
  "sp_name": "AzureHayMaker-vision-admin",
  "message": "Resource group created",
  "resource_id": "/subscriptions/.../resourceGroups/...",
  "resource_type": "Microsoft.Resources/resourceGroups",
  "tags": {"AzureHayMaker-managed": "true"},
  "severity": "info|warning|error",
  "details": {...}
}
```

**Message Types**:

1. **agent_started**: Agent initialization complete
2. **resource_created**: Azure resource provisioned
3. **operation**: Benign management operation performed
4. **cleanup_complete**: Agent finished cleanup phase
5. **error**: Agent encountered an error

**Guarantees**:
- At-least-once delivery
- Dead-letter queue for failed messages
- Session-based ordering (per agent)

### 4. Configuration and Secrets (Azure Key Vault)

**Technology**: Azure Key Vault (Standard tier)

**Secrets Stored**:
- `main-sp-client-id`: Main orchestrator service principal client ID
- `main-sp-client-secret`: Main orchestrator service principal secret
- `anthropic-api-key`: Anthropic API key
- `service-bus-connection-string`: Service Bus connection string
- `target-tenant-id`: Target Azure tenant ID
- `target-subscription-id`: Target Azure subscription ID
- `scenario-sp-{scenario_name}-secret`: Each scenario SP secret (ephemeral)

**Access Control**:
- Orchestrator Function: Get/List secrets (Managed Identity)
- Container Apps: Get secrets (Managed Identity, specific secret only)
- No human access during runtime (break-glass via RBAC for debugging)

**Rotation**:
- Main SP secret: Manual rotation, update Key Vault
- Anthropic API key: Manual rotation, update Key Vault
- Scenario SP secrets: Deleted after cleanup (ephemeral)

**Audit**:
- All secret access logged to Log Analytics
- Alerts on unusual access patterns

### 5. State Management (Azure Storage Account)

**Technology**: Azure Storage Account (Standard, LRS)

**Containers**:

#### `execution-logs`
- Stores aggregated log messages from Service Bus
- Format: JSON Lines (one JSON object per line)
- Path: `{run_id}/{scenario_name}/logs.jsonl`
- Retention: 90 days

#### `execution-state`
- Stores orchestrator state checkpoints
- Format: JSON
- Path: `{run_id}/state.json`
- Updated during orchestration phases

#### `execution-reports`
- Stores final execution summary reports
- Format: JSON
- Path: `{run_id}/report.json`
- Includes:
  - Selected scenarios
  - Created SPs
  - Deployed resources (with IDs)
  - Cleanup status
  - Errors encountered

#### `scenarios`
- Stores scenario documents (synced from repo)
- Format: Markdown
- Path: `{scenario_name}.md`

### 6. Container Registry (Azure Container Registry)

**Technology**: Azure Container Registry (Standard tier)

**Repositories**:

#### `haymaker-agent`
- Base agent runtime image
- Tags: `latest`, `{version}`, `{git_commit_sha}`
- Includes all required tools

**Build Pipeline**:
1. Dockerfile in repo at `/docker/agent/Dockerfile`
2. Build triggered on commit to main (GitHub Actions)
3. Push to ACR with tags
4. Scan for vulnerabilities (Microsoft Defender for Containers)

**Dockerfile Specification**:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Install Terraform
RUN wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && apt-get install -y terraform

# Install Bicep
RUN az bicep install

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent framework
COPY src/agents/common/ /app/common/
COPY src/agents/run_agent.py /app/

# Set entrypoint
ENTRYPOINT ["python", "/app/run_agent.py"]
```

### 7. Monitoring and Observability

**Technology**: Azure Application Insights + Log Analytics

**Metrics Collected**:

#### Orchestrator Metrics
- Execution start/end times
- Scenario selection count
- SP creation success/failure
- Container App deployment success/failure
- Cleanup verification results
- API endpoint response times

#### Agent Metrics
- Agent execution duration
- Resources created per agent
- Operations performed per agent
- Errors encountered per agent
- Cleanup success rate

**Alerts**:

1. **Critical**:
   - Orchestrator execution failure
   - Cleanup verification failure (resources remaining)
   - SP creation failure
   - Key Vault access denied

2. **Warning**:
   - Agent execution timeout
   - Service Bus message dead-letter
   - Container App deployment failure
   - API rate limiting

3. **Informational**:
   - Orchestrator execution start
   - Orchestrator execution complete
   - Cleanup successful

**Dashboards**:
- Real-time execution status
- Historical execution trends
- Resource utilization
- Cost tracking per execution

### 8. API Endpoint (HTTP-triggered Function)

**Technology**: Azure Functions HTTP Trigger

**Endpoints**:

#### `GET /api/status`
Returns overall orchestrator status
```json
{
  "status": "running|idle|error",
  "current_run_id": "uuid",
  "started_at": "2025-11-14T12:00:00Z",
  "scheduled_end_at": "2025-11-14T20:00:00Z"
}
```

#### `GET /api/runs`
Returns list of recent executions
```json
{
  "runs": [
    {
      "run_id": "uuid",
      "started_at": "2025-11-14T12:00:00Z",
      "ended_at": "2025-11-14T20:05:00Z",
      "status": "completed|in_progress|failed",
      "scenarios_count": 5,
      "resources_created": 127,
      "cleanup_status": "verified|partial|failed"
    }
  ]
}
```

#### `GET /api/runs/{run_id}`
Returns detailed execution information
```json
{
  "run_id": "uuid",
  "started_at": "2025-11-14T12:00:00Z",
  "ended_at": "2025-11-14T20:05:00Z",
  "status": "completed",
  "scenarios": [
    {
      "scenario_name": "ai-ml-01-cognitive-services-vision",
      "agent_id": "container-app-vision-uuid",
      "sp_name": "AzureHayMaker-vision-admin",
      "status": "completed",
      "resources_created": 25,
      "cleanup_status": "verified"
    }
  ],
  "total_resources": 127,
  "cleanup_verification": {
    "expected_deleted": 127,
    "actually_deleted": 127,
    "forced_deletions": 0
  }
}
```

#### `GET /api/runs/{run_id}/resources`
Returns list of all resources created in a run
```json
{
  "run_id": "uuid",
  "resources": [
    {
      "resource_id": "/subscriptions/.../resourceGroups/...",
      "resource_type": "Microsoft.Resources/resourceGroups",
      "scenario_name": "ai-ml-01-cognitive-services-vision",
      "created_at": "2025-11-14T12:05:00Z",
      "deleted_at": "2025-11-14T20:02:00Z",
      "status": "deleted|exists",
      "tags": {"AzureHayMaker-managed": "true"}
    }
  ]
}
```

#### `GET /api/runs/{run_id}/service-principals`
Returns list of service principals created in a run
```json
{
  "run_id": "uuid",
  "service_principals": [
    {
      "sp_name": "AzureHayMaker-vision-admin",
      "sp_id": "uuid",
      "scenario_name": "ai-ml-01-cognitive-services-vision",
      "created_at": "2025-11-14T12:01:00Z",
      "deleted_at": "2025-11-14T20:03:00Z",
      "status": "deleted|exists"
    }
  ]
}
```

#### `GET /api/runs/{run_id}/logs`
Returns aggregated logs for a run (paginated)
```json
{
  "run_id": "uuid",
  "page": 1,
  "page_size": 100,
  "total": 15234,
  "logs": [
    {
      "timestamp": "2025-11-14T12:05:23Z",
      "scenario_name": "ai-ml-01-cognitive-services-vision",
      "event_type": "resource_created",
      "message": "Resource group created",
      "severity": "info"
    }
  ]
}
```

**Authentication**:
- Azure AD authentication required
- API key as fallback (stored in Key Vault)
- RBAC: Reader role minimum

---

## Data Flow Diagrams

### 1. Orchestration Execution Flow

```
Timer Trigger (CRON)
  │
  v
┌────────────────────────────────────────────────┐
│ Orchestrator Start                             │
│ - Generate run_id                              │
│ - Load configuration from Key Vault            │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Validation Phase                               │
│ - Test Azure credentials                       │
│ - Test Anthropic API                           │
│ - Verify tools available in agent image        │
│ - Check quotas                                 │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Selection Phase                                │
│ - Load scenarios from Storage                  │
│ - Calculate N from simulation_size             │
│ - Randomly select N scenarios                  │
│ - Validate scenario documents                  │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Provisioning Phase (parallel)                  │
│ - For each scenario:                           │
│   - Create SP                                  │
│   - Assign roles (wait for propagation)        │
│   - Store secret in Key Vault                  │
│   - Deploy Container App                       │
│   - Pass credentials securely                  │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Monitoring Phase (8 hours)                     │
│ - Subscribe to Service Bus                     │
│ - Aggregate logs to Storage                    │
│ - Track resource creation events               │
│ - Monitor agent status                         │
│ - Update execution state                       │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Cleanup Verification Phase                     │
│ - Check all agents reported cleanup_complete   │
│ - Query Azure for tagged resources             │
│ - Compare expected vs actual                   │
│ - Identify resources to force-delete           │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Forced Cleanup Phase                           │
│ - Delete remaining resources                   │
│ - Delete all scenario SPs                      │
│ - Verify all deletions                         │
│ - Log cleanup actions                          │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Report Generation                              │
│ - Aggregate execution metrics                  │
│ - Generate summary report                      │
│ - Store report to Storage                      │
│ - Send completion notification                 │
└────────────────────────────────────────────────┘
```

### 2. Agent Execution Flow

```
Container App Start
  │
  v
┌────────────────────────────────────────────────┐
│ Agent Initialization                           │
│ - Load scenario instructions                   │
│ - Read environment variables                   │
│ - Authenticate to Azure (SP)                   │
│ - Connect to Service Bus                       │
│ - Publish "agent_started" event                │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Phase 1: Deployment                            │
│ - Execute deployment commands                  │
│ - Create resources (tag all)                   │
│ - Publish "resource_created" events            │
│ - Validate deployment success                  │
│ - Store resource IDs locally                   │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Phase 2: Operations (loop for 8 hours)        │
│ - Execute management commands                  │
│ - Perform benign operations                    │
│ - Publish "operation" events                   │
│ - Monitor resource health                      │
│ - Sleep between operations                     │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Phase 3: Cleanup                               │
│ - Execute cleanup commands                     │
│ - Delete all created resources                 │
│ - Verify deletions                             │
│ - Publish "cleanup_complete" event             │
└────────────┬───────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────┐
│ Agent Termination                              │
│ - Close connections                            │
│ - Exit successfully (code 0)                   │
└────────────────────────────────────────────────┘

[Error at any phase]
  │
  v
┌────────────────────────────────────────────────┐
│ Error Handling                                 │
│ - Publish "error" event                        │
│ - Attempt cleanup (best effort)                │
│ - Exit with error code                         │
└────────────────────────────────────────────────┘
```

### 3. Event Flow

```
Agent Container
  │
  │ (publishes events)
  v
Azure Service Bus Topic: "agent-logs"
  │
  ├──> Subscription: "orchestrator-monitoring"
  │      │
  │      │ (pulled by orchestrator)
  │      v
  │    Orchestrator Function
  │      │
  │      │ (processes events)
  │      │ (updates execution state)
  │      │ (extracts resource IDs)
  │      │
  │      v
  │    Storage Account: "execution-logs"
  │      │
  │      │ (stored as JSON Lines)
  │      v
  │    Log Analytics
  │      │
  │      │ (queryable)
  │      v
  │    API Endpoint
  │
  └──> Subscription: "archival"
         │
         │ (auto-forwards)
         v
       Storage Account: "execution-logs"
         │
         │ (long-term retention)
         v
       [Archived]
```

---

## Security Model

### 1. Identity and Access Management

#### Main Service Principal
**Name**: `AzureHayMaker-Orchestrator`

**Roles Required** (on target subscription):
- **Owner**: Required to create SPs and assign roles
- Alternative: **User Access Administrator** + **Contributor**

**Justification**:
- Must create service principals (requires Microsoft.Authorization/roleAssignments/write)
- Must assign roles to created SPs
- Must create/delete resources
- Must query resources across subscription

**Managed Identity** (for Orchestrator Function):
- Assigned same roles as main SP
- Used for Azure API operations
- No credentials stored in code

#### Scenario Service Principals
**Naming Convention**: `AzureHayMaker-{scenario_name}-admin`

**Roles Required** (on target subscription):
- **User Access Administrator**: To assign roles (if scenario requires)
- **Contributor**: To create/delete resources

**Lifecycle**:
1. Created at provisioning phase
2. Secret stored in Key Vault (ephemeral)
3. Assigned to target subscription
4. Wait 60 seconds for role propagation
5. Used by single Container App
6. Deleted after cleanup verification

**Security Properties**:
- Ephemeral (exists only during execution)
- Single-purpose (one scenario only)
- Audited (all actions logged)
- Isolated (no cross-scenario access)

### 2. Credential Protection

#### Secrets Never Logged
**Implementation**:
- Orchestrator scrubs credentials from logs using regex patterns
- Container Apps use environment variable filtering (Azure Container Apps feature)
- Service Bus messages never contain credentials
- Application Insights configured to redact secrets

**Patterns to Scrub**:
```python
SECRET_PATTERNS = [
    r'client_secret=[\w-]+',
    r'password=[\w-]+',
    r'"secret":\s*"[^"]+"',
    r'AZURE_CLIENT_SECRET=[\w-]+',
    r'ANTHROPIC_API_KEY=sk-ant-[\w-]+'
]
```

#### Key Vault Access Control
**RBAC Assignments**:
- Orchestrator Function Managed Identity: "Key Vault Secrets Officer"
- Container App Managed Identity (per scenario): "Key Vault Secrets User" (specific secrets only)
- Humans: "Key Vault Reader" (emergency break-glass only)

**Secrets Policy**:
- All secrets have expiration dates (except ephemeral SP secrets)
- Access logging enabled
- Purge protection enabled
- Soft delete enabled (90 days)

#### Environment Variable Security
**Container Apps**:
- Secrets passed as secure environment variables (not in image)
- Azure manages encryption at rest
- No secrets in Container App definition (only references)

**Example Configuration**:
```json
{
  "secrets": [
    {
      "name": "azure-client-secret",
      "keyVaultUrl": "https://haymaker-kv.vault.azure.net/secrets/scenario-sp-vision-secret"
    }
  ],
  "env": [
    {
      "name": "AZURE_CLIENT_SECRET",
      "secretRef": "azure-client-secret"
    }
  ]
}
```

### 3. Network Security

#### Orchestrator Function
- **Ingress**: HTTPS only (API endpoint)
- **Egress**: Azure services (Key Vault, Service Bus, Container Apps)
- **VNet Integration**: Optional (recommended for production)
- **Private Endpoints**: Key Vault, Storage, Service Bus (optional)

#### Container Apps
- **Ingress**: None (agents don't expose endpoints)
- **Egress**: Azure APIs, Anthropic API
- **VNet Integration**: Optional
- **Network Policies**: Block unnecessary outbound (configurable)

#### Service Bus
- **Ingress**: Azure services only
- **TLS**: Required (1.2+)
- **Shared Access Signatures**: No (Managed Identity only)

### 4. Least Privilege Principle

#### Orchestrator Permissions
- Can create SPs (minimum: Microsoft.Authorization/roleAssignments/write)
- Can assign specific roles (User Access Administrator, Contributor)
- Can query resources (Reader on subscription)
- Can delete resources (Contributor)
- Cannot: Modify subscriptions, delete subscription, assign Owner role

#### Scenario SP Permissions
- Can create resources in assigned subscription only
- Can assign roles if scenario requires (limited scope)
- Cannot: Create other SPs, access other scenarios' resources, modify RBAC outside scope

#### Container App Permissions
- Can read own secrets from Key Vault
- Can publish to Service Bus topic
- Cannot: Read other scenarios' secrets, modify Key Vault, delete Service Bus

### 5. Audit Logging

**Azure Activity Log**:
- All SP creation/deletion logged
- All role assignments logged
- All resource creation/deletion logged
- Retention: 90 days → forward to Log Analytics (2 years)

**Key Vault Audit Log**:
- All secret access logged
- Retention: 90 days → forward to Log Analytics (2 years)

**Service Bus Audit Log**:
- Message send/receive counts
- Dead-letter events
- Retention: 7 days

**Custom Audit Log** (Application Insights):
- Orchestrator decision points
- Scenario selection
- Cleanup actions
- Forced deletions

---

## Deployment Model

### 1. Infrastructure Deployment

**Method**: Bicep templates (Infrastructure as Code)

**Deployment Order**:
1. Resource Group
2. Key Vault
3. Storage Account
4. Container Registry
5. Service Bus
6. Application Insights
7. Log Analytics Workspace
8. Function App (Orchestrator)
9. Container App Environment

**Bicep Modules**:

#### `main.bicep`
```bicep
// Main orchestration template
param location string = resourceGroup().location
param projectName string = 'azurehaymaker'
param environment string = 'prod'

// Deploy all modules
module keyVault 'modules/keyvault.bicep' = { ... }
module storage 'modules/storage.bicep' = { ... }
module serviceBus 'modules/servicebus.bicep' = { ... }
module containerRegistry 'modules/acr.bicep' = { ... }
module monitoring 'modules/monitoring.bicep' = { ... }
module orchestrator 'modules/function.bicep' = { ... }
module containerEnv 'modules/containerenv.bicep' = { ... }
```

#### `modules/keyvault.bicep`
```bicep
// Key Vault configuration
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${projectName}-kv-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    networkAcls: {
      defaultAction: 'Allow'  // Change to 'Deny' with VNet integration
      bypass: 'AzureServices'
    }
  }
}
```

#### `modules/servicebus.bicep`
```bicep
// Service Bus configuration
resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: '${projectName}-sb-${uniqueString(resourceGroup().id)}'
  location: location
  sku: { name: 'Standard', tier: 'Standard' }

  resource topic 'topics' = {
    name: 'agent-logs'
    properties: {
      enablePartitioning: true
      defaultMessageTimeToLive: 'P7D'
      maxSizeInMegabytes: 5120
    }

    resource orchestratorSubscription 'subscriptions' = {
      name: 'orchestrator-monitoring'
      properties: {
        lockDuration: 'PT5M'
        maxDeliveryCount: 10
        deadLetteringOnMessageExpiration: true
      }
    }

    resource archivalSubscription 'subscriptions' = {
      name: 'archival'
      properties: {
        lockDuration: 'PT1M'
        maxDeliveryCount: 10
        deadLetteringOnMessageExpiration: true
      }
    }
  }
}
```

### 2. Application Deployment

**Method**: CI/CD pipeline (GitHub Actions)

**Pipeline Stages**:

1. **Build**:
   - Lint code (ruff)
   - Type check (pyright)
   - Run unit tests (pytest)
   - Build Docker image
   - Scan image for vulnerabilities

2. **Push**:
   - Push image to ACR
   - Tag with version and commit SHA

3. **Deploy**:
   - Update Function App code
   - Update environment variables
   - Restart Function App

**GitHub Actions Workflow** (`.github/workflows/deploy.yml`):
```yaml
name: Deploy Orchestrator

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Lint
        run: uv run ruff check .
      - name: Type check
        run: uv run pyright
      - name: Test
        run: uv run pytest --cov --cov-report=term

  build-image:
    needs: build-and-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Login to ACR
        uses: azure/docker-login@v1
        with:
          login-server: ${{ secrets.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      - name: Build and push
        run: |
          docker build -t ${{ secrets.ACR_LOGIN_SERVER }}/haymaker-agent:${{ github.sha }} -f docker/agent/Dockerfile .
          docker push ${{ secrets.ACR_LOGIN_SERVER }}/haymaker-agent:${{ github.sha }}
          docker tag ${{ secrets.ACR_LOGIN_SERVER }}/haymaker-agent:${{ github.sha }} ${{ secrets.ACR_LOGIN_SERVER }}/haymaker-agent:latest
          docker push ${{ secrets.ACR_LOGIN_SERVER }}/haymaker-agent:latest

  deploy:
    needs: build-image
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - name: Deploy Function App
        run: |
          az functionapp deployment source config-zip \
            --resource-group azurehaymaker-orchestrator-rg \
            --name azurehaymaker-orchestrator-func \
            --src function-app.zip
```

### 3. Configuration Management

**Configuration Sources**:

1. **Bicep Parameters** (deployment time):
   - Project name
   - Location
   - Environment (dev/prod)

2. **Key Vault Secrets** (runtime):
   - Service principal credentials
   - Anthropic API key
   - Target tenant/subscription IDs

3. **Function App Settings** (runtime):
   - `SIMULATION_SIZE`: small|medium|large
   - `SCHEDULE_CRON`: "0 0 */6 * * *" (4x daily)
   - `KEY_VAULT_URL`: https://haymaker-kv.vault.azure.net
   - `SERVICE_BUS_NAMESPACE`: haymaker-sb.servicebus.windows.net
   - `CONTAINER_REGISTRY`: haymaker.azurecr.io
   - `CONTAINER_IMAGE`: haymaker-agent:latest
   - `STORAGE_ACCOUNT`: haymakerst.blob.core.windows.net
   - `LOG_LEVEL`: INFO

4. **Environment-Specific** (per deployment):
   - Development: Small simulation size, 1x daily
   - Production: Configurable simulation size, 4x daily

### 4. Scaling Configuration

**Orchestrator Function**:
- **Consumption Plan**: Default (cost-effective for scheduled execution)
- **Max instances**: 1 (orchestration is single-threaded by design)
- **Timeout**: 230 seconds per activity (Durable Functions extends overall)

**Container Apps Environment**:
- **Max replicas per scenario**: 1 (one agent per scenario)
- **Max total replicas**: 50 (supports up to 50 concurrent scenarios)
- **Resource limits**: 64GB RAM, 2 CPU per replica
- **Scale rules**: Manual (no autoscaling, agents are one-time jobs)

**Service Bus**:
- **Standard tier**: 1,000 message operations/sec (sufficient)
- **Upgrade to Premium**: If > 25 concurrent scenarios (higher throughput)

---

## Error Handling Strategy

### 1. Error Categories

#### Transient Errors
**Examples**:
- Azure API rate limiting
- Network timeouts
- Temporary service unavailability

**Strategy**:
- Retry with exponential backoff
- Max retries: 5
- Backoff: 2^retry_count seconds (capped at 60s)

**Implementation**:
```python
from azure.core.exceptions import HttpResponseError
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type(HttpResponseError)
)
def azure_api_call(...):
    ...
```

#### Fatal Errors
**Examples**:
- Invalid credentials
- Insufficient permissions
- Configuration errors
- Quota exceeded

**Strategy**:
- Fail fast
- Log detailed error
- Notify operations team
- Don't retry

**Implementation**:
```python
class FatalError(Exception):
    """Non-retryable error"""
    pass

def validate_credentials():
    try:
        # Test credentials
        ...
    except AuthenticationError as e:
        raise FatalError(f"Invalid credentials: {e}")
```

#### Agent Errors
**Examples**:
- Scenario execution failure
- Resource creation failure
- Cleanup failure

**Strategy**:
- Continue other agents (isolation)
- Log error details
- Attempt cleanup anyway
- Mark scenario as failed
- Include in execution report

**Implementation**:
```python
# In orchestrator
for scenario in selected_scenarios:
    try:
        await deploy_and_run_agent(scenario)
    except AgentError as e:
        log.error(f"Agent {scenario.name} failed: {e}")
        failed_scenarios.append(scenario)
        # Continue with other scenarios
        continue
```

### 2. Cleanup Error Handling

#### Cleanup Failure Modes

**Mode 1: Agent reports cleanup failure**
- Agent publishes error event
- Orchestrator marks scenario for forced cleanup
- Forced cleanup attempted during cleanup phase

**Mode 2: Agent never completes cleanup**
- 8-hour timeout expires
- Orchestrator marks scenario as timed out
- Forced cleanup attempted during cleanup phase

**Mode 3: Resources remain after agent cleanup**
- Cleanup verification detects remaining resources
- Forced cleanup attempted during cleanup phase

#### Forced Cleanup Process

```python
async def force_cleanup_scenario(scenario_name: str, run_id: str) -> CleanupReport:
    """Force delete all resources for a scenario"""

    # Query resources by tag
    resources = await azure_client.query_resources(
        query=f"Resources | where tags['AzureHayMaker-managed'] == 'true' and tags['RunId'] == '{run_id}' and tags['Scenario'] == '{scenario_name}'"
    )

    # Sort by dependency order (delete children first)
    sorted_resources = sort_by_dependency(resources)

    # Delete each resource
    deletion_report = []
    for resource in sorted_resources:
        try:
            await azure_client.delete_resource(resource.id, wait=True)
            deletion_report.append({
                "resource_id": resource.id,
                "status": "deleted",
                "attempts": 1
            })
        except ResourceDependencyError:
            # Retry after delay (dependencies may still be deleting)
            await asyncio.sleep(30)
            try:
                await azure_client.delete_resource(resource.id, wait=True)
                deletion_report.append({
                    "resource_id": resource.id,
                    "status": "deleted",
                    "attempts": 2
                })
            except Exception as e:
                deletion_report.append({
                    "resource_id": resource.id,
                    "status": "failed",
                    "error": str(e)
                })

    # Delete scenario SP
    await delete_service_principal(f"AzureHayMaker-{scenario_name}-admin")

    return CleanupReport(deletions=deletion_report)
```

#### Cleanup Guarantees

**Best Effort**:
- System attempts to delete all resources
- Retries with increasing delays
- Logs all deletion attempts

**Alerting**:
- If any resource cannot be deleted after retries, alert operations team
- Include resource details and error in alert

**Cost Protection**:
- Failed deletions are flagged in execution report
- Daily job queries for orphaned resources
- Automated cleanup job runs daily to catch any missed resources

### 3. Rollback Strategies

#### SP Creation Failure
**Rollback**:
- Delete any SPs created before failure
- Delete secrets from Key Vault
- Abort execution

#### Container App Deployment Failure
**Rollback**:
- Delete deployed Container Apps
- Delete SPs for failed scenarios
- Continue with successfully deployed scenarios (partial execution)

#### Monitoring Failure
**Behavior**:
- Agents continue execution (decoupled)
- Orchestrator logs warning
- Cleanup verification still runs (queries Azure directly)

---

## Technology Choices with Justification

### 1. Azure Durable Functions vs. Alternatives

**Choice**: Azure Durable Functions

**Alternatives Considered**:
- Azure Container Apps Jobs
- Azure Kubernetes Service (CronJobs)
- Azure Logic Apps

**Justification**:
| Criteria | Durable Functions | Container Apps Jobs | AKS | Logic Apps |
|----------|-------------------|---------------------|-----|------------|
| Long-running support | Excellent (checkpointing) | Good | Excellent | Limited (1 hour) |
| Complexity | Low | Medium | High | Low |
| Cost (4x daily) | Low | Medium | High | Medium |
| Azure integration | Excellent | Good | Good | Excellent |
| Debugging | Good | Medium | Medium | Good |
| **Score** | **9/10** | 7/10 | 6/10 | 5/10 |

**Winner**: Durable Functions provide the best balance of simplicity, cost, and long-running orchestration capabilities.

### 2. Azure Service Bus vs. Alternatives

**Choice**: Azure Service Bus (Standard tier)

**Alternatives Considered**:
- Azure Event Hubs
- Azure Event Grid
- Azure Storage Queues

**Justification**:
| Criteria | Service Bus | Event Hubs | Event Grid | Storage Queues |
|----------|-------------|------------|------------|----------------|
| Guaranteed delivery | Yes | Yes | Yes | Yes |
| Dead-letter queue | Yes | No | Yes | Yes |
| Topics/Subscriptions | Yes | Yes (partitions) | Yes | No |
| Message filtering | Yes | No | Yes | No |
| Max message size | 256KB | 1MB | 64KB | 64KB |
| Complexity | Low | Medium | Low | Very Low |
| Cost (1M messages) | Low | Very Low | Very Low | Very Low |
| **Score** | **9/10** | 6/10 | 7/10 | 5/10 |

**Winner**: Service Bus provides the best feature set for reliable event streaming with dead-letter queues and topic subscriptions.

### 3. Container Apps vs. Alternatives

**Choice**: Azure Container Apps

**Alternatives Considered**:
- Azure Container Instances
- Azure Kubernetes Service
- Azure Batch

**Justification**:
| Criteria | Container Apps | ACI | AKS | Azure Batch |
|----------|----------------|-----|-----|-------------|
| Managed | Yes | Yes | Partial | Yes |
| Scaling | Automatic | Manual | Automatic | Automatic |
| Environment isolation | Excellent | Good | Excellent | Good |
| Secrets management | Excellent | Good | Excellent | Medium |
| Cost (64GB, 8hr) | Medium | Medium | Medium-High | Low-Medium |
| Complexity | Low | Very Low | High | Medium |
| **Score** | **9/10** | 7/10 | 7/10 | 6/10 |

**Winner**: Container Apps provide the best balance of managed services, isolation, and secrets management.

### 4. Python vs. Alternatives

**Choice**: Python

**Alternatives Considered**:
- C# (.NET)
- TypeScript (Node.js)

**Justification**:
| Criteria | Python | C# | TypeScript |
|----------|--------|----|-----------|
| Azure SDK maturity | Excellent | Excellent | Good |
| Anthropic SDK | Excellent | None | Good |
| Learning curve | Low | Medium | Low |
| Agent ecosystem | Excellent | Medium | Good |
| Type safety | Good (pyright) | Excellent | Excellent |
| Async support | Excellent | Excellent | Excellent |
| **Score** | **9/10** | 7/10 | 8/10 |

**Winner**: Python has the best ecosystem for AI agents and Azure automation, with excellent SDKs for both Azure and Anthropic.

### 5. Bicep vs. Alternatives

**Choice**: Bicep

**Alternatives Considered**:
- Terraform
- ARM Templates
- Azure CLI scripts

**Justification**:
| Criteria | Bicep | Terraform | ARM Templates | CLI Scripts |
|----------|-------|-----------|---------------|-------------|
| Azure-native | Yes | No | Yes | Yes |
| Readability | Excellent | Good | Poor | Good |
| Type checking | Yes | Yes | Limited | No |
| State management | Azure | External | Azure | Manual |
| Modularity | Excellent | Excellent | Good | Poor |
| Community | Growing | Large | Medium | N/A |
| **Score** | **9/10** | 8/10 | 5/10 | 4/10 |

**Winner**: Bicep provides the best Azure-native IaC experience with excellent readability and no external state management.

---

## Module Specifications for Implementation

### Module 1: Configuration Manager

**File**: `src/orchestrator/config.py`

**Purpose**: Load, validate, and provide type-safe access to configuration from Key Vault and environment variables.

**Contract**:
- **Inputs**: None (reads from environment and Key Vault)
- **Outputs**: `OrchestratorConfig` dataclass
- **Side Effects**: Reads from Key Vault, validates credentials

**Dependencies**:
- `azure-identity`
- `azure-keyvault-secrets`
- `pydantic` (validation)

**Implementation Notes**:
- Use Pydantic for validation
- No default values for secrets
- Fail fast on missing required config
- Cache config after validation

**Test Requirements**:
- Test with missing required fields (should raise error)
- Test with invalid credentials (should raise error)
- Test with valid config (should return config)
- Mock Key Vault SDK

**Example Interface**:
```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class OrchestratorConfig:
    target_tenant_id: str
    target_subscription_id: str
    main_sp_client_id: str
    main_sp_client_secret: str
    anthropic_api_key: str
    service_bus_namespace: str
    container_registry: str
    container_image: str
    storage_account: str
    key_vault_url: str
    simulation_size: Literal["small", "medium", "large"]

    def get_simulation_count(self) -> int:
        """Map simulation size to scenario count"""
        return {"small": 5, "medium": 15, "large": 30}[self.simulation_size]

async def load_config() -> OrchestratorConfig:
    """Load and validate configuration from Key Vault and environment"""
    ...
```

---

### Module 2: Environment Validator

**File**: `src/orchestrator/validation.py`

**Purpose**: Perform pre-flight validation of credentials, APIs, and tools.

**Contract**:
- **Inputs**: `OrchestratorConfig`
- **Outputs**: `ValidationReport` dataclass
- **Side Effects**: Makes test API calls to Azure and Anthropic

**Dependencies**:
- `azure-identity`
- `azure-mgmt-resource`
- `anthropic`

**Implementation Notes**:
- Test Azure credentials with simple API call (list resource groups)
- Test Anthropic API with simple prompt
- Check container image exists in registry
- All validations must be real checks (no stubs)

**Test Requirements**:
- Test with invalid Azure credentials (should fail)
- Test with invalid Anthropic key (should fail)
- Test with missing container image (should fail)
- Test with valid config (should pass)
- Mock Azure and Anthropic APIs

**Example Interface**:
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ValidationResult:
    check_name: str
    passed: bool
    error: Optional[str] = None
    details: Optional[dict] = None

@dataclass
class ValidationReport:
    overall_passed: bool
    results: List[ValidationResult]

    def get_failed_checks(self) -> List[ValidationResult]:
        return [r for r in self.results if not r.passed]

async def validate_environment(config: OrchestratorConfig) -> ValidationReport:
    """Run all validation checks"""
    results = []

    # Validate Azure credentials
    results.append(await validate_azure_credentials(config))

    # Validate Anthropic API
    results.append(await validate_anthropic_api(config))

    # Validate container image
    results.append(await validate_container_image(config))

    # Validate Service Bus
    results.append(await validate_service_bus(config))

    overall_passed = all(r.passed for r in results)
    return ValidationReport(overall_passed=overall_passed, results=results)
```

---

### Module 3: Service Principal Manager

**File**: `src/orchestrator/sp_manager.py`

**Purpose**: Create, assign roles to, and delete service principals for scenarios.

**Contract**:
- **Inputs**: Scenario name, required roles, Key Vault client
- **Outputs**: Service principal details (client_id, secret_reference)
- **Side Effects**: Creates SP in Entra ID, assigns roles, stores secret in Key Vault

**Dependencies**:
- `azure-identity`
- `azure-mgmt-authorization`
- `msgraph-sdk` (for SP creation)
- `azure-keyvault-secrets`

**Implementation Notes**:
- Wait 60 seconds after role assignment for propagation
- Store secret in Key Vault with naming convention: `scenario-sp-{scenario_name}-secret`
- Delete both SP and secret during cleanup
- Handle rate limiting with retries

**Test Requirements**:
- Test SP creation (should create and return details)
- Test role assignment (should assign roles)
- Test secret storage (should store in Key Vault)
- Test deletion (should delete SP and secret)
- Test duplicate creation (should handle gracefully)
- Mock Azure APIs

**Example Interface**:
```python
from dataclasses import dataclass
from typing import List

@dataclass
class ServicePrincipalDetails:
    sp_name: str
    client_id: str
    principal_id: str
    secret_reference: str  # Key Vault secret name
    created_at: str

async def create_service_principal(
    scenario_name: str,
    subscription_id: str,
    roles: List[str],
    key_vault_client: SecretClient
) -> ServicePrincipalDetails:
    """Create SP, assign roles, store secret"""
    ...

async def delete_service_principal(
    sp_name: str,
    key_vault_client: SecretClient
) -> None:
    """Delete SP and its secret from Key Vault"""
    ...

async def list_haymaker_service_principals() -> List[str]:
    """List all SPs created by HayMaker (for debugging)"""
    ...
```

---

### Module 4: Scenario Selector

**File**: `src/orchestrator/scenario_selector.py`

**Purpose**: Load available scenarios from storage and randomly select N based on simulation size.

**Contract**:
- **Inputs**: Simulation size, storage client
- **Outputs**: List of selected scenario metadata
- **Side Effects**: Reads from storage

**Dependencies**:
- `azure-storage-blob`

**Implementation Notes**:
- Load scenario list from storage account (synced from repo)
- Randomly select N scenarios without replacement
- Validate scenario document structure
- Return scenario name, document path, and agent path

**Test Requirements**:
- Test with various simulation sizes (should return correct count)
- Test scenario validation (should reject malformed scenarios)
- Test random selection (should be different each time, statistically)
- Mock storage client

**Example Interface**:
```python
from dataclasses import dataclass
from typing import List, Literal

@dataclass
class ScenarioMetadata:
    scenario_name: str
    scenario_doc_path: str  # Storage blob path
    agent_path: str  # Path to agent instructions
    technology_area: str

async def load_available_scenarios(
    storage_client: BlobServiceClient
) -> List[ScenarioMetadata]:
    """Load all available scenarios from storage"""
    ...

async def select_scenarios(
    simulation_size: Literal["small", "medium", "large"],
    storage_client: BlobServiceClient
) -> List[ScenarioMetadata]:
    """Randomly select N scenarios based on simulation size"""
    count_map = {"small": 5, "medium": 15, "large": 30}
    count = count_map[simulation_size]

    available = await load_available_scenarios(storage_client)

    if len(available) < count:
        raise ValueError(f"Not enough scenarios available: {len(available)} < {count}")

    import random
    return random.sample(available, count)
```

---

### Module 5: Container Manager

**File**: `src/orchestrator/container_manager.py`

**Purpose**: Deploy Container Apps for scenario execution with proper configuration and secrets.

**Contract**:
- **Inputs**: Scenario metadata, SP details, config
- **Outputs**: Container App details (name, resource_id)
- **Side Effects**: Creates Container App in Azure

**Dependencies**:
- `azure-identity`
- `azure-mgmt-containerinstance`

**Implementation Notes**:
- Use Managed Identity for Container App
- Pass secrets via secure environment variables
- Set resource limits (64GB RAM, 2 CPU)
- Set timeout to 10 hours
- Configure restart policy to Never

**Test Requirements**:
- Test deployment (should create Container App)
- Test secret injection (should not expose secrets)
- Test resource limits (should match config)
- Test timeout (should be 10 hours)
- Mock Azure API

**Example Interface**:
```python
from dataclasses import dataclass

@dataclass
class ContainerAppDetails:
    name: str
    resource_id: str
    created_at: str
    scenario_name: str
    sp_name: str

async def deploy_container_app(
    scenario: ScenarioMetadata,
    sp_details: ServicePrincipalDetails,
    config: OrchestratorConfig,
    run_id: str
) -> ContainerAppDetails:
    """Deploy Container App for scenario execution"""

    # Build environment variables
    env_vars = [
        {"name": "AZURE_TENANT_ID", "value": config.target_tenant_id},
        {"name": "AZURE_CLIENT_ID", "value": sp_details.client_id},
        {"name": "AZURE_CLIENT_SECRET", "secretRef": sp_details.secret_reference},
        {"name": "AZURE_SUBSCRIPTION_ID", "value": config.target_subscription_id},
        {"name": "ANTHROPIC_API_KEY", "secretRef": "anthropic-api-key"},
        {"name": "SERVICE_BUS_CONNECTION_STRING", "secretRef": "service-bus-connection"},
        {"name": "SCENARIO_NAME", "value": scenario.scenario_name},
        {"name": "RUN_ID", "value": run_id},
        {"name": "LOG_LEVEL", "value": "INFO"}
    ]

    # Deploy Container App
    ...

    return ContainerAppDetails(...)

async def delete_container_app(container_app_name: str) -> None:
    """Delete Container App"""
    ...
```

---

### Module 6: Event Bus Manager

**File**: `src/orchestrator/event_bus.py`

**Purpose**: Subscribe to Service Bus topic, receive agent log messages, aggregate to storage.

**Contract**:
- **Inputs**: Config, run_id, storage client
- **Outputs**: Stream of log messages
- **Side Effects**: Reads from Service Bus, writes to Storage

**Dependencies**:
- `azure-servicebus`
- `azure-storage-blob`

**Implementation Notes**:
- Use async generator pattern for message streaming
- Write messages to storage as JSON Lines
- Extract resource IDs from messages
- Track agent status (started, in_progress, cleanup_complete)

**Test Requirements**:
- Test message reception (should receive messages)
- Test storage aggregation (should write to storage)
- Test resource ID extraction (should extract correctly)
- Test status tracking (should track agent status)
- Mock Service Bus and Storage

**Example Interface**:
```python
from dataclasses import dataclass
from typing import AsyncGenerator, Literal

@dataclass
class AgentLogMessage:
    event_type: Literal["agent_started", "resource_created", "operation", "cleanup_complete", "error"]
    timestamp: str
    scenario_name: str
    run_id: str
    agent_id: str
    sp_name: str
    message: str
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    severity: Literal["info", "warning", "error"] = "info"
    details: Optional[dict] = None

async def subscribe_to_agent_logs(
    config: OrchestratorConfig,
    run_id: str
) -> AsyncGenerator[AgentLogMessage, None]:
    """Subscribe to Service Bus and yield log messages"""
    async with ServiceBusClient.from_connection_string(...) as client:
        async with client.get_subscription_receiver(...) as receiver:
            async for message in receiver:
                log_message = AgentLogMessage(**json.loads(str(message)))
                yield log_message
                await receiver.complete_message(message)

async def aggregate_logs_to_storage(
    log_messages: AsyncGenerator[AgentLogMessage, None],
    storage_client: BlobServiceClient,
    run_id: str
) -> None:
    """Aggregate log messages to storage"""
    async for log_message in log_messages:
        # Write to storage as JSON Lines
        blob_client = storage_client.get_blob_client(
            container="execution-logs",
            blob=f"{run_id}/{log_message.scenario_name}/logs.jsonl"
        )
        await blob_client.append_blob(json.dumps(log_message.__dict__) + "\n")
```

---

### Module 7: Cleanup Manager

**File**: `src/orchestrator/cleanup.py`

**Purpose**: Verify scenario cleanup, force-delete remaining resources, delete service principals.

**Contract**:
- **Inputs**: Run ID, list of scenarios, SP details
- **Outputs**: Cleanup report
- **Side Effects**: Deletes Azure resources, deletes SPs, deletes Key Vault secrets

**Dependencies**:
- `azure-identity`
- `azure-mgmt-resource`
- `azure-mgmt-authorization`
- `msgraph-sdk`

**Implementation Notes**:
- Query Azure Resource Graph for tagged resources
- Delete resources in dependency order
- Retry deletions with exponential backoff
- Delete service principals
- Delete Key Vault secrets

**Test Requirements**:
- Test cleanup verification (should detect remaining resources)
- Test forced deletion (should delete resources)
- Test SP deletion (should delete SPs)
- Test retry logic (should retry on dependency errors)
- Mock Azure APIs

**Example Interface**:
```python
from dataclasses import dataclass
from typing import List

@dataclass
class ResourceDeletion:
    resource_id: str
    resource_type: str
    status: Literal["deleted", "failed"]
    attempts: int
    error: Optional[str] = None

@dataclass
class CleanupReport:
    run_id: str
    total_resources_expected: int
    total_resources_deleted: int
    deletions: List[ResourceDeletion]
    service_principals_deleted: List[str]

    def has_failures(self) -> bool:
        return any(d.status == "failed" for d in self.deletions)

async def verify_cleanup(
    run_id: str,
    scenarios: List[ScenarioMetadata]
) -> List[str]:
    """Query Azure for remaining tagged resources"""
    query = f"Resources | where tags['AzureHayMaker-managed'] == 'true' and tags['RunId'] == '{run_id}'"
    remaining_resources = await azure_resource_graph_query(query)
    return [r["id"] for r in remaining_resources]

async def force_cleanup(
    run_id: str,
    scenarios: List[ScenarioMetadata],
    sp_details: List[ServicePrincipalDetails]
) -> CleanupReport:
    """Force delete all remaining resources and SPs"""
    ...
```

---

### Module 8: Monitoring API

**File**: `src/orchestrator/monitoring.py`

**Purpose**: Provide HTTP API endpoints for querying execution status, resources, and logs.

**Contract**:
- **Inputs**: HTTP requests (run_id, filters)
- **Outputs**: JSON responses
- **Side Effects**: Reads from storage, reads execution state

**Dependencies**:
- `azure-functions`
- `azure-storage-blob`

**Implementation Notes**:
- Use Azure Functions HTTP triggers
- Read execution state from storage
- Paginate log responses
- Cache recent data

**Test Requirements**:
- Test status endpoint (should return current status)
- Test runs endpoint (should return run list)
- Test run details endpoint (should return run details)
- Test resources endpoint (should return resource list)
- Test SPs endpoint (should return SP list)
- Test logs endpoint (should return paginated logs)
- Mock storage

**Example Interface**:
```python
from dataclasses import dataclass
from typing import List, Literal, Optional

@dataclass
class ExecutionStatus:
    status: Literal["running", "idle", "error"]
    current_run_id: Optional[str]
    started_at: Optional[str]
    scheduled_end_at: Optional[str]

@dataclass
class ExecutionSummary:
    run_id: str
    started_at: str
    ended_at: Optional[str]
    status: Literal["completed", "in_progress", "failed"]
    scenarios_count: int
    resources_created: int
    cleanup_status: Literal["verified", "partial", "failed"]

async def get_current_status(storage_client: BlobServiceClient) -> ExecutionStatus:
    """Get current orchestrator status"""
    ...

async def get_recent_runs(
    storage_client: BlobServiceClient,
    limit: int = 10
) -> List[ExecutionSummary]:
    """Get recent execution runs"""
    ...

async def get_run_details(
    storage_client: BlobServiceClient,
    run_id: str
) -> dict:
    """Get detailed information for a specific run"""
    ...
```

---

### Module 9: Orchestrator Main

**File**: `src/orchestrator/orchestrator.py`

**Purpose**: Main Durable Functions orchestrator that coordinates the entire workflow.

**Contract**:
- **Inputs**: Timer trigger (CRON)
- **Outputs**: Execution report
- **Side Effects**: Coordinates all other modules

**Dependencies**:
- `azure-functions`
- `azure-durable-functions`
- All other orchestrator modules

**Implementation Notes**:
- Use Durable Functions orchestration pattern
- Fan-out/fan-in for parallel SP creation and Container App deployment
- Wait 8 hours with periodic monitoring checks
- Generate final execution report

**Test Requirements**:
- Test full orchestration flow (integration test)
- Test with failures at various stages
- Test cleanup verification
- Test forced cleanup
- Mock Azure APIs

**Example Interface**:
```python
import azure.functions as func
import azure.durable_functions as df
from typing import List

# Timer trigger (4x daily)
@app.timer_trigger(schedule="0 0 0,6,12,18 * * *", arg_name="myTimer", run_on_startup=False)
@app.durable_client_input(client_name="client")
async def orchestrator_timer(myTimer: func.TimerRequest, client):
    """Timer trigger for orchestrator"""
    instance_id = await client.start_new("orchestrate_haymaker_run")
    return client.create_check_status_response(None, instance_id)

# Orchestrator function
@app.orchestration_trigger(context_name="context")
def orchestrate_haymaker_run(context: df.DurableOrchestrationContext):
    """Main orchestration function"""
    run_id = context.new_guid()

    # Phase 1: Validation
    validation_result = yield context.call_activity("validate_environment")
    if not validation_result["overall_passed"]:
        return {"status": "failed", "reason": "validation_failed"}

    # Phase 2: Selection
    scenarios = yield context.call_activity("select_scenarios")

    # Phase 3: Provisioning (parallel)
    sp_tasks = [
        context.call_activity("create_service_principal", scenario)
        for scenario in scenarios
    ]
    sp_details_list = yield context.task_all(sp_tasks)

    # Deploy Container Apps (parallel)
    container_tasks = [
        context.call_activity("deploy_container_app", {
            "scenario": scenario,
            "sp_details": sp_details,
            "run_id": run_id
        })
        for scenario, sp_details in zip(scenarios, sp_details_list)
    ]
    container_details_list = yield context.task_all(container_tasks)

    # Phase 4: Monitoring (8 hours)
    end_time = context.current_utc_datetime + timedelta(hours=8)
    while context.current_utc_datetime < end_time:
        # Periodic status check
        yield context.call_activity("check_agent_status", run_id)
        # Wait 15 minutes
        yield context.create_timer(context.current_utc_datetime + timedelta(minutes=15))

    # Phase 5: Cleanup Verification
    remaining_resources = yield context.call_activity("verify_cleanup", run_id)

    # Phase 6: Forced Cleanup
    cleanup_report = yield context.call_activity("force_cleanup", {
        "run_id": run_id,
        "scenarios": scenarios,
        "sp_details": sp_details_list
    })

    # Phase 7: Report Generation
    report = yield context.call_activity("generate_report", {
        "run_id": run_id,
        "scenarios": scenarios,
        "cleanup_report": cleanup_report
    })

    return report
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
**Modules**:
1. Configuration Manager
2. Environment Validator

**Deliverables**:
- Config loading from Key Vault
- Validation of Azure/Anthropic credentials
- Unit tests (100% coverage)

**Success Criteria**:
- All tests passing
- Can load config from Key Vault
- Can validate credentials

---

### Phase 2: Service Principal Management (Week 2)
**Modules**:
3. Service Principal Manager

**Deliverables**:
- SP creation/deletion
- Role assignment
- Key Vault secret storage
- Unit tests (100% coverage)

**Success Criteria**:
- Can create SP programmatically
- Can assign roles
- Secret stored in Key Vault
- All tests passing

---

### Phase 3: Scenario Selection (Week 2)
**Modules**:
4. Scenario Selector

**Deliverables**:
- Load scenarios from storage
- Random selection logic
- Scenario validation
- Unit tests (100% coverage)

**Success Criteria**:
- Can load all 50 scenarios
- Random selection works correctly
- All tests passing

---

### Phase 4: Container Deployment (Week 3)
**Modules**:
5. Container Manager
6. Agent Docker Image

**Deliverables**:
- Container App deployment
- Agent Docker image with all tools
- Dockerfile
- Build pipeline
- Unit tests

**Success Criteria**:
- Container App deploys successfully
- Agent image contains all required tools
- Secrets injected securely
- All tests passing

---

### Phase 5: Event Bus Integration (Week 3)
**Modules**:
7. Event Bus Manager

**Deliverables**:
- Service Bus subscription
- Log aggregation to storage
- Resource ID extraction
- Unit tests

**Success Criteria**:
- Can receive messages from Service Bus
- Logs stored in storage account
- Resource IDs extracted correctly
- All tests passing

---

### Phase 6: Cleanup Management (Week 4)
**Modules**:
8. Cleanup Manager

**Deliverables**:
- Cleanup verification logic
- Forced deletion logic
- Retry logic for dependencies
- Unit tests

**Success Criteria**:
- Can query remaining resources
- Can force-delete resources
- Handles dependencies correctly
- All tests passing

---

### Phase 7: Monitoring API (Week 4)
**Modules**:
9. Monitoring API

**Deliverables**:
- HTTP API endpoints
- Status queries
- Resource/SP lists
- Log pagination
- Unit tests

**Success Criteria**:
- All endpoints functional
- Responses match schema
- Pagination works
- All tests passing

---

### Phase 8: Orchestration (Week 5)
**Modules**:
10. Orchestrator Main

**Deliverables**:
- Durable Functions orchestration
- Timer trigger
- Fan-out/fan-in pattern
- Integration tests

**Success Criteria**:
- Full workflow executes successfully
- Cleanup works end-to-end
- Integration tests passing

---

### Phase 9: Infrastructure Deployment (Week 5)
**Modules**:
11. Bicep templates
12. CI/CD pipeline

**Deliverables**:
- Bicep modules for all Azure resources
- GitHub Actions workflow
- Deployment documentation

**Success Criteria**:
- Infrastructure deploys via Bicep
- CI/CD pipeline functional
- Documentation complete

---

### Phase 10: End-to-End Testing (Week 6)
**Activities**:
- Deploy to dev environment
- Run full execution with 1 scenario
- Run full execution with 5 scenarios
- Test failure scenarios
- Test cleanup verification
- Performance testing

**Success Criteria**:
- All E2E tests passing
- No resource leaks
- Cleanup verified
- Performance acceptable

---

### Phase 11: Zero-BS Compliance Review (Week 7)
**Activities**:
- First pass: Automated scan + manual review
- Fix violations
- Second pass: Deep verification
- Final sign-off

**Success Criteria**:
- Zero TODOs
- Zero stubs
- Zero faked data
- All error paths verified
- All cleanup verified
- Documentation complete

---

### Phase 12: Production Deployment (Week 8)
**Activities**:
- Deploy to production environment
- Configure 4x daily schedule
- Enable monitoring and alerts
- Run first production execution
- Monitor for 1 week

**Success Criteria**:
- Service runs reliably
- No manual intervention needed
- Cleanup always succeeds
- Logs provide sufficient debugging info
- Monitoring data accurate

---

## Risks and Mitigations

### Risk 1: Service Principal Permission Escalation
**Risk**: Created SPs might gain excessive permissions inadvertently

**Likelihood**: Medium
**Impact**: High

**Mitigation**:
- Explicit role assignment (only User Access Administrator + Contributor)
- Audit logging of all role assignments
- Time-limited SPs (deleted after 8 hours)
- Regular audit of SP permissions

---

### Risk 2: Resource Cleanup Failure
**Risk**: Resources might not be deleted, causing cost accumulation

**Likelihood**: Medium
**Impact**: High

**Mitigation**:
- Forced cleanup verification
- Retry logic with exponential backoff
- Alerting on cleanup failure
- Daily orphaned resource check
- Cost monitoring and budget alerts

---

### Risk 3: Credential Leakage
**Risk**: SP secrets might be exposed in logs or errors

**Likelihood**: Low
**Impact**: Critical

**Mitigation**:
- Credential scrubbing in logs (regex patterns)
- Key Vault for secret storage
- Secure environment variables
- No secrets in code or container images
- Audit logging of Key Vault access

---

### Risk 4: Container App Quota Exhaustion
**Risk**: Might hit subscription limits for Container Apps

**Likelihood**: Medium
**Impact**: Medium

**Mitigation**:
- Quota validation before execution
- Graceful handling of quota errors
- Configurable simulation size
- Monitoring of quota usage
- Request quota increase if needed

---

### Risk 5: Agent Execution Timeout
**Risk**: Agents might hang or fail to complete in 8 hours

**Likelihood**: Low
**Impact**: Medium

**Mitigation**:
- Container timeout setting (10 hours)
- Health checks during execution
- Forced termination after deadline
- Cleanup verification regardless of agent status

---

### Risk 6: API Rate Limiting
**Risk**: Azure or Anthropic APIs might throttle requests

**Likelihood**: Medium
**Impact**: Medium

**Mitigation**:
- Retry logic with exponential backoff
- Request spacing (stagger Container App deployments)
- Monitoring of API response codes
- Alerting on rate limit errors

---

## Open Decisions

### Decision 1: Exact Schedule Times
**Question**: What are the exact times for 4 daily executions?

**Options**:
- Option A: 00:00, 06:00, 12:00, 18:00 UTC
- Option B: Region-specific times (US: 09:00 EST, Asia: 09:00 JST, etc.)

**Recommendation**: Option A (UTC times)
**Justification**: Simpler to manage, no DST issues, predictable scheduling

**Required Action**: Confirm with stakeholder

---

### Decision 2: Service Bus Tier
**Question**: Standard or Premium tier?

**Options**:
- Standard: 1,000 ops/sec, $0.05/million ops
- Premium: Higher throughput, dedicated resources, $0.928/hour

**Recommendation**: Start with Standard, upgrade to Premium if > 25 scenarios
**Justification**: Standard sufficient for small/medium simulation sizes, cost-effective

**Required Action**: Confirm with stakeholder

---

### Decision 3: Container Registry Location
**Question**: Where to host agent container images?

**Options**:
- Azure Container Registry (ACR)
- Docker Hub
- GitHub Container Registry

**Recommendation**: Azure Container Registry
**Justification**: Native Azure integration, private registry, Managed Identity support

**Required Action**: Confirm with stakeholder

---

### Decision 4: Failure Handling for Individual Agents
**Question**: If one agent fails, should we retry or continue with others?

**Options**:
- Option A: Continue with other agents (isolation)
- Option B: Retry failed agent up to 3 times
- Option C: Abort entire execution

**Recommendation**: Option A (continue with others)
**Justification**: Maximizes successful scenarios, failure is logged, cleanup still runs

**Required Action**: Confirm with stakeholder

---

### Decision 5: Simulation Size Mapping
**Question**: Confirm mapping of simulation size to scenario count

**Proposal**:
- small: 5 scenarios
- medium: 15 scenarios
- large: 30 scenarios

**Rationale**:
- Small: Low cost, quick testing
- Medium: Balanced for regular operations
- Large: Maximum telemetry generation

**Required Action**: Confirm with stakeholder

---

## Success Metrics

### Functional Metrics
- **Execution Success Rate**: > 95% of executions complete without fatal errors
- **Cleanup Success Rate**: 100% of resources cleaned up (verified)
- **Agent Success Rate**: > 90% of agents complete all three phases
- **API Availability**: > 99% uptime for status API

### Performance Metrics
- **Provisioning Time**: < 10 minutes to deploy all Container Apps
- **Cleanup Time**: < 15 minutes to verify and force-delete resources
- **API Response Time**: < 500ms for status queries (p95)
- **Log Latency**: < 30 seconds from agent publish to storage

### Quality Metrics
- **Zero-BS Compliance**: 100% (no TODOs, no stubs, no faked data)
- **Test Coverage**: > 80% overall, 100% for critical paths
- **Code Review Pass Rate**: > 90% on first review
- **Security Scan Pass Rate**: 100% (no critical vulnerabilities)

### Operational Metrics
- **Manual Interventions**: 0 per week (fully automated)
- **Alert Fatigue**: < 5 actionable alerts per week
- **Cost Per Execution**: Tracked and within budget
- **Time to Debug Issues**: < 1 hour (sufficient logging)

---

## Appendix A: Glossary

**Agent**: Goal-seeking Claude Code agent that executes a scenario autonomously

**Container App**: Azure Container Apps instance that runs an agent

**Durable Functions**: Azure Functions extension for long-running workflows

**Orchestrator**: The main service that coordinates scenario execution

**Run**: Single execution of the orchestrator (4x daily)

**Scenario**: Documented Azure operational procedure with Deploy/Operate/Cleanup phases

**Service Principal (SP)**: Azure identity used by agents to access resources

**Simulation Size**: Configuration parameter determining number of scenarios to execute (small/medium/large)

**Zero-BS Philosophy**: Development principle requiring no stubs, TODOs, or faked implementations

---

## Appendix B: Related Documentation

- [Azure Durable Functions Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Service Bus Documentation](https://learn.microsoft.com/en-us/azure/service-bus-messaging/)
- [Azure Key Vault Documentation](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Azure Bicep Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Goal-Seeking Agent Pattern](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/blob/main/docs/GOAL_AGENT_GENERATOR_GUIDE.md)
- [Azure HayMaker Requirements](specs/requirements.md)
- [Azure HayMaker Initial Prompt](specs/initial-prompt.md)

---

## Document Metadata

**Version**: 1.0
**Date**: 2025-11-14
**Author**: Claude Code (Architect Agent)
**Status**: Ready for Review
**Next Steps**:
1. Stakeholder review and feedback
2. Resolve open decisions
3. Security review by security specialist
4. Architecture review by architecture specialist
5. Cost review by cost specialist
6. Approval and handoff to builder agent

---

**End of Architecture Specification**
