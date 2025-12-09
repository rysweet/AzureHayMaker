---
layout: default
title: Your First Multi-Tenant Setup
parent: Tutorials
nav_order: 1
description: "Step-by-step tutorial for setting up cross-tenant orchestration in 30 minutes"
permalink: /tutorials/first-multi-tenant-setup/
---

# Your First Multi-Tenant Setup
{: .no_toc }

Set up cross-tenant orchestration with two target tenants in 30 minutes.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

This tutorial walks through setting up Azure HayMaker cross-tenant orchestration from scratch. By the end, you'll have:

- ✓ Infrastructure tenant with orchestrator deployed
- ✓ Two target tenants configured and running
- ✓ Credentials securely stored in Key Vault
- ✓ First multi-tenant orchestration completed

**Time Required**: 30 minutes
**Cost**: ~$5 for initial test (delete resources after to stop charges)
**Prerequisites**: Two Azure subscriptions (can be in same or different tenants)

---

## What You'll Build

```
Infrastructure Tenant (Where orchestrator runs)
  ├── Azure Functions (Orchestrator)
  ├── Key Vault (Credentials)
  ├── Storage Account (Configs/logs)
  └── Application Insights (Monitoring)

Target Tenant A (Customer A - Development)
  └── Resources deployed by orchestrator
      ├── Linux VM
      └── MySQL Database

Target Tenant B (Customer B - Production)
  └── Resources deployed by orchestrator
      ├── Cognitive Services
      └── Container Instance
```

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Azure CLI installed (`az --version`)
- [ ] Two Azure subscriptions ready
- [ ] Owner or Contributor + User Access Administrator on both subscriptions
- [ ] Python 3.9+ installed
- [ ] Git installed
- [ ] 30 minutes of uninterrupted time

**Verify Azure CLI:**

```bash
az --version
# Should show: azure-cli 2.50.0 or higher

az login
az account list --output table
# Verify you can see both subscriptions
```

---

## Step 1: Deploy Infrastructure Tenant (5 minutes)

Deploy the orchestrator and shared services in your infrastructure tenant.

### 1.1: Login to Infrastructure Tenant

```bash
# Login and set context
az login --tenant <infrastructure-tenant-id>
az account set --subscription <infrastructure-subscription-id>

# Verify subscription
az account show --output table
```

**Expected Output:**
```
Name                            SubscriptionId                        State    IsDefault
------------------------------  ------------------------------------  -------  -----------
Infrastructure Subscription     11111111-1111-1111-1111-111111111111  Enabled  True
```

### 1.2: Clone Repository

```bash
# Clone HayMaker repository
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker

# Switch to multi-tenant branch (or main once merged)
git checkout feat/cross-tenant-orchestration
```

### 1.3: Deploy Infrastructure

```bash
# Navigate to infrastructure directory
cd infra/bicep

# Deploy infrastructure
az deployment sub create \
  --location eastus \
  --template-file main.bicep \
  --parameters \
    orchestratorName=haymaker-tutorial \
    environment=dev

# This takes ~5 minutes
```

**Expected Output:**
```
Deployment 'main' succeeded

Outputs:
  keyVaultName: haymaker-kv-abc123
  storageName: haymakerstorageabc
  orchestratorEndpoint: https://haymaker-tutorial.azurewebsites.net
  functionAppName: haymaker-tutorial
```

### 1.4: Save Output Variables

```bash
# Save for later use
export KEYVAULT_NAME=$(az deployment sub show --name main --query properties.outputs.keyVaultName.value -o tsv)
export STORAGE_NAME=$(az deployment sub show --name main --query properties.outputs.storageName.value -o tsv)
export ORCH_ENDPOINT=$(az deployment sub show --name main --query properties.outputs.orchestratorEndpoint.value -o tsv)

echo "Key Vault: $KEYVAULT_NAME"
echo "Storage: $STORAGE_NAME"
echo "Orchestrator: $ORCH_ENDPOINT"
```

---

## Step 2: Configure Target Tenant A (5 minutes)

Set up first target tenant (Customer A - Development).

### 2.1: Login to Target Tenant A

```bash
# Login to tenant A
az login --tenant <target-tenant-a-id>
az account set --subscription <target-subscription-a-id>

# Verify
az account show --query "{Name:name, TenantId:tenantId, SubscriptionId:id}" -o table
```

**Expected Output:**
```
Name                    TenantId                              SubscriptionId
----------------------  ------------------------------------  ------------------------------------
Customer A Dev          aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa  bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb
```

### 2.2: Create Service Principal

```bash
# Create service principal with Contributor role
SP_RESULT=$(az ad sp create-for-rbac \
  --name "HayMaker-Tutorial-TenantA" \
  --role Contributor \
  --scopes "/subscriptions/<target-subscription-a-id>" \
  --years 1 \
  --sdk-auth)

# Extract values
TENANT_A_CLIENT_ID=$(echo $SP_RESULT | jq -r .clientId)
TENANT_A_CLIENT_SECRET=$(echo $SP_RESULT | jq -r .clientSecret)
TENANT_A_TENANT_ID=$(echo $SP_RESULT | jq -r .tenantId)
TENANT_A_SUBSCRIPTION_ID=$(echo $SP_RESULT | jq -r .subscriptionId)

echo "✓ Service Principal created"
echo "  Client ID: $TENANT_A_CLIENT_ID"
```

⚠️ **Important**: Save these credentials securely. They won't be shown again.

### 2.3: Store Credentials in Key Vault

```bash
# Switch back to infrastructure tenant
az login --tenant <infrastructure-tenant-id>
az account set --subscription <infrastructure-subscription-id>

# Store tenant A credentials
az keyvault secret set --vault-name $KEYVAULT_NAME --name "tenant-a-client-id" --value "$TENANT_A_CLIENT_ID"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "tenant-a-client-secret" --value "$TENANT_A_CLIENT_SECRET"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "tenant-a-tenant-id" --value "$TENANT_A_TENANT_ID"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "tenant-a-subscription-id" --value "$TENANT_A_SUBSCRIPTION_ID"

# Verify secrets stored
az keyvault secret list --vault-name $KEYVAULT_NAME --query "[?contains(name, 'tenant-a')].name" -o table
```

**Expected Output:**
```
Result
--------------------
tenant-a-client-id
tenant-a-client-secret
tenant-a-subscription-id
tenant-a-tenant-id
```

---

## Step 3: Configure Target Tenant B (5 minutes)

Set up second target tenant (Customer B - Production).

### 3.1: Login to Target Tenant B

```bash
# Login to tenant B
az login --tenant <target-tenant-b-id>
az account set --subscription <target-subscription-b-id>

# Verify
az account show --query "{Name:name, TenantId:tenantId, SubscriptionId:id}" -o table
```

### 3.2: Create Service Principal

```bash
# Create service principal
SP_RESULT=$(az ad sp create-for-rbac \
  --name "HayMaker-Tutorial-TenantB" \
  --role Contributor \
  --scopes "/subscriptions/<target-subscription-b-id>" \
  --years 1 \
  --sdk-auth)

# Extract values
TENANT_B_CLIENT_ID=$(echo $SP_RESULT | jq -r .clientId)
TENANT_B_CLIENT_SECRET=$(echo $SP_RESULT | jq -r .clientSecret)
TENANT_B_TENANT_ID=$(echo $SP_RESULT | jq -r .tenantId)
TENANT_B_SUBSCRIPTION_ID=$(echo $SP_RESULT | jq -r .subscriptionId)

echo "✓ Service Principal created"
echo "  Client ID: $TENANT_B_CLIENT_ID"
```

### 3.3: Store Credentials in Key Vault

```bash
# Switch back to infrastructure tenant
az login --tenant <infrastructure-tenant-id>
az account set --subscription <infrastructure-subscription-id>

# Store tenant B credentials
az keyvault secret set --vault-name $KEYVAULT_NAME --name "tenant-b-client-id" --value "$TENANT_B_CLIENT_ID"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "tenant-b-client-secret" --value "$TENANT_B_CLIENT_SECRET"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "tenant-b-tenant-id" --value "$TENANT_B_TENANT_ID"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "tenant-b-subscription-id" --value "$TENANT_B_SUBSCRIPTION_ID"

# Verify all secrets
az keyvault secret list --vault-name $KEYVAULT_NAME --query "[?contains(name, 'tenant-')].name" -o table
```

**Expected Output:**
```
Result
--------------------
tenant-a-client-id
tenant-a-client-secret
tenant-a-subscription-id
tenant-a-tenant-id
tenant-b-client-id
tenant-b-client-secret
tenant-b-subscription-id
tenant-b-tenant-id
```

---

## Step 4: Install HayMaker CLI (2 minutes)

Install the HayMaker CLI to manage your orchestrator.

### 4.1: Install CLI

```bash
# Install from PyPI
pip install haymaker-cli

# Verify installation
haymaker --version
```

**Expected Output:**
```
haymaker-cli version 1.0.0
```

### 4.2: Configure CLI

```bash
# Set orchestrator endpoint
haymaker config set endpoint $ORCH_ENDPOINT

# Enable multi-tenant mode
haymaker config set multi-tenant-enabled true

# Verify configuration
haymaker config list
```

**Expected Output:**
```
endpoint: https://haymaker-tutorial.azurewebsites.net
multi-tenant-enabled: true
```

### 4.3: Test Connection

```bash
# Test orchestrator health
curl $ORCH_ENDPOINT/

# Or use CLI
haymaker status
```

**Expected Output:**
```
{
  "status": "healthy",
  "service": "azure-haymaker-orchestrator",
  "timestamp": "2025-12-09T10:30:00Z"
}
```

---

## Step 5: Add Target Tenants (5 minutes)

Register both target tenants with the orchestrator.

### 5.1: Add Tenant A

```bash
# Add tenant A (development)
haymaker orch tenant add \
  --name tenant-a \
  --display-name "Customer A Development" \
  --tenant-id $TENANT_A_TENANT_ID \
  --subscription-id $TENANT_A_SUBSCRIPTION_ID \
  --keyvault-prefix tenant-a \
  --region eastus
```

**Expected Output:**
```
✓ Tenant 'tenant-a' added successfully
Status: active
Tenant ID: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
Subscription ID: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb
Authentication: Pending validation
```

### 5.2: Add Tenant B

```bash
# Add tenant B (production)
haymaker orch tenant add \
  --name tenant-b \
  --display-name "Customer B Production" \
  --tenant-id $TENANT_B_TENANT_ID \
  --subscription-id $TENANT_B_SUBSCRIPTION_ID \
  --keyvault-prefix tenant-b \
  --region eastus
```

### 5.3: Verify Tenants

```bash
# List all tenants
haymaker orch tenant list
```

**Expected Output:**
```
╭────────────┬──────────────────────────────┬────────────┬──────────────────────────────────────╮
│ Name       │ Display Name                 │ Status     │ Tenant ID                            │
├────────────┼──────────────────────────────┼────────────┼──────────────────────────────────────┤
│ tenant-a   │ Customer A Development       │ active     │ aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa │
│ tenant-b   │ Customer B Production        │ active     │ cccccccc-cccc-cccc-cccc-cccccccccccc │
╰────────────┴──────────────────────────────┴────────────┴──────────────────────────────────────╯
```

---

## Step 6: Test Authentication (3 minutes)

Verify the orchestrator can authenticate to both tenants.

### 6.1: Test Tenant A Authentication

```bash
# Test tenant A
haymaker orch tenant status --tenant tenant-a --check-auth
```

**Expected Output:**
```
Tenant: tenant-a (Customer A Development)
Authentication Test: Running...

✓ Retrieved credentials from Key Vault
✓ Authenticated to Azure AD
✓ Verified subscription access
✓ Confirmed Contributor role

Authentication: Successful
Last Tested: 2025-12-09T10:45:00Z
```

### 6.2: Test Tenant B Authentication

```bash
# Test tenant B
haymaker orch tenant status --tenant tenant-b --check-auth
```

**Expected Output:**
```
Tenant: tenant-b (Customer B Production)
Authentication Test: Running...

✓ Retrieved credentials from Key Vault
✓ Authenticated to Azure AD
✓ Verified subscription access
✓ Confirmed Contributor role

Authentication: Successful
Last Tested: 2025-12-09T10:45:05Z
```

### 6.3: Test All Tenants

```bash
# Test all tenants at once
haymaker orch tenant status --all
```

**Expected Output:**
```
╭────────────┬───────────┬──────────────┬──────────────────────────────────────╮
│ Tenant     │ Status    │ Auth         │ Last Check                           │
├────────────┼───────────┼──────────────┼──────────────────────────────────────┤
│ tenant-a   │ ✓ Healthy │ ✓ Valid      │ 2025-12-09T10:45:00Z                 │
│ tenant-b   │ ✓ Healthy │ ✓ Valid      │ 2025-12-09T10:45:05Z                 │
╰────────────┴───────────┴──────────────┴──────────────────────────────────────╯
```

🎉 If you see ✓ Valid for both tenants, authentication is working!

---

## Step 7: Run First Multi-Tenant Orchestration (5 minutes)

Execute scenarios across both tenants simultaneously.

### 7.1: Start Orchestration

```bash
# Start orchestration on both tenants with simple scenarios
haymaker orch start --all-tenants \
  --scenarios compute-01-linux-vm-web-server \
  --scenarios databases-01-mysql-wordpress \
  --duration-hours 1
```

**Expected Output:**
```
Starting multi-tenant orchestration...

╭────────────┬──────────┬────────────┬─────────────────────────╮
│ Tenant     │ Status   │ Scenarios  │ Execution ID            │
├────────────┼──────────┼────────────┼─────────────────────────┤
│ tenant-a   │ ✓ Started│ 2          │ exec-a-20251209-104500  │
│ tenant-b   │ ✓ Started│ 2          │ exec-b-20251209-104501  │
╰────────────┴──────────┴────────────┴─────────────────────────╯

Meta-Execution ID: meta-exec-20251209-104500
Total Scenarios: 4 across 2 tenants
Started: 2025-12-09T10:45:00Z
```

### 7.2: Monitor Execution

```bash
# Check status
haymaker orch status --all-tenants
```

**Expected Output (after 2 minutes):**
```
Multi-Tenant Orchestration Status
Meta-Execution ID: meta-exec-20251209-104500
Started: 2025-12-09T10:45:00Z (2m ago)
Status: running

╭────────────┬──────────┬────────────┬─────────┬───────────┬────────╮
│ Tenant     │ Status   │ Scenarios  │ Running │ Completed │ Failed │
├────────────┼──────────┼────────────┼─────────┼───────────┼────────┤
│ tenant-a   │ running  │ 2          │ 2       │ 0         │ 0      │
│ tenant-b   │ running  │ 2          │ 2       │ 0         │ 0      │
╰────────────┴──────────┴────────────┴─────────┴───────────┴────────╯

Overall Progress: 0/4 scenarios completed (0%)
Estimated Completion: 2025-12-09T11:50:00Z (in 1h 3m)
```

### 7.3: Watch Logs

```bash
# Follow logs for tenant A
haymaker orch logs --tenant tenant-a --follow
```

**Expected Output:**
```
[2025-12-09 10:45:00] INFO  Starting orchestration for tenant tenant-a
[2025-12-09 10:45:05] INFO  Retrieved credentials from Key Vault
[2025-12-09 10:45:10] INFO  Authenticated to Azure
[2025-12-09 10:45:15] INFO  Starting scenario: compute-01-linux-vm-web-server
[2025-12-09 10:45:20] INFO  Creating resource group: rg-compute-01-abc123
[2025-12-09 10:45:30] INFO  Deploying virtual machine: vm-web-server-001
[2025-12-09 10:46:45] INFO  Virtual machine deployed successfully
[2025-12-09 10:46:50] INFO  Starting scenario: databases-01-mysql-wordpress
...
```

Press Ctrl+C to stop following logs.

---

## Step 8: Verify Resources Deployed (3 minutes)

Check that resources were created in both target tenants.

### 8.1: Check Tenant A Resources

```bash
# Switch to tenant A
az login --tenant $TENANT_A_TENANT_ID
az account set --subscription $TENANT_A_SUBSCRIPTION_ID

# List resource groups created by HayMaker
az group list --tag ManagedBy=HayMaker --output table
```

**Expected Output:**
```
Name                               Location    Status
---------------------------------  ----------  ---------
rg-compute-01-abc123              eastus      Succeeded
rg-databases-01-xyz789            eastus      Succeeded
```

### 8.2: Check Tenant B Resources

```bash
# Switch to tenant B
az login --tenant $TENANT_B_TENANT_ID
az account set --subscription $TENANT_B_SUBSCRIPTION_ID

# List resource groups
az group list --tag ManagedBy=HayMaker --output table
```

**Expected Output:**
```
Name                               Location    Status
---------------------------------  ----------  ---------
rg-compute-01-def456              eastus      Succeeded
rg-databases-01-ghi789            eastus      Succeeded
```

### 8.3: View Resource Details

```bash
# View all resources in tenant A
az resource list --tag ManagedBy=HayMaker --output table
```

**Expected Output:**
```
Name                    ResourceGroup             Location    Type
----------------------  ------------------------  ----------  -------------------------------
vm-web-server-001       rg-compute-01-abc123      eastus      Microsoft.Compute/virtualMachines
mysql-server-001        rg-databases-01-xyz789    eastus      Microsoft.DBforMySQL/servers
...
```

🎉 Success! Resources are deployed in both tenants.

---

## Step 9: Monitor and Verify (2 minutes)

### 9.1: Check Final Status

Wait for orchestration to complete (or check periodically):

```bash
# Check status every 30 seconds
watch -n 30 'haymaker orch status --all-tenants'
```

**After 1 hour (when complete):**
```
Multi-Tenant Orchestration Status
Meta-Execution ID: meta-exec-20251209-104500
Started: 2025-12-09T10:45:00Z (1h 5m ago)
Status: completed

╭────────────┬───────────┬────────────┬─────────┬───────────┬────────╮
│ Tenant     │ Status    │ Scenarios  │ Running │ Completed │ Failed │
├────────────┼───────────┼────────────┼─────────┼───────────┼────────┤
│ tenant-a   │ completed │ 2          │ 0       │ 2         │ 0      │
│ tenant-b   │ completed │ 2          │ 0       │ 2         │ 0      │
╰────────────┴───────────┴────────────┴─────────┴───────────┴────────╯

Overall Progress: 4/4 scenarios completed (100%)
Success Rate: 100%
Total Duration: 1h 5m 23s
```

### 9.2: View Execution Summary

```bash
# Get detailed execution report
haymaker orch status --execution-id meta-exec-20251209-104500 --verbose
```

---

## Step 10: Cleanup (optional)

To avoid ongoing charges, clean up resources.

### 10.1: Cleanup Tenant Resources

```bash
# Cleanup resources in both tenants
haymaker cleanup --all-tenants
```

**Expected Output:**
```
⚠ Warning: This will delete ALL resources managed by HayMaker in all tenants

Tenants:
  - tenant-a: 2 resource groups, ~18 resources
  - tenant-b: 2 resource groups, ~18 resources

Continue? [y/N]: y

Cleaning up tenant-a...
✓ Deleted resource group: rg-compute-01-abc123
✓ Deleted resource group: rg-databases-01-xyz789

Cleaning up tenant-b...
✓ Deleted resource group: rg-compute-01-def456
✓ Deleted resource group: rg-databases-01-ghi789

Cleanup completed successfully
```

### 10.2: Cleanup Infrastructure (optional)

If you're done with the tutorial completely:

```bash
# Switch to infrastructure tenant
az login --tenant <infrastructure-tenant-id>
az account set --subscription <infrastructure-subscription-id>

# Delete infrastructure resource group
az group delete --name haymaker-tutorial-rg --yes --no-wait
```

⚠️ This deletes the orchestrator, Key Vault, and all configurations.

---

## Troubleshooting

### Authentication Failed

**Problem**: `haymaker orch tenant status --tenant tenant-a --check-auth` fails

**Solutions**:

1. Verify secrets exist:
```bash
az keyvault secret list --vault-name $KEYVAULT_NAME | grep tenant-a
```

2. Test credentials manually:
```bash
az login --service-principal \
  --username $(az keyvault secret show --vault-name $KEYVAULT_NAME --name tenant-a-client-id --query value -o tsv) \
  --password $(az keyvault secret show --vault-name $KEYVAULT_NAME --name tenant-a-client-secret --query value -o tsv) \
  --tenant $(az keyvault secret show --vault-name $KEYVAULT_NAME --name tenant-a-tenant-id --query value -o tsv)
```

3. Verify service principal has Contributor role:
```bash
az role assignment list --assignee <client-id> --output table
```

### Orchestrator Not Responding

**Problem**: `curl $ORCH_ENDPOINT` returns error

**Solutions**:

1. Check deployment status:
```bash
az deployment sub show --name main --query properties.provisioningState
```

2. Check function app status:
```bash
az functionapp show --name haymaker-tutorial --resource-group haymaker-tutorial-rg --query state
```

3. View function app logs:
```bash
az functionapp log tail --name haymaker-tutorial --resource-group haymaker-tutorial-rg
```

### Resources Not Deploying

**Problem**: Scenarios start but resources don't appear

**Solutions**:

1. Check scenario logs:
```bash
haymaker orch logs --tenant tenant-a --level error
```

2. Verify quota:
```bash
az vm list-usage --location eastus --output table
```

3. Check service principal permissions:
```bash
az role assignment list --assignee <client-id> --all
```

---

## Next Steps

Congratulations! You've successfully set up cross-tenant orchestration. Here's what to explore next:

### Immediate Next Steps

1. **Add more scenarios**: Configure additional scenarios per tenant
2. **Set up scheduling**: Configure cron-based scheduling
3. **Enable monitoring**: Set up cost alerts and dashboards
4. **Explore CLI**: Try other `haymaker orch` commands

### Advanced Topics

- [Cross-Tenant Orchestration Guide](../guides/cross-tenant-orchestration.md) - Complete feature guide
- [Multi-Tenant Configuration](../configuration/multi-tenant-config.md) - Advanced configuration
- [Cross-Tenant Security](../security/cross-tenant-security.md) - Security hardening
- [Multi-Tenant CLI Commands](../cli/multi-tenant-commands.md) - Full CLI reference

### Production Deployment

When ready for production:

1. Enable private endpoints for Key Vault
2. Configure VNet integration
3. Set up automated credential rotation
4. Enable distributed tracing
5. Configure cost budgets
6. Set up monitoring dashboards
7. Document incident response procedures

---

## Summary

You've completed your first multi-tenant setup! Here's what you accomplished:

✅ Deployed infrastructure tenant with orchestrator
✅ Created service principals in two target tenants
✅ Stored credentials securely in Key Vault
✅ Configured HayMaker CLI
✅ Added two target tenants
✅ Verified authentication
✅ Ran first cross-tenant orchestration
✅ Verified resources deployed in both tenants

**Total time**: 30 minutes
**Tenants configured**: 2
**Scenarios executed**: 4
**Success rate**: 100%

---

## Support

Need help?

1. Review [Troubleshooting](#troubleshooting) section above
2. Check [GitHub Issue #147](https://github.com/rysweet/AzureHayMaker/issues/147)
3. Read [Cross-Tenant Orchestration Guide](../guides/cross-tenant-orchestration.md)
4. Open GitHub issue with `multi-tenant` and `tutorial` labels
