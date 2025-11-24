# Scenario: Azure Synapse Analytics Workspace for Big Data

## Technology Area
Analytics

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Retail / E-commerce
- **Use Case**: Unified analytics platform for data warehousing, big data analytics, and machine learning

## Scenario Description
Deploy Azure Synapse Analytics workspace with dedicated SQL pool, serverless SQL pool, and Spark pool for comprehensive data analytics. Process terabytes of data using either SQL or Spark, creating a unified analytics experience.

## Azure Services Used
- Azure Synapse Analytics (workspace)
- Dedicated SQL Pool (data warehouse)
- Serverless SQL Pool (on-demand querying)
- Apache Spark Pool (big data processing)
- Azure Storage Account (data lake)
- Azure Key Vault (secrets)

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
RESOURCE_GROUP="azurehaymaker-analytics-synapse-${UNIQUE_ID}-rg"
LOCATION="eastus"
SYNAPSE_WORKSPACE="azurehaymaker-synapse-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkrsynapse${UNIQUE_ID}"
SQL_POOL_NAME="sqldwpool"
SPARK_POOL_NAME="sparkpool"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
SQL_ADMIN_USER="sqladmin"
SQL_ADMIN_PASSWORD="P@ssw0rd!${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=analytics-synapse-analytics Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Storage Account with hierarchical namespace
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true \
  --tags ${TAGS}

# Step 3: Create file system for Synapse
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage fs create \
  --name "synapse" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

az storage fs create \
  --name "data" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

# Step 4: Create sample data
mkdir -p /tmp/synapse-data
cat > /tmp/synapse-data/sales.csv <<EOF
product_id,date,quantity,revenue,region
P001,2024-01-15,100,5000.00,North
P002,2024-01-15,50,2500.00,South
P001,2024-01-16,120,6000.00,East
P003,2024-01-16,75,3750.00,West
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "data" \
  --name "sales.csv" \
  --file /tmp/synapse-data/sales.csv

# Step 5: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "sql-admin-password" \
  --value "${SQL_ADMIN_PASSWORD}"

# Step 6: Create Synapse Workspace
az synapse workspace create \
  --name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --storage-account "${STORAGE_ACCOUNT}" \
  --file-system "synapse" \
  --sql-admin-login-user "${SQL_ADMIN_USER}" \
  --sql-admin-login-password "${SQL_ADMIN_PASSWORD}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 7: Create Dedicated SQL Pool
az synapse sql pool create \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_POOL_NAME}" \
  --performance-level DW100c

# Step 8: Create Spark Pool
az synapse spark pool create \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SPARK_POOL_NAME}" \
  --spark-version 3.1 \
  --node-count 3 \
  --node-size Small \
  --enable-auto-scale false

# Step 9: Configure workspace firewall
az synapse workspace firewall-rule create \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "AllowAllAzureIps" \
  --start-ip-address "0.0.0.0" \
  --end-ip-address "0.0.0.0"

# Step 10: Enable managed identity
az synapse workspace update \
  --name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --assign-identity

echo ""
echo "=========================================="
echo "Synapse Workspace Created: ${SYNAPSE_WORKSPACE}"
echo "SQL Pool: ${SQL_POOL_NAME}"
echo "Spark Pool: ${SPARK_POOL_NAME}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Synapse Workspace
az synapse workspace show \
  --name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}"

# List SQL pools
az synapse sql pool list \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}"

# List Spark pools
az synapse spark pool list \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}"

# Check workspace status
az synapse workspace show \
  --name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "connectivityEndpoints" -o table

# Verify storage
az storage fs show \
  --name "data" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Pause Dedicated SQL Pool to save costs
az synapse sql pool pause \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_POOL_NAME}"

# Operation 2: Resume Dedicated SQL Pool
az synapse sql pool resume \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_POOL_NAME}"

# Operation 3: Scale SQL Pool
az synapse sql pool update \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_POOL_NAME}" \
  --performance-level DW200c

# Operation 4: Check Spark pool status
az synapse spark pool show \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SPARK_POOL_NAME}" \
  --query "nodeCount" -o tsv

# Operation 5: Monitor SQL Pool metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Synapse/workspaces/${SYNAPSE_WORKSPACE}/sqlPools/${SQL_POOL_NAME}" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 6: Upload additional data
cat > /tmp/synapse-data/inventory.csv <<EOF
product_id,warehouse_id,quantity_on_hand,reorder_level
P001,W1,500,100
P002,W2,300,75
P003,W1,200,50
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "data" \
  --name "inventory.csv" \
  --file /tmp/synapse-data/inventory.csv \
  --overwrite

# Operation 7: List data files
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "data" \
  --output table

# Operation 8: Monitor workspace activity
az synapse workspace show \
  --name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "connectivity" -o table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Pause SQL pool before deletion
az synapse sql pool pause \
  --workspace-name "${SYNAPSE_WORKSPACE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_POOL_NAME}" \
  --no-wait

# Step 2: Wait for pause to complete
sleep 60

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
rm -rf /tmp/synapse-data
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-analytics-synapse-${UNIQUE_ID}-rg`
- Synapse Workspace: `azurehaymaker-synapse-${UNIQUE_ID}`
- Storage Account: `azmkrsynapse${UNIQUE_ID}`
- SQL Pool: `sqldwpool`
- Spark Pool: `sparkpool`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Synapse Analytics Overview](https://learn.microsoft.com/en-us/azure/synapse-analytics/overview-what-is)
- [Synapse Workspace Guide](https://learn.microsoft.com/en-us/azure/synapse-analytics/quickstart-create-workspace)
- [Dedicated SQL Pool](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql-data-warehouse/overview)
- [Apache Spark in Synapse](https://learn.microsoft.com/en-us/azure/synapse-analytics/spark/apache-spark-overview)
- [Synapse CLI Reference](https://learn.microsoft.com/en-us/cli/azure/synapse)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides straightforward commands for all Synapse components. While Terraform and Bicep are viable, Azure CLI is most efficient for rapid deployment and management.

---

## Estimated Duration
- **Deployment**: 20-30 minutes (SQL and Spark pools take time to provision)
- **Operations Phase**: 8 hours (with scaling, monitoring, and data uploads)
- **Cleanup**: 10-15 minutes

---

## Notes
- Dedicated SQL Pool can be paused to save costs when not in use
- Spark pools provide distributed computing for big data
- Serverless SQL pool queries data directly from storage without provisioned resources
- Managed identity enables secure access to storage and Key Vault
- All operations scoped to single tenant and subscription
- Data lake storage provides scalable, performant data storage
