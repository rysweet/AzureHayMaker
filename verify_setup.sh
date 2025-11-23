#!/bin/bash
# Verify Azure HayMaker Orchestrator Setup
# Run this to check everything is ready

echo "========================================"
echo "Azure HayMaker Setup Verification"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Repository
echo "1. Checking repository..."
if [ -f "src/orchestrator_server.py" ]; then
    echo -e "   ${GREEN}✓${NC} orchestrator_server.py found"
else
    echo -e "   ${RED}✗${NC} orchestrator_server.py NOT FOUND"
    echo "   Run: git checkout develop && git pull origin develop"
fi

if [ -f "src/Dockerfile.orchestrator" ]; then
    echo -e "   ${GREEN}✓${NC} Dockerfile.orchestrator found"
else
    echo -e "   ${RED}✗${NC} Dockerfile.orchestrator NOT FOUND"
fi

if [ -f "COMPLETE_HANDOFF_ISSUE.md" ]; then
    echo -e "   ${GREEN}✓${NC} COMPLETE_HANDOFF_ISSUE.md found"
else
    echo -e "   ${RED}✗${NC} COMPLETE_HANDOFF_ISSUE.md NOT FOUND"
fi

# Check 2: Orchestrator
echo ""
echo "2. Checking orchestrator deployment..."
RESPONSE=$(curl -s --max-time 5 https://haymaker-fastapi-app.azurewebsites.net/)
if echo "$RESPONSE" | grep -q "healthy"; then
    echo -e "   ${GREEN}✓${NC} Orchestrator responding: https://haymaker-fastapi-app.azurewebsites.net"
else
    echo -e "   ${RED}✗${NC} Orchestrator not responding"
    echo "   Response: $RESPONSE"
fi

# Check 3: Azure CLI
echo ""
echo "3. Checking Azure CLI..."
if command -v az &> /dev/null; then
    echo -e "   ${GREEN}✓${NC} Azure CLI installed"

    # Check subscription
    SUB=$(az account show --query id -o tsv 2>/dev/null)
    if [ "$SUB" == "c190c55a-9ab2-4b1e-92c4-cc8b1a032285" ]; then
        echo -e "   ${GREEN}✓${NC} Correct subscription selected"
    else
        echo -e "   ${YELLOW}!${NC} Wrong subscription. Run:"
        echo "   az account set --subscription c190c55a-9ab2-4b1e-92c4-cc8b1a032285"
    fi
else
    echo -e "   ${RED}✗${NC} Azure CLI not installed"
fi

# Check 4: Environment Variables
echo ""
echo "4. Checking App Service configuration..."
echo -e "   ${YELLOW}i${NC} Checking if ANTHROPIC_API_KEY is set..."

# Summary
echo ""
echo "========================================"
echo "NEXT STEPS:"
echo "========================================"
echo "1. If orchestrator responding: ✓ Ready to deploy agents"
echo "2. Set real Anthropic API key in App Service"
echo "3. Deploy agent: POST /api/execute"
echo "4. Monitor execution"
echo ""
echo "See QUICKSTART_FOR_COLLEAGUE.md for detailed steps."
echo "========================================"
