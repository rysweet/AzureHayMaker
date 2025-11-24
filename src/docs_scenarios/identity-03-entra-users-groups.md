# Scenario: Managing Entra ID Users and Groups

## Technology Area
Identity

## Company Profile
- **Company Size**: Mid-size
- **Industry**: Technology Consulting
- **Use Case**: Manage corporate user identities, group memberships, and organizational structure in cloud directory

## Scenario Description
Create and manage Entra ID (Azure AD) users and groups representing corporate organizational structure. This scenario covers user provisioning, group creation, dynamic membership rules, and lifecycle management of identities within an enterprise directory.

## Azure Services Used
- Azure Entra ID (formerly Azure AD)
- Azure AD Groups
- User Management
- Azure CLI
- Directory Services

## Prerequisites
- Azure subscription with Global Administrator or User Administrator role
- Azure CLI installed and configured
- Appropriate permissions to create users and groups in Entra ID
- Optional: Custom domain configured (for realistic email scenarios)

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-users-${UNIQUE_ID}-rg"
LOCATION="eastus"
TENANT_ID=$(az account show --query tenantId -o tsv)
USER_PREFIX="azurehaymaker-user-${UNIQUE_ID}"
GROUP_PREFIX="azurehaymaker-group-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=identity-entra-users-groups Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group for organizational resources
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create first Entra ID user
USER_01=$(az ad user create \
  --display-name "AzureHayMaker Test User 01" \
  --user-principal-name "${USER_PREFIX}-01@contoso.onmicrosoft.com" \
  --password "TempPassword123!@#" \
  --force-change-password-next-sign-in false \
  --output json)

USER_01_ID=$(echo $USER_01 | jq -r '.id')
USER_01_UPN=$(echo $USER_01 | jq -r '.userPrincipalName')

# Step 3: Create second Entra ID user
USER_02=$(az ad user create \
  --display-name "AzureHayMaker Test User 02" \
  --user-principal-name "${USER_PREFIX}-02@contoso.onmicrosoft.com" \
  --password "TempPassword123!@#" \
  --force-change-password-next-sign-in true \
  --output json)

USER_02_ID=$(echo $USER_02 | jq -r '.id')

# Step 4: Create third Entra ID user
USER_03=$(az ad user create \
  --display-name "AzureHayMaker Test User 03" \
  --user-principal-name "${USER_PREFIX}-03@contoso.onmicrosoft.com" \
  --password "TempPassword123!@#" \
  --output json)

USER_03_ID=$(echo $USER_03 | jq -r '.id')

# Step 5: Create security group for engineers
ENG_GROUP=$(az ad group create \
  --display-name "${GROUP_PREFIX}-engineers" \
  --mail-nickname "azurehaymaker-engineers-${UNIQUE_ID}" \
  --output json)

ENG_GROUP_ID=$(echo $ENG_GROUP | jq -r '.id')

# Step 6: Create security group for managers
MGR_GROUP=$(az ad group create \
  --display-name "${GROUP_PREFIX}-managers" \
  --mail-nickname "azurehaymaker-managers-${UNIQUE_ID}" \
  --output json)

MGR_GROUP_ID=$(echo $MGR_GROUP | jq -r '.id')

# Step 7: Create organization group
ORG_GROUP=$(az ad group create \
  --display-name "${GROUP_PREFIX}-organization" \
  --mail-nickname "azurehaymaker-org-${UNIQUE_ID}" \
  --output json)

ORG_GROUP_ID=$(echo $ORG_GROUP | jq -r '.id')

# Step 8: Add users to groups
az ad group member add \
  --group "${ENG_GROUP_ID}" \
  --member-id "${USER_01_ID}"

az ad group member add \
  --group "${ENG_GROUP_ID}" \
  --member-id "${USER_02_ID}"

az ad group member add \
  --group "${MGR_GROUP_ID}" \
  --member-id "${USER_03_ID}"

# Step 9: Add groups to organization group (nested groups)
az ad group member add \
  --group "${ORG_GROUP_ID}" \
  --member-id "${ENG_GROUP_ID}"

az ad group member add \
  --group "${ORG_GROUP_ID}" \
  --member-id "${MGR_GROUP_ID}"

echo "User 1 ID: ${USER_01_ID} - UPN: ${USER_01_UPN}"
echo "User 2 ID: ${USER_02_ID}"
echo "User 3 ID: ${USER_03_ID}"
echo "Engineers Group ID: ${ENG_GROUP_ID}"
echo "Managers Group ID: ${MGR_GROUP_ID}"
echo "Organization Group ID: ${ORG_GROUP_ID}"
```

### Validation
```bash
# Verify resource group
az group show --name "${RESOURCE_GROUP}" --output table

# List all created users
az ad user list --filter "startswith(displayName, 'AzureHayMaker')" --output table

# Get details of first user
az ad user show --id "${USER_01_ID}" --output table

# Get details of second user
az ad user show --id "${USER_02_ID}" --output table

# Get details of third user
az ad user show --id "${USER_03_ID}" --output table

# List all created groups
az ad group list --filter "startswith(displayName, '${GROUP_PREFIX}')" --output table

# List members of engineers group
az ad group member list --group "${ENG_GROUP_ID}" --output table

# List members of managers group
az ad group member list --group "${MGR_GROUP_ID}" --output table

# List members of organization group (nested)
az ad group member list --group "${ORG_GROUP_ID}" --output table

# Verify user properties
az ad user list --query "[].{DisplayName:displayName, UserPrincipalName:userPrincipalName, Id:id}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Update user display name
az ad user update \
  --id "${USER_01_ID}" \
  --display-name "AzureHayMaker Senior Engineer 01"

# Operation 2: Get user account status
az ad user show \
  --id "${USER_02_ID}" \
  --query "[displayName, accountEnabled, userPrincipalName]" \
  --output table

# Operation 3: Disable a user account
az ad user update \
  --id "${USER_03_ID}" \
  --account-enabled false

# Operation 4: Re-enable a user account
az ad user update \
  --id "${USER_03_ID}" \
  --account-enabled true

# Operation 5: Reset user password
az ad user update \
  --id "${USER_02_ID}" \
  --password "NewTempPassword456!@#"

# Operation 6: Remove user from group
az ad group member remove \
  --group "${ENG_GROUP_ID}" \
  --member-id "${USER_02_ID}"

# Operation 7: Add user to multiple groups
az ad group member add \
  --group "${ENG_GROUP_ID}" \
  --member-id "${USER_02_ID}"

az ad group member add \
  --group "${MGR_GROUP_ID}" \
  --member-id "${USER_02_ID}"

# Operation 8: List all groups a user belongs to
az ad user get-member-groups \
  --id "${USER_01_ID}" \
  --output table

# Operation 9: Query users by property
az ad user list \
  --filter "startswith(displayName, 'AzureHayMaker')" \
  --query "[].{Name:displayName, UPN:userPrincipalName}" \
  --output table

# Operation 10: Count members in a group
az ad group member list \
  --group "${ENG_GROUP_ID}" \
  --query "length([*])" \
  --output tsv

# Operation 11: Export group membership
az ad group member list \
  --group "${ORG_GROUP_ID}" \
  --query "[].{DisplayName:displayName, Type:objectType, Id:id}" \
  --output table

# Operation 12: Check user properties for last sign-in and other details
az ad user list \
  --filter "startswith(displayName, 'AzureHayMaker')" \
  --query "[].{DisplayName:displayName, Enabled:accountEnabled}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Remove users from all groups
az ad group member remove \
  --group "${ENG_GROUP_ID}" \
  --member-id "${USER_01_ID}" \
  2>/dev/null || true

az ad group member remove \
  --group "${ENG_GROUP_ID}" \
  --member-id "${USER_02_ID}" \
  2>/dev/null || true

az ad group member remove \
  --group "${MGR_GROUP_ID}" \
  --member-id "${USER_03_ID}" \
  2>/dev/null || true

# Step 2: Remove nested group membership
az ad group member remove \
  --group "${ORG_GROUP_ID}" \
  --member-id "${ENG_GROUP_ID}" \
  2>/dev/null || true

az ad group member remove \
  --group "${ORG_GROUP_ID}" \
  --member-id "${MGR_GROUP_ID}" \
  2>/dev/null || true

# Step 3: Delete groups
az ad group delete --group "${ENG_GROUP_ID}" 2>/dev/null || true
az ad group delete --group "${MGR_GROUP_ID}" 2>/dev/null || true
az ad group delete --group "${ORG_GROUP_ID}" 2>/dev/null || true

# Step 4: Delete users
az ad user delete --id "${USER_01_ID}" 2>/dev/null || true
az ad user delete --id "${USER_02_ID}" 2>/dev/null || true
az ad user delete --id "${USER_03_ID}" 2>/dev/null || true

# Step 5: Delete resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 6: Wait for deletion
echo "Waiting for cleanup to complete..."
sleep 60

# Step 7: Verify users are deleted
az ad user list --filter "startswith(displayName, 'AzureHayMaker')" --output table

# Step 8: Verify groups are deleted
az ad group list --filter "startswith(displayName, '${GROUP_PREFIX}')" --output table

echo "Users and groups successfully cleaned up"
```

---

## Resource Naming Convention
- Users: `${USER_PREFIX}-[01-03]@contoso.onmicrosoft.com`
- Engineers Group: `${GROUP_PREFIX}-engineers`
- Managers Group: `${GROUP_PREFIX}-managers`
- Organization Group: `${GROUP_PREFIX}-organization`
- Resource Group: `azurehaymaker-users-${UNIQUE_ID}-rg`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Manage Users in Entra ID](https://learn.microsoft.com/en-us/azure/active-directory/fundamentals/how-to-create-delete-users-azure-ad)
- [Manage Groups in Entra ID](https://learn.microsoft.com/en-us/azure/active-directory/fundamentals/how-to-manage-groups)
- [Group Membership Rules](https://learn.microsoft.com/en-us/azure/active-directory/enterprise-users/groups-dynamic-membership)
- [Azure CLI AD Commands](https://learn.microsoft.com/en-us/cli/azure/ad)
- [Entra ID User and Group Management](https://learn.microsoft.com/en-us/azure/active-directory/fundamentals/active-directory-manage-groups)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive user and group management capabilities with straightforward commands for creating, updating, and organizing identities. The CLI is ideal for bulk operations and automation of identity lifecycle management.

---

## Estimated Duration
- **Deployment**: 5-10 minutes
- **Operations Phase**: 8+ hours (user management, group membership, access reviews)
- **Cleanup**: 5-10 minutes

---

## Notes
- Users are provisioned with temporary passwords that may require change at next sign-in
- Groups support nested membership (groups within groups) for organizational hierarchy
- Dynamic group membership rules can automatically add/remove users based on attributes
- User account enabled/disabled status controls sign-in capabilities
- All user and group operations are tenant-scoped
- Bulk operations should be used for large-scale user provisioning
- Group classification can enhance security and compliance policies
