# Scenario: Application Gateway with Web Application Firewall

## Technology Area
Networking

## Company Profile
- **Company Size**: Mid-size to large enterprise
- **Industry**: Finance / Healthcare / E-commerce
- **Use Case**: Secure application delivery with advanced routing, SSL/TLS termination, and threat protection

## Scenario Description
Deploy an Azure Application Gateway configured with Web Application Firewall (WAF), backend pools with multiple instances, path-based routing rules, and HTTPS listener configuration. This scenario covers gateway provisioning, WAF policies, health probes, routing rules, and SSL/TLS management.

## Azure Services Used
- Azure Application Gateway with WAF
- Azure Virtual Network
- Azure Public IP
- Azure Virtual Machines
- Azure Network Security Groups
- Azure Key Vault (optional for certificates)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Understanding of HTTP/HTTPS routing and firewall concepts

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-appgw-${UNIQUE_ID}-rg"
LOCATION="eastus"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
GATEWAY_SUBNET="azurehaymaker-gateway-${UNIQUE_ID}"
BACKEND_SUBNET="azurehaymaker-backend-${UNIQUE_ID}"
APP_GW_NAME="azurehaymaker-appgw-${UNIQUE_ID}"
APP_GW_IP="azurehaymaker-appgw-pip-${UNIQUE_ID}"
BACKEND_POOL="azurehaymaker-backend-pool-${UNIQUE_ID}"
HEALTH_PROBE="azurehaymaker-health-probe-${UNIQUE_ID}"
HTTP_SETTINGS="azurehaymaker-http-settings-${UNIQUE_ID}"
LISTENER_HTTP="azurehaymaker-listener-http-${UNIQUE_ID}"
ROUTING_RULE="azurehaymaker-routing-rule-${UNIQUE_ID}"
WAF_POLICY="azurehaymaker-waf-policy-${UNIQUE_ID}"
NSG_NAME="azurehaymaker-appgw-nsg-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=networking-application-gateway Owner=AzureHayMaker"
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

# Step 3: Create Gateway Subnet (required for Application Gateway)
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${GATEWAY_SUBNET}" \
  --address-prefix 10.0.1.0/24

# Step 4: Create Backend Subnet for virtual machines
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${BACKEND_SUBNET}" \
  --address-prefix 10.0.2.0/24

# Step 5: Create Network Security Group for gateway
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_NAME}" \
  --tags ${TAGS}

# Step 6: Add NSG rules for Application Gateway
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-gatewaymanager" \
  --priority 1000 \
  --source-address-prefixes "GatewayManager" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges "65200-65535" \
  --access Allow \
  --protocol Tcp

az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-http-https" \
  --priority 1001 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 80 443 \
  --access Allow \
  --protocol Tcp

# Step 7: Associate NSG with gateway subnet
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${GATEWAY_SUBNET}" \
  --network-security-group "${NSG_NAME}"

# Step 8: Create public IP for Application Gateway
az network public-ip create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_GW_IP}" \
  --allocation-method Static \
  --sku Standard \
  --tags ${TAGS}

# Step 9: Create Application Gateway
az network application-gateway create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_GW_NAME}" \
  --location "${LOCATION}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${GATEWAY_SUBNET}" \
  --public-ip-address "${APP_GW_IP}" \
  --http-settings-cookie-based-affinity Enabled \
  --sku WAF_v2 \
  --capacity 2 \
  --tags ${TAGS}

# Step 10: Create Web Application Firewall policy
az network application-gateway waf-policy create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WAF_POLICY}" \
  --type OWASP \
  --version 3.1 \
  --tags ${TAGS}

# Step 11: Associate WAF policy with Application Gateway
az network application-gateway update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_GW_NAME}" \
  --waf-policy "${WAF_POLICY}"

# Step 12: Create backend pool
az network application-gateway address-pool create \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${BACKEND_POOL}" \
  --servers 10.0.2.4 10.0.2.5

# Step 13: Create HTTP settings
az network application-gateway http-settings create \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${HTTP_SETTINGS}" \
  --port 80 \
  --protocol Http \
  --cookie-based-affinity Enabled \
  --request-timeout 20

# Step 14: Create health probe
az network application-gateway probe create \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${HEALTH_PROBE}" \
  --protocol http \
  --host-name "localhost" \
  --path "/" \
  --port 80 \
  --match-status-codes 200-399

# Step 15: Update HTTP settings to use health probe
az network application-gateway http-settings update \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${HTTP_SETTINGS}" \
  --probe "${HEALTH_PROBE}"

# Step 16: Create HTTP listener
az network application-gateway http-listener create \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${LISTENER_HTTP}" \
  --frontend-ip "appGatewayFrontendIP" \
  --frontend-port "appGatewayFrontendPort" \
  --host-name "*.example.com"

# Step 17: Create routing rule
az network application-gateway rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${ROUTING_RULE}" \
  --http-listener "${LISTENER_HTTP}" \
  --rule-type Basic \
  --address-pool "${BACKEND_POOL}" \
  --http-settings "${HTTP_SETTINGS}"

# Step 18: Create SSH key for VMs
SSH_KEY_NAME="azurehaymaker-key-${UNIQUE_ID}"
az sshkey create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SSH_KEY_NAME}" \
  --tags ${TAGS}

# Step 19: Create backend VMs (simplified - using network interface only)
VM1_NAME="azurehaymaker-vm1-${UNIQUE_ID}"
VM2_NAME="azurehaymaker-vm2-${UNIQUE_ID}"
NIC1_NAME="azurehaymaker-nic1-${UNIQUE_ID}"
NIC2_NAME="azurehaymaker-nic2-${UNIQUE_ID}"

az network nic create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NIC1_NAME}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${BACKEND_SUBNET}" \
  --private-ip-address "10.0.2.4" \
  --tags ${TAGS}

az network nic create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NIC2_NAME}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${BACKEND_SUBNET}" \
  --private-ip-address "10.0.2.5" \
  --tags ${TAGS}

# Step 20: Create VMs
az vm create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM1_NAME}" \
  --nics "${NIC1_NAME}" \
  --image UbuntuLTS \
  --size Standard_B1s \
  --admin-username azureuser \
  --ssh-key-name "${SSH_KEY_NAME}" \
  --os-disk-name "azurehaymaker-osdisk1-${UNIQUE_ID}" \
  --tags ${TAGS}

az vm create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM2_NAME}" \
  --nics "${NIC2_NAME}" \
  --image UbuntuLTS \
  --size Standard_B1s \
  --admin-username azureuser \
  --ssh-key-name "${SSH_KEY_NAME}" \
  --os-disk-name "azurehaymaker-osdisk2-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 21: Install web server on VMs
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM1_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo apt-get update && sudo apt-get install -y nginx && sudo systemctl start nginx && sudo systemctl enable nginx"

az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM2_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo apt-get update && sudo apt-get install -y nginx && sudo systemctl start nginx && sudo systemctl enable nginx"

# Step 22: Get Application Gateway public IP
APP_GW_IP_ADDR=$(az network public-ip show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_GW_IP}" \
  --query ipAddress -o tsv)

echo "Application Gateway Public IP: ${APP_GW_IP_ADDR}"
```

### Validation
```bash
# Verify Application Gateway
az network application-gateway show --resource-group "${RESOURCE_GROUP}" --name "${APP_GW_NAME}"

# Verify WAF policy
az network application-gateway waf-policy show --resource-group "${RESOURCE_GROUP}" --name "${WAF_POLICY}"

# Verify backend pool
az network application-gateway address-pool show --resource-group "${RESOURCE_GROUP}" --gateway-name "${APP_GW_NAME}" --name "${BACKEND_POOL}"

# Verify health probe
az network application-gateway probe show --resource-group "${RESOURCE_GROUP}" --gateway-name "${APP_GW_NAME}" --name "${HEALTH_PROBE}"

# Verify routing rules
az network application-gateway rule list --resource-group "${RESOURCE_GROUP}" --gateway-name "${APP_GW_NAME}" --output table

# Check VM states
az vm list --resource-group "${RESOURCE_GROUP}" --output table

# Test HTTP connectivity
echo "Testing Application Gateway connectivity..."
curl -I "http://${APP_GW_IP_ADDR}/" || echo "Note: May need to wait for VMs to initialize"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: View Application Gateway configuration
az network application-gateway show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_GW_NAME}" \
  --query "{name: name, skuName: sku.name, capacity: sku.capacity, operationalState: operationalState}"

# Operation 2: Check backend health status
az network application-gateway show-backend-health \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${APP_GW_NAME}"

# Operation 3: Monitor Application Gateway metrics - throughput
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/applicationGateways/${APP_GW_NAME}" \
  --metric "BytesReceived BytesSent" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 4: Monitor Application Gateway metrics - request count
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/applicationGateways/${APP_GW_NAME}" \
  --metric "RequestCount" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 5: Create additional routing rule for path-based routing
PATH_RULE="azurehaymaker-path-rule-${UNIQUE_ID}"
az network application-gateway rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${PATH_RULE}" \
  --http-listener "${LISTENER_HTTP}" \
  --rule-type PathBasedRouting \
  --address-pool "${BACKEND_POOL}" \
  --http-settings "${HTTP_SETTINGS}" \
  --paths "/api/*" "/health/*"

# Operation 6: Update WAF policy to enable managed rules
az network application-gateway waf-policy managed-rules add \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WAF_POLICY}" \
  --rules-group-name "GeoBlocking"

# Operation 7: List all HTTP listeners
az network application-gateway http-listener list \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --output table

# Operation 8: Update backend pool with additional servers
az network application-gateway address-pool update \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${BACKEND_POOL}" \
  --servers 10.0.2.4 10.0.2.5 10.0.2.6

# Operation 9: Update VM1 with custom web content
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM1_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo tee /var/www/html/index.html > /dev/null <<'EOF'
<!DOCTYPE html>
<html>
<head><title>AppGW Test</title></head>
<body><h1>Azure Application Gateway - Backend Server 1</h1><p>Protected by WAF</p></body>
</html>
EOF"

# Operation 10: Update VM2 with custom web content
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM2_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo tee /var/www/html/index.html > /dev/null <<'EOF'
<!DOCTYPE html>
<html>
<head><title>AppGW Test</title></head>
<body><h1>Azure Application Gateway - Backend Server 2</h1><p>Protected by WAF</p></body>
</html>
EOF"

# Operation 11: Monitor WAF-blocked requests
az monitor log-analytics query \
  --workspace "workspace-name" \
  --analytics-query "AzureDiagnostics | where ResourceType == 'APPLICATIONGATEWAYS' and Message contains 'Matched'"

# Operation 12: Verify HTTP settings configuration
az network application-gateway http-settings show \
  --resource-group "${RESOURCE_GROUP}" \
  --gateway-name "${APP_GW_NAME}" \
  --name "${HTTP_SETTINGS}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group
az group delete \
  --resource-group "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 2: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 180

# Step 3: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 4: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-appgw-${UNIQUE_ID}-rg`
- Application Gateway: `azurehaymaker-appgw-${UNIQUE_ID}`
- Application Gateway Public IP: `azurehaymaker-appgw-pip-${UNIQUE_ID}`
- WAF Policy: `azurehaymaker-waf-policy-${UNIQUE_ID}`
- Backend Pool: `azurehaymaker-backend-pool-${UNIQUE_ID}`
- Health Probe: `azurehaymaker-health-probe-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Application Gateway Overview](https://learn.microsoft.com/en-us/azure/application-gateway/overview)
- [Web Application Firewall (WAF)](https://learn.microsoft.com/en-us/azure/web-application-firewall/ag/ag-overview)
- [Create Application Gateway with CLI](https://learn.microsoft.com/en-us/azure/application-gateway/quick-create-cli)
- [Path-Based Routing](https://learn.microsoft.com/en-us/azure/application-gateway/url-route-overview)
- [Application Gateway CLI Reference](https://learn.microsoft.com/en-us/cli/azure/network/application-gateway)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive application gateway management with commands for WAF policy configuration, routing rules, and backend pool management. Direct CLI commands enable fine-grained control over security and routing policies.

---

## Estimated Duration
- **Deployment**: 20-25 minutes (includes gateway and VM provisioning)
- **Operations Phase**: 8+ hours (with monitoring, policy updates, and traffic analysis)
- **Cleanup**: 15-20 minutes

---

## Notes
- Application Gateway uses WAF v2 SKU for advanced threat protection
- Web Application Firewall provides OWASP ModSecurity rules (version 3.1)
- Health probe monitors backend instances; unhealthy instances are removed from rotation
- Path-based routing enables different backend pools based on URL paths
- Cookie-based affinity maintains client sessions within backend instances
- All operations scoped to single tenant and subscription
- Gateway requires dedicated subnet (GatewaySubnet)
- Standard SKU public IP required for high availability
