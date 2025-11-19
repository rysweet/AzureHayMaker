#!/bin/bash
# Estimate monthly costs for deployed resources

echo "💰 Azure HayMaker - Cost Estimation"
echo "===================================="
echo ""

RG="haymaker-dev-rg"

# Count resources
KV_COUNT=$(az keyvault list -g $RG --query "length(@)" -o tsv 2>/dev/null || echo "0")
SB_COUNT=$(az servicebus namespace list -g $RG --query "length(@)" -o tsv 2>/dev/null || echo "0")
FA_COUNT=$(az functionapp list -g $RG --query "length(@)" -o tsv 2>/dev/null || echo "0")
SA_COUNT=$(az storage account list -g $RG --query "length(@)" -o tsv 2>/dev/null || echo "0")

echo "Resource Counts:"
echo "  Key Vaults: $KV_COUNT"
echo "  Service Bus: $SB_COUNT"
echo "  Function Apps: $FA_COUNT"
echo "  Storage Accounts: $SA_COUNT"
echo ""

# Estimate costs (rough)
KV_COST=$(echo "$KV_COUNT * 0.03" | bc)
SB_COST=$(echo "$SB_COUNT * 10" | bc)
FA_COST=$(echo "$FA_COUNT * 73" | bc)
SA_COST=$(echo "$SA_COUNT * 20" | bc)
TOTAL=$(echo "$KV_COST + $SB_COST + $FA_COST + $SA_COST" | bc)

echo "Estimated Monthly Costs (USD):"
echo "  Key Vaults: \$$KV_COST (@ \$0.03/vault)"
echo "  Service Bus: \$$SB_COST (@ \$10/namespace)"
echo "  Function Apps: \$$FA_COST (@ \$73/app on S1)"
echo "  Storage Accounts: \$$SA_COST (@ \$20/account)"
echo "  ─────────────"
echo "  TOTAL: ~\$$TOTAL/month"
echo ""

echo "💡 Cleanup Recommendation:"
echo "  Keep: 1 of each resource type"
echo "  Delete: $(($KV_COUNT - 1)) Key Vaults, $(($SB_COUNT - 1)) Service Bus, $(($FA_COUNT - 1)) Function Apps"
echo "  Potential Savings: ~\$$(echo "$TOTAL - 103" | bc)/month"
echo ""
echo "  Run: ./scripts/cleanup-old-function-apps.sh to start"
