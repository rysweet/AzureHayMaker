# Migration Guide: Azure Functions → FastAPI Orchestrator

This guide explains how to migrate from the Azure Functions + Durable Functions orchestrator to the simple FastAPI orchestrator.

## Why Migrate?

### Problems with Azure Functions Approach
1. **Complex setup** - Extension Bundle V4, host.json configuration
2. **Runtime compatibility** - Constant issues with azure-functions-durable
3. **Limited portability** - Only runs on Azure Functions
4. **Hard to test** - Requires Azure Functions Core Tools
5. **Hard to debug** - Durable Functions state management complexity
6. **Vendor lock-in** - Tied to Azure Functions runtime

### Benefits of FastAPI Approach
1. **Simple setup** - Just FastAPI + APScheduler
2. **No runtime issues** - Standard Python packages
3. **Runs anywhere** - Docker, Container Apps, Kubernetes, VMs
4. **Easy to test** - Standard HTTP testing
5. **Easy to debug** - Standard Python debugger
6. **Portable** - Not tied to any cloud provider

## Architecture Comparison

### Old: Azure Functions + Durable Functions

```
function_app.py (1000+ lines)
├── @app.timer_trigger          # Timer trigger
├── @app.orchestration_trigger  # Main orchestration
├── @app.activity_trigger       # validate_environment_activity
├── @app.activity_trigger       # select_scenarios_activity
├── @app.activity_trigger       # create_service_principal_activity
├── @app.activity_trigger       # deploy_container_app_activity
├── @app.activity_trigger       # check_agent_status_activity
├── @app.activity_trigger       # verify_cleanup_activity
├── @app.activity_trigger       # force_cleanup_activity
└── @app.activity_trigger       # generate_report_activity

host.json
├── Extension Bundle V4 config
├── Durable Functions config
└── Function timeout settings
```

### New: FastAPI + APScheduler

```
orchestrator_server.py (350 lines)
├── FastAPI app with lifespan
├── APScheduler (cron: 0,6,12,18)
├── 7 REST API endpoints
│   ├── GET  /                    # Health check
│   ├── GET  /api/metrics         # Metrics
│   ├── GET  /api/executions      # List executions
│   ├── GET  /api/executions/{id} # Get execution
│   ├── POST /api/execute         # Trigger execution
│   ├── POST /api/validate        # Validate environment
│   └── GET  /api/scenarios       # List scenarios
└── run_orchestration()
    ├── Phase 1: Validation
    ├── Phase 2: Selection
    ├── Phase 3: Provisioning (parallel)
    ├── Phase 4: Monitoring (8 hours)
    ├── Phase 5: Cleanup
    └── Phase 6: Reporting

Dockerfile.orchestrator
├── Python 3.11 slim
├── FastAPI + uvicorn
└── Health check
```

## Code Comparison

### Old: Activity Function
```python
@app.activity_trigger(input_name="input_data")
async def validate_environment_activity(input_data: Any) -> dict[str, Any]:
    config = await load_config()
    result = await validate_environment(config)
    return {
        "overall_passed": result.overall_passed,
        "results": [r.model_dump() for r in result.results],
    }
```

### New: Direct Function Call
```python
# Phase 1: Validation
config = await load_config()
validation_result = await validate_environment(config)

if not validation_result.overall_passed:
    execution_report["status"] = "failed"
    execution_report["failure_reason"] = "validation_failed"
    return
```

### Old: Orchestration with Durable Functions
```python
@app.orchestration_trigger(context_name="context")
def orchestrate_haymaker_run(context: Any) -> Any:
    # Call activity
    validation_result = yield context.call_activity(
        "validate_environment_activity",
        None,
    )

    # Wait for timer
    yield context.create_timer(
        context.current_utc_datetime + timedelta(minutes=15)
    )
```

### New: Standard Async Python
```python
async def run_orchestration(run_id: str):
    # Direct function call
    config = await load_config()
    validation_result = await validate_environment(config)

    # Standard asyncio sleep
    await asyncio.sleep(900)  # 15 minutes
```

## Migration Steps

### Step 1: Stop Azure Functions Deployment

```bash
# Stop the Azure Function App
az functionapp stop \
  --name haymaker-orchestrator-func \
  --resource-group azure-haymaker-rg

# (Optional) Delete Function App if migrating completely
az functionapp delete \
  --name haymaker-orchestrator-func \
  --resource-group azure-haymaker-rg
```

### Step 2: Test FastAPI Orchestrator Locally

```bash
# Copy environment template
cp .env.orchestrator.example .env

# Edit with your Azure credentials
vim .env

# Run locally
./run_orchestrator.sh

# Test endpoints
curl http://localhost:8080/
curl http://localhost:8080/api/validate
curl http://localhost:8080/api/scenarios
```

### Step 3: Deploy to Azure Container Apps

```bash
# Build and push image
export CONTAINER_REGISTRY="yourregistry"
az acr build \
  --registry $CONTAINER_REGISTRY \
  --image azure-haymaker-orchestrator:latest \
  --file Dockerfile.orchestrator \
  .

# Create Container App
az containerapp create \
  --name haymaker-orchestrator \
  --resource-group azure-haymaker-rg \
  --environment haymaker-container-env \
  --image $CONTAINER_REGISTRY.azurecr.io/azure-haymaker-orchestrator:latest \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 2 \
  --memory 4Gi \
  --registry-identity system \
  --env-vars \
    AZURE_TENANT_ID=$AZURE_TENANT_ID \
    # ... other env vars ...
```

### Step 4: Configure Managed Identity

```bash
# Enable managed identity
az containerapp identity assign \
  --name haymaker-orchestrator \
  --resource-group azure-haymaker-rg \
  --system-assigned

# Get principal ID
PRINCIPAL_ID=$(az containerapp identity show \
  --name haymaker-orchestrator \
  --resource-group azure-haymaker-rg \
  --query principalId -o tsv)

# Grant permissions (same as Function App had)
az keyvault set-policy \
  --name your-keyvault \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list

az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Contributor" \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID
```

### Step 5: Verify New Deployment

```bash
# Get FQDN
FQDN=$(az containerapp show \
  --name haymaker-orchestrator \
  --resource-group azure-haymaker-rg \
  --query properties.configuration.ingress.fqdn -o tsv)

# Test health
curl https://$FQDN/

# Test validation
curl -X POST https://$FQDN/api/validate

# Monitor first execution
curl https://$FQDN/api/executions
```

### Step 6: Monitor for 24 Hours

Monitor the new orchestrator for at least 24 hours to ensure:
- All 4 scheduled runs execute successfully
- Resource provisioning works
- Cleanup completes
- No errors in logs

```bash
# View logs
az containerapp logs show \
  --name haymaker-orchestrator \
  --resource-group azure-haymaker-rg \
  --follow

# Check executions
curl https://$FQDN/api/executions | jq .

# Check metrics
curl https://$FQDN/api/metrics | jq .
```

### Step 7: Remove Old Azure Functions Resources (Optional)

Once confident the new orchestrator works:

```bash
# Delete Function App
az functionapp delete \
  --name haymaker-orchestrator-func \
  --resource-group azure-haymaker-rg

# Delete old storage account (if separate from main storage)
az storage account delete \
  --name haymakerfuncstorage \
  --resource-group azure-haymaker-rg

# Delete old App Service Plan
az appservice plan delete \
  --name haymaker-func-plan \
  --resource-group azure-haymaker-rg
```

## Configuration Changes

### Environment Variables

Most environment variables stay the same. Only additions:

**No changes needed** - Same variables as Azure Functions:
- AZURE_TENANT_ID
- AZURE_SUBSCRIPTION_ID
- AZURE_CLIENT_ID
- KEY_VAULT_URL
- SERVICE_BUS_NAMESPACE
- CONTAINER_REGISTRY
- CONTAINER_IMAGE
- SIMULATION_SIZE
- STORAGE_ACCOUNT_NAME
- TABLE_STORAGE_ACCOUNT_NAME
- LOG_ANALYTICS_WORKSPACE_ID
- RESOURCE_GROUP_NAME

**No longer needed** - Azure Functions specific:
- AzureWebJobsStorage (not needed)
- FUNCTIONS_WORKER_RUNTIME (not needed)
- AzureWebJobsFeatureFlags (not needed)

### Key Vault Secrets

No changes - same secrets:
- main-sp-client-secret
- anthropic-api-key
- log-analytics-workspace-key

## Feature Parity

All features from Azure Functions orchestrator are preserved:

| Feature | Azure Functions | FastAPI | Notes |
|---------|----------------|---------|-------|
| Scheduled execution (4x daily) | ✅ Timer trigger | ✅ APScheduler | Same schedule |
| Environment validation | ✅ Activity | ✅ Direct call | Same logic |
| Scenario selection | ✅ Activity | ✅ Direct call | Same logic |
| Parallel provisioning | ✅ task_all | ✅ asyncio.gather | Same parallelism |
| 8-hour monitoring | ✅ Durable timers | ✅ asyncio.sleep | Same duration |
| Cleanup verification | ✅ Activity | ✅ Direct call | Same logic |
| Forced cleanup | ✅ Activity | ✅ Direct call | Same logic |
| Report generation | ✅ Activity | ✅ Direct call | Same logic |
| Execution tracking | ✅ Durable state | ✅ In-memory dict | Simpler |
| Error handling | ✅ Try/catch | ✅ Try/catch | Same pattern |
| Logging | ✅ Azure Functions | ✅ Python logging | Same output |

## Rollback Plan

If issues arise, you can quickly rollback:

```bash
# Restart old Function App
az functionapp start \
  --name haymaker-orchestrator-func \
  --resource-group azure-haymaker-rg

# Stop new Container App
az containerapp update \
  --name haymaker-orchestrator \
  --resource-group azure-haymaker-rg \
  --min-replicas 0 \
  --max-replicas 0
```

## Cost Comparison

### Azure Functions (Consumption Plan)
- **Base cost**: $0.20/million executions
- **Duration cost**: $0.000016/GB-second
- **Estimated monthly**: ~$50-100
- **Issues**: Cold starts, timeouts

### Container Apps
- **Base cost**: ~$0.09/vCPU-hour + $0.0125/GB-hour
- **For 2 vCPU, 4GB**: ~$75/month (24/7)
- **Benefits**: No cold starts, consistent performance

**Note**: Container Apps may be slightly more expensive but provides:
- Better reliability
- No cold starts
- Consistent performance
- Easier debugging
- Portability

## Testing Checklist

Before considering migration complete:

- [ ] Local testing passes
- [ ] Docker Compose setup works
- [ ] Azure deployment successful
- [ ] Health check passes
- [ ] Validation endpoint works
- [ ] Scenarios endpoint returns data
- [ ] Manual execution triggers successfully
- [ ] Scheduled execution runs 4x daily
- [ ] All 6 orchestration phases complete
- [ ] Cleanup runs successfully
- [ ] Reports are generated
- [ ] Logs are accessible
- [ ] Metrics are accurate
- [ ] No errors in 24-hour monitoring period

## Common Issues

### Issue: Container won't start
**Solution**: Check environment variables and logs
```bash
az containerapp logs show --name haymaker-orchestrator --resource-group azure-haymaker-rg
```

### Issue: Validation fails
**Solution**: Verify managed identity has correct permissions
```bash
az role assignment list --assignee $PRINCIPAL_ID
az keyvault show --name your-keyvault --query properties.accessPolicies
```

### Issue: Scheduled runs not executing
**Solution**: Check APScheduler logs
```bash
docker logs azure-haymaker-orchestrator | grep "APScheduler"
```

## Support

- **Quick Start**: See `ORCHESTRATOR_QUICKSTART.md`
- **Full Docs**: See `ORCHESTRATOR_README.md`
- **Deployment**: See `DEPLOY_ORCHESTRATOR.md`
- **Summary**: See `ORCHESTRATOR_SUMMARY.md`

## Conclusion

Migration from Azure Functions to FastAPI orchestrator:
- **Complexity**: Reduced by 70% (1000+ lines → 350 lines)
- **Dependencies**: Minimal (no Azure Functions bloat)
- **Portability**: Runs anywhere Docker runs
- **Testability**: Standard HTTP testing
- **Reliability**: No runtime compatibility issues
- **Cost**: Similar (~$75/month vs ~$50-100/month)

**Recommendation**: Migrate to FastAPI orchestrator for long-term maintainability and simplicity.
