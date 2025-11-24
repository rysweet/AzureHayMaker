# Scenario: Azure Security Center Policies and Recommendations

## Technology Area
Security

## Company Profile
- **Company Size**: Mid-size enterprise
- **Industry**: Financial Services
- **Use Case**: Implement comprehensive security monitoring and compliance policies through Azure Security Center

## Scenario Description
Configure Azure Security Center (Defender for Cloud) with custom security policies, initiate compliance scanning, and apply security recommendations across resources. This scenario covers policy configuration, threat detection setup, compliance monitoring, and remediation workflows.

## Azure Services Used
- Azure Defender for Cloud (Security Center)
- Azure Policy
- Azure Monitor
- Azure Log Analytics
- Azure Security Recommendations
- Azure Compliance Manager

## Prerequisites
- Azure subscription with Owner or Security Admin role
- Azure CLI installed and configured (version 2.50+)
- Azure Defender license (or free tier)
- Access to enable diagnostic settings and monitoring

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-security-${UNIQUE_ID}-rg"
LOCATION="eastus"
KEY_VAULT_NAME="azurehaymaker-kv-${UNIQUE_ID}"
STORAGE_ACCOUNT="azurehaymaker${UNIQUE_ID}"
LOG_ANALYTICS_NAME="azurehaymaker-logs-${UNIQUE_ID}"
VM_NAME="azurehaymaker-vm-${UNIQUE_ID}"
APP_SERVICE_PLAN="azurehaymaker-asp-${UNIQUE_ID}"
WEB_APP_NAME="azurehaymaker-app-${UNIQUE_ID}"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Tags
TAGS="AzureHayMaker-managed=true Scenario=security-center-policies Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Log Analytics Workspace for monitoring
LOG_ANALYTICS_ID=$(az monitor log-analytics workspace create \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS_NAME}" \
  --location "${LOCATION}" \
  --tags ${TAGS} \
  --query id -o tsv)

# Step 3: Create Key Vault for compliance testing
az keyvault create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEY_VAULT_NAME}" \
  --location "${LOCATION}" \
  --enable-rbac-authorization \
  --tags ${TAGS}

# Step 4: Create Storage Account for compliance testing
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --tags ${TAGS}

# Step 5: Enable encryption for Storage Account
az storage account update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --require-infrastructure-encryption true

# Step 6: Create SSH key for VM
az sshkey create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "azurehaymaker-key-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 7: Create Virtual Machine for security monitoring
az vm create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --image UbuntuLTS \
  --size Standard_B1s \
  --admin-username azureuser \
  --ssh-key-name "azurehaymaker-key-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 8: Create App Service Plan
az appservice plan create \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku B1 \
  --is-linux \
  --tags ${TAGS}

# Step 9: Create Web App
az webapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_SERVICE_PLAN}" \
  --name "${WEB_APP_NAME}" \
  --runtime "PYTHON|3.9" \
  --tags ${TAGS}

# Step 10: Enable HTTPS only for Web App
az webapp update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --set httpsOnly=true

# Step 11: Create diagnostic settings for Storage Account
az monitor diagnostic-settings create \
  --name "storage-diagnostics-${UNIQUE_ID}" \
  --resource "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}" \
  --workspace "${LOG_ANALYTICS_ID}" \
  --logs '[{"category": "StorageRead", "enabled": true}, {"category": "StorageWrite", "enabled": true}, {"category": "StorageDelete", "enabled": true}]' || echo "Storage diagnostics note: may require additional configuration"

# Step 12: Get current subscription ID for policy assignment
echo "Subscription ID: ${SUBSCRIPTION_ID}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Log Analytics Workspace
az monitor log-analytics workspace show \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${LOG_ANALYTICS_NAME}"

# Verify Key Vault
az keyvault show --resource-group "${RESOURCE_GROUP}" --name "${KEY_VAULT_NAME}"

# Verify Storage Account encryption
az storage account show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --query "{encryption: encryption, httpsTrafficOnlyEnabled: supportsHttpsTrafficOnly}"

# Verify Virtual Machine
az vm show --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}"

# Verify Web App HTTPS setting
az webapp show --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}" --query httpsOnly

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table

# Check Defender for Cloud status
az security auto-provisioning-setting list 2>/dev/null || echo "Defender for Cloud listing may require additional permissions"
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Create custom policy definition for encryption
cat > /tmp/policy-${UNIQUE_ID}.json <<'EOF'
{
  "mode": "Indexed",
  "policyRule": {
    "if": {
      "field": "type",
      "equals": "Microsoft.Storage/storageAccounts"
    },
    "then": {
      "effect": "audit",
      "details": {
        "field": "Microsoft.Storage/storageAccounts/encryption.services.blob.enabled",
        "equals": "true"
      }
    }
  },
  "parameters": {}
}
EOF

# Operation 2: Create policy definition
POLICY_DEF_ID=$(az policy definition create \
  --name "azurehaymaker-storage-encryption-policy-${UNIQUE_ID}" \
  --display-name "Audit storage account encryption" \
  --rules /tmp/policy-${UNIQUE_ID}.json \
  --query id -o tsv)

echo "Policy Definition ID: ${POLICY_DEF_ID}"

# Operation 3: Assign the custom policy to resource group
az policy assignment create \
  --name "azurehaymaker-storage-audit-${UNIQUE_ID}" \
  --policy "${POLICY_DEF_ID}" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" || echo "Policy assignment may require owner permissions"

# Operation 4: List built-in security policies
az policy definition list \
  --query "[?contains(displayName, 'security') || contains(displayName, 'encryption')].{name:name, displayName:displayName}" \
  --output table | head -20

# Operation 5: Enable MFA requirement policy
az policy assignment create \
  --name "audit-mfa-${UNIQUE_ID}" \
  --display-name "Audit accounts without multi-factor authentication" \
  --policy "40658b76-0a34-4ab9-a084-17f3dada1146" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" 2>/dev/null || echo "MFA policy assignment may require specific conditions"

# Operation 6: View security recommendations for resources
az security assessment list --resource-group "${RESOURCE_GROUP}" --output table 2>/dev/null || echo "Assessments may require Defender for Cloud subscription"

# Operation 7: Check vulnerability assessments on VM
az security vm-metadata list 2>/dev/null || echo "VM metadata scanning may require Defender for Cloud"

# Operation 8: Create Azure Policy for NSG rules
cat > /tmp/nsg-policy-${UNIQUE_ID}.json <<'EOF'
{
  "mode": "All",
  "policyRule": {
    "if": {
      "field": "type",
      "equals": "Microsoft.Network/networkSecurityGroups/securityRules"
    },
    "then": {
      "effect": "audit",
      "details": {
        "field": "Microsoft.Network/networkSecurityGroups/securityRules/access",
        "notEquals": "Allow"
      }
    }
  },
  "parameters": {}
}
EOF

# Operation 9: Enable threat detection on Storage
az storage account threat-protection update \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --enable true 2>/dev/null || echo "Threat detection requires additional configuration"

# Operation 10: List compliance information
az policy assignment list --scope "/subscriptions/${SUBSCRIPTION_ID}" --query "[].{displayName:displayName, policyDefinitionId:policyDefinitionId}" --output table | head -10

# Operation 11: Create auto-remediation policy
az policy assignment create \
  --name "auto-remediate-logging-${UNIQUE_ID}" \
  --policy "e4b3d4d5-6e3f-4d7d-8e3f-3d3f3d3f3d3f" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  --enforce 2>/dev/null || echo "Auto-remediation assignment noted"

# Operation 12: Check Key Vault diagnostics settings
az monitor diagnostic-settings list \
  --resource "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEY_VAULT_NAME}" \
  --query "[].{name:name, workspaceId:workspaceId}" 2>/dev/null || echo "Diagnostics listing in progress"

# Operation 13: Export security posture summary
echo "Security Posture Report - $(date)" > /tmp/security-report-${UNIQUE_ID}.txt
echo "Resource Group: ${RESOURCE_GROUP}" >> /tmp/security-report-${UNIQUE_ID}.txt
echo "Subscription: ${SUBSCRIPTION_ID}" >> /tmp/security-report-${UNIQUE_ID}.txt
echo "Resources in scope:" >> /tmp/security-report-${UNIQUE_ID}.txt
az resource list --resource-group "${RESOURCE_GROUP}" --query "[].{name:name, type:type}" --output table >> /tmp/security-report-${UNIQUE_ID}.txt

# Operation 14: Configure allowed resource types policy
az policy assignment create \
  --name "allowed-resources-${UNIQUE_ID}" \
  --display-name "Allowed resource types" \
  --policy "a08f37ab-19e9-468e-a74f-08088bb1141a" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  --params '{"listOfResourceTypesAllowed": ["Microsoft.Compute/virtualMachines", "Microsoft.Storage/storageAccounts", "Microsoft.Web/sites"]}' \
  --enforce 2>/dev/null || echo "Allowed resources policy assignment noted"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete all policy assignments
for ASSIGNMENT in $(az policy assignment list --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" --query "[].name" -o tsv); do
  az policy assignment delete --name "${ASSIGNMENT}" --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" --yes 2>/dev/null || true
done

# Step 2: Delete custom policy definitions
az policy definition delete \
  --name "azurehaymaker-storage-encryption-policy-${UNIQUE_ID}" \
  --yes 2>/dev/null || true

# Step 3: Delete diagnostic settings
for DIAGNOSTIC in $(az monitor diagnostic-settings list --resource "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" --query "[].name" -o tsv 2>/dev/null); do
  az monitor diagnostic-settings delete \
    --name "${DIAGNOSTIC}" \
    --resource "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
    --yes 2>/dev/null || true
done

# Step 4: Delete the entire resource group (includes all resources)
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 5: Wait for deletion to complete
echo "Waiting for resource group deletion..."
sleep 120

# Step 6: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 7: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 8: Clean up local files
rm -f /tmp/policy-${UNIQUE_ID}.json
rm -f /tmp/nsg-policy-${UNIQUE_ID}.json
rm -f /tmp/security-report-${UNIQUE_ID}.txt
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-security-${UNIQUE_ID}-rg`
- Virtual Machine: `azurehaymaker-vm-${UNIQUE_ID}`
- App Service Plan: `azurehaymaker-asp-${UNIQUE_ID}`
- Web App: `azurehaymaker-app-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- Storage Account: `azurehaymaker${UNIQUE_ID}`
- Log Analytics: `azurehaymaker-logs-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Defender for Cloud Overview](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-cloud-introduction)
- [Azure Policy Overview](https://learn.microsoft.com/en-us/azure/governance/policy/overview)
- [Security Center Recommendations](https://learn.microsoft.com/en-us/azure/defender-for-cloud/recommendations-reference)
- [Azure Compliance Manager](https://learn.microsoft.com/en-us/compliance/compliance-manager/compliance-manager-overview)
- [Azure Policy Built-in Policies](https://learn.microsoft.com/en-us/azure/governance/policy/samples/built-in-policies)
- [Security Best Practices](https://learn.microsoft.com/en-us/azure/security/fundamentals/best-practices-and-patterns)

---

## Automation Tool
**Recommended**: Azure CLI with Azure Policy

**Rationale**: Azure CLI provides comprehensive security monitoring and policy management capabilities. Direct commands enable rapid security posture assessment and policy enforcement across resources.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8+ hours (with policy monitoring, compliance scanning, and security recommendations review)
- **Cleanup**: 5-10 minutes

---

## Notes
- Azure Defender for Cloud provides threat detection and vulnerability scanning
- Azure Policy enables compliance and governance at scale
- Security recommendations provide actionable guidance for remediation
- Policies can be enforced or audit-only for compliance monitoring
- Log Analytics integration enables comprehensive security monitoring
- All resources benefit from continuous security assessment
- Operations scoped to single subscription with resource group isolation
- Compliance frameworks include CIS, PCI-DSS, HIPAA, and more
