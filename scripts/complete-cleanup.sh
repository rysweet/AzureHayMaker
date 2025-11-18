#!/bin/bash
# Complete infrastructure cleanup - save $1,666/month!

set -e

RG="haymaker-dev-rg"
KEEP="yow3ex"  # Latest deployment to keep

echo "🧹 Azure HayMaker - Complete Infrastructure Cleanup"
echo "===================================================="
echo ""
echo "⚠️  This will delete ALL resources except those containing: $KEEP"
echo ""

# Show what will be deleted
echo "Resources to DELETE:"
echo "-------------------"

# Function Apps
OLD_FA=$(az functionapp list -g $RG --query "[?!contains(name, '$KEEP')].name" -o tsv 2>/dev/null)
FA_COUNT=$(echo "$OLD_FA" | wc -l)
echo "Function Apps: $FA_COUNT"

# Key Vaults  
OLD_KV=$(az keyvault list -g $RG --query "[?!contains(name, '$KEEP')].name" -o tsv 2>/dev/null)
KV_COUNT=$(echo "$OLD_KV" | wc -l)
echo "Key Vaults: $KV_COUNT"

# Service Bus
OLD_SB=$(az servicebus namespace list -g $RG --query "[?!contains(name, '$KEEP')].name" -o tsv 2>/dev/null)
SB_COUNT=$(echo "$OLD_SB" | wc -l)
echo "Service Bus: $SB_COUNT"

# Storage
OLD_ST=$(az storage account list -g $RG --query "[?!contains(name, '$KEEP')].name" -o tsv 2>/dev/null)
ST_COUNT=$(echo "$OLD_ST" | wc -l)
echo "Storage Accounts: $ST_COUNT"

echo ""
echo "💰 Estimated Monthly Savings: ~\$1,666"
echo ""

read -p "Proceed with deletion? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Cancelled"
  exit 0
fi

echo ""
echo "Starting cleanup..."

# Delete Function Apps
if [ -n "$OLD_FA" ]; then
  echo "Deleting Function Apps..."
  echo "$OLD_FA" | while read app; do
    echo "  - Deleting $app..."
    az functionapp delete --name "$app" -g $RG --yes 2>/dev/null || echo "    Failed (may be already deleted)"
  done
fi

# Delete Service Bus (after Function Apps)
if [ -n "$OLD_SB" ]; then
  echo "Deleting Service Bus namespaces..."
  echo "$OLD_SB" | while read sb; do
    echo "  - Deleting $sb..."
    az servicebus namespace delete --name "$sb" -g $RG --yes 2>/dev/null || echo "    Failed (may be already deleted)"
  done
fi

# Delete Storage Accounts
if [ -n "$OLD_ST" ]; then
  echo "Deleting Storage Accounts..."
  echo "$OLD_ST" | while read st; do
    echo "  - Deleting $st..."
    az storage account delete --name "$st" -g $RG --yes 2>/dev/null || echo "    Failed (may be already deleted)"
  done
fi

# Delete Key Vaults (last - they have soft delete)
if [ -n "$OLD_KV" ]; then
  echo "Deleting Key Vaults..."
  echo "$OLD_KV" | while read kv; do
    echo "  - Deleting $kv..."
    az keyvault delete --name "$kv" -g $RG 2>/dev/null || echo "    Failed (may be already deleted)"
  done
fi

echo ""
echo "✅ Cleanup complete!"
echo "💰 Monthly savings: ~\$1,666"
echo ""
echo "Remaining resources:"
./scripts/check-infrastructure.sh
