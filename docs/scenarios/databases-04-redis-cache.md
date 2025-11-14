# Scenario: Azure Cache for Redis

## Technology Area
Databases

## Company Profile
- **Company Size**: Mid-size e-commerce company
- **Industry**: Retail / E-commerce
- **Use Case**: High-performance session storage and data caching layer

## Scenario Description
Deploy Azure Cache for Redis to provide low-latency caching for application data and sessions. Configure clustering, implement eviction policies, set up persistence options, and demonstrate cache operations.

## Azure Services Used
- Azure Cache for Redis
- Azure Virtual Network (network isolation)
- Azure Key Vault (connection strings)
- Azure Monitor (monitoring and diagnostics)

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
RESOURCE_GROUP="azurehaymaker-db-redis-${UNIQUE_ID}-rg"
LOCATION="eastus"
REDIS_CACHE="azurehaymaker-redis-${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"
LOG_ANALYTICS="azurehaymaker-logs-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=databases-redis-cache Owner=AzureHayMaker"
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
  --subnet-name "redis-subnet" \
  --subnet-prefixes "10.0.0.0/24" \
  --tags ${TAGS}

SUBNET_ID=$(az network vnet subnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "redis-subnet" \
  --query id -o tsv)

# Step 3: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 4: Create Log Analytics Workspace
az monitor log-analytics workspace create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 5: Create Azure Cache for Redis
az redis create \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard \
  --vm-size c1 \
  --enable-non-ssl-port false \
  --minimum-tls-version "1.2" \
  --zones 1 2 \
  --tags ${TAGS}

# Step 6: Get connection information
REDIS_ENDPOINT=$(az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "hostName" -o tsv)

REDIS_PORT=$(az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "sslPort" -o tsv)

REDIS_PRIMARY_KEY=$(az redis list-keys \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "primaryKey" -o tsv)

REDIS_SECONDARY_KEY=$(az redis list-keys \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "secondaryKey" -o tsv)

# Store connection string in Key Vault
REDIS_CONNECTION_STRING="${REDIS_ENDPOINT}:${REDIS_PORT},password=${REDIS_PRIMARY_KEY},ssl=True"
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "redis-connection-string" \
  --value "${REDIS_CONNECTION_STRING}"

# Step 7: Configure firewall rules
az redis firewall-rules create \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --rule-name "AllowVNet" \
  --start-ip "10.0.0.1" \
  --end-ip "10.0.255.254"

# Step 8: Enable diagnostics
az monitor diagnostic-settings create \
  --name "redis-diagnostics" \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Cache/redis/${REDIS_CACHE}" \
  --workspace "${LOG_ANALYTICS}" \
  --logs '[{"category":"ConnectedClientList","enabled":true},{"category":"AllLogs","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]'

# Step 9: Update Redis configuration for session storage
az redis update \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --set config='{"maxmemory-policy":"allkeys-lru"}'

# Step 10: Create diagnostic test data
cat > /tmp/redis_test.json <<EOF
{
  "endpoint": "${REDIS_ENDPOINT}",
  "port": ${REDIS_PORT},
  "test_keys": [
    "session:user:123",
    "cache:product:456",
    "queue:notifications"
  ]
}
EOF

echo ""
echo "=========================================="
echo "Redis Cache Created: ${REDIS_CACHE}"
echo "Endpoint: ${REDIS_ENDPOINT}"
echo "Port: ${REDIS_PORT}"
echo "Connection String stored in Key Vault"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Redis Cache
az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}"

# Check cache status
az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "provisioningState" -o tsv

# Get cache configuration
az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "minimumTlsVersion" -o tsv

# List firewall rules
az redis firewall-rules list \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Check cache size and memory
az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "replicasPerMaster" -o tsv

# Verify Key Vault
az keyvault show --name "${KEYVAULT}"

# List secrets
az keyvault secret list --vault-name "${KEYVAULT}" --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Scale Redis cache to Premium tier
az redis update \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku Premium \
  --vm-size p1

# Operation 2: Enable persistence (RDB)
az redis patch-schedule create \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --schedule-entries '{\"scheduleEntries\":[{\"dayOfWeek\":\"Daily\",\"maintenanceWindow\":\"PT5H\",\"startHourUtc\":2,\"rdbBackupFrequency\":\"60\"}]}'

# Operation 3: Monitor cache metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Cache/redis/${REDIS_CACHE}" \
  --metric "CacheHits" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 4: Get cache statistics
az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "{Sku:sku.name, Size:sku.capacity, Family:sku.family}" -o table

# Operation 5: Check connected clients
echo "To check connected clients, query Redis directly with:"
echo "redis-cli -h ${REDIS_ENDPOINT} -p ${REDIS_PORT} -a ${REDIS_PRIMARY_KEY} --tls CLIENT LIST"

# Operation 6: Regenerate access keys
az redis regenerate-keys \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --key-type Primary

# Operation 7: Export cache for backup
echo "To export cache data:"
echo "Redis export is available in Premium tier with RDB snapshots"

# Operation 8: Monitor memory usage
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Cache/redis/${REDIS_CACHE}" \
  --metric "UsedMemory" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 9: Check eviction policy
az redis show \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "config.maxmemory_policy" -o tsv

# Operation 10: List all backups (Premium tier)
az redis backup list \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
  --output table 2>/dev/null || echo "Backups only available in Premium tier"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete Redis cache
az redis delete \
  --name "${REDIS_CACHE}" \
  --resource-group "${RESOURCE_GROUP}" \
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
rm -rf /tmp/redis_test.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-db-redis-${UNIQUE_ID}-rg`
- Redis Cache: `azurehaymaker-redis-${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- Log Analytics: `azurehaymaker-logs-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Cache for Redis Overview](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-overview)
- [Redis Tiers and Sizing](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-planning-faq)
- [Persistence in Redis](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-persistence)
- [Redis Security](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-authentication)
- [Redis CLI Reference](https://redis.io/docs/manual/client-side-caching/)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI handles Redis cache provisioning and configuration effectively. Direct Redis commands can be used for operational tasks via redis-cli.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8 hours (with scaling, monitoring, and key management)
- **Cleanup**: 5 minutes

---

## Notes
- Standard tier is cost-effective for session and cache storage
- Premium tier adds persistence and clustering
- Data encryption in transit with TLS
- Multi-zone redundancy for high availability
- All operations scoped to single tenant and subscription
- Supports LRU and LFU eviction policies
- Connection pooling recommended for application use
