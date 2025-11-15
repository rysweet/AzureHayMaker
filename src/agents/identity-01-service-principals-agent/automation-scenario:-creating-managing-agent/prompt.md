# Scenario: Creating and Managing Service Principals

## Technology Area
Identity

## Company Profile
- **Company Size**: Mid-size
- **Industry**: Financial Services
- **Use Case**: Automated application authentication for microservices and CI/CD pipelines requiring programmatic Azure access

## Scenario Description
Create and manage service principals for application authentication in Azure. This scenario covers service principal creation, credential management, role assignments, and operational tasks like credential rotation and audit logging. Service principals enable applications to authenticate to Azure services securely without human intervention.

## Azure Services Used
- Azure Entra ID (formerly Azure AD)
- Azure Role-Based Access Control (RBAC)
- Azure Service Principals
- Azure CLI
- Azure Key Vault (for credential storage reference)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed and configured
- Appropriate permissions to create service principals in Entra ID
- Existing resource group or permission to create one

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-identity-${UNIQUE_ID}-rg"
LOCATION="eastus"
SP_NAME="azurehaymaker-sp-${UNIQUE_ID}"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Tags
TAGS="AzureHayMaker-managed=true Scenario=identity-service-principals Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create first service principal
SP_01=$(az ad sp create-for-rbac \
  --name "${SP_NAME}-01" \
  --role Contributor \
  --scopes "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  --output json)

# Store the app ID and credentials
SP_01_APP_ID=$(echo $SP_01 | jq -r '.appId')
SP_01_TENANT=$(echo $SP_01 | jq -r '.tenant')

# Step 3: Create second service principal with no role initially
SP_02=$(az ad sp create-for-rbac \
  --name "${SP_NAME}-02" \
  --skip-assignment \
  --output json)

SP_02_APP_ID=$(echo $SP_02 | jq -r '.appId')

# Step 4: Get object ID of first service principal
SP_01_OBJECT_ID=$(az ad sp show --id "${SP_01_APP_ID}" --query id -o tsv)

# Step 5: Get object ID of second service principal
SP_02_OBJECT_ID=$(az ad sp show --id "${SP_02_APP_ID}" --query id -o tsv)

# Step 6: Create a service principal for resource read-only access
SP_03=$(az ad sp create-for-rbac \
  --name "${SP_NAME}-03" \
  --role Reader \
  --scopes "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  --output json)

SP_03_APP_ID=$(echo $SP_03 | jq -r '.appId')
SP_03_OBJECT_ID=$(az ad sp show --id "${SP_03_APP_ID}" --query id -o tsv)

# Step 7: Assign Reader role to second service principal
az role assignment create \
  --assignee "${SP_02_OBJECT_ID}" \
  --role "Reader" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

# Step 8: Create additional credential for first service principal
CRED=$(az ad sp credential reset \
  --id "${SP_01_APP_ID}" \
  --years 2 \
  --output json)

CRED_ID=$(echo $CRED | jq -r '.keyId')

echo "Service Principal 1 - App ID: ${SP_01_APP_ID}"
echo "Service Principal 2 - App ID: ${SP_02_APP_ID}"
echo "Service Principal 3 - App ID: ${SP_03_APP_ID}"
echo "Credential ID: ${CRED_ID}"
```

### Validation
```bash
# Verify resource group
az group show --name "${RESOURCE_GROUP}" --output table

# List service principals created
az ad sp list --filter "startswith(displayName, '${SP_NAME}')" --output table

# Check service principal 1 details
az ad sp show --id "${SP_01_APP_ID}" --output table

# Check service principal 2 details
az ad sp show --id "${SP_02_APP_ID}" --output table

# Check service principal 3 details
az ad sp show --id "${SP_03_APP_ID}" --output table

# List all role assignments for resource group
az role assignment list \
  --resource-group "${RESOURCE_GROUP}" \
  --output table

# Check credentials for first service principal
az ad sp credential list --id "${SP_01_APP_ID}" --output table

# Verify tag application
az resource list --resource-group "${RESOURCE_GROUP}" --query "[].tags" -o json
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Update service principal display name and description
az ad sp update \
  --id "${SP_01_APP_ID}" \
  --set displayName="azurehaymaker-sp-${UNIQUE_ID}-01-updated"

# Operation 2: List all owners of service principal
az ad sp owner list \
  --id "${SP_01_APP_ID}" \
  --output table

# Operation 3: Rotate credentials for service principal (create new password)
NEW_CRED=$(az ad sp credential reset \
  --id "${SP_02_APP_ID}" \
  --years 1 \
  --output json)

NEW_PASSWORD=$(echo $NEW_CRED | jq -r '.password')

# Operation 4: List all credentials (keys) for a service principal
az ad sp credential list \
  --id "${SP_01_APP_ID}" \
  --output table

# Operation 5: Add an Owner role assignment to service principal
CURRENT_USER_ID=$(az account show --query user.objectId -o tsv)
az role assignment create \
  --assignee-object-id "${SP_02_OBJECT_ID}" \
  --role "Owner" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}"

# Operation 6: Remove a role assignment
az role assignment delete \
  --assignee "${SP_02_OBJECT_ID}" \
  --role "Reader" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

# Operation 7: Audit service principal activity - Check when password last changed
az ad sp credential list --id "${SP_01_APP_ID}" --query "[].startDate" -o table

# Operation 8: Create a federated credential for OIDC auth (simulated)
# This demonstrates modern credential alternatives to passwords
az identity create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "azurehaymaker-mi-${UNIQUE_ID}"

# Operation 9: Assign service principal to custom role (if available)
az role assignment create \
  --assignee "${SP_03_APP_ID}" \
  --role "Contributor" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

# Operation 10: Generate audit log for service principal activity
az monitor activity-log list \
  --resource-group "${RESOURCE_GROUP}" \
  --caller "${SP_01_APP_ID}" \
  --max-events 10 \
  --output table

# Operation 11: Check principal type and app ownership
az ad sp show --id "${SP_01_APP_ID}" --query "[displayName, appDisplayName, appId]" -o table

# Operation 12: List all permissions granted to service principal
az role assignment list \
  --assignee "${SP_01_APP_ID}" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete service principals
az ad sp delete --id "${SP_01_APP_ID}"
az ad sp delete --id "${SP_02_APP_ID}"
az ad sp delete --id "${SP_03_APP_ID}"

# Step 2: Remove role assignments
az role assignment delete \
  --assignee "${SP_03_APP_ID}" \
  --role "Contributor" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
  2>/dev/null || true

# Step 3: Delete managed identity
az identity delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "azurehaymaker-mi-${UNIQUE_ID}"

# Step 4: Delete resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 5: Wait for deletion
echo "Waiting for cleanup to complete..."
sleep 60

# Step 6: Verify deletion
az group exists --name "${RESOURCE_GROUP}"

# Step 7: Confirm service principals are deleted
az ad sp list --filter "startswith(displayName, '${SP_NAME}')" --output table

echo "Service principals and resources successfully cleaned up"
```

---

## Resource Naming Convention
- Service Principal: `azurehaymaker-sp-${UNIQUE_ID}-[01-03]`
- Managed Identity: `azurehaymaker-mi-${UNIQUE_ID}`
- Resource Group: `azurehaymaker-identity-${UNIQUE_ID}-rg`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Azure Service Principals Overview](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
- [Create Service Principal with Azure CLI](https://learn.microsoft.com/en-us/cli/azure/ad/sp)
- [Azure RBAC Role Assignments](https://learn.microsoft.com/en-us/azure/role-based-access-control/role-assignments-cli)
- [Service Principal Credentials and Secrets](https://learn.microsoft.com/en-us/azure/active-directory/develop/active-directory-certificate-credentials)
- [Managed Identities for Azure Resources](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive service principal management capabilities with straightforward commands for creation, credential rotation, and RBAC assignment. The CLI is ideal for automation and scripting identity workflows.

---

## Estimated Duration
- **Deployment**: 5-10 minutes
- **Operations Phase**: 8+ hours (monitoring, audit logging, credential management)
- **Cleanup**: 3-5 minutes

---

## Notes
- Service principals are application objects used for programmatic authentication
- Multiple credentials can be managed for a single service principal for rotation
- Always store credentials securely (e.g., in Azure Key Vault)
- RBAC assignments control what resources the service principal can access
- Service principal deletion is immediate; dependent resources may need cleanup
- Activity logs track all operations performed by service principals
- Federated credentials offer modern alternatives to password-based authentication
