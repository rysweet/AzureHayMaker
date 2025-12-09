---
layout: default
title: Multi-Tenant Configuration
parent: Configuration
nav_order: 3
description: "Configuration schema and examples for cross-tenant orchestration"
permalink: /configuration/multi-tenant/
---

# Multi-Tenant Configuration Reference
{: .no_toc }

Complete configuration schema for cross-tenant orchestration in Azure HayMaker.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

Multi-tenant configuration defines the meta-orchestrator behavior and target tenant settings. Configuration is stored in YAML format and loaded by the orchestrator at startup.

### Configuration Locations

1. **Default**: `~/.haymaker/tenants/multi-tenant-config.yaml`
2. **Custom**: Set via `HAYMAKER_TENANT_CONFIG` environment variable
3. **Project**: `.haymaker/tenants/config.yaml` (for project-specific configs)

### Configuration Loading Priority

1. Command-line `--config` flag (highest priority)
2. `HAYMAKER_TENANT_CONFIG` environment variable
3. Project config: `./.haymaker/tenants/config.yaml`
4. User config: `~/.haymaker/tenants/multi-tenant-config.yaml`
5. Default config: Built-in defaults (lowest priority)

---

## Configuration Schema

### Root Structure

```yaml
meta_orchestrator:
  # Meta-orchestrator settings
  ...

target_tenants:
  # List of target tenant configurations
  - name: tenant-a
    ...
  - name: tenant-b
    ...

global_defaults:
  # Default settings applied to all tenants
  ...
```

---

## Meta-Orchestrator Configuration

### MetaOrchestratorConfig

Master orchestrator settings controlling multi-tenant behavior.

```yaml
meta_orchestrator:
  # Orchestrator identification
  name: string                         # Orchestrator name (required)
  infrastructure_tenant_id: uuid       # Infrastructure tenant ID (required)

  # Concurrency settings
  max_concurrent_tenants: int          # Max tenants running simultaneously (default: 5)
  max_concurrent_scenarios_per_tenant: int  # Max scenarios per tenant (default: 10)

  # Polling and timing
  polling_interval_seconds: int        # Status check interval (default: 30)
  health_check_interval_seconds: int   # Health check interval (default: 60)
  execution_timeout_hours: int         # Max execution duration (default: 24)

  # Retry and resilience
  max_retry_attempts: int              # Max retries on failure (default: 3)
  retry_delay_seconds: int             # Delay between retries (default: 60)
  enable_circuit_breaker: bool         # Enable circuit breaker (default: true)
  circuit_breaker_threshold: int       # Failures before breaking (default: 5)

  # Storage and telemetry
  storage_account_name: string         # Storage account for configs/logs
  application_insights_key: string     # App Insights instrumentation key
  log_level: string                    # Logging level (debug, info, warning, error)

  # Feature flags
  enable_tenant_isolation: bool        # Enforce tenant isolation (default: true)
  enable_cost_tracking: bool           # Track costs per tenant (default: true)
  enable_distributed_tracing: bool     # Enable distributed tracing (default: true)
```

#### Example

```yaml
meta_orchestrator:
  name: haymaker-prod-orchestrator
  infrastructure_tenant_id: 11111111-2222-3333-4444-555555555555

  max_concurrent_tenants: 10
  max_concurrent_scenarios_per_tenant: 15

  polling_interval_seconds: 30
  health_check_interval_seconds: 60
  execution_timeout_hours: 24

  max_retry_attempts: 3
  retry_delay_seconds: 60
  enable_circuit_breaker: true
  circuit_breaker_threshold: 5

  storage_account_name: haymakerstorageprod
  application_insights_key: abcd1234-5678-90ef-ghij-klmnopqrstuv
  log_level: info

  enable_tenant_isolation: true
  enable_cost_tracking: true
  enable_distributed_tracing: true
```

---

## Target Tenant Configuration

### TargetTenantConfig

Configuration for each target tenant where scenarios are deployed.

```yaml
target_tenants:
  - # Tenant identification
    name: string                       # Unique tenant identifier (required)
    display_name: string               # Human-readable name
    description: string                # Tenant description

    # Azure settings
    tenant_id: uuid                    # Azure tenant ID (required)
    subscription_id: uuid              # Azure subscription ID (required)
    region: string                     # Primary Azure region (default: eastus)

    # Authentication
    credentials:
      keyvault_secret_prefix: string   # Key Vault secret prefix (required)
      # Secrets expected:
      #   {prefix}-client-id
      #   {prefix}-client-secret
      #   {prefix}-tenant-id
      #   {prefix}-subscription-id

    # Tenant state
    enabled: bool                      # Enable/disable tenant (default: true)

    # Scenario configuration
    scenarios:
      - string                         # List of scenario names to execute
    scenario_selection_mode: string    # Selection mode (all, random, weighted)
    max_scenarios_per_execution: int   # Limit scenarios per run

    # Scheduling
    schedule:
      cron: string                     # Cron expression for scheduling
      timezone: string                 # Timezone (default: UTC)
      enabled: bool                    # Enable scheduled execution (default: true)

    # Resource configuration
    resource_tags:                     # Tags applied to all resources
      key: value
    resource_naming:
      prefix: string                   # Resource name prefix
      suffix: string                   # Resource name suffix
      include_timestamp: bool          # Add timestamp to names (default: true)

    # Limits and quotas
    limits:
      max_resource_groups: int         # Max resource groups (default: 50)
      max_vms: int                     # Max VMs (default: 20)
      max_storage_accounts: int        # Max storage accounts (default: 10)
      max_cost_per_day_usd: float      # Max daily cost (optional)

    # Monitoring and alerting
    monitoring:
      enable_alerts: bool              # Enable alerting (default: true)
      alert_email: string              # Alert email address
      alert_webhook: string            # Alert webhook URL
      enable_cost_alerts: bool         # Enable cost alerts (default: true)
      cost_alert_threshold_usd: float  # Cost alert threshold

    # Cleanup configuration
    cleanup:
      auto_cleanup: bool               # Auto cleanup after execution (default: true)
      cleanup_delay_hours: int         # Delay before cleanup (default: 0)
      retain_failed_resources: bool    # Keep resources on failure (default: true)
      retention_days: int              # Log/data retention (default: 30)
```

#### Minimal Example

```yaml
target_tenants:
  - name: simple-tenant
    tenant_id: 12345678-1234-1234-1234-123456789abc
    subscription_id: 87654321-4321-4321-4321-cba987654321
    credentials:
      keyvault_secret_prefix: simple-tenant
    scenarios:
      - compute-01-linux-vm-web-server
      - databases-01-mysql-wordpress
```

#### Complete Example

```yaml
target_tenants:
  - name: customer-a-prod
    display_name: "Customer A Production"
    description: "Production environment for Customer A"

    tenant_id: 12345678-1234-1234-1234-123456789abc
    subscription_id: 87654321-4321-4321-4321-cba987654321
    region: eastus

    credentials:
      keyvault_secret_prefix: customer-a-prod

    enabled: true

    scenarios:
      - compute-01-linux-vm-web-server
      - databases-01-mysql-wordpress
      - security-01-key-vault-secrets
      - ai-ml-01-cognitive-services-vision
      - containers-01-aks-cluster
    scenario_selection_mode: all
    max_scenarios_per_execution: 5

    schedule:
      cron: "0 */6 * * *"  # Every 6 hours
      timezone: "America/New_York"
      enabled: true

    resource_tags:
      Environment: Production
      Customer: CustomerA
      ManagedBy: HayMaker
      CostCenter: CS-100
      Owner: john.doe@example.com

    resource_naming:
      prefix: "cust-a-prod"
      suffix: ""
      include_timestamp: true

    limits:
      max_resource_groups: 20
      max_vms: 10
      max_storage_accounts: 5
      max_cost_per_day_usd: 50.00

    monitoring:
      enable_alerts: true
      alert_email: ops-team@example.com
      alert_webhook: https://alerts.example.com/webhook
      enable_cost_alerts: true
      cost_alert_threshold_usd: 40.00

    cleanup:
      auto_cleanup: true
      cleanup_delay_hours: 0
      retain_failed_resources: true
      retention_days: 90
```

---

## Global Defaults

### GlobalDefaults

Default settings applied to all tenants (can be overridden per tenant).

```yaml
global_defaults:
  # Default region
  region: string                       # Default: eastus

  # Default scenario settings
  scenario_duration_hours: int         # Default: 8
  scenario_selection_mode: string      # Default: all

  # Default scheduling
  schedule:
    cron: string                       # Default: "0 0,6,12,18 * * *"
    timezone: string                   # Default: UTC

  # Default resource tags
  resource_tags:
    ManagedBy: HayMaker
    Orchestrator: AzureHayMaker

  # Default limits
  limits:
    max_resource_groups: int           # Default: 50
    max_vms: int                       # Default: 20
    max_storage_accounts: int          # Default: 10

  # Default monitoring
  monitoring:
    enable_alerts: bool                # Default: true
    enable_cost_alerts: bool           # Default: true

  # Default cleanup
  cleanup:
    auto_cleanup: bool                 # Default: true
    cleanup_delay_hours: int           # Default: 0
    retention_days: int                # Default: 30
```

#### Example

```yaml
global_defaults:
  region: eastus
  scenario_duration_hours: 8
  scenario_selection_mode: all

  schedule:
    cron: "0 0,6,12,18 * * *"  # 4 times daily
    timezone: UTC

  resource_tags:
    ManagedBy: HayMaker
    Orchestrator: AzureHayMaker
    Project: TelemetryGeneration

  limits:
    max_resource_groups: 50
    max_vms: 20
    max_storage_accounts: 10

  monitoring:
    enable_alerts: true
    enable_cost_alerts: true

  cleanup:
    auto_cleanup: true
    cleanup_delay_hours: 0
    retention_days: 30
```

---

## Configuration Examples

### MSP Scenario (5 Customer Tenants)

Managed Service Provider managing multiple customer tenants.

```yaml
meta_orchestrator:
  name: msp-haymaker-orchestrator
  infrastructure_tenant_id: 00000000-0000-0000-0000-000000000000
  max_concurrent_tenants: 5
  polling_interval_seconds: 30
  enable_tenant_isolation: true
  enable_cost_tracking: true

global_defaults:
  region: eastus
  scenario_duration_hours: 8
  cleanup:
    auto_cleanup: true
    retention_days: 30

target_tenants:
  - name: customer-a
    display_name: "Acme Corporation"
    tenant_id: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
    subscription_id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb
    credentials:
      keyvault_secret_prefix: cust-a
    scenarios:
      - compute-01-linux-vm-web-server
      - databases-01-mysql-wordpress
      - security-01-key-vault-secrets
    schedule:
      cron: "0 2,8,14,20 * * *"
      timezone: "America/Los_Angeles"
    resource_tags:
      Customer: AcmeCorp
      Tier: Premium
    limits:
      max_cost_per_day_usd: 75.00

  - name: customer-b
    display_name: "Beta Industries"
    tenant_id: cccccccc-cccc-cccc-cccc-cccccccccccc
    subscription_id: dddddddd-dddd-dddd-dddd-dddddddddddd
    credentials:
      keyvault_secret_prefix: cust-b
    scenarios:
      - ai-ml-01-cognitive-services-vision
      - containers-01-aks-cluster
    schedule:
      cron: "0 4,10,16,22 * * *"
      timezone: "America/New_York"
    resource_tags:
      Customer: BetaIndustries
      Tier: Standard
    limits:
      max_cost_per_day_usd: 50.00

  - name: customer-c
    display_name: "Gamma Solutions"
    tenant_id: eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee
    subscription_id: ffffffff-ffff-ffff-ffff-ffffffffffff
    credentials:
      keyvault_secret_prefix: cust-c
    scenarios:
      - networking-01-virtual-network
      - webapps-01-static-website
    schedule:
      cron: "0 0,6,12,18 * * *"
      timezone: "Europe/London"
    resource_tags:
      Customer: GammaSolutions
      Tier: Basic
    limits:
      max_cost_per_day_usd: 25.00

  - name: customer-d
    display_name: "Delta Enterprises"
    tenant_id: 11111111-1111-1111-1111-111111111111
    subscription_id: 22222222-2222-2222-2222-222222222222
    credentials:
      keyvault_secret_prefix: cust-d
    scenarios:
      - analytics-01-synapse-workspace
      - databases-02-cosmos-db
    schedule:
      cron: "0 1,7,13,19 * * *"
      timezone: "America/Chicago"
    resource_tags:
      Customer: DeltaEnterprises
      Tier: Premium
    limits:
      max_cost_per_day_usd: 100.00

  - name: customer-e
    display_name: "Epsilon Group"
    tenant_id: 33333333-3333-3333-3333-333333333333
    subscription_id: 44444444-4444-4444-4444-444444444444
    credentials:
      keyvault_secret_prefix: cust-e
    scenarios:
      - identity-01-entra-id-users
      - security-02-entra-id-groups
    schedule:
      cron: "0 3,9,15,21 * * *"
      timezone: "Asia/Tokyo"
    resource_tags:
      Customer: EpsilonGroup
      Tier: Standard
    limits:
      max_cost_per_day_usd: 40.00
```

### Dev/Test/Prod Separation

Enterprise with separate development, testing, and production tenants.

```yaml
meta_orchestrator:
  name: enterprise-haymaker
  infrastructure_tenant_id: infra-tenant-id
  max_concurrent_tenants: 3
  enable_tenant_isolation: true

target_tenants:
  - name: development
    display_name: "Development Environment"
    tenant_id: dev-tenant-id
    subscription_id: dev-subscription-id
    credentials:
      keyvault_secret_prefix: dev
    region: eastus
    scenarios:
      - compute-01-linux-vm-web-server
      - databases-01-mysql-wordpress
    schedule:
      cron: "0 8 * * 1-5"  # 8 AM weekdays only
      timezone: "America/New_York"
    resource_tags:
      Environment: Development
      AutoShutdown: "true"
    limits:
      max_cost_per_day_usd: 20.00
    cleanup:
      auto_cleanup: true
      cleanup_delay_hours: 2  # Quick cleanup in dev

  - name: testing
    display_name: "Testing Environment"
    tenant_id: test-tenant-id
    subscription_id: test-subscription-id
    credentials:
      keyvault_secret_prefix: test
    region: eastus
    scenarios:
      - compute-01-linux-vm-web-server
      - databases-01-mysql-wordpress
      - security-01-key-vault-secrets
      - ai-ml-01-cognitive-services-vision
    schedule:
      cron: "0 9 * * 1-5"  # 9 AM weekdays
      timezone: "America/New_York"
    resource_tags:
      Environment: Testing
      AutoShutdown: "true"
    limits:
      max_cost_per_day_usd: 30.00
    cleanup:
      auto_cleanup: true
      cleanup_delay_hours: 4

  - name: production
    display_name: "Production Environment"
    tenant_id: prod-tenant-id
    subscription_id: prod-subscription-id
    credentials:
      keyvault_secret_prefix: prod
    region: eastus
    scenarios:
      - compute-01-linux-vm-web-server
      - databases-01-mysql-wordpress
      - security-01-key-vault-secrets
      - ai-ml-01-cognitive-services-vision
      - containers-01-aks-cluster
      - networking-01-virtual-network
      - analytics-01-synapse-workspace
      - identity-01-entra-id-users
    schedule:
      cron: "0 */6 * * *"  # Every 6 hours, 24/7
      timezone: "UTC"
    resource_tags:
      Environment: Production
      CriticalSystem: "true"
    limits:
      max_cost_per_day_usd: 150.00
    monitoring:
      enable_alerts: true
      alert_email: production-ops@enterprise.com
      cost_alert_threshold_usd: 120.00
    cleanup:
      auto_cleanup: true
      cleanup_delay_hours: 0
      retention_days: 90
```

### Single Target Tenant (Simplest)

Minimal configuration for single target tenant.

```yaml
meta_orchestrator:
  name: simple-orchestrator
  infrastructure_tenant_id: infra-tenant-id
  max_concurrent_tenants: 1

target_tenants:
  - name: my-tenant
    tenant_id: target-tenant-id
    subscription_id: target-subscription-id
    credentials:
      keyvault_secret_prefix: target
    scenarios:
      - compute-01-linux-vm-web-server
      - databases-01-mysql-wordpress
      - security-01-key-vault-secrets
```

### Regional Distribution

Tenants distributed across Azure regions.

```yaml
meta_orchestrator:
  name: global-haymaker
  infrastructure_tenant_id: infra-tenant-id
  max_concurrent_tenants: 10

target_tenants:
  - name: us-east
    display_name: "US East Region"
    tenant_id: tenant-id
    subscription_id: subscription-id
    region: eastus
    credentials:
      keyvault_secret_prefix: us-east
    scenarios:
      - compute-01-linux-vm-web-server
    schedule:
      cron: "0 8 * * *"
      timezone: "America/New_York"

  - name: us-west
    display_name: "US West Region"
    tenant_id: tenant-id
    subscription_id: subscription-id
    region: westus2
    credentials:
      keyvault_secret_prefix: us-west
    scenarios:
      - compute-01-linux-vm-web-server
    schedule:
      cron: "0 8 * * *"
      timezone: "America/Los_Angeles"

  - name: eu-west
    display_name: "Europe West Region"
    tenant_id: tenant-id
    subscription_id: subscription-id
    region: westeurope
    credentials:
      keyvault_secret_prefix: eu-west
    scenarios:
      - compute-01-linux-vm-web-server
    schedule:
      cron: "0 8 * * *"
      timezone: "Europe/London"

  - name: asia-east
    display_name: "Asia East Region"
    tenant_id: tenant-id
    subscription_id: subscription-id
    region: eastasia
    credentials:
      keyvault_secret_prefix: asia-east
    scenarios:
      - compute-01-linux-vm-web-server
    schedule:
      cron: "0 8 * * *"
      timezone: "Asia/Tokyo"
```

---

## Configuration Validation

### Validation Rules

The orchestrator validates configuration at startup:

1. **Required Fields**: All required fields must be present
2. **UUID Format**: Tenant IDs and subscription IDs must be valid UUIDs
3. **Cron Expressions**: Schedule cron expressions must be valid
4. **Unique Names**: Tenant names must be unique
5. **Key Vault Secrets**: Referenced secrets must exist
6. **Scenario Names**: Scenario names must match available scenarios
7. **Limits**: Numeric limits must be positive
8. **Timezones**: Timezone strings must be valid IANA timezones

### Validate Configuration

```bash
# Validate configuration file
haymaker orch config validate --config ~/.haymaker/tenants/multi-tenant-config.yaml
```

**Output:**
```
Validating configuration...

✓ Schema validation passed
✓ Meta-orchestrator configuration valid
✓ 5 target tenants validated
✓ All Key Vault secrets exist
✓ All scenarios exist
✓ All cron expressions valid
✓ All timezones valid

Configuration is valid
```

**Validation Errors:**
```
Validating configuration...

✗ Validation failed

Errors:
  [meta_orchestrator] Field 'infrastructure_tenant_id' is required
  [target_tenants.0] Tenant name 'customer-a' contains invalid characters
  [target_tenants.1] Invalid UUID format for tenant_id
  [target_tenants.2.schedule] Invalid cron expression: "0 25 * * *"
  [target_tenants.3] Key Vault secret 'cust-d-client-id' not found
  [target_tenants.4.scenarios] Unknown scenario: 'invalid-scenario-name'

Fix these errors and try again.
```

### Schema Reference

The configuration schema is defined in JSON Schema format and available at:

```bash
# View schema
haymaker orch config schema

# Export schema to file
haymaker orch config schema --output schema.json
```

---

## Configuration Best Practices

### Security

1. **Never commit secrets**: Don't put credentials in config files
2. **Use Key Vault references**: Store all secrets in Azure Key Vault
3. **Restrict config file permissions**: `chmod 600 ~/.haymaker/tenants/config.yaml`
4. **Rotate credentials regularly**: Update Key Vault secrets every 90 days
5. **Use separate Key Vaults**: Production vs non-production

### Organization

1. **Use descriptive names**: `customer-a-prod` better than `tenant1`
2. **Consistent naming**: Follow naming conventions across tenants
3. **Group by environment**: Use tags to group dev/test/prod
4. **Document tenant purpose**: Use `description` field
5. **Version control**: Store configs in git (without secrets)

### Performance

1. **Tune concurrency**: Set `max_concurrent_tenants` based on capacity
2. **Stagger schedules**: Avoid all tenants running simultaneously
3. **Monitor polling**: Adjust `polling_interval_seconds` for efficiency
4. **Limit scenarios**: Don't exceed resource quotas
5. **Set timeouts**: Use `execution_timeout_hours` to prevent hangs

### Cost Management

1. **Set cost limits**: Use `max_cost_per_day_usd` per tenant
2. **Enable cost alerts**: Configure `cost_alert_threshold_usd`
3. **Auto cleanup**: Always enable `auto_cleanup: true`
4. **Track by tags**: Use consistent `resource_tags` for cost analysis
5. **Review regularly**: Monitor costs via Azure Cost Management

---

## Related Documentation

- [Cross-Tenant Orchestration Guide](../guides/cross-tenant-orchestration.md) - Setup guide
- [Multi-Tenant CLI Commands](../cli/multi-tenant-commands.md) - CLI reference
- [Cross-Tenant Security Guide](../security/cross-tenant-security.md) - Security practices

---

## Support

For configuration issues:

1. Validate with `haymaker orch config validate`
2. Check schema with `haymaker orch config schema`
3. Review examples in this document
4. Open GitHub issue with sanitized config
