# Scenario: Docker Container on Azure App Service

## Technology Area
Web Apps

## Company Profile
- **Company Size**: Small to mid-size development company
- **Industry**: Technology / DevOps
- **Use Case**: Deploy containerized web applications with orchestration simplicity

## Scenario Description
Deploy Docker containers directly to Azure App Service without Kubernetes complexity. Build custom container images, push to registry, and automatically update deployments with new images.

## Azure Services Used
- Azure App Service (hosting)
- Azure App Service Plan (compute)
- Azure Container Registry (image storage)
- Azure Application Insights (monitoring)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed with Docker
- Docker installed and running
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-webapp-docker-${UNIQUE_ID}-rg"
LOCATION="eastus"
APP_SERVICE_PLAN="azurehaymaker-plan-${UNIQUE_ID}"
APP_SERVICE="azurehaymaker-docker-${UNIQUE_ID}"
ACR_REGISTRY="azmkrdocker${UNIQUE_ID}"
INSIGHTS_NAME="azurehaymaker-insights-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=webapps-docker Owner=AzureHayMaker"
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
  --sku Standard \
  --admin-enabled true \
  --tags ${TAGS}

# Step 3: Create Dockerfile for custom app
cat > /tmp/Dockerfile <<EOF
FROM python:3.11-slim
WORKDIR /app
RUN pip install flask

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

EXPOSE 8080
ENV FLASK_APP=app.py
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
EOF

cat > /tmp/requirements.txt <<EOF
flask==2.3.0
gunicorn==20.1.0
EOF

cat > /tmp/app.py <<EOF
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({
        'message': 'Azure HayMaker Docker App',
        'scenario': 'webapps-docker-app-service',
        'environment': os.environ.get('ENVIRONMENT', 'production')
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/info')
def info():
    return jsonify({
        'app': 'Docker Container App',
        'version': '1.0.0',
        'platform': 'Azure App Service'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
EOF

# Step 4: Build Docker image
docker build -t "${ACR_REGISTRY}.azurecr.io/webapp:v1" -f /tmp/Dockerfile /tmp/

# Step 5: Get ACR credentials
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

# Step 6: Push image to ACR
docker login "${ACR_LOGIN_SERVER}" -u "${ACR_USERNAME}" -p "${ACR_PASSWORD}"
docker push "${ACR_LOGIN_SERVER}/webapp:v1"

# Step 7: Create Application Insights
az monitor app-insights component create \
  --app "${INSIGHTS_NAME}" \
  --location "${LOCATION}" \
  --resource-group "${RESOURCE_GROUP}" \
  --application-type web \
  --tags ${TAGS}

INSIGHTS_KEY=$(az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "instrumentationKey" -o tsv)

# Step 8: Create App Service Plan for Linux
az appservice plan create \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku B2 \
  --is-linux \
  --tags ${TAGS}

# Step 9: Create App Service with Docker container
az webapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_SERVICE_PLAN}" \
  --name "${APP_SERVICE}" \
  --deployment-container-image-name "${ACR_LOGIN_SERVER}/webapp:v1" \
  --docker-registry-server-url "https://${ACR_LOGIN_SERVER}" \
  --docker-registry-server-user "${ACR_USERNAME}" \
  --docker-registry-server-password "${ACR_PASSWORD}" \
  --tags ${TAGS}

# Step 10: Configure app settings
az webapp config appsettings set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --settings \
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=false \
    DOCKER_ENABLE_CI=true \
    ENVIRONMENT=production \
    APPINSIGHTS_INSTRUMENTATIONKEY="${INSIGHTS_KEY}"

echo ""
echo "=========================================="
echo "Docker App Service Created: ${APP_SERVICE}"
echo "Registry: ${ACR_LOGIN_SERVER}"
echo "URL: https://${APP_SERVICE}.azurewebsites.net"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify App Service
az webapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}"

# Check deployment status
az webapp deployment list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --output table

# Get App Service URL
APP_URL=$(az webapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --query "defaultHostName" -o tsv)

echo "App URL: https://${APP_URL}"

# Test application
curl -s "https://${APP_URL}/" | jq .

# View container logs
az webapp log tail \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --provider "docker" \
  --tail 20

# Verify ACR repositories
az acr repository list \
  --name "${ACR_REGISTRY}" \
  --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Build and push updated image
cat > /tmp/app.py <<EOF
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({
        'message': 'Azure HayMaker Docker App - UPDATED',
        'version': '2.0.0',
        'scenario': 'webapps-docker-app-service'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'version': '2.0.0'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
EOF

docker build -t "${ACR_LOGIN_SERVER}/webapp:v2" -f /tmp/Dockerfile /tmp/
docker login "${ACR_LOGIN_SERVER}" -u "${ACR_USERNAME}" -p "${ACR_PASSWORD}"
docker push "${ACR_LOGIN_SERVER}/webapp:v2"

# Operation 2: Update app to use new image
az webapp config container set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --docker-custom-image-name "${ACR_LOGIN_SERVER}/webapp:v2" \
  --docker-registry-server-url "https://${ACR_LOGIN_SERVER}" \
  --docker-registry-server-user "${ACR_USERNAME}" \
  --docker-registry-server-password "${ACR_PASSWORD}"

# Operation 3: Restart app service
az webapp restart \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}"

# Operation 4: Monitor container metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${APP_SERVICE}" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 5: View container logs
az webapp log tail \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --provider "docker" \
  --tail 50

# Operation 6: Scale up app service
az appservice plan update \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku B3

# Operation 7: List ACR images
az acr repository show \
  --name "${ACR_REGISTRY}" \
  --repository "webapp"

# Operation 8: Enable continuous deployment
# Note: Requires webhook setup
echo "To enable continuous deployment:"
echo "az webapp deployment container config --resource-group ${RESOURCE_GROUP} --name ${APP_SERVICE}"

# Operation 9: Test different endpoints
curl -s "https://${APP_URL}/health" | jq .
curl -s "https://${APP_URL}/api/info" | jq .

# Operation 10: Check Application Insights
az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "instrumentationKey" -o tsv
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete app service
az webapp delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}"

# Step 2: Delete app service plan
az appservice plan delete \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --yes

# Step 3: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 4: Verify deletion
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 5: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 6: Clean up Docker images and local files
docker rmi "${ACR_LOGIN_SERVER}/webapp:v1" 2>/dev/null
docker rmi "${ACR_LOGIN_SERVER}/webapp:v2" 2>/dev/null
rm -rf /tmp/Dockerfile /tmp/app.py /tmp/requirements.txt
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-webapp-docker-${UNIQUE_ID}-rg`
- App Service: `azurehaymaker-docker-${UNIQUE_ID}`
- App Service Plan: `azurehaymaker-plan-${UNIQUE_ID}`
- ACR Registry: `azmkrdocker${UNIQUE_ID}`
- Application Insights: `azurehaymaker-insights-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [App Service with Containers](https://learn.microsoft.com/en-us/azure/app-service/configure-custom-container)
- [Docker on App Service](https://learn.microsoft.com/en-us/azure/app-service/quickstart-docker)
- [Container Registry Integration](https://learn.microsoft.com/en-us/azure/app-service/configure-custom-container?tabs=debian&pivots=container-linux)
- [Continuous Deployment](https://learn.microsoft.com/en-us/azure/app-service/deploy-continuous-deployment)
- [App Service CLI Reference](https://learn.microsoft.com/en-us/cli/azure/webapp)

---

## Automation Tool
**Recommended**: Azure CLI + Docker

**Rationale**: Azure CLI manages App Service lifecycle while Docker handles image building and pushing. This combination provides efficient containerized deployment.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8 hours (with image updates and monitoring)
- **Cleanup**: 5 minutes

---

## Notes
- App Service runs containers on Linux using Docker
- Azure Container Registry integration for secure image storage
- Automatic deployments when new images are pushed
- No Kubernetes complexity required
- All operations scoped to single tenant and subscription
- Suitable for monolithic containerized applications
- Environment variables for configuration management
