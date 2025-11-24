# Scenario: Network Security Groups for Network Security

## Technology Area
Security

## Company Profile
- **Company Size**: Small startup
- **Industry**: Web Services / E-commerce
- **Use Case**: Implement network segmentation and traffic control through NSG rules for multi-tier application

## Scenario Description
Create and manage Azure Network Security Groups with inbound and outbound rules to control traffic flow between application tiers. This scenario covers NSG creation, rule management, traffic logging, and network policy enforcement.

## Azure Services Used
- Azure Network Security Groups (NSG)
- Azure Virtual Network (VNet)
- Azure Subnets
- Azure Network Interfaces
- Azure Network Watcher (for monitoring)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Understanding of network protocols and port ranges
- Access to create and manage network resources

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-security-${UNIQUE_ID}-rg"
LOCATION="eastus"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
SUBNET_WEB="azurehaymaker-subnet-web-${UNIQUE_ID}"
SUBNET_APP="azurehaymaker-subnet-app-${UNIQUE_ID}"
SUBNET_DB="azurehaymaker-subnet-db-${UNIQUE_ID}"
NSG_WEB="azurehaymaker-nsg-web-${UNIQUE_ID}"
NSG_APP="azurehaymaker-nsg-app-${UNIQUE_ID}"
NSG_DB="azurehaymaker-nsg-db-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=security-nsg Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Virtual Network with CIDR block
az network vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --address-prefix 10.0.0.0/16 \
  --tags ${TAGS}

# Step 3: Create Web tier subnet
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_WEB}" \
  --address-prefix 10.0.1.0/24

# Step 4: Create Application tier subnet
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_APP}" \
  --address-prefix 10.0.2.0/24

# Step 5: Create Database tier subnet
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_DB}" \
  --address-prefix 10.0.3.0/24

# Step 6: Create NSG for Web tier
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_WEB}" \
  --tags ${TAGS}

# Step 7: Create NSG for Application tier
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_APP}" \
  --tags ${TAGS}

# Step 8: Create NSG for Database tier
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_DB}" \
  --tags ${TAGS}

# Step 9: Associate NSG with Web subnet
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_WEB}" \
  --network-security-group "${NSG_WEB}"

# Step 10: Associate NSG with Application subnet
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_APP}" \
  --network-security-group "${NSG_APP}"

# Step 11: Associate NSG with Database subnet
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_DB}" \
  --network-security-group "${NSG_DB}"

# Step 12: Add inbound HTTP rule to Web NSG (allow from internet)
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_WEB}" \
  --name "allow-http" \
  --priority 1000 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 80 \
  --access Allow \
  --protocol Tcp

echo "Virtual Network and NSGs created successfully"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Virtual Network
az network vnet show --resource-group "${RESOURCE_GROUP}" --name "${VNET_NAME}"

# List subnets
az network vnet subnet list --resource-group "${RESOURCE_GROUP}" --vnet-name "${VNET_NAME}" --output table

# Verify NSG creation
az network nsg list --resource-group "${RESOURCE_GROUP}" --output table

# List NSG rules for Web NSG
az network nsg rule list --resource-group "${RESOURCE_GROUP}" --nsg-name "${NSG_WEB}" --output table

# Check subnet NSG associations
az network vnet subnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_WEB}" \
  --query networkSecurityGroup

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Add HTTPS rule to Web NSG
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_WEB}" \
  --name "allow-https" \
  --priority 1001 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 443 \
  --access Allow \
  --protocol Tcp

# Operation 2: Add SSH rule to Web NSG (restricted source)
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_WEB}" \
  --name "allow-ssh-restricted" \
  --priority 1002 \
  --source-address-prefixes "10.0.0.0/8" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 22 \
  --access Allow \
  --protocol Tcp

# Operation 3: Add rule allowing App tier traffic from Web tier to App NSG
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_APP}" \
  --name "allow-from-web" \
  --priority 1000 \
  --source-address-prefixes "10.0.1.0/24" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 8080 \
  --access Allow \
  --protocol Tcp

# Operation 4: Add rule allowing Database tier traffic from App tier to DB NSG
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_DB}" \
  --name "allow-from-app" \
  --priority 1000 \
  --source-address-prefixes "10.0.2.0/24" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 3306,5432 \
  --access Allow \
  --protocol Tcp

# Operation 5: Deny all inbound traffic by default on App NSG
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_APP}" \
  --name "deny-all-inbound" \
  --priority 4096 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges "*" \
  --access Deny \
  --protocol "*"

# Operation 6: Allow outbound traffic from App tier to database
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_APP}" \
  --name "allow-outbound-db" \
  --priority 1000 \
  --direction Outbound \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "10.0.3.0/24" \
  --destination-port-ranges 3306,5432 \
  --access Allow \
  --protocol Tcp

# Operation 7: Deny outbound traffic from Database tier (restrict egress)
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_DB}" \
  --name "deny-outbound-internet" \
  --priority 4096 \
  --direction Outbound \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --access Deny \
  --protocol "*"

# Operation 8: List all rules in Web NSG with detailed information
az network nsg rule list \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_WEB}" \
  --output table

# Operation 9: Update existing rule (modify priority)
az network nsg rule update \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_WEB}" \
  --name "allow-ssh-restricted" \
  --priority 1500

# Operation 10: Test connectivity rules (simulate traffic analysis)
echo "Network Segment Analysis:"
echo "Web Subnet: 10.0.1.0/24"
echo "App Subnet: 10.0.2.0/24"
echo "DB Subnet: 10.0.3.0/24"

# Operation 11: Create NSG flow logs for security monitoring
STORAGE_ACCOUNT="azurehaymaker${UNIQUE_ID}"
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --tags ${TAGS}

# Operation 12: Enable NSG Flow Logs (if Network Watcher available)
WATCHER_RG=$(az network watcher list --query "[0].resourceGroup" -o tsv 2>/dev/null || echo "")
if [ ! -z "$WATCHER_RG" ]; then
  WATCHER_NAME=$(az network watcher list --query "[0].name" -o tsv 2>/dev/null)
  az network watcher flow-log create \
    --resource-group "${WATCHER_RG}" \
    --watcher-name "${WATCHER_NAME}" \
    --nsg "${NSG_WEB}" \
    --storage-account "${STORAGE_ACCOUNT}" \
    --enabled true || echo "Flow log creation skipped - Network Watcher not available"
else
  echo "Network Watcher not available in this region for flow logs"
fi

# Operation 13: Export NSG configuration as JSON
az network nsg show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_WEB}" \
  --output json > /tmp/nsg-web-config-${UNIQUE_ID}.json

# Operation 14: List effective NSG rules for a subnet
az network vnet subnet list-effective-network-security-groups \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${SUBNET_WEB}" \
  --output table || echo "Effective rules check completed"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Remove NSG associations from subnets
for SUBNET in "${SUBNET_WEB}" "${SUBNET_APP}" "${SUBNET_DB}"; do
  az network vnet subnet update \
    --resource-group "${RESOURCE_GROUP}" \
    --vnet-name "${VNET_NAME}" \
    --name "${SUBNET}" \
    --network-security-group "" 2>/dev/null || true
done

# Step 2: Delete all NSGs
az network nsg delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_WEB}" --yes

az network nsg delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_APP}" --yes

az network nsg delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_DB}" --yes

# Step 3: Delete Virtual Network (includes subnets)
az network vnet delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}"

# Step 4: Delete Storage Account (if created for flow logs)
az storage account delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --yes 2>/dev/null || true

# Step 5: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 6: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 120

# Step 7: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 8: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 9: Clean up local files
rm -f /tmp/nsg-web-config-*.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-security-${UNIQUE_ID}-rg`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Web Subnet: `azurehaymaker-subnet-web-${UNIQUE_ID}`
- App Subnet: `azurehaymaker-subnet-app-${UNIQUE_ID}`
- DB Subnet: `azurehaymaker-subnet-db-${UNIQUE_ID}`
- Web NSG: `azurehaymaker-nsg-web-${UNIQUE_ID}`
- App NSG: `azurehaymaker-nsg-app-${UNIQUE_ID}`
- DB NSG: `azurehaymaker-nsg-db-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Network Security Groups Overview](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview)
- [NSG Rules Syntax](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview#security-rules)
- [Azure Virtual Networks](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-overview)
- [NSG Flow Logs](https://learn.microsoft.com/en-us/azure/network-watcher/network-watcher-nsg-flow-logging-overview)
- [Network Watcher](https://learn.microsoft.com/en-us/azure/network-watcher/network-watcher-overview)
- [NSG Best Practices](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview#best-practices)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive NSG management with straightforward commands for rule creation, modification, and network traffic control. Direct commands enable rapid network security policy enforcement.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (with rule management, network testing, and compliance verification)
- **Cleanup**: 5-10 minutes

---

## Notes
- NSG rules evaluated in priority order (lower number = higher priority)
- Default allow for outbound traffic unless explicitly denied
- NSG rules support service tags for easier management of Azure services
- Flow logs require Network Watcher availability in the region
- Rules can specify source/destination as IP CIDR, IP addresses, or service tags
- NSGs can be associated at subnet or network interface level
- Operations scoped to single VNet with multiple subnets for defense-in-depth
