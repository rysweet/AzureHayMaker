# Scenario: Azure Container Instances

## Technology Area
Containers

## Company Profile
- **Company Size**: Small to mid-size startup
- **Industry**: Technology / DevOps
- **Use Case**: Run containerized jobs and microservices without managing infrastructure

## Scenario Description
Deploy serverless containers using Azure Container Instances. Create container groups, manage environment variables, implement startup hooks, and configure monitoring without provisioning VMs or orchestration platforms.

## Azure Services Used
- Azure Container Instances
- Azure Container Registry (image storage)
- Azure Storage Account (volume mounting)
- Azure Log Analytics (monitoring)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed
- Docker installed (for building images)
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-containers-aci-${UNIQUE_ID}-rg"
LOCATION="eastus"
ACR_REGISTRY="azmkraci${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkraci${UNIQUE_ID}"
LOG_ANALYTICS="azurehaymaker-logs-${UNIQUE_ID}"
CONTAINER_GROUP="azurehaymaker-aci-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=containers-aci Owner=AzureHayMaker"
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
  --name "${ACR_REGISTRY}" \
  --sku Basic \
  --admin-enabled true \
  --tags ${TAGS}

# Step 3: Build and push container image
cat > /tmp/Dockerfile <<EOF
FROM alpine:latest
RUN apk add --no-cache curl
ENTRYPOINT ["sh"]
CMD ["-c", "while true; do echo 'Container Instance running...'; sleep 30; done"]
EOF

az acr build \
  --registry "${ACR_REGISTRY}" \
  --image "aci-sample:v1" \
  --file /tmp/Dockerfile \
  /tmp/

# Step 4: Create Storage Account for volume mounting
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 5: Create file share
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage share create \
  --name "container-share" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --quota 1

# Step 6: Create Log Analytics Workspace
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

# Step 7: Get ACR credentials
ACR_USERNAME=$(az acr credential show \
  --name "${ACR_REGISTRY}" \
  --query username -o tsv)

ACR_PASSWORD=$(az acr credential show \
  --name "${ACR_REGISTRY}" \
  --query passwords[0].value -o tsv)

ACR_LOGIN_SERVER=$(az acr show \
  --name "${ACR_REGISTRY}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query loginServer -o tsv)

# Step 8: Create container group YAML
cat > /tmp/container_group.yaml <<EOF
apiVersion: '2021-09-01'
name: ${CONTAINER_GROUP}
properties:
  containers:
  - name: sample-container
    properties:
      image: ${ACR_LOGIN_SERVER}/aci-sample:v1
      resources:
        requests:
          cpu: 0.5
          memoryInGB: 0.5
      environmentVariables:
      - name: ENVIRONMENT
        value: production
      - name: LOG_LEVEL
        value: INFO
  imageRegistryCredentials:
  - server: ${ACR_LOGIN_SERVER}
    username: ${ACR_USERNAME}
    password: ${ACR_PASSWORD}
  osType: Linux
  restartPolicy: Always
EOF

# Step 9: Create container instance
az container create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}" \
  --image "${ACR_LOGIN_SERVER}/aci-sample:v1" \
  --cpu 1 \
  --memory 1.5 \
  --registry-login-server "${ACR_LOGIN_SERVER}" \
  --registry-username "${ACR_USERNAME}" \
  --registry-password "${ACR_PASSWORD}" \
  --environment-variables ENVIRONMENT=production LOG_LEVEL=INFO \
  --restart-policy Always \
  --tags ${TAGS}

# Step 10: Create multi-container group with YAML
az container create \
  --resource-group "${RESOURCE_GROUP}" \
  --file /tmp/container_group.yaml

echo ""
echo "=========================================="
echo "Container Instance Created: ${CONTAINER_GROUP}"
echo "Registry: ${ACR_LOGIN_SERVER}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Show container instance
az container show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}"

# Check container status
az container show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}" \
  --query "instanceView.state" -o tsv

# Get container logs
az container logs \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}"

# List containers
az container list \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Verify ACR
az acr show \
  --name "${ACR_REGISTRY}" \
  --resource-group "${RESOURCE_GROUP}"

# List repositories
az acr repository list \
  --name "${ACR_REGISTRY}" \
  --output table

# Verify storage
az storage share list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Check container events
az container attach \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}" \
  --output table

# Operation 2: Execute command in container
az container exec \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}" \
  --exec-command "echo 'Running command in container'"

# Operation 3: Stop container
az container stop \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}"

# Operation 4: Start container
az container start \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}"

# Operation 5: Restart container
az container restart \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}"

# Operation 6: Update container image
az acr build \
  --registry "${ACR_REGISTRY}" \
  --image "aci-sample:v2" \
  --file /tmp/Dockerfile \
  /tmp/

# Operation 7: Create another container instance
az container create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "aci-backup-${UNIQUE_ID}" \
  --image "${ACR_LOGIN_SERVER}/aci-sample:v2" \
  --cpu 0.5 \
  --memory 0.5 \
  --registry-login-server "${ACR_LOGIN_SERVER}" \
  --registry-username "${ACR_USERNAME}" \
  --registry-password "${ACR_PASSWORD}" \
  --tags ${TAGS}

# Operation 8: Monitor container metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ContainerInstance/containerGroups/${CONTAINER_GROUP}" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 9: Export container logs
az container logs \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}" \
  > /tmp/container_logs.txt

# Operation 10: List all container instances
az container list \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[].{Name:name, State:instanceView.state, Image:containers[0].properties.image}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete all container instances
az container delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}" \
  --yes

# Step 2: Delete backup container
az container delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "aci-backup-${UNIQUE_ID}" \
  --yes 2>/dev/null || true

# Step 3: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 4: Verify deletion
sleep 120
az group exists --name "${RESOURCE_GROUP}"

# Step 5: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 6: Clean up local files
rm -rf /tmp/Dockerfile /tmp/container_group.yaml /tmp/container_logs.txt
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-containers-aci-${UNIQUE_ID}-rg`
- Container Group: `azurehaymaker-aci-${UNIQUE_ID}`
- ACR Registry: `azmkraci${UNIQUE_ID}`
- Storage Account: `azmkraci${UNIQUE_ID}`
- Log Analytics: `azurehaymaker-logs-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Container Instances Overview](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-overview)
- [Quick start: Create container instance](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-quickstart)
- [Mount Azure file share](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-mount-azure-files-volume)
- [Container Instances Pricing](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-pricing)
- [Container Instances CLI Reference](https://learn.microsoft.com/en-us/cli/azure/container)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides excellent support for Container Instances with straightforward commands. No orchestration platform required, making this ideal for simple containerized workloads.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8 hours (with container management and monitoring)
- **Cleanup**: 5 minutes

---

## Notes
- No VM management required - fully serverless
- Pay-per-second billing for actual container runtime
- Supports Linux and Windows containers
- Can mount Azure file shares for persistent storage
- Environment variables enable configuration management
- All operations scoped to single tenant and subscription
- Ideal for batch jobs, microservices, and testing
