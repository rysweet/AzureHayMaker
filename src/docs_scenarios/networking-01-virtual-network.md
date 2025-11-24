# Scenario: Basic Virtual Network with Subnets and Network Security

## Technology Area
Networking

## Company Profile
- **Company Size**: Small startup
- **Industry**: Technology / SaaS
- **Use Case**: Establish a secure foundation network infrastructure with isolated subnets for frontend and backend services

## Scenario Description
Deploy a foundational Azure Virtual Network with multiple subnets, configure network security groups with inbound and outbound rules, and implement route tables. This scenario covers VNet provisioning, subnet segmentation, network security policies, and traffic management for a multi-tier application architecture.

## Azure Services Used
- Azure Virtual Network
- Azure Subnets
- Azure Network Security Groups
- Azure Route Tables
- Azure Network Interface (for validation)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Basic understanding of IP addressing and CIDR notation

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-networking-${UNIQUE_ID}-rg"
LOCATION="eastus"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
FRONTEND_SUBNET="azurehaymaker-frontend-${UNIQUE_ID}"
BACKEND_SUBNET="azurehaymaker-backend-${UNIQUE_ID}"
DATABASE_SUBNET="azurehaymaker-database-${UNIQUE_ID}"
FRONTEND_NSG="azurehaymaker-frontend-nsg-${UNIQUE_ID}"
BACKEND_NSG="azurehaymaker-backend-nsg-${UNIQUE_ID}"
DATABASE_NSG="azurehaymaker-database-nsg-${UNIQUE_ID}"
ROUTE_TABLE="azurehaymaker-routes-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=networking-virtual-network Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Virtual Network with address space 10.0.0.0/16
az network vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --address-prefix 10.0.0.0/16 \
  --tags ${TAGS}

# Step 3: Create Frontend Subnet (10.0.1.0/24)
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${FRONTEND_SUBNET}" \
  --address-prefix 10.0.1.0/24

# Step 4: Create Backend Subnet (10.0.2.0/24)
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${BACKEND_SUBNET}" \
  --address-prefix 10.0.2.0/24

# Step 5: Create Database Subnet (10.0.3.0/24)
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${DATABASE_SUBNET}" \
  --address-prefix 10.0.3.0/24

# Step 6: Create Frontend Network Security Group
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${FRONTEND_NSG}" \
  --tags ${TAGS}

# Step 7: Add Frontend NSG rules (allow HTTP, HTTPS from internet)
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${FRONTEND_NSG}" \
  --name "allow-http" \
  --priority 1000 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 80 \
  --access Allow \
  --protocol Tcp

az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${FRONTEND_NSG}" \
  --name "allow-https" \
  --priority 1001 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 443 \
  --access Allow \
  --protocol Tcp

# Step 8: Create Backend Network Security Group
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${BACKEND_NSG}" \
  --tags ${TAGS}

# Step 9: Add Backend NSG rules (allow from frontend only)
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${BACKEND_NSG}" \
  --name "allow-from-frontend" \
  --priority 1000 \
  --source-address-prefixes "10.0.1.0/24" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 8080 8443 \
  --access Allow \
  --protocol Tcp

# Step 10: Create Database Network Security Group
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${DATABASE_NSG}" \
  --tags ${TAGS}

# Step 11: Add Database NSG rules (allow from backend only)
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${DATABASE_NSG}" \
  --name "allow-from-backend" \
  --priority 1000 \
  --source-address-prefixes "10.0.2.0/24" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 5432 3306 1433 \
  --access Allow \
  --protocol Tcp

# Step 12: Associate NSGs with subnets
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${FRONTEND_SUBNET}" \
  --network-security-group "${FRONTEND_NSG}"

az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${BACKEND_SUBNET}" \
  --network-security-group "${BACKEND_NSG}"

az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${DATABASE_SUBNET}" \
  --network-security-group "${DATABASE_NSG}"

# Step 13: Create Route Table
az network route-table create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${ROUTE_TABLE}" \
  --tags ${TAGS}

# Step 14: Associate Route Table with Backend subnet
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${BACKEND_SUBNET}" \
  --route-table "${ROUTE_TABLE}"
```

### Validation
```bash
# Verify Virtual Network
az network vnet show --resource-group "${RESOURCE_GROUP}" --name "${VNET_NAME}"

# List all subnets
az network vnet subnet list --resource-group "${RESOURCE_GROUP}" --vnet-name "${VNET_NAME}" --output table

# Verify Frontend NSG rules
az network nsg rule list --resource-group "${RESOURCE_GROUP}" --nsg-name "${FRONTEND_NSG}" --output table

# Verify Backend NSG rules
az network nsg rule list --resource-group "${RESOURCE_GROUP}" --nsg-name "${BACKEND_NSG}" --output table

# Verify Database NSG rules
az network nsg rule list --resource-group "${RESOURCE_GROUP}" --nsg-name "${DATABASE_NSG}" --output table

# Check Route Table association
az network vnet subnet show --resource-group "${RESOURCE_GROUP}" --vnet-name "${VNET_NAME}" --name "${BACKEND_SUBNET}" --query "routeTable"

# List all resources in resource group
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create additional security rule for outbound traffic on Frontend
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${FRONTEND_NSG}" \
  --name "allow-outbound-backend" \
  --priority 1002 \
  --direction Outbound \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "10.0.2.0/24" \
  --destination-port-ranges "*" \
  --access Allow \
  --protocol "*"

# Operation 2: Add custom route in route table (simulate routing to firewall)
az network route-table route create \
  --resource-group "${RESOURCE_GROUP}" \
  --route-table-name "${ROUTE_TABLE}" \
  --name "route-to-monitoring" \
  --address-prefix "10.0.4.0/24" \
  --next-hop-type VirtualAppliance \
  --next-hop-ip-address "10.0.2.1"

# Operation 3: List all Network Security Groups
az network nsg list --resource-group "${RESOURCE_GROUP}" --output table

# Operation 4: Get detailed Network Security Group information
az network nsg show --resource-group "${RESOURCE_GROUP}" --name "${FRONTEND_NSG}"

# Operation 5: Check effective network security rules on Frontend subnet
az network vnet subnet list-available-delegations --resource-group "${RESOURCE_GROUP}" --vnet-name "${VNET_NAME}" --subnet-name "${FRONTEND_SUBNET}"

# Operation 6: View all routes in Route Table
az network route-table route list --resource-group "${RESOURCE_GROUP}" --route-table-name "${ROUTE_TABLE}" --output table

# Operation 7: Enable flow logs for monitoring (create storage account first)
STORAGE_ACCOUNT="azmkstorage${UNIQUE_ID}"
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --tags ${TAGS}

# Operation 8: Create Network Watcher (if not exists)
az network watcher configure --resource-group "${RESOURCE_GROUP}" --enabled true

# Operation 9: Get VNet configuration summary
az network vnet show --resource-group "${RESOURCE_GROUP}" --name "${VNET_NAME}" --query "{name: name, addressSpace: addressSpace, subnets: subnets[*].name}" -o json

# Operation 10: Update NSG rule - modify Backend rule to allow SSH access
az network nsg rule update \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${BACKEND_NSG}" \
  --name "allow-from-frontend" \
  --destination-port-ranges "22" "8080" "8443"

# Operation 11: Add rule to deny specific traffic on Database NSG
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${DATABASE_NSG}" \
  --name "deny-all-inbound" \
  --priority 4096 \
  --direction Inbound \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges "*" \
  --access Deny \
  --protocol "*"

# Operation 12: List VNet peering (if any)
az network vnet peering list --resource-group "${RESOURCE_GROUP}" --vnet-name "${VNET_NAME}" --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group (includes VNet, subnets, NSGs, route tables, storage)
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 2: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 120

# Step 3: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 4: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-networking-${UNIQUE_ID}-rg`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Frontend Subnet: `azurehaymaker-frontend-${UNIQUE_ID}`
- Backend Subnet: `azurehaymaker-backend-${UNIQUE_ID}`
- Database Subnet: `azurehaymaker-database-${UNIQUE_ID}`
- Frontend NSG: `azurehaymaker-frontend-nsg-${UNIQUE_ID}`
- Backend NSG: `azurehaymaker-backend-nsg-${UNIQUE_ID}`
- Database NSG: `azurehaymaker-database-nsg-${UNIQUE_ID}`
- Route Table: `azurehaymaker-routes-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Virtual Network Overview](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-overview)
- [Subnets and Address Spaces](https://learn.microsoft.com/en-us/azure/virtual-network/concepts-and-best-practices)
- [Network Security Groups](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview)
- [Route Tables](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-udr-overview)
- [Azure CLI Network Commands](https://learn.microsoft.com/en-us/cli/azure/network)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive network management capabilities with straightforward commands for VNet creation, subnet configuration, and security group management. The direct command approach is ideal for foundational network infrastructure scenarios.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (with monitoring, updates, and traffic management)
- **Cleanup**: 5-10 minutes

---

## Notes
- Virtual Network uses standard address space 10.0.0.0/16 with class C subnets
- Network Security Groups follow the principle of least privilege (restrictive rules)
- Subnets are logically segregated by tier (frontend, backend, database)
- Route Tables enable custom routing for advanced network scenarios
- All operations scoped to single tenant and subscription
- NSG rules can be easily updated for changes to security policies
- Storage account created for potential flow logs monitoring
