# Azure HayMaker Infrastructure

Infrastructure as Code for Azure HayMaker using Azure Bicep.

## Overview

This directory contains all infrastructure definitions for deploying Azure HayMaker. The orchestrator runs on Azure Container Apps with E16 workload profile (128GB RAM) using KEDA CRON triggers for scheduling.

```
infra/
├── bicep/
│   ├── main-containerapps.bicep   # Primary: Container Apps deployment
│   ├── main-vm.bicep              # Alternative: VM deployment
│   ├── modules/                   # Reusable Bicep modules
│   │   ├── log-analytics.bicep
│   │   ├── storage.bicep
│   │   ├── servicebus.bicep
│   │   ├── keyvault.bicep
│   │   ├── cosmosdb.bicep
│   │   ├── containerapp-environment.bicep
│   │   ├── orchestrator-containerapp.bicep
│   │   └── container-registry.bicep
│   └── (no parameter files - passed via workflow)
└── README.md
```

## Architecture

### Deployment Options

| Option | Template | Use Case |
|--------|----------|----------|
| **Container Apps (Primary)** | main-containerapps.bicep | Production orchestrator with 128GB RAM, KEDA CRON scheduling |
| **VM (Alternative)** | main-vm.bicep | Alternative deployment for specific requirements |

### Resources Deployed (Container Apps)

| Resource | Purpose | Module |
|----------|---------|--------|
| Log Analytics Workspace | Centralized logging and monitoring | log-analytics.bicep |
| Storage Account | Blob storage for logs, reports, state | storage.bicep |
| Service Bus | Message queue for agent logs and requests | servicebus.bicep |
| Key Vault | Secure secret storage | keyvault.bicep |
| Cosmos DB | NoSQL database for metrics | cosmosdb.bicep |
| Container Apps Environment | E16 workload profile hosting | containerapp-environment.bicep |
| Container Registry | Private image registry | container-registry.bicep |
| Container App (Orchestrator) | FastAPI orchestrator (128GB RAM) | orchestrator-containerapp.bicep |

### Resource Naming Convention

Resources follow this naming pattern:

```
{namingPrefix}-{environment}-{resourceType}
```

Examples:
- `haymaker-dev-orchestrator` - Container App in dev
- `haymaker-prod-kv` - Key Vault in production
- `haymakerprodst123456` - Storage Account (no hyphens, with unique suffix)

### Environment Differences

| Aspect | Dev | Staging | Production |
|--------|-----|---------|------------|
| SKU | Basic/Consumption | Standard | Premium/Standard |
| Redundancy | LRS | LRS | GRS |
| Retention | 7 days | 30 days | 90 days |
| Throughput | Serverless | Serverless | 400 RU/s |
| Cost | ~$50-100/mo | ~$100-200/mo | ~$300-500/mo |

## Prerequisites

### Required Tools

- Azure CLI (v2.50.0+): `az --version`
- Bicep CLI: `az bicep version`

### Required Permissions

- Azure subscription Owner or Contributor role
- Ability to create resource groups
- Ability to assign RBAC roles

## Local Development

### Validate Templates

```bash
# Compile Bicep to ARM JSON
az bicep build --file bicep/main-containerapps.bicep

# Validate deployment (parameters passed directly)
az deployment group validate \
  --resource-group "haymaker-dev-rg" \
  --template-file bicep/main-containerapps.bicep \
  --parameters environment=dev \
               adminObjectIds="['<your-object-id>']" \
               githubOidcClientId="<client-id>"
```

### Preview Changes

```bash
# What-if analysis (preview changes without deploying)
az deployment group what-if \
  --resource-group "haymaker-dev-rg" \
  --template-file bicep/main-containerapps.bicep \
  --parameters environment=dev \
               adminObjectIds="['<your-object-id>']" \
               githubOidcClientId="<client-id>"
```

### Deploy Locally

```bash
# Create resource group first
az group create --name "haymaker-dev-rg" --location eastus

# Deploy Container Apps infrastructure
az deployment group create \
  --name "haymaker-dev-$(date +%s)" \
  --resource-group "haymaker-dev-rg" \
  --template-file bicep/main-containerapps.bicep \
  --parameters environment=dev \
               adminObjectIds="['<your-object-id>']" \
               githubOidcClientId="<client-id>"
```

## Module Documentation

### main-containerapps.bicep

Primary template deploying Container Apps-based orchestrator.

**Parameters**:
- `environment`: Environment name (dev, staging, prod)
- `adminObjectIds`: Object IDs with Key Vault admin access
- `githubOidcClientId`: Client ID for GitHub OIDC
- `simulationSize`: Simulation size configuration
- `orchestratorImage`: Container image for orchestrator
- `acrPassword`: ACR password for image pull

**Outputs**:
- Resource group name
- Orchestrator name and FQDN
- Key Vault name
- All resource endpoints

**Architecture**:
- E16 workload profile (128GB RAM, 16 vCPU)
- KEDA CRON triggers (4x daily: 00:00, 06:00, 12:00, 18:00 UTC)
- System-assigned managed identity
- FastAPI orchestrator running orchestrator_server.py

### main-vm.bicep

Alternative template deploying VM-based orchestrator.

**Use when**:
- Container Apps not suitable for specific requirements
- Need direct VM access for debugging
- Specific networking requirements

### log-analytics.bicep

Deploys Log Analytics workspace for centralized logging.

**Parameters**:
- `workspaceName`: Workspace name
- `location`: Azure region
- `retentionInDays`: Log retention period (30-730)
- `sku`: Workspace SKU (default: PerGB2018)

**Outputs**:
- Workspace ID and name
- Customer ID for log ingestion
- Primary shared key

### storage.bicep

Deploys storage account with containers and tables.

**Parameters**:
- `storageAccountName`: Globally unique name
- `sku`: Storage SKU (Standard_LRS, Standard_GRS, etc.)
- `enableVersioning`: Enable blob versioning
- `retentionDays`: Deleted blob retention

**Outputs**:
- Storage account ID and name
- Connection string
- Primary endpoints

**Containers Created**:
- `logs` - Agent execution logs
- `reports` - Execution reports
- `state` - Orchestrator state

**Tables Created**:
- `executions` - Execution tracking
- `ratelimits` - Rate limiting state

### servicebus.bicep

Deploys Service Bus namespace with topic and queue.

**Parameters**:
- `namespaceName`: Namespace name
- `sku`: Service Bus SKU (Basic, Standard, Premium)
- `topicName`: Topic for agent logs
- `queueName`: Queue for execution requests

**Outputs**:
- Namespace ID and name
- Topic and queue names
- Connection string

### keyvault.bicep

Deploys Key Vault with RBAC authorization.

**Parameters**:
- `keyVaultName`: Globally unique name
- `tenantId`: Azure AD tenant ID
- `adminObjectIds`: Admin principal IDs
- `enableSoftDelete`: Enable soft delete
- `enablePurgeProtection`: Enable purge protection

**Outputs**:
- Key Vault ID, name, and URI

**RBAC Roles**:
- Admins get Key Vault Administrator role
- Container App gets Key Vault Secrets User role

### cosmosdb.bicep

Deploys Cosmos DB account with database and containers.

**Parameters**:
- `accountName`: Globally unique name
- `databaseName`: Database name (default: haymaker)
- `throughput`: RU/s throughput (0 for serverless)

**Outputs**:
- Account ID, name, and endpoint
- Database and container names
- Connection string

**Containers Created**:
- `metrics` - Execution metrics (partitioned by scenario_name)
- `runs` - Run records (partitioned by run_id)

### containerapp-environment.bicep

Deploys Container Apps Environment with E16 workload profile.

**Parameters**:
- `environmentName`: Environment name
- `logAnalyticsWorkspaceId`: Workspace resource ID
- `logAnalyticsSharedKey`: Workspace shared key

**Outputs**:
- Environment ID and name
- Default domain
- Static IP

### container-registry.bicep

Deploys Azure Container Registry for orchestrator image.

**Parameters**:
- `registryName`: Globally unique name (alphanumeric only)
- `sku`: Registry SKU (Basic, Standard, Premium)
- `adminUserEnabled`: Enable admin user

**Outputs**:
- Registry ID, name, and login server
- Admin username and password

### orchestrator-containerapp.bicep

Deploys the Container App running the FastAPI orchestrator.

**Parameters**:
- `name`: Container App name
- `environmentId`: Container Apps Environment ID
- `image`: Container image to deploy
- `keyVaultUri`: Key Vault URI for secret references

**Outputs**:
- Container App ID, name, and FQDN
- Principal ID (managed identity)

**Configuration**:
- 128GB RAM (E16 workload profile)
- KEDA CRON scaling (4x daily)
- System-assigned managed identity
- Health checks configured

## Deployment Workflow

### Automated (GitOps)

Deployments are automated via GitHub Actions using `deploy-containerapps.yml`:

1. **Environment Selection**: Choose dev, staging, or prod via workflow_dispatch
2. **Auto-trigger**: Push to `develop` or `main` branch

See: [Deployment Guide](../docs/DEPLOYMENT.md)

### Manual Deployment Steps

1. **Validate**:
   ```bash
   az bicep build --file bicep/main-containerapps.bicep
   ```

2. **Create Resource Group**:
   ```bash
   az group create --name "haymaker-dev-rg" --location eastus
   ```

3. **Deploy**:
   ```bash
   az deployment group create \
     --resource-group "haymaker-dev-rg" \
     --template-file bicep/main-containerapps.bicep \
     --parameters environment=dev \
                  adminObjectIds="['<your-object-id>']" \
                  githubOidcClientId="<client-id>"
   ```

4. **Inject Secrets**:
   ```bash
   az keyvault secret set --vault-name <kv-name> --name main-sp-client-secret --value "<secret>"
   az keyvault secret set --vault-name <kv-name> --name anthropic-api-key --value "<key>"
   ```

## Troubleshooting

### Common Issues

#### Bicep Compilation Fails

```bash
# Update Bicep CLI
az bicep upgrade

# Check for syntax errors
az bicep build --file bicep/main-containerapps.bicep
```

#### Container App Not Starting

```bash
# Check container app status
az containerapp show \
  --name <container-app-name> \
  --resource-group <rg-name> \
  --query "properties.provisioningState"

# Check logs
az containerapp logs show \
  --name <container-app-name> \
  --resource-group <rg-name> \
  --follow
```

#### ACR Pull Permission Issues

```bash
# Get Container App's managed identity
PRINCIPAL_ID=$(az containerapp show \
  --name <container-app-name> \
  --resource-group <rg-name> \
  --query "identity.principalId" -o tsv)

# Grant AcrPull role
az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role AcrPull \
  --scope <acr-resource-id>
```

### Debug Mode

Enable detailed ARM template logging:

```bash
az deployment group create \
  --resource-group "haymaker-dev-rg" \
  --template-file bicep/main-containerapps.bicep \
  --parameters environment=dev \
  --debug
```

## Best Practices

### Development

- Always validate before deploying
- Use what-if to preview changes
- Test in dev environment first
- Never hardcode secrets in templates

### Production

- Enable purge protection on Key Vault
- Use GRS redundancy for critical data
- Enable versioning on storage accounts
- Review what-if output before deploying

### Maintenance

- Regularly update Bicep modules
- Document custom modifications
- Use semantic versioning for releases

## Additional Resources

- [Azure Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [KEDA Scaling Documentation](https://keda.sh/docs/)
- [Deployment Guide](../docs/DEPLOYMENT.md)
