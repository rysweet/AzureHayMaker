#!/bin/bash
set -e

echo "=========================================="
echo "Azure HayMaker Orchestrator"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found"
    echo "Please copy .env.orchestrator.example to .env and configure it"
    exit 1
fi

# Build the Docker image
echo ""
echo "Building Docker image..."
docker build -t azure-haymaker-orchestrator:latest -f Dockerfile.orchestrator .

# Stop any existing container
echo ""
echo "Stopping existing container (if any)..."
docker stop azure-haymaker-orchestrator 2>/dev/null || true
docker rm azure-haymaker-orchestrator 2>/dev/null || true

# Run the container
echo ""
echo "Starting orchestrator..."
docker run -d \
    --name azure-haymaker-orchestrator \
    -p 8080:80 \
    --env-file .env \
    azure-haymaker-orchestrator:latest

echo ""
echo "Waiting for orchestrator to start..."
sleep 5

# Check if it's running
if docker ps | grep -q azure-haymaker-orchestrator; then
    echo ""
    echo "=========================================="
    echo "Orchestrator started successfully!"
    echo "=========================================="
    echo ""
    echo "Health check:"
    curl -s http://localhost:8080/ | jq .
    echo ""
    echo ""
    echo "Available endpoints:"
    echo "  - Health:      http://localhost:8080/"
    echo "  - Metrics:     http://localhost:8080/api/metrics"
    echo "  - Executions:  http://localhost:8080/api/executions"
    echo "  - Scenarios:   http://localhost:8080/api/scenarios"
    echo ""
    echo "View logs:"
    echo "  docker logs -f azure-haymaker-orchestrator"
    echo ""
    echo "Stop orchestrator:"
    echo "  docker stop azure-haymaker-orchestrator"
    echo ""
else
    echo ""
    echo "ERROR: Orchestrator failed to start"
    echo "Check logs with: docker logs azure-haymaker-orchestrator"
    exit 1
fi
