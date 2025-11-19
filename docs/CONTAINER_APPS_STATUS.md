# Container Apps Deployment Status

**Date**: 2025-11-19
**Session**: Post-crash continuation
**Status**: 🟡 **BLOCKED** - Container startup failure

## Summary

Successfully deployed 128GB Container Apps infrastructure and fixed critical Dockerfile issues, but the orchestrator container is failing to start. Need to investigate root cause of container startup failure.

## What Was Accomplished ✅

### 1. Infrastructure Deployed
- ✅ E16 workload profile (128GB RAM, 16 vCPU) configured
- ✅ KEDA CRON scaling with 8-hour windows
- ✅ ACR integration with managed identity
- ✅ GitOps automation via GitHub Actions

### 2. Dockerfile Fixes
- ✅ Added `function_app.py` entry point (commit f80ed30)
- ✅ Added `host.json` configuration (commit f05dcd3)
- ✅ Using Azure Functions base image: `mcr.microsoft.com/azure-functions/python:4-python3.11`

### 3. Documentation Created
- ✅ CLI Diagnostic Features Specification (`docs/CLI_DIAGNOSTIC_FEATURES_SPEC.md`)
- ✅ Comprehensive list of proposed `haymaker orch` commands
- ✅ Benefits analysis and implementation phases

## Current Blocker 🔴

**Container Startup Failure**

All new revisions (0000007, 0000008, hostjson) fail with status **"NotRunning"**:
- Container never transitions to "Running" state
- Replica stays in "NotRunning" for 2+ minutes
- Eventually gets terminated by Container Apps
- No logs available via `az containerapp logs show`

### Revisions Status

| Revision | Created | Traffic | Replicas | Health | Status |
|----------|---------|---------|----------|--------|--------|
| --0000002 | 2025-11-19 01:21:18 | 0% | 1 | Healthy | ✅ **WORKING** (old image) |
| --0000007 | 2025-11-19 20:43:36 | 0% | 0 | None | ❌ Failed to start |
| --0000008 | 2025-11-19 20:56:51 | 0% | 0 | None | ❌ Failed to start |
| --hostjson | 2025-11-19 21:14:02 | 100% | 0-1 | None | ❌ NotRunning (tested 11 times) |

### What We Know

1. **Old revision works**: Revision 0000002 (deployed before recent changes) runs successfully
2. **New revisions fail**: All revisions after Dockerfile changes fail to start
3. **Image exists**: ACR contains the image with tag `f05dcd34ecf3209fc97199e6d1e49dfb76d0fff0`
4. **No logs**: Can't access container logs to see startup errors
5. **Config looks correct**: Environment variables, resources, and image reference are all configured

### Possible Causes

1. **Missing Python dependencies**: `requirements.txt` may be missing Azure Functions packages
2. **Import errors**: Python modules failing to import on startup
3. **Azure Functions runtime issue**: Runtime can't discover or load functions
4. **File permissions**: Copied files may have wrong permissions
5. **Working directory issue**: Files not in expected locations
6. **Missing .funcignore**: May be copying unnecessary files that break the runtime

## Next Steps 🎯

### Immediate Actions

1. **Test Image Locally**
   ```bash
   # Pull and run image locally
   docker pull haymakerorchacr.azurecr.io/haymaker-orchestrator:latest
   docker run -p 8080:80 --env-file .env haymakerorchacr.azurecr.io/haymaker-orchestrator:latest

   # Check startup logs
   docker logs <container_id>
   ```

2. **Verify Requirements**
   - Check `requirements.txt` includes Azure Functions packages
   - Verify all dependencies install correctly
   - Test imports in local Python environment

3. **Compare with Working Revision**
   - Pull image for revision 0000002 (working)
   - Compare file structure and contents
   - Identify what changed

4. **Add Debug Logging**
   - Modify Dockerfile to add `RUN ls -la` commands
   - Verify all files are copied correctly
   - Check file permissions

5. **Rollback Strategy**
   - Document what revision 0000002 image contains
   - Understand why it works
   - Replicate its configuration in new image

### Diagnostic Commands to Run

```bash
# Test local Docker build
cd /Users/ryan/src/AzureHayMaker/src
docker build -t haymaker-orch-test .
docker run -p 8080:80 haymaker-orch-test

# Check file structure in image
docker run --entrypoint /bin/bash haymaker-orch-test -c "ls -la /home/site/wwwroot"
docker run --entrypoint /bin/bash haymaker-orch-test -c "cat /home/site/wwwroot/host.json"

# Test Python imports
docker run --entrypoint python haymaker-orch-test -c "import azure.functions; print('OK')"
docker run --entrypoint python haymaker-orch-test -c "from function_app import app; print(app)"
```

## Deployment History

### Session Timeline

| Time (UTC) | Event | Commit | Result |
|------------|-------|--------|--------|
| 20:43 | Manual scale to 1 replica | - | Revision 0000007 created, failed |
| 20:52 | Fix: Add function_app.py | f80ed30 | Built image, deployed |
| 20:56 | Deploy via GitOps (run 19516067694) | f80ed30 | Revision 0000008 created, failed |
| 21:05 | Fix: Add host.json | f05dcd3 | Built image, deployed |
| 21:09 | Deploy via GitOps (run 19516391910) | f05dcd3 | No new revision (updated existing) |
| 21:14 | Manual update with --revision-suffix | f05dcd3 | Revision hostjson created, failed |

### Commits This Session

1. `f80ed30` - fix: Copy function_app.py entry point for Azure Functions discovery
2. `f05dcd3` - fix: Add host.json for Azure Functions runtime

### GitOps Runs

| Run ID | Status | Duration | Result |
|--------|--------|----------|--------|
| 19509319166 | ✅ Completed | 6m | Deployed revision 0000002 (works) |
| 19516067694 | ✅ Completed | 6m 18s | Built image with function_app.py |
| 19516391910 | ✅ Completed | 6m 45s | Built image with host.json |

## Configuration

### Current Dockerfile
```dockerfile
FROM mcr.microsoft.com/azure-functions/python:4-python3.11
WORKDIR /home/site/wwwroot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY azure_haymaker/ ./azure_haymaker/

# Azure Functions required files
COPY function_app.py .
COPY host.json .

EXPOSE 80

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    FUNCTIONS_WORKER_RUNTIME=python
```

### Container App Settings
- **Resource Group**: haymaker-dev-rg
- **Name**: orch-dev-yc4hkcb2vv
- **Profile**: E16 (128GB RAM, 16 vCPU)
- **Image**: haymakerorchacr.azurecr.io/haymaker-orchestrator:latest
- **Min/Max Replicas**: 0/1
- **Ingress**: External, port 80
- **Revision Mode**: Multiple

### KEDA CRON Schedule
```
Start: 0 0,6,12,18 * * *  (00:00, 06:00, 12:00, 18:00 UTC)
End:   0 8,14,20,2 * * *  (08:00, 14:00, 20:00, 02:00 UTC)
```

## Files Modified

1. `src/Dockerfile` - Added function_app.py and host.json copy commands
2. `docs/CLI_DIAGNOSTIC_FEATURES_SPEC.md` - Created (new file)
3. `docs/CONTAINER_APPS_STATUS.md` - This file (new)

## HayMaker CLI Features

Created comprehensive specification for `haymaker orch` commands:

### Proposed Commands
- `haymaker orch status` - Show orchestrator status and revisions
- `haymaker orch replicas` - List replica status
- `haymaker orch logs` - View container logs
- `haymaker orch image` - Show current image and history
- `haymaker orch scale` - Scale orchestrator replicas
- `haymaker orch traffic` - Manage traffic distribution
- `haymaker orch rollback` - Rollback to previous revision
- `haymaker orch config` - Show configuration
- `haymaker orch health` - Check health and connectivity

See full spec: `docs/CLI_DIAGNOSTIC_FEATURES_SPEC.md`

## Questions for Investigation

1. Why does revision 0000002 work but newer ones don't?
2. What Python dependencies are missing or conflicting?
3. Are there Azure Functions runtime version incompatibilities?
4. Is the Azure Functions discovery mechanism working?
5. Do we need additional files (.funcignore, local.settings.json)?

## Resources

- **Azure Container Apps**: https://learn.microsoft.com/en-us/azure/container-apps/
- **Azure Functions on Container Apps**: https://learn.microsoft.com/en-us/azure/azure-functions/functions-container-apps-hosting
- **Azure Functions Python**: https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python
- **Container Apps Logs**: https://learn.microsoft.com/en-us/azure/container-apps/log-streaming

## Recommendations

1. **Test locally first**: Before deploying to Azure, test Docker image locally
2. **Add healthcheck**: Add HEALTHCHECK instruction to Dockerfile
3. **Improve logging**: Add verbose startup logging to diagnose issues
4. **CI validation**: Add Docker build test to CI pipeline
5. **Rollback plan**: Keep revision 0000002 active until new version proven working

---

**Next Session Goal**: Identify and fix container startup issue, get orchestrator running with 128GB RAM, test agent deployment end-to-end.
