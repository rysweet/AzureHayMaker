# Scenario: Auto-Scaling VM Scale Set with Load Balancer

## Technology Area
Compute

## Company Profile
- **Company Size**: Mid-size enterprise
- **Industry**: E-Commerce / Retail
- **Use Case**: Deploy auto-scaling virtual machine fleet with load balancing for high-traffic web applications

## Scenario Description
Deploy an Azure Virtual Machine Scale Set with automatic scaling based on CPU utilization, fronted by an Azure Load Balancer for traffic distribution. Includes monitoring, scaling rules configuration, and traffic management.

## Azure Services Used
- Azure Virtual Machine Scale Sets
- Azure Load Balancer
- Azure Network Interfaces
- Azure Network Security Groups
- Azure Public IP Addresses
- Azure Monitor with auto-scaling rules

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Basic understanding of load balancing concepts
- Access to create VMs and networking resources

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-compute-${UNIQUE_ID}-rg"
LOCATION="eastus"
VMSS_NAME="azurehaymaker-vmss-${UNIQUE_ID}"
LB_NAME="azurehaymaker-lb-${UNIQUE_ID}"
LB_BACKEND_POOL="azurehaymaker-backend-${UNIQUE_ID}"
LB_FRONTEND_IP="azurehaymaker-frontend-${UNIQUE_ID}"
NSG_NAME="azurehaymaker-vmss-nsg-${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vmss-vnet-${UNIQUE_ID}"
SUBNET_NAME="azurehaymaker-vmss-subnet-${UNIQUE_ID}"
PUBLIC_IP_NAME="azurehaymaker-lb-pip-${UNIQUE_ID}"
AUTOSCALE_NAME="azurehaymaker-autoscale-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=compute-vm-scale-set Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Virtual Network and Subnet
az network vnet create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VNET_NAME}" \
  --address-prefix 10.0.0.0/16 \
  --subnet-name "${SUBNET_NAME}" \
  --subnet-prefix 10.0.1.0/24 \
  --tags ${TAGS}

# Step 3: Create Network Security Group for VMSS
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_NAME}" \
  --tags ${TAGS}

# Step 4: Add security rules
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-http" \
  --priority 1000 \
  --source-address-prefixes "*" \
  --destination-port-ranges 80 \
  --access Allow \
  --protocol Tcp

az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-https" \
  --priority 1001 \
  --source-address-prefixes "*" \
  --destination-port-ranges 443 \
  --access Allow \
  --protocol Tcp

az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-ssh" \
  --priority 1002 \
  --source-address-prefixes "*" \
  --destination-port-ranges 22 \
  --access Allow \
  --protocol Tcp

# Step 5: Create Public IP for Load Balancer
az network public-ip create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PUBLIC_IP_NAME}" \
  --allocation-method Static \
  --sku Standard \
  --tags ${TAGS}

PUBLIC_IP=$(az network public-ip show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PUBLIC_IP_NAME}" \
  --query ipAddress -o tsv)

echo "Load Balancer Public IP: ${PUBLIC_IP}"

# Step 6: Create Load Balancer
az network lb create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${LB_NAME}" \
  --sku Standard \
  --public-ip-address "${PUBLIC_IP_NAME}" \
  --frontend-ip-name "${LB_FRONTEND_IP}" \
  --backend-pool-name "${LB_BACKEND_POOL}" \
  --tags ${TAGS}

# Step 7: Create health probe for Load Balancer
az network lb probe create \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "health-probe" \
  --protocol http \
  --port 80 \
  --path "/"

# Step 8: Create load balancing rule
az network lb rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "http-rule" \
  --protocol tcp \
  --frontend-port 80 \
  --backend-port 80 \
  --frontend-ip-name "${LB_FRONTEND_IP}" \
  --backend-pool-name "${LB_BACKEND_POOL}" \
  --probe-name "health-probe"

# Step 9: Create Virtual Machine Scale Set
az vmss create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VMSS_NAME}" \
  --image UbuntuLTS \
  --vm-sku Standard_B1s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --vnet-name "${VNET_NAME}" \
  --subnet "${SUBNET_NAME}" \
  --nsg "${NSG_NAME}" \
  --backend-pool-name "${LB_BACKEND_POOL}" \
  --load-balancer "${LB_NAME}" \
  --instance-count 2 \
  --tags ${TAGS}

# Step 10: Install nginx on all VMSS instances using custom script extension
az vmss extension set \
  --resource-group "${RESOURCE_GROUP}" \
  --vmss-name "${VMSS_NAME}" \
  --name CustomScriptExtension \
  --publisher Microsoft.Azure.Extensions \
  --version 2.1 \
  --protected-settings '{"commandToExecute":"bash -c \"apt-get update && apt-get install -y nginx && systemctl start nginx && systemctl enable nginx && HOSTNAME=$(hostname) && cat > /var/www/html/index.html <<EOFHTML\n<!DOCTYPE html>\n<html>\n<head><title>Azure HayMaker - VMSS</title><style>body{font-family:Arial;margin:50px}h1{color:#0078d4}</style></head>\n<body>\n<h1>Azure HayMaker - VM Scale Set</h1>\n<p>Scenario: compute-05-vm-scale-set</p>\n<p>Hostname: ${HOSTNAME}</p>\n<p>Instance ID: $(curl -s -H Metadata:true http://169.254.169.254/metadata/instance?api-version=2020-09-01 | grep -o \"vmId[^,]*\" | cut -d\\\" -f3)</p>\n<p>Timestamp: $(date)</p>\n</body>\n</html>\nEOFHTML\""}'

# Step 11: Create auto-scale settings based on CPU utilization
az monitor autoscale create \
  --resource-group "${RESOURCE_GROUP}" \
  --resource "${VMSS_NAME}" \
  --resource-type "Microsoft.Compute/virtualMachineScaleSets" \
  --name "${AUTOSCALE_NAME}" \
  --min-count 2 \
  --max-count 10 \
  --count 2

# Step 12: Add scale-out rule (when CPU > 70%)
az monitor autoscale rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --autoscale-name "${AUTOSCALE_NAME}" \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 2

# Step 13: Add scale-in rule (when CPU < 30%)
az monitor autoscale rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --autoscale-name "${AUTOSCALE_NAME}" \
  --condition "Percentage CPU < 30 avg 10m" \
  --scale in 1

# Step 14: Wait for VMSS deployment and script execution
echo "Waiting for VMSS initialization..."
sleep 120
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify VMSS configuration
az vmss show --resource-group "${RESOURCE_GROUP}" --name "${VMSS_NAME}"

# Verify Load Balancer
az network lb show --resource-group "${RESOURCE_GROUP}" --name "${LB_NAME}"

# List VMSS instances
az vmss list-instances --resource-group "${RESOURCE_GROUP}" --vmss-name "${VMSS_NAME}" --output table

# Test Load Balancer endpoint
echo "Testing HTTP connection to Load Balancer (${PUBLIC_IP})..."
curl -I "http://${PUBLIC_IP}" || echo "Note: May need to wait a moment for instances to be ready"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Monitor VMSS instance health
az vmss list-instances \
  --resource-group "${RESOURCE_GROUP}" \
  --vmss-name "${VMSS_NAME}" \
  --query "[].{ID:instanceId, ProvisioningState:provisioningState, PowerState:powerState}" \
  --output table

# Operation 2: Check Load Balancer backend pool health
az network lb address-pool show \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --name "${LB_BACKEND_POOL}" \
  --output table

# Operation 3: Monitor CPU metrics for VMSS
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachineScaleSets/${VMSS_NAME}" \
  --metric "Percentage CPU" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 4: Monitor network throughput
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachineScaleSets/${VMSS_NAME}" \
  --metric "Network In Total" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 5: Check auto-scale settings
az monitor autoscale show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${AUTOSCALE_NAME}"

# Operation 6: View auto-scale activity logs
az monitor autoscale-settings list-by-resource-group \
  --resource-group "${RESOURCE_GROUP}"

# Operation 7: Manually scale out VMSS instances
az vmss scale \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VMSS_NAME}" \
  --new-capacity 5

# Operation 8: Manually scale in VMSS instances
az vmss scale \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VMSS_NAME}" \
  --new-capacity 3

# Operation 9: Restart specific VMSS instance
INSTANCE_ID=$(az vmss list-instances --resource-group "${RESOURCE_GROUP}" --vmss-name "${VMSS_NAME}" --query "[0].instanceId" -o tsv)
az vmss restart --resource-group "${RESOURCE_GROUP}" --name "${VMSS_NAME}" --instance-ids "${INSTANCE_ID}"

# Operation 10: Update VMSS instance count from Load Balancer metrics
az network lb show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${LB_NAME}" \
  --query "backendAddressPools[].backendIpConfigurations" \
  --output table

# Operation 11: Check Load Balancer rule configuration
az network lb rule list \
  --resource-group "${RESOURCE_GROUP}" \
  --lb-name "${LB_NAME}" \
  --output table

# Operation 12: Update VMSS base image (rolling upgrade)
az vmss update --resource-group "${RESOURCE_GROUP}" --name "${VMSS_NAME}" --enable-os-disk-encryption false

# Operation 13: Monitor Load Balancer throughput
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/loadBalancers/${LB_NAME}" \
  --metric "BytesInCount" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 14: View VMSS upgrade history
az vmss rolling-upgrade start-extension-upgrade \
  --resource-group "${RESOURCE_GROUP}" \
  --vmss-name "${VMSS_NAME}" || true

# Operation 15: Perform stress testing to trigger auto-scale
for INSTANCE in $(az vmss list-instances --resource-group "${RESOURCE_GROUP}" --vmss-name "${VMSS_NAME}" --query "[].[instanceId]" -o tsv); do
  az vmss run-command invoke \
    --resource-group "${RESOURCE_GROUP}" \
    --instance-ids "${INSTANCE}" \
    --vmss-name "${VMSS_NAME}" \
    --command-id RunShellScript \
    --scripts "stress-ng --cpu 2 --timeout 30s &" 2>/dev/null || true
done
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
- Resource Group: `azurehaymaker-compute-${UNIQUE_ID}-rg`
- Virtual Machine Scale Set: `azurehaymaker-vmss-${UNIQUE_ID}`
- Load Balancer: `azurehaymaker-lb-${UNIQUE_ID}`
- Network Security Group: `azurehaymaker-vmss-nsg-${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vmss-vnet-${UNIQUE_ID}`
- Public IP: `azurehaymaker-lb-pip-${UNIQUE_ID}`
- Auto-scale Setting: `azurehaymaker-autoscale-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Virtual Machine Scale Sets Overview](https://learn.microsoft.com/en-us/azure/virtual-machine-scale-sets/overview)
- [Create VM Scale Set with Azure CLI](https://learn.microsoft.com/en-us/azure/virtual-machine-scale-sets/quick-create-cli)
- [Azure Load Balancer Overview](https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-overview)
- [Autoscale Virtual Machine Scale Sets](https://learn.microsoft.com/en-us/azure/virtual-machine-scale-sets/virtual-machine-scale-sets-autoscale-overview)
- [VM Scale Set Extensions](https://learn.microsoft.com/en-us/azure/virtual-machine-scale-sets/virtual-machine-scale-sets-extensions)
- [Load Balancer Rules](https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-components)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive VMSS and Load Balancer management with straightforward commands for provisioning, scaling, and monitoring. This approach enables flexible infrastructure-as-code patterns.

---

## Estimated Duration
- **Deployment**: 20-25 minutes
- **Operations Phase**: 8+ hours (with scaling operations, monitoring, and performance tuning)
- **Cleanup**: 5-10 minutes

---

## Notes
- Virtual Machine Scale Set provides automated VM lifecycle management
- Load Balancer distributes traffic across healthy instances
- Auto-scaling rules trigger based on CPU metrics (scale out at >70%, scale in at <30%)
- Minimum 2 instances, maximum 10 instances configured
- Health probe monitors instance availability (HTTP port 80)
- Custom Script Extension installs nginx automatically on all instances
- Horizontal scaling handles traffic spikes without manual intervention
- All operations scoped to single tenant and subscription
- Ideal for stateless, horizontally-scalable applications
- Zero-downtime deployments with rolling upgrades
