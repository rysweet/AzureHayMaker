# Scenario: Azure Site Recovery for Disaster Recovery

## Technology Area
Hybrid+Multicloud

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Healthcare
- **Use Case**: Replicate on-premises VMs to Azure for business continuity

## Scenario Description
Deploy Azure Site Recovery to replicate virtual machines from on-premises VMware/Hyper-V to Azure. Configure replication, set up recovery plans, and perform failover testing.

## Azure Services Used
- Azure Site Recovery (disaster recovery)
- Azure Storage (replication target)
- Azure Virtual Network (recovery network)
- Azure Key Vault (credentials)

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
RESOURCE_GROUP="azurehaymaker-hybrid-recovery-${UNIQUE_ID}-rg"
LOCATION="eastus"
VAULT_NAME="azurehaymaker-vault-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkrsiterecovery${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=hybrid-site-recovery Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Virtual Network for recovery
az network vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --address-prefix "10.0.0.0/16" \
  --subnet-name "recovery-subnet" \
  --subnet-prefixes "10.0.0.0/24" \
  --tags ${TAGS}

# Step 3: Create Storage Account for replication
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 4: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 5: Create Recovery Services Vault
az backup vault create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VAULT_NAME}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Note: The above creates a backup vault; for Site Recovery, use:
# az resource create --resource-group ${RESOURCE_GROUP} --api-version 2021-07-01 --resource-type Microsoft.RecoveryServices/vaults

# Alternative: Create recovery vault directly
cat > /tmp/vault_template.json <<EOF
{
  "\$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "resources": [
    {
      "type": "Microsoft.RecoveryServices/vaults",
      "apiVersion": "2021-07-01",
      "name": "${VAULT_NAME}-recovery",
      "location": "${LOCATION}",
      "sku": {
        "name": "Standard"
      },
      "properties": {}
    }
  ]
}
EOF

# Deploy vault
az deployment group create \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file /tmp/vault_template.json

# Step 6: Configure vault storage redundancy
az backup vault backup-properties set \
  --resource-group "${RESOURCE_GROUP}" \
  --vault-name "${VAULT_NAME}" \
  --backup-storage-redundancy LocallyRedundant

# Step 7: Enable replication policies
# Create replication policy
cat > /tmp/policy_config.json <<EOF
{
  "properties": {
    "recoveryPointRetentionInDays": 7,
    "appConsistentFrequencyInMinutes": 0,
    "crashConsistentFrequencyInMinutes": 5,
    "multiVmSyncStatus": "Enabled"
  }
}
EOF

# Step 8: Create sample protected item configuration
cat > /tmp/protected_vm.json <<EOF
{
  "sourceVMName": "on-premises-vm-1",
  "sourceVMResourceGroup": "on-premises-rg",
  "protectionContainerName": "onprem-container",
  "replicationPolicyName": "default-policy",
  "targetResourceGroupName": "${RESOURCE_GROUP}",
  "targetStorageAccount": "${STORAGE_ACCOUNT}",
  "targetVirtualNetwork": "${VNET_NAME}",
  "recoveryVaultName": "${VAULT_NAME}-recovery"
}
EOF

# Step 9: Store recovery configuration in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "site-recovery-config" \
  --value @/tmp/protected_vm.json

# Step 10: Create diagnostic settings
az monitor diagnostic-settings create \
  --name "site-recovery-diagnostics" \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.RecoveryServices/vaults/${VAULT_NAME}" \
  --logs '[{"category":"AzureSiteRecoveryEvents","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]'

echo ""
echo "=========================================="
echo "Site Recovery Vault Created: ${VAULT_NAME}"
echo "Recovery Region: ${LOCATION}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Recovery Vault
az backup vault list \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Check vault properties
az backup vault backup-properties show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VAULT_NAME}" 2>/dev/null || echo "Vault details not available"

# Verify Storage Account
az storage account show \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}"

# Verify Virtual Network
az network vnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}"

# Check Key Vault
az keyvault show --name "${KEYVAULT}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Enable replication for simulated VM
echo "To enable replication for a source VM:"
echo "az site-recovery machine replicate --resource-group ${RESOURCE_GROUP} --fabric-name on-premises-fabric --protection-container-name default-container --machine-name source-vm-name --source-machine-id /subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/virtualMachines/source-vm"

# Operation 2: Create recovery plan
cat > /tmp/recovery_plan.json <<EOF
{
  "name": "production-recovery-plan",
  "description": "Recovery plan for production VMs",
  "groups": [
    {
      "name": "Tier1-DatabaseServers",
      "startGroupActions": [],
      "endGroupActions": [],
      "replicationProtectedItems": []
    },
    {
      "name": "Tier2-AppServers",
      "startGroupActions": [],
      "endGroupActions": [],
      "replicationProtectedItems": []
    }
  ]
}
EOF

# Operation 3: Monitor replication health
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.RecoveryServices/vaults/${VAULT_NAME}" \
  --metric "ReplicationLatency" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ') 2>/dev/null || echo "Metrics not yet available"

# Operation 4: Check latest recovery points
echo "To check recovery points:"
echo "az site-recovery recovery-point list --fabric-name on-premises-fabric --protection-container-name default-container --replicated-item-name source-vm-name"

# Operation 5: Test failover
echo "To perform test failover:"
echo "az site-recovery machine failover-test --fabric-name on-premises-fabric --protection-container-name default-container --machine-name source-vm-name --network-id /subscriptions/xxx/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/virtualNetworks/${VNET_NAME}"

# Operation 6: Perform cleanup of test failover
echo "To cleanup test failover:"
echo "az site-recovery machine failover-test-cleanup --fabric-name on-premises-fabric --protection-container-name default-container --machine-name source-vm-name"

# Operation 7: Commit failover
echo "To commit a failover (after test successful):"
echo "az site-recovery machine failover-commit --fabric-name on-premises-fabric --protection-container-name default-container --machine-name source-vm-name"

# Operation 8: Monitor vault backup jobs
az backup job list \
  --resource-group "${RESOURCE_GROUP}" \
  --vault-name "${VAULT_NAME}" \
  --output table 2>/dev/null || echo "No backup jobs"

# Operation 9: Configure notification settings
echo "To configure notifications:"
echo "Email notifications can be set up in Azure Portal for replication events"

# Operation 10: Review site recovery logs
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[?contains(resourceType, 'RecoveryServices')].{Time:eventTimestamp, Event:operationName.localizedValue, Status:status.localizedValue}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Disable replication for protected items
echo "To disable replication:"
echo "az site-recovery machine remove --fabric-name on-premises-fabric --protection-container-name default-container --name source-vm-name"

# Step 2: Delete recovery vault
az backup vault delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VAULT_NAME}" \
  --yes 2>/dev/null || true

# Step 3: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 4: Verify deletion
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 5: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 6: Clean up local files
rm -rf /tmp/vault_template.json /tmp/policy_config.json /tmp/protected_vm.json /tmp/recovery_plan.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-hybrid-recovery-${UNIQUE_ID}-rg`
- Recovery Vault: `azurehaymaker-vault-${UNIQUE_ID}`
- Storage Account: `azmkrsiterecovery${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Site Recovery Overview](https://learn.microsoft.com/en-us/azure/site-recovery/site-recovery-overview)
- [Site Recovery Architecture](https://learn.microsoft.com/en-us/azure/site-recovery/azure-to-azure-architecture)
- [Replication Process](https://learn.microsoft.com/en-us/azure/site-recovery/site-recovery-replication)
- [Recovery Plans](https://learn.microsoft.com/en-us/azure/site-recovery/recovery-plan-overview)
- [Site Recovery CLI Reference](https://learn.microsoft.com/en-us/cli/azure/site-recovery)

---

## Automation Tool
**Recommended**: Azure CLI + ARM Templates

**Rationale**: Azure CLI handles vault management while ARM templates configure complex replication policies and recovery plans.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8 hours (with replication monitoring and test failovers)
- **Cleanup**: 5-10 minutes

---

## Notes
- Replication RPO (Recovery Point Objective) typically 5-15 minutes
- RTO (Recovery Time Objective) depends on failover complexity
- Test failovers verify recovery plans without affecting production
- Network mapping ensures proper connectivity after failover
- All operations scoped to single tenant and subscription
- Suitable for business-critical workload protection
