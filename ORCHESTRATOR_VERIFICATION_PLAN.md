# Orchestrator End-to-End Verification Plan

## Purpose

Verify that the merge conflict fix (commit 062d501) successfully resolved the container startup issue and that the orchestrator can deploy and monitor agents.

## Prerequisites

### Azure Authentication

**Current Issue**: Azure auth token expired
```bash
# Re-authenticate
az logout
az login --tenant "c7674d41-af6c-46f5-89a5-d41495d2151e" --scope "https://management.core.windows.net//.default"

# Verify authentication
az account show
```

**Expected Output**:
```json
{
  "id": "c190c55a-9ab2-4b1e-92c4-cc8b1a032285",
  "name": "Your Subscription",
  "tenantId": "c7674d41-af6c-46f5-89a5-d41495d2151e"
}
```

### Azure Resources

- **Subscription**: `c190c55a-9ab2-4b1e-92c4-cc8b1a032285`
- **Resource Group**: `haymaker-dev-rg`
- **Container App**: `orch-dev-yc4hkcb2vv`
- **Endpoint**: `https://orch-dev-yc4hkcb2vv.ashyocean-9cc3722e.westus2.azurecontainerapps.io`
- **Working Revision**: `orch-dev-yc4hkcb2vv--0000002` (old, pre-merge-conflict)
- **Fixed Revision**: TBD (will be created by GitOps after commit 062d501)

---

## Phase 1: Verify Container Deployment

### Step 1.1: Check GitOps Status

Verify that GitOps workflow rebuilt the container image from commit 062d501.

```bash
# Check GitHub Actions workflow status
gh run list --workflow=deploy-container-apps-dev.yml --limit 5

# Check latest run details
gh run view --web
```

**Expected**: Workflow should have run after commit 062d501 was pushed to main.

### Step 1.2: Check Container Registry

Verify new image was built and pushed to ACR.

```bash
# List recent images
az acr repository show-tags \
  --name haymakerorchacr \
  --repository haymaker-orchestrator \
  --orderby time_desc \
  --output table

# Check image with 'latest' tag
az acr repository show \
  --name haymakerorchacr \
  --repository haymaker-orchestrator
```

**Expected**: New image tag created after 2025-11-20 06:00 (after commit 062d501).

### Step 1.3: List All Revisions

Check all Container Apps revisions to find the new one.

```bash
az containerapp revision list \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --query "[].{Name:name, Active:properties.active, Traffic:properties.trafficWeight, Replicas:properties.replicas, Health:properties.healthState, Created:properties.createdTime}" \
  --output table
```

**Expected Output**:
```
Name                          Active  Traffic  Replicas  Health    Created
orch-dev-yc4hkcb2vv--0000009  True    100      1         Healthy   2025-11-20 06:15:00
orch-dev-yc4hkcb2vv--0000002  False   0        0         None      2025-11-19 01:21:18
```

**Success Criteria**:
- ✅ New revision created after commit 062d501
- ✅ New revision marked as Active=True
- ✅ Traffic weight = 100% (all traffic going to new revision)

---

## Phase 2: Verify Container Running State

### Step 2.1: Check Replica Status

Verify container replicas reached "Running" state (NOT "NotRunning").

```bash
# Get latest active revision name
LATEST_REVISION=$(az containerapp revision list \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --query "[?properties.active].name | [0]" \
  --output tsv)

echo "Latest active revision: $LATEST_REVISION"

# Check replica status
az containerapp replica list \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --revision $LATEST_REVISION \
  --query "[].{Name:name, Status:properties.runningState, Created:properties.createdTime}" \
  --output table
```

**Expected Output**:
```
Name                                      Status   Created
orch-dev-yc4hkcb2vv--0009-xxx-xxx         Running  2025-11-20 06:15:30
```

**Success Criteria**:
- ✅ Status = "Running" (NOT "NotRunning")
- ✅ At least 1 replica running

**If Status = "NotRunning"**:
- ❌ Merge conflict fix didn't work
- ❌ There's another issue preventing startup
- 🔍 Check logs for actual error

### Step 2.2: Check Container Logs

Verify Azure Functions runtime initialized successfully.

```bash
# Get logs from latest revision
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --revision $LATEST_REVISION \
  --tail 100 \
  --follow false

# OR use Azure CLI streaming
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --tail 200 \
  --follow true
```

**Expected Log Messages** (Azure Functions initialized):
```
Host version: 4.x.x
Function Runtime Version: 4.x
Worker Runtime Version: 3.11.x
Found the following functions:
  Function: 'haymaker_timer'
  Function: 'orchestrate_haymaker_run'
  ...
Job host started
```

**Success Criteria**:
- ✅ "Host version:" appears (Azure Functions runtime started)
- ✅ "Found the following functions:" appears (functions discovered)
- ✅ "haymaker_timer" listed (timer function found)
- ✅ "orchestrate_haymaker_run" listed (orchestration function found)
- ✅ No Python import errors
- ✅ No "app = None" errors

**If Logs Show Errors**:
- 🔍 ImportError → Missing dependency in requirements.txt
- 🔍 "No functions found" → function_app.py not discovered
- 🔍 SyntaxError → Python syntax issue

---

## Phase 3: Verify HTTP Endpoint

### Step 3.1: Test Endpoint Responds

```bash
# Get orchestrator endpoint
ENDPOINT=$(az containerapp show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

echo "Endpoint: https://$ENDPOINT"

# Test endpoint responds (should get 200 or 404, not connection refused)
curl -v https://$ENDPOINT/ 2>&1 | grep -E "(HTTP/|Connection refused)"

# Test health endpoint (if exists)
curl -s https://$ENDPOINT/api/health || echo "Health endpoint not found"
```

**Expected**:
- ✅ Connection succeeds (NOT "Connection refused")
- ✅ HTTP response received (200, 404, or 401 all okay - means server is running)
- ❌ If "Connection refused" → Container not actually running

**Success Criteria**:
- ✅ Endpoint resolves to IP address
- ✅ TCP connection succeeds on port 443
- ✅ HTTP response received (any status code)

---

## Phase 4: Verify Azure Functions Discovery

### Step 4.1: Check Function App Status

Verify Azure Functions runtime discovered and loaded functions.

```bash
# Check if functions are accessible
curl -s https://$ENDPOINT/api/orchestrate_haymaker_run \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{}' || echo "Function not accessible (may require auth)"

# Check function discovery via logs
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --tail 500 | grep -A 10 "Found the following functions:"
```

**Expected Log Output**:
```
Found the following functions:
  Function: 'haymaker_timer'
  Function: 'orchestrate_haymaker_run'
  Function: 'validate_environment_activity'
  Function: 'select_scenarios_activity'
  Function: 'create_service_principal_activity'
  Function: 'deploy_container_app_activity'
  Function: 'check_agent_status_activity'
  Function: 'verify_cleanup_activity'
  Function: 'force_cleanup_activity'
  Function: 'generate_report_activity'
```

**Success Criteria**:
- ✅ All 10 functions discovered (1 timer + 1 orchestrator + 8 activities)
- ✅ No "Could not load function" errors
- ✅ Functions are accessible via HTTP (may require authentication)

---

## Phase 5: Test Agent Deployment

### Step 5.1: Trigger Orchestration Manually

Test if the orchestrator can deploy an agent.

**Option A: Using haymaker CLI** (if available):
```bash
# Use the CLI to trigger orchestration
haymaker orchestrate --scenario test
```

**Option B: Using Azure Functions HTTP trigger**:
```bash
# Get function key
FUNCTION_KEY=$(az functionapp keys list \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --query "functionKeys.default" \
  --output tsv 2>/dev/null || echo "Using Container Apps, no function keys")

# Trigger orchestration via HTTP
curl -X POST https://$ENDPOINT/api/orchestrate_haymaker_run \
  -H "Content-Type: application/json" \
  -H "x-functions-key: $FUNCTION_KEY" \
  -d '{
    "scenarios": ["containers-01-simple-web-app"],
    "timeout": 600
  }'
```

**Option C: Using Timer Trigger**:
```bash
# The haymaker_timer function should trigger automatically based on KEDA CRON schedule
# Check logs for timer execution
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --tail 100 | grep -i "timer\|orchestrate"
```

**Expected**:
- ✅ Orchestration starts
- ✅ Scenario selection occurs
- ✅ Service principal creation initiated
- ✅ Container deployment begins

### Step 5.2: Monitor Agent Container Deployment

Watch for agent containers being created.

```bash
# List container apps (should show new agent containers)
az containerapp list \
  --resource-group haymaker-dev-rg \
  --query "[?starts_with(name, 'haymaker-agent')].{Name:name, Status:properties.provisioningState, Replicas:properties.latestRevisionFqdn}" \
  --output table

# Or use Container Instances if agents deploy there
az container list \
  --resource-group haymaker-dev-rg \
  --query "[].{Name:name, Status:properties.instanceView.state, IP:properties.ipAddress.ip}" \
  --output table
```

**Expected**:
- ✅ New container(s) created with names like `haymaker-agent-<scenario>`
- ✅ Status transitions: Pending → Running
- ✅ Containers successfully provision

**Success Criteria**:
- ✅ At least 1 agent container deployed
- ✅ Agent container reaches "Running" state
- ✅ No deployment errors in orchestrator logs

---

## Phase 6: Monitor Agent Execution

### Step 6.1: Check Agent Logs

Verify agent is executing and producing output.

```bash
# For Container Apps agents
az containerapp logs show \
  --name <agent-container-name> \
  --resource-group haymaker-dev-rg \
  --tail 100

# For Container Instances agents
az container logs \
  --name <agent-container-name> \
  --resource-group haymaker-dev-rg
```

**Expected**:
- ✅ Agent startup messages
- ✅ Anthropic API calls being made
- ✅ Scenario execution progress
- ✅ Results being generated

### Step 6.2: Verify Memory Usage

Check that the orchestrator is using the 128GB profile properly.

```bash
# Check container app configuration
az containerapp show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --query "{WorkloadProfile:properties.workloadProfileName, CPU:properties.template.containers[0].resources.cpu, Memory:properties.template.containers[0].resources.memory}" \
  --output table

# Check environment workload profiles
az containerapp env show \
  --name <environment-name> \
  --resource-group haymaker-dev-rg \
  --query "properties.workloadProfiles[].{Name:name, Type:workloadProfileType, Cores:maximumCount, Memory:memoryGiB}" \
  --output table
```

**Expected**:
- ✅ WorkloadProfile: E16 or similar
- ✅ Memory: 128GB available
- ✅ CPU: 16 vCPU

### Step 6.3: Monitor Agent Status

Watch orchestrator monitoring agents.

```bash
# Check orchestrator logs for agent status checks
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --tail 200 | grep -i "agent\|status\|monitor"
```

**Expected**:
- ✅ Orchestrator checking agent status periodically
- ✅ Agent state transitions logged
- ✅ Completion or failure status recorded

---

## Phase 7: Comprehensive Verification Checklist

### Container Startup Verification

| Check | Command | Expected Result | Status |
|-------|---------|-----------------|--------|
| **GitOps Workflow** | `gh run list --workflow=deploy-container-apps-dev.yml` | Recent successful run | ⏳ |
| **ACR Image** | `az acr repository show-tags --name haymakerorchacr --repository haymaker-orchestrator` | New tag after 2025-11-20 06:00 | ⏳ |
| **New Revision** | `az containerapp revision list --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg` | Active revision created after 062d501 | ⏳ |
| **Replica Running** | `az containerapp replica list ...` | Status = "Running" (NOT "NotRunning") | ⏳ |
| **Logs Available** | `az containerapp logs show ...` | Logs appear (not "No logs available") | ⏳ |
| **Functions Runtime** | Check logs | "Host version:", "Found the following functions:" | ⏳ |
| **Function Discovery** | Check logs | 10 functions listed (1 timer + 1 orchestrator + 8 activities) | ⏳ |
| **Endpoint Responds** | `curl https://$ENDPOINT/` | HTTP response (not connection refused) | ⏳ |

### Agent Deployment Verification

| Check | Command | Expected Result | Status |
|-------|---------|-----------------|--------|
| **Trigger Orchestration** | Trigger via timer/HTTP/CLI | Orchestration starts | ⏳ |
| **Scenario Selection** | Check logs | Scenarios selected from available list | ⏳ |
| **SP Creation** | Check logs | Service principal created or reused | ⏳ |
| **Agent Deployment** | `az containerapp list --resource-group haymaker-dev-rg` | New agent containers created | ⏳ |
| **Agent Running** | Check agent container status | Agent reaches "Running" state | ⏳ |
| **Agent Logs** | `az containerapp logs show --name <agent>` | Agent producing output | ⏳ |
| **Status Monitoring** | Check orchestrator logs | Orchestrator checking agent status | ⏳ |
| **Completion** | Check logs | Agent completes or fails with clear status | ⏳ |

### Memory and Resource Verification

| Check | Command | Expected Result | Status |
|-------|---------|-----------------|--------|
| **Workload Profile** | `az containerapp show ... --query properties.workloadProfileName` | E16 or 128GB profile | ⏳ |
| **Memory Allocation** | Check container configuration | 128GB available | ⏳ |
| **CPU Allocation** | Check container configuration | 16 vCPU available | ⏳ |
| **No OOM Errors** | Check logs | No "out of memory" errors | ⏳ |
| **No Exit 134** | Check agent logs | No SIGABRT/exit code 134 | ⏳ |

---

## Quick Verification Script

Save this as `verify_orchestrator.sh`:

```bash
#!/bin/bash
set -e

echo "=== Orchestrator Verification Script ==="
echo ""

# Configuration
SUBSCRIPTION_ID="c190c55a-9ab2-4b1e-92c4-cc8b1a032285"
RESOURCE_GROUP="haymaker-dev-rg"
CONTAINER_APP="orch-dev-yc4hkcb2vv"

# Set subscription
az account set --subscription $SUBSCRIPTION_ID

echo "1. Checking Container App revisions..."
az containerapp revision list \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query "[].{Name:name, Active:properties.active, Traffic:properties.trafficWeight, Health:properties.healthState, Created:properties.createdTime}" \
  --output table

echo ""
echo "2. Getting latest active revision..."
LATEST_REVISION=$(az containerapp revision list \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query "[?properties.active].name | [0]" \
  --output tsv)

echo "Latest revision: $LATEST_REVISION"

echo ""
echo "3. Checking replica status..."
az containerapp replica list \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --revision $LATEST_REVISION \
  --query "[].{Name:name, Status:properties.runningState, Created:properties.createdTime}" \
  --output table

echo ""
echo "4. Checking container logs (last 50 lines)..."
az containerapp logs show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --revision $LATEST_REVISION \
  --tail 50

echo ""
echo "5. Verifying function discovery..."
az containerapp logs show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --revision $LATEST_REVISION \
  --tail 200 | grep -A 12 "Found the following functions:" || echo "Function discovery not found in logs"

echo ""
echo "6. Testing endpoint connectivity..."
ENDPOINT=$(az containerapp show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

echo "Endpoint: https://$ENDPOINT"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" https://$ENDPOINT/ || echo "Endpoint not responding"

echo ""
echo "7. Checking workload profile..."
az containerapp show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query "{WorkloadProfile:properties.workloadProfileName, CPU:properties.template.containers[0].resources.cpu, Memory:properties.template.containers[0].resources.memory}" \
  --output table

echo ""
echo "=== Verification Complete ==="
echo ""
echo "Success criteria:"
echo "✓ Replica status = 'Running' (not 'NotRunning')"
echo "✓ Logs contain 'Found the following functions:'"
echo "✓ At least 10 functions listed"
echo "✓ Endpoint responds to HTTP requests"
echo "✓ No Python import errors in logs"
```

**Run with**:
```bash
chmod +x verify_orchestrator.sh
./verify_orchestrator.sh
```

---

## Phase 8: Test Agent Deployment (Full E2E)

### Prerequisites
- ✅ Phase 1-7 checks all passed
- ✅ Orchestrator running and healthy
- ✅ Functions discovered

### Test Procedure

**Step 8.1: Trigger Orchestration**

```bash
# Option 1: Wait for timer trigger (automatic)
# Timer triggers based on KEDA CRON schedule

# Option 2: Manual HTTP trigger
ENDPOINT=$(az containerapp show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

curl -X POST https://$ENDPOINT/api/orchestrate_haymaker_run \
  -H "Content-Type: application/json" \
  -d '{}'

# Option 3: Use haymaker CLI (once PR #27 merged)
haymaker deploy --scenario containers-01-simple-web-app
```

**Step 8.2: Monitor Orchestration Logs**

```bash
# Follow orchestrator logs in real-time
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --follow true | grep -E "(Orchestration|Agent|Deploy|Complete)"
```

**Expected Flow**:
```
[timestamp] Orchestration started
[timestamp] Validating environment
[timestamp] Selecting scenarios
[timestamp] Creating service principal
[timestamp] Deploying agent container: containers-01-simple-web-app
[timestamp] Agent container deployed successfully
[timestamp] Monitoring agent status
[timestamp] Agent status: Running
[timestamp] Agent completed successfully
[timestamp] Generating report
[timestamp] Orchestration complete
```

**Step 8.3: Verify Agent Container**

```bash
# List all containers in resource group
az containerapp list \
  --resource-group haymaker-dev-rg \
  --query "[].{Name:name, Status:properties.provisioningState, Created:properties.createdTime}" \
  --output table

# Check specific agent container
az containerapp show \
  --name haymaker-agent-containers-01 \
  --resource-group haymaker-dev-rg \
  --query "{Name:name, Status:properties.runningStatus, Replicas:properties.runningState}" \
  --output table
```

**Step 8.4: Check Agent Logs**

```bash
# View agent execution logs
az containerapp logs show \
  --name haymaker-agent-containers-01 \
  --resource-group haymaker-dev-rg \
  --tail 200
```

**Expected Agent Log Output**:
- ✅ Claude API initialization
- ✅ Scenario execution started
- ✅ Azure SDK operations (deploying resources)
- ✅ Results generated
- ✅ Completion or failure status

---

## Success Criteria Summary

### Critical (MUST PASS)

1. ✅ Container replica status = "Running" (not "NotRunning")
2. ✅ Azure Functions runtime initialized
3. ✅ 10 functions discovered and loaded
4. ✅ HTTP endpoint responds (not connection refused)
5. ✅ No Python import errors in logs
6. ✅ No "app = None" errors

### Important (SHOULD PASS)

7. ✅ Orchestration can be triggered
8. ✅ Scenario selection works
9. ✅ Agent containers can be deployed
10. ✅ Agent containers reach "Running" state
11. ✅ Orchestrator can monitor agent status
12. ✅ 128GB memory profile configured

### Optional (NICE TO HAVE)

13. ✅ Agent completes successfully
14. ✅ Results are generated
15. ✅ Report creation works
16. ✅ Cleanup verification passes

---

## Expected Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Auth Setup** | 2 min | `az login` and verify |
| **Phase 1** | 5 min | Verify deployment (GitOps, ACR, revisions) |
| **Phase 2** | 10 min | Check running state and logs |
| **Phase 3** | 5 min | Test HTTP endpoint |
| **Phase 4** | 5 min | Verify function discovery |
| **Phase 5-6** | 30-60 min | Trigger and monitor agent deployment |
| **Total** | 60-90 min | Complete verification |

---

## Failure Scenarios

### If Replica Still "NotRunning"

**Possible Causes**:
1. Merge conflict fix didn't resolve the issue
2. Different issue preventing startup
3. Missing dependency in requirements.txt
4. Azure Functions runtime incompatibility

**Debug Steps**:
```bash
# Check logs for actual error
az containerapp logs show --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg --tail 500

# Look for:
# - ImportError
# - ModuleNotFoundError
# - SyntaxError
# - Azure Functions runtime errors
```

### If Functions Not Discovered

**Possible Causes**:
1. function_app.py not in correct location
2. function_app.py not importing app correctly
3. host.json misconfigured

**Debug Steps**:
```bash
# Verify files exist in container
az containerapp exec \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --command "ls -la /home/site/wwwroot"

# Check function_app.py content
az containerapp exec \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --command "cat /home/site/wwwroot/function_app.py"
```

### If Agent Deployment Fails

**Possible Causes**:
1. Insufficient permissions for service principal
2. Container deployment quota exceeded
3. Azure SDK errors

**Debug Steps**:
```bash
# Check orchestrator logs for deployment errors
az containerapp logs show --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg | grep -i "error\|fail"

# Check activity function logs
az containerapp logs show --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg | grep -A 20 "deploy_container_app_activity"
```

---

## Verification Report Template

After running verification, document results:

```markdown
# Orchestrator Verification Results

**Date**: YYYY-MM-DD
**Tester**: [Name]
**Environment**: haymaker-dev-rg / orch-dev-yc4hkcb2vv

## Phase 1: Container Deployment
- [ ] GitOps workflow succeeded
- [ ] New image in ACR
- [ ] New revision created
- [ ] Revision is active

**Notes**: ___________

## Phase 2: Container Running State
- [ ] Replica status = "Running"
- [ ] Logs available
- [ ] Functions runtime initialized
- [ ] Functions discovered (count: ___)

**Notes**: ___________

## Phase 3: HTTP Endpoint
- [ ] Endpoint resolves
- [ ] HTTP response received
- [ ] Status code: ___

**Notes**: ___________

## Phase 4: Function Discovery
- [ ] haymaker_timer found
- [ ] orchestrate_haymaker_run found
- [ ] All 8 activity functions found
- [ ] No import errors

**Functions Found**: ___________

## Phase 5-6: Agent Deployment
- [ ] Orchestration triggered
- [ ] Agent container deployed
- [ ] Agent reached "Running" state
- [ ] Agent produced logs
- [ ] Orchestrator monitored agent

**Agent Name**: ___________
**Scenario**: ___________

## Phase 7: Resource Verification
- [ ] Workload profile = E16 (128GB)
- [ ] Memory = 128GB
- [ ] CPU = 16 vCPU
- [ ] No OOM errors

**Notes**: ___________

## Overall Status
- [ ] All critical checks passed (1-6)
- [ ] All important checks passed (7-12)
- [ ] Issue #26 fully resolved

**Recommendation**: ___________
```

---

## Quick Start Commands

**Run these in order after authentication**:

```bash
# 1. Authenticate
az login --tenant "c7674d41-af6c-46f5-89a5-d41495d2151e"

# 2. Set subscription
az account set --subscription "c190c55a-9ab2-4b1e-92c4-cc8b1a032285"

# 3. Run verification script
./verify_orchestrator.sh

# 4. If all checks pass, trigger agent deployment
# (Manual trigger or wait for timer)

# 5. Monitor in real-time
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --follow true
```

---

## Files Created

- `ORCHESTRATOR_VERIFICATION_PLAN.md` (this file)
- `verify_orchestrator.sh` (verification script)

## Related Issues/PRs

- **Issue #26**: Container Apps: Fix orchestrator startup + Implement CLI diagnostic commands
- **Commit 062d501**: Fix merge conflict markers (container startup)
- **PR #27**: Implement haymaker orch CLI commands

---

**Next Action**: Run `verify_orchestrator.sh` after authenticating with Azure CLI.
