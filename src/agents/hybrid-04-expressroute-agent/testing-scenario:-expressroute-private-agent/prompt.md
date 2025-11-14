# Scenario: ExpressRoute Private Connectivity

## Technology Area
Hybrid+Multicloud

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Financial Services
- **Use Case**: Establish dedicated private connection from on-premises to Azure

## Scenario Description
Deploy Azure ExpressRoute to create a private, dedicated network connection between on-premises infrastructure and Azure. Configure peering, monitor circuit health, and implement traffic management.

## Azure Services Used
- Azure ExpressRoute (dedicated connectivity)
- Azure Virtual Network (cloud network)
- Azure Route Server (dynamic routing)
- Azure Monitor (health monitoring)

## Prerequisites
- Azure subscription with appropriate permissions
- Azure CLI installed
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-hybrid-expressroute-${UNIQUE_ID}-rg"
LOCATION="eastus"
EXPRESSROUTE_CIRCUIT="azurehaymaker-er-${UNIQUE_ID}"
EXPRESSROUTE_GATEWAY="azurehaymaker-ergw-${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=hybrid-expressroute Owner=AzureHayMaker"
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
  --subnet-name "gateway-subnet" \
  --subnet-prefixes "10.0.0.0/27" \
  --tags ${TAGS}

# Step 3: Create Key Vault for storing secrets
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 4: Create ExpressRoute circuit
az network express-route create \
  --name "${EXPRESSROUTE_CIRCUIT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --bandwidth 50 \
  --provider "Equinix" \
  --peering-location "San Jose" \
  --sku-family MeteredData \
  --sku-tier Standard \
  --tags ${TAGS}

# Step 5: Get circuit provisioning key
CIRCUIT_KEY=$(az network express-route show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${EXPRESSROUTE_CIRCUIT}" \
  --query "serviceKey" -o tsv)

# Store in Key Vault
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "expressroute-service-key" \
  --value "${CIRCUIT_KEY}"

# Step 6: Create ExpressRoute gateway
az network vnet-gateway create \
  --name "${EXPRESSROUTE_GATEWAY}" \
  --location "${LOCATION}" \
  --public-ip-address-allocation static \
  --vnet "${VNET_NAME}" \
  --gateway-type ExpressRoute \
  --sku Standard \
  --resource-group "${RESOURCE_GROUP}" \
  --tags ${TAGS}

# Step 7: Configure private peering
cat > /tmp/peering_config.json <<EOF
{
  "peeringConfiguration": {
    "peeringType": "AzurePrivatePeering",
    "primaryPeerAddressPrefix": "192.168.1.0/30",
    "secondaryPeerAddressPrefix": "192.168.2.0/30",
    "vlanId": 100,
    "customerASN": 65000,
    "routerASN": 12076
  }
}
EOF

# Step 8: Create Azure peering
az network express-route peering create \
  --circuit-name "${EXPRESSROUTE_CIRCUIT}" \
  --name "AzurePrivatePeering" \
  --peer-asn 65000 \
  --primary-peer-subnet "192.168.1.0/30" \
  --secondary-peer-subnet "192.168.2.0/30" \
  --vlan-id 100 \
  --resource-group "${RESOURCE_GROUP}"

# Step 9: Create gateway connection
GATEWAY_ID=$(az network vnet-gateway show \
  --name "${EXPRESSROUTE_GATEWAY}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "id" -o tsv)

CIRCUIT_ID=$(az network express-route show \
  --name "${EXPRESSROUTE_CIRCUIT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "id" -o tsv)

az network vpn-connection create \
  --name "ExpressRoute-Connection" \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-gateway1 "${EXPRESSROUTE_GATEWAY}" \
  --express-route-circuit2 "${EXPRESSROUTE_CIRCUIT}" \
  --connection-type ExpressRoute \
  --tags ${TAGS}

# Step 10: Create diagnostic settings
az monitor diagnostic-settings create \
  --name "expressroute-diagnostics" \
  --resource "${CIRCUIT_ID}" \
  --logs '[{"category":"ExpressRouteSiteToSiteVpnConnection","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]' 2>/dev/null || echo "Diagnostics will be available after provisioning"

echo ""
echo "=========================================="
echo "ExpressRoute Circuit: ${EXPRESSROUTE_CIRCUIT}"
echo "Service Key: ${CIRCUIT_KEY}"
echo "Gateway: ${EXPRESSROUTE_GATEWAY}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Show ExpressRoute circuit details
az network express-route show \
  --name "${EXPRESSROUTE_CIRCUIT}" \
  --resource-group "${RESOURCE_GROUP}"

# Check circuit provisioning state
az network express-route show \
  --name "${EXPRESSROUTE_CIRCUIT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "circuitProvisioningState" -o tsv

# List peerings
az network express-route peering list \
  --circuit-name "${EXPRESSROUTE_CIRCUIT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Show gateway
az network vnet-gateway show \
  --name "${EXPRESSROUTE_GATEWAY}" \
  --resource-group "${RESOURCE_GROUP}"

# List connections
az network vpn-connection list \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Check Virtual Network
az network vnet show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Monitor circuit status
az network express-route show \
  --name "${EXPRESSROUTE_CIRCUIT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "{ProvisioningState:circuitProvisioningState, ServiceProviderProvisioningState:serviceProviderProvisioningState}" -o table

# Operation 2: Get circuit stats
az network express-route stats show \
  --name "${EXPRESSROUTE_CIRCUIT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --peering-name "AzurePrivatePeering" 2>/dev/null || echo "Stats not yet available"

# Operation 3: Configure Route Server (optional)
cat > /tmp/route_server_config.json <<EOF
{
  "routeServerConfiguration": {
    "name": "route-server-1",
    "asn": 65515,
    "subnetPrefix": "10.0.1.0/27"
  }
}
EOF

# Operation 4: Monitor connection health
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/expressRouteCircuits/${EXPRESSROUTE_CIRCUIT}" \
  --metric "BitsInPerSecond" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ') 2>/dev/null || echo "Metrics not yet available"

# Operation 5: Check BGP sessions
echo "To verify BGP sessions:"
echo "az network express-route peering show --circuit-name ${EXPRESSROUTE_CIRCUIT} --name AzurePrivatePeering --resource-group ${RESOURCE_GROUP}"

# Operation 6: View peering details
az network express-route peering show \
  --circuit-name "${EXPRESSROUTE_CIRCUIT}" \
  --name "AzurePrivatePeering" \
  --resource-group "${RESOURCE_GROUP}" 2>/dev/null || echo "Peering details not available"

# Operation 7: Configure QoS settings
cat > /tmp/qos_config.json <<EOF
{
  "qosConfiguration": {
    "inboundBandwidthMbps": 50,
    "outboundBandwidthMbps": 50,
    "priorityMapping": {
      "businessCritical": 1,
      "important": 2,
      "standard": 3
    }
  }
}
EOF

# Operation 8: Monitor circuit utilization
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/expressRouteCircuits/${EXPRESSROUTE_CIRCUIT}" \
  --metric "BitsOutPerSecond" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ') 2>/dev/null || echo "Metrics not yet available"

# Operation 9: Check ARP table
echo "To check ARP table on-premises:"
echo "show ip arp interface <interface> on service provider edge router"

# Operation 10: Review ExpressRoute activity logs
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[?contains(resourceType, 'expressRouteCircuits')].{Time:eventTimestamp, Event:operationName.localizedValue, Status:status.localizedValue}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete VPN connection
az network vpn-connection delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "ExpressRoute-Connection" \
  --yes

# Step 2: Delete gateway
az network vnet-gateway delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${EXPRESSROUTE_GATEWAY}" \
  --yes

# Step 3: Delete peering
az network express-route peering delete \
  --circuit-name "${EXPRESSROUTE_CIRCUIT}" \
  --name "AzurePrivatePeering" \
  --resource-group "${RESOURCE_GROUP}" \
  --yes 2>/dev/null || true

# Step 4: Delete ExpressRoute circuit
az network express-route delete \
  --name "${EXPRESSROUTE_CIRCUIT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --yes

# Step 5: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 6: Verify deletion
sleep 120
az group exists --name "${RESOURCE_GROUP}"

# Step 7: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 8: Clean up local files
rm -rf /tmp/peering_config.json /tmp/route_server_config.json /tmp/qos_config.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-hybrid-expressroute-${UNIQUE_ID}-rg`
- ExpressRoute Circuit: `azurehaymaker-er-${UNIQUE_ID}`
- Gateway: `azurehaymaker-ergw-${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [ExpressRoute Overview](https://learn.microsoft.com/en-us/azure/expressroute/expressroute-introduction)
- [ExpressRoute Connectivity Models](https://learn.microsoft.com/en-us/azure/expressroute/expressroute-connectivity-models)
- [ExpressRoute Routing](https://learn.microsoft.com/en-us/azure/expressroute/expressroute-routing)
- [ExpressRoute QoS](https://learn.microsoft.com/en-us/azure/expressroute/expressroute-qos)
- [ExpressRoute CLI Reference](https://learn.microsoft.com/en-us/cli/azure/network/express-route)

---

## Automation Tool
**Recommended**: Azure CLI + Terraform

**Rationale**: Azure CLI handles ExpressRoute operations while Terraform manages infrastructure-as-code for reproducible deployments.

---

## Estimated Duration
- **Deployment**: 20-30 minutes (circuit provisioning takes time)
- **Operations Phase**: 8 hours (with monitoring and optimization)
- **Cleanup**: 10-15 minutes

---

## Notes
- ExpressRoute provides dedicated 1, 10, 40, or 100 Gbps bandwidth
- Private peering for direct Azure resource access
- Microsoft peering for Office 365 and Azure services
- Public peering (deprecated) for backward compatibility
- SLA provides 99.95% uptime for standard circuits
- All operations scoped to single tenant and subscription
- Redundancy recommended with multiple ExpressRoute circuits
