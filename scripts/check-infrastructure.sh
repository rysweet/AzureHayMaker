#!/bin/bash
# Check all deployed infrastructure

echo "🏗️ Checking Azure HayMaker Infrastructure..."
echo ""

RG="haymaker-dev-rg"

echo "Resource Group: $RG"
echo "================================"

# Key Vault
echo "📦 Key Vault:"
az keyvault list --resource-group $RG --query "[].{name:name, location:location}" -o table 2>/dev/null || echo "  None found"
echo ""

# Service Bus
echo "📨 Service Bus:"
az servicebus namespace list --resource-group $RG --query "[].{name:name, sku:sku.name}" -o table 2>/dev/null || echo "  None found"
echo ""

# Storage
echo "💾 Storage Accounts:"
az storage account list --resource-group $RG --query "[].{name:name, sku:sku.name}" -o table 2>/dev/null || echo "  None found"
echo ""

# Function Apps
echo "⚡ Function Apps:"
az functionapp list --resource-group $RG --query "[].{name:name, state:state, plan:appServicePlanId}" -o table 2>/dev/null || echo "  None found"
echo ""

# VMs
echo "🖥️ Virtual Machines:"
az vm list --resource-group $RG --query "[].{name:name, size:hardwareProfile.vmSize, state:provisioningState}" -o table 2>/dev/null || echo "  None found"
echo ""

echo "✅ Infrastructure check complete!"
