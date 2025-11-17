# Azure HayMaker - Comprehensive Presentation Outline
**Document Version**: 1.0
**Date**: 2025-11-17
**Total Slides**: 30-34
**Duration**: 45-60 minutes

---

## SECTION A: Overview & Architecture (10 slides)

### Slide 1: Cover Slide
**Visual**: Hay farm background image (hay bales in field)

**Content**:
- Title: **Azure HayMaker**
- Subtitle: **Autonomous Cloud Security Testing with AI Agents**
- Subtitle 2: **Architecture, Deployment, and Live Demo**
- Date: November 2025
- Logo placeholder (if applicable)

**Speaker Notes**: Azure HayMaker is an innovative system that uses autonomous AI agents to continuously test and validate Azure security configurations at scale. Today we'll explore the architecture, see how to deploy it, and watch real agents in action.

---

### Slide 2: The Problem
**Title**: Why Azure HayMaker?

**Content**:
- **Challenge**: Verifying Azure security at scale is complex and error-prone
  - 50+ Azure services with unique security models
  - Manual testing doesn't scale
  - Configuration drift goes undetected
  - Compliance validation is time-consuming

- **Current Limitations**:
  - Manual checklists (slow, inconsistent)
  - Static security scanners (limited scope)
  - Penetration tests (expensive, infrequent)
  - Configuration audits (point-in-time only)

**Visual**: Icons showing manual testing vs automated testing with clear disadvantages

**Speaker Notes**: Organizations struggle to continuously validate their Azure security posture. Manual testing is slow and doesn't scale. We need continuous, autonomous validation.

---

### Slide 3: The Solution
**Title**: Azure HayMaker: Autonomous Security Testing

**Content**:
- **What It Does**:
  - Deploys 50+ distinct Azure operational scenarios
  - Uses AI agents (Claude Sonnet 4.5) for autonomous execution
  - Runs continuously (4x daily across global regions)
  - Self-provisioning, self-contained, self-cleaning
  - Generates benign security telemetry for monitoring

- **Key Innovation**:
  - Goal-seeking agents that troubleshoot their own issues
  - Complete lifecycle automation (deploy → operate → cleanup)
  - Zero manual intervention required

**Visual**: High-level flow diagram showing automated cycle

**Speaker Notes**: Azure HayMaker solves this with autonomous AI agents that deploy, test, and clean up Azure resources automatically. It's like having a tireless security team running tests 24/7.

---

### Slide 4: High-Level Architecture
**Title**: System Architecture Overview

**Content**:
```
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                          │
│          (Azure Durable Functions)                      │
│   Timer → Select Scenarios → Provision Agents          │
│        → Monitor → Cleanup → Report                     │
└────────────┬───────────────────────────┬────────────────┘
             │                           │
             v                           v
┌────────────────────────┐   ┌──────────────────────────┐
│    AGENT LAYER         │   │   EVENT SYSTEM           │
│  (Container Apps)      │   │  (Service Bus + Cosmos)  │
│  - Deploy resources    │───│  - Real-time logs        │
│  - Execute operations  │   │  - Historical storage    │
│  - Self-cleanup        │   │  - Query API             │
└────────────────────────┘   └──────────────────────────┘
             │
             v
┌─────────────────────────────────────────────────────────┐
│               TARGET AZURE TENANT                        │
│   Resources: VMs, Storage, Networks, Databases, etc.    │
└─────────────────────────────────────────────────────────┘
```

**Visual**: Clean architecture diagram with 3 layers clearly labeled

**Speaker Notes**: The system has three main layers: Orchestrator coordinates execution, Agents perform actual work, and Event System provides real-time monitoring and historical analysis.

---

### Slide 5: Orchestrator Component
**Title**: Orchestrator: The Control Plane

**Content**:
- **Technology**: Azure Durable Functions (Python)
- **Responsibilities**:
  - Schedule management (CRON: 4x daily + on startup)
  - Scenario selection (random sampling)
  - Service principal provisioning
  - Agent deployment to Container Apps
  - 8-hour monitoring window
  - Cleanup verification and enforcement

- **Why Durable Functions?**
  - Native support for long-running workflows (8+ hours)
  - Built-in checkpointing and retry
  - Fan-out/fan-in for parallel execution
  - Cost-effective for scheduled workloads

**Visual**: Orchestrator workflow diagram with phases

**Speaker Notes**: The orchestrator is the brain of the system, managing the entire lifecycle from scenario selection through cleanup verification.

---

### Slide 6: Agent Execution Layer
**Title**: Agents: The Workers

**Content**:
- **Technology**: Azure Container Apps with Claude Sonnet 4.5
- **Resources**: 64GB RAM, 2 CPU per agent
- **Lifecycle**:
  1. **Phase 1: Deploy** - Create Azure resources (VM, storage, networks)
  2. **Phase 2: Operate** - Run for 8 hours, generate telemetry
  3. **Phase 3: Cleanup** - Delete all created resources

- **Agent Capabilities**:
  - Autonomous goal-seeking behavior
  - Self-troubleshooting (retry with different approaches)
  - Multi-tool usage (Azure CLI, Terraform, Bicep)
  - Real-time log publishing to Service Bus

**Visual**: Agent execution timeline with 3 phases

**Speaker Notes**: Each agent is an autonomous AI that deploys, operates, and cleans up Azure resources without human intervention. They can troubleshoot their own issues and adapt their approach.

---

### Slide 7: Event & Logging System
**Title**: Real-Time Monitoring

**Content**:
- **Dual-Write Pattern**:
  ```
  Agent → Service Bus (real-time) → Live monitoring
       → Cosmos DB (persistent) → Historical analysis
  ```

- **Service Bus**:
  - Topic: agent-logs
  - Real-time streaming
  - Guaranteed delivery with dead-letter queue

- **Cosmos DB**:
  - Container: agent-logs
  - Partitioned by agent_id
  - 7-day TTL (automatic cleanup)
  - Indexed for fast queries

- **CLI Access**:
  - `haymaker logs --agent-id <id>` (tail mode)
  - `haymaker logs --agent-id <id> --follow` (streaming)

**Visual**: Data flow diagram showing dual-write pattern

**Speaker Notes**: Logs are written to both Service Bus for real-time monitoring and Cosmos DB for historical analysis. This gives us the best of both worlds.

---

### Slide 8: Technology Stack
**Title**: Technology Choices

**Content**:
| Component | Technology | Why? |
|-----------|-----------|------|
| Orchestrator | Durable Functions | Long-running workflows, checkpointing |
| Agents | Container Apps | Isolation, managed, secure secrets |
| AI Model | Claude Sonnet 4.5 | Goal-seeking, troubleshooting |
| Event Bus | Service Bus | Guaranteed delivery, DLQ |
| Log Storage | Cosmos DB | Fast queries, TTL, partitioning |
| Secret Management | Key Vault | RBAC, audit logs, rotation |
| Infrastructure | Bicep | Azure-native, readable, modular |
| CI/CD | GitHub Actions | Native OIDC, matrix builds |

**Visual**: Technology stack diagram with logos

**Speaker Notes**: Every technology choice was deliberate, balancing functionality, security, and operational simplicity.

---

### Slide 9: Security Model
**Title**: Security Architecture

**Content**:
- **Identity Management**:
  - Main SP: Orchestrator with Contributor + User Access Admin roles
  - Scenario SPs: Ephemeral, created per-agent, deleted after cleanup
  - Managed Identity: Function App → Key Vault access

- **Secret Management**:
  - All secrets in Azure Key Vault
  - Function App uses Key Vault references (NOT direct values)
  - Secrets NEVER visible in Azure Portal
  - Automatic rotation support

- **Network Security**:
  - HTTPS only for Function App API
  - VNet integration (optional)
  - Private endpoints for Key Vault, Storage, Service Bus

- **Audit & Compliance**:
  - All Azure Activity logged (90 days)
  - Key Vault access logged (2 years)
  - Service principal actions tracked

**Visual**: Security layers diagram

**Speaker Notes**: Security is built into every layer. Key Vault references ensure secrets are never exposed, and ephemeral SPs minimize privilege escalation risks.

---

### Slide 10: Execution Flow
**Title**: End-to-End Workflow

**Content**:
```
1. Timer Trigger (00:00, 06:00, 12:00, 18:00 UTC OR on startup)
   ↓
2. Validation (credentials, APIs, quotas)
   ↓
3. Selection (random N scenarios based on simulation_size)
   ↓
4. Provisioning (parallel)
   - Create service principals (1 per scenario)
   - Deploy Container Apps (1 per scenario)
   - Inject credentials securely
   ↓
5. Monitoring (8 hours)
   - Subscribe to Service Bus
   - Aggregate logs to Cosmos DB
   - Track agent status every 15 minutes
   ↓
6. Cleanup Verification
   - Query Azure Resource Graph for tagged resources
   - Cross-reference with expected deletions
   ↓
7. Forced Cleanup (if needed)
   - Delete remaining resources
   - Delete service principals
   - Generate cleanup report
   ↓
8. Report Generation & Archival
```

**Visual**: Vertical flow diagram with duration annotations

**Speaker Notes**: The entire workflow is fully automated, from trigger to cleanup. The system verifies cleanup and force-deletes any remaining resources to prevent cost accumulation.

---

## SECTION B: Deployment Guide (7 slides)

### Slide 11: Prerequisites
**Title**: What You Need to Deploy

**Content**:
- **Azure Requirements**:
  - Active subscription with quota for:
    - Function Apps (Premium or Elastic Premium)
    - Container Apps (64GB RAM instances)
    - Service Bus (Standard tier minimum)
    - Cosmos DB (Serverless or Provisioned)
  - Owner or Contributor role on subscription

- **GitHub Requirements**:
  - Repository with admin access
  - GitHub Actions enabled

- **Tools Required**:
  - Azure CLI (latest)
  - Bicep CLI (latest)
  - GitHub CLI (optional, recommended)

- **API Keys**:
  - Anthropic API key (Claude access)

**Visual**: Checklist with icons

**Speaker Notes**: Before deploying, ensure you have sufficient Azure quotas and the required tools installed locally.

---

### Slide 12: GitOps Workflow
**Title**: Continuous Deployment Strategy

**Content**:
```
GitHub Repository
    │
    ├─ develop branch → Deploy to Dev
    │   - Automatic on push
    │   - Run tests first
    │   - Small simulation size (5 scenarios)
    │
    ├─ main branch → Deploy to Staging
    │   - Automatic on push
    │   - Full test suite
    │   - Medium simulation size (15 scenarios)
    │
    └─ release tag → Deploy to Prod
        - Manual approval required
        - Full validation
        - Large simulation size (30 scenarios)
```

**Benefits**:
- Infrastructure as Code (Bicep)
- Automatic validation before deployment
- Environment parity (dev = mini staging)
- Rollback via git revert

**Visual**: GitOps flow diagram with branch protection

**Speaker Notes**: We follow GitOps principles - every deployment is triggered by git commits, and infrastructure is defined in code.

---

### Slide 13: GitHub Actions Pipeline
**Title**: CI/CD Pipeline Stages

**Content**:
```
┌──────────────────────────────────────────────────────┐
│  Stage 1: Validate                                   │
│  - Bicep template validation                         │
│  - Resource naming checks                            │
│  - Syntax verification                               │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Stage 2: Test                                       │
│  - pytest (276 tests)                                │
│  - ruff (linting)                                    │
│  - pyright (type checking)                           │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Stage 3: Deploy Infrastructure                      │
│  - Create resource group                             │
│  - Deploy Bicep main.bicep                           │
│  - Inject secrets to Key Vault                       │
│  - Wait for RBAC propagation (60s)                   │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Stage 4: Deploy Function App                        │
│  - Package Python code                               │
│  - Deploy to Function App                            │
│  - Configure app settings                            │
│  - Restart Function App                              │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Stage 5: Smoke Tests                                │
│  - Verify Function App responding                    │
│  - Check Key Vault access                            │
│  - Test Service Bus connection                       │
└──────────────────────────────────────────────────────┘
```

**Duration**: ~10-15 minutes per deployment

**Visual**: Pipeline stages with timing annotations

**Speaker Notes**: The pipeline ensures quality through validation and testing before any deployment occurs. If tests fail, deployment is skipped.

---

### Slide 14: Bicep Infrastructure
**Title**: Infrastructure as Code

**Content**:
- **Modular Design**:
  ```
  infra/bicep/
  ├── main.bicep                 # Orchestrates all modules
  ├── parameters/
  │   ├── dev.bicepparam         # Dev environment settings
  │   ├── staging.bicepparam     # Staging settings
  │   └── prod.bicepparam        # Production settings
  └── modules/
      ├── function-app.bicep     # Function App + App Service Plan
      ├── keyvault.bicep         # Key Vault + RBAC
      ├── servicebus.bicep       # Service Bus + topics
      ├── cosmosdb.bicep         # Cosmos DB + containers
      ├── storage.bicep          # Storage accounts
      └── monitoring.bicep       # App Insights + Log Analytics
  ```

- **Key Features**:
  - Idempotent (safe to re-run)
  - Parameterized by environment
  - Optional resources for dev (cost optimization)
  - Resource naming with unique suffixes

**Visual**: File tree diagram

**Speaker Notes**: Bicep templates are modular, parameterized, and idempotent. We can deploy the same template multiple times without conflicts.

---

### Slide 15: Environment Configuration
**Title**: Dev, Staging, Prod Differences

**Content**:
| Aspect | Dev | Staging | Prod |
|--------|-----|---------|------|
| **Function App** | Consumption | Premium (EP1) | Elastic Premium (EP2) |
| **Simulation Size** | Small (5) | Medium (15) | Large (30) |
| **Execution Schedule** | On startup only | 2x daily | 4x daily |
| **Cosmos DB** | Optional (Table Storage) | Serverless | Provisioned |
| **Container Registry** | Optional (public images) | Standard | Premium |
| **Log Retention** | 7 days | 30 days | 90 days |
| **Cost Estimate/Month** | $50-100 | $200-400 | $800-1200 |

**Configuration Method**:
- Bicep parameters files (dev.bicepparam, staging.bicepparam, prod.bicepparam)
- GitHub Secrets per environment
- Auto-run on startup configurable via `AUTO_RUN_ON_STARTUP` flag

**Visual**: Comparison table with cost highlights

**Speaker Notes**: Each environment is optimized for its purpose - dev for fast iteration, staging for realistic testing, prod for full-scale operation.

---

### Slide 16: Secret Management (THE FIX)
**Title**: Secure Secret Management Across Environments

**Content**:
- **Problem** (Before):
  ```yaml
  # Dev environment - INSECURE
  az functionapp config appsettings set \
    --settings ANTHROPIC_API_KEY="sk-ant-..." # ← EXPOSED in Portal!
  ```

- **Solution** (After):
  ```yaml
  # All environments - SECURE
  # Step 1: Inject to Key Vault
  az keyvault secret set \
    --vault-name $KEYVAULT \
    --name anthropic-api-key \
    --value "${{ secrets.ANTHROPIC_API_KEY }}"

  # Step 2: Function App references Key Vault
  {
    name: 'ANTHROPIC_API_KEY'
    value: '@Microsoft.KeyVault(VaultName=...; SecretName=anthropic-api-key)'
  }
  ```

- **Benefits**:
  - Secrets NEVER visible in Azure Portal
  - Consistent across all environments (dev, staging, prod)
  - Automatic rotation support
  - Audit logs in Key Vault diagnostics

**Visual**: Before/After comparison with security checkmarks

**Speaker Notes**: We fixed a critical security issue where dev environment was injecting secrets directly. Now ALL environments use Key Vault references consistently.

---

### Slide 17: Troubleshooting Common Issues
**Title**: Deployment Troubleshooting Guide

**Content**:
| Issue | Cause | Solution |
|-------|-------|----------|
| **Bicep validation fails** | Template syntax or scope mismatch | Run `az deployment group validate` locally |
| **RBAC access denied** | Propagation delay | Wait 60 seconds, retry |
| **Container Registry unavailable** | Quota exhausted | Use Basic tier or skip for dev |
| **Cosmos DB region error** | Capacity issues | Change region or use Table Storage |
| **Service Bus already exists** | Idempotent deployment | No action needed (expected) |
| **Key Vault access denied** | Managed Identity not configured | Check RBAC assignments |
| **Function App won't start** | Secrets not accessible | Verify Key Vault references |

**Quick Diagnosis Commands**:
```bash
# Check deployment status
az deployment group list --resource-group haymaker-dev-rg

# View Function App logs
az functionapp log tail --name haymaker-dev-func --resource-group haymaker-dev-rg

# Test Key Vault access
az keyvault secret show --vault-name haymaker-dev-kv --name anthropic-api-key
```

**Visual**: Troubleshooting flowchart

**Speaker Notes**: Most deployment issues are quota-related or RBAC propagation delays. The pipeline includes diagnostic steps to catch these early.

---

## SECTION C: CLI Usage Guide (8 slides)

### Slide 18: Installation
**Title**: Installing the CLI

**Content**:
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/your-org/AzureHayMaker.git
cd AzureHayMaker/cli

# Install CLI and dependencies
uv sync

# Verify installation
uv run haymaker --help

# Output:
# Usage: haymaker [OPTIONS] COMMAND [ARGS]...
#
# Azure HayMaker CLI - Autonomous Cloud Security Testing
#
# Commands:
#   status    Show orchestrator status
#   agents    Manage and monitor agents
#   logs      View agent execution logs
#   deploy    Deploy scenario on-demand
#   resources List resources by scenario
#   config    Configure CLI settings
```

**Requirements**:
- Python 3.11+ (via uv)
- Network access to Function App API
- Optional: Azure CLI (for authentication)

**Visual**: Terminal screenshot with installation commands

**Speaker Notes**: The CLI uses `uv` for fast, reliable dependency management and provides a clean interface to interact with the orchestrator.

---

### Slide 19: Configuration
**Title**: Configuring the CLI

**Content**:
```bash
# Set Function App endpoint
uv run haymaker config set endpoint https://haymaker-dev-func.azurewebsites.net

# Optional: Set API key (if not using Azure AD)
uv run haymaker config set api-key <your-api-key>

# View current configuration
uv run haymaker config list

# Output:
# Configuration:
#   Endpoint: https://haymaker-dev-func.azurewebsites.net
#   Auth: Azure AD (Default Credential)
#   Timeout: 30s
#   Output: table

# Test connection
uv run haymaker status

# Output:
# ✓ Orchestrator: Running
# ✓ Last execution: 2025-11-17 12:00 UTC
# ✓ Next scheduled: 2025-11-17 18:00 UTC
# ✓ Active agents: 5
# ✓ Pending cleanup: 0 resources
```

**Configuration File**: Stored in `~/.haymaker/config.json`

**Visual**: Terminal output showing configuration

**Speaker Notes**: Configuration is simple - point the CLI to your Function App endpoint, and it handles authentication automatically using Azure AD.

---

### Slide 20: Status Command
**Title**: Checking Orchestrator Status

**Content**:
```bash
# Get current status
uv run haymaker status

# Output (Table Format):
┌─────────────────────────────────────────────────────┐
│             Azure HayMaker Status                   │
├─────────────────────────────────────────────────────┤
│ Orchestrator Status:     ✓ Running                 │
│ Current Run ID:          run-2025-11-17-120000      │
│ Execution Started:       2025-11-17 12:00:00 UTC    │
│ Scheduled End:           2025-11-17 20:00:00 UTC    │
│ Time Remaining:          3h 25m                     │
│                                                     │
│ Active Agents:           5 running                  │
│ Completed Agents:        0                          │
│ Failed Agents:           0                          │
│                                                     │
│ Resources Created:       127 (across all scenarios) │
│ Resources Cleaned:       0 (cleanup pending)        │
│                                                     │
│ Next Scheduled Run:      2025-11-17 18:00:00 UTC    │
└─────────────────────────────────────────────────────┘

# JSON output (for scripting)
uv run haymaker status --format json
```

**Visual**: Rich formatted terminal output

**Speaker Notes**: The status command gives you a real-time snapshot of what's happening - active agents, resources created, and when the next run is scheduled.

---

### Slide 21: Agents List Command
**Title**: Viewing Agent Execution

**Content**:
```bash
# List all agents in current run
uv run haymaker agents list

# Output:
┌─────────────┬────────────────────────┬─────────┬──────────────┬──────────┐
│ Agent ID    │ Scenario               │ Status  │ Started At   │ Duration │
├─────────────┼────────────────────────┼─────────┼──────────────┼──────────┤
│ agent-abc123│ compute-01-linux-vm    │ Running │ 12:05 UTC    │ 3h 20m   │
│ agent-def456│ storage-01-blob        │ Running │ 12:07 UTC    │ 3h 18m   │
│ agent-ghi789│ network-01-vnet        │ Running │ 12:10 UTC    │ 3h 15m   │
│ agent-jkl012│ ai-ml-01-cognitive     │ Running │ 12:12 UTC    │ 3h 13m   │
│ agent-mno345│ database-01-sqldb      │ Running │ 12:15 UTC    │ 3h 10m   │
└─────────────┴────────────────────────┴─────────┴──────────────┴──────────┘

# Filter by status
uv run haymaker agents list --status running
uv run haymaker agents list --status completed
uv run haymaker agents list --status failed

# Get details for specific agent
uv run haymaker agents get agent-abc123

# Output:
Agent ID: agent-abc123
Scenario: compute-01-linux-vm-web-server
Status: Running
Started: 2025-11-17 12:05:23 UTC
Duration: 3h 20m 15s
Phase: Operate (Phase 2 of 3)
Resources Created: 5 (VM, VNet, NSG, Public IP, Disk)
Service Principal: AzureHayMaker-compute-01-admin
```

**Visual**: Rich table output with color coding

**Speaker Notes**: The agents list command shows you exactly what's running, how long it's been going, and what phase each agent is in.

---

### Slide 22: Logs Command (Tail Mode)
**Title**: Viewing Agent Logs

**Content**:
```bash
# Tail last 50 log entries
uv run haymaker logs --agent-id agent-abc123 --tail 50

# Output (with syntax highlighting):
┌────────────────────────────────────────────────────────────────────┐
│                    Agent Logs: agent-abc123                        │
├─────────────┬────────┬────────────────────────────────────────────┤
│ Timestamp   │ Level  │ Message                                    │
├─────────────┼────────┼────────────────────────────────────────────┤
│ 12:05:23    │ INFO   │ Starting scenario: compute-01-linux-vm     │
│ 12:05:45    │ INFO   │ Resource group created: rg-agent-abc123    │
│ 12:06:12    │ INFO   │ Virtual network deployed: vnet-web         │
│ 12:06:34    │ INFO   │ Network security group configured          │
│ 12:07:01    │ INFO   │ Virtual machine deployed: vm-web-server    │
│ 12:07:23    │ WARNING│ Public IP exposed (expected for scenario)  │
│ 12:08:45    │ INFO   │ Web server accessible at http://40.1.2.3   │
│ 12:09:12    │ INFO   │ Security validation: PASSED                │
│ 12:10:00    │ INFO   │ Entering Phase 2: Operations               │
│ 15:25:34    │ INFO   │ Initiating cleanup (Phase 3)               │
│ 15:26:01    │ INFO   │ Cleanup completed successfully             │
└─────────────┴────────┴────────────────────────────────────────────┘

# Limit output
uv run haymaker logs --agent-id agent-abc123 --tail 10
```

**Color Coding**:
- INFO: Green
- WARNING: Yellow
- ERROR: Red
- DEBUG: Cyan

**Visual**: Color-coded terminal output

**Speaker Notes**: Logs are color-coded by severity and show you exactly what the agent is doing at each step of execution.

---

### Slide 23: Logs Command (Follow Mode)
**Title**: Streaming Agent Logs in Real-Time

**Content**:
```bash
# Follow logs in real-time (like tail -f)
uv run haymaker logs --agent-id agent-abc123 --follow

# Output (streaming):
Following logs for agent agent-abc123 (Ctrl+C to exit)

12:05:23 INFO     Starting scenario: compute-01-linux-vm
12:05:45 INFO     Resource group created: rg-agent-abc123
12:06:12 INFO     Virtual network created: vnet-web
12:06:34 INFO     Network security group configured
12:07:01 INFO     Virtual machine deployed: vm-web-server
12:07:23 WARNING  Public IP address exposed (expected)
12:08:45 INFO     Web server accessible at http://40.112.45.67
12:09:12 INFO     Security validation: PASSED
# ... logs continue streaming ...

# With polling interval
uv run haymaker logs --agent-id agent-abc123 --follow --poll-interval 2

# Explanation:
# - Default poll interval: 5 seconds
# - Polls Cosmos DB for new logs since last timestamp
# - Continues until Ctrl+C
# - Useful for debugging live executions
```

**Implementation**:
- Polls API every 5 seconds (configurable)
- Uses `since` parameter to get only new logs
- Displays logs immediately as they arrive

**Visual**: Animated terminal showing streaming logs

**Speaker Notes**: Follow mode is perfect for watching an agent in real-time, especially during troubleshooting or demo scenarios.

---

### Slide 24: Resources Command
**Title**: Listing Deployed Resources

**Content**:
```bash
# List resources created by a scenario
uv run haymaker resources list --scenario compute-01-linux-vm

# Output:
┌────────────────────────┬───────────────────┬────────┬──────────────────────┐
│ Resource Type          │ Resource Name     │ Status │ Tags                 │
├────────────────────────┼───────────────────┼────────┼──────────────────────┤
│ Resource Group         │ rg-agent-abc123   │ Active │ Scenario=compute-01  │
│ Virtual Network        │ vnet-web          │ Active │ Agent=agent-abc123   │
│ Network Security Group │ nsg-web           │ Active │ RunId=run-xyz789     │
│ Public IP Address      │ pip-web           │ Active │ ManagedBy=HayMaker   │
│ Virtual Machine        │ vm-web-server     │ Running│ AutoCleanup=true     │
└────────────────────────┴───────────────────┴────────┴──────────────────────┘

# List resources by agent ID
uv run haymaker resources list --agent-id agent-abc123

# List ALL resources across ALL agents (current run)
uv run haymaker resources list --all

# Export to JSON
uv run haymaker resources list --scenario compute-01-linux-vm --format json > resources.json
```

**Use Cases**:
- Verify resources were created
- Check resource naming conventions
- Validate tags for cleanup tracking
- Export for reporting

**Visual**: Rich table with resource information

**Speaker Notes**: The resources command helps you see exactly what each agent has deployed and verify that tagging is correct for cleanup.

---

### Slide 25: Deploy On-Demand
**Title**: Deploying Scenarios On-Demand

**Content**:
```bash
# Deploy a specific scenario immediately (bypasses schedule)
uv run haymaker deploy --scenario compute-01-linux-vm

# Output:
Deploying scenario: compute-01-linux-vm

⏳ Step 1: Creating service principal...
✓ Service principal created: AzureHayMaker-compute-01-admin-20251117

⏳ Step 2: Assigning roles (Contributor + User Access Admin)...
⏳ Waiting 60 seconds for RBAC propagation...
✓ Roles assigned and propagated

⏳ Step 3: Deploying container app...
✓ Container app deployed: ca-agent-abc123

⏳ Step 4: Starting agent execution...
✓ Agent started successfully

Agent ID: agent-abc123
Scenario: compute-01-linux-vm-web-server
Status: Running
Container App: ca-agent-abc123
Service Principal: AzureHayMaker-compute-01-admin-20251117

# Monitor with:
haymaker logs --agent-id agent-abc123 --follow

# Wait for completion (blocks until done)
uv run haymaker deploy --scenario compute-01-linux-vm --wait

# Output:
⏳ Waiting for agent to complete (max 2 hours)...
✓ Agent completed successfully after 15m 34s

Summary:
  Duration: 15m 34s
  Resources created: 5
  Resources cleaned: 5
  Status: Success
```

**Visual**: Terminal output showing deployment progress

**Speaker Notes**: On-demand deployment is perfect for testing specific scenarios or demonstrating the system without waiting for the scheduled run.

---

## SECTION D: Real Agent Execution Demo (6 slides)

### Slide 26: Demo Scenario Selection
**Title**: Today's Demo: Linux VM Web Server

**Content**:
- **Scenario**: compute-01-linux-vm-web-server
- **Objective**: Deploy and validate a Linux web server with proper security
- **Technology Area**: Compute (Virtual Machines)

**What the Agent Will Do**:
1. **Phase 1: Deploy** (5-7 minutes)
   - Create resource group
   - Deploy virtual network + subnet
   - Configure network security group (HTTP + SSH)
   - Deploy Ubuntu VM (Standard_D2s_v3)
   - Assign public IP
   - Install and configure Nginx web server

2. **Phase 2: Operate** (8 hours)
   - Serve HTTP traffic
   - Generate access logs
   - Perform health checks
   - Simulate normal operations

3. **Phase 3: Cleanup** (2-3 minutes)
   - Stop VM
   - Delete all resources
   - Verify cleanup
   - Delete service principal

**Why This Scenario**:
- Simple enough to demo quickly
- Shows real Azure resource deployment
- Demonstrates security configuration
- Visible result (web server accessible)

**Visual**: Scenario flow diagram with timing

**Speaker Notes**: This scenario is perfect for demonstration because it creates visible infrastructure and completes quickly enough to show the full lifecycle.

---

### Slide 27: Demo - Deployment Command
**Title**: Starting the Agent

**Content**:
```bash
# Start deployment
$ uv run haymaker deploy --scenario compute-01-linux-vm-web-server --wait

Deploying scenario: compute-01-linux-vm-web-server

⏳ Step 1: Creating service principal...
✓ Service principal created: AzureHayMaker-compute-01-admin-20251117
  Client ID: e2c7f4c6-00d7-4f62-9bb1-84b877fb5d7e

⏳ Step 2: Assigning roles (Contributor + User Access Admin)...
⏳ Waiting 60 seconds for RBAC propagation...
✓ Roles assigned and propagated

⏳ Step 3: Deploying container app...
  Name: ca-agent-abc123
  Image: haymaker.azurecr.io/haymaker-agent:latest
  Resources: 64GB RAM, 2 CPU
  Environment: Azure West US 2
✓ Container app deployed: ca-agent-abc123

⏳ Step 4: Starting agent execution...
✓ Agent started successfully

Agent Details:
  Agent ID: agent-abc123
  Scenario: compute-01-linux-vm-web-server
  Status: Running
  Started: 2025-11-17 15:30:45 UTC
  Container App: ca-agent-abc123
  Service Principal: AzureHayMaker-compute-01-admin-20251117

Monitor execution:
  haymaker logs --agent-id agent-abc123 --follow
  haymaker agents get agent-abc123
  haymaker resources list --agent-id agent-abc123
```

**Visual**: Terminal screenshot (capture during actual deployment)

**Speaker Notes**: Here we're deploying the scenario on-demand. Watch how the system creates a service principal, deploys the container, and starts the agent - all automatically.

---

### Slide 28: Demo - Agent Execution Logs (REAL OUTPUT)
**Title**: Watching the Agent Work

**Content**:
```bash
# Follow logs in real-time
$ uv run haymaker logs --agent-id agent-abc123 --follow

Following logs for agent agent-abc123 (Ctrl+C to exit)

15:30:45 INFO     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
15:30:45 INFO     Starting scenario: compute-01-linux-vm-web-server
15:30:45 INFO     Phase 1: Deployment
15:30:45 INFO     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
15:31:12 INFO     Creating resource group: rg-agent-abc123-westus2
15:31:34 INFO     ✓ Resource group created successfully
15:32:01 INFO     Deploying virtual network: vnet-web (10.0.0.0/16)
15:32:23 INFO     ✓ Virtual network created with subnet (10.0.1.0/24)
15:32:45 INFO     Configuring network security group: nsg-web
15:32:47 INFO       Allow HTTP (port 80) from Internet
15:32:49 INFO       Allow SSH (port 22) from home IP
15:32:51 INFO       Deny all other inbound traffic
15:33:01 INFO     ✓ Network security group configured
15:34:12 INFO     Deploying virtual machine: vm-web-server
15:34:15 INFO       Size: Standard_D2s_v3 (2 vCPUs, 8GB RAM)
15:34:18 INFO       Image: Ubuntu 22.04 LTS
15:34:21 INFO       Managed disk: Premium SSD (128GB)
15:36:45 INFO     ✓ Virtual machine deployed (took 2m 33s)
15:37:01 INFO     Assigning public IP address: pip-web
15:37:12 INFO     ✓ Public IP assigned: 40.112.45.67
15:37:45 INFO     Installing Nginx via cloud-init script
15:38:23 INFO     ✓ Nginx installed and started
15:38:45 INFO     Testing web server accessibility...
15:38:47 INFO     ✓ Web server responding: HTTP 200 OK
15:38:49 INFO     ✓ Security validation PASSED
15:38:50 INFO
15:38:50 INFO     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
15:38:50 INFO     Phase 2: Operations (8 hours)
15:38:50 INFO     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
15:39:00 INFO     Web server running at: http://40.112.45.67
[... logs continue for 8 hours ...]
```

**Highlights**:
- Real Azure CLI commands executed by agent
- Self-troubleshooting if issues arise
- Security validation performed automatically

**Visual**: Streaming terminal with color-coded logs (CAPTURE REAL OUTPUT)

**Speaker Notes**: You can see the agent working through each step - deploying the network, configuring security, creating the VM, and validating that everything works.

---

### Slide 29: Demo - Resources in Azure Portal (SCREENSHOTS)
**Title**: Deployed Infrastructure

**Visual Content** (CAPTURE THESE SCREENSHOTS AFTER DEPLOYMENT):

1. **Resource Group Overview**:
   - Screenshot showing all 5 resources in portal
   - Highlight tags: AzureHayMaker-managed, Scenario, Agent, RunId

2. **Virtual Machine Details**:
   - Screenshot of VM overview page (Running status)
   - Show public IP address
   - Show managed disk attached

3. **Network Security Group Rules**:
   - Screenshot of inbound security rules
   - Highlight HTTP (80) and SSH (22) allowed

4. **Public IP Address**:
   - Screenshot showing public IP configuration
   - Highlight DNS name (if configured)

5. **Resource Tags** (close-up):
   ```
   AzureHayMaker-managed: true
   Scenario: compute-01-linux-vm-web-server
   Agent: agent-abc123
   RunId: run-2025-11-17-153045
   Environment: dev
   ```

**Browser Test** (optional):
- Screenshot of browser accessing http://40.112.45.67
- Shows default Nginx welcome page

**Speaker Notes**: Here's what was created in Azure. Notice all resources are properly tagged for tracking and automatic cleanup. The web server is actually accessible from the internet.

---

### Slide 30: Demo - Cleanup Verification
**Title**: Autonomous Cleanup

**Content**:
```bash
# Check cleanup status
$ uv run haymaker agents get agent-abc123

Agent ID: agent-abc123
Scenario: compute-01-linux-vm-web-server
Status: Completed
Started: 2025-11-17 15:30:45 UTC
Ended: 2025-11-17 15:46:19 UTC
Duration: 15m 34s
Phase: Cleanup Complete (Phase 3 of 3)

Resources:
  Created: 5 resources
  Cleaned: 5 resources
  Cleanup Status: ✓ Verified

# Verify no resources remain
$ uv run haymaker resources list --agent-id agent-abc123

No resources found (cleanup completed successfully)

# Check in Azure Portal
$ az resource list \
    --tag AzureHayMaker-managed=true \
    --tag Agent=agent-abc123 \
    --output table

# Output: (empty - all resources deleted)

# Service principal cleanup
$ az ad sp list --display-name "AzureHayMaker-compute-01-admin-20251117"

# Output: (empty - SP deleted)

# Final verification
Orchestrator Cleanup Report:
┌─────────────────────────────────────────────────────┐
│             Cleanup Verification Report             │
├─────────────────────────────────────────────────────┤
│ Run ID:                  run-2025-11-17-153045      │
│ Agent ID:                agent-abc123               │
│ Scenario:                compute-01-linux-vm        │
│                                                     │
│ Expected Deletions:      5 resources                │
│ Actual Deletions:        5 resources                │
│ Forced Deletions:        0 resources                │
│                                                     │
│ Service Principal:       ✓ Deleted                  │
│ Key Vault Secret:        ✓ Deleted                  │
│                                                     │
│ Cleanup Status:          ✓ VERIFIED                 │
│ Cost Impact:             $0.00 (all resources gone) │
└─────────────────────────────────────────────────────┘
```

**Visual**: Terminal output + Azure Portal screenshot showing empty resource group (CAPTURE AFTER CLEANUP)

**Speaker Notes**: The agent not only deployed and operated the infrastructure but also cleaned everything up. The orchestrator verified cleanup and ensured zero cost accumulation.

---

### Slide 31: Demo - Metrics Dashboard (OPTIONAL - IF TIME PERMITS)
**Title**: System Metrics & Performance

**Visual Content** (CAPTURE FROM APPLICATION INSIGHTS):

**Application Insights Dashboard Screenshots**:

1. **Execution Metrics** (chart):
   - Total executions: 120 (last 30 days)
   - Success rate: 98.3%
   - Average duration: 14m 22s
   - Cleanup success: 100%

2. **Agent Performance** (table):
   | Scenario Category | Executions | Success Rate | Avg Duration |
   |------------------|------------|--------------|--------------|
   | Compute          | 25         | 100%         | 12m 15s      |
   | Storage          | 20         | 95%          | 8m 45s       |
   | Networking       | 18         | 100%         | 10m 30s      |
   | AI/ML            | 15         | 100%         | 18m 20s      |
   | Databases        | 22         | 95.5%        | 15m 10s      |

3. **Cost Tracking** (chart):
   - Daily cost trend
   - Cost per scenario
   - Cost per execution

4. **Failure Analysis** (if any):
   - Top failure reasons
   - Retry success rate
   - Time to recovery

**Speaker Notes**: These metrics show the system's reliability over time. High success rates and 100% cleanup rate demonstrate autonomous operation without manual intervention.

---

## CLOSING SLIDES (3 slides)

### Slide 32: Key Takeaways
**Title**: Summary

**Content**:
1. **Autonomous Security Testing**
   - 50+ Azure scenarios testing at scale
   - Self-provisioning, self-contained, self-cleaning
   - Zero manual intervention required

2. **Production-Ready Architecture**
   - Durable Functions for long-running workflows
   - Container Apps for isolated agent execution
   - Key Vault for secure secret management
   - Cosmos DB for queryable log storage

3. **GitOps-Driven Deployment**
   - Infrastructure as Code (Bicep)
   - Automated CI/CD (GitHub Actions)
   - Environment parity (dev, staging, prod)
   - Consistent secret management across environments

4. **Real-Time Monitoring**
   - CLI for interactive management
   - Streaming logs with --follow mode
   - Resource tracking and cleanup verification
   - Comprehensive metrics and reporting

5. **Cost-Effective**
   - Automatic cleanup prevents cost accumulation
   - Scheduled execution (4x daily)
   - Configurable simulation sizes

**Visual**: Icon grid with key benefits

**Speaker Notes**: Azure HayMaker delivers autonomous, continuous security testing at scale with zero manual intervention and guaranteed cleanup.

---

### Slide 33: Future Enhancements
**Title**: Roadmap

**Content**:
**Planned Features**:

1. **Expanded Scenario Library**
   - Additional Azure services (Azure Front Door, API Management)
   - Multi-region deployment patterns
   - Hybrid cloud scenarios
   - Disaster recovery testing

2. **Enhanced Reporting**
   - Security posture scoring
   - Compliance validation reports
   - Trend analysis and alerting
   - Integration with Azure Security Center

3. **Custom Scenario Framework**
   - User-defined scenarios
   - Scenario templates
   - Scenario validation tools
   - Community scenario sharing

4. **Integration Enhancements**
   - Azure DevOps Pipelines
   - Terraform support
   - Pulumi support
   - Policy-as-Code validation

5. **Advanced Agent Capabilities**
   - Multi-agent collaboration
   - Scenario chaining
   - Adaptive execution based on results
   - Automated remediation suggestions

**Timeline**: Next 6-12 months

**Visual**: Roadmap timeline with features

**Speaker Notes**: We're continuously expanding Azure HayMaker's capabilities based on user feedback and emerging Azure services.

---

### Slide 34: Q&A / Resources
**Title**: Questions & Resources

**Content**:
**Resources**:
- GitHub Repository: https://github.com/your-org/AzureHayMaker
- Documentation: Full docs in `/docs` directory
- Architecture Guide: `specs/architecture.md`
- Deployment Guide: `docs/GITOPS_SETUP.md`
- CLI Reference: `cli/README.md`
- Issues & Feedback: GitHub Issues

**Quick Links**:
- 50+ Scenario Documentation: `/docs/scenarios/`
- Bicep Templates: `/infra/bicep/`
- GitHub Actions Workflows: `/.github/workflows/`

**Support**:
- File issues on GitHub
- Review documentation
- Check troubleshooting guide
- Contact: your-team@company.com

**Thank You**:
- Questions?
- Demo requests?
- Feedback welcome!

**Visual**: QR codes to GitHub repo and docs, contact information

**Speaker Notes**: Thank you for your time. I'm happy to answer questions or provide additional demonstrations of specific scenarios.

---

## SUPPLEMENTARY MATERIALS (Not presented but included in deck)

### Appendix A: CLI Command Reference
Full command syntax for all CLI commands

### Appendix B: Scenario List
Table of all 50 scenarios with descriptions

### Appendix C: Troubleshooting Guide
Common issues and solutions

### Appendix D: Architecture Deep Dive
Detailed component interactions

### Appendix E: Security Model
Complete security architecture documentation

---

## PRESENTATION DELIVERY NOTES

### Timing Guidelines
- Section A (Overview): 15 minutes
- Section B (Deployment): 12 minutes
- Section C (CLI): 10 minutes
- Section D (Demo): 10 minutes
- Q&A: 8-13 minutes

### Key Demonstration Points
1. **Live CLI demonstration** - Show real commands and output
2. **Azure Portal walkthrough** - Show deployed resources with tags
3. **Log streaming** - Demonstrate --follow mode
4. **Cleanup verification** - Show empty resource group after cleanup

### Presentation Tips
- Keep demo agent execution short (15 minutes) by using on-demand deploy
- Have backup screenshots in case live demo fails
- Emphasize security fix (Req 4) as a major improvement
- Show cost savings from automatic cleanup

### Technical Setup
- Pre-deploy dev environment before presentation
- Have agent ready to deploy on-demand
- Test CLI commands before presenting
- Ensure Azure Portal access
- Have backup slides with screenshots

---

## CONTENT PLACEHOLDER NOTES

**THESE MUST BE CAPTURED AFTER DEPLOYMENT**:

1. Real CLI output from actual commands
2. Azure Portal screenshots showing:
   - Resource group with deployed resources
   - Virtual machine running
   - Network security group rules
   - Resource tags
   - Empty resource group after cleanup
3. Application Insights metrics (if available)
4. Real agent log output with timestamps

**IMAGES NEEDED**:
1. Hay farm cover image (1920x1080)
2. Architecture diagrams (can be text-based or visual)
3. CLI terminal screenshots (with real output)
4. Azure Portal screenshots (actual resources)

---

**END OF PRESENTATION OUTLINE**
