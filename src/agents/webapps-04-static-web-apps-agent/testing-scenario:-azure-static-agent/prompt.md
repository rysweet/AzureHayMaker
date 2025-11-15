# Scenario: Azure Static Web Apps

## Technology Area
Web Apps

## Company Profile
- **Company Size**: Small startup
- **Industry**: Technology / Digital Agency
- **Use Case**: Host JAMstack applications with serverless backend API

## Scenario Description
Deploy modern web applications using Azure Static Web Apps with integrated serverless functions, automatic Git deployment, and global CDN distribution.

## Azure Services Used
- Azure Static Web Apps
- Azure Functions (serverless API)
- Azure API Management (optional)
- Git repository integration

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed
- Git installed
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-webapp-static-${UNIQUE_ID}-rg"
LOCATION="eastus"
STATIC_WEB_APP="azurehaymaker-swa-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=webapps-static-web-apps Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create sample web application structure
mkdir -p /tmp/static-app
cd /tmp/static-app

mkdir -p app
mkdir -p api

# Step 3: Create HTML frontend
cat > /tmp/static-app/app/index.html <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure HayMaker - Static Web App</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>Azure HayMaker Static Web App</h1>
        <p>Scenario: webapps-static-web-apps</p>
    </header>
    <main>
        <section>
            <h2>Welcome to Static Web Apps</h2>
            <p>This is a JAMstack application hosted on Azure Static Web Apps.</p>
            <button onclick="callApi()">Call API Function</button>
            <div id="result"></div>
        </section>
    </main>
    <script src="app.js"></script>
</body>
</html>
EOF

cat > /tmp/static-app/app/styles.css <<EOF
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}
header {
    background-color: rgba(0, 0, 0, 0.3);
    color: white;
    padding: 2rem;
    text-align: center;
}
main {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
}
section {
    background: white;
    padding: 3rem;
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    max-width: 600px;
    text-align: center;
}
button {
    background-color: #667eea;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 16px;
    margin-top: 20px;
}
button:hover { background-color: #764ba2; }
#result {
    margin-top: 20px;
    padding: 10px;
    background-color: #f0f0f0;
    border-radius: 5px;
    min-height: 20px;
}
EOF

cat > /tmp/static-app/app/app.js <<EOF
function callApi() {
    fetch('/api/message')
        .then(response => response.json())
        .then(data => {
            document.getElementById('result').textContent =
                'API Response: ' + JSON.stringify(data, null, 2);
        })
        .catch(error => {
            document.getElementById('result').textContent =
                'Error: ' + error.message;
        });
}

// Call API on page load
window.addEventListener('load', () => {
    fetch('/api/info')
        .then(response => response.json())
        .then(data => console.log('App Info:', data));
});
EOF

# Step 4: Create Azure Functions API
cat > /tmp/static-app/api/message/function.json <<EOF
{
  "scriptFile": "index.js",
  "bindings": [
    {
      "authLevel": "anonymous",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["get", "post"]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "\$return"
    }
  ]
}
EOF

cat > /tmp/static-app/api/message/index.js <<EOF
module.exports = async function (context, req) {
    context.res = {
        body: {
            message: "Hello from Azure Static Web Apps",
            timestamp: new Date().toISOString(),
            scenario: "webapps-static-web-apps"
        }
    };
};
EOF

cat > /tmp/static-app/api/info/function.json <<EOF
{
  "scriptFile": "index.js",
  "bindings": [
    {
      "authLevel": "anonymous",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["get"]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "\$return"
    }
  ]
}
EOF

cat > /tmp/static-app/api/info/index.js <<EOF
module.exports = async function (context, req) {
    context.res = {
        body: {
            app: "Azure Static Web App",
            version: "1.0.0",
            platform: "Azure Static Web Apps",
            uptime: process.uptime()
        }
    };
};
EOF

# Step 5: Create package.json for functions
cat > /tmp/static-app/api/package.json <<EOF
{
  "name": "static-web-app-api",
  "version": "1.0.0",
  "description": "Serverless API for Static Web App",
  "main": "index.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  }
}
EOF

# Step 6: Create staticwebapp.config.json
cat > /tmp/static-app/staticwebapp.config.json <<EOF
{
  "routes": [
    {
      "route": "/api/*",
      "allowedRoles": ["anonymous"]
    },
    {
      "route": "/*",
      "serve": "/index.html",
      "statusCode": 200
    }
  ],
  "navigationFallback": {
    "rewrite": "index.html",
    "exclude": ["/images/*", "/css/*"]
  },
  "responseOverrides": {
    "404": {
      "rewrite": "index.html",
      "statusCode": 200
    }
  }
}
EOF

# Step 7: Create Static Web App using managed mode
az staticwebapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
  --source "/tmp/static-app" \
  --location "${LOCATION}" \
  --build-folder "app" \
  --api-location "api" \
  --output-location "" \
  --tags ${TAGS}

# Wait for deployment
sleep 30

# Step 8: Get Static Web App details
STATIC_WEB_APP_URL=$(az staticwebapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
  --query "defaultDomain" -o tsv)

echo ""
echo "=========================================="
echo "Static Web App Created: ${STATIC_WEB_APP}"
echo "URL: https://${STATIC_WEB_APP_URL}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Static Web App
az staticwebapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}"

# Get deployment status
az staticwebapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
  --query "buildProperties" -o table

# Get app URL
STATIC_WEB_APP_URL=$(az staticwebapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
  --query "defaultDomain" -o tsv)

echo "App URL: https://${STATIC_WEB_APP_URL}"

# Test application
curl -s "https://${STATIC_WEB_APP_URL}/" | grep "Azure HayMaker"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create deployment slot
az staticwebapp environment create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
  --environment-name "staging"

# Operation 2: Add custom domain (requires DNS verification)
echo "To add custom domain:"
echo "az staticwebapp hostname set --resource-group ${RESOURCE_GROUP} --name ${STATIC_WEB_APP} --hostname www.example.com"

# Operation 3: Configure authentication
az staticwebapp auth create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
  --auth-provider "github" \
  --redirect-url "/.auth/login/github/callback" \
  --logout-url "/logout"

# Operation 4: Enable custom domain HTTPS
echo "HTTPS is automatically enabled for Static Web Apps"

# Operation 5: Monitor traffic and performance
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/staticSites/${STATIC_WEB_APP}" \
  --metric "Requests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 6: View build logs
az staticwebapp builds list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
  --output table

# Operation 7: Check API functions
echo "API Functions available at:"
echo "GET /api/message"
echo "GET /api/info"

# Operation 8: Rollback to previous deployment
# Gets list of previous deployments
az staticwebapp builds list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
  --query "[].id" -o tsv | head -1

# Operation 9: Configure routing rules
echo "Routing configured in staticwebapp.config.json"

# Operation 10: Review app configuration
az staticwebapp config show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete Static Web App
az staticwebapp delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STATIC_WEB_APP}" \
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
rm -rf /tmp/static-app
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-webapp-static-${UNIQUE_ID}-rg`
- Static Web App: `azurehaymaker-swa-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Static Web Apps Overview](https://learn.microsoft.com/en-us/azure/static-web-apps/overview)
- [Static Web Apps Configuration](https://learn.microsoft.com/en-us/azure/static-web-apps/configuration)
- [Serverless Functions](https://learn.microsoft.com/en-us/azure/static-web-apps/add-api)
- [Authentication and Authorization](https://learn.microsoft.com/en-us/azure/static-web-apps/authentication-authorization)
- [Static Web Apps CLI Reference](https://learn.microsoft.com/en-us/cli/azure/staticwebapp)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI handles Static Web App provisioning and lifecycle management. Git integration typically handled via GitHub Actions or Azure DevOps.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8 hours (with updates and monitoring)
- **Cleanup**: 5 minutes

---

## Notes
- Automatic HTTPS with free certificates
- Global CDN for static content distribution
- Integrated serverless functions with no cold starts
- JAMstack architecture support
- All operations scoped to single tenant and subscription
- Automatic builds and deployments from Git
- Preview deployments for pull requests
