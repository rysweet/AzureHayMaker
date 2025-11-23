# CLI Examples to Capture for Presentation

This document lists all CLI commands and outputs that need to be captured from the live system for the presentation.

**IMPORTANT**: These must be captured AFTER the deployment is complete and agents are running.

---

## Section C: CLI Usage Examples

### Slide 18: Installation (Verification Output)

**Command**:
```bash
uv run haymaker --help
```

**Expected Output** (capture this):
```
Usage: haymaker [OPTIONS] COMMAND [ARGS]...

Azure HayMaker CLI - Autonomous Cloud Security Testing

Commands:
  status    Show orchestrator status
  agents    Manage and monitor agents
  logs      View agent execution logs
  deploy    Deploy scenario on-demand
  resources List resources by scenario
  config    Configure CLI settings
  version   Show CLI version

Options:
  --help  Show this message and exit
```

**Screenshot Requirements**:
- Terminal with command and full output
- Clear font (monospace)
- Good contrast
- Dimensions: ~1600x400

---

### Slide 19: Configuration (Config Output)

**Commands**:
```bash
# Show configuration
uv run haymaker config list
```

**Expected Output** (capture this):
```
Configuration:
  Endpoint: https://haymaker-dev-func.azurewebsites.net
  Auth: Azure AD (Default Credential)
  Timeout: 30s
  Output: table
  Config File: /Users/ryan/.haymaker/config.json
```

**Screenshot Requirements**:
- Terminal showing config list output
- Dimensions: ~1400x300

---

### Slide 20: Status Command (Real Status)

**Command**:
```bash
uv run haymaker status
```

**Expected Output** (capture this with REAL data):
```
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
```

**Screenshot Requirements**:
- Full terminal window with rich table formatting
- Color coding visible (if applicable)
- Dimensions: ~1600x800

---

### Slide 21: Agents List (Real Agent Data)

**Command**:
```bash
uv run haymaker agents list
```

**Expected Output** (capture with REAL agents):
```
┌─────────────┬────────────────────────┬─────────┬──────────────┬──────────┐
│ Agent ID    │ Scenario               │ Status  │ Started At   │ Duration │
├─────────────┼────────────────────────┼─────────┼──────────────┼──────────┤
│ agent-abc123│ compute-01-linux-vm    │ Running │ 12:05 UTC    │ 3h 20m   │
│ agent-def456│ storage-01-blob        │ Running │ 12:07 UTC    │ 3h 18m   │
│ agent-ghi789│ network-01-vnet        │ Running │ 12:10 UTC    │ 3h 15m   │
│ agent-jkl012│ ai-ml-01-cognitive     │ Running │ 12:12 UTC    │ 3h 13m   │
│ agent-mno345│ database-01-sqldb      │ Running │ 12:15 UTC    │ 3h 10m   │
└─────────────┴────────────────────────┴─────────┴──────────────┴──────────┘
```

**Additional Command** (agent details):
```bash
uv run haymaker agents get agent-abc123
```

**Expected Output**:
```
Agent ID: agent-abc123
Scenario: compute-01-linux-vm-web-server
Status: Running
Started: 2025-11-17 12:05:23 UTC
Duration: 3h 20m 15s
Phase: Operate (Phase 2 of 3)
Resources Created: 5 (VM, VNet, NSG, Public IP, Disk)
Service Principal: AzureHayMaker-compute-01-admin
Container App: ca-agent-abc123
```

**Screenshot Requirements**:
- Full table with all agents
- Details view for one agent
- Dimensions: ~1800x1000 (combined)

---

### Slide 22: Logs Tail Mode (Real Logs)

**Command**:
```bash
uv run haymaker logs --agent-id agent-abc123 --tail 50
```

**Expected Output** (capture REAL logs from deployment):
```
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
│ ...         │        │                                            │
└─────────────┴────────┴────────────────────────────────────────────┘
```

**Screenshot Requirements**:
- Full table with color-coded log levels
- At least 20-30 log entries visible
- Dimensions: ~1800x1000

---

### Slide 23: Logs Follow Mode (Streaming)

**Command**:
```bash
uv run haymaker logs --agent-id agent-abc123 --follow
```

**Expected Output** (capture streaming output):
```
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
```

**Screenshot Requirements**:
- Streaming format (no table borders)
- Show "Following logs" header
- Color coding visible
- Dimensions: ~1600x800

**Alternative**: Capture as animated GIF or video clip (5-10 seconds)

---

### Slide 24: Resources List (Real Resources)

**Command**:
```bash
uv run haymaker resources list --scenario compute-01-linux-vm
```

**Expected Output** (capture REAL resources):
```
┌────────────────────────┬───────────────────┬────────┬──────────────────────┐
│ Resource Type          │ Resource Name     │ Status │ Tags                 │
├────────────────────────┼───────────────────┼────────┼──────────────────────┤
│ Resource Group         │ rg-agent-abc123   │ Active │ Scenario=compute-01  │
│ Virtual Network        │ vnet-web          │ Active │ Agent=agent-abc123   │
│ Network Security Group │ nsg-web           │ Active │ RunId=run-xyz789     │
│ Public IP Address      │ pip-web           │ Active │ ManagedBy=HayMaker   │
│ Virtual Machine        │ vm-web-server     │ Running│ AutoCleanup=true     │
└────────────────────────┴───────────────────┴────────┴──────────────────────┘

Total: 5 resources
```

**Screenshot Requirements**:
- Full table with all resources
- Tags column visible
- Dimensions: ~1800x600

---

### Slide 25: Deploy On-Demand (Full Workflow)

**Command**:
```bash
uv run haymaker deploy --scenario compute-01-linux-vm --wait
```

**Expected Output** (capture FULL output):
```
Deploying scenario: compute-01-linux-vm

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

⏳ Waiting for agent to complete (max 2 hours)...
[Progress indicators...]
✓ Agent completed successfully after 15m 34s

Summary:
  Duration: 15m 34s
  Resources created: 5
  Resources cleaned: 5
  Status: Success
```

**Screenshot Requirements**:
- Capture entire deployment flow
- Show progress indicators
- Multiple screenshots showing different stages
- Dimensions: ~1600x1200 (full terminal)

---

## Section D: Demo Examples

### Slide 27: Starting Agent (Initial Output)

**Command**:
```bash
uv run haymaker deploy --scenario compute-01-linux-vm-web-server --wait
```

**Capture**: First 20 lines of output showing SP creation and Container App deployment

---

### Slide 28: Agent Logs (Deployment Phase)

**Command**:
```bash
uv run haymaker logs --agent-id <real-agent-id> --follow
```

**Capture**: First 30-50 log entries showing:
1. Agent start
2. Resource group creation
3. VNet creation
4. NSG configuration
5. VM deployment
6. Web server validation
7. Phase 2 start

---

### Slide 30: Cleanup Verification

**Commands**:
```bash
# Check agent completion
uv run haymaker agents get <agent-id>

# Verify no resources remain
uv run haymaker resources list --agent-id <agent-id>

# Double-check in Azure
az resource list \
  --tag AzureHayMaker-managed=true \
  --tag Agent=<agent-id> \
  --output table
```

**Capture**:
1. Agent status showing "Completed"
2. Empty resources list
3. Empty Azure CLI output

---

## Azure Portal Screenshots

These screenshots are needed for Section D (Demo):

### Slide 29: Resources in Portal

**Screenshots Needed**:

1. **Resource Group Overview**:
   - URL: Azure Portal → Resource Groups → rg-agent-<id>
   - Show: All resources list (5 items)
   - Highlight: Tags column
   - Dimensions: 1920x1080 (full browser window)

2. **Virtual Machine Details**:
   - URL: Azure Portal → Virtual Machines → vm-web-server
   - Show: Overview page with Status: Running
   - Highlight: Public IP address
   - Dimensions: 1920x1080

3. **Network Security Group Rules**:
   - URL: Azure Portal → Network Security Groups → nsg-web → Inbound security rules
   - Show: Rules table with HTTP (80) and SSH (22)
   - Dimensions: 1920x1080

4. **Resource Tags (Close-up)**:
   - URL: Any resource → Tags blade
   - Show: All HayMaker tags clearly
   - Tags to highlight:
     - AzureHayMaker-managed: true
     - Scenario: compute-01-linux-vm-web-server
     - Agent: agent-<id>
     - RunId: run-<id>
   - Dimensions: 1600x900

5. **Empty Resource Group (After Cleanup)**:
   - URL: Azure Portal → Resource Groups → rg-agent-<id>
   - Show: "No resources found" message
   - OR: Resource group deleted (not found)
   - Dimensions: 1920x1080

**Portal Screenshot Tips**:
- Use Chrome/Edge in full-screen mode
- Zoom to 100%
- Hide browser toolbars (F11 full-screen)
- Clear notifications
- Use light or dark theme consistently

---

## Capture Workflow

### Phase 1: Preparation (Before Deployment)
1. Install and configure CLI
2. Capture --help output
3. Capture config list output

### Phase 2: During Deployment
1. Start deploy command (capture full output)
2. Simultaneously start log follow (capture streaming)
3. Take Azure Portal screenshots of created resources
4. Capture agents list command output
5. Capture resources list command output

### Phase 3: After Completion
1. Capture agent completion status
2. Capture cleanup verification (empty resources)
3. Take Azure Portal screenshot of empty/deleted RG
4. Capture final summary

---

## File Naming Convention

Save captured screenshots as:
```
presentation-assets/screenshots/
├── cli-help-output.png
├── cli-config-list.png
├── cli-status-running.png
├── cli-agents-list-table.png
├── cli-agent-details.png
├── cli-logs-tail-table.png
├── cli-logs-follow-streaming.png
├── cli-resources-list-table.png
├── cli-deploy-command-start.png
├── cli-deploy-command-progress.png
├── cli-deploy-command-complete.png
├── cli-cleanup-verification.png
├── portal-resource-group-overview.png
├── portal-vm-details-running.png
├── portal-nsg-rules.png
├── portal-resource-tags.png
├── portal-resource-group-empty.png
└── portal-resource-group-deleted.png
```

---

## Testing Commands Before Capture

**Test these commands work before capturing**:

```bash
# Test CLI installation
uv run haymaker --version

# Test CLI configuration
uv run haymaker config list

# Test connection to Function App
uv run haymaker status

# Test agents list (will be empty if no run)
uv run haymaker agents list

# Test deploy (do a dry run or quick scenario)
uv run haymaker deploy --scenario compute-01-linux-vm --help
```

---

## Backup Plan

If live deployment isn't available for screenshots:

**Option A: Use Staging Environment**
- Deploy to staging instead of dev
- Capture screenshots there

**Option B: Use Mock Data**
- Create realistic-looking mock output
- Clearly label slides as "Example Output"

**Option C: Use Previous Deployment**
- If logs are retained, use historical data
- Update timestamps to be more recent

**Option D: Text-Based Slides**
- Use formatted code blocks instead of screenshots
- Still professional and readable
- Easier to create and maintain

---

## Quality Checklist

Before using screenshots in presentation:
- [ ] Resolution is 1920x1080 or higher
- [ ] Text is clearly readable
- [ ] No sensitive data visible (real IPs okay, but no secrets)
- [ ] Consistent terminal theme/colors
- [ ] No typos in command names
- [ ] Timestamps are realistic
- [ ] Data is representative of actual usage
- [ ] File sizes are reasonable (<2MB per image)

---

**NEXT STEP**: Deploy Azure HayMaker to dev environment and execute these capture commands.
