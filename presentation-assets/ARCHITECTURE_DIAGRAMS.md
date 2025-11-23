# Architecture Diagram Descriptions for Presentation

This document provides detailed descriptions of the architecture diagrams needed for the Azure HayMaker presentation. These descriptions can be used to create visual diagrams using tools like Draw.io, PowerPoint SmartArt, or Mermaid.

---

## Diagram 1: High-Level System Architecture

**Slide**: 4
**Dimensions**: 1920x1080 (full slide)
**Style**: Clean, professional, 3-layer architecture

### Layers

**Layer 1: Orchestrator (Top)**
- Box: Azure Durable Functions
- Components:
  - Timer Trigger (icon: clock)
  - Scenario Selection (icon: list/shuffle)
  - Agent Provisioning (icon: docker container)
  - Monitoring (icon: graph/dashboard)
  - Cleanup (icon: trash can)
- Color: Blue (#0078D4 - Azure blue)

**Layer 2: Agent Execution & Events (Middle)**
Left side - Agent Layer:
- Box: Azure Container Apps
- Multiple container icons (3-5 shown)
- Each contains:
  - Claude AI agent (icon: robot/brain)
  - Azure CLI, Terraform, Bicep (tool icons)
- Arrows to/from Orchestrator
- Arrows to Target Tenant
- Color: Green (#107C10)

Right side - Event System:
- Box: Service Bus + Cosmos DB
- Service Bus (icon: message queue)
- Cosmos DB (icon: database)
- Arrows from Agent Layer (logs)
- Arrows to Orchestrator (monitoring)
- Color: Purple (#5C2D91)

**Layer 3: Target Environment (Bottom)**
- Box: Azure Tenant
- Icons representing resources:
  - Virtual Machines
  - Storage Accounts
  - Virtual Networks
  - Databases
  - AI Services
- Tag icon showing "AzureHayMaker-managed"
- Color: Orange (#D83B01)

### Data Flow Arrows
- Timer → Orchestrator: Thick solid line
- Orchestrator → Agents: Solid lines (deploy)
- Agents → Event System: Dashed lines (logs)
- Agents → Target Tenant: Bold solid lines (operations)
- Event System → Orchestrator: Dashed lines (monitoring)

### Legend
- Solid lines: Control flow
- Dashed lines: Data flow
- Bold lines: Resource operations

**File Format**: SVG, PNG (1920x1080)

---

## Diagram 2: Orchestrator Workflow

**Slide**: 5
**Dimensions**: 1600x900
**Style**: Vertical flowchart with phases

### Phases (Top to Bottom)

**Phase 1: Validation**
- Icon: Checkmark shield
- Actions:
  - Test Azure credentials
  - Test Anthropic API
  - Verify tools available
- Success: Green checkmark → Next phase
- Failure: Red X → Abort

**Phase 2: Selection**
- Icon: List with shuffle arrows
- Actions:
  - Load 50 scenarios from storage
  - Random select N based on simulation_size
  - Validate scenario documents
- Output: List of selected scenarios

**Phase 3: Provisioning (Fan-Out)**
- Icon: Multiple parallel arrows
- For Each Scenario (parallel):
  - Create Service Principal
  - Assign RBAC roles
  - Wait 60s for propagation
  - Deploy Container App
  - Inject credentials
- Duration: ~5-10 minutes

**Phase 4: Monitoring**
- Icon: Dashboard/graph
- Duration: 8 hours
- Actions (loop every 15 minutes):
  - Check agent status
  - Aggregate logs from Service Bus
  - Track resources created
  - Update execution state

**Phase 5: Cleanup Verification**
- Icon: Magnifying glass
- Actions:
  - Query Azure Resource Graph
  - Find resources with AzureHayMaker-managed tag
  - Compare with expected deletions
- Branching:
  - All cleaned: Green → Report
  - Some remain: Yellow → Forced Cleanup

**Phase 6: Forced Cleanup**
- Icon: Broom/trash
- Actions:
  - Delete remaining resources
  - Delete service principals
  - Retry with dependencies
- Output: Cleanup report

**Phase 7: Report Generation**
- Icon: Document
- Actions:
  - Generate summary
  - Store to blob storage
  - Send notification (if configured)

**Timing Annotations**:
- Total execution: ~8 hours 20 minutes
- Active work: ~20 minutes
- Waiting/monitoring: 8 hours

**File Format**: SVG, PNG (1600x900)

---

## Diagram 3: Agent Execution Timeline

**Slide**: 6
**Dimensions**: 1800x600
**Style**: Horizontal timeline with 3 phases

### Timeline (Left to Right)

**Phase 1: Deploy (0-10 minutes)**
- Color: Blue
- Start: Container starts, agent initializes
- Activities:
  1. Authenticate to Azure (SP)
  2. Connect to Service Bus
  3. Publish "agent_started" event
  4. Create resource group
  5. Deploy infrastructure (Bicep/Terraform)
  6. Configure resources
  7. Validate deployment
  8. Publish "resource_created" events
- End: Deployment complete
- Icon: Rocket launch

**Phase 2: Operate (10 min - 8 hours 10 min)**
- Color: Green
- Activities (loop):
  1. Perform management operations
  2. Generate benign telemetry
  3. Health checks
  4. Publish "operation" events
  5. Sleep intervals
- Duration bar: Very long compared to others
- Icon: Gears/settings
- Note: "Longest phase - simulates real workload"

**Phase 3: Cleanup (8h 10m - 8h 20m)**
- Color: Orange
- Activities:
  1. Stop operations gracefully
  2. Delete resources (reverse dependency order)
  3. Verify deletions
  4. Publish "cleanup_complete" event
  5. Close connections
  6. Exit (code 0)
- End: Container terminates
- Icon: Checkmark in circle

### Error Handling Branch
- Shown below main timeline
- Red color
- "Error at any phase" → Publish "error" event → Best-effort cleanup → Exit (code 1)

**Annotations**:
- Total duration: 8 hours 20 minutes
- Overhead: 20 minutes (deploy + cleanup)
- Efficiency: 98% (8h operation / 8h 20m total)

**File Format**: SVG, PNG (1800x600)

---

## Diagram 4: Dual-Write Log Pattern

**Slide**: 7
**Dimensions**: 1400x800
**Style**: Data flow with branching

### Components

**Source: Agent Container (Left)**
- Icon: Docker container with Claude logo
- Generates logs during execution
- Central component

**Branch 1: Service Bus (Top Right)**
- Path: Agent → Service Bus Topic
- Service Bus icon
- Topic: "agent-logs"
- Characteristics:
  - Real-time streaming
  - Low latency (<100ms)
  - Subscription: orchestrator-monitoring
  - Use case: Live monitoring
- Arrow label: "Publish (real-time)"

**Branch 2: Cosmos DB (Bottom Right)**
- Path: Agent → Cosmos DB
- Cosmos DB icon
- Container: "agent-logs"
- Characteristics:
  - Persistent storage
  - Queryable (SQL API)
  - Indexed (timestamp, agent_id, level)
  - TTL: 7 days
  - Use case: Historical analysis, CLI queries
- Arrow label: "Store (persistent)"

**Consumers (Far Right)**
From Service Bus:
- Orchestrator (monitoring)
- Live dashboard (if applicable)

From Cosmos DB:
- CLI (haymaker logs command)
- API (GET /api/v1/agents/{id}/logs)
- Reporting tools

### Log Entry Schema (Callout Box)
```json
{
  "id": "log-{uuid}",
  "agent_id": "agent-abc123",
  "run_id": "run-xyz789",
  "timestamp": "2025-11-17T12:00:00Z",
  "level": "INFO",
  "message": "Resource group created",
  "source": "agent"
}
```

**Benefits Box** (Bottom):
- Real-time: Service Bus (streaming)
- Historical: Cosmos DB (queryable)
- No data loss: Dual write ensures reliability
- Performance: Optimized for each use case

**File Format**: SVG, PNG (1400x800)

---

## Diagram 5: Security Architecture

**Slide**: 9
**Dimensions**: 1600x900
**Style**: Layered security model

### Layers (Outside to Inside)

**Layer 1: Network Security (Outer)**
- HTTPS only
- Azure AD authentication
- Private endpoints (optional)
- VNet integration (optional)
- Color: Light blue

**Layer 2: Identity & Access (Middle-Outer)**
Components:
- Azure AD
  - Main SP (Orchestrator)
  - Scenario SPs (ephemeral)
- Managed Identity
  - Function App → Key Vault
  - Container Apps → Key Vault
- RBAC assignments
  - Contributor role
  - User Access Administrator role
  - Key Vault Secrets User role
- Color: Yellow

**Layer 3: Secret Management (Middle-Inner)**
- Key Vault (center icon)
- Secrets:
  - Main SP secret
  - Anthropic API key
  - Scenario SP secrets (ephemeral)
  - Service Bus connection
- Access pattern:
  - GitHub Actions → Inject secrets (deployment)
  - Function App → Key Vault references (runtime)
  - Container Apps → Key Vault references (runtime)
- Color: Green

**Layer 4: Audit & Monitoring (Inner)**
- Activity logs
- Key Vault diagnostics
- Application Insights
- Log Analytics (2-year retention)
- Color: Purple

### Key Security Principles (Callout Boxes)

**Least Privilege**:
- Each SP has minimum required roles
- Ephemeral SPs deleted after use
- No human access during runtime

**Defense in Depth**:
- Multiple security layers
- No single point of failure
- Audit at every layer

**Secrets Management**:
- Never in code or config files
- Key Vault references only
- Automatic rotation support
- Masked in logs

**File Format**: SVG, PNG (1600x900)

---

## Diagram 6: GitOps Workflow

**Slide**: 12
**Dimensions**: 1800x700
**Style**: Horizontal workflow with branching

### Workflow (Left to Right)

**Developer Action (Left)**
- Icon: Person at computer
- Actions:
  - git commit
  - git push

**Branch Decision (Center-Left)**
- Diamond: Which branch?

**Branch: develop**
- Arrow to "Deploy to Dev"
- Environment: dev
- Trigger: Automatic on push
- Characteristics:
  - Small simulation (5 scenarios)
  - Fast feedback
  - No approval required
- Deployment time: ~10 minutes

**Branch: main**
- Arrow to "Deploy to Staging"
- Environment: staging
- Trigger: Automatic on push to main
- Characteristics:
  - Medium simulation (15 scenarios)
  - Production-like
  - No approval required
- Deployment time: ~15 minutes

**Tag: v*.**
- Arrow to "Deploy to Prod"
- Environment: prod
- Trigger: Manual (release tag)
- Characteristics:
  - Large simulation (30 scenarios)
  - Full validation
  - Approval required
- Deployment time: ~20 minutes

### Pipeline Stages (For Each Branch)
1. Validate (Bicep templates)
2. Test (pytest, ruff, pyright)
3. Deploy Infrastructure (az deployment group create)
4. Deploy Function (Azure Functions action)
5. Smoke Tests (verify endpoints)

**Success Path**: Green arrows
**Failure Path**: Red arrows → Notification → Manual intervention

### Environment Comparison (Bottom)
Table showing:
| | Dev | Staging | Prod |
|---|-----|---------|------|
| Trigger | Push to develop | Push to main | Release tag |
| Approval | None | None | Required |
| Simulation | Small (5) | Medium (15) | Large (30) |
| Schedule | Startup only | 2x daily | 4x daily |

**File Format**: SVG, PNG (1800x700)

---

## Diagram 7: Secret Management Fix (Before/After)

**Slide**: 16
**Dimensions**: 1600x800
**Style**: Side-by-side comparison

### Left Side: BEFORE (Insecure - Dev Environment)

**GitHub Actions (Top)**
```yaml
- name: Configure secrets (INSECURE)
  run: |
    az functionapp config appsettings set \
      --settings ANTHROPIC_API_KEY="sk-ant-xxx"
```

**Function App (Middle)**
- App Settings showing:
  ```
  ANTHROPIC_API_KEY = "sk-ant-xxx"  ← VISIBLE IN PORTAL!
  ```
- Red X icon: Security violation
- Warning icon: Secrets exposed

**Azure Portal (Bottom)**
- Screenshot concept: Configuration blade showing actual secret value
- Red highlighting: Exposed secret
- Cost: Security risk

**Problems Listed**:
- Secrets visible in Azure Portal
- No rotation support
- Audit gaps
- Inconsistent with staging/prod

---

### Right Side: AFTER (Secure - All Environments)

**GitHub Actions (Top)**
```yaml
- name: Inject to Key Vault (SECURE)
  run: |
    az keyvault secret set \
      --vault-name $KEYVAULT \
      --name anthropic-api-key \
      --value "${{ secrets.ANTHROPIC_API_KEY }}"
```

**Key Vault (Middle-Top)**
- Key Vault icon
- Secrets list:
  - anthropic-api-key (hidden value)
  - main-sp-client-secret (hidden value)
- Green checkmark: Secure storage

**Function App (Middle-Bottom)**
- App Settings showing:
  ```
  ANTHROPIC_API_KEY = "@Microsoft.KeyVault(...)"  ← REFERENCE ONLY
  ```
- Green checkmark: Secure
- Managed Identity arrow to Key Vault

**Azure Portal (Bottom)**
- Screenshot concept: Configuration blade showing Key Vault reference
- Green highlighting: Secure reference
- Cost: Zero additional cost

**Benefits Listed**:
- Secrets never visible in Portal
- Automatic rotation support
- Full audit logging
- Consistent across all environments

---

### Comparison Table (Bottom)
| Aspect | Before (Dev) | After (All Envs) |
|--------|--------------|------------------|
| Visibility | Exposed | Hidden |
| Rotation | Manual | Automatic |
| Audit | Limited | Complete |
| Consistency | Dev ≠ Prod | Dev = Staging = Prod |

**File Format**: SVG, PNG (1600x800)

---

## Diagram 8: CLI Architecture

**Slide**: 18-25 (supporting diagram)
**Dimensions**: 1400x600
**Style**: Component interaction

### Components

**CLI Client (Left)**
- Icon: Terminal/command prompt
- Commands:
  - haymaker status
  - haymaker agents list
  - haymaker logs --follow
  - haymaker resources list
  - haymaker deploy

**API Layer (Center)**
- Function App icon
- HTTP Endpoints:
  - GET /api/v1/status
  - GET /api/v1/agents
  - GET /api/v1/agents/{id}/logs
  - GET /api/v1/resources
  - POST /api/v1/deploy

**Data Sources (Right)**
- Cosmos DB (logs)
- Table Storage (execution state)
- Blob Storage (reports)
- Azure Resource Graph (resources)

### Data Flow
1. CLI command → HTTP request → API endpoint
2. API queries appropriate data source
3. API formats response (JSON)
4. CLI renders output (table, streaming, etc.)

### Follow Mode Detail (Callout)
```
CLI --follow mode:
  Loop:
    1. Query API with ?since=last_timestamp
    2. Get new logs
    3. Display immediately
    4. Update last_timestamp
    5. Sleep 5 seconds
    6. Repeat until Ctrl+C
```

**File Format**: SVG, PNG (1400x600)

---

## Creating These Diagrams

### Recommended Tools

**Option 1: Draw.io (Diagrams.net)**
- Free, web-based or desktop
- Azure stencils available
- Export to PNG, SVG
- URL: https://app.diagrams.net/

**Option 2: Microsoft PowerPoint**
- SmartArt for flowcharts
- Shapes for architecture
- Export slides as images
- Professional templates available

**Option 3: Mermaid (Code-based)**
- Markdown-friendly
- Version control friendly
- Can be rendered in slides
- URL: https://mermaid.js.org/

**Option 4: Azure Architecture Icons**
- Official Azure icons
- Download from: https://learn.microsoft.com/en-us/azure/architecture/icons/
- Use in PowerPoint or Draw.io

### Style Guidelines

**Colors**:
- Azure blue: #0078D4
- Success green: #107C10
- Warning yellow: #FFB900
- Error red: #D83B01
- Info purple: #5C2D91

**Fonts**:
- Headings: Segoe UI Bold, 24pt
- Body text: Segoe UI Regular, 16pt
- Code/CLI: Consolas, 14pt

**Sizing**:
- Minimum icon size: 64x64px
- Line thickness: 2-3px
- Arrow heads: Standard
- Padding: 20px minimum

**Accessibility**:
- High contrast
- Color blind friendly (use shapes + colors)
- Clear labels
- Readable at distance

---

## Export Settings

For all diagrams:
- Format: PNG (for PowerPoint compatibility)
- Resolution: 300 DPI
- Dimensions: As specified per diagram
- Background: Transparent or white
- Compression: Minimal (preserve quality)

For archival:
- Also export as SVG (vector)
- Include source files (.drawio, .pptx)
- Version control in git

---

**END OF ARCHITECTURE DIAGRAMS SPECIFICATION**
