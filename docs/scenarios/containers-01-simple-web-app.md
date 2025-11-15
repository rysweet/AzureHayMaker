# Scenario: Simple Web Application on Azure Container Apps

## Technology Area
Containers

## Company Profile
- **Company Size**: Small software company
- **Industry**: Technology / SaaS
- **Use Case**: Deploy a containerized web application with automatic scaling and HTTPS

## Scenario Description
Deploy a simple containerized web application (nginx) to Azure Container Apps with automatic HTTPS certificates, environment-based configuration, and the ability to scale based on HTTP traffic.

## Azure Services Used
- Azure Container Apps
- Azure Container Registry
- Azure Log Analytics Workspace

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed with containerapp extension (`az extension add --name containerapp`)
- Docker installed (for building container image)
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-containers-${UNIQUE_ID}-rg"
LOCATION="eastus"
CONTAINER_REGISTRY="azmkracr${UNIQUE_ID}"
CONTAINER_APP_ENV="azurehaymaker-env-${UNIQUE_ID}"
CONTAINER_APP="azurehaymaker-webapp-${UNIQUE_ID}"
LOG_ANALYTICS="azurehaymaker-logs-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=containers-simple-webapp Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Azure Container Registry
az acr create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_REGISTRY}" \
  --sku Basic \
  --admin-enabled true \
  --tags ${TAGS}

# Step 3: Build and push a simple container image
cat > /tmp/Dockerfile <<EOF
FROM nginx:alpine
RUN echo '<html><body><h1>Azure HayMaker Test App</h1><p>Scenario: containers-simple-webapp</p></body></html>' > /usr/share/nginx/html/index.html
EOF

az acr build \
  --registry "${CONTAINER_REGISTRY}" \
  --image "haymaker-webapp:v1" \
  --file /tmp/Dockerfile \
  /tmp/

# Step 4: Create Log Analytics Workspace for monitoring
az monitor log-analytics workspace create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS}" \
  --query customerId -o tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS}" \
  --query primarySharedKey -o tsv)

# Step 5: Create Container Apps Environment
az containerapp env create \
  --name "${CONTAINER_APP_ENV}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --logs-workspace-id "${LOG_ANALYTICS_ID}" \
  --logs-workspace-key "${LOG_ANALYTICS_KEY}" \
  --tags ${TAGS}

# Step 6: Get ACR credentials
ACR_SERVER="${CONTAINER_REGISTRY}.azurecr.io"
ACR_USERNAME=$(az acr credential show --name "${CONTAINER_REGISTRY}" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "${CONTAINER_REGISTRY}" --query passwords[0].value -o tsv)

# Step 7: Deploy Container App
az containerapp create \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --environment "${CONTAINER_APP_ENV}" \
  --image "${ACR_SERVER}/haymaker-webapp:v1" \
  --registry-server "${ACR_SERVER}" \
  --registry-username "${ACR_USERNAME}" \
  --registry-password "${ACR_PASSWORD}" \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 0.25 \
  --memory 0.5Gi \
  --tags ${TAGS}

# Step 8: Get the app URL
APP_URL=$(az containerapp show \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Application URL: https://${APP_URL}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Container Registry
az acr show --name "${CONTAINER_REGISTRY}"

# Verify Container App Environment
az containerapp env show --name "${CONTAINER_APP_ENV}" --resource-group "${RESOURCE_GROUP}"

# Verify Container App is running
az containerapp show --name "${CONTAINER_APP}" --resource-group "${RESOURCE_GROUP}" --query "properties.runningStatus"

# Test the application endpoint
curl -k "https://${APP_URL}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Update container image
cat > /tmp/Dockerfile.v2 <<EOF
FROM nginx:alpine
RUN echo '<html><body><h1>Azure HayMaker Test App - Updated!</h1><p>Version 2</p><p>Updated at $(date)</p></body></html>' > /usr/share/nginx/html/index.html
EOF

az acr build \
  --registry "${CONTAINER_REGISTRY}" \
  --image "haymaker-webapp:v2" \
  --file /tmp/Dockerfile.v2 \
  /tmp/

# Operation 2: Update Container App to use new image
az containerapp update \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --image "${ACR_SERVER}/haymaker-webapp:v2"

# Operation 3: Scale up replicas manually
az containerapp update \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --min-replicas 2 \
  --max-replicas 10

# Operation 4: View application logs
az containerapp logs show \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --tail 50

# Operation 5: Check replica count
az containerapp replica list \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Operation 6: Monitor HTTP requests
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/containerApps/${CONTAINER_APP}" \
  --metric "Requests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 7: Restart the application
az containerapp revision restart \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}"

# Operation 8: List all revisions
az containerapp revision list \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 2: Verify deletion
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 3: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-containers-${UNIQUE_ID}-rg`
- Container Registry: `azmkracr${UNIQUE_ID}`
- Container App Environment: `azurehaymaker-env-${UNIQUE_ID}`
- Container App: `azurehaymaker-webapp-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Container Apps Overview](https://learn.microsoft.com/en-us/azure/container-apps/overview)
- [Deploy to Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/deploy-visual-studio-code)
- [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Container Apps CLI Reference](https://learn.microsoft.com/en-us/cli/azure/containerapp)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure Container Apps has excellent Azure CLI support with straightforward commands. While Bicep/Terraform are options, Azure CLI is fastest for this scenario's simplicity level.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8 hours (with periodic updates and monitoring)
- **Cleanup**: 5 minutes

---

## Notes
- Container Apps automatically provides HTTPS certificates
- Automatic scaling based on HTTP requests (0-10 replicas in this example)
- Log Analytics integration for monitoring and diagnostics
- Container Registry admin account used for simplicity (use managed identity in production)
- All operations scoped to single tenant and subscription
