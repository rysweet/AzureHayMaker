# Scenario: Azure SQL Managed Instance

## Technology Area
Databases

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Financial Services
- **Use Case**: Lift-and-shift SQL Server databases with minimal changes

## Scenario Description
Deploy Azure SQL Managed Instance for SQL Server workload migration. Configure high availability, implement database backups, set up user-defined routes, and demonstrate failover capabilities.

## Azure Services Used
- Azure SQL Managed Instance
- Azure Virtual Network (network integration)
- Azure Key Vault (credentials storage)
- Azure Storage (backups)
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
RESOURCE_GROUP="azurehaymaker-db-sqlmi-${UNIQUE_ID}-rg"
LOCATION="eastus"
SQL_MI="azurehaymaker-sqlmi-${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
NSG_NAME="azurehaymaker-nsg-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
STORAGE_ACCOUNT="azmkrsqlmi${UNIQUE_ID}"
SQL_ADMIN_USER="sqladmin"
SQL_ADMIN_PASSWORD="P@ssw0rd!${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=databases-sql-managed-instance Owner=AzureHayMaker"
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
  --address-prefix "10.0.0.0/16" \
  --subnet-name "mi-subnet" \
  --subnet-prefixes "10.0.0.0/24" \
  --tags ${TAGS}

# Step 3: Create Network Security Group
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_NAME}" \
  --tags ${TAGS}

# Step 4: Add NSG rules for SQL MI
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "AllowManagementSubnetInbound" \
  --priority 100 \
  --direction Inbound \
  --access Allow \
  --protocol "*" \
  --source-address-prefixes "*" \
  --destination-address-prefixes "10.0.0.0/24" \
  --source-port-ranges "*" \
  --destination-port-ranges "*"

az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "AllowRedirectRuleInbound" \
  --priority 101 \
  --direction Inbound \
  --access Allow \
  --protocol "Tcp" \
  --source-address-prefixes "*" \
  --destination-address-prefixes "10.0.0.0/24" \
  --source-port-ranges "*" \
  --destination-port-ranges "11000-11999"

# Step 5: Associate NSG with subnet
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "mi-subnet" \
  --network-security-group "${NSG_NAME}"

SUBNET_ID=$(az network vnet subnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "mi-subnet" \
  --query id -o tsv)

# Step 6: Create Storage Account for backups
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 7: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Store credentials in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "sqlmi-admin-user" \
  --value "${SQL_ADMIN_USER}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "sqlmi-admin-password" \
  --value "${SQL_ADMIN_PASSWORD}"

# Step 8: Create SQL Managed Instance
az sql mi create \
  --name "${SQL_MI}" \
  --resource-group "${RESOURCE_GROUP}" \
  --admin-user "${SQL_ADMIN_USER}" \
  --admin-password "${SQL_ADMIN_PASSWORD}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "mi-subnet" \
  --location "${LOCATION}" \
  --sku-name "GP_Gen5" \
  --v-core-count 4 \
  --storage-size-gb 128 \
  --collation "SQL_Latin1_General_CP1_CI_AS" \
  --license-type LicenseIncluded \
  --backup-redundancy "Local" \
  --public-data-endpoint-enabled true \
  --enable-auto-failover false \
  --tags ${TAGS}

# Step 9: Create managed instance database
az sql midb create \
  --resource-group "${RESOURCE_GROUP}" \
  --mi-name "${SQL_MI}" \
  --name "productiondb" \
  --collation "SQL_Latin1_General_CP1_CI_AS"

az sql midb create \
  --resource-group "${RESOURCE_GROUP}" \
  --mi-name "${SQL_MI}" \
  --name "stagingdb" \
  --collation "SQL_Latin1_General_CP1_CI_AS"

# Step 10: Configure backup retention
az sql mi update \
  --name "${SQL_MI}" \
  --resource-group "${RESOURCE_GROUP}" \
  --backup-retention "7" \
  --backup-storage-redundancy "Local"

echo ""
echo "=========================================="
echo "SQL Managed Instance Created: ${SQL_MI}"
echo "Databases: productiondb, stagingdb"
echo "Location: ${LOCATION}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify SQL Managed Instance
az sql mi show \
  --name "${SQL_MI}" \
  --resource-group "${RESOURCE_GROUP}"

# Check instance status
az sql mi show \
  --name "${SQL_MI}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "state" -o tsv

# List databases
az sql midb list \
  --resource-group "${RESOURCE_GROUP}" \
  --mi-name "${SQL_MI}" \
  --output table

# Get instance properties
az sql mi show \
  --name "${SQL_MI}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "{Name:name, VCores:vCores, StorageGB:storageSizeGB, PublicEndpoint:publicDataEndpointEnabled}" -o table

# List NSG rules
az network nsg rule list \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --output table

# Verify storage account
az storage account show \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create database backup
az sql midb backup-long-term-retention-policy set \
  --resource-group "${RESOURCE_GROUP}" \
  --mi-name "${SQL_MI}" \
  --database "productiondb" \
  --weekly-retention "P4W" \
  --monthly-retention "P12M" \
  --yearly-retention "P5Y"

# Operation 2: Trigger manual backup
echo "Manual backups are automatically managed by Azure for Managed Instance"

# Operation 3: Monitor instance metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Sql/managedInstances/${SQL_MI}" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 4: Check storage usage
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Sql/managedInstances/${SQL_MI}" \
  --metric "StorageUsed" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 5: Scale instance (change vCores)
# Note: This operation takes time
az sql mi update \
  --name "${SQL_MI}" \
  --resource-group "${RESOURCE_GROUP}" \
  --v-core-count 8

# Operation 6: Restore database from backup
echo "To restore a database from backup:"
echo "az sql midb restore --resource-group \"${RESOURCE_GROUP}\" --mi-name \"${SQL_MI}\" --name \"productiondb-restored\" --restore-point-in-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

# Operation 7: Create additional database user (for testing)
echo "User management requires SQL connection"

# Operation 8: Monitor failed logins
az sql audit-policy show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SQL_MI}" \
  --managed-instance

# Operation 9: Update maintenance window
az sql mi update \
  --name "${SQL_MI}" \
  --resource-group "${RESOURCE_GROUP}" \
  --maintenance-configuration-id "/subscriptions/$(az account show --query id -o tsv)/providers/Microsoft.Maintenance/maintenanceConfigurations/SQL_Default"

# Operation 10: Check instance connectivity
echo "Instance endpoint: ${SQL_MI}.public.${LOCATION}.database.windows.net"
echo "Connection string: Server=tcp:${SQL_MI}.public.${LOCATION}.database.windows.net,3342;Database=productiondb;User ID=${SQL_ADMIN_USER};Password=<password>;Encrypt=true;Connection Timeout=30;"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete databases
az sql midb delete \
  --resource-group "${RESOURCE_GROUP}" \
  --mi-name "${SQL_MI}" \
  --name "productiondb" \
  --yes

az sql midb delete \
  --resource-group "${RESOURCE_GROUP}" \
  --mi-name "${SQL_MI}" \
  --name "stagingdb" \
  --yes

# Step 2: Delete SQL Managed Instance
az sql mi delete \
  --name "${SQL_MI}" \
  --resource-group "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 3: Wait for instance deletion
sleep 300

# Step 4: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 5: Verify deletion
sleep 120
az group exists --name "${RESOURCE_GROUP}"

# Step 6: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-db-sqlmi-${UNIQUE_ID}-rg`
- SQL Managed Instance: `azurehaymaker-sqlmi-${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Network Security Group: `azurehaymaker-nsg-${UNIQUE_ID}`
- Storage Account: `azmkrsqlmi${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [SQL Managed Instance Overview](https://learn.microsoft.com/en-us/azure/azure-sql/managed-instance/sql-managed-instance-paas-overview)
- [Managed Instance Features](https://learn.microsoft.com/en-us/azure/azure-sql/managed-instance/features-comparison)
- [Networking Configuration](https://learn.microsoft.com/en-us/azure/azure-sql/managed-instance/connectivity-architecture-overview)
- [Backup and Restore](https://learn.microsoft.com/en-us/azure/azure-sql/managed-instance/automated-backups-overview)
- [SQL MI CLI Reference](https://learn.microsoft.com/en-us/cli/azure/sql/mi)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive Managed Instance management. T-SQL operations are typically handled separately via SQL Server Management Studio or sqlcmd.

---

## Estimated Duration
- **Deployment**: 30-45 minutes (MI provisioning takes significant time)
- **Operations Phase**: 8 hours (with scaling and monitoring)
- **Cleanup**: 20-30 minutes (MI deletion is lengthy)

---

## Notes
- Fully managed SQL Server instance with automatic updates and patching
- Multiple database support with up to 100 instances per subscription
- Automatic backups with point-in-time restore capability
- Public endpoint for remote access (optional)
- Private endpoint support for private networks
- All operations scoped to single tenant and subscription
- Suitable for lift-and-shift SQL Server migrations
- Instance-level operations available with T-SQL
