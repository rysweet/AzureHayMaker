# Function App Deployment Issue - Diagnosis and Partial Resolution

## Problem Statement
Function App container crashes with exit code 134 (SIGABRT) during startup, causing 503 errors on all API endpoints.

## Root Causes Identified

### 1. Missing Required Environment Variables ✅ FIXED
The Function App was missing critical environment variables required by `azure_haymaker/orchestrator/config.py`:

**Missing Variables:**
- `SERVICE_BUS_NAMESPACE` - Required for Service Bus operations
- `CONTAINER_REGISTRY` - Required for container management
- `CONTAINER_IMAGE` - Required for agent container deployment
- `SIMULATION_SIZE` - Required for workload sizing
- `LOG_ANALYTICS_WORKSPACE_ID` - Required for logging
- `RESOURCE_GROUP_NAME` - Optional but recommended
- `SERVICE_BUS_TOPIC` - Optional but recommended

**Solution Applied:**
1. Updated `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/function-app.bicep` to accept new parameters
2. Updated `/Users/ryan/src/AzureHayMaker/infra/bicep/main.bicep` to pass required values to function-app module
3. Manually added environment variables to existing Function App: `haymaker-dev-yow3ex-func`

### 2. Missing Azure Functions Configuration Files ✅ FIXED
The deployment was missing critical Azure Functions configuration files:

**Missing Files:**
- `src/requirements.txt` - Azure Functions needs this to install Python dependencies
- `src/host.json` - Required for Azure Functions runtime configuration
- `src/function_app.py` - Entry point for Azure Functions runtime

**Solution Applied:**
1. Generated `requirements.txt` from `pyproject.toml` using `uv pip compile`
2. Created `host.json` with proper Azure Functions v4 configuration
3. Created `function_app.py` that imports and exposes the app from `azure_haymaker.orchestrator`

## Remaining Issue ❌ NOT RESOLVED

### SIGABRT Crash Still Occurring
Despite fixing the environment variables and adding required files, the container still crashes with exit code 134 after ~50-60 seconds.

**Error Pattern:**
```
Container start method finished after 5968 ms.
Container has finished running with exit code: 134.
Site container: haymaker-dev-yow3ex-func terminated during site startup.
Site startup probe failed after 57.4392071 seconds.
```

### Possible Remaining Causes

#### 1. Python 3.13 Compatibility Issue
The project specifies Python 3.13, which is very new. Possible issues:
- Azure Functions Python 3.13 runtime may not be fully stable
- Some dependencies may not be compatible with Python 3.13
- The base image `azure-functions/python:4-python3.13-appservice-stage2` may have issues

**Recommendation:** Try downgrading to Python 3.11 (well-supported and stable)

#### 2. Memory/Resource Exhaustion
The crash happens after ~50 seconds, which could indicate:
- Out of memory during dependency installation
- Stack overflow during module loading
- Timeout during heavy initialization

**Recommendation:**
- Check Application Insights for memory metrics
- Try upgrading from Standard (S1) to Premium plan for more resources
- Add more logging to identify which module is loading when crash occurs

#### 3. Circular Import or Module Loading Issue
The `azure_haymaker` package structure may have circular dependencies:
```
function_app.py (root)
  └─> azure_haymaker.orchestrator
       └─> Multiple modules with complex imports
```

**Recommendation:**
- Add try/except with logging around imports in `function_app.py`
- Check for circular imports in the module structure
- Consider lazy loading of heavy modules

#### 4. Missing System Dependencies
Some Python packages may require system libraries that aren't in the container:
- `cryptography` needs OpenSSL
- Azure SDK packages may need specific system libs

**Recommendation:**
- Check if any packages need custom build flags
- Consider creating a custom Docker container with pre-installed dependencies

## Files Modified

### Infrastructure (Bicep)
1. `/Users/ryan/src/AzureHayMaker/infra/bicep/modules/function-app.bicep`
   - Added parameters: `serviceBusNamespace`, `containerRegistryLoginServer`, `containerImage`, `simulationSize`, `logAnalyticsWorkspaceId`, `resourceGroupName`
   - Added corresponding app settings

2. `/Users/ryan/src/AzureHayMaker/infra/bicep/main.bicep`
   - Updated function-app module invocation to pass new parameters

### Application Code
3. `/Users/ryan/src/AzureHayMaker/src/requirements.txt` (NEW)
   - Generated from pyproject.toml
   - Contains all Python dependencies with pinned versions

4. `/Users/ryan/src/AzureHayMaker/src/host.json` (NEW)
   - Azure Functions v4 configuration
   - Logging configuration
   - Extension bundle configuration

5. `/Users/ryan/src/AzureHayMaker/src/function_app.py` (NEW)
   - Entry point that imports app from azure_haymaker.orchestrator
   - Exposes app to Azure Functions runtime

## Next Steps to Resolve

### Immediate Actions
1. **Try Python 3.11**: Update `pyproject.toml` and Bicep to use Python 3.11
   ```toml
   requires-python = ">=3.11,<3.13"
   ```

2. **Add Debug Logging**: Modify `function_app.py` to add detailed logging:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("Starting function_app.py import")

   try:
       from azure_haymaker.orchestrator import app
       logger.info("Successfully imported app from orchestrator")
   except Exception as e:
       logger.error(f"Failed to import app: {e}", exc_info=True)
       raise
   ```

3. **Check Application Insights**: Query for detailed error messages:
   ```bash
   az monitor app-insights query \
     --app haymaker-dev-yow3ex-func-insights \
     --analytics-query "traces | where timestamp > ago(1h) | order by timestamp desc"
   ```

4. **Enable SSH for Container Inspection**: Add SSH to the container to inspect the crash in real-time

### Alternative Approaches

#### Option A: Deploy to New Function App
The Bicep deployment created a new Function App (`haymaker-dev-ceg5u6-func`) with all the correct settings. Consider:
1. Inject secrets into the new Key Vault
2. Deploy code to the new Function App
3. Test if it starts successfully
4. Delete the old Function App if successful

#### Option B: Simplify the Application
Create a minimal test version:
1. Comment out complex imports in orchestrator.py
2. Create a simple HTTP-triggered function
3. Deploy and verify it works
4. Gradually add back functionality

#### Option C: Use Container App Instead
The infrastructure already includes Container Apps Environment. Consider:
1. Package the application as a Docker container
2. Deploy to Azure Container Apps instead of Functions
3. More control over the runtime environment
4. Easier debugging

## Deployment Commands

### Current Function App (yow3ex)
```bash
# Updated environment variables (DONE)
az functionapp config appsettings set \
  --name haymaker-dev-yow3ex-func \
  --resource-group haymaker-dev-rg \
  --settings \
    SERVICE_BUS_NAMESPACE="haymaker-dev-yow3ex-bus" \
    CONTAINER_REGISTRY="" \
    CONTAINER_IMAGE="azure-haymaker-agent:latest" \
    SIMULATION_SIZE="small" \
    LOG_ANALYTICS_WORKSPACE_ID="/subscriptions/.../workspaces/haymaker-dev-logs" \
    RESOURCE_GROUP_NAME="haymaker-dev-rg" \
    SERVICE_BUS_TOPIC="agent-logs"

# Deploy code (DONE - still crashing)
cd src
zip -r ~/function-app-deploy.zip .
az functionapp deployment source config-zip \
  --name haymaker-dev-yow3ex-func \
  --resource-group haymaker-dev-rg \
  --src ~/function-app-deploy.zip \
  --build-remote true
```

### New Function App (ceg5u6) - If Using This Approach
```bash
# 1. Grant Key Vault Secrets Officer role to GitHub SP
SP_OBJECT_ID=$(az ad sp show --id e2c7f4c6-00d7-4f62-9bb1-84b877fb5d7e --query id -o tsv)
KEY_VAULT_ID=$(az keyvault show --name haymaker-dev-ceg5u6-kv --query id -o tsv)
az role assignment create \
  --role "b86a8fe4-44ce-4948-aee5-eccb2c155cd7" \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "$KEY_VAULT_ID"

# 2. Inject secrets
az keyvault secret set \
  --vault-name haymaker-dev-ceg5u6-kv \
  --name main-sp-client-secret \
  --value "$MAIN_SP_CLIENT_SECRET"

az keyvault secret set \
  --vault-name haymaker-dev-ceg5u6-kv \
  --name anthropic-api-key \
  --value "$ANTHROPIC_API_KEY"

az keyvault secret set \
  --vault-name haymaker-dev-ceg5u6-kv \
  --name log-analytics-workspace-key \
  --value "$LOG_ANALYTICS_WORKSPACE_KEY"

# 3. Wait for RBAC propagation
sleep 90

# 4. Deploy code
cd src
zip -r ~/function-app-deploy.zip .
az functionapp deployment source config-zip \
  --name haymaker-dev-ceg5u6-func \
  --resource-group haymaker-dev-rg \
  --src ~/function-app-deploy.zip \
  --build-remote true
```

## Logs and Diagnostics

### Recent Errors
The most recent deployment logs show:
- Container starts successfully
- Runs for ~50-60 seconds
- Crashes with SIGABRT (exit code 134)
- No Python-level error messages visible in logs

### Log Locations
- Docker logs: `LogFiles/2025_11_18_lw0sdlwk0000G8_docker.log`
- Application logs: Should be in Application Insights but container crashes before they're written
- Kudu logs: Deployment logs available in LogFiles/kudu/trace/

## Summary

**✅ Fixed:**
- Missing environment variables
- Missing requirements.txt
- Missing host.json
- Missing function_app.py entry point

**❌ Still Broken:**
- Container crashes with SIGABRT during startup
- No Python application logs available
- 503 errors on all endpoints

**Most Likely Cause:** Python 3.13 compatibility issue or memory exhaustion during module loading

**Recommended Next Step:** Switch to Python 3.11 and redeploy
