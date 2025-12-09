---
layout: default
title: Cross-Tenant Orchestration Guide
parent: Guides
nav_order: 1
description: "Complete guide to setting up and managing cross-tenant orchestration in Azure HayMaker"
permalink: /guides/cross-tenant-orchestration/
---

# Cross-Tenant Orchestration Guide
{: .no_toc }

Deploy Azure HayMaker scenarios across multiple Azure tenants from a single orchestrator.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

Cross-tenant orchestration enables Azure HayMaker to manage workloads across multiple Azure tenants from a centralized infrastructure tenant. The orchestrator runs in your infrastructure tenant while deploying scenarios to one or more target tenants.

### Why Cross-Tenant Orchestration?

**Managed Service Providers (MSPs)**
- Manage 5-50+ customer tenants from single orchestrator
- Isolated telemetry per customer
- Centralized monitoring and cost tracking

**Enterprise IT**
- Separate dev/test/prod environments across tenants
- Department-specific Azure tenants
- Subsidiary or acquired company tenants

**Security Testing**
- Generate benign telemetry in isolated test tenants
- Simulate multi-tenant attack scenarios
- Compliance testing across organizational boundaries

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Infrastructure Tenant (Orchestrator)            │
│                                                         │
│  ┌──────────────────────────────────────────────┐     │
│  │      Meta-Orchestrator (Durable Function)    │     │
│  │  - Manages multiple tenant orchestrators     │     │
│  │  - Aggregates status and metrics             │     │
│  │  - Handles tenant isolation                  │     │
│  └────────┬─────────────────┬─────────────┬─────┘     │
│           │                 │             │           │
│  ┌────────▼─────┐  ┌────────▼─────┐  ┌───▼────┐     │
│  │Tenant Orch A │  │Tenant Orch B │  │Orch N  │     │
│  └────────┬─────┘  └────────┬─────┘  └───┬────┘     │
│           │                 │             │           │
│  ┌────────▼──────────────────────────────────────┐   │
│  │  Shared Infrastructure                        │   │
│  │  - Azure Key Vault (credentials)              │   │
│  │  - Storage Account (configs, logs)            │   │
│  │  - Application Insights (telemetry)           │   │
│  └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
          │                 │                  │
          │                 │                  │
     ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
     │ Target  │       │ Target  │       │ Target  │
     │Tenant A │       │Tenant B │       │Tenant N │
     │         │       │         │       │         │
     │Resources│       │Resources│       │Resources│
     └─────────┘       └─────────┘       └─────────┘
```

**Key Components:**

1. **Meta-Orchestrator**: Master orchestrator that coordinates all tenant orchestrators
2. **Tenant Orchestrators**: Per-tenant orchestrator instances managing scenario execution
3. **Infrastructure Tenant**: Hosts orchestration services and shared resources
4. **Target Tenants**: Where scenario resources are deployed

### Key Features

- **Tenant Isolation**: Complete resource and data separation per tenant
- **Concurrent Execution**: Run scenarios in multiple tenants simultaneously
- **Centralized Credentials**: Secure credential management via Key Vault
- **Aggregate Monitoring**: Unified view of all tenant operations
- **Independent Configuration**: Each tenant has its own scenarios, schedules, and settings
- **Automatic Failover**: Tenant failures don't affect other tenants

---

## Prerequisites

Before setting up cross-tenant orchestration, ensure you have:

### Infrastructure Tenant

- **Azure Subscription** with these services:
  - Azure Functions (Premium or App Service Plan)
  - Azure Key Vault
  - Azure Storage Account
  - Application Insights
- **Permissions**: Owner or Contributor + User Access Administrator
- **Azure CLI** installed and authenticated

### Target Tenants

For each target tenant:

- **Azure Subscription** to deploy resources
- **Global Administrator** or Application Administrator role (to create service principals)
- **Permissions**: Ability to grant Contributor role to service principals

### Local Environment

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install HayMaker CLI
pip install haymaker-cli

# Verify installation
haymaker --version
az --version
```

---

## Setup Guide

### Step 1: Deploy Infrastructure Tenant

Deploy the orchestrator infrastructure in your management tenant.

```bash
# Login to infrastructure tenant
az login --tenant <infrastructure-tenant-id>

# Set subscription
az account set --subscription <infrastructure-subscription-id>

# Deploy infrastructure
cd infra/bicep
az deployment sub create \
  --location eastus \
  --template-file main.bicep \
  --parameters orchestratorName=haymaker-multi-tenant

# Capture outputs
KEYVAULT_NAME=$(az deployment sub show --name main --query properties.outputs.keyVaultName.value -o tsv)
STORAGE_NAME=$(az deployment sub show --name main --query properties.outputs.storageName.value -o tsv)
ORCH_ENDPOINT=$(az deployment sub show --name main --query properties.outputs.orchestratorEndpoint.value -o tsv)
```

**Expected Output:**
```
Deployment 'main' succeeded
Key Vault: haymaker-kv-abc123
Storage: haymakerstorageabc123
Orchestrator: https://haymaker-multi-tenant.azurewebsites.net
```

### Step 2: Create Target Tenant Service Principals

Create a service principal in each target tenant that the orchestrator will use.

```bash
# Switch to target tenant A
az login --tenant <target-tenant-a-id>

# Create service principal with Contributor role
az ad sp create-for-rbac \
  --name "HayMaker-Orchestrator-SP" \
  --role Contributor \
  --scopes "/subscriptions/<target-subscription-a-id>" \
  --sdk-auth

# Save the output - you'll need these values:
# - clientId (Application ID)
# - clientSecret (Password)
# - tenantId (Directory ID)
# - subscriptionId (Subscription ID)
```

**Example Output:**
```json
{
  "clientId": "12345678-1234-1234-1234-123456789abc",
  "clientSecret": "super-secret-password-xyz",
  "subscriptionId": "87654321-4321-4321-4321-cba987654321",
  "tenantId": "abcdef12-3456-7890-abcd-ef1234567890",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

Repeat for each target tenant (B, C, etc.).

### Step 3: Store Credentials in Key Vault

Store target tenant credentials securely in the infrastructure tenant's Key Vault.

```bash
# Switch back to infrastructure tenant
az login --tenant <infrastructure-tenant-id>

# Store credentials for Target Tenant A
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "tenant-a-client-id" \
  --value "<target-a-client-id>"

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "tenant-a-client-secret" \
  --value "<target-a-client-secret>"

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "tenant-a-tenant-id" \
  --value "<target-a-tenant-id>"

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "tenant-a-subscription-id" \
  --value "<target-a-subscription-id>"

# Repeat for each target tenant (B, C, etc.)
```

**Verify secrets:**
```bash
az keyvault secret list --vault-name $KEYVAULT_NAME --query "[].name" -o table

# Output:
# Name
# ----------------------------
# tenant-a-client-id
# tenant-a-client-secret
# tenant-a-tenant-id
# tenant-a-subscription-id
# tenant-b-client-id
# tenant-b-client-secret
# ...
```

### Step 4: Create Tenant Configuration

Create a configuration file defining your target tenants.

```bash
# Create configuration directory
mkdir -p ~/.haymaker/tenants

# Create tenant configuration
cat > ~/.haymaker/tenants/multi-tenant-config.yaml << 'EOF'
meta_orchestrator:
  name: haymaker-multi-tenant
  infrastructure_tenant_id: <infrastructure-tenant-id>
  max_concurrent_tenants: 5
  polling_interval_seconds: 30

target_tenants:
  - name: customer-a
    display_name: "Customer A Production"
    tenant_id: <target-tenant-a-id>
    subscription_id: <target-subscription-a-id>
    credentials:
      keyvault_secret_prefix: tenant-a
    enabled: true
    scenarios:
      - compute-01-linux-vm-web-server
      - databases-01-mysql-wordpress
      - security-01-key-vault-secrets
    schedule:
      cron: "0 */6 * * *"  # Every 6 hours
      timezone: "UTC"
    resource_tags:
      Environment: Production
      Customer: CustomerA
      ManagedBy: HayMaker

  - name: customer-b
    display_name: "Customer B Development"
    tenant_id: <target-tenant-b-id>
    subscription_id: <target-subscription-b-id>
    credentials:
      keyvault_secret_prefix: tenant-b
    enabled: true
    scenarios:
      - ai-ml-01-cognitive-services-vision
      - containers-01-aks-cluster
    schedule:
      cron: "0 8,20 * * *"  # 8 AM and 8 PM daily
      timezone: "America/New_York"
    resource_tags:
      Environment: Development
      Customer: CustomerB
      ManagedBy: HayMaker
EOF
```

### Step 5: Configure HayMaker CLI

Configure the CLI to use your multi-tenant orchestrator.

```bash
# Set orchestrator endpoint
haymaker config set endpoint $ORCH_ENDPOINT

# Enable multi-tenant mode
haymaker config set multi-tenant-enabled true

# Set tenant configuration path
haymaker config set tenant-config ~/.haymaker/tenants/multi-tenant-config.yaml

# Verify configuration
haymaker config list
```

**Expected Output:**
```
endpoint: https://haymaker-multi-tenant.azurewebsites.net
multi-tenant-enabled: true
tenant-config: /home/user/.haymaker/tenants/multi-tenant-config.yaml
```

### Step 6: Add Target Tenants

Use the CLI to register your target tenants with the orchestrator.

```bash
# Add Customer A tenant
haymaker orch tenant add \
  --name customer-a \
  --tenant-id <target-tenant-a-id> \
  --subscription-id <target-subscription-a-id> \
  --keyvault-prefix tenant-a \
  --display-name "Customer A Production"

# Verify tenant was added
haymaker orch tenant list
```

**Expected Output:**
```
╭─────────────┬───────────────────────────┬────────────┬──────────────────────────────────────╮
│ Name        │ Display Name              │ Status     │ Tenant ID                            │
├─────────────┼───────────────────────────┼────────────┼──────────────────────────────────────┤
│ customer-a  │ Customer A Production     │ active     │ abcdef12-3456-7890-abcd-ef1234567890 │
│ customer-b  │ Customer B Development    │ active     │ fedcba98-7654-3210-fedc-ba9876543210 │
╰─────────────┴───────────────────────────┴────────────┴──────────────────────────────────────╯
```

### Step 7: Test Connectivity

Verify the orchestrator can authenticate to each target tenant.

```bash
# Test individual tenant
haymaker orch tenant status --tenant customer-a

# Test all tenants
haymaker orch tenant status --all
```

**Expected Output:**
```
Tenant: customer-a (Customer A Production)
Status: healthy
Authentication: ✓ Success
Subscription: 87654321-4321-4321-4321-cba987654321
Last Check: 2025-12-09T10:30:00Z

Tenant: customer-b (Customer B Development)
Status: healthy
Authentication: ✓ Success
Subscription: 12345678-8765-4321-1234-567890abcdef
Last Check: 2025-12-09T10:30:05Z
```

### Step 8: Run First Cross-Tenant Orchestration

Execute scenarios across all configured tenants.

```bash
# Start orchestration for all tenants
haymaker orch start --all-tenants

# Monitor execution
haymaker orch status --all-tenants

# View logs for specific tenant
haymaker orch logs --tenant customer-a --follow
```

**Expected Output:**
```
Starting multi-tenant orchestration...
✓ customer-a: Started 3 scenarios
✓ customer-b: Started 2 scenarios

Execution ID: exec-mt-2025120910
Status: running
Total Scenarios: 5 across 2 tenants
Started: 2025-12-09T10:35:00Z
```

---

## CLI Command Reference

### Tenant Management

#### Add Tenant

```bash
haymaker orch tenant add --name TENANT_NAME [OPTIONS]
```

**Options:**
- `--name`: Unique tenant identifier (required)
- `--tenant-id`: Azure tenant ID (required)
- `--subscription-id`: Azure subscription ID (required)
- `--keyvault-prefix`: Key Vault secret prefix for credentials (required)
- `--display-name`: Human-readable name
- `--enabled/--disabled`: Enable or disable tenant (default: enabled)

**Example:**
```bash
haymaker orch tenant add \
  --name production \
  --tenant-id abc-123 \
  --subscription-id xyz-789 \
  --keyvault-prefix prod \
  --display-name "Production Environment"
```

#### List Tenants

```bash
haymaker orch tenant list [OPTIONS]
```

**Options:**
- `--status`: Filter by status (active, disabled, error)
- `--format`: Output format (table, json, yaml)

**Example:**
```bash
haymaker orch tenant list --status active --format json
```

#### Show Tenant Status

```bash
haymaker orch tenant status [OPTIONS]
```

**Options:**
- `--tenant`: Specific tenant name
- `--all`: Check all tenants
- `--format`: Output format (table, json, yaml)

**Example:**
```bash
haymaker orch tenant status --tenant customer-a
```

#### Update Tenant

```bash
haymaker orch tenant update --name TENANT_NAME [OPTIONS]
```

**Options:**
- `--name`: Tenant to update (required)
- `--display-name`: New display name
- `--enabled/--disabled`: Enable or disable
- `--keyvault-prefix`: Update credential prefix

**Example:**
```bash
haymaker orch tenant update --name customer-a --disabled
```

#### Remove Tenant

```bash
haymaker orch tenant remove --name TENANT_NAME [OPTIONS]
```

**Options:**
- `--name`: Tenant to remove (required)
- `--force`: Skip confirmation prompt
- `--cleanup-resources`: Delete tenant resources (default: false)

**Example:**
```bash
haymaker orch tenant remove --name old-tenant --force
```

### Multi-Tenant Orchestration

#### Start Orchestration

```bash
# Start all tenants
haymaker orch start --all-tenants

# Start specific tenant
haymaker orch start --tenant customer-a

# Start multiple specific tenants
haymaker orch start --tenant customer-a --tenant customer-b
```

**Options:**
- `--all-tenants`: Execute on all enabled tenants
- `--tenant`: Execute on specific tenant(s)
- `--duration-hours`: Override default duration (default: 8)
- `--scenarios`: Override configured scenarios

**Example:**
```bash
haymaker orch start \
  --all-tenants \
  --duration-hours 4 \
  --scenarios compute-01 databases-01
```

#### Check Status

```bash
# Status for all tenants
haymaker orch status --all-tenants

# Status for specific tenant
haymaker orch status --tenant customer-a

# Detailed status
haymaker orch status --all-tenants --verbose
```

**Example Output:**
```
╭─────────────┬──────────┬────────────┬─────────────┬────────────╮
│ Tenant      │ Status   │ Scenarios  │ Running     │ Completed  │
├─────────────┼──────────┼────────────┼─────────────┼────────────┤
│ customer-a  │ running  │ 3          │ 2           │ 1          │
│ customer-b  │ running  │ 2          │ 1           │ 1          │
╰─────────────┴──────────┴────────────┴─────────────┴────────────╯
```

#### View Logs

```bash
# Logs for specific tenant
haymaker orch logs --tenant customer-a

# Follow logs
haymaker orch logs --tenant customer-a --follow

# Filter logs by scenario
haymaker orch logs --tenant customer-a --scenario compute-01
```

---

## Configuration Reference

See [Multi-Tenant Configuration Reference](../configuration/multi-tenant-config.md) for complete configuration schema and examples.

---

## Troubleshooting

### Authentication Failures

**Problem:** `Authentication failed for tenant customer-a`

**Solutions:**

1. **Verify service principal credentials:**
```bash
# Check if secrets exist
az keyvault secret list --vault-name $KEYVAULT_NAME | grep tenant-a

# Test authentication manually
az login --service-principal \
  --username $(az keyvault secret show --vault-name $KEYVAULT_NAME --name tenant-a-client-id --query value -o tsv) \
  --password $(az keyvault secret show --vault-name $KEYVAULT_NAME --name tenant-a-client-secret --query value -o tsv) \
  --tenant $(az keyvault secret show --vault-name $KEYVAULT_NAME --name tenant-a-tenant-id --query value -o tsv)
```

2. **Verify service principal has Contributor role:**
```bash
az role assignment list \
  --assignee <client-id> \
  --scope /subscriptions/<subscription-id>
```

3. **Check if service principal is expired:**
```bash
az ad sp show --id <client-id> --query passwordCredentials
```

### Tenant Isolation Issues

**Problem:** Resources from one tenant appearing in another

**Cause:** Incorrect tenant ID in configuration

**Solution:**
```bash
# Verify tenant configuration
haymaker orch tenant status --tenant customer-a --verbose

# Check resource tags
az resource list --tag ManagedBy=HayMaker --query "[].{name:name, tenant:tags.Customer}" -o table
```

### Concurrent Execution Limits

**Problem:** `Max concurrent tenants reached`

**Solution:** Adjust `max_concurrent_tenants` in configuration:

```bash
# Edit config
nano ~/.haymaker/tenants/multi-tenant-config.yaml

# Update:
meta_orchestrator:
  max_concurrent_tenants: 10  # Increase from 5
```

### Resource Quota Exceeded

**Problem:** `Quota exceeded in tenant customer-a`

**Solutions:**

1. **Check current quota usage:**
```bash
az vm list-usage --location eastus --output table
az network vnet list-usage --location eastus --output table
```

2. **Request quota increase:**
```bash
az support tickets create \
  --ticket-name "Increase VM Quota" \
  --title "Request VM Quota Increase" \
  --description "Need higher quota for HayMaker scenarios"
```

3. **Reduce concurrent scenarios per tenant**

### Storage Conflicts

**Problem:** `Storage account name conflict`

**Cause:** Multiple tenants trying to create storage with same name

**Solution:** Ensure unique resource naming per tenant:

```yaml
resource_naming:
  prefix: "customer-a-haymaker"  # Different prefix per tenant
```

---

## Migration Guide

### Single-Tenant to Multi-Tenant

Migrate existing single-tenant deployment to multi-tenant orchestration.

#### Step 1: Backup Current Configuration

```bash
# Export current configuration
haymaker config list > backup-config.txt

# Export execution history
haymaker metrics --period 90d --format json > backup-metrics.json
```

#### Step 2: Deploy Multi-Tenant Infrastructure

Follow [Setup Guide](#setup-guide) to deploy new infrastructure.

#### Step 3: Migrate Existing Tenant

```bash
# Add current tenant as first target tenant
haymaker orch tenant add \
  --name current-tenant \
  --tenant-id <current-tenant-id> \
  --subscription-id <current-subscription-id> \
  --keyvault-prefix current \
  --display-name "Existing Tenant"

# Test execution
haymaker orch start --tenant current-tenant
```

#### Step 4: Add Additional Tenants

Add new target tenants following [Step 2: Create Target Tenant Service Principals](#step-2-create-target-tenant-service-principals).

#### Step 5: Decommission Old Infrastructure

After verifying multi-tenant orchestration works:

```bash
# Delete old single-tenant resources
az group delete --name haymaker-old-rg --yes
```

### Legacy Credential Migration

Migrate from environment variables to Key Vault.

```bash
# Script to migrate credentials
for tenant in customer-a customer-b customer-c; do
  # Read from environment
  CLIENT_ID=$(eval echo \$${tenant^^}_CLIENT_ID)
  CLIENT_SECRET=$(eval echo \$${tenant^^}_CLIENT_SECRET)

  # Store in Key Vault
  az keyvault secret set --vault-name $KEYVAULT_NAME --name "${tenant}-client-id" --value "$CLIENT_ID"
  az keyvault secret set --vault-name $KEYVAULT_NAME --name "${tenant}-client-secret" --value "$CLIENT_SECRET"
done
```

---

## Best Practices

### Security

- **Use managed identities** for orchestrator authentication to Key Vault
- **Rotate service principal credentials** every 90 days
- **Implement least privilege**: Grant only required RBAC roles
- **Enable Key Vault audit logging**
- **Use separate Key Vaults** for production vs non-production

### Resource Management

- **Tag all resources** with tenant identifier
- **Implement resource naming conventions** to prevent conflicts
- **Set up Azure Policies** to enforce tagging and naming
- **Monitor quota usage** per tenant
- **Configure budget alerts** per tenant

### Monitoring

- **Enable Application Insights** per tenant
- **Create tenant-specific dashboards**
- **Set up alerts** for authentication failures
- **Track cross-tenant metrics** in meta-orchestrator
- **Implement distributed tracing** for end-to-end visibility

### Operations

- **Schedule maintenance windows** per tenant
- **Test new scenarios** in dev tenant first
- **Implement gradual rollout** across tenants
- **Maintain tenant-specific runbooks**
- **Document tenant-specific configurations**

---

## Related Documentation

- [Multi-Tenant CLI Commands Reference](../cli/multi-tenant-commands.md) - Complete CLI reference
- [Multi-Tenant Configuration Reference](../configuration/multi-tenant-config.md) - Configuration schema
- [Cross-Tenant Security Guide](../security/cross-tenant-security.md) - Security best practices
- [First Multi-Tenant Setup Tutorial](../tutorials/first-multi-tenant-setup.md) - Step-by-step tutorial

---

## Support

For issues with cross-tenant orchestration:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review [GitHub Issue #147](https://github.com/rysweet/AzureHayMaker/issues/147)
3. Open a new issue with `multi-tenant` label
4. Include tenant configuration (with secrets redacted)
