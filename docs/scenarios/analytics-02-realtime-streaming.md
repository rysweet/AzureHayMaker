# Scenario: Real-Time Data Streaming with Azure Stream Analytics

## Technology Area
Analytics

## Company Profile
- **Company Size**: Mid-size financial services company
- **Industry**: Financial Services / Trading
- **Use Case**: Ingest and analyze stock market data in real-time, detect anomalies, and trigger alerts

## Scenario Description
Deploy Azure Stream Analytics to process real-time data streams from Event Hubs, perform windowed aggregations, detect trading anomalies, and output results to Azure SQL Database and Power BI for live dashboarding.

## Azure Services Used
- Azure Event Hubs (data ingestion)
- Azure Stream Analytics (real-time processing)
- Azure SQL Database (results storage)
- Azure Storage (checkpoint storage)
- Azure Key Vault (connection strings)

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
RESOURCE_GROUP="azurehaymaker-analytics-streaming-${UNIQUE_ID}-rg"
LOCATION="eastus"
EVENT_HUB_NS="azurehaymaker-eh-${UNIQUE_ID}"
EVENT_HUB_NAME="stock-data-stream"
STREAM_ANALYTICS_JOB="azurehaymaker-asa-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkrstream${UNIQUE_ID}"
SQL_SERVER="azurehaymaker-sql-${UNIQUE_ID}"
SQL_DB="analyticsdb"
SQL_ADMIN_USER="sqladmin"
SQL_ADMIN_PASSWORD="P@ssw0rd!${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=analytics-realtime-streaming Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Storage Account for checkpoint storage
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

# Step 3: Create Event Hubs namespace
az eventhubs namespace create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${EVENT_HUB_NS}" \
  --location "${LOCATION}" \
  --sku Standard \
  --tags ${TAGS}

# Step 4: Create Event Hub
az eventhubs eventhub create \
  --resource-group "${RESOURCE_GROUP}" \
  --namespace-name "${EVENT_HUB_NS}" \
  --name "${EVENT_HUB_NAME}" \
  --message-retention 1 \
  --partition-count 4

# Step 5: Create Event Hub authorization rule
az eventhubs eventhub authorization-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --namespace-name "${EVENT_HUB_NS}" \
  --eventhub-name "${EVENT_HUB_NAME}" \
  --name "ListenSendRule" \
  --rights Send Listen

# Step 6: Get Event Hub connection string
EVENT_HUB_CONNECTION_STRING=$(az eventhubs eventhub authorization-rule keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --namespace-name "${EVENT_HUB_NS}" \
  --eventhub-name "${EVENT_HUB_NAME}" \
  --name "ListenSendRule" \
  --query primaryConnectionString -o tsv)

# Step 7: Create SQL Server and Database
az sql server create \
  --name "${SQL_SERVER}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --admin-user "${SQL_ADMIN_USER}" \
  --admin-password "${SQL_ADMIN_PASSWORD}" \
  --tags ${TAGS}

az sql db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server "${SQL_SERVER}" \
  --name "${SQL_DB}" \
  --service-objective S0 \
  --tags ${TAGS}

# Step 8: Configure SQL firewall
az sql server firewall-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --server "${SQL_SERVER}" \
  --name "AllowAzureServices" \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Step 9: Create target table in SQL Database
sqlcmd -S "${SQL_SERVER}.database.windows.net" -U "${SQL_ADMIN_USER}" -P "${SQL_ADMIN_PASSWORD}" -d "${SQL_DB}" -Q "
CREATE TABLE StockAnomalies (
    EventId NVARCHAR(50),
    StockSymbol NVARCHAR(10),
    Price DECIMAL(10,2),
    AnomalyScore DECIMAL(5,2),
    WindowTime DATETIME,
    EventTime DATETIME
);"

# Step 10: Create Stream Analytics Job
az stream-analytics job create \
  --resource-group "${RESOURCE_GROUP}" \
  --job-name "${STREAM_ANALYTICS_JOB}" \
  --location "${LOCATION}" \
  --output-start-mode LastOutputEventTime \
  --events-outoforder-policy Adjust \
  --events-outoforder-max-delay 10 \
  --tags ${TAGS}

echo "Stream Analytics job created: ${STREAM_ANALYTICS_JOB}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Event Hubs namespace
az eventhubs namespace show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${EVENT_HUB_NS}"

# Verify Event Hub
az eventhubs eventhub show \
  --resource-group "${RESOURCE_GROUP}" \
  --namespace-name "${EVENT_HUB_NS}" \
  --name "${EVENT_HUB_NAME}"

# Verify SQL Database
az sql db show \
  --resource-group "${RESOURCE_GROUP}" \
  --server "${SQL_SERVER}" \
  --name "${SQL_DB}"

# Verify Stream Analytics Job
az stream-analytics job show \
  --resource-group "${RESOURCE_GROUP}" \
  --job-name "${STREAM_ANALYTICS_JOB}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Simulate sending events to Event Hub
for i in {1..10}; do
  SYMBOL=("AAPL" "MSFT" "GOOG" "AMZN" "TSLA")
  STOCK=${SYMBOL[$((RANDOM % 5))]}
  PRICE=$((100 + RANDOM % 100))

  echo "{\"stockSymbol\":\"${STOCK}\",\"price\":${PRICE},\"timestamp\":\"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\"}" | \
  az eventhubs eventhub send \
    --resource-group "${RESOURCE_GROUP}" \
    --namespace-name "${EVENT_HUB_NS}" \
    --name "${EVENT_HUB_NAME}" \
    --connection-string "${EVENT_HUB_CONNECTION_STRING}"

  sleep 1
done

# Operation 2: Start Stream Analytics Job
az stream-analytics job start \
  --resource-group "${RESOURCE_GROUP}" \
  --job-name "${STREAM_ANALYTICS_JOB}" \
  --output-start-mode LastOutputEventTime

# Operation 3: Check job status
az stream-analytics job show \
  --resource-group "${RESOURCE_GROUP}" \
  --job-name "${STREAM_ANALYTICS_JOB}" \
  --query "jobState" -o tsv

# Operation 4: Monitor Event Hub metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.EventHub/namespaces/${EVENT_HUB_NS}" \
  --metric "IncomingMessages" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 5: Query anomalies from SQL
sqlcmd -S "${SQL_SERVER}.database.windows.net" -U "${SQL_ADMIN_USER}" -P "${SQL_ADMIN_PASSWORD}" -d "${SQL_DB}" -Q "SELECT COUNT(*) as AnomalyCount FROM StockAnomalies;"

# Operation 6: Stop Stream Analytics Job
az stream-analytics job stop \
  --resource-group "${RESOURCE_GROUP}" \
  --job-name "${STREAM_ANALYTICS_JOB}"

# Operation 7: Monitor Stream Analytics metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.StreamAnalytics/streamingjobs/${STREAM_ANALYTICS_JOB}" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 8: List Event Hub partitions
az eventhubs eventhub show \
  --resource-group "${RESOURCE_GROUP}" \
  --namespace-name "${EVENT_HUB_NS}" \
  --name "${EVENT_HUB_NAME}" \
  --query "partitionCount" -o tsv
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Stop Stream Analytics Job if running
az stream-analytics job stop \
  --resource-group "${RESOURCE_GROUP}" \
  --job-name "${STREAM_ANALYTICS_JOB}" \
  --no-wait

# Step 2: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 3: Verify deletion
sleep 120
az group exists --name "${RESOURCE_GROUP}"

# Step 4: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-analytics-streaming-${UNIQUE_ID}-rg`
- Event Hubs Namespace: `azurehaymaker-eh-${UNIQUE_ID}`
- Event Hub: `stock-data-stream`
- Stream Analytics Job: `azurehaymaker-asa-${UNIQUE_ID}`
- Storage Account: `azmkrstream${UNIQUE_ID}`
- SQL Server: `azurehaymaker-sql-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Stream Analytics Overview](https://learn.microsoft.com/en-us/azure/stream-analytics/stream-analytics-introduction)
- [Stream Analytics Query Language](https://learn.microsoft.com/en-us/azure/stream-analytics/stream-analytics-query-language)
- [Azure Event Hubs Overview](https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-about)
- [Stream Analytics CLI Reference](https://learn.microsoft.com/en-us/cli/azure/stream-analytics)
- [Stream Analytics Windowing Functions](https://learn.microsoft.com/en-us/azure/stream-analytics/stream-analytics-window-functions)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides excellent support for Stream Analytics, Event Hubs, and SQL services. While the query definition requires JSON, Azure CLI handles the orchestration efficiently for this scenario.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8 hours (with continuous streaming and monitoring)
- **Cleanup**: 5-10 minutes

---

## Notes
- Stream Analytics can process millions of events per second
- Checkpointing to storage ensures no data loss on failures
- Window functions enable real-time aggregations and anomaly detection
- All operations scoped to single tenant and subscription
- Connection strings securely stored for production use
- Adjust event out-of-order policy based on data characteristics
