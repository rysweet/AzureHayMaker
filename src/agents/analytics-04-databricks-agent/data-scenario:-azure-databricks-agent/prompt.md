# Scenario: Azure Databricks Cluster for Machine Learning

## Technology Area
Analytics

## Company Profile
- **Company Size**: Large technology company
- **Industry**: Technology / SaaS
- **Use Case**: Build and train machine learning models using Apache Spark with collaborative notebooks

## Scenario Description
Deploy Azure Databricks with an Apache Spark cluster for collaborative data science work. Create notebooks, process large datasets using Spark, and prepare data for machine learning model training.

## Azure Services Used
- Azure Databricks
- Azure Storage Account (data lake)
- Azure Key Vault (credentials)
- Azure Virtual Network (network isolation)

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
RESOURCE_GROUP="azurehaymaker-analytics-databricks-${UNIQUE_ID}-rg"
LOCATION="eastus"
DATABRICKS_WORKSPACE="azurehaymaker-dbk-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkrdbk${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=analytics-databricks Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Virtual Network for Databricks
az network vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --address-prefix "10.0.0.0/16" \
  --subnet-name "default" \
  --subnet-prefixes "10.0.0.0/24" \
  --tags ${TAGS}

# Step 3: Get VNet and subnet IDs
VNET_ID=$(az network vnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --query id -o tsv)

SUBNET_ID=$(az network vnet subnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "default" \
  --query id -o tsv)

# Step 4: Create Storage Account for data
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true \
  --tags ${TAGS}

# Step 5: Create containers
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "datasets" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

az storage container create \
  --name "models" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

# Step 6: Upload sample dataset
cat > /tmp/sample_data.csv <<EOF
feature1,feature2,feature3,label
1.5,2.3,0.5,1
2.1,3.4,1.2,0
1.8,2.9,0.8,1
3.2,4.1,2.1,1
0.9,1.5,0.3,0
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "datasets" \
  --name "sample_data.csv" \
  --file /tmp/sample_data.csv

# Step 7: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "storage-key" \
  --value "${STORAGE_KEY}"

# Step 8: Create Databricks Workspace
az databricks workspace create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${DATABRICKS_WORKSPACE}" \
  --location "${LOCATION}" \
  --sku premium \
  --tags ${TAGS}

# Step 9: Create Databricks cluster configuration file
cat > /tmp/cluster_config.json <<EOF
{
  "spark_version": "13.3.x-scala2.12",
  "node_type_id": "Standard_DS3_v2",
  "num_workers": 2,
  "spark_conf": {
    "spark.databricks.cluster.profile": "singleNode"
  },
  "cluster_name": "ml-cluster",
  "autotermination_minutes": 30
}
EOF

# Step 10: Get workspace URL for cluster creation context
WORKSPACE_URL=$(az databricks workspace show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${DATABRICKS_WORKSPACE}" \
  --query "workspaceUrl" -o tsv)

echo ""
echo "=========================================="
echo "Databricks Workspace Created: ${DATABRICKS_WORKSPACE}"
echo "Workspace URL: ${WORKSPACE_URL}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Databricks Workspace
az databricks workspace show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${DATABRICKS_WORKSPACE}"

# Verify Storage Account
az storage account show \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}"

# List storage containers
az storage container list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --output table

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# Verify Virtual Network
az network vnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: List Databricks workspaces
az databricks workspace list --resource-group "${RESOURCE_GROUP}"

# Operation 2: Monitor workspace resource usage
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Databricks/workspaces/${DATABRICKS_WORKSPACE}" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 3: Upload additional datasets
cat > /tmp/training_data.csv <<EOF
feature1,feature2,feature3,feature4,label
1.2,2.5,0.7,1.5,1
2.3,3.6,1.4,2.1,0
1.5,2.8,0.9,1.8,1
3.4,4.5,2.3,2.8,1
0.8,1.3,0.2,0.9,0
1.9,3.1,1.0,2.0,1
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "datasets" \
  --name "training_data.csv" \
  --file /tmp/training_data.csv \
  --overwrite

# Operation 4: List all datasets
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "datasets" \
  --output table

# Operation 5: Check storage usage
az storage account show-usage \
  --location "${LOCATION}"

# Operation 6: View Key Vault secrets
az keyvault secret list --vault-name "${KEYVAULT}" --output table

# Operation 7: Create a notebook in Databricks context
echo "To create notebooks, use Databricks UI at: ${WORKSPACE_URL}"
echo "Or use Databricks API with workspace token"

# Operation 8: List VNet and subnets
az network vnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete Databricks Workspace
az databricks workspace delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${DATABRICKS_WORKSPACE}" \
  --yes

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

# Step 5: Clean up local files
rm -rf /tmp/sample_data.csv /tmp/training_data.csv /tmp/cluster_config.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-analytics-databricks-${UNIQUE_ID}-rg`
- Databricks Workspace: `azurehaymaker-dbk-${UNIQUE_ID}`
- Storage Account: `azmkrdbk${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Databricks Overview](https://learn.microsoft.com/en-us/azure/databricks/introduction/)
- [Create Databricks Workspace](https://learn.microsoft.com/en-us/azure/databricks/workspace/)
- [Apache Spark in Databricks](https://learn.microsoft.com/en-us/azure/databricks/spark/)
- [Databricks Clusters](https://learn.microsoft.com/en-us/azure/databricks/clusters/)
- [Databricks CLI Reference](https://learn.microsoft.com/en-us/cli/azure/databricks)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI handles Databricks workspace creation efficiently. Advanced cluster and notebook management is typically done via Databricks UI or API after workspace provisioning.

---

## Estimated Duration
- **Deployment**: 20-25 minutes (Databricks workspace provisioning takes time)
- **Operations Phase**: 8 hours (with data uploads and cluster management)
- **Cleanup**: 5-10 minutes

---

## Notes
- Premium SKU provides features like job scheduling and DBFS
- Spark clusters are created and managed within the Databricks workspace
- All compute resources are ephemeral and created on-demand
- Data stored in Azure Storage with direct Databricks integration
- All operations scoped to single tenant and subscription
- Notebooks support Python, SQL, Scala, and R languages
