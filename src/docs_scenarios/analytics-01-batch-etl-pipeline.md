# Scenario: Scheduled Batch ETL Pipeline

## Technology Area
Analytics

## Company Profile
- **Company Size**: Mid-size retail company
- **Industry**: Retail / E-commerce
- **Use Case**: Daily sales data processing from multiple stores into a central data warehouse for business intelligence reporting

## Scenario Description
Extract daily sales data from cloud storage (CSV files uploaded by each store), transform the data to clean and aggregate it, and load it into Azure SQL Database for Power BI dashboards. The pipeline runs automatically on a daily schedule.

## Azure Services Used
- Azure Storage Account (Data Lake Gen2)
- Azure Data Factory
- Azure SQL Database
- Azure Key Vault (for connection strings)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed (`az --version`)
- A unique identifier for this scenario run (e.g., timestamp or GUID)

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-analytics-etl-${UNIQUE_ID}-rg"
LOCATION="eastus"
STORAGE_ACCOUNT="azmkretl${UNIQUE_ID}"
SQL_SERVER="azurehaymaker-sql-${UNIQUE_ID}"
SQL_DB="saleswarehouse"
DATA_FACTORY="azurehaymaker-adf-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
SQL_ADMIN_USER="sqladmin"
SQL_ADMIN_PASSWORD="P@ssw0rd!${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=analytics-batch-etl Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Storage Account with Data Lake Gen2
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true \
  --tags ${TAGS}

# Step 3: Create containers for raw and processed data
STORAGE_KEY=$(az storage account keys list --resource-group "${RESOURCE_GROUP}" --account-name "${STORAGE_ACCOUNT}" --query '[0].value' -o tsv)

az storage container create \
  --name "raw-sales-data" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

az storage container create \
  --name "processed-sales-data" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

# Step 4: Upload sample data file
cat > /tmp/sales_sample.csv <<EOF
store_id,date,product_id,quantity,revenue
001,2024-01-15,P1001,5,125.50
001,2024-01-15,P1002,3,89.99
002,2024-01-15,P1001,8,200.00
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "raw-sales-data" \
  --name "sales_2024-01-15.csv" \
  --file /tmp/sales_sample.csv

# Step 5: Create Azure SQL Database
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

# Step 6: Configure firewall to allow Azure services
az sql server firewall-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --server "${SQL_SERVER}" \
  --name "AllowAzureServices" \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Step 7: Create target table in SQL Database
SQL_CONNECTION_STRING="Server=tcp:${SQL_SERVER}.database.windows.net,1433;Database=${SQL_DB};User ID=${SQL_ADMIN_USER};Password=${SQL_ADMIN_PASSWORD};Encrypt=true;Connection Timeout=30;"

sqlcmd -S "${SQL_SERVER}.database.windows.net" -U "${SQL_ADMIN_USER}" -P "${SQL_ADMIN_PASSWORD}" -d "${SQL_DB}" -Q "
CREATE TABLE SalesFacts (
    store_id VARCHAR(10),
    sale_date DATE,
    product_id VARCHAR(20),
    quantity INT,
    revenue DECIMAL(10,2),
    load_timestamp DATETIME DEFAULT GETDATE()
);"

# Step 8: Create Key Vault for secrets
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "sql-connection-string" \
  --value "${SQL_CONNECTION_STRING}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "storage-account-key" \
  --value "${STORAGE_KEY}"

# Step 9: Create Azure Data Factory
az datafactory create \
  --resource-group "${RESOURCE_GROUP}" \
  --factory-name "${DATA_FACTORY}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 10: Create Data Factory linked services and pipeline
# Note: This requires JSON files for pipeline definition
# For simplicity, we'll create a basic copy activity via Azure CLI

echo "Data Factory created. Pipeline definition would go here."
echo "In a full implementation, you would define:"
echo "  - Linked service for Storage Account"
echo "  - Linked service for SQL Database"
echo "  - Dataset for source CSV files"
echo "  - Dataset for destination SQL table"
echo "  - Pipeline with Copy Activity"
echo "  - Schedule trigger for daily execution"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Storage Account
az storage account show --name "${STORAGE_ACCOUNT}"

# Verify SQL Server and Database
az sql db show --resource-group "${RESOURCE_GROUP}" --server "${SQL_SERVER}" --name "${SQL_DB}"

# Verify Data Factory
az datafactory show --resource-group "${RESOURCE_GROUP}" --factory-name "${DATA_FACTORY}"

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# List all resources in resource group
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Upload new sales data file
NEW_DATE=$(date +%Y-%m-%d)
cat > /tmp/sales_${NEW_DATE}.csv <<EOF
store_id,date,product_id,quantity,revenue
001,${NEW_DATE},P1001,12,300.00
002,${NEW_DATE},P1003,7,175.99
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "raw-sales-data" \
  --name "sales_${NEW_DATE}.csv" \
  --file /tmp/sales_${NEW_DATE}.csv \
  --overwrite

# Operation 2: Manually trigger pipeline run (simulating scheduled execution)
echo "In production, Data Factory pipeline would automatically trigger on schedule"
echo "Manual trigger command would be:"
echo "az datafactory pipeline create-run --resource-group \"${RESOURCE_GROUP}\" --factory-name \"${DATA_FACTORY}\" --name \"CopySalesToSQL\""

# Operation 3: Check pipeline run status
echo "Check pipeline runs:"
echo "az datafactory pipeline-run query-by-factory --resource-group \"${RESOURCE_GROUP}\" --factory-name \"${DATA_FACTORY}\""

# Operation 4: Monitor storage account metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}" \
  --metric "Transactions" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ') \
  --interval PT1H

# Operation 5: Monitor SQL Database DTU usage
az sql db show \
  --resource-group "${RESOURCE_GROUP}" \
  --server "${SQL_SERVER}" \
  --name "${SQL_DB}" \
  --query "currentServiceObjectiveName"

# Operation 6: Query data warehouse for record count
sqlcmd -S "${SQL_SERVER}.database.windows.net" -U "${SQL_ADMIN_USER}" -P "${SQL_ADMIN_PASSWORD}" -d "${SQL_DB}" -Q "SELECT COUNT(*) as RecordCount FROM SalesFacts;"

# Operation 7: List recent blob uploads
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "raw-sales-data" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group (deletes all contained resources)
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 2: Verify deletion (wait a few minutes for async deletion to complete)
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 3: Verify no orphaned resources
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-analytics-etl-${UNIQUE_ID}-rg`
- Storage Account: `azmkretl${UNIQUE_ID}`
- SQL Server: `azurehaymaker-sql-${UNIQUE_ID}`
- Data Factory: `azurehaymaker-adf-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Data Factory Quickstart](https://learn.microsoft.com/en-us/azure/data-factory/quickstart-create-data-factory)
- [Copy Activity in Azure Data Factory](https://learn.microsoft.com/en-us/azure/data-factory/copy-activity-overview)
- [Azure SQL Database Overview](https://learn.microsoft.com/en-us/azure/azure-sql/database/sql-database-paas-overview)
- [Azure Storage Account with Data Lake Gen2](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-introduction)
- [Azure Data Factory CLI Reference](https://learn.microsoft.com/en-us/cli/azure/datafactory)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides straightforward commands for all services in this scenario. While Terraform could be used for infrastructure, the Data Factory pipeline definitions are easier to manage with Azure CLI or ARM templates. For this scenario's complexity level, Azure CLI offers the best balance of simplicity and functionality.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8 hours (with periodic data uploads and monitoring)
- **Cleanup**: 5-10 minutes

---

## Notes
- This scenario uses Azure SQL Database Basic/Standard tier to keep costs low
- Data Factory pipeline definition is simplified - full implementation would include:
  - Complete pipeline JSON with Copy Activity
  - Schedule trigger configuration
  - Error handling and retry logic
- All operations scoped to single tenant and subscription
- Connection strings stored in Key Vault following security best practices
- Sample data files are minimal for testing purposes
