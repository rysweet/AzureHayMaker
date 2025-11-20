#!/bin/bash
set -e

echo "=== Orchestrator Verification Script ==="
echo ""

# Configuration
SUBSCRIPTION_ID="c190c55a-9ab2-4b1e-92c4-cc8b1a032285"
RESOURCE_GROUP="haymaker-dev-rg"
CONTAINER_APP="orch-dev-yc4hkcb2vv"

# Set subscription
echo "Setting Azure subscription..."
az account set --subscription $SUBSCRIPTION_ID

echo ""
echo "=== Phase 1: Container Deployment Status ==="
echo ""

echo "1. Checking Container App revisions..."
az containerapp revision list \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query "[].{Name:name, Active:properties.active, Traffic:properties.trafficWeight, Health:properties.healthState, Created:properties.createdTime}" \
  --output table

echo ""
echo "2. Getting latest active revision..."
LATEST_REVISION=$(az containerapp revision list \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query "[?properties.active].name | [0]" \
  --output tsv)

echo "Latest revision: $LATEST_REVISION"

echo ""
echo "=== Phase 2: Container Running State ==="
echo ""

echo "3. Checking replica status..."
az containerapp replica list \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --revision $LATEST_REVISION \
  --query "[].{Name:name, Status:properties.runningState, Created:properties.createdTime}" \
  --output table

echo ""
echo "=== Phase 3: HTTP Endpoint ==="
echo ""

echo "4. Getting endpoint..."
ENDPOINT=$(az containerapp show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

echo "Endpoint: https://$ENDPOINT"

echo ""
echo "5. Testing endpoint connectivity..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$ENDPOINT/ 2>/dev/null || echo "000")
echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "000" ]; then
    echo "❌ Connection refused - container not responding"
else
    echo "✓ Endpoint responding (HTTP $HTTP_STATUS)"
fi

echo ""
echo "=== Phase 4: Function Discovery ==="
echo ""

echo "6. Checking logs for function discovery..."
az containerapp logs show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --revision $LATEST_REVISION \
  --tail 200 | grep -A 12 "Found the following functions:" || echo "❌ Function discovery not found in logs"

echo ""
echo "=== Phase 5: Resource Configuration ==="
echo ""

echo "7. Checking workload profile and resources..."
az containerapp show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query "{WorkloadProfile:properties.workloadProfileName, CPU:properties.template.containers[0].resources.cpu, Memory:properties.template.containers[0].resources.memory}" \
  --output table

echo ""
echo "=== Verification Summary ==="
echo ""
echo "Check the following success criteria:"
echo "  ✓ Replica status = 'Running' (not 'NotRunning')"
echo "  ✓ Endpoint responds (HTTP status != 000)"
echo "  ✓ Logs contain 'Found the following functions:'"
echo "  ✓ At least 10 functions listed"
echo "  ✓ No Python import errors"
echo "  ✓ Workload profile configured (E16 or 128GB)"
echo ""
echo "=== Script Complete ==="
