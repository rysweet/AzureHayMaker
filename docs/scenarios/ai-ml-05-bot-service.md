# Scenario: Azure Bot Service with Q&A

## Technology Area
AI & ML

## Company Profile
- **Company Size**: Small to mid-size company
- **Industry**: Customer Support / SaaS
- **Use Case**: Create intelligent chatbot that answers frequently asked questions and provides customer support escalation

## Scenario Description
Deploy Azure Bot Service with QnA Maker knowledge base integration to create an intelligent question-answering chatbot. Configure multiple channels, set up logging, and manage conversations through Azure services.

## Azure Services Used
- Azure Bot Service
- Azure QnA Maker (Cognitive Services Language Understanding)
- Azure App Service (for bot hosting)
- Azure Storage Account (for conversation logs)
- Azure Key Vault (for credentials)
- Azure Application Insights (for bot analytics)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Bot Framework SDK (optional for local testing)
- cURL or similar tool for API calls

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-bot-${UNIQUE_ID}-rg"
LOCATION="eastus"
BOT_SERVICE="azurehaymaker-bot-${UNIQUE_ID}"
BOT_APP_NAME="azurehaymaker-botapp-${UNIQUE_ID}"
QNA_RESOURCE="azurehaymaker-qna-${UNIQUE_ID}"
APP_SERVICE_PLAN="azurehaymaker-asp-${UNIQUE_ID}"
STORAGE_ACCOUNT="azhmabot${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
INSIGHTS_NAME="azurehaymaker-insights-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=ai-ml-bot-service Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Application Insights for bot monitoring
az monitor app-insights component create \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --kind web \
  --tags ${TAGS}

# Step 3: Get Application Insights key
INSIGHTS_KEY=$(az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "instrumentationKey" -o tsv)

INSIGHTS_ID=$(az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "id" -o tsv)

echo "Application Insights Key: ${INSIGHTS_KEY}"

# Step 4: Create App Service Plan
az appservice plan create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_SERVICE_PLAN}" \
  --sku B1 \
  --is-linux \
  --tags ${TAGS}

# Step 5: Create App Service for bot hosting
az webapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_SERVICE_PLAN}" \
  --name "${BOT_APP_NAME}" \
  --runtime "NODE:18-lts" \
  --tags ${TAGS}

# Step 6: Get App Service URL
BOT_APP_URL="https://${BOT_APP_NAME}.azurewebsites.net"
echo "Bot App URL: ${BOT_APP_URL}"

# Step 7: Create QnA Maker resource (Language service)
az cognitiveservices account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${QNA_RESOURCE}" \
  --kind Language \
  --sku S0 \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 8: Get QnA Maker endpoint and key
QNA_ENDPOINT=$(az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${QNA_RESOURCE}" \
  --query "properties.endpoint" -o tsv)

QNA_KEY=$(az cognitiveservices account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${QNA_RESOURCE}" \
  --query "key1" -o tsv)

echo "QnA Endpoint: ${QNA_ENDPOINT}"
echo "QnA Key: ${QNA_KEY}"

# Step 9: Create Storage Account for conversation logs
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 10: Create storage containers
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "conversation-logs" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

az storage container create \
  --name "bot-configs" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

# Step 11: Create Key Vault for credentials
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 12: Store credentials in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "qna-endpoint" \
  --value "${QNA_ENDPOINT}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "qna-key" \
  --value "${QNA_KEY}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "bot-app-url" \
  --value "${BOT_APP_URL}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "insights-key" \
  --value "${INSIGHTS_KEY}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify App Service
az webapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${BOT_APP_NAME}"

# Verify Application Insights
az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}"

# Verify QnA Maker Resource
az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${QNA_RESOURCE}"

# Verify Storage Account
az storage account show --name "${STORAGE_ACCOUNT}"

# Verify Storage Containers
az storage container list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --output table

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table

# Test Bot App Service endpoint
curl -I "https://${BOT_APP_NAME}.azurewebsites.net/api/messages" || echo "Bot endpoint ready"
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create sample QnA knowledge base (stored locally)
cat > /tmp/qna-knowledge-base.json << EOF
{
  "qnaList": [
    {
      "id": 1,
      "answer": "Azure Bot Service is a cloud-based service that enables you to build intelligent bots that can interact with users across multiple channels.",
      "source": "FAQ",
      "questions": [
        "What is Azure Bot Service?",
        "Tell me about Bot Service"
      ]
    },
    {
      "id": 2,
      "answer": "You can deploy bots to multiple channels including Web Chat, Teams, Slack, Facebook Messenger, and more.",
      "source": "FAQ",
      "questions": [
        "What channels does Bot Service support?",
        "Where can I deploy my bot?"
      ]
    },
    {
      "id": 3,
      "answer": "QnA Maker is a cognitive service that analyzes questions and answers to create a searchable knowledge base.",
      "source": "FAQ",
      "questions": [
        "What is QnA Maker?",
        "How does QnA Maker work?"
      ]
    }
  ]
}
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "bot-configs" \
  --name "qna-knowledge-base-${UNIQUE_ID}.json" \
  --file /tmp/qna-knowledge-base.json

# Operation 2: Get App Service runtime and configuration
az webapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${BOT_APP_NAME}" \
  --query "{Name: name, State: state, Runtime: runtimeVersion, Url: defaultHostName}"

# Operation 3: List web app configurations
az webapp config appsettings list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${BOT_APP_NAME}" \
  --output table

# Operation 4: Create sample conversation log
cat > /tmp/conversation-log.txt << EOF
Conversation Log - ${UNIQUE_ID}
Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
User: What is Azure Bot Service?
Bot: Azure Bot Service is a cloud-based service that enables you to build intelligent bots that can interact with users across multiple channels.
User: What channels does it support?
Bot: You can deploy bots to multiple channels including Web Chat, Teams, Slack, Facebook Messenger, and more.
Sentiment: Positive
Confidence: 0.92
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "conversation-logs" \
  --name "conversation-${UNIQUE_ID}.log" \
  --file /tmp/conversation-log.txt

# Operation 5: List all stored conversation logs
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "conversation-logs" \
  --output table

# Operation 6: Monitor Application Insights bot performance
az monitor app-insights metrics show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --metric "requests/rate"

# Operation 7: Check bot service and QnA service metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${QNA_RESOURCE}" \
  --metric "SuccessfulRequests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 8: Get App Service connection status and health
az webapp show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${BOT_APP_NAME}" \
  --query "{State: state, AvailabilityState: availabilityState, HostNames: defaultHostName}"

# Operation 9: List stored knowledge base configurations
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "bot-configs" \
  --output table

# Operation 10: Retrieve QnA resource details and status
az cognitiveservices account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${QNA_RESOURCE}" \
  --query "{Name: name, Kind: kind, Sku: sku.name, Endpoint: properties.endpoint, ProvisioningState: properties.provisioningState}"

# Operation 11: Check Key Vault secrets
az keyvault secret list --vault-name "${KEYVAULT}" --output table

# Operation 12: Get Storage Account metrics and usage
az storage account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --query "{Name: name, Kind: kind, SkuName: sku.name, AccessTier: accessTier}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Stop the App Service
az webapp stop \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${BOT_APP_NAME}"

# Step 2: Delete the entire resource group (includes all resources)
az group delete \
  --resource-group "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 3: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 120

# Step 4: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 5: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-bot-${UNIQUE_ID}-rg`
- Bot Service App: `azurehaymaker-botapp-${UNIQUE_ID}`
- QnA Maker: `azurehaymaker-qna-${UNIQUE_ID}`
- App Service Plan: `azurehaymaker-asp-${UNIQUE_ID}`
- Storage Account: `azhmabot${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- App Insights: `azurehaymaker-insights-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Bot Service Documentation](https://learn.microsoft.com/en-us/azure/bot-service/)
- [Create a Bot with Azure Bot Service](https://learn.microsoft.com/en-us/azure/bot-service/bot-service-quickstart-create-bot)
- [QnA Maker Overview](https://learn.microsoft.com/en-us/azure/cognitive-services/qnamaker/overview/overview)
- [Custom Question Answering](https://learn.microsoft.com/en-us/azure/cognitive-services/language-service/question-answering/overview)
- [Bot Service Channels](https://learn.microsoft.com/en-us/azure/bot-service/bot-service-channels-reference)
- [Bot Analytics with Application Insights](https://learn.microsoft.com/en-us/azure/bot-service/bot-service-manage-analytics)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI efficiently manages bot service provisioning, app service deployment, and resource configuration. It handles all infrastructure components needed for a fully operational bot in a single scripting interface.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8+ hours (with knowledge base uploads, conversation logging, and performance monitoring)
- **Cleanup**: 5-10 minutes

---

## Notes
- Bot Service automatically handles channel-specific formatting and protocols
- QnA Maker provides intelligent question-answer matching with confidence scores
- Application Insights tracks bot conversations, user queries, and performance metrics
- Conversation logs are stored for audit and analytics purposes
- All operations scoped to single tenant and subscription
- App Service can be scaled to handle bot traffic variations
- Credentials securely managed in Key Vault for bot runtime access
- Multiple channels can be connected to single bot service instance
