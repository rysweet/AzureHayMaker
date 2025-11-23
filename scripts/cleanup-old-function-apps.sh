#!/bin/bash
# Clean up old Function Apps to save $437/month

set -e

echo "🧹 Cleaning up old Function Apps..."

# List all Function Apps except the latest one
OLD_APPS=$(az functionapp list --resource-group haymaker-dev-rg \
  --query "[?name!='haymaker-dev-yow3ex-func'].name" -o tsv)

if [ -z "$OLD_APPS" ]; then
  echo "No old Function Apps to clean up"
  exit 0
fi

echo "Found old Function Apps:"
echo "$OLD_APPS"

read -p "Delete these to save ~\$437/month? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "$OLD_APPS" | while read app; do
    echo "Deleting $app..."
    az functionapp delete --name "$app" --resource-group haymaker-dev-rg
  done
  echo "✅ Cleanup complete! Cost savings: ~\$437/month"
else
  echo "Cancelled"
fi
