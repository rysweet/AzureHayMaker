# Security Guide: Knowledge Worker Framework

## Overview

The Knowledge Worker framework requires Microsoft 365 credentials to operate. This document provides security best practices for credential management, permission configuration, and production deployment.

## Credential Management

### Development Environment

For development and testing, environment variables are acceptable:

```bash
export KW_TENANT_ID="your-tenant-id"
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-client-secret"
```

**Security Considerations:**
- Use `.env` files (add to `.gitignore`)
- Set file permissions to `0600` (owner read/write only)
- Never commit credentials to source control
- Rotate secrets every 90 days

### Production Environment (REQUIRED)

**🔒 CRITICAL: Production deployments MUST use Azure Key Vault.**

Environment variables in production are a security anti-pattern. Use Azure Key Vault for:
- Secret storage with encryption at rest
- Access logging and auditing
- Automatic secret rotation
- RBAC for secret access

#### Implementation Pattern

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_credentials_from_keyvault(vault_url: str) -> dict:
    """Load M365 credentials from Azure Key Vault.

    Args:
        vault_url: Key Vault URL (e.g., https://myvault.vault.azure.net/)

    Returns:
        Dict with tenant_id, client_id, client_secret

    Example:
        >>> vault_url = "https://haymaker-prod.vault.azure.net/"
        >>> creds = get_credentials_from_keyvault(vault_url)
        >>> client = GraphServiceClient(
        ...     ClientSecretCredential(
        ...         creds["tenant_id"],
        ...         creds["client_id"],
        ...         creds["client_secret"]
        ...     )
        ... )
    """
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)

    return {
        "tenant_id": client.get_secret("kw-tenant-id").value,
        "client_id": client.get_secret("kw-app-id").value,
        "client_secret": client.get_secret("kw-client-secret").value,
    }
```

#### Setting Up Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name haymaker-kw-prod \
  --resource-group haymaker-rg \
  --location eastus

# Store secrets
az keyvault secret set \
  --vault-name haymaker-kw-prod \
  --name kw-tenant-id \
  --value "your-tenant-id"

az keyvault secret set \
  --vault-name haymaker-kw-prod \
  --name kw-app-id \
  --value "your-app-id"

az keyvault secret set \
  --vault-name haymaker-kw-prod \
  --name kw-client-secret \
  --value "your-client-secret"

# Grant access to your application
az keyvault set-policy \
  --name haymaker-kw-prod \
  --spn <your-app-id> \
  --secret-permissions get list
```

### Credential Rotation

Rotate service principal credentials every 90 days:

```bash
# Generate new client secret
az ad sp credential reset \
  --id <app-id> \
  --years 1

# Update Key Vault with new secret
az keyvault secret set \
  --vault-name haymaker-kw-prod \
  --name kw-client-secret \
  --value "<new-secret>"
```

## Microsoft Graph API Permissions

### Required Permissions

The Knowledge Worker framework requires these **Application permissions**:

| Permission | Scope | Purpose |
|------------|-------|---------|
| `User.ReadWrite.All` | Application | Create and manage Entra users |
| `Mail.Send` | Application | Send emails on behalf of users |
| `Calendars.ReadWrite` | Application | Create calendar events |

### Granting Permissions

```bash
APP_ID="your-app-id"
GRAPH_API="00000003-0000-0000-c000-000000000000"

# Add User.ReadWrite.All
az ad app permission add \
  --id $APP_ID \
  --api $GRAPH_API \
  --api-permissions 741f803b-c850-494e-b5df-cde7c675a1ca=Role

# Add Mail.Send
az ad app permission add \
  --id $APP_ID \
  --api $GRAPH_API \
  --api-permissions b633e1c5-b582-4048-a93e-9f11b44c7e96=Role

# Add Calendars.ReadWrite
az ad app permission add \
  --id $APP_ID \
  --api $GRAPH_API \
  --api-permissions ef54d2bf-783f-4e0f-bca1-3210c0444d99=Role

# Grant admin consent
az ad app permission admin-consent --id $APP_ID
```

### Principle of Least Privilege

- Use **Application permissions**, not Delegated
- Do NOT grant more permissions than listed above
- Regularly audit permission usage
- Remove unused permissions

## License Management

### E5 License Assignment

The framework automatically assigns Microsoft 365 E5 licenses to created users. This requires:

1. **Available E5 licenses** in the tenant
2. **License assignment permissions** (included in User.ReadWrite.All)

### License Cost Considerations

**⚠️ WARNING: E5 licenses have significant cost implications.**

- E5 license: ~$57 USD per user per month
- 50 workers = ~$2,850/month
- 300 workers = ~$17,100/month

**Recommendations:**
- Use test/dev tenants for non-production deployments
- Implement auto-cleanup for temporary deployments
- Set budget alerts in Azure Cost Management
- Consider E3 licenses for basic testing (requires code modification)

### License Availability Check

Before deploying, verify license availability:

```python
from msgraph import GraphServiceClient

async def check_license_availability(client: GraphServiceClient) -> dict:
    """Check available E5 licenses in tenant.

    Returns:
        Dict with total and available license counts
    """
    skus = await client.subscribed_skus.get()

    e5_sku_id = "06ebc4ee-1bb5-47dd-8120-11324bc54e06"

    for sku in skus.value:
        if str(sku.sku_id) == e5_sku_id:
            consumed = sku.consumed_units
            enabled = sku.prepaid_units.enabled
            available = enabled - consumed

            return {
                "total": enabled,
                "consumed": consumed,
                "available": available,
            }

    return {"total": 0, "consumed": 0, "available": 0}
```

## Network Security

### Transport Rules

The framework creates Exchange transport rules to **block all external email**:

```python
# Created automatically by orchestrator
TransportRuleManager.create_block_external_rule(
    group_id=security_group_id,
    tenant_domain=tenant_domain
)
```

This ensures Knowledge Workers can only communicate internally.

### Firewall Rules

For additional security:
- Restrict Graph API access to known IP ranges
- Use Azure Private Endpoints for Key Vault
- Enable Azure Defender for Key Vault

## Monitoring and Auditing

### Audit Logs

Monitor these events in Azure AD audit logs:
- User creation/deletion
- License assignment
- Application permission grants
- Secret access from Key Vault

### Alerts

Set up alerts for:
- Failed authentication attempts
- Unusual license assignment patterns
- Secret rotation failures
- Permission changes to the app registration

## Compliance Considerations

### Data Residency

- All M365 data is stored in tenant's home region
- Respect data residency requirements
- Document data flows for compliance

### GDPR/Privacy

- Knowledge Worker accounts are test accounts
- Document data retention policies
- Implement automated cleanup

## Security Checklist

### Development
- [ ] Credentials in `.env` file (not committed)
- [ ] File permissions set to `0600`
- [ ] Test tenant used (not production)
- [ ] Regular credential rotation scheduled

### Production
- [ ] **Azure Key Vault configured** (MANDATORY)
- [ ] Managed Identity enabled for app
- [ ] Application permissions granted (not Delegated)
- [ ] Admin consent provided
- [ ] Transport rules block external email
- [ ] Audit logging enabled
- [ ] Cost alerts configured
- [ ] Automated cleanup scheduled
- [ ] Security review completed

## Incident Response

### Compromised Credentials

If credentials are compromised:

1. **Immediately rotate** client secret:
   ```bash
   az ad sp credential reset --id <app-id>
   ```

2. **Revoke** all active tokens:
   ```bash
   az ad app credential delete --id <app-id> --key-id <key-id>
   ```

3. **Audit** recent activity in Azure AD logs

4. **Update** Key Vault secrets

5. **Restart** all applications using old credentials

### Excessive License Usage

If unexpected license consumption occurs:

1. **List all** Knowledge Worker users:
   ```bash
   az ad user list --filter "startswith(userPrincipalName,'kw-')"
   ```

2. **Clean up** orphaned resources:
   ```python
   cleanup_manager = KnowledgeWorkerCleanupManager(...)
   await cleanup_manager.cleanup_all_resources(run_id)
   ```

3. **Review** deployment logs for errors

## References

- [Azure Key Vault Best Practices](https://learn.microsoft.com/en-us/azure/key-vault/general/best-practices)
- [Microsoft Graph API Permissions](https://learn.microsoft.com/en-us/graph/permissions-reference)
- [Azure AD App Security](https://learn.microsoft.com/en-us/azure/active-directory/develop/security-best-practices)
- [Microsoft 365 Licensing](https://learn.microsoft.com/en-us/microsoft-365/enterprise/m365-license-overview)

## Support

For security concerns, contact the HayMaker security team or file an issue at:
https://github.com/rysweet/AzureHayMaker/issues
