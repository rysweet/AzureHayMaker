# Deploy Orchestrator to Azure Container Apps

Simple deployment guide for the FastAPI orchestrator.

## Prerequisites

1. Azure CLI installed and logged in
2. Container registry created
3. Container Apps environment created
4. All required secrets in Key Vault

## Step 1: Build and Push Image

```bash
# Set variables
export RESOURCE_GROUP="azure-haymaker-rg"
export CONTAINER_REGISTRY="yourregistry"
export ACR_NAME="${CONTAINER_REGISTRY}.azurecr.io"

# Log in to ACR
az acr login --name $CONTAINER_REGISTRY

# Build and push (using ACR build for simplicity)
az acr build \
  --registry $CONTAINER_REGISTRY \
  --image azure-haymaker-orchestrator:latest \
  --file Dockerfile.orchestrator \
  .
```

## Step 2: Create Container App

```bash
# Set environment variables
export CONTAINER_ENV="haymaker-container-env"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_CLIENT_ID="your-client-id"
export KEY_VAULT_URL="https://your-keyvault.vault.azure.net/"
export SERVICE_BUS_NAMESPACE="your-servicebus-namespace"
export CONTAINER_IMAGE="azure-haymaker-agent:latest"
export SIMULATION_SIZE="small"
export STORAGE_ACCOUNT_NAME="yourstorageaccount"
export TABLE_STORAGE_ACCOUNT_NAME="yourtablestorageaccount"
export LOG_ANALYTICS_WORKSPACE_ID="your-workspace-id"

# Create Container App
az containerapp create \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_NAME/azure-haymaker-orchestrator:latest \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 2 \
  --memory 4Gi \
  --registry-server $ACR_NAME \
  --registry-identity system \
  --env-vars \
    AZURE_TENANT_ID=$AZURE_TENANT_ID \
    AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
    AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
    KEY_VAULT_URL=$KEY_VAULT_URL \
    SERVICE_BUS_NAMESPACE=$SERVICE_BUS_NAMESPACE \
    CONTAINER_REGISTRY=$ACR_NAME \
    CONTAINER_IMAGE=$CONTAINER_IMAGE \
    SIMULATION_SIZE=$SIMULATION_SIZE \
    STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT_NAME \
    TABLE_STORAGE_ACCOUNT_NAME=$TABLE_STORAGE_ACCOUNT_NAME \
    LOG_ANALYTICS_WORKSPACE_ID=$LOG_ANALYTICS_WORKSPACE_ID \
    RESOURCE_GROUP_NAME=$RESOURCE_GROUP
```

## Step 3: Enable Managed Identity

```bash
# Enable system-assigned managed identity (if not already enabled)
az containerapp identity assign \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --system-assigned

# Get the principal ID
PRINCIPAL_ID=$(az containerapp identity show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --query principalId -o tsv)

echo "Principal ID: $PRINCIPAL_ID"
```

## Step 4: Grant Permissions

```bash
# Grant Key Vault access
az keyvault set-policy \
  --name your-keyvault \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list

# Grant Storage access
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT_NAME

# Grant Table Storage access
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Storage Table Data Contributor" \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$TABLE_STORAGE_ACCOUNT_NAME

# Grant Service Bus access
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Azure Service Bus Data Owner" \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ServiceBus/namespaces/$SERVICE_BUS_NAMESPACE

# Grant subscription-level permissions for resource management
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Contributor" \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID
```

## Step 5: Verify Deployment

```bash
# Get the FQDN
FQDN=$(az containerapp show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Orchestrator URL: https://$FQDN"

# Test health endpoint
curl https://$FQDN/

# Test metrics endpoint
curl https://$FQDN/api/metrics

# Test scenarios endpoint
curl https://$FQDN/api/scenarios
```

## Step 6: View Logs

```bash
# Stream logs
az containerapp logs show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --follow

# Or use Log Analytics
az monitor log-analytics query \
  --workspace $LOG_ANALYTICS_WORKSPACE_ID \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'haymaker-orchestrator' | order by TimeGenerated desc | take 100"
```

## Update Deployment

When you make changes:

```bash
# Build and push new image
az acr build \
  --registry $CONTAINER_REGISTRY \
  --image azure-haymaker-orchestrator:latest \
  --file Dockerfile.orchestrator \
  .

# Update container app (it will pull latest automatically)
az containerapp update \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME/azure-haymaker-orchestrator:latest
```

## Troubleshooting

### Container won't start

```bash
# Check logs
az containerapp logs show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --tail 100

# Check revisions
az containerapp revision list \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --query "[].{Name:name, Active:properties.active, Created:properties.createdTime, Status:properties.runningState}"
```

### Health check fails

```bash
# Check ingress configuration
az containerapp ingress show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP

# Test health endpoint directly
curl https://$FQDN/
```

### Permission errors

```bash
# Verify managed identity has required permissions
az role assignment list \
  --assignee $PRINCIPAL_ID \
  --all

# Check Key Vault access policies
az keyvault show \
  --name your-keyvault \
  --query properties.accessPolicies
```

## Cost Optimization

The orchestrator runs 24/7 but only executes 4x daily. To reduce costs:

1. Use smallest CPU/memory that works (2 CPU, 4Gi RAM is a good start)
2. Set min-replicas to 1 (don't need HA for this workload)
3. Consider using Azure Container Instances for on-demand execution
4. Monitor actual resource usage and adjust:

```bash
az monitor metrics list \
  --resource /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/haymaker-orchestrator \
  --metric "CpuUsage" \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

## Security

1. **Managed Identity**: Container App uses managed identity - no secrets in code
2. **Key Vault**: All secrets retrieved from Key Vault at runtime
3. **Private networking**: Consider VNet integration if needed:

```bash
az containerapp update \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --set properties.configuration.ingress.external=false
```

4. **Least privilege**: Container only has permissions it needs

## Monitoring

Set up alerts for orchestration failures:

```bash
# Alert on health check failures
az monitor metrics alert create \
  --name orchestrator-health-alert \
  --resource-group $RESOURCE_GROUP \
  --scopes /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/haymaker-orchestrator \
  --condition "avg Percentage CPU > 80" \
  --description "Orchestrator CPU usage is high"
```

## Next Steps

1. Set up Application Insights for detailed monitoring
2. Configure auto-scaling if needed (though 1 replica is usually sufficient)
3. Set up CI/CD pipeline for automated deployments
4. Configure backup and disaster recovery
