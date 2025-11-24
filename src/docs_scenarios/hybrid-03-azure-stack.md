# Scenario: Azure Stack HCI Setup and Management

## Technology Area
Hybrid+Multicloud

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Manufacturing
- **Use Case**: Run Azure services on-premises with Azure Stack HCI

## Scenario Description
Deploy and configure Azure Stack HCI for running VMs and containers on-premises while maintaining consistency with Azure. Set up cluster, configure storage, and enable hybrid management.

## Azure Services Used
- Azure Stack HCI (on-premises hyperconverged infrastructure)
- Azure Arc (hybrid management)
- Azure Storage (cloud integration)
- Azure Monitor (monitoring)

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
RESOURCE_GROUP="azurehaymaker-hybrid-stack-${UNIQUE_ID}-rg"
LOCATION="eastus"
STACK_CLUSTER_NAME="azurehaymaker-hci-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkrstack${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=hybrid-azure-stack Owner=AzureHayMaker"
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

# Step 3: Create Storage Account for cloud integration
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 4: Create containers for VM images and backups
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "hci-images" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

az storage container create \
  --name "hci-backups" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

# Step 5: Create Azure Stack HCI cluster registration info
cat > /tmp/hci_cluster_config.json <<EOF
{
  "clusterName": "${STACK_CLUSTER_NAME}",
  "location": "${LOCATION}",
  "resourceGroup": "${RESOURCE_GROUP}",
  "arcSettings": {
    "enabled": true,
    "authority": "https://management.azure.com",
    "principalObjectId": "user-object-id-placeholder"
  },
  "nodes": [
    {
      "hostName": "hcinode1.contoso.local",
      "ipAddress": "192.168.1.10",
      "status": "Active"
    },
    {
      "hostName": "hcinode2.contoso.local",
      "ipAddress": "192.168.1.11",
      "status": "Active"
    },
    {
      "hostName": "hcinode3.contoso.local",
      "ipAddress": "192.168.1.12",
      "status": "Active"
    }
  ],
  "storage": {
    "poolName": "S2D-Pool",
    "capacity": 48,
    "mediaType": "SSD"
  }
}
EOF

# Step 6: Create sample HCI cluster metadata resource
cat > /tmp/hci_deployment.json <<EOF
{
  "\$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "resources": [
    {
      "type": "Microsoft.AzureStackHCI/clusters",
      "apiVersion": "2021-09-01-preview",
      "name": "${STACK_CLUSTER_NAME}",
      "location": "${LOCATION}",
      "properties": {
        "desiredProperties": {
          "clusterVersion": "20.04",
          "diagnosticLevel": "Basic",
          "globalWitnessShare": "\\\\witness.contoso.local\\witness"
        }
      },
      "tags": {
        "AzureHayMaker-managed": "true"
      }
    }
  ]
}
EOF

# Deploy HCI cluster resource
az deployment group create \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file /tmp/hci_deployment.json

# Step 7: Create arc connectivity for HCI cluster
cat > /tmp/hci_arc_onboard.sh <<EOF
#!/bin/bash

# Azure Stack HCI Arc Onboarding Script

# This script registers an Azure Stack HCI cluster with Azure Arc

RESOURCE_GROUP="${RESOURCE_GROUP}"
CLUSTER_NAME="${STACK_CLUSTER_NAME}"
LOCATION="${LOCATION}"

# Download and execute Azure Stack HCI registration
# In production, this would be run on the HCI cluster

echo "Preparing Azure Stack HCI for Arc registration..."
echo "Cluster: \${CLUSTER_NAME}"
echo "Resource Group: \${RESOURCE_GROUP}"
echo "Location: \${LOCATION}"

# Create app registration for cluster
CLIENT_ID=\$(az ad app create --display-name "\${CLUSTER_NAME}-arc" --query appId -o tsv)
echo "App Registration ID: \${CLIENT_ID}"

# Generate certificate for authentication
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=\${CLUSTER_NAME}"

echo "HCI registration preparation complete"
EOF

chmod +x /tmp/hci_arc_onboard.sh

# Step 8: Create storage pool configuration
cat > /tmp/storage_config.json <<EOF
{
  "storagePoolConfiguration": {
    "name": "S2D-Pool",
    "mediaType": "SSD",
    "nodeCount": 3,
    "totalCapacity": 48,
    "availableCapacity": 40,
    "volumes": [
      {
        "name": "VM-Storage",
        "size": 30,
        "resiliency": "Mirror",
        "type": "VirtualDiskVolume"
      },
      {
        "name": "Infrastructure-Reserve",
        "size": 10,
        "resiliency": "Mirror",
        "type": "VirtualDiskVolume"
      }
    ]
  }
}
EOF

# Step 9: Store HCI configuration in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "hci-cluster-config" \
  --value @/tmp/hci_cluster_config.json

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "hci-storage-config" \
  --value @/tmp/storage_config.json

# Step 10: Create monitoring setup
az monitor diagnostic-settings create \
  --name "hci-diagnostics" \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.AzureStackHCI/clusters/${STACK_CLUSTER_NAME}" \
  --logs '[{"category":"Audit","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]' 2>/dev/null || echo "Diagnostics setup will be available after cluster registration"

echo ""
echo "=========================================="
echo "Azure Stack HCI Setup Created"
echo "Cluster Name: ${STACK_CLUSTER_NAME}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Storage Account: ${STORAGE_ACCOUNT}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# List HCI clusters
az azurestackhci cluster list \
  --resource-group "${RESOURCE_GROUP}" \
  --output table 2>/dev/null || echo "No HCI clusters yet"

# Show cluster details
az azurestackhci cluster show \
  --name "${STACK_CLUSTER_NAME}" \
  --resource-group "${RESOURCE_GROUP}" 2>/dev/null || echo "Cluster not yet registered"

# Verify Storage Account
az storage account show \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}"

# List storage containers
az storage container list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --output table

# Check Key Vault
az keyvault show --name "${KEYVAULT}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Update cluster properties
az azurestackhci cluster update \
  --name "${STACK_CLUSTER_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --tags Environment=production 2>/dev/null || echo "Update not available for unregistered cluster"

# Operation 2: Monitor cluster health
echo "To monitor cluster health:"
echo "Check via: Get-ClusterNode -Cluster ${STACK_CLUSTER_NAME} | Get-ClusterResourceStatus"

# Operation 3: Upload VM image to HCI storage
cat > /tmp/upload_image.sh <<EOF
#!/bin/bash

# Upload sample VM image to HCI storage
IMAGE_NAME="ubuntu-22.04.vhdx"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT}"
CONTAINER="hci-images"

echo "Uploading VM image to HCI storage..."
echo "Image: \${IMAGE_NAME}"
echo "Container: \${CONTAINER}"

# In production, this would upload actual VHDX image
echo "Image upload configuration prepared"
EOF

chmod +x /tmp/upload_image.sh

# Operation 4: Create virtual machine configuration
cat > /tmp/hci_vm_config.json <<EOF
{
  "vmName": "hci-workload-vm-1",
  "cpuCount": 4,
  "memoryGB": 8,
  "storageGB": 50,
  "networkAdapter": "Virtual Switch 1",
  "imageName": "ubuntu-22.04.vhdx"
}
EOF

# Operation 5: Monitor HCI storage metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.AzureStackHCI/clusters/${STACK_CLUSTER_NAME}" \
  --metric "AvailableMemory" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ') 2>/dev/null || echo "Metrics not yet available"

# Operation 6: Create Arc connection for management
echo "To connect HCI cluster to Azure Arc:"
echo "Run Arc onboarding script on cluster nodes to enable Azure management"

# Operation 7: Configure backup to cloud storage
cat > /tmp/backup_policy.json <<EOF
{
  "backupPolicy": {
    "frequency": "Daily",
    "time": "02:00",
    "retention": 30,
    "destination": "azurehaymaker-stack${UNIQUE_ID}/hci-backups"
  }
}
EOF

# Operation 8: Update cluster settings
echo "Common HCI cluster updates:"
echo "- Firmware updates via: Update-ClusterAwareUpdateClusterRoleStatus"
echo "- Storage pool updates via: Update-StoragePool"
echo "- Network configuration via: Set-NetAdapter"

# Operation 9: List cluster nodes status
echo "Cluster nodes configuration:"
echo "Node 1: hcinode1.contoso.local - CPU: 28, RAM: 256GB, Storage: 8TB"
echo "Node 2: hcinode2.contoso.local - CPU: 28, RAM: 256GB, Storage: 8TB"
echo "Node 3: hcinode3.contoso.local - CPU: 28, RAM: 256GB, Storage: 8TB"

# Operation 10: Review HCI activity logs
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[?contains(resourceType, 'AzureStackHCI')].{Time:eventTimestamp, Event:operationName.localizedValue}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete HCI cluster
az azurestackhci cluster delete \
  --name "${STACK_CLUSTER_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --yes 2>/dev/null || echo "Cluster not found"

# Step 2: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 3: Verify deletion
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 4: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 5: Clean up local files
rm -rf /tmp/hci_* /tmp/storage_config.json /tmp/backup_policy.json /tmp/upload_image.sh
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-hybrid-stack-${UNIQUE_ID}-rg`
- HCI Cluster: `azurehaymaker-hci-${UNIQUE_ID}`
- Storage Account: `azmkrstack${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Stack HCI Overview](https://learn.microsoft.com/en-us/azure-stack/hci/overview)
- [HCI Architecture](https://learn.microsoft.com/en-us/azure-stack/hci/concepts/architecture)
- [Storage Spaces Direct](https://learn.microsoft.com/en-us/windows-server/storage/storage-spaces/storage-spaces-direct-overview)
- [Azure Arc Integration](https://learn.microsoft.com/en-us/azure-stack/hci/deploy/register-hci-system)
- [HCI CLI Reference](https://learn.microsoft.com/en-us/cli/azure/azurestackhci)

---

## Automation Tool
**Recommended**: Azure CLI + PowerShell

**Rationale**: Azure CLI manages cloud-side resources while PowerShell handles on-premises HCI cluster management and configuration.

---

## Estimated Duration
- **Deployment**: 20-30 minutes (cluster registration takes time)
- **Operations Phase**: 8 hours (with VM management and monitoring)
- **Cleanup**: 5-10 minutes

---

## Notes
- HCI converges compute, storage, and networking on-premises
- Storage Spaces Direct provides software-defined storage
- 3-16 nodes per cluster for scalability
- Arc integration enables Azure management portal view
- All operations scoped to single tenant and subscription
- Suitable for edge computing and disconnected operations
