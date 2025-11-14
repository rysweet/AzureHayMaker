# Scenario: Computer Vision API for Image Analysis

## Technology Area
AI & ML

## Company Profile
- **Company Size**: Small startup
- **Industry**: E-commerce / Product Management
- **Use Case**: Automated product image analysis and categorization for catalog management and quality control

## Scenario Description
Deploy Azure Cognitive Services Computer Vision API to automatically analyze product images, extract object information, and generate descriptions. This scenario covers resource provisioning, image analysis operations, and management of AI service metrics and performance.

## Azure Services Used
- Azure Cognitive Services (Computer Vision)
- Azure Storage Account (for image storage)
- Azure Key Vault (for API credentials)
- Azure Application Insights (for monitoring)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Sample images for testing (or we'll create them)
- cURL or similar tool for API calls

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-vision-${UNIQUE_ID}-rg"
LOCATION="eastus"
VISION_RESOURCE="azurehaymaker-vision-${UNIQUE_ID}"
STORAGE_ACCOUNT="azhmakvision${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
INSIGHTS_NAME="azurehaymaker-insights-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=ai-ml-vision Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Azure Cognitive Services Computer Vision
az cognitiveservices account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VISION_RESOURCE}" \
  --kind ComputerVision \
  --sku S0 \
  --location "${LOCATION}" \
  --custom-domain "${VISION_RESOURCE}" \
  --tags ${TAGS}

# Step 3: Get Computer Vision endpoint and key
VISION_ENDPOINT=$(az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VISION_RESOURCE}" \
  --query "properties.endpoint" -o tsv)

VISION_KEY=$(az cognitiveservices account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VISION_RESOURCE}" \
  --query "key1" -o tsv)

echo "Vision Endpoint: ${VISION_ENDPOINT}"
echo "Vision Key: ${VISION_KEY}"

# Step 4: Create Storage Account for image storage
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 5: Create storage container for images
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "product-images" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

# Step 6: Create Key Vault for credentials
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 7: Store Vision credentials in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "vision-endpoint" \
  --value "${VISION_ENDPOINT}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "vision-key" \
  --value "${VISION_KEY}"

# Step 8: Create Application Insights for monitoring
az monitor app-insights component create \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --kind web \
  --tags ${TAGS}

# Step 9: Get Application Insights instrumentation key
INSIGHTS_KEY=$(az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "instrumentationKey" -o tsv)

echo "Application Insights Key: ${INSIGHTS_KEY}"

# Step 10: Create a test image file (simple PNG placeholder)
cat > /tmp/test-image.txt << EOF
This is a test image file reference
Used for demonstrating Computer Vision API
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "product-images" \
  --name "test-product-001.txt" \
  --file /tmp/test-image.txt
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Computer Vision Resource
az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VISION_RESOURCE}"

# Verify Storage Account
az storage account show \
  --name "${STORAGE_ACCOUNT}"

# Verify Storage Container
az storage container exists \
  --name "product-images" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# Verify Application Insights
az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table

# Test Computer Vision API connectivity
curl -I -X GET "${VISION_ENDPOINT}computervision/models?api-version=2024-02-01" \
  -H "Ocp-Apim-Subscription-Key: ${VISION_KEY}"
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Analyze an image using Computer Vision (using a public URL)
TEST_IMAGE_URL="https://learn.microsoft.com/en-us/azure/cognitive-services/computer-vision/media/quickstarts/presentation.png"

curl -X POST "${VISION_ENDPOINT}vision/v3.2/analyze?visualFeatures=Categories,Description,Color,Objects&language=en" \
  -H "Ocp-Apim-Subscription-Key: ${VISION_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${TEST_IMAGE_URL}\"}" \
  | jq '.' > /tmp/vision-analysis-result.json

cat /tmp/vision-analysis-result.json

# Operation 2: Extract text from an image using OCR
curl -X POST "${VISION_ENDPOINT}vision/v3.2/read/analyze" \
  -H "Ocp-Apim-Subscription-Key: ${VISION_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${TEST_IMAGE_URL}\"}" \
  | jq '.'

# Operation 3: Get Computer Vision account details and quota
az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VISION_RESOURCE}" \
  --query "{Name: name, Kind: kind, Sku: sku.name, Endpoint: properties.endpoint, ProvisioningState: properties.provisioningState}"

# Operation 4: List all images in storage container
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "product-images" \
  --output table

# Operation 5: Monitor Computer Vision account metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${VISION_RESOURCE}" \
  --metric "SuccessfulRequests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 6: Check Application Insights performance metrics
az monitor app-insights metrics show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --metric "performanceCounters/processCpuTime"

# Operation 7: Upload additional test images
for i in {1..3}; do
  cat > /tmp/test-image-${i}.txt << EOF
Test product image ${i}
EOF
  az storage blob upload \
    --account-name "${STORAGE_ACCOUNT}" \
    --account-key "${STORAGE_KEY}" \
    --container-name "product-images" \
    --name "product-batch-${i}.txt" \
    --file /tmp/test-image-${i}.txt \
    --overwrite
done

# Operation 8: Batch tag computation (list and review stored results)
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "product-images" \
  --num-results 10

# Operation 9: Retrieve stored analysis results
az keyvault secret list --vault-name "${KEYVAULT}" --output table

# Operation 10: Check Computer Vision API availability and health
az cognitiveservices account identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VISION_RESOURCE}"

# Operation 11: Monitor API throttling status
curl -X GET "${VISION_ENDPOINT}computervision/models?api-version=2024-02-01" \
  -H "Ocp-Apim-Subscription-Key: ${VISION_KEY}" \
  -w "\n%{http_code}\n" \
  -D /tmp/vision-headers.txt

cat /tmp/vision-headers.txt | grep -i "apim"

# Operation 12: List all stored credentials and configuration
az keyvault secret list --vault-name "${KEYVAULT}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group (includes all resources)
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
- Resource Group: `azurehaymaker-vision-${UNIQUE_ID}-rg`
- Computer Vision: `azurehaymaker-vision-${UNIQUE_ID}`
- Storage Account: `azhmakvision${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- App Insights: `azurehaymaker-insights-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Computer Vision Documentation](https://learn.microsoft.com/en-us/azure/cognitive-services/computer-vision/)
- [Computer Vision API Reference](https://learn.microsoft.com/en-us/azure/cognitive-services/computer-vision/reference)
- [Analyze Images with Computer Vision](https://learn.microsoft.com/en-us/azure/cognitive-services/computer-vision/concept-analyzing-images)
- [Azure Cognitive Services CLI Reference](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices)
- [Azure Storage Blobs](https://learn.microsoft.com/en-us/azure/storage/blobs/)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides straightforward commands for provisioning and managing Cognitive Services resources. The REST API calls can be made directly with curl, making this a flexible and scriptable approach for AI service operations.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (with multiple analyses, monitoring, and batch operations)
- **Cleanup**: 5-10 minutes

---

## Notes
- Computer Vision API uses pay-per-call or subscription-based billing
- Images can be analyzed from public URLs or uploaded to storage
- OCR supports multiple languages
- Results are returned in JSON format with confidence scores
- All operations scoped to single tenant and subscription
- Storage account provides persistent image storage for batch operations
- Key Vault securely stores API credentials
