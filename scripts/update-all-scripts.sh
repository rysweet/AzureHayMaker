#!/bin/bash
# Update all scripts to be executable

echo "🔧 Updating script permissions..."

find scripts -name "*.sh" -exec chmod +x {} \;
chmod +x deploy-vm-portal-guide.sh 2>/dev/null || true

echo "✅ All scripts are now executable"
echo ""
echo "Available scripts:"
find scripts -name "*.sh" -exec basename {} \; | sort
