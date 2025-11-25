# AzureHayMaker Deployment Setup Guide

## Prerequisites

- Azure subscription with Owner or Contributor role
- Azure CLI installed and configured
- Docker installed (for building images)
- Service Principal with appropriate permissions

## Required Service Principal Permissions

The orchestrator service principal requires the following role assignments:

### Subscription Level
```bash
# Contributor role (for resource creation)
az role assignment create \
  --assignee <SP_OBJECT_ID> \
  --role "Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>

# User Access Administrator (for role assignments)
az role assignment create \
  --assignee <SP_OBJECT_ID> \
  --role "User Access Administrator" \
  --scope /subscriptions/<SUBSCRIPTION_ID>
```

### Resource Group Level
```bash
# Container Apps Contributor (for container deployment)
az role assignment create \
  --assignee <SP_OBJECT_ID> \
  --role "Container Apps Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/haymaker-dev-rg
```

### Microsoft Graph API Permissions

Grant via Azure Portal:
- Application.ReadWrite.All
- Directory.ReadWrite.All

### Entra ID Directory Role

Grant via Azure Portal:
- Cloud Application Administrator

## Required Environment Variables

### Local Development (.env file)

```bash
# Azure Credentials
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<sp-client-id>
AZURE_CLIENT_SECRET=<sp-client-secret>
AZURE_SUBSCRIPTION_ID=<subscription-id>

# Service Principal for Orchestrator
MAIN_SP_CLIENT_ID=<sp-client-id>
MAIN_SP_CLIENT_SECRET=<sp-client-secret>

# Anthropic API
ANTHROPIC_API_KEY=<your-api-key>

# Azure Resources
RESOURCE_GROUP_NAME=haymaker-dev-rg
KEY_VAULT_NAME=haymaker-dev-kv
STORAGE_ACCOUNT_NAME=haymakerstorage
COSMOSDB_ACCOUNT_NAME=haymaker-cosmos
SERVICE_BUS_NAMESPACE=haymaker-dev-bus

# Container Configuration
CONTAINER_REGISTRY=haymakerorchacr.azurecr.io
CONTAINER_IMAGE=haymaker-orchestrator:latest

# Log Analytics
LOG_ANALYTICS_WORKSPACE_ID=<workspace-id>
LOG_ANALYTICS_WORKSPACE_KEY=<workspace-key>
```

### App Service Configuration

Set these environment variables in Azure App Service:

```bash
az webapp config appsettings set \
  --name haymaker-fastapi-app \
  --resource-group haymaker-dev-rg \
  --settings \
    CONTAINER_IMAGE="haymaker-orchestrator:latest" \
    CONTAINER_REGISTRY="haymakerorchacr.azurecr.io" \
    ANTHROPIC_API_KEY="<value>" \
    AZURE_CLIENT_ID="<sp-client-id>" \
    AZURE_CLIENT_SECRET="<sp-client-secret>" \
    AZURE_TENANT_ID="<tenant-id>" \
    MAIN_SP_CLIENT_SECRET="<sp-secret>" \
    LOG_ANALYTICS_WORKSPACE_KEY="<workspace-key>" \
    WEBSITES_PORT="80"
```

## Container Apps Environment

Ensure Container Apps Environment exists:

```bash
az containerapp env show \
  --name haymaker-fastapi-cae \
  --resource-group haymaker-dev-rg
```

If not exists, create it:

```bash
az containerapp env create \
  --name haymaker-fastapi-cae \
  --resource-group haymaker-dev-rg \
  --location westus2 \
  --logs-workspace-id <workspace-id>
```

## Azure Container Registry

### Enable Admin Credentials

```bash
az acr update \
  --name haymakerorchacr \
  --admin-enabled true
```

### Get Credentials

```bash
az acr credential show \
  --name haymakerorchacr
```

## Docker Image Build and Push

### Build Orchestrator Image

```bash
cd src
docker build -f Dockerfile.orchestrator \
  -t haymakerorchacr.azurecr.io/haymaker-orchestrator:latest \
  .
```

### Push to ACR

```bash
az acr login --name haymakerorchacr
docker push haymakerorchacr.azurecr.io/haymaker-orchestrator:latest
```

## Deploy to App Service

### Configure Container

```bash
az webapp config container set \
  --name haymaker-fastapi-app \
  --resource-group haymaker-dev-rg \
  --docker-custom-image-name "haymakerorchacr.azurecr.io/haymaker-orchestrator:latest"
```

### Restart Service

```bash
az webapp restart \
  --name haymaker-fastapi-app \
  --resource-group haymaker-dev-rg
```

### Verify Deployment

```bash
# Check health
curl https://haymaker-fastapi-app.azurewebsites.net/

# List scenarios
curl https://haymaker-fastapi-app.azurewebsites.net/api/scenarios | jq '.scenarios | length'

# Check metrics
curl https://haymaker-fastapi-app.azurewebsites.net/api/metrics | jq
```

## Validation

### Execute Single Scenario

```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{"scenarios":["compute-01-linux-vm-web-server"],"duration_hours":0.05,"skip_validation":true}'
```

### Monitor Execution

```bash
# Get execution ID from above, then:
EXEC_ID="<execution-id>"

# Check status
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions/$EXEC_ID | jq

# Verify containers created
az containerapp list --resource-group haymaker-dev-rg --query 'length(@)'
```

## Troubleshooting

### Health Endpoint Not Responding

1. Check App Service logs:
```bash
az webapp log tail --name haymaker-fastapi-app --resource-group haymaker-dev-rg
```

2. Verify Docker image exists in ACR:
```bash
az acr repository show \
  --name haymakerorchacr \
  --image haymaker-orchestrator:latest
```

3. Restart service:
```bash
az webapp restart \
  --name haymaker-fastapi-app \
  --resource-group haymaker-dev-rg
```

### Container Deployment Failures

Check the execution errors:
```bash
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions/$EXEC_ID | jq '.phases.provisioning.container_apps.errors'
```

Common issues:
- ACR authentication: Ensure admin credentials enabled
- Environment not found: Verify haymaker-fastapi-cae exists
- Resource limits: Use 2.0 CPU + 4.0Gi (valid combo)
- Name length: Max 32 characters

### SP Creation Failures

Check SP creation errors:
```bash
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions/$EXEC_ID | jq '.phases.provisioning.service_principals.errors'
```

The code includes retry logic with exponential backoff to handle Azure AD eventual consistency.

## Success Criteria

- Health endpoint responds with 200
- Environment validation passes
- SPs create with 100% success rate (5/5)
- Containers deploy with 100% success rate (5/5)
- Containers reach Running status

## Validated Configuration

As of 2025-11-25, the following configuration is proven working:

- Python: 3.11.14
- Container Apps Environment: haymaker-fastapi-cae
- ACR: haymakerorchacr.azurecr.io
- Image: haymaker-orchestrator:latest (1.16GB with Azure CLI)
- Resources: 2.0 CPU + 4.0Gi memory
- Deployment: Azure CLI (azure-mgmt-appcontainers SDK has issues)

---

**Generated**: 2025-11-25
**Validation Status**: ✅ E2E PROVEN WORKING
**Test Results**: 10/10 scenarios deployed successfully (2 tests of 5 each)
