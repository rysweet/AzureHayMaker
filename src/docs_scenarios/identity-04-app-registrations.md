# Scenario: Application Registrations and Permissions

## Technology Area
Identity

## Company Profile
- **Company Size**: Mid-size
- **Industry**: SaaS Platform
- **Use Case**: Register cloud applications with Entra ID and manage API permissions for multi-tenant scenarios

## Scenario Description
Register applications with Entra ID to enable secure authentication and authorization. This scenario covers creating app registrations, managing client secrets, configuring API permissions, and setting up application roles for delegated and application-based access patterns.

## Azure Services Used
- Azure Entra ID (formerly Azure AD)
- Application Registrations
- API Permissions
- Client Secrets
- Azure AD Graph API
- Microsoft Graph API

## Prerequisites
- Azure subscription with Application Administrator role
- Azure CLI installed and configured
- Appropriate permissions to register applications in Entra ID
- Understanding of OAuth 2.0 and API permission scopes

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-apps-${UNIQUE_ID}-rg"
LOCATION="eastus"
TENANT_ID=$(az account show --query tenantId -o tsv)
APP_PREFIX="azurehaymaker-app-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=identity-app-registrations Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create first application registration (Web app)
APP_01=$(az ad app create \
  --display-name "${APP_PREFIX}-webapp-01" \
  --sign-in-audience AzureADMyOrg \
  --web-redirect-uris "https://localhost:3000/auth/callback" "https://localhost:8080/callback" \
  --output json)

APP_01_ID=$(echo $APP_01 | jq -r '.id')
APP_01_APPID=$(echo $APP_01 | jq -r '.appId')

# Step 3: Create second application registration (API)
APP_02=$(az ad app create \
  --display-name "${APP_PREFIX}-api-02" \
  --sign-in-audience AzureADMultipleOrgs \
  --output json)

APP_02_ID=$(echo $APP_02 | jq -r '.id')
APP_02_APPID=$(echo $APP_02 | jq -r '.appId')

# Step 4: Create third application registration (Mobile app)
APP_03=$(az ad app create \
  --display-name "${APP_PREFIX}-mobile-03" \
  --public-client-redirect-uris "msal${APP_PREFIX}://auth" \
  --sign-in-audience AzureADMyOrg \
  --output json)

APP_03_ID=$(echo $APP_03 | jq -r '.id')
APP_03_APPID=$(echo $APP_03 | jq -r '.appId')

# Step 5: Add client secret to first application
SECRET_01=$(az ad app credential reset \
  --id "${APP_01_ID}" \
  --years 1 \
  --output json)

SECRET_01_VALUE=$(echo $SECRET_01 | jq -r '.password')

# Step 6: Add client secret to second application
SECRET_02=$(az ad app credential reset \
  --id "${APP_02_ID}" \
  --years 2 \
  --output json)

SECRET_02_ID=$(echo $SECRET_02 | jq -r '.keyId')

# Step 7: Create service principal for first app
SP_01=$(az ad sp create \
  --id "${APP_01_APPID}" \
  --output json)

SP_01_OBJECT_ID=$(echo $SP_01 | jq -r '.id')

# Step 8: Create service principal for second app
SP_02=$(az ad sp create \
  --id "${APP_02_APPID}" \
  --output json)

SP_02_OBJECT_ID=$(echo $SP_02 | jq -r '.id')

# Step 9: Create service principal for third app
SP_03=$(az ad sp create \
  --id "${APP_03_APPID}" \
  --output json)

SP_03_OBJECT_ID=$(echo $SP_03 | jq -r '.id')

echo "App 1 ID: ${APP_01_APPID}"
echo "App 2 ID: ${APP_02_APPID}"
echo "App 3 ID: ${APP_03_APPID}"
echo "Secret stored securely (use Key Vault in production)"
```

### Validation
```bash
# Verify resource group
az group show --name "${RESOURCE_GROUP}" --output table

# List all created app registrations
az ad app list --filter "startswith(displayName, '${APP_PREFIX}')" --output table

# Get details of first app
az ad app show --id "${APP_01_APPID}" --output table

# Get details of second app
az ad app show --id "${APP_02_APPID}" --output table

# Get details of third app
az ad app show --id "${APP_03_APPID}" --output table

# List service principals
az ad sp list --filter "startswith(displayName, '${APP_PREFIX}')" --output table

# Check client secrets for app 1
az ad app credential list --id "${APP_01_ID}" --output table

# Check credentials for app 2
az ad app credential list --id "${APP_02_ID}" --output table

# Verify redirect URIs
az ad app show --id "${APP_01_APPID}" --query "web.redirectUris" --output json
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Add additional redirect URI to application
az ad app update \
  --id "${APP_01_ID}" \
  --web-redirect-uris "https://localhost:3000/auth/callback" "https://localhost:8080/callback" "https://prod.example.com/callback"

# Operation 2: Update application display name
az ad app update \
  --id "${APP_01_ID}" \
  --display-name "${APP_PREFIX}-webapp-01-updated"

# Operation 3: List all credentials for an application
az ad app credential list \
  --id "${APP_01_ID}" \
  --output table

# Operation 4: Create additional client secret
NEW_SECRET=$(az ad app credential reset \
  --id "${APP_02_ID}" \
  --years 1 \
  --output json)

NEW_SECRET_ID=$(echo $NEW_SECRET | jq -r '.keyId')

# Operation 5: Delete specific credential by ID
# Note: Use with caution - this will revoke access for clients using this credential
# az ad app credential delete --id "${APP_01_ID}" --key-id <key-id>

# Operation 6: Add API permissions to application (Microsoft Graph API)
az ad app permission add \
  --id "${APP_01_APPID}" \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

# Operation 7: List existing API permissions
az ad app permission list \
  --id "${APP_01_APPID}" \
  --output table

# Operation 8: Grant admin consent for API permissions (simulated)
# In production, use: az ad app permission admin-consent --id <app-id>
az ad app permission list --id "${APP_01_APPID}" --query "[].{resourceAppId:resourceAppId, id:id}" --output table

# Operation 9: Update application properties
az ad app update \
  --id "${APP_02_ID}" \
  --set "description=API application for data processing"

# Operation 10: Assign role to service principal
az role assignment create \
  --assignee-object-id "${SP_01_OBJECT_ID}" \
  --role "Reader" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}"

# Operation 11: Check service principal properties
az ad sp show \
  --id "${SP_01_OBJECT_ID}" \
  --query "[displayName, appId, accountEnabled]" \
  --output table

# Operation 12: Generate JWT token (simulated - for testing client credentials flow)
# In production: az account get-access-token --resource-id <app-id>
az ad app show \
  --id "${APP_02_APPID}" \
  --query "[appId, id, displayName]" \
  --output table
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Remove role assignments from service principals
az role assignment delete \
  --assignee-object-id "${SP_01_OBJECT_ID}" \
  --role "Reader" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}" \
  2>/dev/null || true

# Step 2: Delete service principals
az ad sp delete --id "${SP_01_OBJECT_ID}" 2>/dev/null || true
az ad sp delete --id "${SP_02_OBJECT_ID}" 2>/dev/null || true
az ad sp delete --id "${SP_03_OBJECT_ID}" 2>/dev/null || true

# Step 3: Delete application registrations
az ad app delete --id "${APP_01_ID}" 2>/dev/null || true
az ad app delete --id "${APP_02_ID}" 2>/dev/null || true
az ad app delete --id "${APP_03_ID}" 2>/dev/null || true

# Step 4: Delete resource group
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 5: Wait for deletion
echo "Waiting for cleanup to complete..."
sleep 60

# Step 6: Verify applications are deleted
az ad app list --filter "startswith(displayName, '${APP_PREFIX}')" --output table

# Step 7: Verify service principals are deleted
az ad sp list --filter "startswith(displayName, '${APP_PREFIX}')" --output table

# Step 8: Verify resource group deletion
az group exists --name "${RESOURCE_GROUP}"

echo "Applications, service principals, and resources successfully cleaned up"
```

---

## Resource Naming Convention
- Web App: `${APP_PREFIX}-webapp-01`
- API App: `${APP_PREFIX}-api-02`
- Mobile App: `${APP_PREFIX}-mobile-03`
- Resource Group: `azurehaymaker-apps-${UNIQUE_ID}-rg`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Application Registration in Entra ID](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
- [Register an Application](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [Client Credentials Grant Flow](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-client-creds-grant-flow)
- [API Permissions and Consent](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent)
- [Azure CLI AD App Commands](https://learn.microsoft.com/en-us/cli/azure/ad/app)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides comprehensive application registration management with commands for creating apps, managing secrets, and configuring permissions. The CLI is ideal for automating application lifecycle and authentication workflows.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8+ hours (credential rotation, permission management, testing)
- **Cleanup**: 5-10 minutes

---

## Notes
- Application registrations represent your application in Entra ID
- Service principals are the runtime instance of the app registration
- Client secrets should be stored securely in Azure Key Vault
- API permissions define what resources the app can access
- Redirect URIs are validated during OAuth 2.0 flows
- Multi-tenant apps can be used across multiple Entra ID tenants
- Admin consent is required for certain sensitive permissions
- Credential rotation should be performed regularly for security
