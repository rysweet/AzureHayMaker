# Cross-Tenant Configuration Guide

This guide covers configuring Azure HayMaker for cross-tenant and multi-tenant orchestration.

## Configuration Methods

Azure HayMaker configuration follows this priority order:

1. **Environment variables** (highest priority)
2. **Azure Key Vault secrets**
3. **.env file** (local development only)

## Single Cross-Tenant Setup

For deploying to a single target tenant different from the orchestrator tenant.

### Required Environment Variables

```bash
# Target tenant (where scenarios deploy)
export AZURE_TENANT_ID="target-tenant-id"
export AZURE_SUBSCRIPTION_ID="target-subscription-id"

# Orchestrator service principal (in infrastructure tenant)
export AZURE_CLIENT_ID="orchestrator-sp-client-id"

# Cross-tenant credentials (SP in target tenant)
export TARGET_TENANT_SP_CLIENT_ID="target-tenant-sp-client-id"
export TARGET_TENANT_SP_CLIENT_SECRET="target-tenant-sp-secret"

# Key Vault for additional secrets
export KEY_VAULT_URL="https://haymaker-kv.vault.azure.net"

# Azure services configuration
export SERVICE_BUS_NAMESPACE="haymaker-sb.servicebus.windows.net"
export CONTAINER_REGISTRY="haymakerregistry.azurecr.io"
export CONTAINER_IMAGE="haymaker-agent:latest"
export SIMULATION_SIZE="medium"  # small, medium, or large

# Storage configuration
export STORAGE_ACCOUNT_NAME="haymakerstorage"
export TABLE_STORAGE_ACCOUNT_NAME="haymakertables"

# Monitoring
export LOG_ANALYTICS_WORKSPACE_ID="workspace-id"
```

### Key Vault Secrets

These secrets must be stored in Key Vault:

| Secret Name | Description |
|:------------|:------------|
| `main-sp-client-secret` | Orchestrator SP secret |
| `anthropic-api-key` | Anthropic API key for Claude |
| `log-analytics-workspace-key` | Log Analytics workspace key |
| `target-tenant-{id}-sp-secret` | Target tenant SP secret (optional) |

```bash
# Store secrets in Key Vault
az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "main-sp-client-secret" \
  --value "your-sp-secret"

az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "anthropic-api-key" \
  --value "sk-ant-..."

az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "log-analytics-workspace-key" \
  --value "workspace-key-value"
```

## Multi-Tenant Setup

For deploying to multiple target tenants from a single orchestrator.

### Tenant Configuration in Key Vault

Each target tenant requires two secrets following this naming convention:

```
tenant-{prefix}-config   # JSON configuration
tenant-{prefix}-secret   # SP client secret
```

#### Config Secret Format

```json
{
  "tenant_id": "12345678-1234-1234-1234-123456789abc",
  "subscription_id": "87654321-4321-4321-4321-cba987654321",
  "sp_client_id": "abcdef12-3456-7890-abcd-ef1234567890",
  "display_name": "Customer A Production",
  "enabled": true,
  "resource_group": "rg-haymaker-customerA"
}
```

#### Config Fields

| Field | Required | Description |
|:------|:---------|:------------|
| `tenant_id` | Yes | Azure AD tenant ID |
| `subscription_id` | Yes | Target subscription for deployments |
| `sp_client_id` | Yes | Service principal client ID in this tenant |
| `display_name` | No | Human-readable name (default: tenant-{id}) |
| `enabled` | No | Whether tenant is active (default: true) |
| `resource_group` | No | Default resource group for deployments |

### Adding Tenant Configurations

```bash
# Add Customer A tenant
az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "tenant-customerA-config" \
  --value '{
    "tenant_id": "12345678-1234-1234-1234-123456789abc",
    "subscription_id": "sub-customerA-001",
    "sp_client_id": "sp-customerA-client-id",
    "display_name": "Customer A Production",
    "enabled": true,
    "resource_group": "rg-haymaker"
  }'

az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "tenant-customerA-secret" \
  --value "customer-A-sp-secret-value"

# Add Customer B tenant
az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "tenant-customerB-config" \
  --value '{
    "tenant_id": "87654321-4321-4321-4321-cba987654321",
    "subscription_id": "sub-customerB-001",
    "sp_client_id": "sp-customerB-client-id",
    "display_name": "Customer B Staging",
    "enabled": true
  }'

az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "tenant-customerB-secret" \
  --value "customer-B-sp-secret-value"
```

### Filtering Tenants

Use prefix filtering to load subsets of tenants:

```bash
# Load only production tenants (tenant-prod-*)
export TENANT_PREFIX_FILTER="prod"

# Load only customer tenants (tenant-customer-*)
export TENANT_PREFIX_FILTER="customer"
```

## Service Principal Setup

### Creating Cross-Tenant Service Principal

1. **Register multi-tenant app in infrastructure tenant:**

```bash
# Create multi-tenant app registration
az ad app create \
  --display-name "HayMaker Cross-Tenant" \
  --sign-in-audience "AzureADMultipleOrgs"
```

2. **Create service principal in target tenant:**

In target tenant, have an admin consent to the app:

```
https://login.microsoftonline.com/{target-tenant-id}/adminconsent?client_id={app-id}
```

3. **Grant permissions in target tenant:**

```bash
# Switch to target tenant context
az login --tenant "target-tenant-id"

# Get the SP object ID in target tenant
SP_OBJECT_ID=$(az ad sp show --id "app-id" --query id -o tsv)

# Assign Contributor role on subscription
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/{subscription-id}"
```

### Required Permissions

| Permission | Scope | Purpose |
|:-----------|:------|:--------|
| Contributor | Subscription | Deploy Container Apps and resources |
| User Access Administrator | Subscription | Create ephemeral SPs for scenarios |
| Key Vault Secrets Officer | Key Vault | Store ephemeral SP secrets |

## VNet Configuration

For secure deployments, configure VNet integration:

```bash
export VNET_INTEGRATION_ENABLED="true"
export VNET_RESOURCE_GROUP="rg-networking"
export VNET_NAME="vnet-haymaker"
export SUBNET_NAME="subnet-containers"
```

### VNet Requirements

- Subnet must be delegated to Container Apps
- Minimum /23 CIDR for Container Apps Environment
- NSG rules allowing outbound to Azure services

## Simulation Size

Control how many scenarios run per execution:

| Size | Scenario Count | Use Case |
|:-----|:---------------|:---------|
| `small` | 5 | Development, testing |
| `medium` | 15 | Standard operations |
| `large` | 30 | Full simulation |

```bash
export SIMULATION_SIZE="medium"
```

## Optional Configuration

### Container Configuration

```bash
export CONTAINER_MEMORY_GB="64"      # Default: 64
export CONTAINER_CPU_CORES="2"       # Default: 2
export CONTAINER_TIMEOUT_HOURS="10"  # Default: 10
export EXECUTION_DURATION_HOURS="8"  # Default: 8
```

### Service Principal Rotation

```bash
export SP_SECRET_ROTATION_DAYS="30"           # Days between rotations
export SP_SECRET_EXPIRATION_WARNING_DAYS="7"  # Warning before expiration
export SP_SECRET_AUTO_ROTATE="true"           # Enable auto-rotation
export SP_SECRET_MAX_AGE_DAYS="90"            # Force rotation after 90 days
```

### Webhooks

```bash
export WEBHOOK_URL="https://your-endpoint/webhooks/haymaker"
```

## Complete Example Configuration

### Infrastructure Tenant .env

```bash
# Infrastructure tenant identity
AZURE_CLIENT_ID=orchestrator-sp-client-id

# Target tenant (default)
AZURE_TENANT_ID=target-tenant-id
AZURE_SUBSCRIPTION_ID=target-subscription-id

# Cross-tenant SP (optional, for single cross-tenant)
TARGET_TENANT_SP_CLIENT_ID=target-sp-client-id
TARGET_TENANT_SP_CLIENT_SECRET=target-sp-secret

# Key Vault
KEY_VAULT_URL=https://haymaker-kv.vault.azure.net

# Azure Services
SERVICE_BUS_NAMESPACE=haymaker-sb.servicebus.windows.net
SERVICE_BUS_TOPIC=agent-logs
CONTAINER_REGISTRY=haymakerregistry.azurecr.io
CONTAINER_IMAGE=haymaker-agent:latest

# Simulation
SIMULATION_SIZE=medium
RESOURCE_GROUP_NAME=azure-haymaker-rg

# Storage
STORAGE_ACCOUNT_NAME=haymakerstorage
TABLE_STORAGE_ACCOUNT_NAME=haymakertables
COSMOSDB_ENDPOINT=https://haymaker-cosmos.documents.azure.com:443/
COSMOSDB_DATABASE=haymaker

# Monitoring
LOG_ANALYTICS_WORKSPACE_ID=workspace-guid

# VNet (optional)
VNET_INTEGRATION_ENABLED=false
```

## Validation

Verify configuration using the validate endpoint:

```bash
curl -X POST https://your-orchestrator/api/validate \
  -H "Authorization: Bearer <token>"
```

**Response:**

```json
{
  "overall_passed": true,
  "results": [
    {"check": "key_vault_access", "passed": true},
    {"check": "target_tenant_auth", "passed": true},
    {"check": "container_registry_access", "passed": true},
    {"check": "storage_access", "passed": true}
  ]
}
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|:------|:------|:---------|
| "Target tenant SP secret not found" | Missing Key Vault secret | Add `target-tenant-{id}-sp-secret` to Key Vault |
| "Cross-tenant mode enabled but no SP" | Missing `TARGET_TENANT_SP_CLIENT_ID` | Set environment variable or add to Key Vault |
| "Key Vault access denied" | Orchestrator lacks permissions | Grant "Key Vault Secrets User" role |
| "VNet integration enabled but config missing" | Incomplete VNet config | Set all VNet variables or disable integration |

### Verify Cross-Tenant Mode

Check if cross-tenant mode is active:

```bash
curl https://your-orchestrator/api/status \
  -H "Authorization: Bearer <token>"
```

Look for `mode: "cross-tenant"` in the response.

## Related Documentation

- [Architecture](./ARCHITECTURE.md) - System architecture
- [API Reference](./API.md) - Endpoint specifications
- [Security Guide](/AzureHayMaker/security) - Security best practices
