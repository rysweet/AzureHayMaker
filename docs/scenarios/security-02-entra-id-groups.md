# Scenario: Entra ID Groups and Role Assignments

## Technology Area
Security

## Company Profile
- **Company Size**: Mid-size enterprise
- **Industry**: Enterprise Software / Consulting
- **Use Case**: Manage user access through Azure AD groups with role-based access control to Azure resources

## Scenario Description
Create and manage Azure Entra ID (formerly Azure AD) groups with hierarchical organization, assign role-based access to Azure resources, and manage membership. This scenario covers group creation, role assignment, access management, and compliance auditing.

## Azure Services Used
- Azure Entra ID (Azure AD)
- Azure Role-Based Access Control (RBAC)
- Azure Key Vault (for access validation)
- Azure App Service (for access validation)

## Prerequisites
- Azure subscription with Owner or User Access Administrator role
- Azure CLI installed and configured (version 2.40+)
- Microsoft Graph CLI (optional, for advanced AD operations)
- User with Entra ID administrator permissions

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
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Entra ID Groups
ADMIN_GROUP="azurehaymaker-admins-${UNIQUE_ID}"
DEVELOPER_GROUP="azurehaymaker-developers-${UNIQUE_ID}"
READER_GROUP="azurehaymaker-readers-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=security-entra-id-groups Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Key Vault for role-based access testing
az keyvault create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${KEY_VAULT_NAME}" \
  --location "${LOCATION}" \
  --enable-rbac-authorization \
  --tags ${TAGS}

# Step 3: Create Storage Account for role-based access testing
az storage account create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${STORAGE_ACCOUNT}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --tags ${TAGS}

# Step 4: Create Entra ID Admin Group
ADMIN_GROUP_ID=$(az ad group create \
  --display-name "${ADMIN_GROUP}" \
  --mail-nickname "azurehaymaker-admins-${UNIQUE_ID}" \
  --query id -o tsv)

# Step 5: Create Entra ID Developer Group
DEVELOPER_GROUP_ID=$(az ad group create \
  --display-name "${DEVELOPER_GROUP}" \
  --mail-nickname "azurehaymaker-developers-${UNIQUE_ID}" \
  --query id -o tsv)

# Step 6: Create Entra ID Reader Group
READER_GROUP_ID=$(az ad group create \
  --display-name "${READER_GROUP}" \
  --mail-nickname "azurehaymaker-readers-${UNIQUE_ID}" \
  --query id -o tsv)

# Step 7: Assign Owner role to Admin Group on Resource Group
az role assignment create \
  --role "Owner" \
  --assignee-object-id "${ADMIN_GROUP_ID}" \
  --assignee-principal-type Group \
  --resource-group "${RESOURCE_GROUP}"

# Step 8: Assign Contributor role to Developer Group on Resource Group
az role assignment create \
  --role "Contributor" \
  --assignee-object-id "${DEVELOPER_GROUP_ID}" \
  --assignee-principal-type Group \
  --resource-group "${RESOURCE_GROUP}"

# Step 9: Assign Reader role to Reader Group on Resource Group
az role assignment create \
  --role "Reader" \
  --assignee-object-id "${READER_GROUP_ID}" \
  --assignee-principal-type Group \
  --resource-group "${RESOURCE_GROUP}"

# Step 10: Assign Key Vault Secrets Officer role to Admin Group
az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee-object-id "${ADMIN_GROUP_ID}" \
  --assignee-principal-type Group \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEY_VAULT_NAME}"

# Step 11: Assign Key Vault Secrets User role to Developer Group
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id "${DEVELOPER_GROUP_ID}" \
  --assignee-principal-type Group \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEY_VAULT_NAME}"

# Step 12: Assign Storage Account Contributor role to Developer Group
STORAGE_RESOURCE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}"
az role assignment create \
  --role "Storage Account Contributor" \
  --assignee-object-id "${DEVELOPER_GROUP_ID}" \
  --assignee-principal-type Group \
  --scope "${STORAGE_RESOURCE_ID}"

echo "Admin Group ID: ${ADMIN_GROUP_ID}"
echo "Developer Group ID: ${DEVELOPER_GROUP_ID}"
echo "Reader Group ID: ${READER_GROUP_ID}"
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Entra ID Groups exist
az ad group list --filter "displayName eq '${ADMIN_GROUP}'" --output table
az ad group list --filter "displayName eq '${DEVELOPER_GROUP}'" --output table
az ad group list --filter "displayName eq '${READER_GROUP}'" --output table

# List role assignments on Resource Group
az role assignment list --resource-group "${RESOURCE_GROUP}" --output table

# List role assignments on Key Vault
az role assignment list \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.KeyVault/vaults/${KEY_VAULT_NAME}" \
  --output table

# List role assignments on Storage Account
az role assignment list \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}" \
  --output table

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table

# Get group details
az ad group show --id "${ADMIN_GROUP_ID}"
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Get current user object ID for testing
CURRENT_USER_OID=$(az ad signed-in-user show --query objectId -o tsv)

# Operation 2: Add current user to Admin Group
az ad group member add \
  --group "${ADMIN_GROUP_ID}" \
  --member-id "${CURRENT_USER_OID}"

# Operation 3: Add current user to Developer Group
az ad group member add \
  --group "${DEVELOPER_GROUP_ID}" \
  --member-id "${CURRENT_USER_OID}"

# Operation 4: List members of Admin Group
az ad group member list --group "${ADMIN_GROUP_ID}" --output table

# Operation 5: List members of Developer Group
az ad group member list --group "${DEVELOPER_GROUP_ID}" --output table

# Operation 6: Create a second group for nested membership
NESTED_GROUP="azurehaymaker-nested-${UNIQUE_ID}"
NESTED_GROUP_ID=$(az ad group create \
  --display-name "${NESTED_GROUP}" \
  --mail-nickname "azurehaymaker-nested-${UNIQUE_ID}" \
  --query id -o tsv)

# Operation 7: Add Developer Group as member to Admin Group (nested membership)
az ad group member add \
  --group "${ADMIN_GROUP_ID}" \
  --member-id "${DEVELOPER_GROUP_ID}"

# Operation 8: Check role assignments for current user
az role assignment list \
  --assignee "${CURRENT_USER_OID}" \
  --output table

# Operation 9: Deny specific action on resource for Developer Group
az role assignment create \
  --role "Reader" \
  --assignee-object-id "${READER_GROUP_ID}" \
  --assignee-principal-type Group \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  --condition "((!(ActionMatches{'Microsoft.Storage/storageAccounts/write','Microsoft.Storage/storageAccounts/delete'})) OR (@Resource[Microsoft.Authorization/locks/level] StringEquals 'CanNotDelete'))" \
  --condition-version "2.0" || echo "Condition-based RBAC not available in current CLI version"

# Operation 10: List all roles assigned to a group
az role assignment list --assignee-object-id "${DEVELOPER_GROUP_ID}" --output table

# Operation 11: Remove user from Developer Group
az ad group member remove \
  --group "${DEVELOPER_GROUP_ID}" \
  --member-id "${CURRENT_USER_OID}"

# Operation 12: Update group membership with batch operation
# Create additional test group
TEST_GROUP="azurehaymaker-test-${UNIQUE_ID}"
TEST_GROUP_ID=$(az ad group create \
  --display-name "${TEST_GROUP}" \
  --mail-nickname "azurehaymaker-test-${UNIQUE_ID}" \
  --query id -o tsv)

# Assign Reader role to Test Group
az role assignment create \
  --role "Reader" \
  --assignee-object-id "${TEST_GROUP_ID}" \
  --assignee-principal-type Group \
  --resource-group "${RESOURCE_GROUP}"

# Operation 13: List all Entra ID groups in tenant
az ad group list --output table

# Operation 14: Export group membership for compliance report
echo "Group Membership Report - $(date)" > /tmp/group-report-${UNIQUE_ID}.txt
echo "Admin Group Members:" >> /tmp/group-report-${UNIQUE_ID}.txt
az ad group member list --group "${ADMIN_GROUP_ID}" --output table >> /tmp/group-report-${UNIQUE_ID}.txt
echo "Developer Group Members:" >> /tmp/group-report-${UNIQUE_ID}.txt
az ad group member list --group "${DEVELOPER_GROUP_ID}" --output table >> /tmp/group-report-${UNIQUE_ID}.txt
cat /tmp/group-report-${UNIQUE_ID}.txt
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Remove all group members
for GROUP_ID in "${ADMIN_GROUP_ID}" "${DEVELOPER_GROUP_ID}" "${READER_GROUP_ID}"; do
  for MEMBER in $(az ad group member list --group "${GROUP_ID}" --query "[].id" -o tsv); do
    az ad group member remove \
      --group "${GROUP_ID}" \
      --member-id "${MEMBER}" || true
  done
done

# Step 2: Delete all Entra ID groups
az ad group delete --id "${ADMIN_GROUP_ID}" || true
az ad group delete --id "${DEVELOPER_GROUP_ID}" || true
az ad group delete --id "${READER_GROUP_ID}" || true
az ad group delete --id "${NESTED_GROUP_ID}" 2>/dev/null || true
az ad group delete --id "${TEST_GROUP_ID}" 2>/dev/null || true

# Step 3: Remove all role assignments from resource group
for ASSIGNMENT in $(az role assignment list --resource-group "${RESOURCE_GROUP}" --query "[].id" -o tsv); do
  az role assignment delete --ids "${ASSIGNMENT}" || true
done

# Step 4: Delete the entire resource group (includes Key Vault, Storage, etc.)
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
rm -f /tmp/group-report-*.txt
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-security-${UNIQUE_ID}-rg`
- Admin Group: `azurehaymaker-admins-${UNIQUE_ID}`
- Developer Group: `azurehaymaker-developers-${UNIQUE_ID}`
- Reader Group: `azurehaymaker-readers-${UNIQUE_ID}`
- Key Vault: `azurehaymaker-kv-${UNIQUE_ID}`
- Storage Account: `azurehaymaker${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Entra ID Overview](https://learn.microsoft.com/en-us/azure/active-directory/fundamentals/active-directory-whatis)
- [Azure Groups and Members](https://learn.microsoft.com/en-us/azure/active-directory/fundamentals/how-to-manage-groups)
- [Azure Role-Based Access Control (RBAC)](https://learn.microsoft.com/en-us/azure/role-based-access-control/overview)
- [Built-in Azure Roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles)
- [Azure CLI AD Commands](https://learn.microsoft.com/en-us/cli/azure/ad)
- [Azure RBAC Best Practices](https://learn.microsoft.com/en-us/azure/role-based-access-control/best-practices)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive Entra ID and RBAC management capabilities for group lifecycle and role assignment operations. Direct commands enable rapid access control provisioning and governance.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (with membership management, role auditing, and compliance reviews)
- **Cleanup**: 5-10 minutes

---

## Notes
- Entra ID groups support nested membership for hierarchical access structures
- RBAC provides least-privilege access model with fine-grained role control
- Role assignments inherit from resource group to contained resources
- Groups can be used across subscriptions within the same tenant
- Managed identity groups cannot be manually managed
- Operations scoped to single tenant with multiple resource groups support
- Audit logs track all group membership and role assignment changes
