# Scenario: Private Endpoints for Azure Services

## Technology Area
Networking

## Company Profile
- **Company Size**: Enterprise
- **Industry**: Banking / Healthcare / Government
- **Use Case**: Secure connectivity to Azure services with private IP addresses and eliminate exposure to public internet

## Scenario Description
Deploy Azure Private Endpoints to provide private IP addresses for Azure services (Storage Account, SQL Database, Azure Key Vault) within a virtual network. This scenario covers private endpoint provisioning, DNS zone configuration, network policies, and private link services.

## Azure Services Used
- Azure Private Endpoints
- Azure Private Link
- Azure Virtual Network
- Azure Storage Account
- Azure SQL Database
- Azure Key Vault
- Azure Private DNS Zones
- Azure Network Interface

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Understanding of private networking and DNS concepts

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-pe-${UNIQUE_ID}-rg"
LOCATION="eastus"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
PRIVATE_SUBNET="azurehaymaker-private-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkstorage${UNIQUE_ID}"
KEYVAULT_NAME="azurehaymaker-kv${UNIQUE_ID}"
SQL_SERVER="azurehaymaker-sql-${UNIQUE_ID}"
SQL_DB="azurehaymaker-sqldb-${UNIQUE_ID}"
STORAGE_PE="azurehaymaker-storage-pe-${UNIQUE_ID}"
KEYVAULT_PE="azurehaymaker-kv-pe-${UNIQUE_ID}"
SQL_PE="azurehaymaker-sql-pe-${UNIQUE_ID}"
PRIVATE_DNS_STORAGE="privatelink.blob.core.windows.net"
PRIVATE_DNS_KV="privatelink.vaultcore.azure.net"
PRIVATE_DNS_SQL="privatelink.database.windows.net"
NSG_NAME="azurehaymaker-pe-nsg-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=networking-private-endpoint Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Virtual Network
az network vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --address-prefix 10.0.0.0/16 \
  --tags ${TAGS}

# Step 3: Create Private Subnet
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${PRIVATE_SUBNET}" \
  --address-prefix 10.0.1.0/24

# Step 4: Disable private endpoint network policies (required)
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${PRIVATE_SUBNET}" \
  --disable-private-endpoint-network-policies true

# Step 5: Create Storage Account
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 6: Restrict Storage Account access to private endpoint only
STORAGE_ID=$(az storage account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --query id -o tsv)

az storage account update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --default-action Deny

# Step 7: Create Private Endpoint for Storage Account
az network private-endpoint create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_PE}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${PRIVATE_SUBNET}" \
  --private-connection-resource-id "${STORAGE_ID}" \
  --group-ids blob \
  --connection-name "azurehaymaker-storage-connection-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 8: Create Private DNS Zone for Storage
az network private-dns zone create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PRIVATE_DNS_STORAGE}" \
  --tags ${TAGS}

# Step 9: Link Private DNS Zone to VNet for Storage
az network private-dns link vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_STORAGE}" \
  --name "azurehaymaker-storage-link-${UNIQUE_ID}" \
  --virtual-network "${VNET_NAME}" \
  --registration-enabled false

# Step 10: Create DNS A record for Storage
STORAGE_PE_IP=$(az network private-endpoint show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_PE}" \
  --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)

az network private-dns record-set a create \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_STORAGE}" \
  --name "${STORAGE_ACCOUNT}" \
  --ttl 300

az network private-dns record-set a add-record \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_STORAGE}" \
  --record-set-name "${STORAGE_ACCOUNT}" \
  --ipv4-address "${STORAGE_PE_IP}"

# Step 11: Create Key Vault
az keyvault create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEYVAULT_NAME}" \
  --location "${LOCATION}" \
  --sku standard \
  --tags ${TAGS}

# Step 12: Get Key Vault resource ID
KEYVAULT_ID=$(az keyvault show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEYVAULT_NAME}" \
  --query id -o tsv)

# Step 13: Create Private Endpoint for Key Vault
az network private-endpoint create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEYVAULT_PE}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${PRIVATE_SUBNET}" \
  --private-connection-resource-id "${KEYVAULT_ID}" \
  --group-ids vault \
  --connection-name "azurehaymaker-kv-connection-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 14: Create Private DNS Zone for Key Vault
az network private-dns zone create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PRIVATE_DNS_KV}" \
  --tags ${TAGS}

# Step 15: Link Private DNS Zone to VNet for Key Vault
az network private-dns link vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_KV}" \
  --name "azurehaymaker-kv-link-${UNIQUE_ID}" \
  --virtual-network "${VNET_NAME}" \
  --registration-enabled false

# Step 16: Create DNS A record for Key Vault
KEYVAULT_PE_IP=$(az network private-endpoint show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEYVAULT_PE}" \
  --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)

az network private-dns record-set a create \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_KV}" \
  --name "${KEYVAULT_NAME}" \
  --ttl 300

az network private-dns record-set a add-record \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_KV}" \
  --record-set-name "${KEYVAULT_NAME}" \
  --ipv4-address "${KEYVAULT_PE_IP}"

# Step 17: Create Azure SQL Server
az sql server create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_SERVER}" \
  --location "${LOCATION}" \
  --admin-user azureuser \
  --admin-password "P@ssw0rd1234567!" \
  --tags ${TAGS}

# Step 18: Create Azure SQL Database
az sql db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server "${SQL_SERVER}" \
  --name "${SQL_DB}" \
  --service-objective Basic \
  --tags ${TAGS}

# Step 19: Get SQL Server resource ID
SQL_SERVER_ID=$(az sql server show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_SERVER}" \
  --query id -o tsv)

# Step 20: Create Private Endpoint for SQL Database
az network private-endpoint create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_PE}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${PRIVATE_SUBNET}" \
  --private-connection-resource-id "${SQL_SERVER_ID}" \
  --group-ids sqlServer \
  --connection-name "azurehaymaker-sql-connection-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 21: Create Private DNS Zone for SQL
az network private-dns zone create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PRIVATE_DNS_SQL}" \
  --tags ${TAGS}

# Step 22: Link Private DNS Zone to VNet for SQL
az network private-dns link vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_SQL}" \
  --name "azurehaymaker-sql-link-${UNIQUE_ID}" \
  --virtual-network "${VNET_NAME}" \
  --registration-enabled false

# Step 23: Create DNS A record for SQL
SQL_PE_IP=$(az network private-endpoint show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_PE}" \
  --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)

az network private-dns record-set a create \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_SQL}" \
  --name "${SQL_SERVER}" \
  --ttl 300

az network private-dns record-set a add-record \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_SQL}" \
  --record-set-name "${SQL_SERVER}" \
  --ipv4-address "${SQL_PE_IP}"
```

### Validation
```bash
# Verify Virtual Network and Subnet
az network vnet show --resource-group "${RESOURCE_GROUP}" --name "${VNET_NAME}"

# Verify Storage Account
az storage account show --resource-group "${RESOURCE_GROUP}" --name "${STORAGE_ACCOUNT}" --query "{name: name, accessTier: accessTier, minimumTlsVersion: minimumTlsVersion}"

# Verify Storage Private Endpoint
az network private-endpoint show --resource-group "${RESOURCE_GROUP}" --name "${STORAGE_PE}"

# Verify Key Vault
az keyvault show --resource-group "${RESOURCE_GROUP}" --name "${KEYVAULT_NAME}"

# Verify Key Vault Private Endpoint
az network private-endpoint show --resource-group "${RESOURCE_GROUP}" --name "${KEYVAULT_PE}"

# Verify SQL Server and Database
az sql server show --resource-group "${RESOURCE_GROUP}" --name "${SQL_SERVER}"

# Verify SQL Private Endpoint
az network private-endpoint show --resource-group "${RESOURCE_GROUP}" --name "${SQL_PE}"

# List all Private Endpoints
az network private-endpoint list --resource-group "${RESOURCE_GROUP}" --output table

# Verify Private DNS Zones
az network private-dns zone list --resource-group "${RESOURCE_GROUP}" --output table

# Verify DNS records
az network private-dns record-set a list --resource-group "${RESOURCE_GROUP}" --zone-name "${PRIVATE_DNS_STORAGE}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Get Storage Account network rules
az storage account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --query "networkRuleSet"

# Operation 2: Allow specific VNet access to Storage Account
az storage account network-rule add \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --vnet-name "${VNET_NAME}" \
  --subnet-name "${PRIVATE_SUBNET}"

# Operation 3: Get Key Vault access policies
az keyvault show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEYVAULT_NAME}" \
  --query "properties.accessPolicies"

# Operation 4: Create storage account blob container
az storage container create \
  --account-name "${STORAGE_ACCOUNT}" \
  --name "azurehaymaker-container-${UNIQUE_ID}" \
  --auth-mode login

# Operation 5: Upload test file to storage
echo "Test data for private endpoint" > /tmp/test-file.txt
az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --container-name "azurehaymaker-container-${UNIQUE_ID}" \
  --name "test-file.txt" \
  --file "/tmp/test-file.txt" \
  --auth-mode login

# Operation 6: Store secret in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT_NAME}" \
  --name "azurehaymaker-secret" \
  --value "MySecureSecretValue123!"

# Operation 7: List all private endpoint connections for Storage
az network private-endpoint-connection list \
  --id "${STORAGE_ID}" \
  --output table

# Operation 8: List all private endpoint connections for Key Vault
az network private-endpoint-connection list \
  --id "${KEYVAULT_ID}" \
  --output table

# Operation 9: Get SQL Server firewall rules
az sql server firewall-rule list \
  --resource-group "${RESOURCE_GROUP}" \
  --server "${SQL_SERVER}" \
  --output table

# Operation 10: Monitor private endpoint connection status
az network private-endpoint show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_PE}" \
  --query "{name: name, provisioningState: provisioningState, connectionState: privateLinkServiceConnections[0].privateLinkServiceConnectionState.status}"

# Operation 11: Create additional private DNS record for redundancy
az network private-dns record-set a add-record \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_STORAGE}" \
  --record-set-name "${STORAGE_ACCOUNT}-backup" \
  --ipv4-address "${STORAGE_PE_IP}"

# Operation 12: List virtual network links for DNS zones
az network private-dns link vnet list \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${PRIVATE_DNS_STORAGE}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete all private endpoint connections
az network private-endpoint delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_PE}" \
  --yes

az network private-endpoint delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEYVAULT_PE}" \
  --yes

az network private-endpoint delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_PE}" \
  --yes

# Step 2: Delete Private DNS Zones
az network private-dns zone delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PRIVATE_DNS_STORAGE}" \
  --yes

az network private-dns zone delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PRIVATE_DNS_KV}" \
  --yes

az network private-dns zone delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PRIVATE_DNS_SQL}" \
  --yes

# Step 3: Delete the entire resource group (includes all remaining resources)
az group delete \
  --resource-group "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 4: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 120

# Step 5: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 6: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-pe-${UNIQUE_ID}-rg`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Private Subnet: `azurehaymaker-private-${UNIQUE_ID}`
- Storage Account: `azmkstorage${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv${UNIQUE_ID}`
- SQL Server: `azurehaymaker-sql-${UNIQUE_ID}`
- SQL Database: `azurehaymaker-sqldb-${UNIQUE_ID}`
- Storage Private Endpoint: `azurehaymaker-storage-pe-${UNIQUE_ID}`
- Key Vault Private Endpoint: `azurehaymaker-kv-pe-${UNIQUE_ID}`
- SQL Private Endpoint: `azurehaymaker-sql-pe-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Private Endpoints Overview](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview)
- [Azure Private Link Service](https://learn.microsoft.com/en-us/azure/private-link/private-link-service-overview)
- [Private DNS Zones](https://learn.microsoft.com/en-us/azure/dns/private-dns-overview)
- [Create Private Endpoint with CLI](https://learn.microsoft.com/en-us/azure/private-link/create-private-endpoint-cli)
- [Private Endpoint Connection States](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview)
- [Azure Storage Private Endpoints](https://learn.microsoft.com/en-us/azure/storage/common/storage-private-endpoints)
- [Azure SQL Database Private Endpoints](https://learn.microsoft.com/en-us/azure/azure-sql/database/private-endpoint-overview)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive private link management with straightforward commands for creating private endpoints, configuring DNS zones, and managing private connectivity. Direct CLI commands enable fine-grained control over service access policies.

---

## Estimated Duration
- **Deployment**: 20-25 minutes (includes service provisioning and endpoint creation)
- **Operations Phase**: 8+ hours (with monitoring, access policy updates, and network verification)
- **Cleanup**: 10-15 minutes

---

## Notes
- Private Endpoints require dedicated subnet with network policies disabled
- Storage Account access restricted to private endpoint (default deny)
- Private DNS Zones automatically resolve service hostnames to private IP addresses
- SQL Server requires firewall rule adjustment when using private endpoints
- Key Vault access remains restricted to explicitly allowed principals
- Private Endpoints eliminate exposure to public internet for Azure services
- DNS resolution works transparently within VNet without client configuration changes
- All operations scoped to single tenant and subscription
- Private endpoint connections must be approved (auto-approved in this scenario)
- Custom DNS configurations ensure seamless service discovery over private network
