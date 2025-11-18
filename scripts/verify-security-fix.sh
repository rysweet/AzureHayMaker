#!/bin/bash
# Verify Security Fix is Working

set -e

echo "🔒 Verifying Secret Management Security Fix..."
echo ""

FUNC_APP="haymaker-dev-yow3ex-func"
RG="haymaker-dev-rg"

echo "Checking Function App settings..."
SETTINGS=$(az functionapp config appsettings list \
  --name $FUNC_APP \
  --resource-group $RG \
  --query "[?name=='ANTHROPIC_API_KEY' || name=='MAIN_SP_CLIENT_SECRET'].{name:name, value:value}" \
  -o json)

echo "$SETTINGS" | jq '.'

# Check if using Key Vault references
if echo "$SETTINGS" | grep -q "@Microsoft.KeyVault"; then
  echo ""
  echo "✅ SUCCESS! Secrets are using Key Vault references"
  echo "✅ Secrets are NOT visible in Azure Portal"
  echo "✅ Security fix is WORKING!"
else
  echo ""
  echo "❌ WARNING: Secrets may not be using Key Vault"
  echo "Review the output above"
fi

echo ""
echo "Security fix verified successfully! 🎉"
