# Azure HayMaker FastAPI Orchestrator

**A SIMPLE orchestrator that WORKS.**

No Azure Functions. No Durable Functions. Just a FastAPI server that runs anywhere.

## Quick Start

### 1. Local Testing (Docker)

```bash
# Build the image
docker build -t azure-haymaker-orchestrator -f Dockerfile.orchestrator .

# Run the container
docker run -p 8080:80 \
  -e AZURE_TENANT_ID=$AZURE_TENANT_ID \
  -e AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
  -e AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
  # ... other env vars ...
  azure-haymaker-orchestrator

# Test it works
curl http://localhost:8080/
```

### 2. Docker Compose (Recommended for local dev)

```bash
# Create .env file with all required environment variables
cp .env.example .env
# Edit .env with your values

# Start the orchestrator
docker-compose -f docker-compose.orchestrator.yml up -d

# View logs
docker-compose -f docker-compose.orchestrator.yml logs -f

# Test endpoints
./test_orchestrator.sh
```

### 3. Direct Python (Development)

```bash
# Install dependencies
pip install -r requirements-orchestrator.txt

# Set environment variables
export AZURE_TENANT_ID=...
export AZURE_SUBSCRIPTION_ID=...
# ... other env vars ...

# Run the server
python orchestrator_server.py

# In another terminal, test it
curl http://localhost:80/
```

## API Endpoints

### Health & Status

- **GET /** - Health check
  ```bash
  curl http://localhost:8080/
  ```

- **GET /api/metrics** - Execution metrics
  ```bash
  curl http://localhost:8080/api/metrics
  ```

### Executions

- **GET /api/executions** - List all executions
  ```bash
  curl http://localhost:8080/api/executions
  ```

- **GET /api/executions/{id}** - Get execution details
  ```bash
  curl http://localhost:8080/api/executions/abc-123
  ```

- **POST /api/execute** - Manually trigger execution
  ```bash
  curl -X POST http://localhost:8080/api/execute
  ```

### Configuration

- **POST /api/validate** - Validate environment
  ```bash
  curl -X POST http://localhost:8080/api/validate
  ```

- **GET /api/scenarios** - List available scenarios
  ```bash
  curl http://localhost:8080/api/scenarios
  ```

## Scheduled Execution

The orchestrator automatically runs 4x daily:
- 00:00 UTC (midnight)
- 06:00 UTC (6am)
- 12:00 UTC (noon)
- 18:00 UTC (6pm)

Uses APScheduler for reliable cron scheduling.

## Orchestration Workflow

Each execution follows these phases:

1. **Validation** - Verify Azure credentials and environment
2. **Selection** - Select random scenarios based on simulation size
3. **Provisioning** - Create service principals and deploy containers
4. **Monitoring** - Monitor agent execution for 8 hours
5. **Cleanup** - Verify and force cleanup of resources
6. **Reporting** - Generate and store execution report

## Environment Variables

### Required

```bash
AZURE_TENANT_ID=...              # Azure tenant ID
AZURE_SUBSCRIPTION_ID=...         # Target subscription ID
AZURE_CLIENT_ID=...               # Main SP client ID
KEY_VAULT_URL=...                 # Key Vault URL for secrets
SERVICE_BUS_NAMESPACE=...         # Service Bus namespace
CONTAINER_REGISTRY=...            # Container registry URL
CONTAINER_IMAGE=...               # Agent container image
SIMULATION_SIZE=small             # small/medium/large
STORAGE_ACCOUNT_NAME=...          # Blob storage account
TABLE_STORAGE_ACCOUNT_NAME=...    # Table storage account
LOG_ANALYTICS_WORKSPACE_ID=...    # Log Analytics workspace ID
```

### Optional

```bash
RESOURCE_GROUP_NAME=azure-haymaker-rg  # Resource group name
SERVICE_BUS_TOPIC=agent-logs           # Service Bus topic
COSMOSDB_ENDPOINT=...                  # Cosmos DB endpoint (optional)
COSMOSDB_DATABASE=haymaker             # Cosmos DB database name
VNET_INTEGRATION_ENABLED=false         # Enable VNet integration
```

### Secrets (from Key Vault)

These are automatically retrieved from Key Vault:
- `main-sp-client-secret` - Main service principal secret
- `anthropic-api-key` - Anthropic API key
- `log-analytics-workspace-key` - Log Analytics workspace key

## Deployment to Azure Container Apps

```bash
# Build and push image
az acr build \
  --registry $CONTAINER_REGISTRY \
  --image azure-haymaker-orchestrator:latest \
  --file Dockerfile.orchestrator \
  .

# Create Container App
az containerapp create \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP_NAME \
  --environment $CONTAINER_ENV_NAME \
  --image $CONTAINER_REGISTRY/azure-haymaker-orchestrator:latest \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 2 \
  --memory 4Gi \
  --registry-server $CONTAINER_REGISTRY \
  --env-vars \
    AZURE_TENANT_ID=$AZURE_TENANT_ID \
    AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
    AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
    KEY_VAULT_URL=$KEY_VAULT_URL \
    SERVICE_BUS_NAMESPACE=$SERVICE_BUS_NAMESPACE \
    CONTAINER_REGISTRY=$CONTAINER_REGISTRY \
    CONTAINER_IMAGE=$CONTAINER_IMAGE \
    SIMULATION_SIZE=small \
    STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT_NAME \
    TABLE_STORAGE_ACCOUNT_NAME=$TABLE_STORAGE_ACCOUNT_NAME \
    LOG_ANALYTICS_WORKSPACE_ID=$LOG_ANALYTICS_WORKSPACE_ID \
    RESOURCE_GROUP_NAME=$RESOURCE_GROUP_NAME
```

## Architecture Comparison

### Old (Azure Functions + Durable Functions)

- Complex setup with Extension Bundle V4
- Durable Functions state management
- Azure Functions runtime compatibility issues
- Limited to Azure Functions hosting

### New (FastAPI + APScheduler)

- Simple REST API (FastAPI)
- In-memory state tracking
- APScheduler for reliable cron jobs
- Runs anywhere: Docker, Container Apps, Kubernetes, VMs

## Benefits

1. **Simple** - No Azure Functions complexity
2. **Portable** - Runs anywhere Docker runs
3. **Testable** - Easy to test locally
4. **Debuggable** - Standard Python debugging
5. **Observable** - Built-in health checks and metrics
6. **Reliable** - APScheduler handles cron scheduling

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs <container-id>

# Verify environment variables
docker exec <container-id> env | grep AZURE
```

### Health check fails

```bash
# Test health endpoint directly
curl http://localhost:8080/

# Check if port is bound
netstat -tulpn | grep 80
```

### Validation fails

```bash
# Test validation manually
curl -X POST http://localhost:8080/api/validate | jq .

# Check Azure credentials
az account show
```

### Orchestration fails

```bash
# Check execution status
curl http://localhost:8080/api/executions | jq .

# Get execution details
curl http://localhost:8080/api/executions/<run-id> | jq .
```

## Development

### Adding new endpoints

Edit `orchestrator_server.py`:

```python
@app.get("/api/my-endpoint")
async def my_endpoint():
    return {"status": "ok"}
```

### Modifying orchestration logic

Edit the `run_orchestration()` function in `orchestrator_server.py`.

### Running tests

```bash
# Start the server
python orchestrator_server.py

# Run tests
./test_orchestrator.sh
```

## License

Same as Azure HayMaker project.
