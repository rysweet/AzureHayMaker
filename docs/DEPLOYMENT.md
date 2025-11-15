# Azure HayMaker Deployment Guide

Complete guide for deploying Azure HayMaker infrastructure using GitOps and Azure Bicep.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Deployment Process](#deployment-process)
- [Environments](#environments)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

## Overview

Azure HayMaker uses a fully automated GitOps deployment pipeline with:

- **Infrastructure as Code**: All Azure resources defined in Bicep templates
- **GitHub Actions**: Automated CI/CD workflows for three environments
- **OIDC Authentication**: No long-lived credentials stored in GitHub
- **Secret Management**: GitHub Secrets injected into Azure Key Vault
- **Multi-Environment**: Separate deployments for dev, staging, and production

### Architecture

```
GitHub Repository
    ├── .github/workflows/
    │   ├── deploy-dev.yml      (Auto-deploy on push to develop)
    │   ├── deploy-staging.yml  (Auto-deploy on push to main)
    │   └── deploy-prod.yml     (Manual deploy on release)
    │
    └── infra/bicep/
        ├── main.bicep          (Root template)
        ├── modules/            (Reusable modules)
        └── parameters/         (Environment configs)
```

## Prerequisites

### Required Tools

1. **Azure CLI** (v2.50.0 or later)
   ```bash
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   az --version
   ```

2. **Azure Subscription** with:
   - Owner or Contributor role
   - Ability to create service principals
   - Sufficient quota for resources

3. **GitHub Repository** with:
   - Admin access
   - GitHub Actions enabled

### Required Secrets

The following secrets must be configured in your Azure subscription and GitHub repository:

| Secret Name | Description | Where to Get |
|-------------|-------------|--------------|
| AZURE_TENANT_ID | Azure AD tenant ID | Azure Portal → Azure AD → Properties |
| AZURE_SUBSCRIPTION_ID | Azure subscription ID | Azure Portal → Subscriptions |
| AZURE_CLIENT_ID | OIDC app registration client ID | Created in setup below |
| MAIN_SP_CLIENT_SECRET | Service principal secret for orchestrator | Created in setup below |
| ANTHROPIC_API_KEY | Anthropic API key for Claude | https://console.anthropic.com/ |
| LOG_ANALYTICS_WORKSPACE_KEY | Log Analytics shared key | Created during deployment |

## Initial Setup

### Step 1: Create Azure AD App Registration for OIDC

This enables GitHub Actions to authenticate with Azure without long-lived secrets.

```bash
# Login to Azure
az login

# Set variables
SUBSCRIPTION_ID="<your-subscription-id>"
APP_NAME="github-oidc-haymaker"
GITHUB_ORG="<your-github-org>"
GITHUB_REPO="<your-repo-name>"

# Create app registration
APP_ID=$(az ad app create \
  --display-name "$APP_NAME" \
  --query appId \
  --output tsv)

echo "App ID (AZURE_CLIENT_ID): $APP_ID"

# Create service principal
az ad sp create --id $APP_ID

# Get service principal object ID
SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query id --output tsv)

# Assign Contributor role to subscription
az role assignment create \
  --role Contributor \
  --assignee-object-id $SP_OBJECT_ID \
  --assignee-principal-type ServicePrincipal \
  --scope /subscriptions/$SUBSCRIPTION_ID

# Configure federated identity credential for GitHub Actions
# For main/staging environment
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-staging",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG"'/'"$GITHUB_REPO"':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# For develop/dev environment
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-dev",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG"'/'"$GITHUB_REPO"':ref:refs/heads/develop",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# For production releases
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-prod",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG"'/'"$GITHUB_REPO"':environment:prod",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### Step 2: Create Service Principal for Orchestrator

This service principal is used by the orchestrator to manage Azure resources.

```bash
# Create service principal
MAIN_SP_NAME="haymaker-orchestrator-sp"
MAIN_SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "$MAIN_SP_NAME" \
  --role Contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID \
  --output json)

MAIN_SP_CLIENT_ID=$(echo $MAIN_SP_OUTPUT | jq -r '.appId')
MAIN_SP_CLIENT_SECRET=$(echo $MAIN_SP_OUTPUT | jq -r '.password')

echo "Main SP Client ID: $MAIN_SP_CLIENT_ID"
echo "Main SP Client Secret: $MAIN_SP_CLIENT_SECRET"
echo ""
echo "IMPORTANT: Save the client secret securely - it cannot be retrieved later!"
```

### Step 3: Configure GitHub Secrets

Add the following secrets to your GitHub repository:

1. Go to: `https://github.com/<your-org>/<your-repo>/settings/secrets/actions`

2. Click "New repository secret" and add each:

   - **AZURE_TENANT_ID**: Your Azure AD tenant ID
   - **AZURE_SUBSCRIPTION_ID**: Your Azure subscription ID
   - **AZURE_CLIENT_ID**: App ID from Step 1 (`$APP_ID`)
   - **MAIN_SP_CLIENT_SECRET**: Client secret from Step 2
   - **ANTHROPIC_API_KEY**: Your Anthropic API key

### Step 4: Configure GitHub Environments

Create environments with protection rules:

1. **Development Environment**:
   - Go to: Settings → Environments → New environment
   - Name: `dev`
   - No protection rules needed (auto-deploy)

2. **Staging Environment**:
   - Name: `staging`
   - No protection rules needed (auto-deploy)

3. **Production Environment**:
   - Name: `prod`
   - Enable "Required reviewers" (recommended)
   - Add at least one reviewer
   - Enable "Wait timer" (optional, e.g., 5 minutes)

## Deployment Process

### Automatic Deployments

#### Development Environment

Automatically deploys on push to `develop` branch:

```bash
# Create and push to develop branch
git checkout -b develop
git push origin develop

# Push changes
git add .
git commit -m "Deploy to dev"
git push origin develop
```

Watch deployment: https://github.com/<your-org>/<your-repo>/actions

#### Staging Environment

Automatically deploys on push to `main` branch:

```bash
# Merge to main
git checkout main
git merge develop
git push origin main
```

#### Production Environment

Deploy via GitHub release:

```bash
# Create and push a tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Create release in GitHub UI
# Or use GitHub CLI:
gh release create v1.0.0 --title "v1.0.0" --notes "Production release"
```

### Manual Deployments

To manually trigger a deployment:

1. Go to: Actions → Deploy to [Environment]
2. Click "Run workflow"
3. Select branch (for prod, type confirmation phrase)
4. Click "Run workflow"

### Local Infrastructure Deployment

For testing Bicep templates locally:

```bash
# Login to Azure
az login

# Validate templates
az bicep build --file infra/bicep/main.bicep

# Validate deployment
az deployment sub validate \
  --location eastus \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/parameters/dev.bicepparam \
  --parameters adminObjectIds="['<your-object-id>']" \
  --parameters githubOidcClientId="<your-client-id>"

# What-if analysis (preview changes)
az deployment sub what-if \
  --location eastus \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/parameters/dev.bicepparam \
  --parameters adminObjectIds="['<your-object-id>']" \
  --parameters githubOidcClientId="<your-client-id>"

# Deploy
az deployment sub create \
  --location eastus \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/parameters/dev.bicepparam \
  --parameters adminObjectIds="['<your-object-id>']" \
  --parameters githubOidcClientId="<your-client-id>"
```

## Environments

### Development (dev)

- **Purpose**: Feature development and testing
- **Trigger**: Push to `develop` branch
- **Resources**: Minimal SKUs (Basic, Consumption)
- **Data Retention**: 7 days
- **Cost**: ~$50-100/month

### Staging (staging)

- **Purpose**: Pre-production testing
- **Trigger**: Push to `main` branch
- **Resources**: Standard SKUs
- **Data Retention**: 30 days
- **Cost**: ~$100-200/month

### Production (prod)

- **Purpose**: Live workloads
- **Trigger**: GitHub release or manual
- **Resources**: Premium SKUs with redundancy
- **Data Retention**: 90 days
- **Cost**: ~$300-500/month

## Troubleshooting

### Common Issues

#### 1. OIDC Authentication Failed

**Error**: `Login failed with Error: Unable to get OIDC token`

**Solution**:
```bash
# Verify federated credentials are configured
az ad app federated-credential list --id <app-id>

# Recreate if missing
az ad app federated-credential create \
  --id <app-id> \
  --parameters '{...}'
```

#### 2. Key Vault Access Denied

**Error**: `The user, group or application does not have secrets get permission`

**Solution**:
```bash
# Grant Key Vault Secrets User role to Function App
FUNCTION_APP_PRINCIPAL_ID=$(az functionapp show \
  --name <function-app-name> \
  --resource-group <rg-name> \
  --query identity.principalId \
  --output tsv)

az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $FUNCTION_APP_PRINCIPAL_ID \
  --scope /subscriptions/<subscription-id>/resourceGroups/<rg-name>/providers/Microsoft.KeyVault/vaults/<kv-name>
```

#### 3. Bicep Deployment Failed

**Error**: `Deployment validation failed`

**Solution**:
```bash
# Check Bicep version
az bicep version

# Upgrade if needed
az bicep upgrade

# Validate template
az bicep build --file infra/bicep/main.bicep

# Check for syntax errors in output
```

#### 4. Function App Not Starting

**Error**: Function app shows "Stopped" status

**Solution**:
```bash
# Check app settings
az functionapp config appsettings list \
  --name <function-app-name> \
  --resource-group <rg-name>

# Check logs
az functionapp log tail \
  --name <function-app-name> \
  --resource-group <rg-name>

# Restart function app
az functionapp restart \
  --name <function-app-name> \
  --resource-group <rg-name>
```

#### 5. Secrets Not Available

**Error**: Function app cannot read Key Vault secrets

**Solution**:
```bash
# Verify secrets exist in Key Vault
az keyvault secret list --vault-name <kv-name>

# Check Function App identity has access
az role assignment list \
  --assignee <function-app-principal-id> \
  --scope /subscriptions/<subscription-id>/resourceGroups/<rg-name>/providers/Microsoft.KeyVault/vaults/<kv-name>

# Manually inject secrets if needed
az keyvault secret set \
  --vault-name <kv-name> \
  --name main-sp-client-secret \
  --value "<secret-value>"
```

### Debug Mode

To enable detailed logging in GitHub Actions:

1. Go to: Settings → Secrets → Actions
2. Add secret: `ACTIONS_STEP_DEBUG` = `true`
3. Add secret: `ACTIONS_RUNNER_DEBUG` = `true`
4. Re-run workflow

### View Deployment Logs

```bash
# List recent deployments
az deployment sub list --query "[].{name:name, state:properties.provisioningState, timestamp:properties.timestamp}" --output table

# Show deployment details
az deployment sub show --name <deployment-name>

# View deployment operations
az deployment operation sub list --name <deployment-name>
```

## Rollback Procedures

### Quick Rollback

If deployment fails or causes issues:

#### Option 1: Redeploy Previous Release

```bash
# For production
git checkout <previous-tag>
gh release create <new-tag> --title "Rollback to <previous-tag>"
```

#### Option 2: Manual Rollback via Azure CLI

```bash
# Get previous deployment
PREVIOUS_DEPLOYMENT=$(az deployment sub list \
  --query "[?properties.provisioningState=='Succeeded'] | [1].name" \
  --output tsv)

# Redeploy previous deployment
az deployment sub create \
  --name "rollback-$(date +%s)" \
  --location eastus \
  --template-file infra/bicep/main.bicep \
  --parameters @infra/bicep/parameters/prod.bicepparam
```

#### Option 3: Point-in-Time Restore

For data recovery (Cosmos DB):

```bash
# List restore points
az cosmosdb show \
  --name <cosmos-account> \
  --resource-group <rg-name>

# Restore to previous point
az cosmosdb restore \
  --target-database-account-name <new-account-name> \
  --account-name <source-account-name> \
  --resource-group <rg-name> \
  --restore-timestamp "2025-11-15T10:00:00Z"
```

### Emergency Stop

To immediately stop all orchestrator operations:

```bash
# Stop Function App
az functionapp stop \
  --name <function-app-name> \
  --resource-group <rg-name>

# Disable all functions
az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group <rg-name> \
  --settings AzureWebJobsStorage=""
```

### Complete Infrastructure Teardown

To delete all resources (USE WITH CAUTION):

```bash
# Delete resource group (dev/staging only)
az group delete \
  --name haymaker-dev-rg \
  --yes \
  --no-wait

# For production, manual confirmation required
az group delete \
  --name haymaker-prod-rg \
  --yes
```

## Best Practices

### Pre-Deployment Checklist

- [ ] All tests passing in CI
- [ ] Code reviewed and approved
- [ ] Breaking changes documented
- [ ] Migration scripts prepared (if needed)
- [ ] Rollback plan documented
- [ ] Team notified of deployment window

### Post-Deployment Checklist

- [ ] Smoke tests passed
- [ ] Function App responding
- [ ] No errors in Application Insights
- [ ] Secrets accessible from Key Vault
- [ ] Monitoring dashboards updated
- [ ] Team notified of successful deployment

### Monitoring After Deployment

Monitor these metrics for 24 hours after production deployment:

1. **Function App Health**:
   - Response times
   - Error rates
   - Request counts

2. **Resource Usage**:
   - CPU utilization
   - Memory usage
   - Storage consumption

3. **Business Metrics**:
   - Scenario execution success rate
   - Agent deployment times
   - Cleanup completion rate

### Regular Maintenance

- **Weekly**: Review Application Insights for errors
- **Monthly**: Review costs and optimize resources
- **Quarterly**: Update dependencies and Azure CLI
- **Annually**: Rotate secrets and credentials

## Additional Resources

- [Azure Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [GitHub Actions OIDC with Azure](https://learn.microsoft.com/azure/developer/github/connect-from-azure)
- [Azure Functions Documentation](https://learn.microsoft.com/azure/azure-functions/)
- [Project Architecture](./ARCHITECTURE.md)

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review GitHub Actions logs
3. Check Azure Portal for resource status
4. Contact DevOps team
