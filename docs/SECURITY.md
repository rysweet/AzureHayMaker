---
layout: default
title: Security
nav_order: 8
has_children: true
description: "Security architecture, policies, and best practices for Azure HayMaker"
permalink: /security/
---

# Security Guide
{: .no_toc }

Security architecture, policies, and best practices for Azure HayMaker.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Reporting Security Issues

{: .warning }
> **DO NOT** create public GitHub issues for security vulnerabilities.

**Responsible Disclosure Process**:

1. Email: rysweet@microsoft.com
2. Include: Detailed description, steps to reproduce, impact assessment
3. Wait for acknowledgment before public disclosure

---

## Security Architecture Overview

Azure HayMaker implements defense-in-depth with multiple security layers:

```
+------------------------------------------------------------------+
|                      SECURITY LAYERS                              |
+------------------------------------------------------------------+
|  1. Identity & Access  |  Azure AD, Service Principals, RBAC     |
+------------------------+------------------------------------------+
|  2. Credential Mgmt    |  Key Vault, Ephemeral SPs, Rotation     |
+------------------------+------------------------------------------+
|  3. Network Security   |  Private Endpoints, NSGs, Firewall      |
+------------------------+------------------------------------------+
|  4. Data Protection    |  TLS 1.2+, Encryption at Rest           |
+------------------------+------------------------------------------+
|  5. Audit & Monitoring |  Activity Logs, Key Vault Logs, Alerts  |
+------------------------------------------------------------------+
```

---

## Key Vault Integration

### Architecture

All secrets are stored in Azure Key Vault with RBAC-based access control:

```
+-------------------+       +------------------+       +----------------+
|   Orchestrator    | ----> |   Azure         | ----> |  Function App  |
|   (Creates SP)    |       |   Key Vault     |       |  (Reads SP)    |
+-------------------+       +------------------+       +----------------+
                                    |
                                    v
                            +----------------+
                            | Agent Container|
                            | (Uses SP)      |
                            +----------------+
```

### Credential Flow

1. **Orchestrator creates ephemeral service principal**
2. **Credentials stored in Key Vault** (never in code or logs)
3. **Agent retrieves credentials via managed identity**
4. **Credentials used for scenario execution**
5. **SP deleted after scenario completes** (credentials invalidated)

### Key Vault Configuration

**Production Settings**:

```bicep
publicNetworkAccess: false       // Disabled - use private endpoints
networkAcls: {
  bypass: 'AzureServices'
  defaultAction: 'Deny'          // Deny by default
}
enablePurgeProtection: true      // Prevent accidental deletion
softDeleteRetentionInDays: 30    // 30-day recovery window
```

**Development Settings**:

```bicep
publicNetworkAccess: true        // Enabled for local development
networkAcls: {
  defaultAction: 'Allow'         // Allow for dev convenience
  ipRules: [...]                 // Restrict to known IPs
}
```

---

## Service Principal Lifecycle

### Ephemeral Service Principals

Azure HayMaker uses **ephemeral service principals** for enhanced security:

| Property | Value | Rationale |
|:---------|:------|:----------|
| Lifetime | 12 hours max | Limits exposure window |
| Scope | Single subscription | Prevents lateral movement |
| Credentials | Rotated per execution | No credential reuse |
| Storage | Key Vault only | Never in code or logs |
| Cleanup | Automatic deletion | No orphaned credentials |

### Roles Assigned

**Main Service Principal** (Orchestrator):
- `Contributor` - Create/delete Azure resources
- `User Access Administrator` - Assign roles to scenario SPs
- `Key Vault Administrator` - Manage credential storage

**Scenario Service Principal** (Per-execution):
- `Contributor` - Create/delete scenario resources only
- Scoped to single resource group
- Time-limited (deleted after scenario)

### Lifecycle Flow

```
┌─────────────┐
│ Orchestrator│
│   Start     │
└──────┬──────┘
       │
       v
┌─────────────────────────────┐
│ 1. Create Service Principal │
│    - Generate credentials   │
│    - Store in Key Vault     │
│    - Assign minimal roles   │
└──────────────┬──────────────┘
               │
               v
┌─────────────────────────────┐
│ 2. Deploy Agent Container   │
│    - Pass SP reference      │
│    - Agent retrieves from   │
│      Key Vault              │
└──────────────┬──────────────┘
               │
               v
┌─────────────────────────────┐
│ 3. Execute Scenario         │
│    - Create resources       │
│    - Perform operations     │
│    - Clean up resources     │
└──────────────┬──────────────┘
               │
               v
┌─────────────────────────────┐
│ 4. Delete Service Principal │
│    - Delete SP from AAD     │
│    - Delete secret from KV  │
│    - Credentials invalidated│
└─────────────────────────────┘
```

---

## RBAC Configuration

### Role Assignments

| Principal | Role | Scope | Purpose |
|:----------|:-----|:------|:--------|
| Orchestrator SP | Contributor | Subscription | Manage resources |
| Orchestrator SP | User Access Administrator | Subscription | Assign roles |
| Orchestrator SP | Key Vault Administrator | Key Vault | Manage secrets |
| Scenario SP | Contributor | Resource Group | Execute scenario |
| Function App MI | Key Vault Secrets User | Key Vault | Read secrets |

### Least Privilege Principles

1. **No Global Administrator** - Never required
2. **Subscription-scoped only** - No management group access
3. **Time-limited SPs** - Deleted after 12 hours max
4. **Resource group isolation** - Each scenario in dedicated RG

---

## Network Security

### Production Configuration

1. **Private Endpoints** for Key Vault and Storage
2. **Network Security Groups** restricting inbound/outbound
3. **Azure Firewall** for egress filtering (optional)
4. **VNet Integration** for Function App

### Container Network Policy

Agents have restricted network access:

```yaml
# Allowed Outbound
- Azure Management APIs (management.azure.com)
- Anthropic API (api.anthropic.com)
- Azure Service Bus (for logging)
- Azure Key Vault (for credentials)

# Blocked Outbound
- All other internet destinations
- Internal networks
```

---

## Data Protection

### Encryption

| Layer | Mechanism | Status |
|:------|:----------|:-------|
| In Transit | TLS 1.2+ required | Enabled |
| At Rest | Azure Storage Encryption | Enabled |
| Key Vault | HSM-backed keys | Enabled |
| Logs | Log Analytics encryption | Enabled |

### Credential Scrubbing

All logs are scrubbed to prevent credential exposure:

- Service principal secrets
- API keys
- Connection strings
- Access tokens

---

## Audit Logging

### Logged Events

All security-relevant operations are logged:

- Service principal creation/deletion
- Role assignments
- Key Vault access
- Resource creation/deletion
- Authentication events
- Error conditions

### Log Retention

| Log Type | Retention | Location |
|:---------|:----------|:---------|
| Azure Activity Log | 90 days | Azure subscription |
| Key Vault Audit Logs | 90 days | Log Analytics |
| Container Logs | 30 days | Log Analytics |
| Service Bus Messages | 7 days | Service Bus |

### Monitoring Alerts

Recommended alerts for security monitoring:

1. **Failed Key Vault Access** - Unauthorized access attempts
2. **SP Creation Outside Orchestrator** - Unexpected SP creation
3. **Role Assignment Changes** - RBAC modifications
4. **Resource Deletion Failures** - Cleanup issues
5. **High Error Rates** - Potential attacks

---

## Security Fixes History

### PR #6 Security Review (2025-11-17)

Fixed **8 vulnerabilities** (3 CRITICAL, 5 HIGH):

| Severity | Issue | Fix |
|:---------|:------|:----|
| CRITICAL | OData Injection | Input sanitization |
| CRITICAL | CLI Config Permissions | 0600 file permissions |
| CRITICAL | Key Vault Network Exposure | Default deny, private endpoints |
| HIGH | Race Conditions | Atomic operations |
| HIGH | Missing Authentication | API key validation |
| HIGH | Credential Leaks | Log scrubbing |
| HIGH | Path Traversal | Input validation |
| HIGH | Error Information Leaks | Generic error messages |

**See**: [SECURITY_FIXES.md](SECURITY_FIXES.md) for detailed fix documentation.

---

## Security Best Practices

### Secret Management

{: .important }
> **Production**: Always use Key Vault with private endpoints.
> **Development**: Use .env file (gitignored) for local testing.
> **Never**: Commit secrets to git or log them.

### Access Control

1. **Use Managed Identity** where possible (eliminates credentials)
2. **Apply least privilege** - Only assign required roles
3. **Rotate secrets regularly** - 90-day maximum lifetime
4. **Monitor access logs** - Review Key Vault audit logs weekly

### Code Security

1. **No hardcoded credentials** - Use environment variables or Key Vault
2. **Input validation** - Sanitize all user inputs
3. **Secure defaults** - Deny by default, allow explicitly
4. **Error handling** - Never expose sensitive info in errors

---

## Compliance Checklist

| Requirement | Status | Evidence |
|:------------|:-------|:---------|
| RBAC implemented | Complete | Azure role assignments |
| Encryption at rest | Complete | Azure Storage Encryption |
| Encryption in transit | Complete | TLS 1.2+ enforced |
| Audit logging | Complete | Log Analytics workspace |
| Secret rotation | Supported | Key Vault rotation policies |
| Least privilege | Complete | Scoped role assignments |
| Network isolation | Complete | NSGs, private endpoints |
| Vulnerability scanning | Ongoing | Dependabot, CodeQL |

---

## Verification

### Run Security Verification Script

```bash
./scripts/verify-security-fix.sh
```

**Expected output**:
```
Checking Key Vault references...
SUCCESS! Key Vault references confirmed!

Checking file permissions...
SUCCESS! Config files have secure permissions!

Checking network configuration...
SUCCESS! Network security configured!
```

### Manual Security Checks

```bash
# Check Key Vault network rules
az keyvault show --name <vault-name> \
  --query "properties.networkAcls"

# Check service principal roles
az role assignment list \
  --assignee <sp-id> \
  --output table

# Check activity logs for anomalies
az monitor activity-log list \
  --resource-group <rg-name> \
  --max-events 100
```

---

## Related Documentation

- [Architecture - Security Section](/AzureHayMaker/architecture/#security-architecture)
- [Security Fixes Detail](SECURITY_FIXES.md)
- [Deployment Guide - Secrets Setup](/AzureHayMaker/deployment/)
- [GitOps Setup - OIDC Configuration](GITOPS_SETUP.md)

---

## Security Updates

**Last Security Review**: 2025-11-17
**Findings**: 0 critical, 0 high (all fixed)
**Status**: APPROVED

**Next Scheduled Review**: 2026-02-17 (quarterly)
