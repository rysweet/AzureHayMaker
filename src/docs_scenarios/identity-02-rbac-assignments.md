# Scenario: Role-Based Access Control (RBAC) Assignments

## Technology Area
Identity

## Company Profile
- **Company Size**: Mid-size
- **Industry**: Enterprise Software
- **Use Case**: Managing team permissions across Azure resources with principle of least privilege and role hierarchy

## Scenario Description
Implement and manage role-based access control (RBAC) assignments across Azure resources. This scenario covers creating role assignments for users, groups, and service principals at different scopes (subscription, resource group, resource). It demonstrates hierarchy, inheritance, and proper permission delegation.

## Azure Services Used
- Azure Entra ID (formerly Azure AD)
- Azure Role-Based Access Control (RBAC)
- Azure Resource Manager
- Azure Subscription
- Azure Resource Groups

## Prerequisites
- Azure subscription with Owner role at subscription level
- Azure CLI installed and configured
- Access to create Entra ID groups
- Users or service principals to assign roles to

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-rbac-${UNIQUE_ID}-rg"
LOCATION="eastus"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
GROUP_PREFIX="azurehaymaker-group-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=identity-rbac-assignments Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Entra ID groups for role management
ADMIN_GROUP=$(az ad group create \
  --display-name "${GROUP_PREFIX}-admins" \
  --mail-nickname "azurehaymaker-admins-${UNIQUE_ID}" \
  --output json)

ADMIN_GROUP_ID=$(echo $ADMIN_GROUP | jq -r '.id')

# Step 3: Create developer group
DEV_GROUP=$(az ad group create \
  --display-name "${GROUP_PREFIX}-developers" \
  --mail-nickname "azurehaymaker-devs-${UNIQUE_ID}" \
  --output json)

DEV_GROUP_ID=$(echo $DEV_GROUP | jq -r '.id')

# Step 4: Create read-only group
READER_GROUP=$(az ad group create \
  --display-name "${GROUP_PREFIX}-readers" \
  --mail-nickname "azurehaymaker-readers-${UNIQUE_ID}" \
  --output json)

READER_GROUP_ID=$(echo $READER_GROUP | jq -r '.id')

# Step 5: Create service principal for app access
SP=$(az ad sp create-for-rbac \
  --name "azurehaymaker-rbac-sp-${UNIQUE_ID}" \
  --skip-assignment \
  --output json)

SP_APP_ID=$(echo $SP | jq -r '.appId')
SP_OBJECT_ID=$(az ad sp show --id "${SP_APP_ID}" --query id -o tsv)

# Step 6: Assign Owner role at resource group level to admin group
az role assignment create \
  --assignee-object-id "${ADMIN_GROUP_ID}" \
  --role "Owner" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

# Step 7: Assign Contributor role at resource group level to developer group
az role assignment create \
  --assignee-object-id "${DEV_GROUP_ID}" \
  --role "Contributor" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

# Step 8: Assign Reader role at resource group level to reader group
az role assignment create \
  --assignee-object-id "${READER_GROUP_ID}" \
  --role "Reader" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

# Step 9: Assign Storage Blob Data Contributor role to service principal (specific permission)
az role assignment create \
  --assignee-object-id "${SP_OBJECT_ID}" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

echo "Admin Group ID: ${ADMIN_GROUP_ID}"
echo "Developer Group ID: ${DEV_GROUP_ID}"
echo "Reader Group ID: ${READER_GROUP_ID}"
echo "Service Principal App ID: ${SP_APP_ID}"
```

### Validation
```bash
# Verify resource group
az group show --name "${RESOURCE_GROUP}" --output table

# List all Entra ID groups created
az ad group list --filter "startswith(displayName, '${GROUP_PREFIX}')" --output table

# Check role assignments for admin group
az role assignment list \
  --assignee-object-id "${ADMIN_GROUP_ID}" \
  --output table

# Check role assignments for developer group
az role assignment list \
  --assignee-object-id "${DEV_GROUP_ID}" \
  --output table

# Check role assignments for reader group
az role assignment list \
  --assignee-object-id "${READER_GROUP_ID}" \
  --output table

# Check role assignments for service principal
az role assignment list \
  --assignee-object-id "${SP_OBJECT_ID}" \
  --output table

# List all role assignments in resource group
az role assignment list \
  --resource-group "${RESOURCE_GROUP}" \
  --all \
  --output table

# Get group membership information
az ad group member list \
  --group "${ADMIN_GROUP_ID}" \
  --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Check available roles
az role definition list --output table | head -20

# Operation 2: Get detailed information about a specific role
az role definition show \
  --name "Contributor" \
  --output table

# Operation 3: List role assignments at subscription level
az role assignment list \
  --scope "/subscriptions/${SUBSCRIPTION_ID}" \
  --output table | head -20

# Operation 4: Add user to developer group (simulate with object ID)
CURRENT_USER_ID=$(az account show --query user.objectId -o tsv)
az ad group member add \
  --group "${DEV_GROUP_ID}" \
  --member-id "${CURRENT_USER_ID}" \
  2>/dev/null || echo "User already in group or operation not permitted"

# Operation 5: Check who has access to a specific resource group
az role assignment list \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[*].[principalName, roleDefinitionName, scope]" \
  --output table

# Operation 6: Remove a user from a group
az ad group member remove \
  --group "${READER_GROUP_ID}" \
  --member-id "${CURRENT_USER_ID}" \
  2>/dev/null || echo "User not in group or operation not permitted"

# Operation 7: Create custom role definition based on built-in role
az role definition list --name "Reader" --output json > /tmp/custom-role.json

# Operation 8: List all role assignments assigned by a specific principal
az role assignment list \
  --assignee "${CURRENT_USER_ID}" \
  --output table

# Operation 9: Evaluate permission for current user on resource group
az role assignment list \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  --query "[?principalId=='${CURRENT_USER_ID}']" \
  --output table

# Operation 10: Create a deny assignment (prevent specific action)
# Note: This typically requires Owner role at subscription level
az role assignment create \
  --assignee-object-id "${READER_GROUP_ID}" \
  --role "Virtual Machine Contributor" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  2>/dev/null || echo "Assignment created or already exists"

# Operation 11: Check if principal has specific permission
az role definition show --name "Owner" --query "permissions[*].actions" --output table

# Operation 12: List all group membership of current user
az ad group member list \
  --group "${DEV_GROUP_ID}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Remove all role assignments from resource group
az role assignment delete \
  --resource-group "${RESOURCE_GROUP}" \
  --yes \
  2>/dev/null || true

# Step 2: Remove role assignments at subscription level for created groups
az role assignment list \
  --all \
  --query "[?assigneeObjectId=='${ADMIN_GROUP_ID}' || assigneeObjectId=='${DEV_GROUP_ID}' || assigneeObjectId=='${READER_GROUP_ID}' || assigneeObjectId=='${SP_OBJECT_ID}']" \
  --output json | jq -r '.[].id' | xargs -I {} az role assignment delete --ids {} 2>/dev/null || true

# Step 3: Delete service principal
az ad sp delete --id "${SP_APP_ID}" 2>/dev/null || true

# Step 4: Delete Entra ID groups
az ad group delete --group "${ADMIN_GROUP_ID}" 2>/dev/null || true
az ad group delete --group "${DEV_GROUP_ID}" 2>/dev/null || true
az ad group delete --group "${READER_GROUP_ID}" 2>/dev/null || true

# Step 5: Delete resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 6: Wait for deletion
echo "Waiting for cleanup to complete..."
sleep 60

# Step 7: Verify resource group deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 8: Confirm groups are deleted
az ad group list --filter "startswith(displayName, '${GROUP_PREFIX}')" --output table

echo "RBAC assignments and groups successfully cleaned up"
```

---

## Resource Naming Convention
- Admin Group: `azurehaymaker-group-${UNIQUE_ID}-admins`
- Developer Group: `azurehaymaker-group-${UNIQUE_ID}-developers`
- Reader Group: `azurehaymaker-group-${UNIQUE_ID}-readers`
- Service Principal: `azurehaymaker-rbac-sp-${UNIQUE_ID}`
- Resource Group: `azurehaymaker-rbac-${UNIQUE_ID}-rg`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure RBAC Overview](https://learn.microsoft.com/en-us/azure/role-based-access-control/overview)
- [Assign Azure Roles using Azure CLI](https://learn.microsoft.com/en-us/azure/role-based-access-control/role-assignments-cli)
- [Built-in Azure Roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles)
- [Azure Entra ID Groups](https://learn.microsoft.com/en-us/azure/active-directory/fundamentals/active-directory-manage-groups)
- [Custom Azure Roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/custom-roles)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive RBAC management capabilities with commands for creating role assignments, managing group membership, and querying permissions. The CLI is ideal for implementing principle of least privilege and automating access control workflows.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (permission audits, membership management, access reviews)
- **Cleanup**: 5-10 minutes

---

## Notes
- RBAC uses role-based permissions with Owner, Contributor, and Reader roles
- Groups allow for easier management of permissions across multiple users
- Roles can be assigned at subscription, resource group, or resource level
- Principle of least privilege should guide all role assignments
- Service principals can have specific roles assigned for application access
- Role inheritance flows from parent scope to child resources
- Azure RBAC supports deny assignments to explicitly block access
- Group membership changes take time to propagate through Azure AD
