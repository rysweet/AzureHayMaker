# Scenario: Windows Server VM with IIS Web Server

## Technology Area
Compute

## Company Profile
- **Company Size**: Mid-size enterprise
- **Industry**: Financial Services
- **Use Case**: Deploy a Windows Server VM with IIS for hosting legacy ASP.NET web applications

## Scenario Description
Deploy a Windows Server 2019/2022 virtual machine with Internet Information Services (IIS) installed and configured. Includes basic web content deployment, performance monitoring, and Windows Update management.

## Azure Services Used
- Azure Virtual Machines (Windows Server)
- Azure Network Interfaces
- Azure Public IP Addresses
- Azure Network Security Groups
- Azure Managed Disks

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- RDP client available for remote desktop access (optional for validation)
- Access to create virtual machines and manage Windows servers

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-compute-${UNIQUE_ID}-rg"
LOCATION="eastus"
VM_NAME="azurehaymaker-winvm-${UNIQUE_ID}"
NIC_NAME="azurehaymaker-winnic-${UNIQUE_ID}"
NSG_NAME="azurehaymaker-winnsg-${UNIQUE_ID}"
VNET_NAME="azurehaymaker-winvnet-${UNIQUE_ID}"
SUBNET_NAME="azurehaymaker-winsubnet-${UNIQUE_ID}"
PUBLIC_IP_NAME="azurehaymaker-winpip-${UNIQUE_ID}"
ADMIN_USERNAME="azureuser"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=compute-windows-iis Owner=AzureHayMaker"
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

# Step 4: Add security rules for RDP, HTTP, and HTTPS
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name "${NSG_NAME}" \
  --name "allow-rdp" \
  --priority 1000 \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 3389 \
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

# Step 7: Create Windows Server Virtual Machine
az vm create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --nics "${NIC_NAME}" \
  --image Win2022Datacenter \
  --size Standard_B2s \
  --admin-username "${ADMIN_USERNAME}" \
  --admin-password "P@ssw0rd$(openssl rand -hex 4)" \
  --os-disk-name "azurehaymaker-osdisk-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 8: Get the Public IP Address
PUBLIC_IP=$(az network public-ip show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${PUBLIC_IP_NAME}" \
  --query ipAddress -o tsv)

echo "Public IP Address: ${PUBLIC_IP}"

# Step 9: Install IIS and required components using Custom Script Extension
az vm extension set \
  --resource-group "${RESOURCE_GROUP}" \
  --vm-name "${VM_NAME}" \
  --name CustomScriptExtension \
  --publisher Microsoft.Compute \
  --version 1.10 \
  --settings '{"fileUris":[],"commandToExecute":"powershell.exe -Command \"Install-WindowsFeature -Name Web-Server, Web-WebServer, Web-Common-Http, Web-Default-Doc, Web-Dir-Browsing, Web-Http-Errors, Web-Static-Content, Web-Health, Web-Http-Logging, Web-Log-Libraries, Web-Request-Monitor, Web-Http-Tracing, Web-Performance, Web-Compression, Web-Security, Web-Filtering, Web-Basic-Auth, Web-Windows-Auth, Web-App-Dev, Web-Asp-Net, Web-Asp-Net45, Web-Net-Ext, Web-Net-Ext45, Web-AppInit, Web-CGI, Web-ISAPI-Ext, Web-ISAPI-Filter, Web-Includes, Web-WebSockets, Web-Mgmt-Tools, Web-Mgmt-Console, Web-Scripting-Tools, Web-Mgmt-Service -Restart\""}'

# Step 10: Wait for IIS installation
echo "Waiting for IIS installation to complete..."
sleep 120

# Step 11: Create sample ASP.NET welcome page
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts @- <<'EOF'
$htmlContent = @"
<!DOCTYPE html>
<html>
<head>
    <title>Azure HayMaker - IIS Server</title>
    <style>
        body { font-family: Segoe UI, sans-serif; margin: 50px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #0078d4; }
        .info { background: #f0f0f0; padding: 15px; border-left: 4px solid #0078d4; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Azure HayMaker - Windows IIS Server</h1>
        <div class="info">
            <p><strong>Scenario:</strong> compute-02-windows-vm-iis</p>
            <p><strong>Server Name:</strong> $env:COMPUTERNAME</p>
            <p><strong>OS Version:</strong> Windows Server 2022 Datacenter</p>
            <p><strong>IIS Version:</strong> 10.0</p>
            <p><strong>Timestamp:</strong> $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>
            <p><strong>PowerShell Version:</strong> $($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor)</p>
        </div>
        <hr>
        <p>This server is running on an Azure Windows VM with Internet Information Services (IIS) web server.</p>
    </div>
</body>
</html>
"@

Set-Content -Path "C:\inetpub\wwwroot\index.html" -Value $htmlContent -Force
EOF
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
curl -I "http://${PUBLIC_IP}" || echo "Note: May need to wait a moment for IIS to fully initialize"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Check VM CPU metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachines/${VM_NAME}" \
  --metric "Percentage CPU" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 2: Check network metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachines/${VM_NAME}" \
  --metric "Network In Total" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 3: Check IIS application pool status
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "Get-IISAppPool"

# Operation 4: Check IIS websites
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "Get-IISBindings"

# Operation 5: View IIS HTTP logs
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "Get-ChildItem C:\inetpub\logs\LogFiles\W3SVC1\ -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Tail 20"

# Operation 6: Stop and start the IIS service
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "Stop-Service W3SVC; Start-Sleep -Seconds 5; Start-Service W3SVC; Get-Service W3SVC"

# Operation 7: Check Windows Update status
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10"

# Operation 8: Get system information and performance metrics
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "Write-Host 'System Information:'; Get-ComputerInfo -Property CsProcessors, CsPhysicalMemory, OsVersion; Write-Host 'Disk Space:'; Get-Volume | Select-Object DriveLetter, Size, SizeRemaining | Format-Table"

# Operation 9: Create a new IIS application pool
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "New-IISAppPool -Name 'HayMakerAppPool' -ErrorAction SilentlyContinue; Get-IISAppPool -Name 'HayMakerAppPool'"

# Operation 10: Add a new website binding
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "New-Item -Path 'C:\inetpub\wwwroot\api' -ItemType Directory -Force | Out-Null; Set-Content -Path 'C:\inetpub\wwwroot\api\index.html' -Value '<h1>API Endpoint</h1><p>Test content</p>' -Force"

# Operation 11: Check IIS worker process status
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "Get-Process w3wp | Select-Object ProcessName, Id, WorkingSet, Handles"

# Operation 12: Monitor disk usage
az vm run-command invoke \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --command-id RunPowerShellScript \
  --scripts "Get-Volume | Where-Object {$_.DriveLetter -ne $null} | Select-Object DriveLetter, Size, SizeRemaining, @{Name='PercentFree';Expression={[math]::Round(($_.SizeRemaining/$_.Size)*100,2)}} | Format-Table"

# Operation 13: Resize VM (scale up)
az vm resize --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --size Standard_B4ms

# Operation 14: Restart the VM
az vm restart --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}" --no-wait
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
- Virtual Machine: `azurehaymaker-winvm-${UNIQUE_ID}`
- Network Interface: `azurehaymaker-winnic-${UNIQUE_ID}`
- Network Security Group: `azurehaymaker-winnsg-${UNIQUE_ID}`
- Virtual Network: `azurehaymaker-winvnet-${UNIQUE_ID}`
- Public IP: `azurehaymaker-winpip-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Virtual Machines Overview](https://learn.microsoft.com/en-us/azure/virtual-machines/overview)
- [Create Windows Virtual Machine with Azure CLI](https://learn.microsoft.com/en-us/azure/virtual-machines/windows/quick-create-cli)
- [Internet Information Services (IIS)](https://learn.microsoft.com/en-us/iis/get-started/introduction-to-iis/iis-overview)
- [IIS PowerShell Module](https://learn.microsoft.com/en-us/powershell/module/iisadministration)
- [Windows Server on Azure Virtual Machines](https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/rds-vms-on-azure)
- [Azure VM Extensions](https://learn.microsoft.com/en-us/azure/virtual-machines/extensions/overview)

---

## Automation Tool
**Recommended**: Azure CLI with PowerShell

**Rationale**: Azure CLI handles VM provisioning while PowerShell scripts enable granular Windows Server and IIS configuration management. This combination provides optimal control for Windows-based scenarios.

---

## Estimated Duration
- **Deployment**: 20-25 minutes
- **Operations Phase**: 8+ hours (with IIS management, performance monitoring, and maintenance)
- **Cleanup**: 5-10 minutes

---

## Notes
- Windows Server 2022 Datacenter edition provides latest features and support
- IIS installed with comprehensive web server components including ASP.NET 4.8 support
- RDP access available for remote desktop connections (port 3389)
- Custom Script Extension used for automated IIS installation
- PowerShell scripts used for advanced Windows Server management operations
- All operations scoped to single tenant and subscription
- Password generation ensures secure initial admin credentials (consider Azure Key Vault for production)
