---
layout: default
title: Cross-Tenant Security Guide
parent: Security
nav_order: 1
description: "Security architecture and best practices for cross-tenant orchestration"
permalink: /security/cross-tenant/
---

# Cross-Tenant Security Guide
{: .no_toc }

Comprehensive security architecture, threat model, and best practices for cross-tenant orchestration.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Security Model Overview

Cross-tenant orchestration introduces unique security challenges requiring defense-in-depth across multiple Azure tenants. The security model ensures complete isolation between target tenants while maintaining centralized credential management.

### Security Principles

1. **Tenant Isolation**: Complete resource and data separation between target tenants
2. **Least Privilege**: Minimum required permissions at every level
3. **Defense in Depth**: Multiple layers of security controls
4. **Credential Segmentation**: Isolated credentials per tenant in Key Vault
5. **Audit Everything**: Comprehensive logging of all cross-tenant operations
6. **Zero Trust**: Never assume trust, always verify

### Security Boundaries

```
┌────────────────────────────────────────────────────────────┐
│              Infrastructure Tenant (Trust Boundary 1)       │
│                                                            │
│  ┌─────────────────────────────────────────────────┐     │
│  │    Meta-Orchestrator (Managed Identity)         │     │
│  │    - Accesses Key Vault for credentials         │     │
│  │    - No direct target tenant access              │     │
│  └─────────────────────────────────────────────────┘     │
│                                                            │
│  ┌─────────────────────────────────────────────────┐     │
│  │    Azure Key Vault (Credential Store)           │     │
│  │    - Tenant-specific credentials isolated        │     │
│  │    - Access controlled by managed identity       │     │
│  │    - Audit logging enabled                       │     │
│  └─────────────────────────────────────────────────┘     │
│                                                            │
└────────────────────────────────────────────────────────────┘
               │                    │                │
               │                    │                │
         ┌─────▼─────┐       ┌─────▼─────┐   ┌────▼─────┐
         │ Tenant A  │       │ Tenant B  │   │ Tenant N │
         │(Trust     │       │(Trust     │   │(Trust    │
         │Boundary 2)│       │Boundary 3)│   │Boundary N│
         │           │       │           │   │          │
         │ SP-A only │       │ SP-B only │   │ SP-N only│
         └───────────┘       └───────────┘   └──────────┘
```

**Trust Boundaries:**

1. **Infrastructure Tenant**: Orchestrator and shared services
2. **Target Tenant A**: Service Principal A credentials only
3. **Target Tenant B**: Service Principal B credentials only
4. **Target Tenant N**: Service Principal N credentials only

---

## Credential Management

### Architecture

Credentials for target tenants are managed using Azure Key Vault with strict access controls.

#### Credential Storage Pattern

```
Azure Key Vault: haymaker-kv-abc123
├── Secrets
│   ├── tenant-a-client-id         (Service Principal App ID)
│   ├── tenant-a-client-secret     (Service Principal Password)
│   ├── tenant-a-tenant-id         (Azure AD Directory ID)
│   ├── tenant-a-subscription-id   (Azure Subscription ID)
│   ├── tenant-b-client-id
│   ├── tenant-b-client-secret
│   ├── tenant-b-tenant-id
│   ├── tenant-b-subscription-id
│   └── ...
├── Access Policies
│   └── Orchestrator Managed Identity: Get, List secrets
└── Audit Logs
    └── All secret access logged
```

### Service Principal Creation

Create dedicated service principals for each target tenant with minimal required permissions.

#### Step 1: Create Service Principal

```bash
# Login to target tenant
az login --tenant <target-tenant-id>

# Create service principal with Contributor role at subscription scope
az ad sp create-for-rbac \
  --name "HayMaker-Orchestrator-SP-TenantA" \
  --role Contributor \
  --scopes "/subscriptions/<subscription-id>" \
  --years 1 \
  --sdk-auth
```

**Output:**
```json
{
  "clientId": "12345678-1234-1234-1234-123456789abc",
  "clientSecret": "super-secret-password-DO-NOT-COMMIT",
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

#### Step 2: Store Credentials in Key Vault

```bash
# Switch to infrastructure tenant
az login --tenant <infrastructure-tenant-id>

# Store each credential component
az keyvault secret set \
  --vault-name haymaker-kv-abc123 \
  --name tenant-a-client-id \
  --value "12345678-1234-1234-1234-123456789abc"

az keyvault secret set \
  --vault-name haymaker-kv-abc123 \
  --name tenant-a-client-secret \
  --value "super-secret-password-DO-NOT-COMMIT"

az keyvault secret set \
  --vault-name haymaker-kv-abc123 \
  --name tenant-a-tenant-id \
  --value "abcdef12-3456-7890-abcd-ef1234567890"

az keyvault secret set \
  --vault-name haymaker-kv-abc123 \
  --name tenant-a-subscription-id \
  --value "87654321-4321-4321-4321-cba987654321"
```

#### Step 3: Verify Access

```bash
# Test retrieval
az keyvault secret show \
  --vault-name haymaker-kv-abc123 \
  --name tenant-a-client-id \
  --query value -o tsv
```

### Credential Rotation

Rotate service principal credentials every 90 days.

#### Rotation Process

```bash
# 1. Create new credential for existing service principal
az ad sp credential reset \
  --id <client-id> \
  --years 1

# Output:
# {
#   "appId": "12345678-1234-1234-1234-123456789abc",
#   "password": "new-super-secret-password",
#   "tenant": "abcdef12-3456-7890-abcd-ef1234567890"
# }

# 2. Update Key Vault secret with new password
az keyvault secret set \
  --vault-name haymaker-kv-abc123 \
  --name tenant-a-client-secret \
  --value "new-super-secret-password"

# 3. Test authentication with new credentials
az login --service-principal \
  --username <client-id> \
  --password "new-super-secret-password" \
  --tenant <tenant-id>

# 4. Verify orchestrator can authenticate
haymaker orch tenant status --tenant tenant-a --check-auth

# Output:
# ✓ Authentication successful with new credentials
```

#### Rotation Automation

**Automation script (for production):**

```bash
#!/bin/bash
# rotate-tenant-credentials.sh

TENANT_NAME=$1
KEYVAULT_NAME="haymaker-kv-abc123"

# Get current client ID
CLIENT_ID=$(az keyvault secret show \
  --vault-name $KEYVAULT_NAME \
  --name "${TENANT_NAME}-client-id" \
  --query value -o tsv)

# Reset credential
echo "Rotating credentials for $TENANT_NAME (Client ID: $CLIENT_ID)..."
NEW_CRED=$(az ad sp credential reset --id $CLIENT_ID --years 1)

NEW_PASSWORD=$(echo $NEW_CRED | jq -r .password)

# Update Key Vault
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "${TENANT_NAME}-client-secret" \
  --value "$NEW_PASSWORD"

echo "✓ Credentials rotated successfully"
echo "✓ Updated Key Vault secret: ${TENANT_NAME}-client-secret"
echo "⚠ Test authentication: haymaker orch tenant status --tenant $TENANT_NAME --check-auth"
```

**Schedule rotation:**

```bash
# Add to crontab (every 90 days)
0 2 1 */3 * /path/to/rotate-tenant-credentials.sh tenant-a
0 2 2 */3 * /path/to/rotate-tenant-credentials.sh tenant-b
```

---

## RBAC and Permissions

### Infrastructure Tenant

#### Orchestrator Managed Identity

The orchestrator runs with a system-assigned managed identity.

**Required Permissions:**

| Resource              | Role                      | Scope                | Purpose                        |
|-----------------------|---------------------------|----------------------|--------------------------------|
| Key Vault             | Key Vault Secrets User    | Key Vault            | Read target tenant credentials |
| Storage Account       | Storage Blob Data Owner   | Storage Account      | Read/write configs and logs    |
| Application Insights  | Monitoring Metrics Publisher | App Insights      | Write telemetry                |

**Assign permissions:**

```bash
# Get orchestrator managed identity principal ID
ORCH_PRINCIPAL_ID=$(az functionapp identity show \
  --name haymaker-orchestrator \
  --resource-group haymaker-infra-rg \
  --query principalId -o tsv)

# Grant Key Vault Secrets User
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $ORCH_PRINCIPAL_ID \
  --scope "/subscriptions/<infra-subscription-id>/resourceGroups/haymaker-infra-rg/providers/Microsoft.KeyVault/vaults/haymaker-kv-abc123"

# Grant Storage Blob Data Owner
az role assignment create \
  --role "Storage Blob Data Owner" \
  --assignee $ORCH_PRINCIPAL_ID \
  --scope "/subscriptions/<infra-subscription-id>/resourceGroups/haymaker-infra-rg/providers/Microsoft.Storage/storageAccounts/haymakerstorage"

# Grant Monitoring Metrics Publisher
az role assignment create \
  --role "Monitoring Metrics Publisher" \
  --assignee $ORCH_PRINCIPAL_ID \
  --scope "/subscriptions/<infra-subscription-id>/resourceGroups/haymaker-infra-rg/providers/microsoft.insights/components/haymaker-appinsights"
```

#### Administrator Access

Limit administrative access to infrastructure tenant.

**Recommended roles:**

- **Owner**: 0-1 users (break-glass account only)
- **Contributor**: 2-3 operators
- **Reader**: Read-only access for auditors
- **Key Vault Administrator**: Separate role for credential management

### Target Tenants

#### Service Principal Permissions

Each target tenant has a dedicated service principal with minimal permissions.

**Required Role: Contributor** (at subscription scope)

This allows:
- Creating/deleting resource groups
- Deploying Azure resources
- Managing resource lifecycle

**Does NOT allow:**
- Managing RBAC assignments
- Accessing other subscriptions
- Modifying Azure AD objects
- Reading secrets from other Key Vaults

#### Optional: Restricted Permissions

For enhanced security, use custom roles with specific permissions:

```json
{
  "Name": "HayMaker Scenario Deployer",
  "IsCustom": true,
  "Description": "Minimal permissions for HayMaker scenario deployment",
  "Actions": [
    "Microsoft.Resources/subscriptions/resourceGroups/write",
    "Microsoft.Resources/subscriptions/resourceGroups/delete",
    "Microsoft.Compute/virtualMachines/*",
    "Microsoft.Network/virtualNetworks/*",
    "Microsoft.Storage/storageAccounts/*",
    "Microsoft.KeyVault/vaults/*",
    "Microsoft.ContainerInstance/containerGroups/*",
    "Microsoft.Web/sites/*",
    "Microsoft.DBforMySQL/servers/*",
    "Microsoft.CognitiveServices/accounts/*"
  ],
  "NotActions": [
    "Microsoft.Authorization/*/write",
    "Microsoft.Authorization/*/delete"
  ],
  "AssignableScopes": [
    "/subscriptions/<target-subscription-id>"
  ]
}
```

**Create and assign custom role:**

```bash
# Create custom role
az role definition create --role-definition haymaker-deployer-role.json

# Assign to service principal
az role assignment create \
  --role "HayMaker Scenario Deployer" \
  --assignee <service-principal-client-id> \
  --scope "/subscriptions/<target-subscription-id>"
```

---

## Tenant Isolation

### Resource Isolation

Resources in different target tenants are completely isolated.

#### Isolation Mechanisms

1. **Separate Azure Tenants**: Each target tenant is a distinct Azure AD tenant
2. **Dedicated Service Principals**: One service principal per target tenant
3. **Credential Segregation**: Credentials stored separately in Key Vault
4. **Resource Tagging**: All resources tagged with tenant identifier
5. **Separate Resource Groups**: Resources grouped by tenant and scenario

#### Resource Naming Convention

```
<tenant-prefix>-<scenario>-<resource-type>-<unique-id>

Examples:
  tenant-a-compute-01-vm-abc123
  tenant-b-databases-01-mysql-xyz789
```

### Data Isolation

Data from different tenants is stored separately.

#### Storage Isolation Pattern

```
Storage Account: haymakerstorage
├── Container: tenant-a-configs
│   ├── tenant-config.yaml
│   └── scenario-definitions/
├── Container: tenant-a-logs
│   ├── execution-logs/
│   └── audit-logs/
├── Container: tenant-b-configs
│   └── ...
├── Container: tenant-b-logs
│   └── ...
└── Container: meta-orchestrator-logs
    └── aggregated-logs/
```

**Access Control:**

- Orchestrator: Read/write all containers
- Tenant-specific apps: Read/write only their tenant's containers
- External services: No access (use SAS tokens with time limits)

### Network Isolation

Optional: Use VNet integration to isolate network traffic.

```
Infrastructure VNet
├── Orchestrator Subnet
│   └── Private endpoint to Key Vault
├── Storage Subnet
│   └── Private endpoint to Storage
└── Management Subnet
    └── Jump box for administration

Target Tenant A VNet
├── Scenario Subnet
│   └── Deployed resources
└── Private DNS zones

Target Tenant B VNet
├── Scenario Subnet
│   └── Deployed resources
└── Private DNS zones
```

**Configuration:**

```bash
# Create private endpoint to Key Vault from orchestrator
az network private-endpoint create \
  --name kv-private-endpoint \
  --resource-group haymaker-infra-rg \
  --vnet-name infrastructure-vnet \
  --subnet orchestrator-subnet \
  --private-connection-resource-id <keyvault-resource-id> \
  --group-id vault \
  --connection-name kv-connection
```

---

## Audit Logging

### Required Logging

Enable comprehensive audit logging for security and compliance.

#### Key Vault Audit Logs

Track all secret access operations.

```bash
# Enable diagnostic settings for Key Vault
az monitor diagnostic-settings create \
  --name kv-audit-logs \
  --resource <keyvault-resource-id> \
  --logs '[
    {
      "category": "AuditEvent",
      "enabled": true,
      "retentionPolicy": {
        "enabled": true,
        "days": 365
      }
    }
  ]' \
  --workspace <log-analytics-workspace-id>
```

**Query Key Vault access:**

```kusto
// Log Analytics query
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where OperationName == "SecretGet"
| where ResultType == "Success"
| project TimeGenerated, CallerIPAddress, identity_claim_appid_g, id_s
| order by TimeGenerated desc
```

#### Orchestrator Activity Logs

Log all cross-tenant operations.

```python
# Example logging in orchestrator
import logging
from azure.monitor.opentelemetry import configure_azure_monitor

# Configure Application Insights
configure_azure_monitor(
    connection_string="InstrumentationKey=<key>",
)

logger = logging.getLogger(__name__)

# Log tenant authentication
logger.info(
    "Authenticating to target tenant",
    extra={
        "tenant_name": "customer-a",
        "tenant_id": "12345678-...",
        "operation": "authenticate",
    }
)

# Log scenario execution
logger.info(
    "Starting scenario execution",
    extra={
        "tenant_name": "customer-a",
        "scenario": "compute-01-linux-vm-web-server",
        "execution_id": "exec-abc123",
    }
)

# Log security events
logger.warning(
    "Authentication failed for tenant",
    extra={
        "tenant_name": "customer-b",
        "error": "Invalid credentials",
        "action_taken": "Disabled tenant",
    }
)
```

#### Target Tenant Activity Logs

Enable activity logs in each target tenant.

```bash
# Create diagnostic settings for subscription
az monitor diagnostic-settings subscription create \
  --name tenant-a-activity-logs \
  --location eastus \
  --logs '[
    {
      "category": "Administrative",
      "enabled": true
    },
    {
      "category": "Security",
      "enabled": true
    },
    {
      "category": "ResourceHealth",
      "enabled": true
    }
  ]' \
  --workspace <log-analytics-workspace-id>
```

### Audit Queries

**Track all tenant authentications:**

```kusto
traces
| where customDimensions.operation == "authenticate"
| project
    timestamp,
    tenant = customDimensions.tenant_name,
    tenant_id = customDimensions.tenant_id,
    result = customDimensions.result
| order by timestamp desc
```

**Monitor credential access:**

```kusto
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where OperationName == "SecretGet"
| where id_s contains "client-secret"
| summarize AccessCount = count() by
    Tenant = extract("(tenant-[^-]+)", 1, id_s),
    Hour = bin(TimeGenerated, 1h)
| order by Hour desc
```

**Detect anomalous behavior:**

```kusto
// Detect unusual number of authentication attempts
traces
| where customDimensions.operation == "authenticate"
| summarize
    Attempts = count(),
    Failures = countif(customDimensions.result == "failed")
    by Tenant = customDimensions.tenant_name, bin(timestamp, 1h)
| where Failures > 3
| order by timestamp desc
```

---

## Threat Model

### Threats and Mitigations

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| **Credential Theft** | Critical | Medium | Store in Key Vault, rotate regularly, managed identity access |
| **Tenant Cross-Contamination** | Critical | Low | Strict isolation, separate service principals, validation |
| **Unauthorized Access** | High | Medium | RBAC, least privilege, audit logging |
| **Service Principal Compromise** | High | Medium | Limited scope, monitoring, automatic rotation |
| **Key Vault Breach** | Critical | Low | Private endpoints, access policies, network restrictions |
| **Insider Threat** | High | Low | RBAC, audit logging, separation of duties |
| **Denial of Service** | Medium | Medium | Rate limiting, circuit breakers, resource quotas |
| **Resource Quota Exhaustion** | Medium | High | Per-tenant limits, monitoring, alerts |

### Attack Scenarios

#### Scenario 1: Compromised Service Principal

**Attack:** Attacker obtains service principal credentials for Tenant A.

**Impact:** Attacker can deploy resources in Tenant A only.

**Mitigations:**
1. Credentials scoped to single tenant/subscription
2. Resource deployment logs in Activity Log
3. Cost alerts detect unusual spending
4. Automatic credential rotation limits exposure window
5. Circuit breaker stops orchestration on repeated failures

**Detection:**
```kusto
// Detect resources created outside orchestration
AzureDiagnostics
| where OperationName == "Create or Update Resource Group"
| where CallerObjectId == "<service-principal-object-id>"
| where not(tags_s contains "ManagedBy=HayMaker")
```

#### Scenario 2: Key Vault Access

**Attack:** Attacker gains access to infrastructure tenant and tries to read all secrets.

**Impact:** Could obtain credentials for all target tenants.

**Mitigations:**
1. Key Vault private endpoint (no internet access)
2. Managed identity authentication only
3. Network restrictions on Key Vault
4. Audit logging of all secret access
5. Alert on unusual access patterns

**Detection:**
```kusto
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where OperationName == "SecretList"
| where identity_claim_appid_g != "<orchestrator-app-id>"
```

#### Scenario 3: Tenant Isolation Breach

**Attack:** Bug in orchestrator allows cross-tenant resource access.

**Impact:** Resources from Tenant A deployed in Tenant B.

**Mitigations:**
1. Strict credential validation before use
2. Resource tagging enforcement
3. Separate service principals per tenant
4. Code review and testing of isolation logic
5. Monitoring for unexpected resource creation

**Detection:**
```kusto
// Detect resources with mismatched tenant tags
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.RESOURCES"
| where OperationName == "Create or Update Resource"
| where tags_s contains "TenantName"
| where not(tags_s contains subscription_s)
```

---

## Compliance Considerations

### Regulatory Requirements

#### Data Residency

Ensure data stays in required regions.

```yaml
target_tenants:
  - name: eu-customer
    region: westeurope
    allowed_regions:
      - westeurope
      - northeurope
    blocked_regions:
      - eastus
      - westus
```

#### GDPR Compliance

**Personal Data Handling:**

1. **Minimize PII**: Don't collect unnecessary personal data
2. **Encryption**: Encrypt data at rest and in transit
3. **Data Retention**: Automatic deletion after retention period
4. **Right to Erasure**: Support tenant data deletion
5. **Audit Trail**: Comprehensive logging for accountability

**Implementation:**

```yaml
cleanup:
  retention_days: 30  # Delete logs after 30 days
  delete_personal_data: true
  maintain_audit_trail: true
```

#### SOC 2 Compliance

**Required Controls:**

1. **Access Control**: RBAC and least privilege
2. **Encryption**: TLS 1.2+, AES-256 at rest
3. **Monitoring**: Continuous monitoring and alerting
4. **Incident Response**: Documented procedures
5. **Change Management**: Approval workflows

### Compliance Audit

**Generate compliance report:**

```bash
# Run compliance check
haymaker orch compliance-check --tenant customer-a

# Output:
# Compliance Check: customer-a
# ═══════════════════════════════════════
#
# ✓ Encryption at rest enabled
# ✓ TLS 1.2 enforced
# ✓ Audit logging enabled
# ✓ RBAC configured correctly
# ✓ Data retention policy set
# ✓ Resource tagging compliant
# ⚠ Key Vault soft-delete not enabled
#
# Score: 6/7 (86%)
# Recommendation: Enable Key Vault soft-delete
```

---

## Security Best Practices

### Development

1. **Never commit secrets**: Use `.gitignore` for credential files
2. **Use separate dev credentials**: Don't use production credentials in development
3. **Test isolation**: Verify tenant isolation in test environments
4. **Security reviews**: Code review all authentication logic
5. **Dependency scanning**: Regularly update dependencies

### Operations

1. **Principle of least privilege**: Grant minimum required permissions
2. **Rotate credentials**: Every 90 days or on security events
3. **Monitor continuously**: Set up alerts for security events
4. **Incident response plan**: Document procedures for security incidents
5. **Regular audits**: Review access logs monthly

### Monitoring Checklist

- [ ] Key Vault access monitored
- [ ] Failed authentication attempts alerted
- [ ] Unusual cost spikes detected
- [ ] Resource creation audited
- [ ] Service principal usage tracked
- [ ] Network traffic logged (if using private endpoints)
- [ ] Compliance reports generated monthly

---

## Incident Response

### Security Event Response

#### Compromised Service Principal

**Immediate Actions:**

```bash
# 1. Disable service principal
az ad sp update --id <client-id> --set accountEnabled=false

# 2. Revoke all credentials
az ad sp credential reset --id <client-id> --append false

# 3. Disable tenant in orchestrator
haymaker orch tenant update --name tenant-a --disabled

# 4. Review recent activity
az monitor activity-log list \
  --caller <service-principal-object-id> \
  --start-time 2025-12-01 \
  --end-time 2025-12-09

# 5. Delete unauthorized resources
az group list --tag "CreatedOutsideOrchestration=true" |
  jq -r '.[].name' |
  xargs -I {} az group delete --name {} --yes --no-wait
```

**Post-Incident:**

1. Root cause analysis
2. Update threat model
3. Implement additional controls
4. Notify affected parties
5. Document lessons learned

#### Key Vault Breach Suspected

**Immediate Actions:**

```bash
# 1. Enable Key Vault firewall (block all access)
az keyvault update \
  --name haymaker-kv-abc123 \
  --default-action Deny

# 2. Review access logs
az monitor activity-log list \
  --resource-id <keyvault-resource-id> \
  --start-time 2025-12-01

# 3. Rotate ALL credentials
for tenant in customer-a customer-b customer-c; do
  ./rotate-tenant-credentials.sh $tenant
done

# 4. Update firewall to allow orchestrator only
az keyvault network-rule add \
  --name haymaker-kv-abc123 \
  --ip-address <orchestrator-public-ip>
```

---

## Related Documentation

- [Cross-Tenant Orchestration Guide](../guides/cross-tenant-orchestration.md) - Setup guide
- [Multi-Tenant Configuration](../configuration/multi-tenant-config.md) - Configuration reference
- [Multi-Tenant CLI Commands](../cli/multi-tenant-commands.md) - CLI reference

---

## Security Contacts

For security issues:

1. **Do not open public GitHub issues for security vulnerabilities**
2. Email: security@example.com
3. Use GitHub Security Advisories (private disclosure)
4. Include: tenant name (if applicable), timestamps, relevant logs (sanitized)

Response SLA: 24 hours for critical, 72 hours for non-critical
