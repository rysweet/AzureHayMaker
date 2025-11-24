# Scenario: Azure Arc for Hybrid Server Management

## Technology Area
Hybrid+Multicloud

## Company Profile
- **Company Size**: Large enterprise
- **Industry**: Financial Services
- **Use Case**: Manage on-premises and multicloud servers with unified Azure control plane

## Scenario Description
Deploy Azure Arc to connect on-premises servers and cloud VMs into a unified management experience. Apply policies, deploy agents, and monitor resources across hybrid infrastructure.

## Azure Services Used
- Azure Arc (hybrid server management)
- Azure Policy (governance)
- Azure Monitor (centralized monitoring)
- Azure Key Vault (secrets management)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed
- Virtual machines (on-premises or cloud)
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-hybrid-arc-${UNIQUE_ID}-rg"
LOCATION="eastus"
SERVICE_PRINCIPAL_NAME="azurehaymaker-arc-${UNIQUE_ID}"
KEYVAULT="azurehaymaker-kv-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=hybrid-azure-arc Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Service Principal for Arc agents
SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "${SERVICE_PRINCIPAL_NAME}" \
  --role "Azure Connected Machine Onboarding" \
  --scopes "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}")

SP_CLIENT_ID=$(echo ${SP_OUTPUT} | jq -r '.appId')
SP_TENANT_ID=$(echo ${SP_OUTPUT} | jq -r '.tenant')
SP_PASSWORD=$(echo ${SP_OUTPUT} | jq -r '.password')

# Step 3: Create Key Vault
az keyvault create \
  --name "${KEYVAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Store SP credentials
az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "arc-client-id" \
  --value "${SP_CLIENT_ID}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "arc-client-secret" \
  --value "${SP_PASSWORD}"

az keyvault secret set \
  --vault-name "${KEYVAULT}" \
  --name "arc-tenant-id" \
  --value "${SP_TENANT_ID}"

# Step 4: Create sample script for Arc agent installation
cat > /tmp/arc_installation_script.sh <<EOF
#!/bin/bash

# Azure Arc Connected Machine Agent Installation Script

# Variables
CLIENT_ID="${SP_CLIENT_ID}"
CLIENT_SECRET="${SP_PASSWORD}"
TENANT_ID="${SP_TENANT_ID}"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
RESOURCE_GROUP="${RESOURCE_GROUP}"
LOCATION="${LOCATION}"
RESOURCE_NAME="hybrid-vm-\$(hostname)"

# Download and install Azure Connected Machine Agent
# For Ubuntu/Debian
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "\$ID" = "ubuntu" ] || [ "\$ID" = "debian" ]; then
        apt-get update
        apt-get install -y azcmagent
    fi
fi

# Connect machine to Azure Arc
azcmagent connect \
    --service-principal-id "\${CLIENT_ID}" \
    --service-principal-secret "\${CLIENT_SECRET}" \
    --resource-group "\${RESOURCE_GROUP}" \
    --tenant-id "\${TENANT_ID}" \
    --location "\${LOCATION}" \
    --subscription-id "\${SUBSCRIPTION_ID}" \
    --resource-name "\${RESOURCE_NAME}"

# Verify connection
azcmagent show
EOF

chmod +x /tmp/arc_installation_script.sh

# Step 5: Create onboarding script for Windows
cat > /tmp/arc_onboard.ps1 <<EOF
# Azure Arc Connected Machine Agent Installation for Windows

param(
    [Parameter(Mandatory=\$true)]
    [string]\$ClientId,

    [Parameter(Mandatory=\$true)]
    [string]\$ClientSecret,

    [Parameter(Mandatory=\$true)]
    [string]\$TenantId
)

# Download agent
\$URL = "https://aka.ms/dependencyagentwindows"
\$Path = "C:\temp\InstallDependencyAgent-Windows-x64.exe"

if ((Test-Path C:\temp) -eq 0) {
    New-Item -Path C:\temp -ItemType Directory
}

Invoke-WebRequest -Uri \$URL -OutFile \$Path

# Install agent
Start-Process -FilePath \$Path -ArgumentList "/S /AcceptLicense" -Wait

# Connect to Azure Arc
echo "Connecting to Azure Arc..."

EOF

# Step 6: Create diagnostic script
cat > /tmp/arc_diagnostics.sh <<EOF
#!/bin/bash

echo "=== Azure Arc Agent Diagnostics ==="

# Check agent status
echo "Agent Status:"
azcmagent show

# Check agent logs
echo -e "\nAgent Logs:"
tail -20 /var/opt/azcmagent/log/azcmagent.log 2>/dev/null || echo "Log file not found"

# Check connectivity
echo -e "\nConnectivity Test:"
curl -s https://management.azure.com/version

echo -e "\n=== Diagnostics Complete ==="
EOF

chmod +x /tmp/arc_diagnostics.sh

# Step 7: Create sample Arc-connected servers (simulated)
# In real scenario, these would be actual on-premises or multicloud servers

for i in {1..3}; do
  MACHINE_NAME="hybrid-server-${i}"

  # Register Arc machine (simulated - actual servers would run agent)
  az connectedmachine machine create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${MACHINE_NAME}" \
    --location "${LOCATION}" \
    --os-profile osName="Linux" osVersion="Ubuntu 20.04" \
    --machine-type "Physical" \
    --tags ${TAGS} 2>/dev/null || true
done

# Step 8: Create Azure Policy for Arc resources
cat > /tmp/arc_policy.json <<EOF
{
  "mode": "All",
  "policyRule": {
    "if": {
      "field": "type",
      "equals": "Microsoft.HybridCompute/machines"
    },
    "then": {
      "effect": "audit",
      "details": {}
    }
  }
}
EOF

# Step 9: Assign monitoring extension to Arc machines
echo "To assign extensions to Arc machines:"
echo "az connectedmachine extension create --resource-group ${RESOURCE_GROUP} --machine-name <machine-name> --name MonitoringAgent --type MicrosoftMonitoringAgent"

# Step 10: Create Activity Log Alert for Arc resources
az monitor activity-log alert create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "arc-connection-alert" \
  --condition \
    category=Administrative \
    operationName="Microsoft.HybridCompute/machines/write" \
  --scope "/subscriptions/$(az account show --query id -o tsv)" \
  --location "global" \
  --tags ${TAGS}

echo ""
echo "=========================================="
echo "Azure Arc Setup Created: ${RESOURCE_GROUP}"
echo "Service Principal: ${SERVICE_PRINCIPAL_NAME}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# List Arc-connected machines
az connectedmachine machine list \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Show machine details
az connectedmachine machine show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "hybrid-server-1" 2>/dev/null || echo "Machine not yet connected"

# List extensions deployed
az connectedmachine extension list \
  --resource-group "${RESOURCE_GROUP}" \
  --machine-name "hybrid-server-1" 2>/dev/null || echo "No extensions yet"

# Verify Service Principal
az ad sp show --id "${SP_CLIENT_ID}"

# Check Key Vault
az keyvault show --name "${KEYVAULT}"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Deploy monitoring extension
echo "To deploy Log Analytics agent to Arc machine:"
echo "az connectedmachine extension create --resource-group ${RESOURCE_GROUP} --machine-name hybrid-server-1 --name AzureMonitorLinuxAgent --type AzureMonitorLinuxAgent --publisher Microsoft.Azure.Monitor --enable-auto-upgrade"

# Operation 2: Check Arc machine connectivity status
for machine in $(az connectedmachine machine list --resource-group "${RESOURCE_GROUP}" --query "[].name" -o tsv); do
  echo "Machine: $machine"
  az connectedmachine machine show --resource-group "${RESOURCE_GROUP}" --name "$machine" --query "status" -o tsv 2>/dev/null || echo "Status: Not connected"
done

# Operation 3: List all extensions
echo "Available Arc extensions:"
az connectedmachine extension-metadata list --machine-type "Linux" --output table 2>/dev/null || echo "Extension metadata not available"

# Operation 4: Create Azure Policy assignment
echo "To assign policies to Arc resources:"
echo "az policy assignment create --name 'audit-arc-machines' --policy AuditMachinesWithoutRequiredTools --resource-group ${RESOURCE_GROUP}"

# Operation 5: Monitor Arc machine metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.HybridCompute/machines/hybrid-server-1" \
  --metric "CPU%" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ') 2>/dev/null || echo "Metrics not yet available"

# Operation 6: Check Arc agent version
echo "Arc Agent Information:"
echo "For connected machines, check via: azcmagent version"

# Operation 7: List activity logs for Arc
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --caller-identity "Microsoft.HybridCompute" \
  --output table

# Operation 8: Verify Arc machine tags
az connectedmachine machine update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "hybrid-server-1" \
  --tags Environment=production Department=IT 2>/dev/null || echo "Update skipped"

# Operation 9: Enable log collection
echo "To enable log collection:"
echo "az connectedmachine extension create --resource-group ${RESOURCE_GROUP} --machine-name hybrid-server-1 --name CustomScriptExtension"

# Operation 10: Review Arc onboarding status
az connectedmachine machine list-by-resource-group \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[].{Name:name, Status:status, OSName:osProfile.osName}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete registered machines
for machine in $(az connectedmachine machine list --resource-group "${RESOURCE_GROUP}" --query "[].name" -o tsv); do
  az connectedmachine machine delete \
    --resource-group "${RESOURCE_GROUP}" \
    --name "$machine" \
    --yes 2>/dev/null || true
done

# Step 2: Delete activity log alert
az monitor activity-log alert delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "arc-connection-alert" \
  --yes 2>/dev/null || true

# Step 3: Delete Service Principal
az ad sp delete --id "${SP_CLIENT_ID}"

# Step 4: Delete the entire resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 5: Verify deletion
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 6: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 7: Clean up local files
rm -rf /tmp/arc_*.sh /tmp/arc_*.ps1 /tmp/arc_policy.json
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-hybrid-arc-${UNIQUE_ID}-rg`
- Service Principal: `azurehaymaker-arc-${UNIQUE_ID}`
- Machines: `hybrid-server-1`, `hybrid-server-2`, `hybrid-server-3`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Arc Overview](https://learn.microsoft.com/en-us/azure/azure-arc/overview)
- [Azure Arc Servers](https://learn.microsoft.com/en-us/azure/azure-arc/servers/overview)
- [Onboarding Connected Machines](https://learn.microsoft.com/en-us/azure/azure-arc/servers/onboard-portal)
- [Arc Extensions](https://learn.microsoft.com/en-us/azure/azure-arc/servers/manage-extensions)
- [Azure Arc CLI Reference](https://learn.microsoft.com/en-us/cli/azure/connectedmachine)

---

## Automation Tool
**Recommended**: Azure CLI + Shell Scripts

**Rationale**: Azure CLI manages Arc resources while shell scripts handle agent installation on connected servers. This combination enables comprehensive hybrid management.

---

## Estimated Duration
- **Deployment**: 10-15 minutes (agent installation takes longer on actual servers)
- **Operations Phase**: 8 hours (with monitoring and policy management)
- **Cleanup**: 5 minutes

---

## Notes
- Arc agents enable unified management of on-premises and cloud servers
- Supports Linux and Windows operating systems
- Policy compliance enforcement across hybrid infrastructure
- Centralized monitoring with Azure Monitor
- All operations scoped to single tenant and subscription
- Network connectivity required for agent communication
- Suitable for enterprises with distributed infrastructure
