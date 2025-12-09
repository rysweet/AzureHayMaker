---
layout: default
title: Multi-Tenant CLI Commands
parent: CLI Guide
nav_order: 2
description: "Complete CLI command reference for multi-tenant orchestration"
permalink: /cli/multi-tenant/
---

# Multi-Tenant CLI Commands
{: .no_toc }

Complete reference for haymaker CLI commands managing cross-tenant orchestration.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The `haymaker orch tenant` command group manages target tenants in cross-tenant orchestration. All commands require the orchestrator to be configured for multi-tenant mode.

### Prerequisites

```bash
# Enable multi-tenant mode
haymaker config set multi-tenant-enabled true

# Set orchestrator endpoint
haymaker config set endpoint https://haymaker-multi-tenant.azurewebsites.net

# Verify configuration
haymaker config get multi-tenant-enabled
# Output: true
```

---

## Tenant Management Commands

### haymaker orch tenant add

Add a new target tenant to the orchestrator.

#### Syntax

```bash
haymaker orch tenant add --name TENANT_NAME [OPTIONS]
```

#### Required Options

- `--name TEXT`: Unique tenant identifier (alphanumeric, hyphens, underscores)
- `--tenant-id UUID`: Azure tenant ID (Azure Active Directory ID)
- `--subscription-id UUID`: Azure subscription ID for resource deployment
- `--keyvault-prefix TEXT`: Key Vault secret prefix for tenant credentials

#### Optional Options

- `--display-name TEXT`: Human-readable tenant name (default: same as name)
- `--enabled/--disabled`: Enable tenant immediately (default: enabled)
- `--region TEXT`: Primary Azure region (default: eastus)
- `--tags KEY=VALUE`: Resource tags (can specify multiple times)
- `--format TEXT`: Output format (table, json, yaml) (default: table)

#### Examples

**Basic tenant addition:**
```bash
haymaker orch tenant add \
  --name customer-a \
  --tenant-id 12345678-1234-1234-1234-123456789abc \
  --subscription-id 87654321-4321-4321-4321-cba987654321 \
  --keyvault-prefix tenant-a
```

**Output:**
```
✓ Tenant 'customer-a' added successfully
Status: active
Tenant ID: 12345678-1234-1234-1234-123456789abc
Subscription ID: 87654321-4321-4321-4321-cba987654321
Authentication: Pending validation
```

**With display name and tags:**
```bash
haymaker orch tenant add \
  --name prod-east \
  --display-name "Production East US" \
  --tenant-id abc-123 \
  --subscription-id xyz-789 \
  --keyvault-prefix prod-east \
  --region eastus \
  --tags Environment=Production \
  --tags Region=EastUS \
  --tags CostCenter=Engineering
```

**Output:**
```
✓ Tenant 'prod-east' added successfully
Display Name: Production East US
Status: active
Region: eastus
Tags: Environment=Production, Region=EastUS, CostCenter=Engineering
```

**Add disabled tenant (enable later):**
```bash
haymaker orch tenant add \
  --name dev-tenant \
  --tenant-id dev-123 \
  --subscription-id dev-789 \
  --keyvault-prefix dev \
  --disabled
```

**JSON output for automation:**
```bash
haymaker orch tenant add \
  --name automation-tenant \
  --tenant-id auto-123 \
  --subscription-id auto-789 \
  --keyvault-prefix auto \
  --format json
```

**Output:**
```json
{
  "name": "automation-tenant",
  "tenant_id": "auto-123",
  "subscription_id": "auto-789",
  "status": "active",
  "created_at": "2025-12-09T10:30:00Z",
  "keyvault_prefix": "auto"
}
```

#### Error Handling

**Duplicate tenant name:**
```bash
haymaker orch tenant add --name customer-a --tenant-id xyz --subscription-id abc --keyvault-prefix tenant-a
# Error: Tenant 'customer-a' already exists. Use 'haymaker orch tenant update' to modify.
```

**Missing Key Vault secrets:**
```bash
haymaker orch tenant add --name new-tenant --tenant-id xyz --subscription-id abc --keyvault-prefix missing
# Warning: Key Vault secrets not found for prefix 'missing'
# Tenant added but authentication will fail until secrets are created.
# Create secrets: tenant-missing-client-id, tenant-missing-client-secret
```

---

### haymaker orch tenant list

List all configured target tenants.

#### Syntax

```bash
haymaker orch tenant list [OPTIONS]
```

#### Options

- `--status TEXT`: Filter by status (active, disabled, error, all) (default: all)
- `--region TEXT`: Filter by region
- `--tag KEY=VALUE`: Filter by tag (can specify multiple)
- `--limit INT`: Maximum number of results (default: 100)
- `--sort TEXT`: Sort by field (name, created, status) (default: name)
- `--format TEXT`: Output format (table, json, yaml) (default: table)

#### Examples

**List all tenants:**
```bash
haymaker orch tenant list
```

**Output:**
```
╭──────────────┬──────────────────────────┬────────────┬──────────────────────────────────────╮
│ Name         │ Display Name             │ Status     │ Tenant ID                            │
├──────────────┼──────────────────────────┼────────────┼──────────────────────────────────────┤
│ customer-a   │ Customer A Production    │ active     │ 12345678-1234-1234-1234-123456789abc │
│ customer-b   │ Customer B Development   │ active     │ abcdef12-3456-7890-abcd-ef1234567890 │
│ dev-tenant   │ Development              │ disabled   │ fedcba98-7654-3210-fedc-ba9876543210 │
│ prod-east    │ Production East US       │ active     │ 11111111-2222-3333-4444-555555555555 │
╰──────────────┴──────────────────────────┴────────────┴──────────────────────────────────────╯

Total: 4 tenants (3 active, 1 disabled)
```

**List only active tenants:**
```bash
haymaker orch tenant list --status active
```

**Filter by region:**
```bash
haymaker orch tenant list --region eastus
```

**Filter by tag:**
```bash
haymaker orch tenant list --tag Environment=Production
```

**Multiple filters:**
```bash
haymaker orch tenant list \
  --status active \
  --region eastus \
  --tag Environment=Production
```

**JSON output with all details:**
```bash
haymaker orch tenant list --format json
```

**Output:**
```json
{
  "tenants": [
    {
      "name": "customer-a",
      "display_name": "Customer A Production",
      "status": "active",
      "tenant_id": "12345678-1234-1234-1234-123456789abc",
      "subscription_id": "87654321-4321-4321-4321-cba987654321",
      "region": "eastus",
      "keyvault_prefix": "tenant-a",
      "created_at": "2025-12-01T08:00:00Z",
      "last_execution": "2025-12-09T06:00:00Z",
      "scenarios_count": 5,
      "tags": {
        "Environment": "Production",
        "Customer": "CustomerA"
      }
    }
  ],
  "total": 1,
  "active": 1,
  "disabled": 0,
  "error": 0
}
```

**Sort by creation date:**
```bash
haymaker orch tenant list --sort created
```

**Limit results:**
```bash
haymaker orch tenant list --limit 10
```

---

### haymaker orch tenant status

Show detailed status for one or all tenants.

#### Syntax

```bash
haymaker orch tenant status [OPTIONS]
```

#### Options

- `--tenant TEXT`: Show status for specific tenant
- `--all`: Show status for all tenants (default if no tenant specified)
- `--check-auth`: Test authentication credentials
- `--check-quota`: Check resource quota usage
- `--verbose`: Show detailed information
- `--format TEXT`: Output format (table, json, yaml) (default: table)

#### Examples

**Status for specific tenant:**
```bash
haymaker orch tenant status --tenant customer-a
```

**Output:**
```
╭────────────────────────────────────────────────────────────────╮
│ Tenant: customer-a (Customer A Production)                     │
├────────────────────────────────────────────────────────────────┤
│ Status:          ✓ Healthy                                     │
│ Tenant ID:       12345678-1234-1234-1234-123456789abc         │
│ Subscription:    87654321-4321-4321-4321-cba987654321         │
│ Region:          eastus                                        │
│ Authentication:  ✓ Valid                                       │
│ Last Execution:  2025-12-09 06:00:00 (4 hours ago)            │
│ Active Scenarios: 3                                            │
│ Running Agents:  2                                             │
╰────────────────────────────────────────────────────────────────╯
```

**Status for all tenants:**
```bash
haymaker orch tenant status --all
```

**Output:**
```
╭──────────────┬───────────┬──────────────┬─────────────┬──────────────╮
│ Tenant       │ Status    │ Auth         │ Scenarios   │ Last Run     │
├──────────────┼───────────┼──────────────┼─────────────┼──────────────┤
│ customer-a   │ ✓ Healthy │ ✓ Valid      │ 3           │ 4h ago       │
│ customer-b   │ ✓ Healthy │ ✓ Valid      │ 2           │ 6h ago       │
│ dev-tenant   │ ⊘ Disabled│ - Not tested │ 0           │ Never        │
│ prod-east    │ ⚠ Warning │ ✓ Valid      │ 5           │ 12h ago      │
╰──────────────┴───────────┴──────────────┴─────────────┴──────────────╯
```

**Check authentication:**
```bash
haymaker orch tenant status --tenant customer-a --check-auth
```

**Output:**
```
Tenant: customer-a
Authentication Test: Running...

✓ Retrieved credentials from Key Vault
✓ Authenticated to Azure AD
✓ Verified subscription access
✓ Confirmed Contributor role
✓ Tested resource group creation (dry-run)

Authentication: Successful
Last Tested: 2025-12-09T10:45:00Z
```

**Check quota usage:**
```bash
haymaker orch tenant status --tenant customer-a --check-quota
```

**Output:**
```
Tenant: customer-a
Resource Quotas (eastus):

Virtual Machines:    15 / 100 (15%)
vCPUs:              60 / 350 (17%)
Storage Accounts:    5 / 250 (2%)
Virtual Networks:    3 / 50 (6%)
Public IPs:         8 / 100 (8%)

⚠ Warnings: None
✓ Sufficient quota for standard workload
```

**Verbose output:**
```bash
haymaker orch tenant status --tenant customer-a --verbose
```

**Output:**
```
Tenant: customer-a (Customer A Production)
═══════════════════════════════════════════

Configuration:
  Tenant ID:           12345678-1234-1234-1234-123456789abc
  Subscription ID:     87654321-4321-4321-4321-cba987654321
  Region:              eastus
  Status:              active
  Created:             2025-12-01T08:00:00Z
  Key Vault Prefix:    tenant-a

Authentication:
  Service Principal:   ✓ Valid
  Credentials Source:  Azure Key Vault (haymaker-kv-abc123)
  Last Validated:      2025-12-09T10:30:00Z
  Token Expiry:        2025-12-09T12:30:00Z

Scenarios:
  Configured:          5
  Active:              3
  Completed (24h):     12
  Failed (24h):        0
  Success Rate:        100%

Resources:
  Active Resources:    18
  Resource Groups:     3
  Total Cost (MTD):    $45.67

Execution History:
  Last Execution:      2025-12-09T06:00:00Z (4h ago)
  Next Scheduled:      2025-12-09T12:00:00Z (in 2h)
  Executions (7d):     28
  Avg Duration:        8.2 hours

Tags:
  Environment:         Production
  Customer:            CustomerA
  ManagedBy:           HayMaker
```

**JSON output:**
```bash
haymaker orch tenant status --tenant customer-a --format json
```

**Output:**
```json
{
  "name": "customer-a",
  "display_name": "Customer A Production",
  "status": "healthy",
  "tenant_id": "12345678-1234-1234-1234-123456789abc",
  "subscription_id": "87654321-4321-4321-4321-cba987654321",
  "authentication": {
    "valid": true,
    "last_validated": "2025-12-09T10:30:00Z"
  },
  "scenarios": {
    "configured": 5,
    "active": 3,
    "completed_24h": 12,
    "failed_24h": 0
  },
  "last_execution": "2025-12-09T06:00:00Z",
  "next_scheduled": "2025-12-09T12:00:00Z"
}
```

---

### haymaker orch tenant update

Update tenant configuration.

#### Syntax

```bash
haymaker orch tenant update --name TENANT_NAME [OPTIONS]
```

#### Required Options

- `--name TEXT`: Tenant to update

#### Optional Options

- `--display-name TEXT`: Update display name
- `--enabled/--disabled`: Enable or disable tenant
- `--region TEXT`: Change primary region
- `--keyvault-prefix TEXT`: Update Key Vault secret prefix
- `--add-tag KEY=VALUE`: Add or update tag
- `--remove-tag KEY`: Remove tag
- `--format TEXT`: Output format (table, json, yaml)

#### Examples

**Enable disabled tenant:**
```bash
haymaker orch tenant update --name dev-tenant --enabled
```

**Output:**
```
✓ Tenant 'dev-tenant' updated successfully
Status changed: disabled → active
```

**Disable tenant:**
```bash
haymaker orch tenant update --name customer-b --disabled
```

**Output:**
```
✓ Tenant 'customer-b' updated successfully
Status changed: active → disabled
Running executions will complete, new executions blocked.
```

**Update display name:**
```bash
haymaker orch tenant update \
  --name customer-a \
  --display-name "Customer A Production v2"
```

**Update tags:**
```bash
haymaker orch tenant update \
  --name customer-a \
  --add-tag CostCenter=CS-100 \
  --add-tag Owner=john.doe@example.com \
  --remove-tag OldTag
```

**Output:**
```
✓ Tenant 'customer-a' updated successfully
Tags updated:
  Added: CostCenter=CS-100, Owner=john.doe@example.com
  Removed: OldTag
```

**Change region:**
```bash
haymaker orch tenant update --name prod-west --region westus2
```

**Update Key Vault prefix (credential rotation):**
```bash
haymaker orch tenant update \
  --name customer-a \
  --keyvault-prefix tenant-a-v2
```

**Output:**
```
✓ Tenant 'customer-a' updated successfully
Key Vault prefix changed: tenant-a → tenant-a-v2

⚠ Important: Ensure new secrets exist in Key Vault:
  - tenant-a-v2-client-id
  - tenant-a-v2-client-secret
  - tenant-a-v2-tenant-id
  - tenant-a-v2-subscription-id
```

---

### haymaker orch tenant remove

Remove tenant from orchestrator.

#### Syntax

```bash
haymaker orch tenant remove --name TENANT_NAME [OPTIONS]
```

#### Required Options

- `--name TEXT`: Tenant to remove

#### Optional Options

- `--force`: Skip confirmation prompt
- `--cleanup-resources`: Delete all tenant resources (default: false)
- `--keep-data`: Retain execution history and logs (default: true)
- `--format TEXT`: Output format

#### Examples

**Remove tenant (with confirmation):**
```bash
haymaker orch tenant remove --name old-tenant
```

**Output:**
```
⚠ Warning: You are about to remove tenant 'old-tenant'

Tenant Details:
  Display Name: Old Customer Tenant
  Status: disabled
  Active Resources: 0
  Execution History: 245 executions

This action will:
  ✓ Remove tenant from orchestrator configuration
  ✓ Preserve execution history and logs
  ✗ NOT delete Azure resources

Continue? [y/N]: y

✓ Tenant 'old-tenant' removed successfully
Execution history preserved in storage
```

**Force remove without confirmation:**
```bash
haymaker orch tenant remove --name old-tenant --force
```

**Remove and cleanup resources:**
```bash
haymaker orch tenant remove --name old-tenant --cleanup-resources
```

**Output:**
```
⚠ Warning: You are about to remove tenant 'old-tenant' and DELETE ALL RESOURCES

This action will:
  ✓ Remove tenant from orchestrator
  ✓ Delete all Azure resources in tenant
  ✗ Delete execution history and logs
  ⚠ This action CANNOT be undone

Type 'delete-old-tenant' to confirm: delete-old-tenant

Removing tenant and cleaning up resources...
✓ Deleted 3 resource groups
✓ Deleted 18 resources
✓ Removed tenant configuration
✓ Cleaned up execution history

Tenant 'old-tenant' removed successfully
```

**Remove but keep execution data:**
```bash
haymaker orch tenant remove --name old-tenant --keep-data
```

---

## Multi-Tenant Orchestration Commands

### haymaker orch start

Start scenario execution across one or more tenants.

#### Syntax

```bash
haymaker orch start [OPTIONS]
```

#### Options

- `--all-tenants`: Execute on all enabled tenants
- `--tenant TEXT`: Execute on specific tenant(s) (can specify multiple)
- `--duration-hours INT`: Scenario run duration (default: 8)
- `--scenarios TEXT`: Override configured scenarios (can specify multiple)
- `--wait`: Wait for execution to complete
- `--poll-interval INT`: Polling interval in seconds (default: 30)
- `--format TEXT`: Output format

#### Examples

**Start all tenants:**
```bash
haymaker orch start --all-tenants
```

**Output:**
```
Starting multi-tenant orchestration...

╭──────────────┬──────────┬────────────┬─────────────────────────╮
│ Tenant       │ Status   │ Scenarios  │ Execution ID            │
├──────────────┼──────────┼────────────┼─────────────────────────┤
│ customer-a   │ ✓ Started│ 5          │ exec-a-20251209-103000  │
│ customer-b   │ ✓ Started│ 3          │ exec-b-20251209-103001  │
│ prod-east    │ ✓ Started│ 8          │ exec-pe-20251209-103002 │
╰──────────────┴──────────┴────────────┴─────────────────────────╯

Meta-Execution ID: meta-exec-20251209-103000
Total Scenarios: 16 across 3 tenants
Started: 2025-12-09T10:30:00Z
```

**Start specific tenant:**
```bash
haymaker orch start --tenant customer-a
```

**Start multiple specific tenants:**
```bash
haymaker orch start --tenant customer-a --tenant customer-b
```

**Override duration:**
```bash
haymaker orch start --all-tenants --duration-hours 4
```

**Override scenarios:**
```bash
haymaker orch start \
  --tenant customer-a \
  --scenarios compute-01-linux-vm-web-server \
  --scenarios databases-01-mysql-wordpress
```

**Start and wait for completion:**
```bash
haymaker orch start --all-tenants --wait
```

**Output:**
```
Starting multi-tenant orchestration...
✓ 3 tenants started

Waiting for completion...
[10:30:00] customer-a: Deploy phase (5/5 scenarios started)
[10:30:30] customer-b: Deploy phase (3/3 scenarios started)
[10:31:00] customer-a: Running phase (5/5 scenarios operational)
[10:31:30] customer-b: Running phase (3/3 scenarios operational)
...
[18:30:00] customer-a: Cleanup phase (5/5 scenarios completed)
[18:31:00] customer-b: Cleanup phase (3/3 scenarios completed)

✓ Multi-tenant orchestration completed
Duration: 8h 1m 15s
Total Scenarios: 8
Success: 8 (100%)
Failed: 0
```

---

### haymaker orch status

Show execution status across tenants.

#### Syntax

```bash
haymaker orch status [OPTIONS]
```

#### Options

- `--all-tenants`: Show status for all tenants (default)
- `--tenant TEXT`: Show status for specific tenant(s)
- `--execution-id TEXT`: Show status for specific execution
- `--verbose`: Show detailed information
- `--format TEXT`: Output format

#### Examples

**Status for all tenants:**
```bash
haymaker orch status --all-tenants
```

**Output:**
```
Multi-Tenant Orchestration Status
Meta-Execution ID: meta-exec-20251209-103000
Started: 2025-12-09T10:30:00Z (2h ago)
Status: running

╭──────────────┬──────────┬────────────┬─────────┬───────────┬────────╮
│ Tenant       │ Status   │ Scenarios  │ Running │ Completed │ Failed │
├──────────────┼──────────┼────────────┼─────────┼───────────┼────────┤
│ customer-a   │ running  │ 5          │ 3       │ 2         │ 0      │
│ customer-b   │ running  │ 3          │ 2       │ 1         │ 0      │
│ prod-east    │ running  │ 8          │ 5       │ 3         │ 0      │
╰──────────────┴──────────┴────────────┴─────────┴───────────┴────────╯

Overall Progress: 6/16 scenarios completed (38%)
Estimated Completion: 2025-12-09T18:35:00Z (in 6h)
```

**Status for specific tenant:**
```bash
haymaker orch status --tenant customer-a
```

**Verbose status:**
```bash
haymaker orch status --tenant customer-a --verbose
```

**Output:**
```
Tenant: customer-a
Execution ID: exec-a-20251209-103000
Status: running
Started: 2025-12-09T10:30:00Z (2h 15m ago)

Scenarios:
  ✓ compute-01-linux-vm-web-server   Completed  Duration: 8h 2m
  ✓ databases-01-mysql-wordpress     Completed  Duration: 8h 5m
  ⟳ security-01-key-vault-secrets    Running    Elapsed: 2h 10m
  ⟳ ai-ml-01-cognitive-services      Running    Elapsed: 2h 12m
  ⏳ containers-01-aks-cluster        Pending    -

Resources Created: 23
Resource Groups: 3
Estimated Cost (current): $12.45
```

**Status for specific execution:**
```bash
haymaker orch status --execution-id meta-exec-20251209-103000
```

---

### haymaker orch logs

View logs from tenant executions.

#### Syntax

```bash
haymaker orch logs [OPTIONS]
```

#### Options

- `--tenant TEXT`: Tenant name (required unless --all)
- `--all`: Show logs from all tenants
- `--execution-id TEXT`: Filter by execution ID
- `--scenario TEXT`: Filter by scenario name
- `--level TEXT`: Log level (debug, info, warning, error)
- `--tail INT`: Show last N lines (default: 100)
- `--follow`: Stream logs in real-time
- `--since TEXT`: Show logs since time (e.g., "1h", "30m")
- `--format TEXT`: Output format

#### Examples

**View logs for tenant:**
```bash
haymaker orch logs --tenant customer-a
```

**Output:**
```
[2025-12-09 10:30:00] INFO  Starting orchestration for tenant customer-a
[2025-12-09 10:30:05] INFO  Retrieved credentials from Key Vault
[2025-12-09 10:30:10] INFO  Authenticated to Azure (tenant: 12345678...)
[2025-12-09 10:30:15] INFO  Starting scenario: compute-01-linux-vm-web-server
[2025-12-09 10:30:20] INFO  Creating resource group: rg-compute-01-abc123
[2025-12-09 10:30:25] INFO  Deploying virtual machine: vm-web-server-001
...
```

**Follow logs in real-time:**
```bash
haymaker orch logs --tenant customer-a --follow
```

**Filter by scenario:**
```bash
haymaker orch logs --tenant customer-a --scenario compute-01
```

**Show last 50 lines:**
```bash
haymaker orch logs --tenant customer-a --tail 50
```

**Show logs since 1 hour ago:**
```bash
haymaker orch logs --tenant customer-a --since 1h
```

**Filter by log level:**
```bash
haymaker orch logs --tenant customer-a --level error
```

**Output:**
```
[2025-12-09 12:45:32] ERROR Scenario failed: databases-01-mysql-wordpress
[2025-12-09 12:45:32] ERROR MySQL deployment timeout after 30 minutes
[2025-12-09 12:45:33] ERROR Stack trace: ...
```

**View logs from all tenants:**
```bash
haymaker orch logs --all
```

**JSON output for parsing:**
```bash
haymaker orch logs --tenant customer-a --format json | jq '.logs[] | select(.level == "error")'
```

---

## Configuration Commands

### haymaker config set

Set configuration values for multi-tenant mode.

#### Examples

**Enable multi-tenant mode:**
```bash
haymaker config set multi-tenant-enabled true
```

**Set tenant configuration file:**
```bash
haymaker config set tenant-config ~/.haymaker/tenants/multi-tenant-config.yaml
```

**Set maximum concurrent tenants:**
```bash
haymaker config set max-concurrent-tenants 10
```

---

## Output Formats

All commands support multiple output formats.

### Table Format (Default)

Human-readable table with colors and symbols.

```bash
haymaker orch tenant list
```

### JSON Format

Machine-readable JSON for automation.

```bash
haymaker orch tenant list --format json | jq '.tenants[] | select(.status == "active")'
```

### YAML Format

Human-readable structured output.

```bash
haymaker orch tenant status --tenant customer-a --format yaml
```

**Output:**
```yaml
name: customer-a
display_name: Customer A Production
status: healthy
tenant_id: 12345678-1234-1234-1234-123456789abc
authentication:
  valid: true
  last_validated: 2025-12-09T10:30:00Z
scenarios:
  configured: 5
  active: 3
```

---

## Exit Codes

| Code | Meaning                          | Example                              |
|------|----------------------------------|--------------------------------------|
| 0    | Success                          | Command completed successfully       |
| 1    | General error                    | Invalid arguments, network error     |
| 2    | Authentication error             | Invalid credentials                  |
| 3    | Configuration error              | Missing required configuration       |
| 4    | Resource not found               | Tenant doesn't exist                 |
| 5    | Operation failed                 | Execution failed                     |
| 6    | Permission denied                | Insufficient permissions             |

**Example usage in scripts:**
```bash
haymaker orch tenant status --tenant customer-a
if [ $? -eq 0 ]; then
  echo "Tenant is healthy"
else
  echo "Tenant check failed"
  exit 1
fi
```

---

## Environment Variables

Override configuration with environment variables:

```bash
# Orchestrator endpoint
export HAYMAKER_ENDPOINT=https://haymaker.azurewebsites.net

# Multi-tenant mode
export HAYMAKER_MULTI_TENANT=true

# Tenant configuration path
export HAYMAKER_TENANT_CONFIG=~/.haymaker/tenants/config.yaml

# Output format
export HAYMAKER_OUTPUT_FORMAT=json

# Use in commands
haymaker orch tenant list  # Uses environment variables
```

---

## Related Documentation

- [Cross-Tenant Orchestration Guide](../guides/cross-tenant-orchestration.md) - Complete setup guide
- [Multi-Tenant Configuration Reference](../configuration/multi-tenant-config.md) - Configuration schema
- [Cross-Tenant Security Guide](../security/cross-tenant-security.md) - Security best practices
- [CLI Guide](../CLI_GUIDE.md) - General CLI documentation

---

## Support

For CLI issues:

1. Check `haymaker --version` for current version
2. Review [Troubleshooting Guide](../guides/cross-tenant-orchestration.md#troubleshooting)
3. Enable debug logging: `haymaker --debug orch tenant list`
4. Open GitHub issue with full command output
