# Scenario: Multi-Container Application

## Technology Area
Containers

## Company Profile
- **Company Size**: Mid-size development company
- **Industry**: Technology / SaaS
- **Use Case**: Deploy complex multi-tier application with frontend, API, and database

## Scenario Description
Deploy a complete multi-container application using Docker Compose and Azure Container Instances. Includes a web frontend, REST API backend, and Redis cache configured to work together as a unified application.

## Azure Services Used
- Azure Container Instances
- Azure Container Registry (image storage)
- Azure Database for Redis (caching)
- Azure Virtual Network (networking)
- Azure Storage (persistent volumes)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed
- Docker and Docker Compose installed
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-containers-multi-${UNIQUE_ID}-rg"
LOCATION="eastus"
ACR_REGISTRY="azmkrmulti${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
REDIS_CACHE="azurehaymaker-redis-${UNIQUE_ID}"
CONTAINER_GROUP="azurehaymaker-multi-app-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkrmulti${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=containers-multi-container Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Virtual Network
az network vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --address-prefix "10.0.0.0/16" \
  --subnet-name "container-subnet" \
  --subnet-prefixes "10.0.0.0/24" \
  --tags ${TAGS}

# Step 3: Create Azure Container Registry
az acr create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${ACR_REGISTRY}" \
  --sku Standard \
  --admin-enabled true \
  --tags ${TAGS}

# Step 4: Create Storage Account
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 5: Create file share for persistent data
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage share create \
  --name "app-data" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --quota 5

# Step 6: Create Azure Database for Redis
az redis create \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Basic \
  --vm-size c0 \
  --tags ${TAGS}

# Step 7: Get Redis connection string
REDIS_ENDPOINT=$(az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "hostName" -o tsv)

REDIS_KEY=$(az redis list-keys \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "primaryKey" -o tsv)

REDIS_CONNECTION_STRING="${REDIS_ENDPOINT}:6379,password=${REDIS_KEY},ssl=True"

# Step 8: Create frontend Dockerfile
cat > /tmp/frontend_Dockerfile <<EOF
FROM node:alpine
WORKDIR /app
RUN echo "const express = require('express'); const app = express(); app.get('/', (req, res) => { res.send('<html><body><h1>Frontend</h1><p>Multi-container app</p></body></html>'); }); app.listen(3000, () => console.log('Frontend running on port 3000'));" > index.js
RUN npm init -y && npm install express
EXPOSE 3000
CMD ["node", "index.js"]
EOF

# Step 9: Create API backend Dockerfile
cat > /tmp/api_Dockerfile <<EOF
FROM python:3.11-alpine
WORKDIR /app
RUN echo "from flask import Flask; app = Flask(__name__); @app.route('/api/health'); def health(): return {'status': 'healthy'}; if __name__ == '__main__': app.run(host='0.0.0.0', port=5000)" > app.py
RUN pip install flask
EXPOSE 5000
CMD ["python", "app.py"]
EOF

# Step 10: Build and push images to ACR
ACR_LOGIN_SERVER=$(az acr show \
  --name "${ACR_REGISTRY}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query loginServer -o tsv)

az acr build \
  --registry "${ACR_REGISTRY}" \
  --image "frontend:v1" \
  --file /tmp/frontend_Dockerfile \
  /tmp/

az acr build \
  --registry "${ACR_REGISTRY}" \
  --image "api:v1" \
  --file /tmp/api_Dockerfile \
  /tmp/

# Step 11: Get ACR credentials
ACR_USERNAME=$(az acr credential show \
  --name "${ACR_REGISTRY}" \
  --query username -o tsv)

ACR_PASSWORD=$(az acr credential show \
  --name "${ACR_REGISTRY}" \
  --query passwords[0].value -o tsv)

# Step 12: Create multi-container YAML
cat > /tmp/docker_compose.yaml <<EOF
version: '3.9'
services:
  frontend:
    image: ${ACR_LOGIN_SERVER}/frontend:v1
    ports:
      - "3000:3000"
    environment:
      - API_URL=http://api:5000
    depends_on:
      - api
  api:
    image: ${ACR_LOGIN_SERVER}/api:v1
    ports:
      - "5000:5000"
    environment:
      - REDIS_HOST=${REDIS_ENDPOINT}
      - REDIS_PASSWORD=${REDIS_KEY}
    depends_on:
      - cache
  cache:
    image: redis:latest
    ports:
      - "6379:6379"
networks:
  default:
    name: multi-app-network
EOF

# Step 13: Create container instances for each component
az container create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api" \
  --image "${ACR_LOGIN_SERVER}/api:v1" \
  --cpu 1 \
  --memory 1 \
  --registry-login-server "${ACR_LOGIN_SERVER}" \
  --registry-username "${ACR_USERNAME}" \
  --registry-password "${ACR_PASSWORD}" \
  --environment-variables REDIS_HOST="${REDIS_ENDPOINT}" REDIS_PASSWORD="${REDIS_KEY}" \
  --ports 5000 \
  --protocol TCP \
  --tags ${TAGS}

az container create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-frontend" \
  --image "${ACR_LOGIN_SERVER}/frontend:v1" \
  --cpu 1 \
  --memory 1 \
  --registry-login-server "${ACR_LOGIN_SERVER}" \
  --registry-username "${ACR_USERNAME}" \
  --registry-password "${ACR_PASSWORD}" \
  --environment-variables API_URL="http://${CONTAINER_GROUP}-api:5000" \
  --ports 3000 \
  --protocol TCP \
  --tags ${TAGS}

echo ""
echo "=========================================="
echo "Multi-container Application Deployed"
echo "Frontend Container: ${CONTAINER_GROUP}-frontend"
echo "API Container: ${CONTAINER_GROUP}-api"
echo "Redis Cache: ${REDIS_CACHE}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Check frontend container
az container show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-frontend" \
  --query "instanceView.state" -o tsv

# Check API container
az container show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api" \
  --query "instanceView.state" -o tsv

# Get frontend logs
az container logs \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-frontend"

# Get API logs
az container logs \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api"

# Verify Redis
az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}"

# Check Redis status
az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "provisioningState" -o tsv

# List all containers
az container list \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Check frontend container events
az container attach \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-frontend"

# Operation 2: Execute command in API container
az container exec \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api" \
  --exec-command "ps aux"

# Operation 3: Stop containers for maintenance
az container stop \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-frontend"

az container stop \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api"

# Operation 4: Start containers
az container start \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-frontend"

az container start \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api"

# Operation 5: Update API container image
az acr build \
  --registry "${ACR_REGISTRY}" \
  --image "api:v2" \
  --file /tmp/api_Dockerfile \
  /tmp/

# Operation 6: Restart container with new config
az container restart \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api"

# Operation 7: Monitor Redis metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Cache/redis/${REDIS_CACHE}" \
  --metric "CacheHits" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 8: Export container logs for debugging
az container logs \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-frontend" > /tmp/frontend_logs.txt

az container logs \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api" > /tmp/api_logs.txt

# Operation 9: Create backup container instance
az container create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api-backup" \
  --image "${ACR_LOGIN_SERVER}/api:v2" \
  --cpu 0.5 \
  --memory 0.5 \
  --registry-login-server "${ACR_LOGIN_SERVER}" \
  --registry-username "${ACR_USERNAME}" \
  --registry-password "${ACR_PASSWORD}" \
  --tags ${TAGS}

# Operation 10: Monitor application health
for i in {1..5}; do
  echo "Health check $i:"
  az container show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CONTAINER_GROUP}-frontend" \
    --query "instanceView.state" -o tsv
  sleep 5
done
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete all container instances
az container delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-frontend" \
  --yes

az container delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api" \
  --yes

az container delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_GROUP}-api-backup" \
  --yes 2>/dev/null || true

# Step 2: Delete Redis cache
az redis delete \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --yes

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
rm -rf /tmp/frontend_Dockerfile /tmp/api_Dockerfile /tmp/docker_compose.yaml /tmp/frontend_logs.txt /tmp/api_logs.txt
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-containers-multi-${UNIQUE_ID}-rg`
- Frontend Container: `${CONTAINER_GROUP}-frontend`
- API Container: `${CONTAINER_GROUP}-api`
- ACR Registry: `azmkrmulti${UNIQUE_ID}`
- Redis Cache: `azurehaymaker-redis-${UNIQUE_ID}`
- Storage Account: `azmkrmulti${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Multi-Container Groups in ACI](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-multi-container-yaml)
- [Docker Compose to ACI](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-docker-compose)
- [Azure Cache for Redis](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-overview)
- [Container Instances Networking](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-container-groups)
- [Container Instances CLI Reference](https://learn.microsoft.com/en-us/cli/azure/container)

---

## Automation Tool
**Recommended**: Azure CLI + Docker

**Rationale**: Azure CLI orchestrates container deployment while Docker handles image building. This combination enables complete multi-container application lifecycle management.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8 hours (with management and monitoring)
- **Cleanup**: 10-15 minutes

---

## Notes
- Multi-container groups in ACI support shared networking
- Environment variables enable service communication
- Persistent storage via Azure Files for data durability
- Redis caching improves application performance
- All operations scoped to single tenant and subscription
- Ideal for monolithic application decomposition
- Container groups share storage and networking context
