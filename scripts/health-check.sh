#!/bin/bash
# Complete health check of Azure HayMaker infrastructure

echo "🏥 Azure HayMaker - Health Check"
echo "================================="
echo ""

RG="haymaker-dev-rg"
KV="haymaker-dev-yow3ex-kv"
SB="haymaker-dev-yow3ex-bus"
FA="haymaker-dev-yow3ex-func"

# Key Vault Health
echo "🔑 Key Vault: $KV"
KV_STATUS=$(az keyvault show --name $KV -g $RG --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NOT FOUND")
echo "  Status: $KV_STATUS"

if [ "$KV_STATUS" = "Succeeded" ]; then
  SECRET_COUNT=$(az keyvault secret list --vault-name $KV --query "length(@)" -o tsv 2>/dev/null || echo "0")
  echo "  Secrets: $SECRET_COUNT"
fi
echo ""

# Service Bus Health
echo "📨 Service Bus: $SB"
SB_STATUS=$(az servicebus namespace show --name $SB -g $RG --query "provisioningState" -o tsv 2>/dev/null || echo "NOT FOUND")
echo "  Status: $SB_STATUS"

if [ "$SB_STATUS" = "Succeeded" ]; then
  TOPIC_COUNT=$(az servicebus topic list --namespace-name $SB -g $RG --query "length(@)" -o tsv 2>/dev/null || echo "0")
  echo "  Topics: $TOPIC_COUNT"
fi
echo ""

# Function App Health
echo "⚡ Function App: $FA"
FA_STATUS=$(az functionapp show --name $FA -g $RG --query "state" -o tsv 2>/dev/null || echo "NOT FOUND")
echo "  State: $FA_STATUS"

if [ "$FA_STATUS" = "Running" ]; then
  # Try to hit status endpoint
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://${FA}.azurewebsites.net/api/v1/status 2>/dev/null || echo "000")
  echo "  API Status: HTTP $HTTP_CODE"
  
  if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ HEALTHY"
  else
    echo "  ⚠️  API not responding (expected if VM migration pending)"
  fi
fi
echo ""

# Overall Health
echo "📊 Overall Health:"
if [ "$KV_STATUS" = "Succeeded" ] && [ "$SB_STATUS" = "Succeeded" ]; then
  echo "  ✅ Infrastructure: HEALTHY"
else
  echo "  ⚠️  Infrastructure: CHECK REQUIRED"
fi

echo ""
echo "Health check complete!"
