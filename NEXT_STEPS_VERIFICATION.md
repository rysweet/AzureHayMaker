# Next Steps: Orchestrator End-to-End Verification

## Current Status

✅ **Part 1: Container Startup Fix** - Committed to main (062d501, 1c3d9e7)
✅ **Part 2: CLI Commands** - Implemented in PR #27 with bug fixes
⏳ **Verification** - Blocked by Azure authentication (token expired)

---

## Immediate Actions Required

### Step 1: Re-authenticate with Azure (REQUIRED)

```bash
# Logout old session
az logout

# Login with correct tenant and scope
az login --tenant "c7674d41-af6c-46f5-89a5-d41495d2151e"

# Verify authentication
az account show

# Set correct subscription
az account set --subscription "c190c55a-9ab2-4b1e-92c4-cc8b1a032285"
```

---

### Step 2: Install and Configure haymaker CLI

```bash
# Navigate to worktree with CLI implementation
cd /home/azureuser/src/AzureHayMaker/worktrees/feat-issue-26-cli-commands

# Install CLI (already done, but if needed)
uv pip install -e cli/

# Verify installation
haymaker orch --help
```

**Expected**: Shows 4 commands (status, replicas, logs, health)

---

### Step 3: Verify Orchestrator with haymaker Commands

**Test 1: Check Orchestrator Status**
```bash
haymaker orch status \
  --app-name orch-dev-yc4hkcb2vv \
  --subscription-id c190c55a-9ab2-4b1e-92c4-cc8b1a032285 \
  --resource-group haymaker-dev-rg
```

**Expected Output**:
```
Orchestrator Status
===================
Endpoint: https://orch-dev-yc4hkcb2vv.ashyocean-9cc3722e.westus2.azurecontainerapps.io
Status: Running

Active Revisions
NAME                          TRAFFIC  REPLICAS  HEALTH    CREATED
orch-dev-yc4hkcb2vv--0000009    100%       1      Healthy   2025-11-20 06:15
```

**Success Criteria**:
- ✅ Command runs without errors
- ✅ Shows orchestrator endpoint
- ✅ Lists at least one active revision
- ✅ Replica status = "Healthy" (NOT "NotRunning" or "Unhealthy")
- ✅ Latest revision created after 2025-11-20 06:00 (after commit 062d501)

---

**Test 2: Run Health Diagnostics**
```bash
haymaker orch health \
  --app-name orch-dev-yc4hkcb2vv \
  --subscription-id c190c55a-9ab2-4b1e-92c4-cc8b1a032285 \
  --resource-group haymaker-dev-rg \
  --deep \
  --verbose
```

**Expected Output**:
```
Health Check Results
====================
✓ Container App Status    PASS    App is running, 1 healthy replica
✓ Endpoint Connectivity   PASS    DNS and TCP connection successful
✓ Replica Health          PASS    All replicas healthy
✓ HTTP Health Endpoint    PASS    Endpoint responds with 200/404
```

**Success Criteria**:
- ✅ All checks show "PASS" or "WARN" (no "FAIL")
- ✅ Container app status check passes
- ✅ Endpoint connectivity check passes
- ✅ No connection refused errors

---

**Test 3: Check Replica Details**
```bash
# Get latest revision name from status output
LATEST_REVISION="<revision-name-from-status>"

haymaker orch replicas \
  --app-name orch-dev-yc4hkcb2vv \
  --subscription-id c190c55a-9ab2-4b1e-92c4-cc8b1a032285 \
  --resource-group haymaker-dev-rg \
  --revision $LATEST_REVISION
```

**Expected Output**:
```
Replica Status
==============
NAME                                      STATUS   CPU    MEMORY   RESTARTS
orch-dev-yc4hkcb2vv--0009-xxx            Running  0.1    512Mi    0
```

**Success Criteria**:
- ✅ At least 1 replica listed
- ✅ STATUS = "Running"
- ✅ RESTARTS = 0 or low number

---

### Step 4: Verify Azure Functions Discovery

Check container logs to confirm functions were discovered.

```bash
# Use Azure CLI (haymaker orch logs not fully implemented yet)
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --tail 200 | grep -A 12 "Found the following functions:"
```

**Expected Output**:
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
- ✅ "Found the following functions:" appears in logs
- ✅ All 10 functions listed (1 timer + 1 orchestrator + 8 activities)
- ✅ No Python import errors
- ✅ No "app = None" errors

---

### Step 5: Test Agent Deployment (End-to-End)

**Option A: Trigger via Timer** (automatic):
```bash
# Wait for next timer trigger (check KEDA CRON schedule)
# Monitor orchestrator logs
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --follow true | grep -E "(Orchestration|Agent|Deploy)"
```

**Option B: Trigger Manually** (if HTTP endpoint available):
```bash
# Get orchestrator endpoint
ENDPOINT=$(az containerapp show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

# Trigger orchestration
curl -X POST https://$ENDPOINT/api/orchestrate_haymaker_run \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": ["containers-01-simple-web-app"],
    "timeout": 600
  }'
```

**Expected Flow**:
```
[timestamp] Orchestration started
[timestamp] Validating environment
[timestamp] Selecting scenarios
[timestamp] Creating service principal
[timestamp] Deploying agent container
[timestamp] Agent status: Running
[timestamp] Monitoring agent execution
[timestamp] Agent completed
```

**Success Criteria**:
- ✅ Orchestration triggers successfully
- ✅ Scenario selection works
- ✅ Agent container deploys
- ✅ Agent reaches "Running" state
- ✅ Orchestrator monitors agent status
- ✅ Agent completes without errors

---

### Step 6: Verify 128GB Resources

Check that orchestrator is using the E16 workload profile with 128GB RAM.

```bash
az containerapp show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --query "{WorkloadProfile:properties.workloadProfileName, CPU:properties.template.containers[0].resources.cpu, Memory:properties.template.containers[0].resources.memory}" \
  --output table
```

**Expected**:
- WorkloadProfile: E16 (or similar 128GB profile)
- CPU: 16 cores
- Memory: 128Gi

---

## Verification Checklist

After running all steps above, check off:

**Container Startup (Part 1)**:
- [ ] New revision created after commit 062d501
- [ ] Replica status = "Running" (NOT "NotRunning")
- [ ] Logs available and viewable
- [ ] Azure Functions runtime initialized
- [ ] 10 functions discovered and loaded
- [ ] HTTP endpoint responds (not connection refused)
- [ ] No Python import errors in logs

**CLI Commands (Part 2)**:
- [ ] `haymaker orch status` works
- [ ] `haymaker orch health` runs all checks
- [ ] `haymaker orch replicas` shows replica details
- [ ] `haymaker orch logs` provides guidance
- [ ] Output formats work (table, JSON, YAML)
- [ ] Error handling works (clear messages, correct exit codes)

**Agent Deployment (End-to-End)**:
- [ ] Orchestration can be triggered
- [ ] Agent container deploys successfully
- [ ] Agent reaches "Running" state
- [ ] Orchestrator monitors agent
- [ ] Agent completes execution
- [ ] 128GB memory profile configured

---

## Quick Verification Commands

**After `az login`, run these in order**:

```bash
# 1. Check orchestrator status
haymaker orch status \
  --app-name orch-dev-yc4hkcb2vv \
  --subscription-id c190c55a-9ab2-4b1e-92c4-cc8b1a032285 \
  --resource-group haymaker-dev-rg

# 2. Run health checks
haymaker orch health \
  --app-name orch-dev-yc4hkcb2vv \
  --subscription-id c190c55a-9ab2-4b1e-92c4-cc8b1a032285 \
  --resource-group haymaker-dev-rg \
  --deep

# 3. Check replicas (use revision name from status output)
haymaker orch replicas \
  --app-name orch-dev-yc4hkcb2vv \
  --subscription-id c190c55a-9ab2-4b1e-92c4-cc8b1a032285 \
  --resource-group haymaker-dev-rg \
  --revision <REVISION_NAME>

# 4. Verify function discovery
az containerapp logs show \
  --name orch-dev-yc4hkcb2vv \
  --resource-group haymaker-dev-rg \
  --tail 200 | grep -A 12 "Found the following functions:"
```

---

## Expected Timeline

| Step | Duration | Description |
|------|----------|-------------|
| **Step 1** | 2 min | Azure re-authentication |
| **Step 2** | 1 min | CLI verification (already installed) |
| **Step 3** | 5 min | Test 3 haymaker orch commands |
| **Step 4** | 5 min | Check function discovery in logs |
| **Step 5** | 30-60 min | Trigger and monitor agent deployment |
| **Step 6** | 2 min | Verify 128GB configuration |
| **Total** | 45-75 min | Complete end-to-end verification |

---

## Troubleshooting

### If `haymaker orch status` fails with authentication error:
```bash
# Re-run az login
az logout
az login --tenant "c7674d41-af6c-46f5-89a5-d41495d2151e"
```

### If container still shows "NotRunning":
- The merge conflict fix may not have deployed yet
- Check GitOps workflow status: `gh run list --workflow=deploy-container-apps-dev.yml`
- Wait for new image to build and deploy

### If functions not discovered:
- Check logs for ImportError or ModuleNotFoundError
- Verify function_app.py exists in container
- Check that `app` is not None in logs

---

## Success = Issue #26 Fully Resolved

When all checks pass:
- ✅ Container startup issue resolved (Part 1)
- ✅ CLI diagnostic commands working (Part 2)
- ✅ Orchestrator can deploy and monitor agents (End-to-End)
- ✅ 128GB resources properly configured

**Then**:
1. Update PR #27 with test results
2. Merge PR #27
3. Close Issue #26
4. Celebrate! 🎉

---

**CURRENT BLOCKER**: Azure authentication expired
**NEXT ACTION**: Run `az login` then execute Step 3 commands above

