# Rollback Procedure - Requirement 4: Secret Management Consolidation

## Overview

This document provides step-by-step instructions for rolling back the Secret Management Consolidation changes if issues occur during or after deployment.

**Change Date:** 2025-11-17
**Requirement:** Issue #10 - Requirement 4
**Risk Level:** HIGH (Production outage if Function App cannot access Key Vault)

---

## When to Rollback

Trigger rollback if:

1. **Function App fails to start** after deployment
2. **Key Vault access denied errors** in Function App logs
3. **Secrets not accessible** at runtime (400/401/403 errors)
4. **RBAC propagation fails** after 10 minutes
5. **Critical production functionality broken**

---

## Quick Rollback (Emergency - 5 minutes)

If the Function App is down and you need immediate recovery:

### Step 1: Restore Direct Secret Injection

```bash
# Get Function App name
FUNCTION_APP_NAME="haymaker-dev-func-<suffix>"
RG_NAME="haymaker-dev-rg"

# Inject secrets directly as environment variables (TEMPORARY FIX)
az functionapp config appsettings set \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --settings \
    MAIN_SP_CLIENT_SECRET="<value-from-github-secret>" \
    ANTHROPIC_API_KEY="<value-from-github-secret>" \
    LOG_ANALYTICS_WORKSPACE_KEY="<value-from-github-secret>" \
    AZURE_TENANT_ID="<value-from-github-secret>" \
    AZURE_SUBSCRIPTION_ID="<value-from-github-secret>" \
    AZURE_CLIENT_ID="<value-from-github-secret>" \
    SIMULATION_SIZE="small" \
  --output none
```

### Step 2: Restart Function App

```bash
az functionapp restart \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME"

# Wait 30 seconds
sleep 30

# Verify Function App is running
az functionapp show \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query "state" -o tsv
```

### Step 3: Verify Recovery

```bash
# Check Function App logs
az functionapp log tail \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME"

# Should see successful startup, no KeyVault errors
```

**SECURITY WARNING:** Secrets are now visible in Azure Portal. This is a temporary fix only.

---

## Full Rollback (Code Revert - 30 minutes)

For a complete rollback to the previous secure state:

### Step 1: Identify Commit Hash

```bash
cd /Users/ryan/src/AzureHayMaker/worktrees/feat/issue-10-five-critical-improvements

# Find the commit before Requirement 4 changes
git log --oneline --grep="Requirement 4" -n 1
# Note the commit hash BEFORE this commit

# Or use this to see recent commits
git log --oneline -10
```

### Step 2: Revert Code Changes

```bash
# Revert the specific commit (creates a new revert commit)
git revert <commit-hash> --no-edit

# Or restore specific files from before the change
git checkout <commit-hash-before-req4> -- .github/workflows/deploy-dev.yml
git checkout <commit-hash-before-req4> -- .env.example
git checkout <commit-hash-before-req4> -- README.md

# Commit the revert
git add .
git commit -m "Revert Requirement 4: Secret Management - Rollback to direct injection"
```

### Step 3: Push and Redeploy

```bash
# Push to trigger deployment
git push origin feat/issue-10-five-critical-improvements

# Or manually trigger workflow
gh workflow run deploy-dev.yml
```

### Step 4: Monitor Deployment

```bash
# Watch workflow execution
gh run watch

# Check deployment logs
gh run view --log
```

### Step 5: Verify Function App

```bash
# Wait for deployment to complete (5-10 minutes)
# Then verify Function App settings
az functionapp config appsettings list \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query "[?name=='ANTHROPIC_API_KEY'].value" -o tsv

# Should show the actual key value, NOT @Microsoft.KeyVault reference
```

---

## Diagnostic Steps (Before Rollback)

Try these diagnostics before triggering full rollback:

### 1. Check RBAC Role Assignment

```bash
# Get Function App Managed Identity Principal ID
FUNCTION_APP_PRINCIPAL_ID=$(az functionapp identity show \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query principalId -o tsv)

echo "Function App Principal ID: $FUNCTION_APP_PRINCIPAL_ID"

# Get Key Vault name
KEY_VAULT_NAME=$(az keyvault list \
  --resource-group "$RG_NAME" \
  --query "[0].name" -o tsv)

echo "Key Vault Name: $KEY_VAULT_NAME"

# Check if role assignment exists
az role assignment list \
  --assignee "$FUNCTION_APP_PRINCIPAL_ID" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/$RG_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME" \
  --query "[?roleDefinitionName=='Key Vault Secrets User']" -o table

# Should show one role assignment
```

### 2. Manually Assign RBAC (If Missing)

```bash
# Get Key Vault resource ID
KEY_VAULT_ID=$(az keyvault show \
  --name "$KEY_VAULT_NAME" \
  --query id -o tsv)

# Assign Key Vault Secrets User role
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id "$FUNCTION_APP_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "$KEY_VAULT_ID"

# Wait 60 seconds for propagation
sleep 60

# Restart Function App
az functionapp restart --name "$FUNCTION_APP_NAME" --resource-group "$RG_NAME"
```

### 3. Verify Secrets in Key Vault

```bash
# List secrets (requires your user to have access)
az keyvault secret list \
  --vault-name "$KEY_VAULT_NAME" \
  --query "[].name" -o tsv

# Should show:
# - main-sp-client-secret
# - anthropic-api-key
# - log-analytics-workspace-key

# Verify secret exists (DO NOT show value)
az keyvault secret show \
  --vault-name "$KEY_VAULT_NAME" \
  --name anthropic-api-key \
  --query "id" -o tsv

# Should return secret ID without error
```

### 4. Check Function App Configuration

```bash
# Verify Key Vault references are configured
az functionapp config appsettings list \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query "[?contains(value, '@Microsoft.KeyVault')]" -o table

# Should show 3 settings with Key Vault references
```

### 5. Test Key Vault Access

```bash
# Restart Function App to force Key Vault resolution
az functionapp restart --name "$FUNCTION_APP_NAME" --resource-group "$RG_NAME"

# Wait 30 seconds
sleep 30

# Check logs for errors
az functionapp log tail \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  | grep -i "keyvault\|secret\|access denied"

# Should NOT show any access denied errors
```

---

## Post-Rollback Actions

After successful rollback:

1. **Document the Issue**
   - What went wrong?
   - Error messages captured?
   - Timeline of events?

2. **Update GitHub Issue**
   - Add comment to Issue #10
   - Mark Requirement 4 as "Blocked"
   - Link to error logs/screenshots

3. **Schedule Investigation**
   - Root cause analysis
   - Test in isolated environment
   - Fix and re-test before retry

4. **Security Reminder**
   - Direct injection is a security risk
   - Plan to re-attempt Key Vault migration
   - Monitor for secret exposure

---

## Prevention for Next Attempt

Before re-attempting Requirement 4:

1. **Test in Isolated Environment**
   ```bash
   # Create test resource group
   az group create --name haymaker-test-keyvault-rg --location eastus2

   # Deploy minimal infrastructure
   # Test Key Vault access pattern
   # Verify RBAC propagation time
   # Delete test resources
   ```

2. **Extended RBAC Wait**
   - Increase wait time from 60s to 120s
   - Add retry logic to Key Vault access
   - Implement health check endpoint

3. **Gradual Rollout**
   - Deploy to dev first (wait 24 hours)
   - Then staging (wait 24 hours)
   - Finally production

4. **Monitoring**
   - Set up Application Insights alerts
   - Monitor Key Vault access failures
   - Track secret resolution errors

---

## Contact Information

If rollback fails or issues persist:

- **GitHub Issue:** [Issue #10](https://github.com/your-org/AzureHayMaker/issues/10)
- **Escalation:** Tag @your-team in issue comments
- **Emergency:** Contact Azure Support (if Azure-side issue)

---

## Rollback Checklist

Use this checklist during rollback:

### Quick Rollback
- [ ] Function App name and resource group identified
- [ ] Secrets retrieved from GitHub Secrets
- [ ] Direct injection command executed
- [ ] Function App restarted
- [ ] Function App state verified (running)
- [ ] Logs checked (no errors)
- [ ] Orchestrator functionality tested
- [ ] Security warning documented

### Full Rollback
- [ ] Commit hash identified (before Requirement 4)
- [ ] Code reverted (deploy-dev.yml, .env.example, README.md)
- [ ] Changes committed to git
- [ ] Changes pushed to remote
- [ ] Deployment workflow triggered
- [ ] Deployment completed successfully
- [ ] Function App settings verified (direct values, not references)
- [ ] Function App restarted
- [ ] Integration tests passed
- [ ] Issue #10 updated with rollback status

### Post-Rollback
- [ ] Root cause documented
- [ ] Error logs saved
- [ ] Screenshots captured (if applicable)
- [ ] Team notified
- [ ] Prevention measures planned
- [ ] Re-attempt scheduled

---

**Last Updated:** 2025-11-17
**Document Version:** 1.0
**Status:** Active
