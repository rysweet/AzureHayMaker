# Scenario: Azure API Management Gateway

## Technology Area
Web Apps

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Technology / SaaS
- **Use Case**: Centralize API management, security, and analytics across microservices

## Scenario Description
Deploy Azure API Management to manage, protect, and monitor APIs. Configure API policies, implement rate limiting, set up developer portal, and integrate with backend services.

## Azure Services Used
- Azure API Management
- Azure Virtual Network (network integration)
- Azure Key Vault (secrets)
- Azure Application Insights (analytics)

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
RESOURCE_GROUP="azurehaymaker-webapp-apim-${UNIQUE_ID}-rg"
LOCATION="eastus"
APIM_SERVICE="azurehaymaker-apim-${UNIQUE_ID}"
APIM_ADMIN_EMAIL="admin@example.com"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=webapps-api-management Owner=AzureHayMaker"
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
  --subnet-name "apim-subnet" \
  --subnet-prefixes "10.0.0.0/24" \
  --tags ${TAGS}

SUBNET_ID=$(az network vnet subnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "apim-subnet" \
  --query id -o tsv)

# Step 3: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 4: Store backend URLs in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "backend-url-products" \
  --value "https://api.example.com/products"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "backend-url-orders" \
  --value "https://api.example.com/orders"

# Step 5: Create API Management service
az apim create \
  --name "${APIM_SERVICE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --publisher-name "Azure HayMaker" \
  --publisher-email "${APIM_ADMIN_EMAIL}" \
  --sku-name Developer \
  --enable-client-certificate false \
  --enable-managed-identity true \
  --tags ${TAGS}

# Step 6: Create API in APIM
az apim api create \
  --api-id "products-api" \
  --api-type "http" \
  --display-name "Products API" \
  --path "products" \
  --protocols "https" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --service-url "https://api.example.com/products"

# Step 7: Add API operations
az apim api operation create \
  --api-id "products-api" \
  --operation-id "get-all-products" \
  --display-name "Get All Products" \
  --method "GET" \
  --url-template "/" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}"

az apim api operation create \
  --api-id "products-api" \
  --operation-id "get-product" \
  --display-name "Get Product by ID" \
  --method "GET" \
  --url-template "/{id}" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}"

az apim api operation create \
  --api-id "products-api" \
  --operation-id "create-product" \
  --display-name "Create Product" \
  --method "POST" \
  --url-template "/" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}"

# Step 8: Create subscription (access key)
az apim subscription create \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --subscription-id "subscription-1" \
  --display-name "Developer Subscription"

# Step 9: Create product
az apim product create \
  --product-id "basic-product" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --display-name "Basic Product" \
  --description "Basic API product with rate limiting" \
  --subscription-required true \
  --approval-required false \
  --state "published"

# Step 10: Add API to product
az apim product api add \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --product-id "basic-product" \
  --api-id "products-api"

echo ""
echo "=========================================="
echo "API Management Created: ${APIM_SERVICE}"
echo "Gateway URL: https://${APIM_SERVICE}.azure-api.net"
echo "Developer Portal: https://${APIM_SERVICE}.developer.azure-api.net"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify APIM service
az apim show \
  --name "${APIM_SERVICE}" \
  --resource-group "${RESOURCE_GROUP}"

# Check APIM status
az apim show \
  --name "${APIM_SERVICE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "provisioningState" -o tsv

# Get gateway URL
APIM_GATEWAY_URL=$(az apim show \
  --name "${APIM_SERVICE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "gatewayUrl" -o tsv)

echo "Gateway URL: ${APIM_GATEWAY_URL}"

# List APIs
az apim api list \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --output table

# List API operations
az apim api operation list \
  --api-id "products-api" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --output table

# List products
az apim product list \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --output table

# List subscriptions
az apim subscription list \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Add rate limiting policy
cat > /tmp/rate-limit-policy.xml <<EOF
<policies>
  <inbound>
    <rate-limit calls="10" renewal-period="60" />
  </inbound>
</policies>
EOF

az apim api operation policy create-or-update \
  --api-id "products-api" \
  --operation-id "get-all-products" \
  --policy-id "policy" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --value @/tmp/rate-limit-policy.xml

# Operation 2: Create another API
az apim api create \
  --api-id "orders-api" \
  --api-type "http" \
  --display-name "Orders API" \
  --path "orders" \
  --protocols "https" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --service-url "https://api.example.com/orders"

# Operation 3: Add operations to Orders API
az apim api operation create \
  --api-id "orders-api" \
  --operation-id "get-orders" \
  --display-name "Get Orders" \
  --method "GET" \
  --url-template "/" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}"

# Operation 4: Monitor API calls
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ApiManagement/service/${APIM_SERVICE}" \
  --metric "Requests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 5: Check API analytics
echo "API Analytics available in Azure Portal"

# Operation 6: Enable logging
az apim logger create \
  --logger-id "app-insights-logger" \
  --name "AppInsights" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --logger-type "applicationInsights" \
  --is-buffered false

# Operation 7: Create diagnostic setting
az apim diagnostic create-or-update \
  --diagnostic-id "applicationinsights" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --logger-id "app-insights-logger" \
  --always-log-errors true

# Operation 8: Test API operation
echo "Testing API endpoint:"
echo "curl -i -X GET \"${APIM_GATEWAY_URL}/products\" -H \"Ocp-Apim-Subscription-Key: <subscription-key>\""

# Operation 9: Create API version
az apim api create \
  --api-id "products-api-v2" \
  --api-type "http" \
  --display-name "Products API v2" \
  --path "products" \
  --protocols "https" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --service-url "https://api.example.com/v2/products" \
  --api-version "v2"

# Operation 10: List all backends
az apim backend list \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete products
az apim product delete \
  --product-id "basic-product" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --yes

# Step 2: Delete APIs
az apim api delete \
  --api-id "products-api" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --yes

az apim api delete \
  --api-id "orders-api" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
  --yes 2>/dev/null || true

az apim api delete \
  --api-id "products-api-v2" \
  --resource-group "${RESOURCE_GROUP}" \
  --service-name "${APIM_SERVICE}" \
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
rm -rf /tmp/rate-limit-policy.xml
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-webapp-apim-${UNIQUE_ID}-rg`
- API Management: `azurehaymaker-apim-${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure API Management Overview](https://learn.microsoft.com/en-us/azure/api-management/api-management-overview)
- [API Management Policies](https://learn.microsoft.com/en-us/azure/api-management/api-management-policies)
- [API Management Security](https://learn.microsoft.com/en-us/azure/api-management/api-management-security-controls)
- [Developer Portal](https://learn.microsoft.com/en-us/azure/api-management/api-management-customize-styles)
- [APIM CLI Reference](https://learn.microsoft.com/en-us/cli/azure/apim)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI handles API Management operations effectively. Policy files are XML-based and can be managed separately.

---

## Estimated Duration
- **Deployment**: 20-30 minutes (APIM provisioning takes time)
- **Operations Phase**: 8 hours (with API management and monitoring)
- **Cleanup**: 10-15 minutes

---

## Notes
- Developer SKU is suitable for development and testing
- Rate limiting protects backends from overload
- API versioning enables backward compatibility
- Policies enable traffic management and security
- All operations scoped to single tenant and subscription
- Analytics provide insights into API usage
- Built-in developer portal for API documentation
