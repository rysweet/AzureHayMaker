#!/bin/bash
# Knowledge Worker App Registration Setup Script
#
# This script creates and configures the Azure Entra app registration
# required for Knowledge Worker operations (M365 email, Teams, etc.)
#
# Prerequisites:
# - Azure CLI logged in with tenant admin privileges
# - Permissions: Application Administrator or Global Administrator role
#
# Usage:
#   ./setup_kw_app.sh [--tenant-id TENANT_ID]

set -e

# Configuration
KW_APP_NAME="haymaker-knowledge-worker"
GRAPH_API_ID="00000003-0000-0000-c000-000000000000"

# Parse arguments
TENANT_ID=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --tenant-id)
            TENANT_ID="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get tenant ID if not provided
if [ -z "$TENANT_ID" ]; then
    TENANT_ID=$(az account show --query tenantId -o tsv)
fi

echo "================================================"
echo "Knowledge Worker App Registration Setup"
echo "================================================"
echo "Tenant ID: $TENANT_ID"
echo ""

# Step 1: Check if app already exists
echo "Checking for existing app registration..."
EXISTING_APP=$(az ad app list --filter "displayName eq '$KW_APP_NAME'" --query "[0].appId" -o tsv 2>/dev/null || echo "")

if [ -n "$EXISTING_APP" ]; then
    echo "App already exists: $EXISTING_APP"
    KW_APP_ID=$EXISTING_APP
else
    # Create app registration
    echo "Creating app registration: $KW_APP_NAME..."
    KW_APP_ID=$(az ad app create \
        --display-name "$KW_APP_NAME" \
        --sign-in-audience "AzureADMyOrg" \
        --query appId -o tsv)
    echo "Created app: $KW_APP_ID"
fi

# Step 2: Add required Microsoft Graph permissions
echo ""
echo "Adding Microsoft Graph API permissions..."

# Permission IDs (Application type)
declare -A PERMISSIONS=(
    ["User.ReadWrite.All"]="741f803b-c850-494e-b5df-cde7c675a1ca"
    ["Mail.ReadWrite"]="e2a3a72e-5f79-4c64-b1b1-878b674786c9"
    ["Mail.Send"]="b633e1c5-b582-4048-a93e-9f11b44c7e96"
    ["Team.Create"]="23fc2474-f741-46ce-8465-674744c5c361"
    ["Calendars.ReadWrite"]="ef54d2bf-783f-4e0f-bca1-3210c0444d99"
    ["Files.ReadWrite.All"]="75359482-378d-4052-8f01-80520e7db3cd"
    ["Directory.ReadWrite.All"]="19dbc75e-c2e2-444c-a770-ec69d8559fc7"
)

for PERM_NAME in "${!PERMISSIONS[@]}"; do
    PERM_ID="${PERMISSIONS[$PERM_NAME]}"
    echo "  Adding $PERM_NAME..."
    az ad app permission add \
        --id "$KW_APP_ID" \
        --api "$GRAPH_API_ID" \
        --api-permissions "$PERM_ID=Role" 2>/dev/null || true
done

# Step 3: Create service principal
echo ""
echo "Creating service principal..."
SP_ID=$(az ad sp show --id "$KW_APP_ID" --query id -o tsv 2>/dev/null || echo "")
if [ -z "$SP_ID" ]; then
    SP_ID=$(az ad sp create --id "$KW_APP_ID" --query id -o tsv)
    echo "Created service principal: $SP_ID"
else
    echo "Service principal already exists: $SP_ID"
fi

# Step 4: Create client secret
echo ""
echo "Creating client secret..."
SECRET_RESULT=$(az ad app credential reset \
    --id "$KW_APP_ID" \
    --display-name "kw-secret-$(date +%Y%m%d)" \
    --years 1 \
    --query "{appId:appId, password:password, tenant:tenant}" -o json)

CLIENT_SECRET=$(echo "$SECRET_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

# Step 5: Output configuration
echo ""
echo "================================================"
echo "App Registration Complete!"
echo "================================================"
echo ""
echo "Add these to your .env file:"
echo ""
echo "KW_APP_ID=$KW_APP_ID"
echo "KW_CLIENT_SECRET=$CLIENT_SECRET"
echo "KW_TENANT_ID=$TENANT_ID"
echo ""

# Step 6: Generate admin consent URL
CONSENT_URL="https://login.microsoftonline.com/$TENANT_ID/adminconsent?client_id=$KW_APP_ID"
echo "================================================"
echo "IMPORTANT: Admin Consent Required"
echo "================================================"
echo ""
echo "The permissions require admin consent."
echo "Open this URL in a browser and sign in as a tenant admin:"
echo ""
echo "$CONSENT_URL"
echo ""
echo "Or use Azure Portal:"
echo "1. Go to Azure Portal > Entra ID > App registrations"
echo "2. Find '$KW_APP_NAME'"
echo "3. Go to 'API permissions'"
echo "4. Click 'Grant admin consent for $TENANT_ID'"
echo ""

# Save config to file
CONFIG_FILE="kw_app_config.env"
cat > "$CONFIG_FILE" << EOF
# Knowledge Worker App Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

KW_APP_ID=$KW_APP_ID
KW_CLIENT_SECRET=$CLIENT_SECRET
KW_TENANT_ID=$TENANT_ID
KW_SP_ID=$SP_ID

# Admin consent URL (open in browser as tenant admin)
# $CONSENT_URL
EOF

echo "Configuration saved to: $CONFIG_FILE"
echo ""
echo "Next steps:"
echo "1. Grant admin consent using the URL above"
echo "2. Add the config values to your .env file"
echo "3. Test with: haymaker kw test --tenant-domain YOUR_DOMAIN.onmicrosoft.com"
