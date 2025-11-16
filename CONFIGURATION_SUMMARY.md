# Azure HayMaker Configuration Summary

**Created**: 2025-11-15
**Status**: ✅ Ready for deployment

## Service Principal Details

**Name**: AzureHayMaker-Main-20251115-125358
**Client ID**: e2c7f4c6-00d7-4f62-9bb1-84b877fb5d7e
**Tenant ID**: c7674d41-af6c-46f5-89a5-d41495d2151e
**Subscription**: DefenderATEVET12 (c190c55a-9ab2-4b1e-92c4-cc8b1a032285)

**Roles Assigned**:
- ✅ Contributor (subscription scope)
- ✅ User Access Administrator (subscription scope)

## Configuration Files

### Local Development (.env)
- **Location**: `/Users/ryan/src/AzureHayMaker/.env`
- **Permissions**: 600 (owner read/write only)
- **Status**: ✅ Created and gitignored
- **Contains**: All required configuration + secrets

### GitHub Secrets (for GitOps)
- **Status**: ✅ All secrets configured
- **Count**: 7 secrets set

**Secrets Configured**:
1. AZURE_TENANT_ID
2. AZURE_SUBSCRIPTION_ID
3. AZURE_CLIENT_ID
4. AZURE_CLIENT_SECRET
5. ANTHROPIC_API_KEY
6. AZURE_LOCATION (westus2)
7. SIMULATION_SIZE (small)

## Deployment Configuration

**Azure Region**: westus2
**Simulation Size**: small (5 concurrent scenarios)
**Environment**: Development

## Next Steps

### Test Local Development
```bash
# Load .env and test configuration
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✅ Config loaded:', os.getenv('AZURE_TENANT_ID')[:8])"
```

### Test GitOps Deployment
```bash
# Create develop branch and push to trigger dev deployment
git checkout -b develop
git push -u origin develop

# Monitor deployment
gh workflow view deploy-dev
```

### Manual Resource Creation (if needed)
If you want to test without GitOps first:
```bash
# Create resource group
az group create --name azure-haymaker-rg --location westus2

# Create Key Vault
az keyvault create \
  --name haymaker-kv-<unique> \
  --resource-group azure-haymaker-rg \
  --location westus2

# Store secrets
az keyvault secret set --vault-name haymaker-kv-<unique> \
  --name "azure-client-secret" \
  --value "<AZURE_CLIENT_SECRET_FROM_.ENV>"

az keyvault secret set --vault-name haymaker-kv-<unique> \
  --name "anthropic-api-key" \
  --value "<ANTHROPIC_API_KEY_FROM_.ENV>"
```

## Security Notes

- ✅ Service principal has minimal required permissions
- ✅ Secrets stored securely (Key Vault for prod, GitHub Secrets for CI/CD)
- ✅ .env file has restrictive permissions (600)
- ✅ .env is gitignored
- ⚠️ User Access Administrator is powerful - consider custom RBAC role for production

## Verification

Run these commands to verify setup:

```bash
# Verify Azure login
az account show

# Verify SP exists
az ad sp show --id e2c7f4c6-00d7-4f62-9bb1-84b877fb5d7e

# Verify roles
az role assignment list --assignee e2c7f4c6-00d7-4f62-9bb1-84b877fb5d7e --output table

# Verify GitHub Secrets
gh secret list

# Test .env loading
cat .env | grep -v "SECRET\|KEY" | head -10
```

## Support

- Deployment Guide: `docs/DEPLOYMENT.md`
- GitOps Setup: `docs/GITOPS_SETUP.md`
- Getting Started: `docs/GETTING_STARTED.md`
