# Scenario: Azure Cosmos DB with SQL API

## Technology Area
Databases

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Retail / E-commerce
- **Use Case**: Global-scale NoSQL database for customer profiles and product catalogs

## Scenario Description
Deploy Azure Cosmos DB with SQL API for globally distributed, low-latency access to document data. Configure containers, implement partitioning strategy, set up throughput scaling, and demonstrate backup capabilities.

## Azure Services Used
- Azure Cosmos DB (multi-model database)
- Azure Key Vault (connection strings)
- Azure Monitor (logging and monitoring)
- Azure Backup (disaster recovery)

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
RESOURCE_GROUP="azurehaymaker-db-cosmos-${UNIQUE_ID}-rg"
LOCATION="eastus"
COSMOS_ACCOUNT="azurehaymaker-cosmos-${UNIQUE_ID}"
COSMOS_DB="retaildb"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
LOG_ANALYTICS="azurehaymaker-logs-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=databases-cosmos-db Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 3: Create Log Analytics Workspace
az monitor log-analytics workspace create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 4: Create Cosmos DB Account
az cosmosdb create \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --locations regionName="${LOCATION}" failoverPriority=0 \
  --default-consistency-level "Session" \
  --enable-multiple-write-locations true \
  --capabilities EnableServerless \
  --tags ${TAGS}

# Step 5: Create database
az cosmosdb sql database create \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${COSMOS_DB}" \
  --throughput 400

# Step 6: Create containers with partition keys
az cosmosdb sql container create \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Customers" \
  --partition-key-path "/customerId" \
  --throughput 400

az cosmosdb sql container create \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Products" \
  --partition-key-path "/categoryId" \
  --throughput 400

az cosmosdb sql container create \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Orders" \
  --partition-key-path "/customerId" \
  --throughput 400

# Step 7: Enable automatic failover
az cosmosdb failover-priority-change \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --failover-policies regionName="${LOCATION}" failoverPriority=0

# Step 8: Get connection string
COSMOS_CONNECTION_STRING=$(az cosmosdb keys list \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --type "connection-strings" \
  --query "connectionStrings[0].connectionString" -o tsv)

# Store in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "cosmos-connection-string" \
  --value "${COSMOS_CONNECTION_STRING}"

# Step 9: Enable backup retention
az cosmosdb update \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --backup-policy-type Periodic \
  --backup-interval 240 \
  --backup-retention 720

# Step 10: Create diagnostic settings for monitoring
az monitor diagnostic-settings create \
  --name "cosmos-diagnostics" \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.DocumentDB/databaseAccounts/${COSMOS_ACCOUNT}" \
  --workspace "${LOG_ANALYTICS}" \
  --logs '[{"category":"DataPlaneRequests","enabled":true}]' \
  --metrics '[{"category":"Requests","enabled":true}]'

echo ""
echo "=========================================="
echo "Cosmos DB Account Created: ${COSMOS_ACCOUNT}"
echo "Database: ${COSMOS_DB}"
echo "Containers: Customers, Products, Orders"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Cosmos DB Account
az cosmosdb show \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}"

# Check account status
az cosmosdb show \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "provisioningState" -o tsv

# List databases
az cosmosdb sql database list \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# List containers
az cosmosdb sql container list \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --output table

# Get container details
az cosmosdb sql container show \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Customers"

# Check throughput settings
az cosmosdb sql container throughput show \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Customers"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Scale throughput for Customers container
az cosmosdb sql container throughput update \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Customers" \
  --throughput 800

# Operation 2: Add sample documents
# Create sample customer data
cat > /tmp/customer_sample.json <<EOF
{
  "customerId": "CUST001",
  "name": "John Doe",
  "email": "john@example.com",
  "tier": "premium",
  "registeredDate": "2024-01-01"
}
EOF

# Operation 3: View container metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.DocumentDB/databaseAccounts/${COSMOS_ACCOUNT}" \
  --metric "TotalRequests" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 4: List backup information
az cosmosdb backup show \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}"

# Operation 5: Create point-in-time restore (for testing)
echo "To create a point-in-time restore:"
echo "az cosmosdb restore --account-name ${COSMOS_ACCOUNT} --resource-group ${RESOURCE_GROUP} --restore-timestamp $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

# Operation 6: Enable analytical store on Products container
az cosmosdb sql container update \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Products" \
  --analytical-storage-ttl 86400

# Operation 7: Monitor request usage
az cosmosdb sql database show \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${COSMOS_DB}" \
  --query "properties.throughput" -o tsv

# Operation 8: Create index policy for Customers
cat > /tmp/index_policy.json <<EOF
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {
      "path": "/*"
    }
  ],
  "excludedPaths": [
    {
      "path": "/sensitive/*"
    }
  ]
}
EOF

# Operation 9: Check connection limits
az cosmosdb account show \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "virtualNetworkRules" -o table

# Operation 10: List all containers with TTL settings
az cosmosdb sql container list \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --query "[].{Name:name, PartitionKey:partitionKey.paths[0]}" -o table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete containers
az cosmosdb sql container delete \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Customers" \
  --yes

az cosmosdb sql container delete \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Products" \
  --yes

az cosmosdb sql container delete \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DB}" \
  --name "Orders" \
  --yes

# Step 2: Delete database
az cosmosdb sql database delete \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${COSMOS_DB}" \
  --yes

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
rm -rf /tmp/customer_sample.json /tmp/index_policy.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-db-cosmos-${UNIQUE_ID}-rg`
- Cosmos DB Account: `azurehaymaker-cosmos-${UNIQUE_ID}`
- Database: `retaildb`
- Containers: `Customers`, `Products`, `Orders`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Cosmos DB Overview](https://learn.microsoft.com/en-us/azure/cosmos-db/introduction)
- [SQL API for Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/sql/)
- [Partitioning in Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/partitioning-overview)
- [Throughput and RU/s](https://learn.microsoft.com/en-us/azure/cosmos-db/request-units)
- [Cosmos DB CLI Reference](https://learn.microsoft.com/en-us/cli/azure/cosmosdb)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides excellent support for Cosmos DB operations including database, container, and throughput management. Simple and declarative for this scenario.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8 hours (with scaling and monitoring)
- **Cleanup**: 10-15 minutes

---

## Notes
- Serverless billing option available for unpredictable workloads
- Multiple write regions provide high availability
- Session consistency balances consistency and performance
- Automatic failover ensures business continuity
- All operations scoped to single tenant and subscription
- Point-in-time restore enables disaster recovery
- TTL on documents enables automatic data cleanup
