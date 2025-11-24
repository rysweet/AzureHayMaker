# Scenario: MySQL Database for WordPress Application

## Technology Area
Databases

## Company Profile
- **Company Size**: Small marketing agency
- **Industry**: Marketing / Media
- **Use Case**: Host multiple client WordPress websites with shared MySQL database backend

## Scenario Description
Deploy Azure Database for MySQL Flexible Server to host WordPress databases. Configure firewall rules, create databases for different clients, and implement basic backup strategy.

## Azure Services Used
- Azure Database for MySQL - Flexible Server
- Azure Virtual Network
- Azure Private DNS Zone (for private connectivity)

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
RESOURCE_GROUP="azurehaymaker-db-mysql-${UNIQUE_ID}-rg"
LOCATION="eastus"
MYSQL_SERVER="azurehaymaker-mysql-${UNIQUE_ID}"
MYSQL_ADMIN_USER="mysqladmin"
MYSQL_ADMIN_PASSWORD="P@ssw0rd!${UNIQUE_ID}Aa"  # Must meet complexity requirements
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
SUBNET_NAME="mysql-subnet"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=databases-mysql-wordpress Owner=AzureHayMaker"
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
  --subnet-name "${SUBNET_NAME}" \
  --subnet-prefixes "10.0.1.0/24" \
  --tags ${TAGS}

# Step 3: Delegate subnet to MySQL Flexible Server
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_NAME}" \
  --delegations "Microsoft.DBforMySQL/flexibleServers"

SUBNET_ID=$(az network vnet subnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_NAME}" \
  --query id -o tsv)

# Step 4: Create Private DNS Zone for MySQL
az network private-dns zone create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}.private.mysql.database.azure.com" \
  --tags ${TAGS}

# Step 5: Link Private DNS Zone to VNet
az network private-dns link vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --zone-name "${MYSQL_SERVER}.private.mysql.database.azure.com" \
  --name "mysql-dns-link" \
  --virtual-network "${VNET_NAME}" \
  --registration-enabled false

# Step 6: Create MySQL Flexible Server
az mysql flexible-server create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --location "${LOCATION}" \
  --admin-user "${MYSQL_ADMIN_USER}" \
  --admin-password "${MYSQL_ADMIN_PASSWORD}" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 8.0 \
  --vnet "${VNET_NAME}" \
  --subnet "${SUBNET_NAME}" \
  --private-dns-zone "${MYSQL_SERVER}.private.mysql.database.azure.com" \
  --tags ${TAGS}

# Step 7: Configure server parameters for WordPress
az mysql flexible-server parameter set \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --name max_connections \
  --value 200

az mysql flexible-server parameter set \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --name innodb_buffer_pool_size \
  --value 134217728

# Step 8: Create databases for WordPress sites
az mysql flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --database-name "wordpress_client1"

az mysql flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --database-name "wordpress_client2"

az mysql flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --database-name "wordpress_client3"

# Step 9: Configure backup retention
az mysql flexible-server update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --backup-retention 7 \
  --geo-redundant-backup Disabled

# Step 10: Add firewall rule for Azure services (if needed)
# Note: With private VNet integration, this may not be necessary
az mysql flexible-server firewall-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --rule-name "AllowAzureServices" \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

echo ""
echo "=========================================="
echo "MySQL Server Details:"
echo "Server: ${MYSQL_SERVER}.mysql.database.azure.com"
echo "Admin User: ${MYSQL_ADMIN_USER}"
echo "Databases: wordpress_client1, wordpress_client2, wordpress_client3"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify MySQL Server
az mysql flexible-server show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}"

# List databases
az mysql flexible-server db list \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --output table

# Check server state
az mysql flexible-server show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --query "state" -o tsv

# List firewall rules
az mysql flexible-server firewall-rule list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create new database for new client
az mysql flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --database-name "wordpress_client4"

# Operation 2: Update server configuration
az mysql flexible-server parameter set \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --name max_allowed_packet \
  --value 67108864

# Operation 3: Perform on-demand backup
az mysql flexible-server backup create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --backup-name "manual-backup-$(date +%Y%m%d-%H%M%S)"

# Operation 4: List available backups
az mysql flexible-server backup list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --output table

# Operation 5: Monitor server metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.DBforMySQL/flexibleServers/${MYSQL_SERVER}" \
  --metric "cpu_percent" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ') \
  --interval PT1M

# Operation 6: Check storage usage
az mysql flexible-server show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --query "{StorageGB:storage.storageSizeGB, StorageUsedMB:storage.storageUsageMB}"

# Operation 7: Restart server (simulating maintenance)
az mysql flexible-server restart \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}"

# Operation 8: Add temporary firewall rule for admin access
MY_IP=$(curl -s ifconfig.me)
az mysql flexible-server firewall-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --rule-name "AdminAccess-$(date +%Y%m%d)" \
  --start-ip-address "${MY_IP}" \
  --end-ip-address "${MY_IP}"

# Operation 9: Remove temporary firewall rule
az mysql flexible-server firewall-rule delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${MYSQL_SERVER}" \
  --rule-name "AdminAccess-$(date +%Y%m%d)" \
  --yes

# Operation 10: Check server logs (last 100 lines)
az mysql flexible-server server-logs list \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${MYSQL_SERVER}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 2: Verify deletion
sleep 120  # MySQL deletion takes longer
az group exists --name "${RESOURCE_GROUP}"

# Step 3: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-db-mysql-${UNIQUE_ID}-rg`
- MySQL Server: `azurehaymaker-mysql-${UNIQUE_ID}`
- VNet: `azurehaymaker-vnet-${UNIQUE_ID}`
- Databases: `wordpress_client1`, `wordpress_client2`, `wordpress_client3`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Database for MySQL Flexible Server](https://learn.microsoft.com/en-us/azure/mysql/flexible-server/overview)
- [MySQL Flexible Server CLI Reference](https://learn.microsoft.com/en-us/cli/azure/mysql/flexible-server)
- [Configure server parameters](https://learn.microsoft.com/en-us/azure/mysql/flexible-server/how-to-configure-server-parameters-cli)
- [Backup and restore](https://learn.microsoft.com/en-us/azure/mysql/flexible-server/concepts-backup-restore)
- [VNet integration](https://learn.microsoft.com/en-us/azure/mysql/flexible-server/concepts-networking-vnet)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides excellent support for MySQL Flexible Server with all necessary commands. Terraform is also a good option for infrastructure-as-code, but Azure CLI is simpler for this scenario.

---

## Estimated Duration
- **Deployment**: 15-20 minutes (VNet and MySQL setup)
- **Operations Phase**: 8 hours (with periodic monitoring and configuration changes)
- **Cleanup**: 10-15 minutes (MySQL deletion takes longer than other services)

---

## Notes
- Uses Burstable tier (B1ms) for cost optimization
- Private VNet integration provides better security than public access
- Backup retention set to 7 days
- WordPress-specific MySQL parameters configured
- All operations scoped to single tenant and subscription
- Connection string format: `mysql://${MYSQL_ADMIN_USER}:${MYSQL_ADMIN_PASSWORD}@${MYSQL_SERVER}.mysql.database.azure.com:3306/wordpress_client1`
