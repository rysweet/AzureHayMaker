# Scenario: Azure OpenAI Service Deployment

## Technology Area
AI & ML

## Company Profile
- **Company Size**: Mid-size enterprise
- **Industry**: Software Development / Consulting
- **Use Case**: Deploy Azure OpenAI models for code generation, content creation, and AI-powered application features

## Scenario Description
Deploy Azure OpenAI Service with GPT model access, configure API endpoints, and demonstrate model inference operations. This scenario covers resource provisioning, model deployment, API testing, and operational management.

## Azure Services Used
- Azure OpenAI Service
- Azure Storage Account (for prompt/response logs)
- Azure Key Vault (for API credentials and model keys)
- Azure Application Insights (for monitoring)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Azure OpenAI API access (requires registration)
- cURL or similar tool for API calls

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-openai-${UNIQUE_ID}-rg"
LOCATION="eastus"
OPENAI_RESOURCE="azurehaymaker-openai-${UNIQUE_ID}"
STORAGE_ACCOUNT="azurehaymaker${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
INSIGHTS_NAME="azurehaymaker-insights-${UNIQUE_ID}"
DEPLOYMENT_NAME="gpt-35-turbo-deployment"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=ai-ml-openai Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Azure OpenAI Service
az cognitiveservices account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${OPENAI_RESOURCE}" \
  --kind OpenAI \
  --sku s0 \
  --location "${LOCATION}" \
  --custom-domain "${OPENAI_RESOURCE}" \
  --tags ${TAGS}

# Step 3: Get OpenAI endpoint and key
OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${OPENAI_RESOURCE}" \
  --query "properties.endpoint" -o tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${OPENAI_RESOURCE}" \
  --query "key1" -o tsv)

echo "OpenAI Endpoint: ${OPENAI_ENDPOINT}"
echo "OpenAI Key: ${OPENAI_KEY}"

# Step 4: Create model deployment using Azure CLI (if supported)
# Note: Model deployments may require Azure Portal or ARM templates
# This creates the deployment configuration
cat > /tmp/deployment-config.json << EOF
{
  "sku": {
    "name": "standard",
    "capacity": 1
  },
  "properties": {
    "model": {
      "format": "OpenAI",
      "name": "gpt-35-turbo",
      "version": "0613"
    },
    "scaleSettings": {
      "scaleType": "manual",
      "capacity": 1
    }
  }
}
EOF

# Step 5: Create Storage Account for logs
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 6: Create storage containers
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "prompts" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

az storage container create \
  --name "responses" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

az storage container create \
  --name "logs" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

# Step 7: Create Key Vault for credentials
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 8: Store OpenAI credentials in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "openai-endpoint" \
  --value "${OPENAI_ENDPOINT}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "openai-key" \
  --value "${OPENAI_KEY}"

# Step 9: Create Application Insights for monitoring
az monitor app-insights component create \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --kind web \
  --tags ${TAGS}

# Step 10: Get Application Insights key
INSIGHTS_KEY=$(az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "instrumentationKey" -o tsv)

echo "Application Insights Key: ${INSIGHTS_KEY}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify OpenAI Resource
az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${OPENAI_RESOURCE}"

# Verify Storage Account
az storage account show --name "${STORAGE_ACCOUNT}"

# Verify Storage Containers
az storage container list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --output table

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# Verify Application Insights
az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table

# Test OpenAI API connectivity
curl -I -X GET "${OPENAI_ENDPOINT}openai/models" \
  -H "api-key: ${OPENAI_KEY}"
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Test chat completion API with GPT-3.5
curl -X POST "${OPENAI_ENDPOINT}openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-02-15-preview" \
  -H "api-key: ${OPENAI_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is Azure OpenAI Service?"}
    ],
    "temperature": 0.7,
    "max_tokens": 256
  }' | jq '.' > /tmp/openai-response-1.json

cat /tmp/openai-response-1.json

# Operation 2: Test code generation capability
curl -X POST "${OPENAI_ENDPOINT}openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-02-15-preview" \
  -H "api-key: ${OPENAI_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a Python function to calculate factorial"}
    ],
    "temperature": 0.5,
    "max_tokens": 512
  }' | jq '.choices[0].message.content'

# Operation 3: Store prompt in storage
cat > /tmp/prompt-log.txt << EOF
Prompt: What is Azure OpenAI Service?
Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
Model: gpt-35-turbo
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "prompts" \
  --name "prompt-001-$(date +%s).txt" \
  --file /tmp/prompt-log.txt

# Operation 4: Store response in storage
az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "responses" \
  --name "response-001-$(date +%s).json" \
  --file /tmp/openai-response-1.json

# Operation 5: Get OpenAI resource metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${OPENAI_RESOURCE}" \
  --metric "SuccessfulRequests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 6: Test with different temperature (more creative)
curl -X POST "${OPENAI_ENDPOINT}openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-02-15-preview" \
  -H "api-key: ${OPENAI_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Create a creative product name for a new AI tool"}
    ],
    "temperature": 0.9,
    "max_tokens": 100
  }' | jq '.choices[0].message.content'

# Operation 7: Test with system role and context
curl -X POST "${OPENAI_ENDPOINT}openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-02-15-preview" \
  -H "api-key: ${OPENAI_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a technical documentation expert. Answer in bullet points."},
      {"role": "user", "content": "Explain the benefits of using Azure OpenAI Service"}
    ],
    "temperature": 0.3,
    "max_tokens": 256
  }' | jq '.choices[0].message.content'

# Operation 8: List all prompts stored
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "prompts" \
  --output table

# Operation 9: List all responses stored
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "responses" \
  --output table

# Operation 10: Check OpenAI account status and quota
az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${OPENAI_RESOURCE}" \
  --query "{Name: name, Kind: kind, Sku: sku.name, Endpoint: properties.endpoint, ProvisioningState: properties.provisioningState}"

# Operation 11: Retrieve stored credentials
az keyvault secret list --vault-name "${KEYVAULT}" --output table

# Operation 12: Monitor Application Insights
az monitor app-insights metrics show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --metric "requests/rate"
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
- Resource Group: `azurehaymaker-openai-${UNIQUE_ID}-rg`
- OpenAI Service: `azurehaymaker-openai-${UNIQUE_ID}`
- Storage Account: `azurehaymaker${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- App Insights: `azurehaymaker-insights-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure OpenAI Service Documentation](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)
- [Azure OpenAI API Reference](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/reference)
- [Chat Completions API Guide](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/chatgpt?tabs=python)
- [Deploy Azure OpenAI Models](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource)
- [Azure OpenAI Quotas and Limits](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/quotas-limits)
- [Best Practices for Azure OpenAI](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/concepts/best-practices)

---

## Automation Tool
**Recommended**: Azure CLI with REST API

**Rationale**: Azure CLI handles infrastructure provisioning, while REST API calls via curl provide direct access to OpenAI chat completion and code generation APIs. This combination enables comprehensive testing and operational management.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8+ hours (with multiple model testing, prompt iterations, and monitoring)
- **Cleanup**: 5-10 minutes

---

## Notes
- Azure OpenAI Service requires prior registration and access approval
- Model deployments need to be created via Azure Portal, REST API, or ARM templates
- Chat Completions API supports system roles, user messages, and assistant responses
- Temperature parameter (0-2) controls response randomness and creativity
- Max tokens parameter limits response length
- All operations scoped to single tenant and subscription
- Credentials securely stored in Key Vault
- Prompts and responses logged to storage for audit and analysis
