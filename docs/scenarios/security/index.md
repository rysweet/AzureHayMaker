---
layout: default
title: Security
parent: Scenarios
nav_order: 9
has_children: true
description: "Security scenarios including Key Vault and NSGs"
permalink: /scenarios/security/
---

# Security Scenarios
{: .no_toc }

Scenarios for Azure security services including Key Vault, Network Security, and Identity.
{: .fs-6 .fw-300 }

---

## Available Scenarios

| Scenario | Description | Complexity |
|:---------|:------------|:-----------|
| [Key Vault Secrets](../security-01-key-vault-secrets/) | Secret management with Key Vault | Low |
| [Entra ID Groups](../security-02-entra-id-groups/) | Azure AD group management | Medium |
| [Network Security Groups](../security-03-network-security-groups/) | NSG configuration | Medium |
| [Managed Identity](../security-04-managed-identity/) | Managed Identity setup | Medium |
| [Security Center Policies](../security-05-security-center-policies/) | Defender for Cloud policies | High |

## Technologies Used

- Azure Key Vault
- Microsoft Entra ID (Azure AD)
- Network Security Groups
- Managed Identities
- Microsoft Defender for Cloud

## Prerequisites

- Azure subscription with security services enabled
- Microsoft Entra ID tenant
- Security Administrator role for some scenarios
