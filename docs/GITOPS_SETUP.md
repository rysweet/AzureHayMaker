# GitOps Setup Guide for Azure HayMaker

Step-by-step guide for setting up the complete GitOps deployment pipeline.

## Overview

This guide walks through the complete setup process for automated GitOps deployments, including:

- Azure AD app registration for OIDC
- Service principal creation
- GitHub repository configuration
- Environment setup
- First deployment

**Estimated Time**: 30-45 minutes

## Prerequisites

Before starting, ensure you have:

- Azure subscription with Owner or Contributor role
- GitHub repository with admin access
- Azure CLI installed (`az --version`)
- GitHub CLI installed (optional, `gh --version`)
- Anthropic API key

## Step-by-Step Setup

### Step 1: Azure Authentication Setup

Login to Azure and set your subscription:

```bash
# Login to Azure
az login

# List subscriptions
az account list --output table

# Set active subscription
az account set --subscription "<subscription-id>"

# Verify
az account show
```

Export variables for the rest of the setup:

```bash
# Set these variables
export SUBSCRIPTION_ID="<your-subscription-id>"
export TENANT_ID="<your-tenant-id>"
export GITHUB_ORG="<your-github-org>"
export GITHUB_REPO="<your-repo-name>"
export LOCATION="eastus"

# Verify
echo "Subscription: $SUBSCRIPTION_ID"
echo "Tenant: $TENANT_ID"
echo "GitHub: $GITHUB_ORG/$GITHUB_REPO"
echo "Location: $LOCATION"
```

### Step 2: Create Azure AD App for GitHub OIDC

Create an app registration that GitHub Actions will use to authenticate:

```bash
# Create app registration
APP_NAME="github-oidc-haymaker"
echo "Creating app registration: $APP_NAME"

APP_ID=$(az ad app create \
  --display-name "$APP_NAME" \
  --query appId \
  --output tsv)

echo "✓ App created with ID: $APP_ID"
echo "Save this as AZURE_CLIENT_ID: $APP_ID"

# Create service principal
echo "Creating service principal..."
az ad sp create --id $APP_ID

SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query id --output tsv)
echo "✓ Service principal created with Object ID: $SP_OBJECT_ID"

# Wait for propagation
echo "Waiting 10 seconds for propagation..."
sleep 10

# Assign Contributor role
echo "Assigning Contributor role..."
az role assignment create \
  --role Contributor \
  --assignee-object-id $SP_OBJECT_ID \
  --assignee-principal-type ServicePrincipal \
  --scope /subscriptions/$SUBSCRIPTION_ID

echo "✓ Contributor role assigned"
```

### Step 3: Configure Federated Identity Credentials

Setup federated identity for GitHub Actions:

```bash
# For develop branch (dev environment)
echo "Creating federated credential for develop branch..."
az ad app federated-credential create \
  --id $APP_ID \
  --parameters "{
    \"name\": \"github-dev\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$GITHUB_ORG/$GITHUB_REPO:ref:refs/heads/develop\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
echo "✓ Federated credential created for develop branch"

# For main branch (staging environment)
echo "Creating federated credential for main branch..."
az ad app federated-credential create \
  --id $APP_ID \
  --parameters "{
    \"name\": \"github-staging\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$GITHUB_ORG/$GITHUB_REPO:ref:refs/heads/main\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
echo "✓ Federated credential created for main branch"

# For production environment
echo "Creating federated credential for prod environment..."
az ad app federated-credential create \
  --id $APP_ID \
  --parameters "{
    \"name\": \"github-prod\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$GITHUB_ORG/$GITHUB_REPO:environment:prod\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
echo "✓ Federated credential created for prod environment"

# Verify
echo "Verifying federated credentials..."
az ad app federated-credential list --id $APP_ID --output table
```

### Step 4: Create Orchestrator Service Principal

Create a service principal for the HayMaker orchestrator:

```bash
# Create service principal
MAIN_SP_NAME="haymaker-orchestrator-sp"
echo "Creating orchestrator service principal: $MAIN_SP_NAME"

MAIN_SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "$MAIN_SP_NAME" \
  --role Contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID \
  --output json)

MAIN_SP_CLIENT_ID=$(echo $MAIN_SP_OUTPUT | jq -r '.appId')
MAIN_SP_CLIENT_SECRET=$(echo $MAIN_SP_OUTPUT | jq -r '.password')
MAIN_SP_TENANT_ID=$(echo $MAIN_SP_OUTPUT | jq -r '.tenant')

echo "✓ Service principal created"
echo ""
echo "Save these values securely:"
echo "  Main SP Client ID: $MAIN_SP_CLIENT_ID"
echo "  Main SP Client Secret: $MAIN_SP_CLIENT_SECRET"
echo ""
echo "⚠️  WARNING: This secret cannot be retrieved again!"
```

### Step 5: Configure GitHub Repository Secrets

Add secrets to your GitHub repository:

#### Using GitHub CLI (Recommended)

```bash
# Login to GitHub
gh auth login

# Set repository secrets
gh secret set AZURE_TENANT_ID --body "$TENANT_ID" --repo $GITHUB_ORG/$GITHUB_REPO
gh secret set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID" --repo $GITHUB_ORG/$GITHUB_REPO
gh secret set AZURE_CLIENT_ID --body "$APP_ID" --repo $GITHUB_ORG/$GITHUB_REPO
gh secret set MAIN_SP_CLIENT_SECRET --body "$MAIN_SP_CLIENT_SECRET" --repo $GITHUB_ORG/$GITHUB_REPO

echo "✓ GitHub secrets configured"

# Verify
gh secret list --repo $GITHUB_ORG/$GITHUB_REPO
```

#### Using GitHub Web UI

Alternatively, add secrets manually:

1. Go to: `https://github.com/$GITHUB_ORG/$GITHUB_REPO/settings/secrets/actions`
2. Click "New repository secret"
3. Add each secret:
   - **AZURE_TENANT_ID**: `$TENANT_ID`
   - **AZURE_SUBSCRIPTION_ID**: `$SUBSCRIPTION_ID`
   - **AZURE_CLIENT_ID**: `$APP_ID`
   - **MAIN_SP_CLIENT_SECRET**: `$MAIN_SP_CLIENT_SECRET`

### Step 6: Add Anthropic API Key

Add your Anthropic API key to GitHub secrets:

```bash
# Get API key from https://console.anthropic.com/
read -s -p "Enter Anthropic API key: " ANTHROPIC_API_KEY
echo ""

# Set in GitHub
gh secret set ANTHROPIC_API_KEY --body "$ANTHROPIC_API_KEY" --repo $GITHUB_ORG/$GITHUB_REPO

echo "✓ Anthropic API key configured"
```

### Step 7: Configure GitHub Environments

Create environments with protection rules:

#### Using GitHub CLI

```bash
# Create dev environment
gh api repos/$GITHUB_ORG/$GITHUB_REPO/environments/dev --method PUT

# Create staging environment
gh api repos/$GITHUB_ORG/$GITHUB_REPO/environments/staging --method PUT

# Create prod environment with protection
gh api repos/$GITHUB_ORG/$GITHUB_REPO/environments/prod --method PUT \
  --field wait_timer=300 \
  --field prevent_self_review=true

echo "✓ Environments created"
```

#### Using GitHub Web UI

1. Go to: `https://github.com/$GITHUB_ORG/$GITHUB_REPO/settings/environments`
2. Click "New environment"
3. Create three environments:
   - **dev**: No protection rules
   - **staging**: No protection rules
   - **prod**: Enable "Required reviewers", add reviewers

### Step 8: Verify Configuration

Run verification checks:

```bash
echo "========================================="
echo "Configuration Summary"
echo "========================================="
echo ""
echo "Azure Configuration:"
echo "  Tenant ID: $TENANT_ID"
echo "  Subscription ID: $SUBSCRIPTION_ID"
echo "  App ID (OIDC): $APP_ID"
echo "  Location: $LOCATION"
echo ""
echo "GitHub Configuration:"
echo "  Repository: $GITHUB_ORG/$GITHUB_REPO"
echo "  Secrets configured: $(gh secret list --repo $GITHUB_ORG/$GITHUB_REPO | wc -l)"
echo "  Environments: dev, staging, prod"
echo ""
echo "Verification Steps:"
echo "  1. Check federated credentials:"
az ad app federated-credential list --id $APP_ID --output table
echo ""
echo "  2. Check role assignments:"
az role assignment list --assignee $SP_OBJECT_ID --output table
echo ""
echo "  3. Check GitHub secrets:"
gh secret list --repo $GITHUB_ORG/$GITHUB_REPO
echo ""
echo "========================================="
```

### Step 9: Test Deployment

Test the setup with a dev deployment:

```bash
# Clone repository
git clone https://github.com/$GITHUB_ORG/$GITHUB_REPO.git
cd $GITHUB_REPO

# Create develop branch
git checkout -b develop
git push origin develop

# Monitor deployment
gh workflow list --repo $GITHUB_ORG/$GITHUB_REPO
gh run watch --repo $GITHUB_ORG/$GITHUB_REPO
```

### Step 10: Add Log Analytics Secret (Post-Deployment)

After the first deployment, get the Log Analytics workspace key:

```bash
# Wait for deployment to complete
echo "Waiting for deployment to complete..."
sleep 60

# Get workspace key
WORKSPACE_NAME="haymaker-dev-logs"
RG_NAME="haymaker-dev-rg"

WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group $RG_NAME \
  --workspace-name $WORKSPACE_NAME \
  --query primarySharedKey \
  --output tsv)

# Add to GitHub secrets
gh secret set LOG_ANALYTICS_WORKSPACE_KEY --body "$WORKSPACE_KEY" --repo $GITHUB_ORG/$GITHUB_REPO

echo "✓ Log Analytics workspace key configured"
```

## Verification Checklist

After completing all steps, verify:

- [ ] Azure AD app created with correct permissions
- [ ] Federated credentials configured for all branches
- [ ] Service principal created with Contributor role
- [ ] GitHub secrets configured (5 secrets)
- [ ] GitHub environments created (dev, staging, prod)
- [ ] GitHub Actions enabled
- [ ] First deployment to dev succeeded
- [ ] Function App accessible
- [ ] Key Vault contains secrets

## Troubleshooting Setup

### Issue: Federated Credential Creation Fails

```bash
# Check if app exists
az ad app show --id $APP_ID

# List existing credentials
az ad app federated-credential list --id $APP_ID

# Delete and recreate if needed
az ad app federated-credential delete --id $APP_ID --federated-credential-id <name>
```

### Issue: Role Assignment Fails

```bash
# Check if service principal exists
az ad sp show --id $APP_ID

# Verify you have permissions
az role assignment list --assignee $(az account show --query user.name -o tsv)

# Wait and retry (propagation delay)
sleep 30
az role assignment create --role Contributor --assignee-object-id $SP_OBJECT_ID --scope /subscriptions/$SUBSCRIPTION_ID
```

### Issue: GitHub Secrets Not Working

```bash
# Verify secrets exist
gh secret list --repo $GITHUB_ORG/$GITHUB_REPO

# Update secret
gh secret set AZURE_CLIENT_ID --body "$APP_ID" --repo $GITHUB_ORG/$GITHUB_REPO

# Check workflow runs
gh run list --repo $GITHUB_ORG/$GITHUB_REPO --limit 5
```

## Next Steps

After completing setup:

1. Review [Deployment Guide](./DEPLOYMENT.md) for ongoing deployments
2. Configure monitoring and alerts
3. Set up staging and production deployments
4. Configure branch protection rules
5. Add additional team members to environments

## Cleanup (For Testing)

To remove all created resources:

```bash
# Delete resource groups
az group delete --name haymaker-dev-rg --yes --no-wait
az group delete --name haymaker-staging-rg --yes --no-wait
az group delete --name haymaker-prod-rg --yes --no-wait

# Delete app registration
az ad app delete --id $APP_ID

# Delete service principal
az ad sp delete --id $MAIN_SP_CLIENT_ID

# Delete GitHub secrets
gh secret remove AZURE_TENANT_ID --repo $GITHUB_ORG/$GITHUB_REPO
gh secret remove AZURE_SUBSCRIPTION_ID --repo $GITHUB_ORG/$GITHUB_REPO
gh secret remove AZURE_CLIENT_ID --repo $GITHUB_ORG/$GITHUB_REPO
gh secret remove MAIN_SP_CLIENT_SECRET --repo $GITHUB_ORG/$GITHUB_REPO
gh secret remove ANTHROPIC_API_KEY --repo $GITHUB_ORG/$GITHUB_REPO
gh secret remove LOG_ANALYTICS_WORKSPACE_KEY --repo $GITHUB_ORG/$GITHUB_REPO
```

## Support

For issues during setup:

1. Check Azure Portal for resource creation
2. Review GitHub Actions logs for deployment issues
3. Verify all secrets are configured correctly
4. Check Azure AD propagation (can take up to 10 minutes)

## Security Best Practices

- Never commit secrets to git
- Rotate service principal secrets every 90 days
- Use separate service principals per environment
- Enable audit logging in Azure AD
- Review role assignments regularly
- Use GitHub environment protection rules for production
