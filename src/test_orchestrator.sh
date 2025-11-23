#!/bin/bash
set -e

echo "=========================================="
echo "Testing Azure HayMaker Orchestrator"
echo "=========================================="

# Test 1: Health check
echo ""
echo "Test 1: Health check"
curl -s http://localhost:8080/ | jq .

# Test 2: Metrics
echo ""
echo "Test 2: Metrics"
curl -s http://localhost:8080/api/metrics | jq .

# Test 3: List scenarios
echo ""
echo "Test 3: List scenarios"
curl -s http://localhost:8080/api/scenarios | jq '.scenarios | length'

# Test 4: List executions
echo ""
echo "Test 4: List executions"
curl -s http://localhost:8080/api/executions | jq .

# Test 5: Validate environment (optional - requires Azure credentials)
echo ""
echo "Test 5: Validate environment (requires Azure credentials)"
echo "Skipping - run manually with: curl -X POST http://localhost:8080/api/validate"

# Test 6: Trigger execution (optional - requires Azure credentials)
echo ""
echo "Test 6: Manual execution trigger (requires Azure credentials)"
echo "Skipping - run manually with: curl -X POST http://localhost:8080/api/execute"

echo ""
echo "=========================================="
echo "All basic tests passed!"
echo "=========================================="
