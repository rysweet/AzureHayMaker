# Scenario: Simple Linux VM Running Nginx Web Server

## Technology Area
Compute

## Company Profile
- **Company Size**: Small startup
- **Industry**: Technology / SaaS
- **Use Case**: Deploy a lightweight web server on a Linux VM for internal documentation hosting

## Scenario Description
Deploy a Linux virtual machine running Ubuntu with nginx web server, configure custom domain resolution, and manage the server through SSH. This scenario covers VM provisioning, network configuration, and HTTP service management.

## Azure Services Used
- Azure Virtual Machines (Linux - Ubuntu)
- Azure Network Interfaces
- Azure Public IP Addresses
- Azure Network Security Groups

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- SSH key pair generated locally (or one will be created during deployment)
- Access to create virtual machines and manage network resources

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-compute-${UNIQUE_ID}-rg"
LOCATION="eastus"
VM_NAME="azurehaymaker-web-${UNIQUE_ID}"
NIC_NAME="azurehaymaker-nic-${UNIQUE_ID}"
NSG_NAME="azurehaymaker-nsg-${UNIQUE_ID}"
VNET_NAME="azurehaymaker-vnet-${UNIQUE_ID}"
SUBNET_NAME="azurehaymaker-subnet-${UNIQUE_ID}"
PUBLIC_IP_NAME="azurehaymaker-pip-${UNIQUE_ID}"
SSH_KEY_NAME="azurehaymaker-key-${UNIQUE_ID}"
STORAGE_ACCOUNT="azurehaymaker${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=compute-linux-vm Owner=AzureHayMaker"
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

# Step 3: Create Network Security Group
az network nsg create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NSG_NAME}" \
  --tags ${TAGS}

# Step 4: Add security rules for HTTP, HTTPS, and SSH
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-ssh" \
  --priority 1000 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 22 \
  --access Allow \
  --protocol Tcp

az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-http" \
  --priority 1001 \
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
  --priority 1002 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 443 \
  --access Allow \
  --protocol Tcp

# Step 5: Create Public IP Address
az network public-ip create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PUBLIC_IP_NAME}" \
  --allocation-method Static \
  --sku Standard \
  --tags ${TAGS}

# Step 6: Create Network Interface
az network nic create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${NIC_NAME}" \
  --vnet-name "${VNET_NAME}" \
  --subnet "${SUBNET_NAME}" \
  --public-ip-address "${PUBLIC_IP_NAME}" \
  --network-security-group "${NSG_NAME}" \
  --tags ${TAGS}

# Step 7: Create SSH key pair for authentication
az sshkey create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SSH_KEY_NAME}" \
  --tags ${TAGS}

# Step 8: Get the SSH public key
PUBLIC_KEY_PATH=$(az sshkey show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${SSH_KEY_NAME}" \
  --query "publicKey" -o tsv)

# Step 9: Create Linux Virtual Machine
az vm create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --nics "${NIC_NAME}" \
  --image UbuntuLTS \
  --size Standard_B1s \
  --admin-username azureuser \
  --ssh-key-name "${SSH_KEY_NAME}" \
  --os-disk-name "azurehaymaker-osdisk-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 10: Get the Public IP Address
PUBLIC_IP=$(az network public-ip show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PUBLIC_IP_NAME}" \
  --query ipAddress -o tsv)

echo "Public IP Address: ${PUBLIC_IP}"

# Step 11: Run custom script to install and configure nginx
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo apt-get update && sudo apt-get install -y nginx && sudo systemctl start nginx && sudo systemctl enable nginx"

# Step 12: Create a custom index page
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo tee /var/www/html/index.html > /dev/null <<'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>Azure HayMaker - Linux VM Nginx Server</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 50px; }
    .container { max-width: 600px; margin: 0 auto; }
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>Azure HayMaker - Linux VM Web Server</h1>
    <p><strong>Scenario:</strong> compute-01-linux-vm-web-server</p>
    <p><strong>Hostname:</strong> $(hostname)</p>
    <p><strong>OS:</strong> $(lsb_release -ds)</p>
    <p><strong>Nginx Version:</strong> $(nginx -v 2>&1)</p>
    <p><strong>Timestamp:</strong> $(date)</p>
    <hr>
    <p>This server is running on an Azure Linux VM with nginx web server.</p>
  </div>
</body>
</html>
EOF"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Virtual Machine
az vm show --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --query "powerState" -o tsv

# Verify Network Interface
az network nic show --resource-group "${RESOURCE_GROUP}" --name "${NIC_NAME}"

# Verify Public IP
az network public-ip show --resource-group "${RESOURCE_GROUP}" --name "${PUBLIC_IP_NAME}"

# Verify Network Security Group Rules
az network nsg rule list --resource-group "${RESOURCE_GROUP}" --nsg-name "${NSG_NAME}" --output table

# Test HTTP connectivity
echo "Testing HTTP connection to ${PUBLIC_IP}..."
curl -I "http://${PUBLIC_IP}" || echo "Note: May need to wait a moment for nginx to fully initialize"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Check VM performance metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachines/${VM_NAME}" \
  --metric "Percentage CPU" \
  --start-time $(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 2: Check disk I/O metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachines/${VM_NAME}" \
  --metric "Disk Read Bytes" \
  --start-time $(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 3: Check VM network metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachines/${VM_NAME}" \
  --metric "Network In Total" \
  --start-time $(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 4: Restart the VM
az vm restart --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --no-wait

# Operation 5: Deallocate VM (stop and release compute resources)
az vm deallocate --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --no-wait

# Operation 6: Start the deallocated VM
az vm start --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --no-wait

# Operation 7: Update custom content on web server
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo tee /var/www/html/info.html > /dev/null <<'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>System Information</title>
</head>
<body>
  <h1>System Information</h1>
  <p>Last updated: $(date)</p>
  <p>Uptime: $(uptime)</p>
  <p>Disk usage: $(df -h / | tail -1)</p>
  <p>Memory: $(free -h | grep Mem)</p>
</body>
</html>
EOF"

# Operation 8: Check disk usage on VM
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunShellScript \
  --scripts "df -h && echo '---' && du -sh /var/www/"

# Operation 9: Verify nginx status
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo systemctl status nginx"

# Operation 10: View nginx access logs
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunShellScript \
  --scripts "sudo tail -20 /var/log/nginx/access.log"

# Operation 11: Modify VM size (scale up)
az vm resize --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --size Standard_B2s

# Operation 12: View VM details and configuration
az vm show --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --output table

# Operation 13: List all network interfaces attached to VM
az vm open-port --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --port 8080 --priority 1003

# Operation 14: Add a new data disk to the VM
DATA_DISK_NAME="azurehaymaker-datadisk-${UNIQUE_ID}"
az disk create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${DATA_DISK_NAME}" \
  --size-gb 10 \
  --tags ${TAGS}

az vm disk attach \
  --resource-group "${RESOURCE_GROUP}" \
  --vm-name "${VM_NAME}" \
  --name "${DATA_DISK_NAME}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete the entire resource group (includes VM, NICs, storage, etc.)
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
- Virtual Machine: `azurehaymaker-web-${UNIQUE_ID}`
- Network Interface: `azurehaymaker-nic-${UNIQUE_ID}`
- Network Security Group: `azurehaymaker-nsg-${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-vnet-${UNIQUE_ID}`
- Public IP: `azurehaymaker-pip-${UNIQUE_ID}`
- SSH Key: `azurehaymaker-key-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Virtual Machines Overview](https://learn.microsoft.com/en-us/azure/virtual-machines/overview)
- [Create Linux Virtual Machine with Azure CLI](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-cli)
- [Azure Network Security Groups](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview)
- [SSH Keys in Azure](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/ssh-keys-portal)
- [Azure Virtual Machine CLI Reference](https://learn.microsoft.com/en-us/cli/azure/vm)
- [Nginx Web Server Documentation](https://nginx.org/en/docs/)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive VM management capabilities with straightforward commands for provisioning, configuration, and monitoring. The direct command approach is ideal for this straightforward infrastructure scenario.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8+ hours (with monitoring, updates, and maintenance)
- **Cleanup**: 5-10 minutes

---

## Notes
- SSH key is managed by Azure and securely stored
- VM runs Ubuntu LTS for long-term support and stability
- nginx is installed and configured to auto-start on VM reboot
- Public IP allows direct HTTP/HTTPS access from the internet
- NSG rules restrict traffic to necessary ports (SSH, HTTP, HTTPS)
- All operations scoped to single tenant and subscription
- Operations demonstrate VM lifecycle management including start/stop/resize
