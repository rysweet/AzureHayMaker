# Scenario: Serverless HTTP Triggers with Azure Functions

## Technology Area
Compute

## Company Profile
- **Company Size**: Small startup
- **Industry**: Event-Driven Services / APIs
- **Use Case**: Deploy serverless HTTP-triggered functions for lightweight API endpoints and webhooks

## Scenario Description
Deploy Azure Functions with HTTP triggers to create serverless API endpoints. Functions automatically scale based on demand, with minimal operational overhead. Includes function monitoring, logging, and integration with Application Insights.

## Azure Services Used
- Azure Functions
- Azure Storage Account (function runtime)
- Azure Application Insights
- Azure Log Analytics Workspace
- Azure Event Grid (optional for triggers)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed with function core tools extension
- Node.js 18+ or Python 3.9+ for local development
- Azure Functions Core Tools installed locally (optional for testing)

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-compute-${UNIQUE_ID}-rg"
LOCATION="eastus"
STORAGE_ACCOUNT="azurehaymaker${UNIQUE_ID}"
FUNCTION_APP_NAME="azurehaymaker-func-${UNIQUE_ID}"
APP_INSIGHTS_NAME="azurehaymaker-appinsights-${UNIQUE_ID}"
LOG_ANALYTICS_NAME="azurehaymaker-logs-${UNIQUE_ID}"
RUNTIME="python"  # or "node" for JavaScript
RUNTIME_VERSION="3.10"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=compute-azure-functions Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Log Analytics Workspace
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

# Step 3: Create Application Insights
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

# Step 4: Create Storage Account for function runtime
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --tags ${TAGS}

STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --query connectionString -o tsv)

# Step 5: Create Function App
az functionapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --consumption-plan-location "${LOCATION}" \
  --runtime ${RUNTIME} \
  --runtime-version ${RUNTIME_VERSION} \
  --functions-version 4 \
  --name "${FUNCTION_APP_NAME}" \
  --storage-account "${STORAGE_ACCOUNT}" \
  --os-type Linux \
  --tags ${TAGS}

# Step 6: Configure application settings for Application Insights
az functionapp config appsettings set \
  --name "${FUNCTION_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --settings "APPINSIGHTS_INSTRUMENTATIONKEY=${INSTRUMENTATION_KEY}" \
  "ApplicationInsightsAgent_EXTENSION_VERSION=~3" \
  "ENVIRONMENT=production"

# Step 7: Create HTTP trigger function - HelloWorld
az functionapp function create \
  --resource-group "${RESOURCE_GROUP}" \
  --function-app-name "${FUNCTION_APP_NAME}" \
  --name "HelloWorld" \
  --template "HTTP trigger"

# Step 8: Update HelloWorld function code (Python)
cat > /tmp/hello_function_code.py <<'EOF'
import azure.functions as func
import json
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function that returns a JSON response
    """
    name = req.params.get('name', 'Azure')

    response_data = {
        'message': f'Hello, {name}!',
        'timestamp': datetime.utcnow().isoformat(),
        'scenario': 'compute-04-azure-functions-http',
        'function': 'HelloWorld'
    }

    return func.HttpResponse(
        json.dumps(response_data),
        status_code=200,
        mimetype="application/json"
    )
EOF

# Step 9: Create API Status function
az functionapp function create \
  --resource-group "${RESOURCE_GROUP}" \
  --function-app-name "${FUNCTION_APP_NAME}" \
  --name "ApiStatus" \
  --template "HTTP trigger"

# Step 10: Create Echo function
az functionapp function create \
  --resource-group "${RESOURCE_GROUP}" \
  --function-app-name "${FUNCTION_APP_NAME}" \
  --name "Echo" \
  --template "HTTP trigger"

# Step 11: Create HealthCheck function
az functionapp function create \
  --resource-group "${RESOURCE_GROUP}" \
  --function-app-name "${FUNCTION_APP_NAME}" \
  --name "HealthCheck" \
  --template "HTTP trigger"

# Step 12: Get Function App master key for testing
MASTER_KEY=$(az functionapp keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FUNCTION_APP_NAME}" \
  --query "masterKey" -o tsv)

# Step 13: Get function URL
FUNCTION_URL=$(az functionapp function show \
  --resource-group "${RESOURCE_GROUP}" \
  --function-app-name "${FUNCTION_APP_NAME}" \
  --name "HelloWorld" \
  --query "invokeUrlTemplate" -o tsv)

echo "Function App Name: ${FUNCTION_APP_NAME}"
echo "Function URL: ${FUNCTION_URL}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Function App
az functionapp show --resource-group "${RESOURCE_GROUP}" --name "${FUNCTION_APP_NAME}"

# List all functions
az functionapp function list --resource-group "${RESOURCE_GROUP}" --name "${FUNCTION_APP_NAME}" --output table

# Get function app URL
FUNC_APP_URL=$(az functionapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FUNCTION_APP_NAME}" \
  --query "defaultHostName" -o tsv)

echo "Function App URL: https://${FUNC_APP_URL}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Monitor function execution metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${FUNCTION_APP_NAME}" \
  --metric "FunctionExecutionCount" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 2: Monitor function execution units
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${FUNCTION_APP_NAME}" \
  --metric "FunctionExecutionUnits" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 3: View function logs in real-time
az webapp log tail \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FUNCTION_APP_NAME}" \
  --lines 50

# Operation 4: Query Application Insights for recent traces
az monitor app-insights query \
  --app "${APP_INSIGHTS_NAME}" \
  --analytics-query "traces | where timestamp > ago(1h) | take 20"

# Operation 5: Get application settings
az functionapp config appsettings list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FUNCTION_APP_NAME}"

# Operation 6: Update function configuration settings
az functionapp config set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FUNCTION_APP_NAME}" \
  --use-32bit-worker-process false \
  --always-on true

# Operation 7: List function key for authentication
az functionapp function keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --function-app-name "${FUNCTION_APP_NAME}" \
  --name "HelloWorld"

# Operation 8: Test HelloWorld function via HTTP
FUNC_APP_URL=$(az functionapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FUNCTION_APP_NAME}" \
  --query "defaultHostName" -o tsv)

curl "https://${FUNC_APP_URL}/api/HelloWorld?name=AzureHayMaker"

# Operation 9: Create timer-based trigger function for scheduled execution
az functionapp function create \
  --resource-group "${RESOURCE_GROUP}" \
  --function-app-name "${FUNCTION_APP_NAME}" \
  --name "ScheduledJob" \
  --template "Timer trigger"

# Operation 10: Monitor HTTP response times
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${FUNCTION_APP_NAME}" \
  --metric "AverageResponseTime" \
  --start-time $(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 11: Enable staging slot for blue-green deployment
az functionapp deployment slot create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FUNCTION_APP_NAME}" \
  --slot "staging"

# Operation 12: View storage account connected to function app
az storage account list --resource-group "${RESOURCE_GROUP}" --output table

# Operation 13: Monitor storage operations for function data
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}" \
  --metric "Transactions" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 14: Check function app memory usage
az functionapp config set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FUNCTION_APP_NAME}" \
  --number-of-workers 1
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

# Step 2: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 120

# Step 3: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 4: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-compute-${UNIQUE_ID}-rg`
- Function App: `azurehaymaker-func-${UNIQUE_ID}`
- Storage Account: `azurehaymaker${UNIQUE_ID}`
- Application Insights: `azurehaymaker-appinsights-${UNIQUE_ID}`
- Log Analytics: `azurehaymaker-logs-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Functions Overview](https://learn.microsoft.com/en-us/azure/azure-functions/functions-overview)
- [Create HTTP Trigger Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-first-azure-function-azure-cli)
- [Azure Functions Python Developer Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Application Insights for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-monitoring)
- [Azure Functions Bindings](https://learn.microsoft.com/en-us/azure/azure-functions/functions-triggers-bindings)
- [Azure Functions Pricing](https://azure.microsoft.com/en-us/pricing/details/functions/)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides excellent Azure Functions management with straightforward commands for creation, deployment, and monitoring. The consumption plan model provides automatic scaling without infrastructure management.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (with function testing, monitoring, and scaling operations)
- **Cleanup**: 5 minutes

---

## Notes
- Functions run on consumption plan with automatic scaling (0-unlimited instances)
- Charges only for actual function execution time and requests
- HTTP triggers provide RESTful API endpoints
- Application Insights automatically collects function performance metrics
- Python 3.10 runtime selected for modern language features
- Storage account required for function state and bindings
- All operations scoped to single tenant and subscription
- Ideal for microservices, webhooks, and event-driven architectures
- No VM or container management required - fully serverless
