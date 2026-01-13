# Verify Auto-Granted Microsoft Graph Permissions

How to verify that the PermissionGranter successfully auto-granted Mail.ReadWrite and other Microsoft Graph permissions during deployment.

## When to Use This Guide

After running `haymaker kw-setup` or deploying the Knowledge Worker framework, verify that admin consent was automatically granted for all required Microsoft Graph permissions.

## Quick Verification

Check permission status for the Knowledge Worker app:

```bash
# Get the app's service principal ID
az ad sp list --display-name "haymaker-knowledge-worker" \
  --query "[0].id" -o tsv

# Verify granted permissions (look for Mail.ReadWrite)
az ad sp show --id <SP_ID> \
  --query "appRoles[?value=='Mail.ReadWrite']" -o json
```

Expected output shows `Mail.ReadWrite` with granted status.

## Step-by-Step Verification

### 1. Check Auto-Grant Status in Setup Output

After running `haymaker kw-setup`, look for the PermissionGranter confirmation:

```bash
haymaker kw-setup --tenant-id <TENANT_ID>
```

Expected output includes:

```
✓ App registration created: haymaker-knowledge-worker
✓ Permissions requested: 7 permissions
✓ Service principal created
✓ Auto-granting admin consent...
✓ Mail.ReadWrite granted successfully
✓ All permissions granted: 7/7
✓ Setup complete!
```

### 2. Verify in Azure Portal

Navigate to Azure Portal and confirm permissions:

1. Open **Azure Active Directory** > **App registrations**
2. Search for `haymaker-knowledge-worker`
3. Click **API permissions**
4. Verify these permissions show green checkmarks:
   - Mail.ReadWrite (Application)
   - Mail.Send (Application)
   - User.ReadWrite.All (Application)
   - Calendars.ReadWrite (Application)
   - Files.ReadWrite.All (Application)
   - Team.Create (Application)
   - Directory.ReadWrite.All (Application)

**Status column must show**: "Granted for [Your Tenant]"

### 3. Verify with Azure CLI

List all granted permissions:

```bash
# Get app ID
APP_ID=$(az ad app list --display-name "haymaker-knowledge-worker" \
  --query "[0].appId" -o tsv)

# Get service principal
SP_ID=$(az ad sp show --id $APP_ID --query "id" -o tsv)

# List all OAuth2 permission grants (admin consent)
az rest --method GET \
  --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?\$filter=clientId eq '$SP_ID'"
```

Expected output shows `consentType: "AllPrincipals"` (admin consent granted).

### 4. Test Permission with API Call

Verify Mail.ReadWrite works by testing the Microsoft Graph API:

```bash
# Get access token
ACCESS_TOKEN=$(az account get-access-token \
  --resource https://graph.microsoft.com \
  --query accessToken -o tsv)

# Test Mail.ReadWrite permission
curl -X GET "https://graph.microsoft.com/v1.0/users" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

Expected output: JSON list of users (permission working).

### 5. Check Deployment Logs

If setup was part of automated deployment, check the logs:

```bash
# For container apps
az containerapp logs show \
  --name haymaker-knowledge-worker \
  --resource-group haymaker-dev-rg \
  --follow false \
  --tail 100 | grep "PermissionGranter"

# Expected log entries:
# PermissionGranter: Starting auto-grant for app <APP_ID>
# PermissionGranter: Granting Mail.ReadWrite (e2a3a72e-5f79-4c64-b1b1-878b674786c9)
# PermissionGranter: Successfully granted 7/7 permissions
```

## Troubleshooting

### Permission Not Granted

**Symptom**: Azure Portal shows "Not granted" for Mail.ReadWrite

**Solution**:

```bash
# Manually grant admin consent
az ad app permission admin-consent --id <APP_ID>

# Or use the admin consent URL
echo "https://login.microsoftonline.com/<TENANT_ID>/adminconsent?client_id=<APP_ID>"
# Open URL in browser as tenant administrator
```

### Insufficient Privileges Error

**Symptom**: Setup logs show "Insufficient privileges to grant consent"

**Cause**: The service principal running deployment lacks admin role.

**Solution**: Ensure deployment service principal has one of these roles:
- Global Administrator
- Privileged Role Administrator
- Cloud Application Administrator

Grant the role:

```bash
# Get deployment SP object ID
DEPLOY_SP_ID=<your-deployment-sp-id>

# Assign Cloud Application Administrator role
az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignments" \
  --headers "Content-Type=application/json" \
  --body "{
    \"principalId\": \"$DEPLOY_SP_ID\",
    \"roleDefinitionId\": \"158c047a-c907-4556-b7ef-446551a6b5f7\",
    \"directoryScopeId\": \"/\"
  }"
```

### Auto-Grant Skipped

**Symptom**: Setup completes but shows "Admin consent required (manual)"

**Cause**: PermissionGranter detected existing app with pending consent.

**Solution**: Either grant consent manually (see above) or delete and recreate:

```bash
# Delete existing app
az ad app delete --id <APP_ID>

# Run setup again
haymaker kw-setup --tenant-id <TENANT_ID>
```

## What PermissionGranter Does

The PermissionGranter component automatically grants admin consent during deployment by:

1. **Detecting deployment context**: Identifies if running with admin privileges
2. **Creating OAuth2 permission grant**: Uses Microsoft Graph API to create admin consent
3. **Granting per-permission**: Iterates through all 7 required Graph permissions
4. **Verifying success**: Confirms each permission granted before proceeding
5. **Logging audit trail**: Records all consent operations for compliance

## Why Auto-Grant is Needed

**Manual consent breaks automation**: Traditional Azure app setup requires a tenant administrator to manually click "Grant admin consent" in the portal. This blocks:
- Automated CI/CD pipelines
- Infrastructure-as-code deployments
- Self-service environment provisioning

**PermissionGranter solves this** by programmatically granting consent during setup when the deployment principal has appropriate admin roles.

## What Gets Granted

All Knowledge Worker scenarios require these Microsoft Graph application permissions:

| Permission              | Purpose                              | Auto-Granted |
| ----------------------- | ------------------------------------ | ------------ |
| Mail.ReadWrite          | Read and write mailbox data          | ✓            |
| Mail.Send               | Send email as any user               | ✓            |
| User.ReadWrite.All      | Manage user accounts                 | ✓            |
| Calendars.ReadWrite     | Manage calendar events               | ✓            |
| Files.ReadWrite.All     | Access OneDrive and SharePoint files | ✓            |
| Team.Create             | Create Microsoft Teams               | ✓            |
| Directory.ReadWrite.All | Manage directory objects             | ✓            |

All permissions granted as **Application permissions** (not delegated), allowing the app to operate without user interaction.

## When Permissions Are Granted

PermissionGranter runs automatically during:

1. **Initial setup**: `haymaker kw-setup` command
2. **CI/CD deployment**: GitHub Actions workflow step
3. **Infrastructure provisioning**: Terraform/Bicep apply phase
4. **Environment bootstrap**: First-time environment initialization

Permissions persist across deployments - auto-grant only runs if consent not already present.

## Security Considerations

**Principle of least privilege**: Only grant permissions required for planned Knowledge Worker scenarios. To customize:

```bash
# Setup with minimal permissions (Mail only)
haymaker kw-setup --permissions Mail.ReadWrite,Mail.Send

# Full permission set (default)
haymaker kw-setup --permissions all
```

**Audit trail**: All auto-grant operations logged to:
- Azure Active Directory audit logs
- Application Insights telemetry
- Deployment pipeline logs

Review logs periodically to verify no unauthorized consent grants.

## Related Documentation

- [Knowledge Worker Setup](../knowledge-worker-framework/ARCHITECTURE.md) - Complete framework setup
- [Deployment Setup Guide](../DEPLOYMENT_SETUP.md) - Full deployment instructions
- [Microsoft Graph Permissions Reference](https://learn.microsoft.com/en-us/graph/permissions-reference) - Official Microsoft documentation

---

**Last Updated**: 2025-12-11
**Feature Status**: ✓ Production Ready
**Verification Required**: After every deployment
