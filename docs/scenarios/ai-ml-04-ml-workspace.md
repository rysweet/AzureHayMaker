# Scenario: Azure Machine Learning Workspace Setup

## Technology Area
AI & ML

## Company Profile
- **Company Size**: Enterprise
- **Industry**: Manufacturing / Predictive Analytics
- **Use Case**: Set up ML workspace for training predictive models, managing experiments, and automating model deployment pipelines

## Scenario Description
Create and configure Azure Machine Learning workspace with compute resources, storage, and managed identity. Set up ML experiments, register models, and establish CI/CD integration for automated model training and deployment.

## Azure Services Used
- Azure Machine Learning Service
- Azure Storage Account (for data and models)
- Azure Cosmos DB (for experiment metadata)
- Azure Container Registry (for model containers)
- Azure Key Vault (for credentials)
- Azure Application Insights (for monitoring)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI with ML extension installed (`az extension add -n ml`)
- Python SDK for ML (optional but recommended)
- Docker (optional for custom containers)

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-ml-${UNIQUE_ID}-rg"
LOCATION="eastus"
ML_WORKSPACE="azurehaymaker-ml-${UNIQUE_ID}"
STORAGE_ACCOUNT="azhmaklws${UNIQUE_ID}"
CONTAINER_REGISTRY="azhmaklcr${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
INSIGHTS_NAME="azurehaymaker-insights-${UNIQUE_ID}"
COMPUTE_CLUSTER="ml-cluster-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=ai-ml-workspace Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Storage Account for ML workspace
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 3: Create storage containers
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "training-data" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

az storage container create \
  --name "models" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

az storage container create \
  --name "outputs" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --public-access off

# Step 4: Create Container Registry for model images
az acr create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_REGISTRY}" \
  --sku Basic \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 5: Create Key Vault for credentials
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 6: Create Application Insights
az monitor app-insights component create \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --kind web \
  --tags ${TAGS}

# Step 7: Get Application Insights instrumentation key
INSIGHTS_KEY=$(az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "instrumentationKey" -o tsv)

# Step 8: Create Machine Learning Workspace
az ml workspace create \
  --file - <<EOF
{
  "name": "${ML_WORKSPACE}",
  "resource_group": "${RESOURCE_GROUP}",
  "location": "${LOCATION}",
  "display_name": "Azure HayMaker ML Workspace",
  "description": "ML workspace for model training and deployment",
  "storage_account": "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}",
  "key_vault": "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEYVAULT}",
  "container_registry": "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ContainerRegistry/registries/${CONTAINER_REGISTRY}",
  "application_insights": "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Insights/components/${INSIGHTS_NAME}",
  "tags": {
    "AzureHayMaker-managed": "true",
    "Scenario": "ai-ml-workspace"
  }
}
EOF

# Step 9: Create Compute Cluster for training
az ml compute create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --name "${COMPUTE_CLUSTER}" \
  --type "AmlCompute" \
  --min-instances 0 \
  --max-instances 4 \
  --size "Standard_DS2_v2" \
  --idle-time-before-scale-down 300

# Step 10: Create compute instance for development
az ml compute create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --name "dev-instance-${UNIQUE_ID}" \
  --type "ComputeInstance" \
  --size "Standard_D2s_v3"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Storage Account
az storage account show --name "${STORAGE_ACCOUNT}"

# Verify Container Registry
az acr show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CONTAINER_REGISTRY}"

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# Verify Application Insights
az monitor app-insights component show \
  --app "${INSIGHTS_NAME}" \
  --resource-group "${RESOURCE_GROUP}"

# Verify ML Workspace
az ml workspace show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${ML_WORKSPACE}"

# List compute resources
az ml compute list \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create and register training data
cat > /tmp/training-data.csv << EOF
feature1,feature2,feature3,label
1.5,2.3,3.1,0
2.1,3.2,4.5,1
1.2,2.0,3.5,0
3.1,4.2,5.1,1
EOF

STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name "training-data" \
  --name "training-data-${UNIQUE_ID}.csv" \
  --file /tmp/training-data.csv

# Operation 2: Create ML Dataset from storage
az ml data create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --file - <<EOF
{
  "name": "training-dataset-${UNIQUE_ID}",
  "description": "Training data for model",
  "path": "azureml://subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/datastores/workspaceblobstore/paths/training-data/training-data-${UNIQUE_ID}.csv",
  "type": "mltable"
}
EOF

# Operation 3: List registered datasets
az ml data list \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --output table

# Operation 4: Create experiment
az ml experiment create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --name "exp-model-training-${UNIQUE_ID}"

# Operation 5: Get workspace details and configuration
az ml workspace show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${ML_WORKSPACE}" \
  --query "{Name: name, Location: location, StorageAccount: storage_account, ContainerRegistry: container_registry}"

# Operation 6: Check compute cluster status
az ml compute show \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --name "${COMPUTE_CLUSTER}" \
  --query "{Name: name, Type: type, ProvisioningState: provisioning_state, RunningCount: current_node_count}"

# Operation 7: Monitor workspace metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.MachineLearningServices/workspaces/${ML_WORKSPACE}" \
  --metric "cpuUsagePercentage" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 8: List models in workspace
az ml model list \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --output table

# Operation 9: Create environment for training
az ml environment create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --file - <<EOF
{
  "name": "sklearn-env-${UNIQUE_ID}",
  "description": "Environment for scikit-learn training",
  "conda_file": {
    "name": "sklearn_env",
    "channels": ["conda-forge"],
    "dependencies": [
      "python=3.11",
      "pip",
      {
        "pip": [
          "scikit-learn==1.3.0",
          "pandas==2.0.0",
          "numpy==1.24.0"
        ]
      }
    ]
  }
}
EOF

# Operation 10: List environments
az ml environment list \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --output table

# Operation 11: Scale compute cluster
az ml compute update \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --name "${COMPUTE_CLUSTER}" \
  --min-instances 0 \
  --max-instances 8

# Operation 12: Get compute instance details
az ml compute show \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --name "dev-instance-${UNIQUE_ID}" \
  --query "{Name: name, Type: type, State: state, ComputeType: compute_type}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete all compute instances
az ml compute delete \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --name "${COMPUTE_CLUSTER}" \
  --yes

az ml compute delete \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${ML_WORKSPACE}" \
  --name "dev-instance-${UNIQUE_ID}" \
  --yes

# Step 2: Delete the entire resource group (includes all resources)
az group delete \
  --name "${RESOURCE_GROUP}" \
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
- Resource Group: `azurehaymaker-ml-${UNIQUE_ID}-rg`
- ML Workspace: `azurehaymaker-ml-${UNIQUE_ID}`
- Storage Account: `azhmaklws${UNIQUE_ID}`
- Container Registry: `azhmaklcr${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- App Insights: `azurehaymaker-insights-${UNIQUE_ID}`
- Compute Cluster: `ml-cluster-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Machine Learning Documentation](https://learn.microsoft.com/en-us/azure/machine-learning/)
- [Create ML Workspace](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-manage-workspace)
- [Azure ML Compute Resources](https://learn.microsoft.com/en-us/azure/machine-learning/concept-compute-target)
- [Training Jobs in Azure ML](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-train-cli)
- [Register and Deploy Models](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-and-where)
- [Azure ML CLI Reference](https://learn.microsoft.com/en-us/cli/azure/ml)

---

## Automation Tool
**Recommended**: Azure CLI with ML extension

**Rationale**: Azure CLI with the ML extension provides comprehensive workspace and compute management. It handles infrastructure provisioning, compute resource scaling, and experiment tracking in a unified command interface.

---

## Estimated Duration
- **Deployment**: 20-30 minutes
- **Operations Phase**: 8+ hours (with dataset creation, environment setup, compute scaling, and monitoring)
- **Cleanup**: 10-15 minutes

---

## Notes
- ML Workspace integrates storage, container registry, and Key Vault automatically
- Compute clusters auto-scale based on job demand and idle time settings
- Environments define reproducible training dependencies and Python packages
- Datasets are versioned and registered for experiment reproducibility
- All operations scoped to single tenant and subscription
- Experiments track training runs, metrics, and model artifacts
- Container Registry supports custom training and inference images
