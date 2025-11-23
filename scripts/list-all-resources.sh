#!/bin/bash
# List ALL resources in haymaker-dev-rg

echo "📋 All Resources in haymaker-dev-rg"
echo "===================================="
echo ""

az resource list --resource-group haymaker-dev-rg \
  --query "sort_by([].{Name:name, Type:type, Location:location}, &Type)" \
  --output table

echo ""
echo "💰 Cost estimate: Run 'az consumption usage list' for details"
