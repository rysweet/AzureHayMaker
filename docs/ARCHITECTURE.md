# Azure HayMaker Architecture

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Specifications](#component-specifications)
- [Implementation Status](#implementation-status)
- [Design Decisions](#design-decisions)
- [Security Architecture](#security-architecture)
- [Data Flow](#data-flow)
- [Deployment Model](#deployment-model)

## Overview

Azure HayMaker is an orchestration service that generates benign telemetry to simulate ordinary Azure tenant operations. The system executes multiple concurrent scenarios, each managed by an autonomous goal-seeking agent operating with dedicated credentials in isolated container environments.

### Core Principles

1. **Zero-BS Philosophy**: Every component implements real functionality with no stubs, TODOs, or placeholders
2. **Goal-Seeking Agents**: Autonomous agents resolve problems encountered during execution
3. **Complete Cleanup**: All resources are tracked, verified, and removed after execution
4. **Single Tenant Scope**: All operations constrained to one Azure tenant and subscription
5. **Observable Operations**: Comprehensive logging and monitoring at every level

### High-Level Architecture

```mermaid
graph TB
    subgraph "Azure Functions - Orchestrator"
        Timer[Timer Trigger<br/>4x Daily]
        Config[Configuration<br/>Validator]
        Selector[Scenario<br/>Selector]
        SPMgr[Service Principal<br/>Manager]
        Monitor[Monitoring<br/>Service]
        Cleanup[Cleanup<br/>Enforcer]
    end

    subgraph "Azure Container Apps - Agent Execution"
        Agent1[Agent Container 1<br/>Scenario: compute-03]
        Agent2[Agent Container 2<br/>Scenario: security-01]
        AgentN[Agent Container N<br/>Scenario: ai-ml-03]
    end

    subgraph "Azure Service Bus"
        EventBus[Event Bus<br/>Agent Logs]
    end

    subgraph "Azure Key Vault"
        Secrets[Credentials<br/>Storage]
    end

    subgraph "Target Azure Tenant"
        Resources[Deployed<br/>Resources]
    end

    Timer --> Config
    Config --> Selector
    Selector --> SPMgr
    SPMgr --> Secrets
    SPMgr --> Agent1
    SPMgr --> Agent2
    SPMgr --> AgentN

    Agent1 --> EventBus
    Agent2 --> EventBus
    AgentN --> EventBus

    Agent1 --> Resources
    Agent2 --> Resources
    AgentN --> Resources

    EventBus --> Monitor
    Monitor --> Cleanup
    Cleanup --> Resources
```

## System Architecture

### Component Overview

Azure HayMaker is designed around five primary components:

1. **Orchestrator Service** (Azure Functions) - Schedules and coordinates scenario execution, manages service principal lifecycle, and enforces cleanup policies

2. **Agent Containers** (Azure Container Apps) - Execute individual scenarios in isolated environments and generate operational telemetry

3. **Event Bus** (Azure Service Bus) - Collects logs from all agents and provides audit trail

4. **Configuration Store** (Azure Key Vault) - Securely stores credentials and configuration

5. **Scenario Repository** (Filesystem/Git) - Currently implemented with 50+ documented scenarios, template for creating new scenarios, and reference architectures

### Architectural Layers

```mermaid
graph TD
    subgraph "Presentation Layer"
        API[REST API<br/>Status Endpoints]
        CLI[CLI Interface]
    end

    subgraph "Orchestration Layer"
        Scheduler[Execution Scheduler]
        Validator[Configuration Validator]
        SPManager[SP Lifecycle Manager]
        Selector[Scenario Selector]
    end

    subgraph "Execution Layer"
        ContainerMgr[Container Manager]
        AgentRuntime[Agent Runtime]
        EventCollector[Event Collector]
    end

    subgraph "Infrastructure Layer"
        Azure[Azure SDK]
        Anthropic[Anthropic SDK]
        Tools[CLI Tools<br/>az, terraform, bicep]
    end

    subgraph "Data Layer"
        Scenarios[Scenario Documents]
        Logs[Execution Logs]
        Metrics[Telemetry Metrics]
    end

    API --> Scheduler
    CLI --> Validator
    Scheduler --> SPManager
    Scheduler --> Selector
    Validator --> Scheduler

    SPManager --> ContainerMgr
    Selector --> ContainerMgr
    ContainerMgr --> AgentRuntime
    AgentRuntime --> EventCollector

    AgentRuntime --> Azure
    AgentRuntime --> Anthropic
    AgentRuntime --> Tools

    Selector --> Scenarios
    EventCollector --> Logs
    EventCollector --> Metrics
```

## Scenario Repository

**Purpose**: Storage and version control for scenario documents.

**Structure**:
```
docs/scenarios/
├── SCENARIO_TEMPLATE.md          # Template for new scenarios
├── SCALING_PLAN.md               # Roadmap for expansion
├── [area]-[num]-[name].md        # 50+ scenario documents
```

**Scenario Count by Technology Area**:
- AI & ML: 5 scenarios
- Analytics: 5 scenarios
- Compute: 5 scenarios
- Containers: 5 scenarios
- Databases: 5 scenarios
- Hybrid + Multicloud: 5 scenarios
- Identity: 5 scenarios
- Networking: 5 scenarios
- Security: 5 scenarios
- Web Apps: 5 scenarios

**Total**: 50 scenarios implemented

**Example Scenarios**:
- `compute-03-app-service-python.md` - Flask web app on App Service
- `security-01-key-vault-secrets.md` - Secret management with Key Vault
- `containers-02-aks-cluster.md` - Kubernetes cluster deployment
- `databases-02-cosmos-db.md` - NoSQL database operations
- `ai-ml-03-azure-openai.md` - OpenAI service integration

**See**: [SCENARIO_MANAGEMENT.md](SCENARIO_MANAGEMENT.md) for detailed scenario documentation.

## Design Decisions

### Decision 1: Azure Functions vs. Container Apps for Orchestrator

**Chosen**: Azure Functions (Timer Trigger)

**Rationale**:
- **Scheduling**: Built-in timer trigger for 4x daily execution
- **Cost**: Pay-per-execution model (runs 4x daily)
- **Serverless**: No infrastructure management required
- **Integration**: Native Azure SDK support
- **Simplicity**: Straightforward deployment model

**Alternatives Considered**:
- **Container Apps**: More complex for scheduling, better for long-running processes
- **Logic Apps**: Less flexible for complex Python logic
- **VM-based**: Higher cost and maintenance burden

### Decision 2: Azure Service Bus vs. Event Hubs vs. Event Grid

**Chosen**: Azure Service Bus (Queue)

**Rationale**:
- **Message Ordering**: Guaranteed FIFO for agent logs
- **Persistence**: 7-day message retention for audit
- **Reliability**: At-least-once delivery guarantee
- **Simplicity**: Straightforward queue model
- **Cost**: Reasonable for expected message volume

**Alternatives Considered**:
- **Event Hubs**: Overkill for our message volume, designed for millions of events/sec
- **Event Grid**: Better for event routing, not log aggregation
- **Storage Queues**: Less features, no topics/subscriptions

### Decision 3: Scenario Selection Algorithm - Random vs. Round-Robin

**Chosen**: Random Selection

**Rationale**:
- **Realism**: Real tenants don't execute scenarios in predictable patterns
- **Simplicity**: No state to maintain between executions
- **Coverage**: Over time, all scenarios get executed
- **Flexibility**: Easy to weight certain scenarios if needed

**Alternatives Considered**:
- **Round-Robin**: Ensures even distribution but predictable
- **Priority-Based**: More complex, requires priority assignment
- **Load-Based**: Requires resource profiling of scenarios

### Decision 4: Container Resources - 64GB RAM, 2 CPUs

**Chosen**: 64GB RAM, 2 CPUs per agent container

**Rationale**:
- **Azure CLI**: Requires ~2GB for operations
- **Terraform**: State management can be memory-intensive
- **Claude Code**: Requires substantial memory for context
- **Overhead**: OS, Python runtime, tools
- **Safety Margin**: Ensures agents don't run out of memory

**Cost Consideration**:
- 5 concurrent scenarios = 320GB RAM, 10 CPUs
- ~$200-300/month for 4 executions/day (8 hours each)
- Acceptable for realistic telemetry generation

**Alternatives Considered**:
- **32GB RAM, 1 CPU**: Risk of memory exhaustion
- **128GB RAM, 4 CPUs**: Unnecessary overhead, higher cost

### Decision 5: Service Principal Lifecycle - Ephemeral vs. Persistent

**Chosen**: Ephemeral (created per execution, deleted after)

**Rationale**:
- **Security**: Minimizes credential lifetime and exposure
- **Isolation**: Each execution gets fresh credentials
- **Cleanup**: Credentials automatically invalidated after scenario
- **Auditing**: Clear association between SP and scenario execution

**Cost**: Negligible (SP creation is free, role assignments are free)

**Alternatives Considered**:
- **Persistent SPs**: Reused across executions, easier but less secure
- **Managed Identity**: Cannot be used for service-to-service in this model

### Decision 6: Scenario Document Format - Markdown vs. YAML

**Chosen**: Markdown with embedded bash code blocks

**Rationale**:
- **Readability**: Human-readable documentation
- **Embedded**: Scenario context and commands in one file
- **Agent-Friendly**: Claude can easily parse and extract commands
- **Version Control**: Git-friendly format with clear diffs
- **Documentation**: Doubles as reference documentation

**Alternatives Considered**:
- **YAML with scripts**: Harder to read, requires separate script files
- **Python modules**: Less accessible for non-developers
- **JSON**: Not human-friendly

### Decision 7: Cleanup Strategy - Agent-Only vs. Orchestrator-Enforced

**Chosen**: Orchestrator-Enforced with Tag-Based Verification

**Rationale**:
- **Reliability**: Ensures cleanup happens even if agent fails
- **Cost Control**: Prevents resource leaks
- **Accountability**: Orchestrator validates cleanup completion
- **Safety Net**: Force-deletes anything agent misses

**Process**:
1. Agent performs cleanup (Phase 3)
2. Agent logs cleanup completion
3. Orchestrator queries Azure for tagged resources
4. Orchestrator force-deletes any remaining resources
5. Orchestrator deletes service principal

**Alternatives Considered**:
- **Agent-Only**: Risky, agent failures leave resources behind
- **Orchestrator-Only**: Agent doesn't learn, no graceful cleanup

### Decision 8: Agent Error Handling - Fail-Fast vs. Goal-Seeking

**Chosen**: Goal-Seeking with Claude Analysis

**Rationale**:
- **Resilience**: Agents attempt to resolve errors autonomously
- **Learning**: Errors and resolutions logged for analysis
- **Realism**: Real administrators troubleshoot and resolve issues
- **Telemetry**: Error resolution generates valuable telemetry

**Process**:
1. Agent encounters error
2. Agent sends error context to Claude
3. Claude analyzes error and suggests resolution
4. Agent attempts resolution
5. If resolved, continue; if not, cleanup and fail gracefully

**Alternatives Considered**:
- **Fail-Fast**: Simpler but less realistic, more manual intervention
- **Retry-Only**: Doesn't address root cause

## Security Architecture

### Threat Model

**Assumptions**:
- Azure tenant is test/dev environment (not production)
- Operators trust the orchestrator service
- Service principals have limited scope (single subscription)
- No malicious scenarios in repository

**Threats**:

1. **Credential Leakage**
   - **Risk**: Service principal secrets exposed in logs or errors
   - **Mitigation**: Credential scrubbing, secure environment variables, Key Vault storage

2. **Privilege Escalation**
   - **Risk**: Scenario SPs gain excessive permissions
   - **Mitigation**: Strict role assignment logic, time-limited SPs, audit logging

3. **Resource Leakage**
   - **Risk**: Resources not cleaned up, accumulating costs
   - **Mitigation**: Forced cleanup verification, cost alerts, tag-based queries

4. **Lateral Movement**
   - **Risk**: Compromised agent affects other resources
   - **Mitigation**: Isolated containers, scoped credentials, network policies

5. **Data Exfiltration**
   - **Risk**: Agents extract sensitive data
   - **Mitigation**: Benign-only scenarios, network egress controls, audit logs

### Security Controls

#### 1. Credential Management

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant KV as Key Vault
    participant SP as Service Principal Manager
    participant A as Agent Container

    O->>KV: Retrieve main SP credentials
    KV-->>O: Return credentials
    O->>SP: Create scenario SP
    SP->>KV: Store scenario SP credentials
    KV-->>SP: Confirm storage
    O->>A: Deploy container with SP reference
    A->>KV: Retrieve scenario SP credentials
    KV-->>A: Return credentials (secure)
    A->>A: Use credentials (never log)
    A->>O: Scenario complete
    O->>SP: Delete scenario SP
    SP->>KV: Delete credentials
```

**Controls**:
- Main SP credentials stored in Azure Key Vault
- Scenario SP credentials generated per execution
- Credentials passed via secure environment variables only
- Credentials never logged or written to disk
- Credentials cleared from memory after use
- Credentials automatically invalidated after scenario (SP deleted)

#### 2. Least Privilege

**Main Service Principal Roles**:
- **Contributor**: Create/delete Azure resources
- **User Access Administrator**: Assign roles to scenario SPs
- **Key Vault Administrator**: Manage credential storage

**Scenario Service Principal Roles**:
- **Contributor**: Create/delete scenario resources only
- **User Access Administrator**: Assign roles within scenario scope

**Restrictions**:
- All roles scoped to single subscription
- No Global Administrator or privileged roles
- Time-limited (12 hours max)
- Deleted immediately after scenario

#### 3. Network Security

**Container Network Policy**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-network-policy
spec:
  podSelector:
    matchLabels:
      app: haymaker-agent
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 443  # HTTPS only
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 53  # DNS
```

**Allowed Outbound**:
- Azure management APIs (management.azure.com)
- Anthropic API (api.anthropic.com)
- Azure Service Bus (for logging)
- Azure Key Vault (for credentials)

**Blocked Outbound**:
- All other internet destinations
- Internal networks (if applicable)

#### 4. Audit Logging

**Logged Events**:
- All service principal creation/deletion
- All role assignments
- All resource creation/deletion
- All API calls to Azure and Anthropic
- All errors and exceptions
- All cleanup operations

**Log Retention**:
- Event Bus messages: 7 days
- Azure Activity Log: 90 days (default)
- Container logs: 30 days

**Log Access**:
- Orchestrator: Read/write
- Monitoring service: Read-only
- Audit system: Read-only

#### 5. Resource Tagging

**Required Tags**:
```bash
AzureHayMaker-managed=true
Scenario=[scenario-id]
Owner=AzureHayMaker
ExecutionId=[unique-execution-id]
CreatedAt=[timestamp]
```

**Purpose**:
- Identify all HayMaker-created resources
- Enable cleanup verification
- Support cost tracking
- Facilitate audit queries

**Enforcement**:
- Scenarios must include tags in all creation commands
- Orchestrator verifies tags present
- Cleanup queries by tag

## Data Flow

### Execution Flow

```mermaid
sequenceDiagram
    participant T as Timer Trigger
    participant O as Orchestrator
    participant KV as Key Vault
    participant SPM as SP Manager
    participant CM as Container Manager
    participant A as Agent
    participant EB as Event Bus
    participant Az as Azure Resources

    T->>O: Trigger (4x daily)
    O->>O: Validate configuration
    O->>KV: Retrieve credentials
    KV-->>O: Return credentials
    O->>O: Select N scenarios
    loop For each scenario
        O->>SPM: Create scenario SP
        SPM-->>O: Return SP credentials
        O->>CM: Deploy agent container
        CM->>A: Start agent
        A->>Az: Phase 1 - Deploy resources
        Az-->>A: Resources created
        A->>EB: Log deployment
        loop Phase 2 - Operations (8 hours)
            A->>Az: Execute operation
            Az-->>A: Operation result
            A->>EB: Log operation
        end
        A->>Az: Phase 3 - Cleanup
        Az-->>A: Resources deleted
        A->>EB: Log cleanup complete
    end
    O->>EB: Retrieve all logs
    EB-->>O: Return logs
    O->>Az: Query tagged resources
    Az-->>O: Return resource list
    O->>Az: Force delete remaining
    O->>SPM: Delete scenario SPs
    O->>O: Generate report
```

### Logging Data Flow

```mermaid
flowchart LR
    A1[Agent 1] --> EB[Event Bus Queue]
    A2[Agent 2] --> EB
    AN[Agent N] --> EB

    EB --> MS[Monitoring Service]
    EB --> OS[Orchestrator]
    EB --> AS[Audit System]

    MS --> API[REST API]
    OS --> CR[Cleanup Reports]
    AS --> AL[Audit Logs]

    API --> User[Operators]
    CR --> User
    AL --> User
```

## On-Demand Execution

In addition to the scheduled execution (4x daily), Azure HayMaker supports on-demand execution via HTTP API. This allows operators to trigger specific scenarios without waiting for the next scheduled run.

### Architecture

```mermaid
graph TB
    Client[CLI/API Client]
    API[HTTP Trigger<br/>POST /execute]
    RateLimiter[Rate Limiter<br/>Token Bucket]
    Tracker[Execution Tracker<br/>Table Storage]
    Queue[Service Bus<br/>execution-requests]
    Processor[Queue Processor]
    Orchestrator[On-Demand<br/>Orchestrator]

    Client -->|1. Submit Request| API
    API -->|2. Check Limits| RateLimiter
    RateLimiter -->|3. Create Record| Tracker
    API -->|4. Enqueue| Queue
    API -->|5. Return execution_id| Client
    Queue -->|6. Dequeue| Processor
    Processor -->|7. Start Execution| Orchestrator
    Orchestrator -->|8. Update Status| Tracker
    Client -->|9. Poll Status| Tracker
```

### Execution Flow

1. **Request Submission**: Client submits execution request via `POST /api/v1/execute` with:
   - `scenarios`: List of scenario names (1-5 scenarios)
   - `duration_hours`: Execution duration (default 8 hours)
   - `tags`: Optional tags for tracking

2. **Validation & Rate Limiting**: API validates:
   - Request format (Pydantic validation)
   - Scenario existence (checks docs/scenarios/)
   - Rate limits (global, per-scenario, per-user)

3. **Queuing**: Request is queued to Service Bus `execution-requests` queue

4. **Processing**: Queue processor:
   - Creates service principals for each scenario
   - Deploys Container Apps
   - Monitors execution for specified duration
   - Verifies cleanup and forces deletion if needed
   - Generates execution report

5. **Status Tracking**: Client can query status via `GET /api/v1/executions/{execution_id}`

### Rate Limiting

Azure HayMaker implements token bucket rate limiting using Table Storage:

- **Global**: 100 executions/hour across all users
- **Per-Scenario**: 10 executions/hour per scenario
- **Per-User**: 20 executions/hour per user (if authentication enabled)

Rate limits reset on a sliding window basis. When exceeded, API returns `429 Too Many Requests` with `Retry-After` header.

### API Endpoints

#### POST /api/v1/execute

Submit on-demand execution request.

**Request**:
```json
{
  "scenarios": ["compute-01-linux-vm-web-server", "networking-01-virtual-network"],
  "duration_hours": 2,
  "tags": {"requester": "admin@example.com"}
}
```

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
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

#### GET /api/v1/executions/{execution_id}

Query execution status.

**Response** (200 OK):
```json
{
  "execution_id": "exec-20251115-abc123",
  "status": "running",
  "scenarios": ["compute-01-linux-vm-web-server"],
  "created_at": "2025-11-15T08:00:00Z",
  "started_at": "2025-11-15T08:05:00Z",
  "progress": {
    "completed": 0,
    "running": 1,
    "failed": 0,
    "total": 1
  },
  "resources_created": 5,
  "container_ids": ["haymaker-compute-01-abc123"]
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

### Security

**Authentication**: On-demand execution API uses Azure Functions authentication:
- **API Key** (default): Function-level key required in `x-functions-key` header
- **Azure AD** (future): OAuth 2.0 bearer tokens for user-level authentication

**Authorization**: Future enhancement will add role-based access control (RBAC) for execution permissions.

### Implementation Details

**Key Modules**:
- `execute_api.py`: HTTP trigger functions for API endpoints
- `execute_processor.py`: Service Bus queue processor
- `execution_tracker.py`: Status tracking in Table Storage
- `rate_limiter.py`: Token bucket rate limiter

**Storage**:
- **Table Storage (Executions)**: Execution status records with history
- **Table Storage (RateLimits)**: Rate limit counters per type/identifier
- **Service Bus (execution-requests)**: Queued execution requests
- **Blob Storage (execution-reports)**: Generated execution reports

## Deployment Model

### Deployment Considerations

The Azure HayMaker architecture is designed to use:
- Azure Functions for orchestration scheduling
- Azure Service Bus for logging infrastructure
- Azure Key Vault for credential management
- Azure Container Apps for isolated scenario execution
- Tag-based resource tracking for cleanup verification

---

## API Endpoints

Azure HayMaker provides HTTP API endpoints for querying status and triggering operations.

### Status Endpoint

**GET /api/v1/status**

Get current orchestrator status.

Response:
```json
{
  "status": "running|idle|error",
  "current_run_id": "run-123",
  "phase": "monitoring",
  "active_agents": 5,
  "next_run": "2025-11-15T18:00:00Z"
}
```

### Metrics Endpoint

**GET /api/v1/metrics**

Get execution metrics and statistics.

Query Parameters:
- `period`: Time period (7d, 30d, 90d) - default: 7d
- `scenario`: Optional scenario filter

Response:
```json
{
  "total_executions": 150,
  "active_agents": 5,
  "total_resources": 234,
  "last_execution": "2025-11-15T10:00:00Z",
  "success_rate": 0.95,
  "period": "7d",
  "scenarios": [
    {
      "scenario_name": "compute-01",
      "run_count": 50,
      "success_count": 48,
      "fail_count": 2,
      "avg_duration_hours": 8.5
    }
  ]
}
```

### Agents Endpoint

**GET /api/v1/agents**

List currently running and recent agents.

Query Parameters:
- `status`: Filter by status (running, completed, failed)
- `limit`: Maximum results (default: 100)

Response:
```json
{
  "agents": [
    {
      "agent_id": "agent-123",
      "scenario": "compute-01",
      "status": "running",
      "started_at": "2025-11-15T08:00:00Z",
      "completed_at": null,
      "progress": "Phase 2: Operations",
      "error": null
    }
  ]
}
```

### Agent Logs Endpoint

**GET /api/v1/agents/{agent_id}/logs**

Get logs for a specific agent.

Query Parameters:
- `tail`: Number of recent entries (default: 100)
- `follow`: Stream logs (not implemented via HTTP)

Response:
```json
{
  "logs": [
    {
      "timestamp": "2025-11-15T08:00:00Z",
      "level": "INFO",
      "message": "Starting scenario execution",
      "agent_id": "agent-123",
      "scenario": "compute-01"
    }
  ]
}
```

### Resources Endpoint

**GET /api/v1/resources**

List all tracked resources.

Query Parameters:
- `execution_id`: Filter by execution ID
- `scenario`: Filter by scenario name
- `status`: Filter by status (created, deleted)
- `limit`: Maximum results (default: 100)

Response:
```json
{
  "resources": [
    {
      "id": "/subscriptions/.../resourceGroups/...",
      "name": "azurehaymaker-compute-...",
      "type": "Microsoft.Compute/virtualMachines",
      "scenario": "compute-01",
      "execution_id": "exec-123",
      "created_at": "2025-11-15T08:30:00Z",
      "deleted_at": null,
      "status": "created",
      "tags": {
        "AzureHayMaker-managed": "true",
        "execution_id": "exec-123"
      }
    }
  ]
}
```

### Execution Endpoint

**POST /api/v1/execute**

Execute a scenario on-demand.

Request:
```json
{
  "scenario_name": "compute-01-linux-vm-web-server",
  "parameters": {}
}
```

Response (202 Accepted):
```json
{
  "execution_id": "exec-456",
  "status": "queued",
  "status_url": "/api/v1/executions/exec-456",
  "created_at": "2025-11-15T10:00:00Z"
}
```

### Execution Status Endpoint

**GET /api/v1/executions/{execution_id}**

Get status of an execution.

Response:
```json
{
  "execution_id": "exec-456",
  "scenario_name": "compute-01",
  "status": "running|completed|failed",
  "created_at": "2025-11-15T10:00:00Z",
  "started_at": "2025-11-15T10:05:00Z",
  "completed_at": null,
  "agent_id": "agent-789",
  "report_url": null,
  "error": null
}
```

### Cleanup Endpoint

**POST /api/v1/cleanup**

Trigger cleanup of resources.

Request:
```json
{
  "execution_id": "exec-123",
  "scenario": null,
  "dry_run": false
}
```

Response:
```json
{
  "cleanup_id": "cleanup-789",
  "status": "running",
  "resources_found": 25,
  "resources_deleted": 0,
  "errors": []
}
```

---

## CLI Client

Azure HayMaker provides a command-line interface for managing operations.

### Installation

```bash
pip install haymaker-cli
```

### Configuration

```bash
haymaker config set endpoint https://haymaker.azurewebsites.net
haymaker config set api-key your-api-key
```

### Commands

- `haymaker status` - Show orchestrator status
- `haymaker metrics` - Show execution metrics
- `haymaker agents list` - List running agents
- `haymaker logs --agent-id <id>` - View agent logs
- `haymaker resources list` - List all resources
- `haymaker deploy --scenario <name>` - Deploy scenario on-demand
- `haymaker cleanup` - Trigger cleanup

For complete CLI documentation, see [CLI_GUIDE.md](CLI_GUIDE.md).

---

## Summary

Azure HayMaker is designed as a robust, secure, and scalable orchestration service for generating benign Azure telemetry. The architecture prioritizes:

1. **Security First**: Ephemeral credentials, least privilege, comprehensive auditing
2. **Complete Cleanup**: Tag-based tracking and forced cleanup verification
3. **Goal-Seeking Agents**: Autonomous error resolution capabilities
4. **Observable Operations**: Comprehensive logging and monitoring at every level
5. **Single Tenant Scope**: All operations constrained to one Azure subscription

For scenario implementation details, see [SCENARIO_MANAGEMENT.md](SCENARIO_MANAGEMENT.md).
For getting started with scenarios, see [GETTING_STARTED.md](GETTING_STARTED.md).
