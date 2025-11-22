# Orchestrator Quick Start

**Get the orchestrator running in 5 minutes.**

## Local Testing

```bash
# 1. Copy environment template
cp .env.orchestrator.example .env

# 2. Edit .env with your Azure credentials
vim .env

# 3. Run the orchestrator
./run_orchestrator.sh

# 4. Test it works
curl http://localhost:8080/
curl http://localhost:8080/api/metrics
curl http://localhost:8080/api/scenarios
```

## Docker Compose (Recommended)

```bash
# 1. Setup environment
cp .env.orchestrator.example .env
vim .env

# 2. Start services
docker-compose -f docker-compose.orchestrator.yml up -d

# 3. View logs
docker-compose -f docker-compose.orchestrator.yml logs -f

# 4. Test endpoints
./test_orchestrator.sh

# 5. Stop services
docker-compose -f docker-compose.orchestrator.yml down
```

## Deploy to Azure

```bash
# 1. Build and push image
export CONTAINER_REGISTRY="yourregistry"
az acr build \
  --registry $CONTAINER_REGISTRY \
  --image azure-haymaker-orchestrator:latest \
  --file Dockerfile.orchestrator \
  .

# 2. Create Container App
export RESOURCE_GROUP="azure-haymaker-rg"
export CONTAINER_ENV="haymaker-container-env"
export ACR_NAME="${CONTAINER_REGISTRY}.azurecr.io"

az containerapp create \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_NAME/azure-haymaker-orchestrator:latest \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 2 \
  --memory 4Gi \
  --registry-server $ACR_NAME \
  --registry-identity system \
  --env-vars \
    AZURE_TENANT_ID=$AZURE_TENANT_ID \
    AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
    # ... other env vars ...

# 3. Enable managed identity and grant permissions
az containerapp identity assign \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --system-assigned

PRINCIPAL_ID=$(az containerapp identity show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --query principalId -o tsv)

# Grant Key Vault access
az keyvault set-policy \
  --name your-keyvault \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list

# Grant Contributor role
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Contributor" \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID

# 4. Test deployment
FQDN=$(az containerapp show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

curl https://$FQDN/
```

## Troubleshooting

### Won't start locally
```bash
# Check environment variables
docker exec azure-haymaker-orchestrator env | grep AZURE

# Check logs
docker logs azure-haymaker-orchestrator
```

### Won't start in Azure
```bash
# Check logs
az containerapp logs show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --tail 100

# Check revision status
az containerapp revision list \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP
```

### Validation fails
```bash
# Test validation endpoint
curl -X POST http://localhost:8080/api/validate | jq .

# Verify Azure credentials
az account show
az keyvault secret show --vault-name your-keyvault --name anthropic-api-key
```

## Key Files

- `orchestrator_server.py` - Main FastAPI application
- `Dockerfile.orchestrator` - Docker image definition
- `docker-compose.orchestrator.yml` - Docker Compose configuration
- `requirements-orchestrator.txt` - Python dependencies
- `.env.orchestrator.example` - Environment variable template
- `run_orchestrator.sh` - Quick start script
- `test_orchestrator.sh` - Test script

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/metrics` | GET | Execution metrics |
| `/api/executions` | GET | List all executions |
| `/api/executions/{id}` | GET | Get execution details |
| `/api/execute` | POST | Trigger execution manually |
| `/api/validate` | POST | Validate environment |
| `/api/scenarios` | GET | List available scenarios |

## Scheduled Execution

Runs automatically 4x daily:
- 00:00 UTC
- 06:00 UTC
- 12:00 UTC
- 18:00 UTC

## Next Steps

1. Read `ORCHESTRATOR_README.md` for detailed documentation
2. Read `DEPLOY_ORCHESTRATOR.md` for Azure deployment guide
3. Customize orchestration logic in `orchestrator_server.py`
4. Set up monitoring and alerts

## Support

- Documentation: `ORCHESTRATOR_README.md`
- Deployment: `DEPLOY_ORCHESTRATOR.md`
- Issues: Check logs and health endpoints
