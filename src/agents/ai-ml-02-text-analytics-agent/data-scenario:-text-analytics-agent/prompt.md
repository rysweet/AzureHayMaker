# Scenario: Text Analytics for Sentiment Analysis

## Technology Area
AI & ML

## Company Profile
- **Company Size**: Mid-size tech company
- **Industry**: Customer Service / SaaS Platform
- **Use Case**: Analyze customer feedback and support tickets for sentiment to prioritize high-value support cases and identify trends

## Scenario Description
Deploy Azure Cognitive Services Text Analytics to analyze customer feedback, support tickets, and reviews for sentiment scores and key phrases. This scenario demonstrates text processing, sentiment classification, and operational management of language AI services.

## Azure Services Used
- Azure Cognitive Services (Text Analytics)
- Azure Storage Account (for text data storage)
- Azure Cosmos DB (for storing analysis results)
- Azure Key Vault (for API credentials)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Sample text data for analysis
- cURL or similar tool for API calls

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-textanalytics-${UNIQUE_ID}-rg"
LOCATION="eastus"
TEXT_RESOURCE="azurehaymaker-text-${UNIQUE_ID}"
STORAGE_ACCOUNT="azhmaktext${UNIQUE_ID}"
COSMOS_ACCOUNT="azurehaymaker-cosmos-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
COSMOS_DB="sentiment-analysis"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=ai-ml-text-analytics Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Azure Cognitive Services Text Analytics
az cognitiveservices account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${TEXT_RESOURCE}" \
  --kind TextAnalytics \
  --sku S0 \
  --location "${LOCATION}" \
  --custom-domain "${TEXT_RESOURCE}" \
  --tags ${TAGS}

# Step 3: Get Text Analytics endpoint and key
TEXT_ENDPOINT=$(az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${TEXT_RESOURCE}" \
  --query "properties.endpoint" -o tsv)

TEXT_KEY=$(az cognitiveservices account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${TEXT_RESOURCE}" \
  --query "key1" -o tsv)

echo "Text Analytics Endpoint: ${TEXT_ENDPOINT}"
echo "Text Analytics Key: ${TEXT_KEY}"

# Step 4: Create Storage Account for text data storage
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 5: Create storage containers
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "feedback-data" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

az storage container create \
  --name "analysis-results" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

# Step 6: Create Cosmos DB account for storing results
az cosmosdb create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${COSMOS_ACCOUNT}" \
  --locations regionName="${LOCATION}" isZoneRedundant=false failoverPriority=0 \
  --capabilities EnableServerless \
  --kind GlobalDocumentDB \
  --tags ${TAGS}

# Step 7: Create Cosmos DB database
az cosmosdb sql database create \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${COSMOS_ACCOUNT}" \
  --name "${COSMOS_DB}"

# Step 8: Create Cosmos DB container for sentiment results
az cosmosdb sql container create \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${COSMOS_ACCOUNT}" \
  --database-name "${COSMOS_DB}" \
  --name "sentiment-results" \
  --partition-key-path "/id"

# Step 9: Create Key Vault and store credentials
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "text-endpoint" \
  --value "${TEXT_ENDPOINT}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "text-key" \
  --value "${TEXT_KEY}"

# Step 10: Upload sample feedback data
cat > /tmp/customer-feedback.json << EOF
{
  "documents": [
    {
      "id": "1",
      "language": "en",
      "text": "This product is absolutely amazing! I love it and recommend to everyone."
    },
    {
      "id": "2",
      "language": "en",
      "text": "Terrible experience. The service was slow and unhelpful. Very disappointed."
    },
    {
      "id": "3",
      "language": "en",
      "text": "Good product overall. Works as expected. Some minor issues but acceptable."
    }
  ]
}
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "feedback-data" \
  --name "feedback-batch-001.json" \
  --file /tmp/customer-feedback.json
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Text Analytics Resource
az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${TEXT_RESOURCE}"

# Verify Storage Account
az storage account show --name "${STORAGE_ACCOUNT}"

# Verify Cosmos DB Account
az cosmosdb show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${COSMOS_ACCOUNT}"

# Verify Cosmos DB Database and Container
az cosmosdb sql database show \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${COSMOS_ACCOUNT}" \
  --name "${COSMOS_DB}"

az cosmosdb sql container show \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${COSMOS_ACCOUNT}" \
  --database-name "${COSMOS_DB}" \
  --name "sentiment-results"

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table

# Test Text Analytics API connectivity
curl -I -X GET "${TEXT_ENDPOINT}text/analytics/v3.1/languages" \
  -H "Ocp-Apim-Subscription-Key: ${TEXT_KEY}"
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Analyze sentiment of customer feedback
curl -X POST "${TEXT_ENDPOINT}text/analytics/v3.1/sentiment?model-version=latest&showStats=true" \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: ${TEXT_KEY}" \
  -d @/tmp/customer-feedback.json \
  | jq '.' > /tmp/sentiment-results.json

cat /tmp/sentiment-results.json

# Operation 2: Extract key phrases from feedback
curl -X POST "${TEXT_ENDPOINT}text/analytics/v3.1/keyPhrases" \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: ${TEXT_KEY}" \
  -d @/tmp/customer-feedback.json \
  | jq '.documents[] | {id, keyPhrases}'

# Operation 3: Detect language of text documents
curl -X POST "${TEXT_ENDPOINT}text/analytics/v3.1/languages" \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: ${TEXT_KEY}" \
  -d @/tmp/customer-feedback.json \
  | jq '.'

# Operation 4: Extract named entities
curl -X POST "${TEXT_ENDPOINT}text/analytics/v3.1/entities/recognition/general" \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: ${TEXT_KEY}" \
  -d @/tmp/customer-feedback.json \
  | jq '.documents[] | {id, entities}'

# Operation 5: Store analysis results in Cosmos DB
COSMOS_KEY=$(az cosmosdb keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${COSMOS_ACCOUNT}" \
  --type keys \
  --query primaryMasterKey -o tsv)

cat > /tmp/cosmos-insert.json << EOF
{
  "id": "sentiment-analysis-${UNIQUE_ID}",
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "documentsAnalyzed": 3,
  "sentimentDistribution": {
    "positive": 1,
    "negative": 1,
    "neutral": 1
  }
}
EOF

# Operation 6: Upload processed results to storage
az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "analysis-results" \
  --name "sentiment-${UNIQUE_ID}.json" \
  --file /tmp/sentiment-results.json

# Operation 7: List all feedback files processed
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "feedback-data" \
  --output table

# Operation 8: Get Text Analytics resource quota and usage
az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${TEXT_RESOURCE}" \
  --query "{Name: name, Kind: kind, Sku: sku.name, Endpoint: properties.endpoint}"

# Operation 9: Monitor Text Analytics metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${TEXT_RESOURCE}" \
  --metric "SuccessfulRequests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 10: Add new customer feedback for analysis
cat > /tmp/new-feedback.json << EOF
{
  "documents": [
    {
      "id": "4",
      "language": "en",
      "text": "Outstanding customer service and excellent product quality!"
    }
  ]
}
EOF

curl -X POST "${TEXT_ENDPOINT}text/analytics/v3.1/sentiment" \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: ${TEXT_KEY}" \
  -d @/tmp/new-feedback.json | jq '.documents[0] | {id, sentiment, scores}'

# Operation 11: Check Cosmos DB item count
COSMOS_URI="https://${COSMOS_ACCOUNT}.documents.azure.com:443/"
echo "Cosmos DB connection string generated for: ${COSMOS_URI}"

# Operation 12: Retrieve and display analysis from storage
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "analysis-results" \
  --output table
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
- Resource Group: `azurehaymaker-textanalytics-${UNIQUE_ID}-rg`
- Text Analytics: `azurehaymaker-text-${UNIQUE_ID}`
- Storage Account: `azhmaktext${UNIQUE_ID}`
- Cosmos DB: `azurehaymaker-cosmos-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Text Analytics Documentation](https://learn.microsoft.com/en-us/azure/cognitive-services/text-analytics/)
- [Text Analytics API Reference](https://learn.microsoft.com/en-us/azure/cognitive-services/text-analytics/how-tos/text-analytics-how-to-call-api)
- [Sentiment Analysis Guide](https://learn.microsoft.com/en-us/azure/cognitive-services/text-analytics/concepts/sentiment-analysis)
- [Key Phrase Extraction](https://learn.microsoft.com/en-us/azure/cognitive-services/text-analytics/concepts/key-phrase-extraction)
- [Named Entity Recognition](https://learn.microsoft.com/en-us/azure/cognitive-services/text-analytics/concepts/named-entity-recognition)
- [Azure Cosmos DB Overview](https://learn.microsoft.com/en-us/azure/cosmos-db/introduction)

---

## Automation Tool
**Recommended**: Azure CLI with REST API calls

**Rationale**: Azure CLI manages infrastructure provisioning efficiently, while REST API calls via curl provide flexible text analysis operations. This combination gives straightforward access to all Text Analytics capabilities.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8+ hours (with multiple analyses, data uploads, and result storage)
- **Cleanup**: 5-10 minutes

---

## Notes
- Text Analytics supports multiple languages and language detection
- Sentiment analysis returns scores from 0 (negative) to 1 (positive)
- Key phrases are automatically extracted from input text
- Cosmos DB stores analysis results in a scalable, distributed manner
- All operations scoped to single tenant and subscription
- Results include confidence scores for each classification
- Document size limited to 5,120 characters per document
