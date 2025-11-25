# Azure HayMaker Infrastructure

Infrastructure as Code for Azure HayMaker using Azure Bicep.

## Overview

This directory contains all infrastructure definitions for deploying Azure HayMaker using Container Apps architecture.

```
infra/
├── bicep/
│   ├── main.bicep              # Container Apps orchestration template
│   ├── modules/                # Reusable Bicep modules
│   │   ├── log-analytics.bicep
│   │   ├── storage.bicep
│   │   ├── servicebus.bicep
│   │   ├── keyvault.bicep
│   │   ├── cosmosdb.bicep
│   │   ├── containerapp-environment.bicep
│   │   ├── container-registry.bicep
│   │   └── orchestrator-containerapp.bicep
│   ├── parameters/             # Environment-specific parameters
│   │   ├── dev.bicepparam
│   │   ├── staging.bicepparam
│   │   └── prod.bicepparam
│   └── archive/                # Archived templates (Function App, VM)
└── README.md
```

## Architecture

**Single Architecture: Container Apps with E16 Workload Profile (128GB RAM)**

This infrastructure deploys all HayMaker components to Azure Container Apps, following ruthless simplicity principles. Previous architectures (Function App, VM-based) have been archived.

### Resources Deployed

| Resource | Purpose | Module |
|----------|---------|--------|
| Log Analytics Workspace | Centralized logging and monitoring | log-analytics.bicep |
| Storage Account | Blob storage for logs, reports, state | storage.bicep |
| Service Bus | Message queue for agent logs and requests | servicebus.bicep |
| Key Vault | Secure secret storage | keyvault.bicep |
| Container Apps Environment | E16 workload profile (128GB RAM) | containerapp-environment.bicep |
| Orchestrator Container App | Main orchestration logic | orchestrator-containerapp.bicep |
| Container Registry | Private image registry (created by workflow) | container-registry.bicep |

### Resource Naming Convention

Resources follow this naming pattern:

```
{namingPrefix}-{environment}-{resourceType}
```

Examples:
- `haymaker-dev-func` - Function App in dev
- `haymaker-prod-kv` - Key Vault in production
- `haymakerdevst123456` - Storage Account (no hyphens, with unique suffix)

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
az bicep build --file bicep/main.bicep

# Validate deployment
az deployment sub validate \
  --location eastus \
  --template-file bicep/main.bicep \
  --parameters bicep/parameters/dev.bicepparam \
  --parameters adminObjectIds="['<your-object-id>']" \
  --parameters githubOidcClientId="<client-id>"
```

### Preview Changes

```bash
# What-if analysis (preview changes without deploying)
az deployment sub what-if \
  --location eastus \
  --template-file bicep/main.bicep \
  --parameters bicep/parameters/dev.bicepparam \
  --parameters adminObjectIds="['<your-object-id>']" \
  --parameters githubOidcClientId="<client-id>"
```

### Deploy Locally

```bash
# Deploy to dev environment
az deployment sub create \
  --name "haymaker-dev-$(date +%s)" \
  --location eastus \
  --template-file bicep/main.bicep \
  --parameters bicep/parameters/dev.bicepparam \
  --parameters adminObjectIds="['<your-object-id>']" \
  --parameters githubOidcClientId="<client-id>"
```

## Module Documentation

### main.bicep

Root template that orchestrates all module deployments.

**Parameters**:
- `environment`: Environment name (dev, staging, prod)
- `location`: Azure region (default: eastus)
- `namingPrefix`: Resource name prefix (default: haymaker)
- `tenantId`: Azure AD tenant ID
- `subscriptionId`: Azure subscription ID
- `adminObjectIds`: Object IDs with Key Vault admin access
- `githubOidcClientId`: Client ID for GitHub OIDC

**Outputs**:
- Resource group name
- All resource names and endpoints
- Function App URL and principal ID

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
- Function App gets Key Vault Secrets User role (via main.bicep)

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

Deploys Container Apps Environment with E16 workload profile (128GB RAM).

**Parameters**:
- `environmentName`: Environment name
- `logAnalyticsWorkspaceId`: Workspace resource ID
- `workloadProfiles`: Workload profile configurations (default: E16 with 1-3 instances)

**Outputs**:
- Environment ID and name
- Default domain

### orchestrator-containerapp.bicep

Deploys orchestrator as a Container App with 128GB RAM allocation.

**Parameters**:
- `containerAppName`: Container App name
- `environmentId`: Container Apps Environment ID
- `containerImage`: Orchestrator container image
- `containerRegistry`: ACR login server
- `keyVaultUri`: Key Vault URI for secret references
- `serviceBusNamespace`: Service Bus namespace
- `storageAccountName`: Storage account name
- `simulationSize`: Simulation size (small, medium, large)

**Outputs**:
- Container App ID, name, and FQDN
- Principal ID (managed identity)

**Configuration**:
- E16 workload profile (128GB RAM, 16 vCPU)
- Managed identity for Key Vault access
- Environment variables for all service connections

## Deployment Workflow

### Automated (GitOps)

Deployments are automated via GitHub Actions:

1. **Dev**: Push to `develop` branch
2. **Staging**: Push to `main` branch
3. **Production**: Create GitHub release

See: [Deployment Guide](../docs/DEPLOYMENT.md)

### Manual Deployment Steps

1. **Validate**:
   ```bash
   az bicep build --file bicep/main.bicep
   az deployment sub validate --template-file bicep/main.bicep --parameters @bicep/parameters/dev.bicepparam
   ```

2. **What-If**:
   ```bash
   az deployment sub what-if --template-file bicep/main.bicep --parameters @bicep/parameters/dev.bicepparam
   ```

3. **Deploy**:
   ```bash
   az deployment sub create --template-file bicep/main.bicep --parameters @bicep/parameters/dev.bicepparam
   ```

4. **Inject Secrets**:
   ```bash
   az keyvault secret set --vault-name <kv-name> --name main-sp-client-secret --value "<secret>"
   az keyvault secret set --vault-name <kv-name> --name anthropic-api-key --value "<key>"
   ```

5. **Deploy Container App**:
   Container images are built and deployed via GitHub Actions workflow. See [.github/workflows/deploy-containerapps.yml](../.github/workflows/deploy-containerapps.yml)

## Troubleshooting

### Common Issues

#### Bicep Compilation Fails

```bash
# Update Bicep CLI
az bicep upgrade

# Check for syntax errors
az bicep build --file bicep/main.bicep
```

#### Deployment Validation Fails

```bash
# Check parameter values
cat bicep/parameters/dev.bicepparam

# Verify subscription and permissions
az account show
az role assignment list --assignee $(az account show --query user.name -o tsv)
```

#### Resource Name Conflicts

```bash
# Check existing resources
az resource list --name "*haymaker*" --output table

# Use different naming prefix
az deployment sub create \
  --template-file bicep/main.bicep \
  --parameters @bicep/parameters/dev.bicepparam \
  --parameters namingPrefix="myorg"
```

### Debug Mode

Enable detailed ARM template logging:

```bash
az deployment sub create \
  --template-file bicep/main.bicep \
  --parameters @bicep/parameters/dev.bicepparam \
  --debug
```

## Best Practices

### Development

- Always validate before deploying
- Use what-if to preview changes
- Test in dev environment first
- Never hardcode secrets in templates

### Production

- Use parameter files for configuration
- Enable purge protection on Key Vault
- Use GRS redundancy for critical data
- Enable versioning on storage accounts
- Review what-if output before deploying

### Maintenance

- Regularly update Bicep modules
- Keep parameter files in sync
- Document custom modifications
- Use semantic versioning for releases

## Additional Resources

- [Azure Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Bicep Best Practices](https://learn.microsoft.com/azure/azure-resource-manager/bicep/best-practices)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [GitOps Setup Guide](../docs/GITOPS_SETUP.md)
