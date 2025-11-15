# Scenario: Azure Load Balancer with Virtual Machines

## Technology Area
Networking

## Company Profile
- **Company Size**: Mid-size technology company
- **Industry**: Software / SaaS
- **Use Case**: Distribute incoming traffic across multiple virtual machines for high availability and fault tolerance

## Scenario Description
Deploy an Azure Load Balancer configured to distribute HTTP and HTTPS traffic across multiple backend virtual machines. This scenario covers load balancer provisioning, backend pool configuration, health probes, load balancing rules, and inbound NAT rules for management access.

## Azure Services Used
- Azure Load Balancer (Standard SKU)
- Azure Virtual Machines
- Azure Virtual Network
- Azure Public IP
- Azure Network Interfaces
- Azure Network Security Groups

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Access to create multiple VMs and load balancers

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-lb-${UNIQUE_ID}-rg"
LOCATION="eastus"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
BACKEND_SUBNET="azurehaymaker-backend-${UNIQUE_ID}"
LB_NAME="azurehaymaker-lb-${UNIQUE_ID}"
LB_PUBLIC_IP="azurehaymaker-lb-pip-${UNIQUE_ID}"
BACKEND_POOL="azurehaymaker-backend-pool-${UNIQUE_ID}"
HEALTH_PROBE="azurehaymaker-health-probe-${UNIQUE_ID}"
LB_RULE_HTTP="azurehaymaker-http-rule-${UNIQUE_ID}"
LB_RULE_HTTPS="azurehaymaker-https-rule-${UNIQUE_ID}"
NSG_NAME="azurehaymaker-lb-nsg-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=networking-load-balancer Owner=AzureHayMaker"
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

# Step 3: Create Backend Subnet
az network vnet subnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${BACKEND_SUBNET}" \
  --address-prefix 10.0.1.0/24

# Step 4: Create Network Security Group
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_NAME}" \
  --tags ${TAGS}

# Step 5: Add NSG rules for HTTP, HTTPS, and SSH
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
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
  --nsg-name "${NSG_NAME}" \
  --name "allow-https" \
  --priority 1001 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 443 \
  --access Allow \
  --protocol Tcp

az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-ssh" \
  --priority 1002 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 22 \
  --access Allow \
  --protocol Tcp

# Step 6: Associate NSG with backend subnet
az network vnet subnet update \
  --resource-group "${RESOURCE_GROUP}" \
  --vnet-name "${VNET_NAME}" \
  --name "${BACKEND_SUBNET}" \
  --network-security-group "${NSG_NAME}"

# Step 7: Create public IP for Load Balancer
az network public-ip create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${LB_PUBLIC_IP}" \
  --allocation-method Static \
  --sku Standard \
  --tags ${TAGS}

# Step 8: Create Load Balancer
az network lb create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${LB_NAME}" \
  --sku Standard \
  --public-ip-address "${LB_PUBLIC_IP}" \
  --frontend-ip-name "azurehaymaker-frontend-${UNIQUE_ID}" \
  --backend-pool-name "${BACKEND_POOL}" \
  --tags ${TAGS}

# Step 9: Create health probe
az network lb probe create \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "${HEALTH_PROBE}" \
  --protocol http \
  --port 80 \
  --path "/"

# Step 10: Create load balancing rule for HTTP
az network lb rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "${LB_RULE_HTTP}" \
  --protocol tcp \
  --frontend-port 80 \
  --backend-port 80 \
  --frontend-ip-name "azurehaymaker-frontend-${UNIQUE_ID}" \
  --backend-pool-name "${BACKEND_POOL}" \
  --probe-name "${HEALTH_PROBE}"

# Step 11: Create load balancing rule for HTTPS
az network lb rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "${LB_RULE_HTTPS}" \
  --protocol tcp \
  --frontend-port 443 \
  --backend-port 443 \
  --frontend-ip-name "azurehaymaker-frontend-${UNIQUE_ID}" \
  --backend-pool-name "${BACKEND_POOL}" \
  --probe-name "${HEALTH_PROBE}"

# Step 12: Create SSH key pair
SSH_KEY_NAME="azurehaymaker-key-${UNIQUE_ID}"
az sshkey create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SSH_KEY_NAME}" \
  --tags ${TAGS}

# Step 13: Create first VM with network interface
VM1_NAME="azurehaymaker-vm1-${UNIQUE_ID}"
NIC1_NAME="azurehaymaker-nic1-${UNIQUE_ID}"

az network nic create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NIC1_NAME}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${BACKEND_SUBNET}" \
  --lb-name "${LB_NAME}" \
  --lb-address-pools "${BACKEND_POOL}" \
  --tags ${TAGS}

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

# Step 14: Create second VM with network interface
VM2_NAME="azurehaymaker-vm2-${UNIQUE_ID}"
NIC2_NAME="azurehaymaker-nic2-${UNIQUE_ID}"

az network nic create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NIC2_NAME}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${BACKEND_SUBNET}" \
  --lb-name "${LB_NAME}" \
  --lb-address-pools "${BACKEND_POOL}" \
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

# Step 15: Install web server on both VMs
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

# Step 16: Get Load Balancer public IP
LB_IP=$(az network public-ip show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${LB_PUBLIC_IP}" \
  --query ipAddress -o tsv)

echo "Load Balancer Public IP: ${LB_IP}"
```

### Validation
```bash
# Verify Load Balancer
az network lb show --resource-group "${RESOURCE_GROUP}" --name "${LB_NAME}"

# Verify backend pool
az network lb address-pool show --resource-group "${RESOURCE_GROUP}" --lb-name "${LB_NAME}" --name "${BACKEND_POOL}"

# Verify health probe
az network lb probe show --resource-group "${RESOURCE_GROUP}" --lb-name "${LB_NAME}" --name "${HEALTH_PROBE}"

# Verify load balancing rules
az network lb rule list --resource-group "${RESOURCE_GROUP}" --lb-name "${LB_NAME}" --output table

# Check VM states
az vm list --resource-group "${RESOURCE_GROUP}" --output table

# Get network interface status
az network nic show --resource-group "${RESOURCE_GROUP}" --name "${NIC1_NAME}" --query "ipConfigurations"

# Test HTTP connectivity
echo "Testing Load Balancer connectivity..."
curl -I "http://${LB_IP}/" || echo "Note: May need to wait for VMs to fully initialize"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Check backend pool health status
az network lb address-pool list \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --output table

# Operation 2: Monitor load balancer metrics - throughput
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/loadBalancers/${LB_NAME}" \
  --metric "BytesIn BytesOut" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 3: Monitor load balancer metrics - connections
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/loadBalancers/${LB_NAME}" \
  --metric "SNAT Connection Count" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 4: Restart health probe to verify detection
az network lb probe update \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "${HEALTH_PROBE}" \
  --protocol http \
  --port 80 \
  --path "/"

# Operation 5: Create inbound NAT rule for SSH to VM1
NAT_RULE1="azurehaymaker-nat-vm1-${UNIQUE_ID}"
az network lb inbound-nat-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "${NAT_RULE1}" \
  --protocol Tcp \
  --frontend-port 2201 \
  --backend-port 22 \
  --frontend-ip-name "azurehaymaker-frontend-${UNIQUE_ID}"

# Operation 6: Create inbound NAT rule for SSH to VM2
NAT_RULE2="azurehaymaker-nat-vm2-${UNIQUE_ID}"
az network lb inbound-nat-rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "${NAT_RULE2}" \
  --protocol Tcp \
  --frontend-port 2202 \
  --backend-port 22 \
  --frontend-ip-name "azurehaymaker-frontend-${UNIQUE_ID}"

# Operation 7: Associate NAT rules with NICs
az network nic ip-config inbound-nat-rule add \
  --resource-group "${RESOURCE_GROUP}" \
  --nic-name "${NIC1_NAME}" \
  --ip-config-name "ipconfig${VM1_NAME}" \
  --inbound-nat-rule "${NAT_RULE1}" \
  --lb-name "${LB_NAME}"

az network nic ip-config inbound-nat-rule add \
  --resource-group "${RESOURCE_GROUP}" \
  --nic-name "${NIC2_NAME}" \
  --ip-config-name "ipconfig${VM2_NAME}" \
  --inbound-nat-rule "${NAT_RULE2}" \
  --lb-name "${LB_NAME}"

# Operation 8: Update VM1 with custom web content
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM1_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo tee /var/www/html/index.html > /dev/null <<'EOF'
<!DOCTYPE html>
<html>
<head><title>Server 1</title></head>
<body><h1>Azure Load Balancer - Server 1</h1><p>Hostname: $(hostname)</p></body>
</html>
EOF"

# Operation 9: Update VM2 with custom web content
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM2_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo tee /var/www/html/index.html > /dev/null <<'EOF'
<!DOCTYPE html>
<html>
<head><title>Server 2</title></head>
<body><h1>Azure Load Balancer - Server 2</h1><p>Hostname: $(hostname)</p></body>
</html>
EOF"

# Operation 10: Check outbound rules
az network lb outbound-rule list \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --output table

# Operation 11: Monitor individual VM metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachines/${VM1_NAME}" \
  --metric "Percentage CPU" \
  --start-time $(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 12: Verify network interface status and IP configuration
az network nic show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NIC1_NAME}" \
  --query "{name: name, ipConfigurations: ipConfigurations, privateIpAddress: ipConfigurations[0].privateIpAddress}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group (includes load balancer, VMs, NICs, storage, etc.)
az group delete \
  --resource-group "${RESOURCE_GROUP}" \
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
- Resource Group: `azurehaymaker-lb-${UNIQUE_ID}-rg`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Load Balancer: `azurehaymaker-lb-${UNIQUE_ID}`
- Load Balancer Public IP: `azurehaymaker-lb-pip-${UNIQUE_ID}`
- Backend Pool: `azurehaymaker-backend-pool-${UNIQUE_ID}`
- Health Probe: `azurehaymaker-health-probe-${UNIQUE_ID}`
- Virtual Machines: `azurehaymaker-vm1-${UNIQUE_ID}`, `azurehaymaker-vm2-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Load Balancer Overview](https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-overview)
- [Create Azure Load Balancer with CLI](https://learn.microsoft.com/en-us/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
- [Health Probes](https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-custom-probe-overview)
- [Inbound NAT Rules](https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-inbound-nat-rules)
- [Load Balancer CLI Reference](https://learn.microsoft.com/en-us/cli/azure/network/lb)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive load balancer management with straightforward commands for provisioning, configuration of rules and health probes, and backend pool management. Direct CLI commands are ideal for managing distributed application workloads.

---

## Estimated Duration
- **Deployment**: 15-20 minutes (includes VM creation and software installation)
- **Operations Phase**: 8+ hours (with monitoring, updates, and load distribution verification)
- **Cleanup**: 10-15 minutes

---

## Notes
- Load Balancer uses Standard SKU for production-ready functionality
- Health probe monitors HTTP port 80 on backend VMs
- Two VMs provide redundancy for demonstration purposes
- NAT rules enable direct SSH access to individual VMs through load balancer
- Custom web content differentiates responses from each VM
- All operations scoped to single tenant and subscription
- SSH keys securely managed by Azure
- Backend pool automatically distributes traffic across healthy VMs
