# Cross-Tenant Deployment Setup Guide

## Overview

Enable Azure HayMaker to deploy scenarios from an orchestrator tenant (Tenant A) to a different target tenant (Tenant B).

**Use Case**: Run orchestrator in "infrastructure tenant", deploy resources to "customer tenant".

**Phase 1 MVP Scope**: Deploy one scenario to a single different Azure tenant using explicit cross-tenant credentials, with tenant-aware logging and storage partitioning.

## Prerequisites

### Orchestrator Tenant (Tenant A)

- Service principal with permissions:
  - Key Vault: Get/Set secrets
  - Storage: Read/Write access to Table Storage and Blob Storage
- Key Vault for storing secrets
- Storage account for execution tracking
- Azure HayMaker orchestrator deployed

### Target Tenant (Tenant B)

- Service principal with permissions:
  - **Application.ReadWrite.All** (create service principals in target tenant)
  - **Contributor** on target subscription (deploy Azure resources)
- Subscription for resource deployment
- Resource group for deployments (optional, can be auto-created)

## Configuration

### Environment Variables

Configure both orchestrator credentials (existing) and target tenant credentials (new):

```bash
# Orchestrator tenant credentials (existing - no changes)
export AZURE_TENANT_ID="<orchestrator-tenant-id>"
export AZURE_CLIENT_ID="<orchestrator-sp-client-id>"
export AZURE_CLIENT_SECRET="<orchestrator-sp-secret>"

# Target tenant credentials (NEW for cross-tenant)
export TARGET_TENANT_SP_CLIENT_ID="<target-tenant-sp-client-id>"
export TARGET_TENANT_SP_CLIENT_SECRET="<target-tenant-sp-secret>"

# Deployment target (existing - update to target tenant)
export TARGET_TENANT_ID="<target-tenant-id>"  # Must differ from AZURE_TENANT_ID
export AZURE_SUBSCRIPTION_ID="<target-subscription-id>"
```

### Alternative: Key Vault Storage

Store target tenant credentials in Key Vault instead of environment variables:

```bash
# Store target tenant SP credentials in Key Vault
az keyvault secret set \
  --vault-name <orchestrator-key-vault> \
  --name "target-tenant-<first-8-chars-of-tenant-id>-sp-secret" \
  --value "<target-tenant-sp-secret>"
```

Priority order: Environment variables → Key Vault

### Service Principal Creation

#### Orchestrator Tenant SP

Create with permissions for Key Vault and Storage (existing setup - no changes):

```bash
az ad sp create-for-rbac \
  --name "haymaker-orchestrator-sp" \
  --role "Contributor" \
  --scopes "/subscriptions/<orchestrator-subscription-id>"
```

Grant Key Vault and Storage permissions as per standard HayMaker setup.

#### Target Tenant SP

Create in target tenant with elevated permissions:

```bash
# Create SP in target tenant
az ad sp create-for-rbac \
  --name "haymaker-target-tenant-sp" \
  --role "Contributor" \
  --scopes "/subscriptions/<target-subscription-id>"

# Grant Application.ReadWrite.All permission (required for SP creation)
# This must be done via Azure Portal or Graph API:
# 1. Navigate to Azure AD → App registrations → haymaker-target-tenant-sp
# 2. API permissions → Add permission → Microsoft Graph → Application permissions
# 3. Select "Application.ReadWrite.All"
# 4. Grant admin consent
```

**Critical**: Target tenant SP needs **Application.ReadWrite.All** to create ephemeral service principals for scenarios.

## Verification

### Check Mode Detection

Verify cross-tenant mode is detected correctly:

```bash
# Check logs when orchestrator starts
# Should see: "Cross-tenant mode enabled: orchestrator=<tenant-a> -> target=<tenant-b>"

# Or check via API if available
curl http://localhost:8000/api/status
```

Expected response (cross-tenant mode):
```json
{
  "status": "healthy",
  "mode": "cross-tenant",
  "orchestrator_tenant": "tenant-a...",
  "target_tenant": "tenant-b..."
}
```

### Test Deployment

Deploy a single scenario to verify cross-tenant works:

```bash
# Trigger execution via API or Functions
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": ["compute-01-linux-vm-web-server"],
    "duration_hours": 1
  }'
```

### Verify Resource Creation

Check resources created in target tenant:

```bash
# List resources in target subscription
az resource list \
  --subscription $AZURE_SUBSCRIPTION_ID \
  --tag "AzureHayMaker-managed=true"
```

### Check Storage Partitioning

Verify execution data stored with tenant context:

```bash
# Check blob storage has tenant prefix
az storage blob list \
  --account-name $STORAGE_ACCOUNT_NAME \
  --container-name execution-reports \
  | grep "<target-tenant-id>"

# Query Table Storage for tenant-partitioned data
# (Requires Table Storage query tool or SDK)
```

## Execution

### Deploy Scenarios

Standard execution API works in cross-tenant mode:

```bash
# POST /api/execute
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": ["compute-01-linux-vm-web-server", "networking-01-vnet"],
    "duration_hours": 2
  }'
```

### Monitor Execution

```bash
# GET /api/executions/{execution_id}
curl http://localhost:8000/api/executions/<execution-id>
```

### Query Resources by Tenant

```bash
# GET /api/resources?tenant_id=<target-tenant-id>
curl "http://localhost:8000/api/resources?tenant_id=<target-tenant-id>&status=created"
```

## Storage Organization

Cross-tenant execution data is stored with tenant isolation:

### Blob Storage

Reports stored with tenant prefix:
- **Cross-tenant**: `{tenant_id}/{run_id}/report.json`
- **Single-tenant**: `{run_id}/report.json` (backward compatible)

### Table Storage

#### ExecutionTracker Table

- **PartitionKey**: `execution_id` (unchanged for performance)
- **TenantId** field: Added for filtering
- Query: Can filter executions by `tenant_id`

#### ResourceInventory Table

- **PartitionKey**: `tenant_id` (changed from shared "resources")
- Each tenant gets own partition for isolation
- Query: Must provide `tenant_id` parameter

## Troubleshooting

### "Cross-tenant mode detected but credentials missing"

**Cause**: `TARGET_TENANT_SP_CLIENT_ID` or `TARGET_TENANT_SP_CLIENT_SECRET` not set

**Fix**: Set environment variables or store in Key Vault:
```bash
export TARGET_TENANT_SP_CLIENT_ID="<client-id>"
export TARGET_TENANT_SP_CLIENT_SECRET="<secret>"
```

### SP Creation Fails with "Insufficient Privileges"

**Cause**: Target tenant SP lacks `Application.ReadWrite.All` permission

**Fix**: Grant API permission via Azure Portal:
1. Azure AD → App registrations → [Target Tenant SP]
2. API permissions → Add permission → Microsoft Graph
3. Application permissions → Application.ReadWrite.All
4. Grant admin consent

### Container Deployment Fails with Auth Error

**Cause**: Azure CLI not authenticated to target tenant

**Fix**: Deployment automatically handles authentication. Check logs for:
- `"Deploying container to target tenant"`
- `"mode": "cross-tenant"`

If still failing, verify target tenant SP has Contributor role on subscription.

### Resources API Returns Empty Results

**Cause**: Missing `tenant_id` query parameter

**Fix**: Provide tenant_id in query:
```bash
curl "http://localhost:8000/api/resources?tenant_id=<target-tenant-id>"
```

### Logs Don't Show Cross-Tenant Context

**Cause**: Configuration may not be loaded properly

**Fix**: Check logs at orchestration start for:
- `"Starting orchestration"` with tenant context
- `"Cross-tenant deployment: orchestrator tenant ... -> target tenant ..."`

## Backward Compatibility

Single-tenant mode continues to work with no changes required:

### What Stays the Same

- Don't set `TARGET_TENANT_SP_*` environment variables
- Set `TARGET_TENANT_ID` same as `AZURE_TENANT_ID` (or omit)
- All existing deployments work unchanged
- Storage paths remain `{run_id}/report.json` (no tenant prefix)

### Configuration for Single-Tenant

```bash
# Orchestrator credentials (same as before)
export AZURE_TENANT_ID="<tenant-id>"
export AZURE_CLIENT_ID="<sp-client-id>"
export AZURE_CLIENT_SECRET="<sp-secret>"

# Target is same as orchestrator (backward compatible)
export TARGET_TENANT_ID="<tenant-id>"  # Same as AZURE_TENANT_ID
export AZURE_SUBSCRIPTION_ID="<subscription-id>"

# No TARGET_TENANT_SP_* variables needed
```

System automatically detects single-tenant mode and uses orchestrator credentials.

## Security Considerations

### Credential Management

- Store `TARGET_TENANT_SP_CLIENT_SECRET` in Key Vault when possible
- Rotate secrets regularly (30-day default expiration)
- Use different SPs for orchestrator and target tenants

### Permissions

- Target tenant SP should have **minimum required permissions**:
  - Application.ReadWrite.All (for SP creation only)
  - Contributor on specific resource groups (not subscription-wide if possible)
- Ephemeral scenario SPs automatically expire after 30 days

### Isolation

- Storage partitioned by tenant_id prevents cross-tenant data leaks
- Each tenant's resources stored in separate Table Storage partitions
- Blob paths prefixed with tenant_id

## Limitations (Phase 1 MVP)

### What's Supported

- ✅ Single target tenant per execution
- ✅ Explicit credential configuration via environment variables
- ✅ Tenant-isolated storage and tracking
- ✅ Full backward compatibility with single-tenant mode

### What's NOT Supported (Deferred to Future Phases)

- ❌ Multiple target tenants in one execution (fan-out)
- ❌ CLI commands for tenant management
- ❌ Automatic tenant discovery
- ❌ Meta-orchestrator (orchestrator of orchestrators)
- ❌ Dynamic tenant selection at runtime

## Next Steps

### After Successful Setup

1. **Test with single scenario**: Verify end-to-end cross-tenant flow
2. **Monitor logs**: Ensure tenant context appears in all phases
3. **Validate cleanup**: Verify resources cleaned up in target tenant
4. **Check storage**: Confirm tenant-prefixed blobs and partitioned tables

### Common Workflows

#### Deploying to Multiple Customer Tenants

For Phase 1, deploy separately to each tenant:

```bash
# Deploy to Customer A (set credentials and run)
export TARGET_TENANT_ID="customer-a-tenant-id"
export TARGET_TENANT_SP_CLIENT_ID="customer-a-sp-id"
export TARGET_TENANT_SP_CLIENT_SECRET="customer-a-sp-secret"
curl -X POST .../api/execute -d '{"scenarios": ["compute-01"], "duration_hours": 1}'

# Deploy to Customer B (update credentials and run)
export TARGET_TENANT_ID="customer-b-tenant-id"
export TARGET_TENANT_SP_CLIENT_ID="customer-b-sp-id"
export TARGET_TENANT_SP_CLIENT_SECRET="customer-b-sp-secret"
curl -X POST .../api/execute -d '{"scenarios": ["compute-01"], "duration_hours": 1}'
```

Future phases will support fan-out to multiple tenants in parallel.

## Support

For issues or questions:
- Check GitHub Issues for known problems
- Review logs with tenant context enabled
- Verify all environment variables set correctly

---

**Documentation Version**: Phase 1 MVP (Cross-Tenant Foundation)
**Last Updated**: 2024-01-15
