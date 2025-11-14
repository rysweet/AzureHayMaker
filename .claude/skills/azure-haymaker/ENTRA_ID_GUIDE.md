# EntraID (Azure AD) Administration Guide

Comprehensive guide for identity and access management in Azure.

## Core Concepts

### Identity Types
- **Users**: Human identities
- **Groups**: Collections of users
- **Service Principals**: Application identities
- **Managed Identities**: Azure resource identities (no credentials)

### Authentication vs Authorization
- **Authentication**: Who are you? (Entra ID)
- **Authorization**: What can you do? (Azure RBAC)

## Service Principals

### Creating Service Principals

```bash
# Method 1: Create with RBAC assignment
az ad sp create-for-rbac \
  --name "sp-myapp" \
  --role Contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{rg-name}

# Method 2: Create without role
az ad app create --display-name "myapp"
az ad sp create --id {app-id}

# Method 3: With certificate auth
az ad sp create-for-rbac \
  --name "sp-myapp" \
  --create-cert \
  --cert cert-name \
  --keyvault {keyvault-name}
```

### Managing SP Credentials

```bash
# Reset password
az ad sp credential reset --id {sp-object-id}

# Add new password
az ad sp credential reset --id {sp-object-id} --append

# List credentials
az ad sp credential list --id {sp-object-id}

# Delete credential
az ad sp credential delete --id {sp-object-id} --key-id {key-id}
```

### Best Practices
- Use managed identities instead of SPs when possible
- Rotate credentials regularly (90 days recommended)
- Use certificates over passwords
- Scope permissions to minimum required
- Monitor SP usage with sign-in logs

## Role-Based Access Control (RBAC)

### Built-in Roles (Common)
- **Owner**: Full access including RBAC
- **Contributor**: Full access except RBAC
- **Reader**: View only
- **User Access Administrator**: Manage RBAC only

### Role Assignment

```bash
# Assign at subscription level
az role assignment create \
  --assignee {object-id} \
  --role "Contributor" \
  --scope /subscriptions/{subscription-id}

# Assign at resource group level
az role assignment create \
  --assignee {object-id} \
  --role "Reader" \
  --scope /subscriptions/{subscription-id}/resourceGroups/{rg-name}

# Assign at resource level
az role assignment create \
  --assignee {object-id} \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage-name}
```

### Custom Roles

```bash
# Create custom role from JSON
az role definition create --role-definition @role.json

# Example role.json
{
  "Name": "Custom VM Operator",
  "Description": "Can start and stop VMs",
  "Actions": [
    "Microsoft.Compute/virtualMachines/start/action",
    "Microsoft.Compute/virtualMachines/powerOff/action",
    "Microsoft.Compute/virtualMachines/read"
  ],
  "NotActions": [],
  "AssignableScopes": [
    "/subscriptions/{subscription-id}"
  ]
}
```

### Listing Assignments

```bash
# List all assignments for a user/SP
az role assignment list --assignee {object-id}

# List assignments for a resource
az role assignment list --scope {resource-id}

# List with readable output
az role assignment list \
  --assignee {object-id} \
  --output table \
  --query "[].{Role:roleDefinitionName, Scope:scope}"
```

## Managed Identities

### System-Assigned Managed Identity

```bash
# Enable on VM
az vm identity assign --resource-group {rg} --name {vm-name}

# Enable on App Service
az webapp identity assign --resource-group {rg} --name {app-name}

# Enable on Function App
az functionapp identity assign --resource-group {rg} --name {function-name}

# Enable on Container App
az containerapp identity assign --resource-group {rg} --name {app-name}
```

### User-Assigned Managed Identity

```bash
# Create user-assigned identity
az identity create \
  --resource-group {rg} \
  --name {identity-name}

# Get identity details
IDENTITY_ID=$(az identity show \
  --resource-group {rg} \
  --name {identity-name} \
  --query id -o tsv)

PRINCIPAL_ID=$(az identity show \
  --resource-group {rg} \
  --name {identity-name} \
  --query principalId -o tsv)

# Assign to VM
az vm identity assign \
  --resource-group {rg} \
  --name {vm-name} \
  --identities $IDENTITY_ID

# Grant permissions to managed identity
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Storage Blob Data Reader" \
  --scope {storage-account-id}
```

### Using Managed Identities in Code

**Python Example:**
```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# Automatically uses managed identity when running in Azure
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(
    account_url="https://{storage-account}.blob.core.windows.net",
    credential=credential
)
```

## Groups

### Creating Groups

```bash
# Create security group
az ad group create \
  --display-name "Developers" \
  --mail-nickname "developers" \
  --description "Development team members"

# Create Microsoft 365 group
az ad group create \
  --display-name "Marketing" \
  --mail-nickname "marketing" \
  --mail-enabled true \
  --security-enabled false
```

### Managing Members

```bash
# Add member
az ad group member add \
  --group "Developers" \
  --member-id {user-object-id}

# Remove member
az ad group member remove \
  --group "Developers" \
  --member-id {user-object-id}

# List members
az ad group member list --group "Developers"

# Check membership
az ad group member check \
  --group "Developers" \
  --member-id {user-object-id}
```

### Group-Based RBAC

```bash
# Assign role to group
GROUP_ID=$(az ad group show --group "Developers" --query id -o tsv)

az role assignment create \
  --assignee $GROUP_ID \
  --role "Contributor" \
  --scope /subscriptions/{subscription-id}/resourceGroups/{rg-name}
```

## Users

### Creating Users

```bash
# Create user
az ad user create \
  --display-name "John Doe" \
  --user-principal-name john.doe@domain.com \
  --password {temp-password} \
  --force-change-password-next-sign-in true

# Create with additional details
az ad user create \
  --display-name "Jane Smith" \
  --user-principal-name jane.smith@domain.com \
  --password {temp-password} \
  --given-name "Jane" \
  --surname "Smith" \
  --department "Engineering"
```

### Managing Users

```bash
# Update user
az ad user update \
  --id {user-id} \
  --set department="Sales"

# Disable user
az ad user update \
  --id {user-id} \
  --account-enabled false

# Reset password
az ad user update \
  --id {user-id} \
  --password {new-password} \
  --force-change-password-next-sign-in true

# Delete user
az ad user delete --id {user-id}
```

## Application Registrations

### Creating App Registration

```bash
# Create app
az ad app create \
  --display-name "MyWebApp" \
  --sign-in-audience "AzureADMyOrg"

# Get app ID
APP_ID=$(az ad app list --display-name "MyWebApp" --query [0].appId -o tsv)

# Create service principal
az ad sp create --id $APP_ID
```

### Configure API Permissions

```bash
# Add Microsoft Graph permission (User.Read)
az ad app permission add \
  --id $APP_ID \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

# Grant admin consent
az ad app permission admin-consent --id $APP_ID
```

### Configure Redirect URIs

```bash
# Add web redirect URI
az ad app update \
  --id $APP_ID \
  --web-redirect-uris "https://myapp.com/callback"

# Add SPA redirect URI
az ad app update \
  --id $APP_ID \
  --public-client-redirect-uris "http://localhost:3000"
```

## Conditional Access

### Prerequisites
- Azure AD Premium P1 or P2 license
- Global Administrator or Security Administrator role

### Common Policies

**Policy 1: Require MFA for Administrators**
- Targets: Directory roles (Global Admin, Security Admin, etc.)
- Conditions: Any location
- Grant: Require MFA

**Policy 2: Block Legacy Authentication**
- Targets: All users
- Conditions: Legacy authentication clients
- Grant: Block access

**Policy 3: Require Compliant Devices**
- Targets: All users
- Conditions: Any location except trusted networks
- Grant: Require device to be marked as compliant

### Creating Conditional Access Policy (Portal Only)
Note: Conditional Access policies cannot be fully managed via Azure CLI.
Use Azure Portal → Azure AD → Security → Conditional Access

## Security Best Practices

### Identity Security
1. **Enable MFA** for all users
2. **Use managed identities** instead of service principals
3. **Implement least privilege** with RBAC
4. **Regular access reviews** (quarterly minimum)
5. **Monitor sign-in logs** for anomalies

### Service Principal Security
1. **Rotate credentials** every 90 days
2. **Use certificates** instead of secrets
3. **Scope permissions** to specific resources
4. **Store secrets in Key Vault**
5. **Audit SP usage** regularly

### RBAC Best Practices
1. **Assign roles to groups**, not individual users
2. **Use built-in roles** when possible
3. **Scope assignments** to lowest level needed
4. **Document custom roles** thoroughly
5. **Review assignments** quarterly

### Managed Identity Best Practices
1. **Use system-assigned** for single-resource scenarios
2. **Use user-assigned** for multi-resource scenarios
3. **Grant minimal permissions** required
4. **Document identity purpose** and permissions
5. **Monitor usage** with Azure Monitor

## Troubleshooting

### Common Issues

**"Insufficient privileges"**
- Check role assignments: `az role assignment list --assignee {id}`
- Verify scope of assignment
- May need Owner role to assign roles

**"Application with identifier not found"**
- App may not have service principal created
- Run: `az ad sp create --id {app-id}`

**"Managed identity not found"**
- Identity may not be enabled
- Check: `az vm/webapp identity show`
- Enable: `az vm/webapp identity assign`

**"The credentials in ServicePrincipalCredential are invalid"**
- Credentials expired or wrong
- Reset: `az ad sp credential reset --id {sp-id}`

## Useful Queries

```bash
# Find all Contributor assignments
az role assignment list \
  --role "Contributor" \
  --output table

# List all service principals you own
az ad sp list --show-mine

# Find users without MFA
az ad user list \
  --query "[?accountEnabled==\`true\` && !strongAuthenticationMethods].userPrincipalName"

# List all custom roles
az role definition list \
  --custom-role-only true \
  --output table
```

---

**Guide Version**: 1.0
**Last Updated**: 2024
**Azure CLI Version**: 2.50+
