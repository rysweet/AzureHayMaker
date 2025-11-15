# Scenario: Node.js Application on Azure App Service

## Technology Area
Web Apps

## Company Profile
- **Company Size**: Mid-size technology startup
- **Industry**: SaaS / Web Services
- **Use Case**: Host Node.js REST API backend with automatic scaling

## Scenario Description
Deploy a Node.js application to Azure App Service with continuous deployment from Git, environment configuration management, and automatic scaling based on HTTP metrics.

## Azure Services Used
- Azure App Service (hosting)
- Azure App Service Plan (compute resources)
- Azure SQL Database (data storage)
- Azure Application Insights (monitoring)
- Azure Key Vault (secrets)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed
- Node.js installed (for local testing)
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-webapp-nodejs-${UNIQUE_ID}-rg"
LOCATION="eastus"
APP_SERVICE_PLAN="azurehaymaker-plan-${UNIQUE_ID}"
APP_SERVICE="azurehaymaker-nodejs-${UNIQUE_ID}"
INSIGHTS_NAME="azurehaymaker-insights-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=webapps-nodejs Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 3: Create Application Insights
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

# Store in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "app-insights-key" \
  --value "${INSIGHTS_KEY}"

# Step 4: Create App Service Plan
az appservice plan create \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku B2 \
  --is-linux \
  --tags ${TAGS}

# Step 5: Create sample Node.js application
mkdir -p /tmp/nodejs-app
cat > /tmp/nodejs-app/package.json <<EOF
{
  "name": "azure-nodejs-app",
  "version": "1.0.0",
  "description": "Sample Node.js App for Azure App Service",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
EOF

cat > /tmp/nodejs-app/index.js <<EOF
const express = require('express');
const app = express();
const port = process.env.PORT || 8080;

app.get('/', (req, res) => {
  res.json({
    message: 'Azure HayMaker Node.js App',
    scenario: 'webapps-nodejs-app-service',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development'
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.get('/api/info', (req, res) => {
  res.json({
    app: 'Azure HayMaker',
    version: '1.0.0',
    uptime: process.uptime()
  });
});

app.listen(port, () => {
  console.log(\`App listening on port \${port}\`);
});
EOF

# Step 6: Create Azure App Service
az webapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_SERVICE_PLAN}" \
  --name "${APP_SERVICE}" \
  --runtime "NODE|18.0" \
  --tags ${TAGS}

# Step 7: Configure app settings
az webapp config appsettings set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --settings \
    NODE_ENV=production \
    WEBSITE_NODE_DEFAULT_VERSION=18.0 \
    APPINSIGHTS_INSTRUMENTATIONKEY="${INSIGHTS_KEY}"

# Step 8: Configure connection strings (if needed)
az webapp config connection-string set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --settings \
    DefaultConnection="Server=tcp:example.database.windows.net,1433" \
  --connection-string-type SQLAzure

# Step 9: Deploy application code
cd /tmp/nodejs-app
npm install
zip -r /tmp/app.zip .

az webapp deployment source config-zip \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --src /tmp/app.zip

# Step 10: Enable automatic scaling
az monitor autoscale create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "nodejs-autoscale" \
  --resource-namespace "Microsoft.Web" \
  --resource-type "serverFarms" \
  --resource "${APP_SERVICE_PLAN}" \
  --min-count 1 \
  --max-count 5 \
  --count 2

# Add scale rule
az monitor autoscale rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --autoscale-name "nodejs-autoscale" \
  --condition "Percentage CPU > 75 avg 5m 2 times count 3" \
  --scale out 1

az monitor autoscale rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --autoscale-name "nodejs-autoscale" \
  --condition "Percentage CPU < 25 avg 5m 1 times count 1" \
  --scale in 1

echo ""
echo "=========================================="
echo "Node.js App Service Created: ${APP_SERVICE}"
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

# Get App Service status
az webapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --query "state" -o tsv

# Get App Service URL
APP_URL=$(az webapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --query "defaultHostName" -o tsv)

echo "App URL: https://${APP_URL}"

# Test application endpoint
curl -s "https://${APP_URL}/"

# Check Application Insights
az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}"

# List app settings
az webapp config appsettings list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: View application logs
az webapp log tail \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --provider "anyazure" \
  --tail 20

# Operation 2: Restart web app
az webapp restart \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}"

# Operation 3: Deploy updated code
cat > /tmp/nodejs-app/index.js <<EOF
const express = require('express');
const app = express();
const port = process.env.PORT || 8080;

app.get('/', (req, res) => {
  res.json({
    message: 'Azure HayMaker Node.js App - UPDATED',
    scenario: 'webapps-nodejs-app-service',
    timestamp: new Date().toISOString(),
    version: '2.0.0'
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.listen(port, () => {
  console.log(\`App listening on port \${port}\`);
});
EOF

cd /tmp/nodejs-app
npm install
zip -r /tmp/app-updated.zip .

az webapp deployment source config-zip \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}" \
  --src /tmp/app-updated.zip

# Operation 4: Scale up manually
az appservice plan update \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku B3

# Operation 5: Monitor application performance
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${APP_SERVICE}" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 6: Configure SSL/TLS
echo "To add SSL certificate:"
echo "az webapp config ssl bind --certificate-thumbprint <thumbprint> --resource-group ${RESOURCE_GROUP} --name ${APP_SERVICE}"

# Operation 7: Add custom domain
echo "To add custom domain:"
echo "az webapp config hostname add --webapp-name ${APP_SERVICE} --resource-group ${RESOURCE_GROUP} --hostname www.example.com"

# Operation 8: Enable managed identity
az webapp identity assign \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE}"

# Operation 9: Check autoscale metrics
az monitor autoscale show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "nodejs-autoscale"

# Operation 10: Test health endpoint
curl -s "https://${APP_URL}/health" | jq .
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete autoscale settings
az monitor autoscale delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "nodejs-autoscale" \
  --yes

# Step 2: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 3: Verify deletion
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 4: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 5: Clean up local files
rm -rf /tmp/nodejs-app /tmp/app.zip /tmp/app-updated.zip
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-webapp-nodejs-${UNIQUE_ID}-rg`
- App Service: `azurehaymaker-nodejs-${UNIQUE_ID}`
- App Service Plan: `azurehaymaker-plan-${UNIQUE_ID}`
- Application Insights: `azurehaymaker-insights-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [App Service Overview](https://learn.microsoft.com/en-us/azure/app-service/overview)
- [Node.js on App Service](https://learn.microsoft.com/en-us/azure/app-service/quickstart-nodejs)
- [Autoscaling in App Service](https://learn.microsoft.com/en-us/azure/app-service/manage-scale-up)
- [Application Insights](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
- [App Service CLI Reference](https://learn.microsoft.com/en-us/cli/azure/webapp)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI handles App Service provisioning and management efficiently. Application code deployment uses zip deployment for simplicity.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8 hours (with updates and monitoring)
- **Cleanup**: 5-10 minutes

---

## Notes
- App Service provides automatic HTTPS
- Built-in Application Insights monitoring
- Auto-scaling based on CPU and HTTP metrics
- Multiple deployment options (zip, git, Docker)
- All operations scoped to single tenant and subscription
- Managed identity enables secure Azure resource access
- Suitable for production Node.js applications
