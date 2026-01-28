# AzureHayMaker Deployment Setup Guide

> **⚠️ This document is for reference only.** For deployment instructions, see:
> - **[Developer Quick Start](DEVELOPER_QUICK_START.md)** - Deploy your own isolated dev stack
> - **[GitOps Deployment](GITOPS_DEPLOYMENT.md)** - Production CI/CD pipeline

---

## Legacy Reference: Manual Deployment

The sections below document the manual deployment process for reference. **Do not use these instructions for new deployments** - use the Developer Quick Start or GitOps workflows instead.

## Prerequisites

- Azure subscription with Owner or Contributor role
- Azure CLI installed and configured
- Service Principal with appropriate permissions

## Required Service Principal Permissions

The orchestrator service principal requires the following role assignments:

### Subscription Level
```bash
# Contributor role (for resource creation)
az role assignment create \
  --assignee <SP_OBJECT_ID> \
  --role "Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>

# User Access Administrator (for role assignments)
az role assignment create \
  --assignee <SP_OBJECT_ID> \
  --role "User Access Administrator" \
  --scope /subscriptions/<SUBSCRIPTION_ID>
```

### Microsoft Graph API Permissions

Grant via Azure Portal:
- Application.ReadWrite.All
- Directory.ReadWrite.All

### Entra ID Directory Role

Grant via Azure Portal:
- Cloud Application Administrator

## Required Environment Variables

See [Developer Quick Start](DEVELOPER_QUICK_START.md#23-create-your-env-file) for the complete `.env` template.

## Troubleshooting

### Health Endpoint Not Responding

1. Check Container App logs:
```bash
az containerapp logs show \
  --name haymaker-fastapi-orch \
  --resource-group haymaker-<name>-dev-rg \
  --tail 50
```

2. Verify AZURE_CLIENT_ID is set:
```bash
az containerapp show \
  --name haymaker-fastapi-orch \
  --resource-group haymaker-<name>-dev-rg \
  --query "properties.template.containers[0].env[?name=='AZURE_CLIENT_ID']"
```

3. Check deployment workflow succeeded in GitHub Actions

### Container Deployment Failures

Common issues:
- ACR authentication: Ensure managed identity has AcrPull role
- RBAC propagation: Wait 60+ seconds after role assignment
- Resource limits: Use valid CPU/memory combinations
- Name length: Container App names max 32 characters

---

**Note**: This document retained for historical reference. Active deployment docs:
- [Developer Quick Start](DEVELOPER_QUICK_START.md)
- [GitOps Deployment](GITOPS_DEPLOYMENT.md)
