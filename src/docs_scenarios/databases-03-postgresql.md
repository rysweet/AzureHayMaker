# Scenario: Azure Database for PostgreSQL

## Technology Area
Databases

## Company Profile
- **Company Size**: Mid-size technology company
- **Industry**: SaaS / Analytics
- **Use Case**: Host PostgreSQL databases for multi-tenant SaaS applications

## Scenario Description
Deploy Azure Database for PostgreSQL with flexible server, configure high availability, set up read replicas for analytics workloads, and implement backup strategy with point-in-time restore.

## Azure Services Used
- Azure Database for PostgreSQL (Flexible Server)
- Azure Virtual Network (network integration)
- Azure Key Vault (connection strings)
- Azure Monitor (logging and metrics)

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
RESOURCE_GROUP="azurehaymaker-db-postgres-${UNIQUE_ID}-rg"
LOCATION="eastus"
POSTGRES_SERVER="azurehaymaker-postgres-${UNIQUE_ID}"
POSTGRES_ADMIN_USER="pgadmin"
POSTGRES_ADMIN_PASSWORD="P@ssw0rd!${UNIQUE_ID}Aa"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=databases-postgres Owner=AzureHayMaker"
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
  --subnet-name "postgres-subnet" \
  --subnet-prefixes "10.0.0.0/24" \
  --tags ${TAGS}

SUBNET_ID=$(az network vnet subnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "postgres-subnet" \
  --query id -o tsv)

# Step 3: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 4: Create PostgreSQL Flexible Server
az postgres flexible-server create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --location "${LOCATION}" \
  --admin-user "${POSTGRES_ADMIN_USER}" \
  --admin-password "${POSTGRES_ADMIN_PASSWORD}" \
  --sku-name "Standard_B1ms" \
  --tier "Burstable" \
  --storage-size 32 \
  --version 14 \
  --vnet "${VNET_NAME}" \
  --subnet "postgres-subnet" \
  --high-availability "Enabled" \
  --backup-retention 7 \
  --tags ${TAGS}

# Step 5: Configure firewall rules
az postgres flexible-server firewall-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --rule-name "AllowAzureServices" \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Step 6: Create databases
az postgres flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --database-name "tenantdb"

az postgres flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --database-name "analyticsdb"

az postgres flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --database-name "configdb"

# Step 7: Configure server parameters
az postgres flexible-server parameter set \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --name "max_connections" \
  --value 200

az postgres flexible-server parameter set \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --name "shared_buffers" \
  --value 262144

az postgres flexible-server parameter set \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --name "log_statement" \
  --value "all"

# Step 8: Get connection string
POSTGRES_ENDPOINT="${POSTGRES_SERVER}.postgres.database.azure.com"
POSTGRES_CONNECTION_STRING="postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_ENDPOINT}:5432/tenantdb?sslmode=require"

# Store in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "postgres-connection-string" \
  --value "${POSTGRES_CONNECTION_STRING}"

# Step 9: Create read replica for analytics
az postgres flexible-server replica create \
  --name "${POSTGRES_SERVER}-replica" \
  --source-server "${POSTGRES_SERVER}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}"

# Step 10: Configure backup retention and PITR
az postgres flexible-server update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --backup-retention 7 \
  --geo-redundant-backup Disabled

echo ""
echo "=========================================="
echo "PostgreSQL Server Created: ${POSTGRES_SERVER}"
echo "Endpoint: ${POSTGRES_ENDPOINT}"
echo "Databases: tenantdb, analyticsdb, configdb"
echo "Read Replica: ${POSTGRES_SERVER}-replica"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify PostgreSQL Server
az postgres flexible-server show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}"

# Check server state
az postgres flexible-server show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --query "state" -o tsv

# List databases
az postgres flexible-server db list \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --output table

# List parameters
az postgres flexible-server parameter list \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --output table

# Check read replica
az postgres flexible-server show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}-replica"

# List firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create new database for new tenant
az postgres flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --database-name "tenant_newclient"

# Operation 2: Update server parameters
az postgres flexible-server parameter set \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --name "max_prepared_transactions" \
  --value 100

# Operation 3: Create on-demand backup
az postgres flexible-server backup create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --backup-name "manual-backup-$(date +%Y%m%d-%H%M%S)"

# Operation 4: List available backups
az postgres flexible-server backup list \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --output table

# Operation 5: Monitor server metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.DBforPostgreSQL/flexibleServers/${POSTGRES_SERVER}" \
  --metric "cpu_percent" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 6: Check storage usage
az postgres flexible-server show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --query "{StorageGB:storage.storageSizeGB}"

# Operation 7: Restart server
az postgres flexible-server restart \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}"

# Operation 8: Add temporary firewall rule for admin access
MY_IP=$(curl -s ifconfig.me)
az postgres flexible-server firewall-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --rule-name "AdminAccess-$(date +%Y%m%d)" \
  --start-ip-address "${MY_IP}" \
  --end-ip-address "${MY_IP}"

# Operation 9: Remove temporary firewall rule
az postgres flexible-server firewall-rule delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --rule-name "AdminAccess-$(date +%Y%m%d)" \
  --yes 2>/dev/null || true

# Operation 10: List all databases with sizes
az postgres flexible-server db list \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${POSTGRES_SERVER}" \
  --query "[].name" -o table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete read replica
az postgres flexible-server delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}-replica" \
  --yes

# Step 2: Wait for replica deletion
sleep 60

# Step 3: Delete PostgreSQL server
az postgres flexible-server delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${POSTGRES_SERVER}" \
  --yes

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
- Resource Group: `azurehaymaker-db-postgres-${UNIQUE_ID}-rg`
- PostgreSQL Server: `azurehaymaker-postgres-${UNIQUE_ID}`
- Read Replica: `${POSTGRES_SERVER}-replica`
- Databases: `tenantdb`, `analyticsdb`, `configdb`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/postgresql/)
- [PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/)
- [High Availability](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-high-availability)
- [Read Replicas](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-read-replicas)
- [PostgreSQL CLI Reference](https://learn.microsoft.com/en-us/cli/azure/postgres)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive PostgreSQL management capabilities. Flexible Server model offers better performance and management than previous generations.

---

## Estimated Duration
- **Deployment**: 20-25 minutes (HA and replica setup)
- **Operations Phase**: 8 hours (with database management and monitoring)
- **Cleanup**: 10-15 minutes

---

## Notes
- High availability provides automatic failover
- Read replicas enable scaling of read-heavy workloads
- Point-in-time restore enables disaster recovery
- Multi-tier backup strategy with geo-redundancy available
- All operations scoped to single tenant and subscription
- Supports multi-tenant database patterns
- Flexible server tier offers better performance
