# Scenario: Managed Identities for Azure Resources

## Technology Area
Security

## Company Profile
- **Company Size**: Small to mid-size enterprise
- **Industry**: Cloud-Native Applications / Microservices
- **Use Case**: Enable secure, credential-free access to Azure resources using managed identities

## Scenario Description
Implement managed identities for Azure resources to enable authentication without storing credentials. This scenario covers system-assigned and user-assigned identities, role assignments, and secure service-to-service communication patterns.

## Azure Services Used
- Azure Managed Identity (System-assigned and User-assigned)
- Azure Virtual Machines
- Azure App Service
- Azure Key Vault
- Azure Storage Account

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Understanding of service principals and managed identities
- Access to create VMs, App Services, and manage roles

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-security-${UNIQUE_ID}-rg"
LOCATION="eastus"
VM_NAME="azurehaymaker-vm-${UNIQUE_ID}"
APP_SERVICE_PLAN="azurehaymaker-asp-${UNIQUE_ID}"
WEB_APP_NAME="azurehaymaker-app-${UNIQUE_ID}"
USER_MANAGED_ID="azurehaymaker-identity-${UNIQUE_ID}"
KEY_VAULT_NAME="azurehaymaker-kv-${UNIQUE_ID}"
STORAGE_ACCOUNT="azurehaymaker${UNIQUE_ID}"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Tags
TAGS="AzureHayMaker-managed=true Scenario=security-managed-identity Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create User-assigned Managed Identity
USER_IDENTITY_ID=$(az identity create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${USER_MANAGED_ID}" \
  --query id -o tsv)

USER_IDENTITY_PRINCIPAL=$(az identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${USER_MANAGED_ID}" \
  --query principalId -o tsv)

# Step 3: Create Key Vault for identity access testing
az keyvault create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEY_VAULT_NAME}" \
  --location "${LOCATION}" \
  --enable-rbac-authorization \
  --tags ${TAGS}

# Step 4: Create Storage Account for identity access testing
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --tags ${TAGS}

# Step 5: Create storage container
az storage container create \
  --account-name "${STORAGE_ACCOUNT}" \
  --name "managed-identity-test"

# Step 6: Create App Service Plan
az appservice plan create \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku B1 \
  --is-linux \
  --tags ${TAGS}

# Step 7: Create Web App with system-assigned identity
az webapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_SERVICE_PLAN}" \
  --name "${WEB_APP_NAME}" \
  --runtime "PYTHON|3.9" \
  --tags ${TAGS}

# Step 8: Enable system-assigned identity on Web App
az webapp identity assign \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --identities [system]

# Step 9: Assign user-assigned identity to Web App
az webapp identity assign \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --identities "${USER_IDENTITY_ID}"

# Step 10: Get system-assigned identity principal ID
SYSTEM_IDENTITY_PRINCIPAL=$(az webapp identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --query principalId -o tsv)

# Step 11: Create SSH key for VM
az sshkey create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "azurehaymaker-key-${UNIQUE_ID}" \
  --tags ${TAGS}

# Step 12: Create Virtual Machine with system-assigned identity
az vm create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --image UbuntuLTS \
  --size Standard_B1s \
  --admin-username azureuser \
  --ssh-key-name "azurehaymaker-key-${UNIQUE_ID}" \
  --assign-identity \
  --tags ${TAGS}

echo "User Identity ID: ${USER_IDENTITY_ID}"
echo "User Identity Principal: ${USER_IDENTITY_PRINCIPAL}"
echo "System Identity Principal (App): ${SYSTEM_IDENTITY_PRINCIPAL}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify user-assigned identity
az identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${USER_MANAGED_ID}"

# Get identity details
az identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${USER_MANAGED_ID}" \
  --query "{principalId: principalId, clientId: clientId, tenantId: tenantId}"

# Verify Web App identities
az webapp identity show --resource-group "${RESOURCE_GROUP}" --name "${WEB_APP_NAME}"

# Verify VM identity
az vm identity show --resource-group "${RESOURCE_GROUP}" --name "${VM_NAME}"

# List all identities in resource group
az identity list --resource-group "${RESOURCE_GROUP}" --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Assign Key Vault Secrets User role to system identity (Web App)
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id "${SYSTEM_IDENTITY_PRINCIPAL}" \
  --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEY_VAULT_NAME}"

# Operation 2: Assign Key Vault Secrets User role to user-assigned identity
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id "${USER_IDENTITY_PRINCIPAL}" \
  --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEY_VAULT_NAME}"

# Operation 3: Assign Storage Blob Data Contributor role to system identity
STORAGE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}"
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee-object-id "${SYSTEM_IDENTITY_PRINCIPAL}" \
  --assignee-principal-type ServicePrincipal \
  --scope "${STORAGE_ID}"

# Operation 4: Assign Storage Blob Data Reader role to user-assigned identity
az role assignment create \
  --role "Storage Blob Data Reader" \
  --assignee-object-id "${USER_IDENTITY_PRINCIPAL}" \
  --assignee-principal-type ServicePrincipal \
  --scope "${STORAGE_ID}"

# Operation 5: Get VM system-assigned identity principal
VM_IDENTITY_PRINCIPAL=$(az vm identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --query principalId -o tsv)

# Operation 6: Assign Storage Account Contributor role to VM identity
az role assignment create \
  --role "Storage Account Contributor" \
  --assignee-object-id "${VM_IDENTITY_PRINCIPAL}" \
  --assignee-principal-type ServicePrincipal \
  --scope "${STORAGE_ID}"

# Operation 7: Add secret to Key Vault for testing
az keyvault secret set \
  --vault-name "${KEY_VAULT_NAME}" \
  --name "managed-identity-test-secret" \
  --value "Secret value for managed identity testing $(openssl rand -hex 8)"

# Operation 8: List role assignments for system identity
az role assignment list \
  --assignee-object-id "${SYSTEM_IDENTITY_PRINCIPAL}" \
  --output table

# Operation 9: List role assignments for user-assigned identity
az role assignment list \
  --assignee-object-id "${USER_IDENTITY_PRINCIPAL}" \
  --output table

# Operation 10: Get access token using user-assigned identity
WEB_APP_IDENTITY_CLIENT=$(az identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${USER_MANAGED_ID}" \
  --query clientId -o tsv)

echo "User-assigned Identity Client ID: ${WEB_APP_IDENTITY_CLIENT}"

# Operation 11: Update VM to use user-assigned identity
az vm identity assign \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --identities "${USER_IDENTITY_ID}"

# Operation 12: Create additional user-assigned identity
SECONDARY_IDENTITY_ID=$(az identity create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "azurehaymaker-secondary-${UNIQUE_ID}" \
  --query id -o tsv)

SECONDARY_PRINCIPAL=$(az identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "azurehaymaker-secondary-${UNIQUE_ID}" \
  --query principalId -o tsv)

# Operation 13: Assign secondary identity to Web App
az webapp identity assign \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --identities "${SECONDARY_IDENTITY_ID}"

# Operation 14: List all identities assigned to Web App
az webapp identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --query userAssignedIdentities
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Remove all role assignments for identities
for PRINCIPAL in "${SYSTEM_IDENTITY_PRINCIPAL}" "${USER_IDENTITY_PRINCIPAL}" "${VM_IDENTITY_PRINCIPAL}" "${SECONDARY_PRINCIPAL}"; do
  for ASSIGNMENT in $(az role assignment list --assignee-object-id "${PRINCIPAL}" --query "[].id" -o tsv); do
    az role assignment delete --ids "${ASSIGNMENT}" || true
  done
done

# Step 2: Remove identities from resources
az webapp identity remove \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --identities "${USER_IDENTITY_ID}" 2>/dev/null || true

az webapp identity remove \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEB_APP_NAME}" \
  --identities "${SECONDARY_IDENTITY_ID}" 2>/dev/null || true

az vm identity remove \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${VM_NAME}" \
  --identities "${USER_IDENTITY_ID}" 2>/dev/null || true

# Step 3: Delete user-assigned identities
az identity delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${USER_MANAGED_ID}" || true

az identity delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "azurehaymaker-secondary-${UNIQUE_ID}" || true

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
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-security-${UNIQUE_ID}-rg`
- User-assigned Identity: `azurehaymaker-identity-${UNIQUE_ID}`
- Virtual Machine: `azurehaymaker-vm-${UNIQUE_ID}`
- App Service Plan: `azurehaymaker-asp-${UNIQUE_ID}`
- Web App: `azurehaymaker-app-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- Storage Account: `azurehaymaker${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Managed Identities Overview](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)
- [Managed Identities for Azure Resources](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
- [How to Use Managed Identities](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/how-to-use-vm-token)
- [System-assigned vs User-assigned Identities](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview#managed-identity-types)
- [Service Principals in Azure](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
- [Managed Identity Best Practices](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/managed-identities-faq)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive managed identity management with straightforward commands for identity creation, assignment, and RBAC configuration. Direct commands enable rapid secure service-to-service communication setup.

---

## Estimated Duration
- **Deployment**: 15-20 minutes
- **Operations Phase**: 8+ hours (with identity management, role assignment, and credential rotation)
- **Cleanup**: 5-10 minutes

---

## Notes
- System-assigned identities are created and destroyed with the resource
- User-assigned identities persist independently and can be reused across resources
- No credentials or secrets stored when using managed identities
- Each managed identity is a service principal in Entra ID
- Role assignments determine permissions for managed identities
- Managed identities automatically handled token lifecycle
- Operations scoped to single subscription with multiple resource integration
- Recommended approach for service-to-service authentication in Azure
