# Scenario: Power BI Embedded Reports

## Technology Area
Analytics

## Company Profile
- **Company Size**: Mid-size SaaS company
- **Industry**: Technology / Business Intelligence
- **Use Case**: Embed Power BI reports into customer-facing applications

## Scenario Description
Deploy Power BI Embedded capacity with datasets and reports. Create service principal for programmatic access, configure capacity scaling, and demonstrate report embedding in applications.

## Azure Services Used
- Power BI Embedded (capacity)
- Power BI API
- Azure Service Principal (authentication)
- Azure Key Vault (credentials storage)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-analytics-powerbi-${UNIQUE_ID}-rg"
LOCATION="eastus"
POWERBI_CAPACITY="azurehaymaker-pbi-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
APP_NAME="azurehaymaker-powerbi-app-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=analytics-power-bi-embed Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Key Vault for storing credentials
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 3: Create Service Principal for Power BI access
SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "${APP_NAME}" \
  --role Reader)

SP_OBJECT_ID=$(echo ${SP_OUTPUT} | jq -r '.id')
SP_CLIENT_ID=$(echo ${SP_OUTPUT} | jq -r '.appId')
SP_TENANT_ID=$(echo ${SP_OUTPUT} | jq -r '.tenant')
SP_PASSWORD=$(echo ${SP_OUTPUT} | jq -r '.password')

# Store in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "powerbi-client-id" \
  --value "${SP_CLIENT_ID}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "powerbi-client-secret" \
  --value "${SP_PASSWORD}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "powerbi-tenant-id" \
  --value "${SP_TENANT_ID}"

# Step 4: Create Power BI Embedded Capacity
az powerbi embedded-capacity create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POWERBI_CAPACITY}" \
  --sku "A1" \
  --location "${LOCATION}" \
  --administrator "${SP_OBJECT_ID}" \
  --tags ${TAGS}

# Step 5: Create sample Power BI workspace collection
# (Note: This requires Power BI API calls, storing configuration for reference)
cat > /tmp/powerbi_config.json <<EOF
{
  "workspaceName": "SalesAnalytics",
  "displayName": "Sales Analytics Workspace",
  "description": "Embedded analytics workspace for customer reports",
  "capacity": "${POWERBI_CAPACITY}",
  "datasets": [
    {
      "name": "SalesData",
      "description": "Historical sales data"
    },
    {
      "name": "CustomerMetrics",
      "description": "Customer metrics and KPIs"
    }
  ],
  "reports": [
    {
      "name": "SalesOverview",
      "description": "High-level sales dashboard"
    },
    {
      "name": "RegionalAnalysis",
      "description": "Regional sales breakdown"
    }
  ]
}
EOF

# Step 6: Enable Power BI Embedded capacity
az powerbi embedded-capacity update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POWERBI_CAPACITY}" \
  --sku "A1"

# Step 7: Create sample application database (for demo)
cat > /tmp/powerbi_app_config.json <<EOF
{
  "appName": "CustomerDashboard",
  "embedApiUrl": "https://api.powerbi.com",
  "datasetId": "dataset-id-placeholder",
  "reportId": "report-id-placeholder",
  "workspaceId": "workspace-id-placeholder",
  "permissions": ["View", "Update", "Create"],
  "features": [
    "Embedding",
    "Export to PDF",
    "Refresh",
    "Filters"
  ]
}
EOF

# Step 8: Store application configuration in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "powerbi-app-config" \
  --value @/tmp/powerbi_app_config.json

# Step 9: Create storage account for Power BI export scenarios
STORAGE_ACCOUNT="azmkrpbi${UNIQUE_ID}"

az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 10: Set CORS on storage for embedded reports
az storage cors add \
  --services b \
  --methods GET POST PUT DELETE \
  --allowed-origins "*" \
  --allowed-headers "*" \
  --exposed-headers "*" \
  --account-name "${STORAGE_ACCOUNT}"

echo ""
echo "=========================================="
echo "Power BI Embedded Capacity Created"
echo "Capacity Name: ${POWERBI_CAPACITY}"
echo "Service Principal: ${APP_NAME}"
echo "Config stored in Key Vault: ${KEYVAULT}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Power BI Embedded Capacity
az powerbi embedded-capacity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POWERBI_CAPACITY}"

# Check capacity status
az powerbi embedded-capacity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POWERBI_CAPACITY}" \
  --query "state" -o tsv

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# List Key Vault secrets
az keyvault secret list \
  --vault-name "${KEYVAULT}" \
  --query "[].name" -o table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Scale Power BI Embedded capacity
az powerbi embedded-capacity update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POWERBI_CAPACITY}" \
  --sku "A2"

# Operation 2: Check capacity SKU
az powerbi embedded-capacity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POWERBI_CAPACITY}" \
  --query "sku" -o tsv

# Operation 3: Suspend capacity (to save costs during off-hours)
az powerbi embedded-capacity update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POWERBI_CAPACITY}" \
  --mode "Gen2"

# Operation 4: Monitor capacity metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.PowerBIDedicated/capacities/${POWERBI_CAPACITY}" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 5: Create additional Key Vault secret for workspace token
WORKSPACE_TOKEN="token-placeholder-$(date +%s)"
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "powerbi-workspace-token" \
  --value "${WORKSPACE_TOKEN}"

# Operation 6: Retrieve configuration from Key Vault
az keyvault secret show \
  --vault-name "${KEYVAULT}" \
  --name "powerbi-client-id" \
  --query "value" -o tsv

# Operation 7: Create service principal assignment
az ad app permission add \
  --id ${SP_CLIENT_ID} \
  --api 00000009-0000-0000-c000-000000000000 \
  --api-permissions "dcf25eaf-e99c-434c-a505-352a08913b1f=Application"

# Operation 8: Upload sample Power BI report file (for reference)
cat > /tmp/report_manifest.json <<EOF
{
  "reports": [
    {
      "id": "report-1",
      "name": "Sales Dashboard",
      "description": "Main sales metrics dashboard",
      "refreshSchedule": "daily at 2 AM"
    },
    {
      "id": "report-2",
      "name": "Customer Analysis",
      "description": "Deep dive customer metrics",
      "refreshSchedule": "weekly on Monday"
    }
  ]
}
EOF

STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage blob create-container \
  --name "powerbi-artifacts" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" 2>/dev/null || true

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "powerbi-artifacts" \
  --name "report_manifest.json" \
  --file /tmp/report_manifest.json
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete Service Principal
az ad sp delete --id ${SP_OBJECT_ID}

# Step 2: Delete application registration
az ad app delete --id ${SP_CLIENT_ID}

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
rm -rf /tmp/powerbi_config.json /tmp/powerbi_app_config.json /tmp/report_manifest.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-analytics-powerbi-${UNIQUE_ID}-rg`
- Power BI Embedded Capacity: `azurehaymaker-pbi-${UNIQUE_ID}`
- Storage Account: `azmkrpbi${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- Service Principal App: `azurehaymaker-powerbi-app-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Power BI Embedded Overview](https://learn.microsoft.com/en-us/azure/power-bi-embedded/overview)
- [Capacity and SKUs](https://learn.microsoft.com/en-us/azure/power-bi-embedded/capacity-skus)
- [Power BI Embedding for Customers](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-sample-for-customers)
- [Service Principal Authentication](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-service-principal)
- [Power BI REST API](https://learn.microsoft.com/en-us/rest/api/power-bi/)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI handles capacity provisioning and Key Vault management efficiently. Power BI API calls for workspace and report management are typically handled by application code or Power BI management tools.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8 hours (with scaling, monitoring, and configuration)
- **Cleanup**: 10-15 minutes

---

## Notes
- Power BI Embedded supports multiple SKUs (A1-A3, Gen2)
- Service Principal authentication enables programmatic access
- Capacity must be paused/resumed to save costs
- Tokens are time-limited and must be refreshed
- All operations scoped to single tenant and subscription
- Reports can be embedded in web applications and Power BI apps
- Premium SKUs support dedicated capacity for predictable performance
