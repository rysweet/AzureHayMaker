# Cross-Tenant Orchestration

Deploy Azure HayMaker scenarios across multiple Azure tenants from a single infrastructure tenant.

## Overview

Cross-tenant orchestration enables a central orchestrator in an "infrastructure tenant" to deploy and manage scenarios in one or more "target tenants." This is useful for:

- **Managed service providers (MSPs)** running simulations across customer tenants
- **Large enterprises** with multiple Azure AD tenants
- **Security teams** testing detection across isolated environments

## When to Use

| Scenario | Recommended Mode |
|:---------|:-----------------|
| Single organization, one tenant | Single-tenant (default) |
| MSP managing multiple customers | Multi-tenant orchestration |
| Enterprise with dev/staging/prod tenants | Multi-tenant orchestration |
| Security team testing cross-boundary detection | Cross-tenant mode |

## Quick Start

### Prerequisites

- Azure HayMaker orchestrator deployed in infrastructure tenant
- Service principal with permissions in target tenant
- Target tenant SP credentials stored in Key Vault

### 1. Configure Target Tenant Credentials

Set environment variables or store in Key Vault:

```bash
# Environment variables (for single target tenant)
export TARGET_TENANT_SP_CLIENT_ID="your-target-sp-client-id"
export TARGET_TENANT_SP_CLIENT_SECRET="your-target-sp-secret"
export AZURE_TENANT_ID="target-tenant-id"
export AZURE_SUBSCRIPTION_ID="target-subscription-id"
```

Or store in Key Vault for multi-tenant:

```bash
# Key Vault secret naming convention
# tenant-{prefix}-config: JSON with tenant metadata
# tenant-{prefix}-secret: SP client secret

az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "tenant-customerA-config" \
  --value '{"tenant_id":"...", "subscription_id":"...", "sp_client_id":"...", "display_name":"Customer A", "enabled":true}'

az keyvault secret set \
  --vault-name "haymaker-kv" \
  --name "tenant-customerA-secret" \
  --value "sp-client-secret-value"
```

### 2. Execute Scenarios

Single target tenant:

```bash
curl -X POST https://your-orchestrator/api/execute \
  -H "Content-Type: application/json" \
  -d '{"scenarios": ["compute-01-linux-vm-web-server"]}'
```

Multi-tenant (when Key Vault tenants are configured):

```bash
curl -X POST https://your-orchestrator/api/execute/multi-tenant \
  -H "Content-Type: application/json" \
  -d '{"scenarios": ["compute-01-linux-vm-web-server"]}'
```

### 3. Monitor Execution

```bash
# Get execution status
curl https://your-orchestrator/api/executions/{execution_id}

# Get per-tenant status (multi-tenant)
curl https://your-orchestrator/api/executions/{execution_id}/tenants
```

## Architecture

```
Infrastructure Tenant                    Target Tenant(s)
┌─────────────────────────┐             ┌─────────────────────────┐
│  HayMaker Orchestrator  │             │   Deployed Resources    │
│  - FastAPI Service      │────────────>│   - Container Apps      │
│  - Key Vault (secrets)  │  Cross-     │   - Service Principals  │
│  - Table Storage        │  Tenant     │   - Scenario Resources  │
│  - Blob Storage         │  Auth       │                         │
└─────────────────────────┘             └─────────────────────────┘
```

See [Architecture Documentation](./ARCHITECTURE.md) for detailed diagrams and component descriptions.

## Configuration Reference

| Variable | Required | Description |
|:---------|:---------|:------------|
| `AZURE_TENANT_ID` | Yes | Target tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Yes | Target subscription ID |
| `TARGET_TENANT_SP_CLIENT_ID` | Cross-tenant | SP client ID in target tenant |
| `TARGET_TENANT_SP_CLIENT_SECRET` | Cross-tenant | SP secret for target tenant |
| `KEY_VAULT_URL` | Yes | Key Vault URL for secrets |

See [Configuration Guide](./CONFIGURATION.md) for complete reference.

## Documentation

- [Architecture](./ARCHITECTURE.md) - Two-tier architecture and data flow
- [API Reference](./API.md) - Endpoint specifications and examples
- [Configuration](./CONFIGURATION.md) - Environment variables and Key Vault setup

## Related Documentation

- [Deployment Guide](/AzureHayMaker/deployment) - Initial orchestrator deployment
- [Security Guide](/AzureHayMaker/security) - Authentication and authorization
- [API Reference](/AzureHayMaker/api) - Complete API documentation
