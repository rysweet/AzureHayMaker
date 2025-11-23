# HayMaker CLI Diagnostic Features - Feature Specification

## Executive Summary

During Container Apps orchestrator deployment and testing, numerous Azure CLI commands were required for diagnostics and troubleshooting. This document proposes adding diagnostic capabilities to the HayMaker CLI to streamline orchestrator management and debugging.

## Problem Statement

Current workflow requires:
- Manual Azure CLI commands for status checking
- Multiple steps to diagnose container failures
- No unified interface for orchestrator health monitoring
- Difficult to track deployment state across revisions
- No easy way to view container logs or startup failures

## Diagnostic Commands Used

### 1. Orchestrator Status Check
**Azure CLI Commands:**
```bash
az containerapp show --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv

az containerapp revision list --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg \
  --query "[?properties.active==\`true\`].{name:name, traffic:properties.trafficWeight, replicas:properties.replicas, health:properties.healthState}"
```

**What Info Needed:**
- Orchestrator endpoint URL
- Active revisions and traffic distribution
- Replica count and health status
- Whether orchestrator is scaled up or down

**Proposed CLI Command:**
```bash
haymaker orch status [--format json|table]
```

**Output:**
```
Orchestrator Status
===================
Endpoint: https://orch-dev-yc4hkcb2vv.ashyocean-9cc3722e.westus2.azurecontainerapps.io
Status: Running (scaled to 1 replica)

Active Revisions:
NAME                      TRAFFIC  REPLICAS  HEALTH    CREATED
orch-dev-yc4hkcb2vv--0002    0%       1      Healthy   2025-11-19T01:21:18Z
orch-dev-yc4hkcb2vv--0008   100%      0      None      2025-11-19T20:56:51Z
```

### 2. Replica Diagnostics
**Azure CLI Commands:**
```bash
az containerapp replica list --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg \
  --revision orch-dev-yc4hkcb2vv--0000008 \
  --query "[].{name:name, status:properties.runningState, created:properties.createdTime}"
```

**What Info Needed:**
- Replica running state (Running/NotRunning/Failed)
- Creation timestamp
- Why replica failed to start
- Container startup errors

**Proposed CLI Command:**
```bash
haymaker orch replicas [--revision REVISION] [--show-failed]
```

**Output:**
```
Replica Status (revision: orch-dev-yc4hkcb2vv--0008)
====================================================
NAME                                      STATUS       CREATED              ERROR
orch-dev-yc4hkcb2vv--0008-5478db65ff-pg  NotRunning   2025-11-19 20:56:52  ImagePullError: manifest not found
```

### 3. Container Logs
**Azure CLI Commands:**
```bash
az containerapp logs show --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg \
  --tail 50 --follow false
```

**What Info Needed:**
- Container startup logs
- Application errors
- Azure Functions runtime initialization
- Why Functions aren't being discovered

**Proposed CLI Command:**
```bash
haymaker orch logs [--tail N] [--follow] [--revision REVISION]
```

**Output:**
```
[2025-11-19 21:00:05] INFO  - Starting Azure Functions runtime...
[2025-11-19 21:00:06] ERROR - Missing host.json configuration file
[2025-11-19 21:00:06] ERROR - Container failed to start
```

### 4. Image Verification
**Azure CLI Commands:**
```bash
az acr repository show --name haymakerorchacr --repository haymaker-orchestrator
az acr repository show-tags --name haymakerorchacr --repository haymaker-orchestrator --orderby time_desc
```

**What Info Needed:**
- Latest image tag
- When image was built
- Image SHA for specific commit
- Image size and layers

**Proposed CLI Command:**
```bash
haymaker orch image [--show-tags] [--show-history]
```

**Output:**
```
Current Image
=============
Repository: haymakerorchacr.azurecr.io/haymaker-orchestrator
Tag: latest (f05dcd34ecf3209fc97199e6d1e49dfb76d0fff0)
Built: 2025-11-19 21:05:15 UTC
Size: 1.2 GB

Recent Tags:
f05dcd34ecf3209fc97199e6d1e49dfb76d0fff0  2025-11-19 21:05:15
f80ed30ff39396c05b7eb90f39f8ead3d6d630ef  2025-11-19 20:52:00
86a07ffe9380dcad5832827dee03ad522c748d60  2025-11-19 16:53:02
```

### 5. Revision Management
**Azure CLI Commands:**
```bash
az containerapp update --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg \
  --min-replicas 1 --max-replicas 1

az containerapp revision set-mode --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg \
  --mode multiple

az containerapp ingress traffic set --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg \
  --revision-weight orch-dev-yc4hkcb2vv--0000002=100
```

**What Info Needed:**
- Manually scale orchestrator for testing
- Switch traffic between revisions
- Roll back to previous working revision

**Proposed CLI Commands:**
```bash
# Scale orchestrator
haymaker orch scale --replicas N

# Switch traffic between revisions
haymaker orch traffic --revision REVISION --weight PERCENTAGE

# Rollback to previous revision
haymaker orch rollback [--to-revision REVISION]
```

**Output:**
```bash
$ haymaker orch scale --replicas 1
✓ Scaled orchestrator to 1 replica
  Waiting for replica to start...
  ✓ Replica is Running

$ haymaker orch rollback
Available revisions:
  1. orch-dev-yc4hkcb2vv--hostjson (current, 100% traffic, 0 replicas, None health)
  2. orch-dev-yc4hkcb2vv--0002 (0% traffic, 1 replica, Healthy)

Rolling back to revision #2 (orch-dev-yc4hkcb2vv--0002)...
✓ Traffic routed to orch-dev-yc4hkcb2vv--0002 (100%)
```

### 6. Deployment Monitoring
**Azure CLI Commands:**
```bash
gh run list --workflow=deploy-containerapps.yml --limit 1
gh run watch 19516067694 --interval 10
```

**What Info Needed:**
- GitOps deployment status
- Which stage is running
- Build/deploy failures
- When deployment completed

**Proposed CLI Command:**
```bash
haymaker deploy status [--watch] [--run-id ID]
```

**Output:**
```
Deployment Status (Run #19516067694)
====================================
Status: In Progress (4m 32s elapsed)

Stages:
✓ Validate Bicep Templates (31s)
✓ Build and Push Image (1m 52s)
⟳ Deploy Infrastructure (2m 9s, in progress)
  Deploying Container Apps Infrastructure...
⋯ Validate Deployment (pending)

Last Update: 2025-11-19 21:08:45 UTC
```

### 7. Configuration Validation
**Azure CLI Commands:**
```bash
az containerapp revision show --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg \
  --revision orch-dev-yc4hkcb2vv--0000007 \
  --query "properties.template.containers[0].{image:image, env:env, resources:resources}"
```

**What Info Needed:**
- Environment variables configured
- Resource limits (CPU, memory)
- Image being used
- Missing configuration

**Proposed CLI Command:**
```bash
haymaker orch config [--show-env] [--show-resources]
```

**Output:**
```
Orchestrator Configuration
==========================
Image: haymakerorchacr.azurecr.io/haymaker-orchestrator:latest
Profile: E16 (128GB RAM, 16 vCPU)

Environment Variables:
AZURE_TENANT_ID          = c7674d41-af6c-46f5-89a5-d41495d2151e
AZURE_SUBSCRIPTION_ID    = c190c55a-9ab2-4b1e-92c4-cc8b1a032285
KEY_VAULT_URL            = https://haymaker-dev-yc4hkc-kv.vault.azure.net/
STORAGE_ACCOUNT_NAME     = haymakerdevyc4hkcb2
COSMOSDB_ENDPOINT        = (not set) ⚠️
SIMULATION_SIZE          = small

Resources:
CPU:    16 cores
Memory: 128 GiB
```

### 8. Health Check
**Current Approach:**
```bash
curl -s https://orch-dev-yc4hkcb2vv.ashyocean-9cc3722e.westus2.azurecontainerapps.io/api/execute
```

**Proposed CLI Command:**
```bash
haymaker orch health [--verbose]
```

**Output:**
```
Orchestrator Health Check
=========================
Endpoint: https://orch-dev-yc4hkcb2vv.ashyocean-9cc3722e.westus2.azurecontainerapps.io
Status: ✗ Unhealthy

Checks:
✓ DNS Resolution        (12ms)
✓ TCP Connection        (45ms)
✗ HTTP Response         (404 Not Found)
✗ API Endpoints         (/api/execute not responding)
✗ Functions Runtime     (Not initialized)

Diagnosis: Azure Functions runtime not discovering function_app.py
Suggestion: Check container logs with: haymaker orch logs
```

## Proposed CLI Architecture

### Command Structure
```
haymaker orch <command> [options]

Commands:
  status      Show orchestrator status and active revisions
  replicas    List replica status and diagnostics
  logs        View container logs
  image       Show current image and build history
  scale       Scale orchestrator replicas
  traffic     Manage traffic distribution between revisions
  rollback    Rollback to previous revision
  config      Show orchestrator configuration
  health      Check orchestrator health and connectivity
```

### Integration Points

1. **Azure SDK Integration**
   - Use Azure SDK for Python instead of subprocess az CLI calls
   - Reuse authentication from environment/Azure CLI
   - Support managed identity when running in Azure

2. **Configuration**
   - Read Container App name from config file or environment
   - Support multiple environments (dev/staging/prod)
   - Store last used configuration for convenience

3. **Output Formats**
   - Table format (default, human-readable)
   - JSON format (for scripting)
   - Compact format (single-line status)

### Implementation Phases

**Phase 1: Core Status Commands** (Week 1)
- `haymaker orch status`
- `haymaker orch replicas`
- `haymaker orch logs`
- `haymaker orch health`

**Phase 2: Management Commands** (Week 2)
- `haymaker orch scale`
- `haymaker orch rollback`
- `haymaker orch config`

**Phase 3: Advanced Features** (Week 3)
- `haymaker orch image`
- `haymaker orch traffic`
- `haymaker deploy status`
- Watch/follow modes for all commands

### Testing Strategy

1. **Unit Tests**
   - Mock Azure SDK calls
   - Test command parsing and output formatting
   - Validate error handling

2. **Integration Tests**
   - Test against dev environment
   - Verify actual Azure API calls
   - Test rollback scenarios

3. **E2E Tests**
   - Full deployment workflow
   - Failure recovery scenarios
   - Multi-revision management

## Benefits

1. **Unified Interface**: Single CLI for all orchestrator operations
2. **Faster Debugging**: Diagnose issues in seconds instead of minutes
3. **Better UX**: Human-readable output with actionable suggestions
4. **Automation**: JSON output enables scripting and CI/CD integration
5. **Knowledge Capture**: CLI embeds Azure best practices and common workflows

## Alternative Considered

**Azure Portal Dashboard**
- Pros: Visual, no CLI needed
- Cons: Not scriptable, slower for power users, requires browser

**Standalone Diagnostic Tool**
- Pros: Could be more feature-rich
- Cons: Another tool to install, not integrated with HayMaker workflow

## Open Questions

1. Should CLI support agent operations (deploy/monitor) or just orchestrator?
2. How to handle authentication for team members without Azure CLI setup?
3. Should we add `haymaker orch restart` command?
4. Do we need `haymaker orch exec` for remote container execution?

## Success Metrics

- Time to diagnose orchestrator issues reduced by 80%
- Number of manual Azure CLI commands reduced to zero for common tasks
- User satisfaction with debugging experience

## References

- Azure Container Apps CLI: https://learn.microsoft.com/en-us/cli/azure/containerapp
- Azure SDK for Python: https://github.com/Azure/azure-sdk-for-python
- Click CLI framework: https://click.palletsprojects.com/
