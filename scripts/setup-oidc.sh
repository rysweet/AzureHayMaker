#!/bin/bash
# Azure HayMaker OIDC Setup Script
# This script automates the creation of service principal with federated identity credentials
# for GitHub Actions OIDC authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
GITHUB_ORG="${GITHUB_ORG:-rysweet}"
GITHUB_REPO="${GITHUB_REPO:-AzureHayMaker}"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"

# Validate prerequisites
echo -e "${YELLOW}Validating prerequisites...${NC}"

if ! command -v az &> /dev/null; then
    echo -e "${RED}ERROR: Azure CLI not found. Please install: https://aka.ms/InstallAzureCLI${NC}"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo -e "${RED}ERROR: GitHub CLI not found. Please install: https://cli.github.com${NC}"
    exit 1
fi

# Check Azure login
if ! az account show &> /dev/null; then
    echo -e "${RED}ERROR: Not logged in to Azure. Run: az login${NC}"
    exit 1
fi

# Get subscription ID if not set
if [ -z "$SUBSCRIPTION_ID" ]; then
    SUBSCRIPTION_ID=$(az account show --query id --output tsv)
    echo -e "${GREEN}Using subscription: $SUBSCRIPTION_ID${NC}"
fi

TENANT_ID=$(az account show --query tenantId --output tsv)

# Step 1: Create Service Principal
echo -e "\n${YELLOW}Step 1: Creating Service Principal...${NC}"
SP_NAME="AzureHayMaker-Main-$(date +%Y%m%d-%H%M%S)"

SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "$SP_NAME" \
  --role Contributor \
  --scopes "/subscriptions/$SUBSCRIPTION_ID" \
  --query "{appId: appId, password: password}" \
  -o json)

CLIENT_ID=$(echo "$SP_OUTPUT" | jq -r '.appId')
CLIENT_SECRET=$(echo "$SP_OUTPUT" | jq -r '.password')

echo -e "${GREEN}✓ Service Principal created: $SP_NAME${NC}"
echo -e "  Client ID: $CLIENT_ID"

# Wait for propagation
echo -e "${YELLOW}Waiting 30 seconds for Azure AD propagation...${NC}"
sleep 30

# Step 2: Assign User Access Administrator role
echo -e "\n${YELLOW}Step 2: Assigning User Access Administrator role...${NC}"
az role assignment create \
  --assignee "$CLIENT_ID" \
  --role "User Access Administrator" \
  --scope "/subscriptions/$SUBSCRIPTION_ID" \
  --output none

echo -e "${GREEN}✓ User Access Administrator role assigned${NC}"

# Step 3: Get App Object ID for federated credentials
echo -e "\n${YELLOW}Step 3: Configuring OIDC federated credentials...${NC}"
APP_OBJECT_ID=$(az ad app show --id "$CLIENT_ID" --query id --output tsv)

# Step 4: Create federated credentials for branches
echo -e "${YELLOW}Creating federated credential for main branch...${NC}"
az ad app federated-credential create \
  --id "$APP_OBJECT_ID" \
  --parameters "{
    \"name\": \"github-actions-main-branch\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$GITHUB_ORG/$GITHUB_REPO:ref:refs/heads/main\",
    \"audiences\": [\"api://AzureADTokenExchange\"],
    \"description\": \"GitHub Actions for main branch\"
  }" \
  --output none

echo -e "${GREEN}✓ Main branch OIDC configured${NC}"

echo -e "${YELLOW}Creating federated credential for develop branch...${NC}"
az ad app federated-credential create \
  --id "$APP_OBJECT_ID" \
  --parameters "{
    \"name\": \"github-actions-develop-branch\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$GITHUB_ORG/$GITHUB_REPO:ref:refs/heads/develop\",
    \"audiences\": [\"api://AzureADTokenExchange\"],
    \"description\": \"GitHub Actions for develop branch\"
  }" \
  --output none

echo -e "${GREEN}✓ Develop branch OIDC configured${NC}"

# Step 5: Create federated credentials for environments
for ENV in dev staging prod; do
    echo -e "${YELLOW}Creating federated credential for $ENV environment...${NC}"
    az ad app federated-credential create \
      --id "$APP_OBJECT_ID" \
      --parameters "{
        \"name\": \"github-actions-env-$ENV\",
        \"issuer\": \"https://token.actions.githubusercontent.com\",
        \"subject\": \"repo:$GITHUB_ORG/$GITHUB_REPO:environment:$ENV\",
        \"audiences\": [\"api://AzureADTokenExchange\"],
        \"description\": \"GitHub Actions for $ENV environment\"
      }" \
      --output none
    echo -e "${GREEN}✓ $ENV environment OIDC configured${NC}"
done

# Step 6: Set GitHub Secrets
echo -e "\n${YELLOW}Step 6: Setting GitHub Secrets...${NC}"

gh secret set AZURE_TENANT_ID --body "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID"
gh secret set AZURE_CLIENT_ID --body "$CLIENT_ID"
gh secret set MAIN_SP_CLIENT_SECRET --body "$CLIENT_SECRET"

echo -e "${GREEN}✓ GitHub Secrets configured${NC}"

# Step 7: Display summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}OIDC Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nService Principal Details:"
echo -e "  Name: $SP_NAME"
echo -e "  Client ID: $CLIENT_ID"
echo -e "  Tenant ID: $TENANT_ID"
echo -e "  Subscription: $SUBSCRIPTION_ID"
echo -e "\nRoles Assigned:"
echo -e "  ✓ Contributor"
echo -e "  ✓ User Access Administrator"
echo -e "\nFederated Credentials Configured:"
echo -e "  ✓ main branch"
echo -e "  ✓ develop branch"
echo -e "  ✓ dev environment"
echo -e "  ✓ staging environment"
echo -e "  ✓ prod environment"
echo -e "\nGitHub Secrets Set:"
echo -e "  ✓ AZURE_TENANT_ID"
echo -e "  ✓ AZURE_SUBSCRIPTION_ID"
echo -e "  ✓ AZURE_CLIENT_ID"
echo -e "  ✓ MAIN_SP_CLIENT_SECRET"
echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "1. Set remaining GitHub Secrets:"
echo -e "   - ANTHROPIC_API_KEY"
echo -e "   - AZURE_LOCATION (e.g., westus2)"
echo -e "   - SIMULATION_SIZE (small/medium/large)"
echo -e "   - LOG_ANALYTICS_WORKSPACE_KEY"
echo -e "2. Trigger deployment:"
echo -e "   gh workflow run 'Deploy to Development'"
echo -e "3. Monitor deployment:"
echo -e "   gh run list --workflow='Deploy to Development' --limit 1"
echo -e "\n${GREEN}Configuration saved to: .env${NC}"
echo -e "${YELLOW}Remember: Keep .env secure and never commit to git!${NC}"

# Save configuration to .env
cat > .env <<ENVEOF
# Azure HayMaker Configuration
# Created: $(date)

AZURE_TENANT_ID=$TENANT_ID
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
AZURE_CLIENT_ID=$CLIENT_ID
AZURE_CLIENT_SECRET=$CLIENT_SECRET
AZURE_LOCATION=westus2
SIMULATION_SIZE=small
ENVEOF

chmod 600 .env
echo -e "\n${GREEN}✓ Configuration saved to .env (permissions: 600)${NC}"
