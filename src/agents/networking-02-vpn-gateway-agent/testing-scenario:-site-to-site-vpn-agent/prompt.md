# Scenario: Site-to-Site VPN Gateway Connection

## Technology Area
Networking

## Company Profile
- **Company Size**: Mid-size enterprise
- **Industry**: Finance / Professional Services
- **Use Case**: Establish secure site-to-site VPN connectivity between on-premises network and Azure

## Scenario Description
Deploy an Azure VPN Gateway configured for site-to-site VPN connectivity to simulate an on-premises network connection. This scenario covers gateway provisioning, IPsec configuration, connection management, and traffic routing through encrypted tunnels.

## Azure Services Used
- Azure VPN Gateway
- Azure Virtual Network
- Azure Public IP
- Azure Local Network Gateway
- Azure Connection (VPN)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Understanding of VPN concepts and IPsec protocols

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-vpn-${UNIQUE_ID}-rg"
LOCATION="eastus"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
GATEWAY_SUBNET="GatewaySubnet"
APPLICATION_SUBNET="azurehaymaker-app-${UNIQUE_ID}"
VPN_GATEWAY="azurehaymaker-vpn-gw-${UNIQUE_ID}"
VPN_PUBLIC_IP="azurehaymaker-vpn-pip-${UNIQUE_ID}"
LOCAL_GATEWAY="azurehaymaker-local-gw-${UNIQUE_ID}"
VPN_CONNECTION="azurehaymaker-vpn-conn-${UNIQUE_ID}"

# Simulated on-premises network
LOCAL_NETWORK_PREFIX="192.168.0.0/16"
LOCAL_GATEWAY_IP="203.0.113.12"  # Simulated public IP
SHARED_KEY="AzureHayMaker2024Secure"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=networking-vpn-gateway Owner=AzureHayMaker"
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

# Step 3: Create Gateway Subnet (required for VPN Gateway)
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${GATEWAY_SUBNET}" \
  --address-prefix 10.0.255.0/27

# Step 4: Create application subnet for testing
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${APPLICATION_SUBNET}" \
  --address-prefix 10.0.1.0/24

# Step 5: Create public IP for VPN Gateway
az network public-ip create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_PUBLIC_IP}" \
  --allocation-method Static \
  --sku Standard \
  --tags ${TAGS}

# Step 6: Create VPN Gateway (this may take 15-20 minutes)
az network vnet-gateway create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_GATEWAY}" \
  --public-ip-addresses "${VPN_PUBLIC_IP}" \
  --vnet "${VNET_NAME}" \
  --gateway-type Vpn \
  --vpn-type RouteBased \
  --sku VpnGw1 \
  --tags ${TAGS} \
  --no-wait

# Wait for gateway creation
echo "Waiting for VPN Gateway creation (this typically takes 15-20 minutes)..."
sleep 180

# Step 7: Get VPN Gateway public IP
VPN_GATEWAY_IP=$(az network public-ip show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_PUBLIC_IP}" \
  --query ipAddress -o tsv)

echo "VPN Gateway Public IP: ${VPN_GATEWAY_IP}"

# Step 8: Create Local Network Gateway (represents on-premises network)
az network local-gateway create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${LOCAL_GATEWAY}" \
  --gateway-ip-address "${LOCAL_GATEWAY_IP}" \
  --local-address-prefixes "${LOCAL_NETWORK_PREFIX}" \
  --tags ${TAGS}

# Step 9: Create VPN Connection
az network vpn-connection create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_CONNECTION}" \
  --vnet-gateway1 "${VPN_GATEWAY}" \
  --local-gateway2 "${LOCAL_GATEWAY}" \
  --shared-key "${SHARED_KEY}" \
  --tags ${TAGS}

# Step 10: Configure IPsec policies (optional but recommended)
az network vpn-connection ipsec-policy add \
  --resource-group "${RESOURCE_GROUP}" \
  --connection-name "${VPN_CONNECTION}" \
  --dh-group DHGroup14 \
  --ike-encryption AES256 \
  --ike-integrity SHA256 \
  --ipsec-encryption AES256 \
  --ipsec-integrity SHA256 \
  --pfs-group PFS2048 \
  --sa-lifetime 27000

# Step 11: Verify connection status
az network vpn-connection show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_CONNECTION}" \
  --query "connectionStatus"

# Step 12: Create Network Security Group for application subnet
NSG_NAME="azurehaymaker-vpn-nsg-${UNIQUE_ID}"
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_NAME}" \
  --tags ${TAGS}

# Step 13: Add NSG rules for VPN traffic
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-from-onpremises" \
  --priority 1000 \
  --source-address-prefixes "${LOCAL_NETWORK_PREFIX}" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges "*" \
  --access Allow \
  --protocol "*"

# Step 14: Associate NSG with application subnet
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${APPLICATION_SUBNET}" \
  --network-security-group "${NSG_NAME}"
```

### Validation
```bash
# Verify VPN Gateway
az network vnet-gateway show --resource-group "${RESOURCE_GROUP}" --name "${VPN_GATEWAY}"

# Verify VPN Gateway public IP
az network public-ip show --resource-group "${RESOURCE_GROUP}" --name "${VPN_PUBLIC_IP}"

# Verify Local Network Gateway
az network local-gateway show --resource-group "${RESOURCE_GROUP}" --name "${LOCAL_GATEWAY}"

# Check VPN Connection status
az network vpn-connection show --resource-group "${RESOURCE_GROUP}" --name "${VPN_CONNECTION}" --query "{name: name, connectionStatus: connectionStatus, provisioningState: provisioningState}"

# List all VPN connections
az network vpn-connection list --resource-group "${RESOURCE_GROUP}" --output table

# Get IPsec policies
az network vpn-connection ipsec-policy list --resource-group "${RESOURCE_GROUP}" --connection-name "${VPN_CONNECTION}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Check VPN Connection statistics
az network vpn-connection get-ikesa \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_CONNECTION}"

# Operation 2: Reset VPN Gateway (may be needed for troubleshooting)
# Note: This operation temporarily disconnects VPN connections
# az network vnet-gateway reset --resource-group "${RESOURCE_GROUP}" --name "${VPN_GATEWAY}" --no-wait

# Operation 3: View VPN Gateway configuration
az network vnet-gateway show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_GATEWAY}" \
  --query "{name: name, type: type, vpnType: vpnType, gatewayType: gatewayType, skuName: sku.name}"

# Operation 4: List all subnets in VNet
az network vnet subnet list \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --output table

# Operation 5: Update VPN Connection shared key (change encryption key)
az network vpn-connection shared-key update \
  --resource-group "${RESOURCE_GROUP}" \
  --connection-name "${VPN_CONNECTION}" \
  --value "NewAzureHayMaker2024Key"

# Operation 6: Get VPN Gateway supported VPN protocols
az network vnet-gateway supported-vpn-devices \
  --query "[].supportedVpnDevices" -o json

# Operation 7: Monitor connection metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/connections/${VPN_CONNECTION}" \
  --metric "BytesIn BytesOut Packets" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 8: Create VPN client configuration (for point-to-site - simulated)
az network vnet-gateway vpn-client generate \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_GATEWAY}" \
  --processor-architecture Amd64 \
  --authentication-method EAP \
  --output table

# Operation 9: Update NSG to add additional allowed ports
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-rdp-from-onpremises" \
  --priority 1001 \
  --source-address-prefixes "${LOCAL_NETWORK_PREFIX}" \
  --source-port-ranges "*" \
  --destination-address-prefixes "10.0.1.0/24" \
  --destination-port-ranges "3389" \
  --access Allow \
  --protocol Tcp

# Operation 10: Verify routing table configuration
az network route-table list --resource-group "${RESOURCE_GROUP}" --output table

# Operation 11: Check gateway connectivity status
az network vpn-connection show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_CONNECTION}" \
  --query "{connectionStatus: connectionStatus, egressBytesTransferred: egressBytesTransferred, ingressBytesTransferred: ingressBytesTransferred}"

# Operation 12: List Local Network Gateway address prefixes
az network local-gateway show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${LOCAL_GATEWAY}" \
  --query "localNetworkAddressSpace.addressPrefixes"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete VPN Connection
az network vpn-connection delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_CONNECTION}" \
  --yes \
  --no-wait

# Step 2: Delete VPN Gateway (this may take several minutes)
az network vnet-gateway delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VPN_GATEWAY}" \
  --yes \
  --no-wait

# Step 3: Wait for gateway deletion
echo "Waiting for VPN Gateway deletion..."
sleep 180

# Step 4: Delete Local Network Gateway
az network local-gateway delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${LOCAL_GATEWAY}" \
  --yes

# Step 5: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 6: Verify deletion
echo "Waiting for resource group deletion..."
sleep 120

az group exists --name "${RESOURCE_GROUP}"

# Step 7: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-vpn-${UNIQUE_ID}-rg`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- VPN Gateway: `azurehaymaker-vpn-gw-${UNIQUE_ID}`
- VPN Gateway Public IP: `azurehaymaker-vpn-pip-${UNIQUE_ID}`
- Local Network Gateway: `azurehaymaker-local-gw-${UNIQUE_ID}`
- VPN Connection: `azurehaymaker-vpn-conn-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure VPN Gateway Overview](https://learn.microsoft.com/en-us/azure/vpn-gateway/vpn-gateway-about-vpngateways)
- [Site-to-Site VPN Configuration](https://learn.microsoft.com/en-us/azure/vpn-gateway/vpn-gateway-howto-site-to-site-resource-manager-cli)
- [IPsec Policies](https://learn.microsoft.com/en-us/azure/vpn-gateway/vpn-gateway-ipsecikepolicy-overview)
- [VPN Gateway CLI Reference](https://learn.microsoft.com/en-us/cli/azure/network/vnet-gateway)
- [Local Network Gateway](https://learn.microsoft.com/en-us/azure/vpn-gateway/vpn-gateway-tutorial-vpnconnection-cli)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive VPN Gateway management with all necessary commands for configuration, monitoring, and troubleshooting. Direct CLI commands enable fine-grained control over IPsec policies and connection parameters.

---

## Estimated Duration
- **Deployment**: 25-30 minutes (includes gateway provisioning time)
- **Operations Phase**: 8+ hours (with monitoring and maintenance)
- **Cleanup**: 15-20 minutes (includes gateway deletion)

---

## Notes
- VPN Gateway provisioning takes 15-20 minutes; operations wait accordingly
- RouteBased VPN supports dynamic routing with BGP
- IPsec policies configured for strong encryption (AES256)
- Local Network Gateway simulates on-premises network with 192.168.0.0/16
- Shared key is stored securely; update periodically in production
- Connection status may show "NotConnected" in lab environment without actual on-premises VPN device
- All operations scoped to single tenant and subscription
- Gateway SKU (VpnGw1) supports up to 128 concurrent connections
