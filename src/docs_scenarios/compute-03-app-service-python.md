# Scenario: Python Web Application on Azure App Service

## Technology Area
Compute

## Company Profile
- **Company Size**: Small startup
- **Industry**: Data Analytics / SaaS
- **Use Case**: Deploy a Python Flask web application with continuous deployment and auto-scaling

## Scenario Description
Deploy a Python Flask-based web application to Azure App Service with automatic scaling, continuous integration from Git, environment configuration, and monitoring. This scenario covers serverless compute management without VM overhead.

## Azure Services Used
- Azure App Service (Web Apps)
- Azure App Service Plan
- Azure Container Registry (optional)
- Azure Application Insights
- Azure Log Analytics Workspace

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Git installed locally
- Python 3.9+ installed (for local development/testing)
- A GitHub account or Git repository access (for deployment)

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-compute-${UNIQUE_ID}-rg"
LOCATION="eastus"
APP_SERVICE_PLAN="azurehaymaker-asp-${UNIQUE_ID}"
WEB_APP_NAME="azurehaymaker-py-app-${UNIQUE_ID}"
APP_INSIGHTS_NAME="azurehaymaker-appinsights-${UNIQUE_ID}"
LOG_ANALYTICS_NAME="azurehaymaker-logs-${UNIQUE_ID}"
STORAGE_ACCOUNT="azurehaymaker${UNIQUE_ID}"
ARTIFACT_DIR="/tmp/azurehaymaker-flask-app"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=compute-app-service-python Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Log Analytics Workspace for monitoring
az monitor log-analytics workspace create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS_NAME}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS_NAME}" \
  --query customerId -o tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS_NAME}" \
  --query primarySharedKey -o tsv)

# Step 3: Create Application Insights for monitoring
az monitor app-insights component create \
  --app "${APP_INSIGHTS_NAME}" \
  --location "${LOCATION}" \
  --resource-group "${RESOURCE_GROUP}" \
  --application-type web \
  --workspace "${LOG_ANALYTICS_NAME}" \
  --tags ${TAGS}

INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app "${APP_INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query instrumentationKey -o tsv)

# Step 4: Create App Service Plan (B1 Basic tier for small apps)
az appservice plan create \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku B1 \
  --is-linux \
  --tags ${TAGS}

# Step 5: Create the Web App with Python runtime
az webapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_SERVICE_PLAN}" \
  --name "${WEB_APP_NAME}" \
  --runtime "PYTHON|3.9" \
  --tags ${TAGS}

# Step 6: Configure application settings
az webapp config appsettings set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --settings "APPINSIGHTS_INSTRUMENTATIONKEY=${INSTRUMENTATION_KEY}" \
  "ApplicationInsightsAgent_EXTENSION_VERSION=~3" \
  "XDT_MicrosoftApplicationInsights_Mode=default"

# Step 7: Create the Flask application files locally
mkdir -p "${ARTIFACT_DIR}"

# Create requirements.txt
cat > "${ARTIFACT_DIR}/requirements.txt" <<'EOF'
Flask==3.0.0
gunicorn==21.2.0
applicationinsights==0.11.10
python-dotenv==1.0.0
EOF

# Create main Flask application
cat > "${ARTIFACT_DIR}/app.py" <<'EOF'
import os
from datetime import datetime
from flask import Flask, jsonify
from applicationinsights import TelemetryClient

app = Flask(__name__)

# Application Insights telemetry client
tc = TelemetryClient(os.environ.get('APPINSIGHTS_INSTRUMENTATIONKEY', ''))

@app.route('/')
def home():
    """Root endpoint returning welcome page"""
    tc.track_pageview('home')
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Azure HayMaker - Python App Service</title>
        <style>
            body {{ font-family: Segoe UI, sans-serif; margin: 50px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 5px; }}
            h1 {{ color: #0078d4; }}
            .info {{ background: #f0f0f0; padding: 15px; border-left: 4px solid #0078d4; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Azure HayMaker - Python Web App</h1>
            <div class="info">
                <p><strong>Scenario:</strong> compute-03-app-service-python</p>
                <p><strong>Framework:</strong> Flask 3.0</p>
                <p><strong>Runtime:</strong> Python 3.9</p>
                <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Hostname:</strong> {os.environ.get('COMPUTERNAME', 'Azure App Service')}</p>
            </div>
            <hr>
            <p>
                <a href="/api/health">Health Check</a> |
                <a href="/api/info">System Info</a> |
                <a href="/api/status">Status</a>
            </p>
        </div>
    </body>
    </html>
    ''', 200, {'Content-Type': 'text/html'}

@app.route('/api/health')
def health():
    """Health check endpoint"""
    tc.track_event('health_check')
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Azure App Service - Python'
    }), 200

@app.route('/api/info')
def info():
    """System information endpoint"""
    tc.track_event('info_request')
    return jsonify({
        'app': 'Azure HayMaker Python Web App',
        'scenario': 'compute-03-app-service-python',
        'framework': 'Flask',
        'python_version': os.sys.version,
        'environment': os.environ.get('AZURE_APP_SERVICE', 'Unknown'),
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/status')
def status():
    """Application status endpoint"""
    tc.track_event('status_request')
    return jsonify({
        'running': True,
        'app_service': 'Azure App Service',
        'deployment_slot': os.environ.get('WEBSITE_SLOT_NAME', 'production'),
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/echo/<message>')
def echo(message):
    """Echo endpoint for testing"""
    tc.track_event('echo', {'message': message})
    return jsonify({
        'echo': message,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found', 'message': str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    tc.track_exception()
    return jsonify({'error': 'Internal Server Error', 'message': str(error)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8000)
EOF

# Create runtime configuration
cat > "${ARTIFACT_DIR}/.runtime" <<'EOF'
python-3.9
EOF

# Create Procfile for gunicorn
cat > "${ARTIFACT_DIR}/Procfile" <<'EOF'
web: gunicorn --bind 0.0.0.0 --workers 4 --timeout 60 app:app
EOF

# Step 8: Initialize git repository
cd "${ARTIFACT_DIR}"
git init
git add .
git commit -m "Initial Flask application commit for Azure App Service"

# Step 9: Configure local Git deployment
az webapp deployment user set --user-name "azureuser" --password "HayMaker$(openssl rand -hex 6)"

# Step 10: Get the Git URL for the web app
GIT_URL=$(az webapp deployment source config-local-git \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --query url -o tsv)

echo "Git deployment URL: ${GIT_URL}"

# Step 11: Add Azure remote and push
cd "${ARTIFACT_DIR}"
git remote add azure "${GIT_URL}"
git push azure master 2>&1 || git push azure main 2>&1 || echo "Push attempted"

# Step 12: Configure auto-scaling settings
az monitor autoscale create \
  --resource-group "${RESOURCE_GROUP}" \
  --resource "${APP_SERVICE_PLAN}" \
  --resource-type "Microsoft.Web/serverfarms" \
  --name "azurehaymaker-autoscale-${UNIQUE_ID}" \
  --min-count 1 \
  --max-count 5 \
  --count 1

# Step 13: Enable Application Insights
az webapp config set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --use-32bit-worker-process false

# Step 14: Wait for deployment to complete
echo "Waiting for application deployment..."
sleep 60
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify App Service Plan
az appservice plan show --resource-group "${RESOURCE_GROUP}" --name "${APP_SERVICE_PLAN}"

# Verify Web App
az webapp show --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}"

# Get the web app URL
WEB_APP_URL=$(az webapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --query defaultHostName -o tsv)

echo "Web App URL: https://${WEB_APP_URL}"

# Test the application
curl -I "https://${WEB_APP_URL}" || echo "Note: App may still be deploying"

# Test health endpoint
curl "https://${WEB_APP_URL}/api/health"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Monitor application performance
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${WEB_APP_NAME}" \
  --metric "CpuTime" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 2: Check HTTP request metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${WEB_APP_NAME}" \
  --metric "Requests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 3: View application logs
az webapp log tail --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}" --lines 50

# Operation 4: Restart the web app
az webapp restart --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}"

# Operation 5: Update application settings
az webapp config appsettings set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --settings "FLASK_ENV=production" "DEBUG=False"

# Operation 6: Enable diagnostics logging
az webapp log config \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --application-logging true \
  --level verbose

# Operation 7: Check deployment status and history
az webapp deployment list --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}" --output table

# Operation 8: View Application Insights traces
az monitor app-insights query \
  --app "${APP_INSIGHTS_NAME}" \
  --analytics-query "traces | take 10"

# Operation 9: Test API endpoints
WEB_APP_URL=$(az webapp show --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}" --query defaultHostName -o tsv)
echo "Testing API endpoints..."
curl "https://${WEB_APP_URL}/api/info"
curl "https://${WEB_APP_URL}/api/status"
curl "https://${WEB_APP_URL}/api/echo/test-message"

# Operation 10: Scale up the App Service Plan
az appservice plan update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE_PLAN}" \
  --sku S1

# Operation 11: View auto-scale settings
az monitor autoscale show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "azurehaymaker-autoscale-${UNIQUE_ID}"

# Operation 12: Check application deployment slots
az webapp deployment slot list --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}" --output table

# Operation 13: Update Python runtime version
az webapp config set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --linux-fx-version "PYTHON|3.10"

# Operation 14: Monitor HTTP response times
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${WEB_APP_NAME}" \
  --metric "ResponseTime" \
  --start-time $(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group (includes app service, app insights, etc.)
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 2: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 120

# Step 3: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 4: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 5: Clean up local files
rm -rf "${ARTIFACT_DIR}"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-compute-${UNIQUE_ID}-rg`
- App Service Plan: `azurehaymaker-asp-${UNIQUE_ID}`
- Web App: `azurehaymaker-py-app-${UNIQUE_ID}`
- Application Insights: `azurehaymaker-appinsights-${UNIQUE_ID}`
- Log Analytics: `azurehaymaker-logs-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure App Service Overview](https://learn.microsoft.com/en-us/azure/app-service/overview)
- [Create Python Web App on App Service](https://learn.microsoft.com/en-us/azure/app-service/quickstart-python)
- [Configure Python Apps on App Service](https://learn.microsoft.com/en-us/azure/app-service/configure-language-python)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Application Insights for Python](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
- [App Service Auto-Scale](https://learn.microsoft.com/en-us/azure/app-service/manage-scale-up)

---

## Automation Tool
**Recommended**: Azure CLI with Git

**Rationale**: Azure CLI provides comprehensive App Service management while Git enables continuous deployment. This serverless compute approach eliminates VM management overhead while maintaining full scalability.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8+ hours (with monitoring, scaling, and application updates)
- **Cleanup**: 5-10 minutes

---

## Notes
- Flask application includes health check, info, and status endpoints
- Application Insights integration for automatic performance monitoring
- Auto-scaling configured to handle traffic spikes (1-5 instances)
- Local Git deployment used for quick iteration
- Python 3.9 runtime selected for stability and support
- gunicorn used as production WSGI server
- All operations scoped to single tenant and subscription
- Application designed for microservices and API-first architecture
