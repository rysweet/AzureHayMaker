# Testing Checklist - Requirement 4: Secret Management Consolidation

## Overview

This checklist provides comprehensive testing procedures for validating the Secret Management Consolidation implementation.

**Change Date:** 2025-11-17
**Requirement:** Issue #10 - Requirement 4
**Test Environment:** Dev (haymaker-dev-rg)
**Expected Duration:** 30-45 minutes

---

## Pre-Deployment Validation

### Code Review Checklist

- [ ] **deploy-dev.yml**: Lines 183-225 replaced with Key Vault injection pattern
- [ ] **deploy-dev.yml**: Contains "Inject secrets to Key Vault" step
- [ ] **deploy-dev.yml**: Contains "Wait for RBAC propagation" step (60 seconds)
- [ ] **deploy-dev.yml**: Contains "Verify Key Vault access" step
- [ ] **deploy-dev.yml**: NO direct secret injection via `az functionapp config appsettings set`
- [ ] **.env.example**: Clear "LOCAL DEV ONLY" header added
- [ ] **.env.example**: Secrets section documents Key Vault for production
- [ ] **.env.example**: `AUTO_RUN_ON_STARTUP` variable added
- [ ] **README.md**: Configuration section updated with local vs production
- [ ] **README.md**: Security benefits documented
- [ ] **function-app.bicep**: Key Vault references present (lines 152-164)
- [ ] **main.bicep**: RBAC role assignment present (line 184)
- [ ] **.gitignore**: Contains `.env` and `.env.local` patterns
- [ ] **ROLLBACK_PROCEDURE_REQ4.md**: Rollback documentation created

### Security Pre-Checks

```bash
# 1. Verify .env not tracked by git
cd /Users/ryan/src/AzureHayMaker/worktrees/feat/issue-10-five-critical-improvements
git status | grep -q ".env" && echo "ERROR: .env is tracked!" || echo "✓ .env not tracked"

# 2. Verify .gitignore coverage
cat .gitignore | grep -E "^\.env$|^\.env\.local$" && echo "✓ .env patterns covered"

# 3. Check for hardcoded secrets in code
git log --all --full-history -- .env
# Should show: "fatal: ambiguous argument '.env': unknown revision or path"

# 4. Verify GitHub Secrets are configured
gh secret list --repo your-org/AzureHayMaker
# Should show: MAIN_SP_CLIENT_SECRET, ANTHROPIC_API_KEY, LOG_ANALYTICS_WORKSPACE_KEY
```

**Pre-Deployment Checklist:**
- [ ] `.env` not tracked by git
- [ ] `.gitignore` properly configured
- [ ] No hardcoded secrets found in code
- [ ] GitHub Secrets configured
- [ ] All code changes reviewed and approved

---

## Deployment Testing

### Step 1: Trigger Deployment

```bash
# Option A: Push to develop branch (automated)
git add .
git commit -m "fix: Implement Requirement 4 - Secret Management Consolidation

- Replace direct secret injection with Key Vault pattern in deploy-dev.yml
- Update .env.example to clarify local vs production usage
- Update README.md configuration documentation
- Add RBAC propagation wait (60 seconds)
- Add Key Vault access verification step

SECURITY FIX: Secrets now stored in Key Vault, not visible in Azure Portal

Closes #10 (Requirement 4)"

git push origin feat/issue-10-five-critical-improvements

# Option B: Manual workflow trigger
gh workflow run deploy-dev.yml --ref feat/issue-10-five-critical-improvements
```

**Deployment Checklist:**
- [ ] Code pushed to repository
- [ ] Workflow triggered successfully
- [ ] Deployment name recorded: `haymaker-dev-YYYYMMDD-HHMMSS`

### Step 2: Monitor Deployment

```bash
# Watch workflow execution
gh run watch

# Or view in browser
gh run view --web
```

**Expected Stages:**
1. ✓ Validate Infrastructure (2-3 min)
2. ✓ Run Tests (3-5 min)
3. ✓ Deploy Infrastructure (5-8 min)
   - Create resource group
   - Deploy Bicep infrastructure
   - Grant Key Vault Secrets Officer role
   - **Inject secrets to Key Vault** ← NEW STEP
   - **Wait for RBAC propagation (60s)** ← NEW STEP
   - **Verify Key Vault access** ← NEW STEP
4. ✓ Deploy Function App (3-5 min)
5. ✓ Run Smoke Tests (1-2 min)

**Deployment Monitoring Checklist:**
- [ ] Validate stage passed
- [ ] Test stage passed
- [ ] Infrastructure deployment started
- [ ] "Inject secrets to Key Vault" step executed
- [ ] "Wait for RBAC propagation" step executed (60s)
- [ ] "Verify Key Vault access" step passed
- [ ] Function App deployment completed
- [ ] Smoke tests passed
- [ ] No errors in workflow logs

### Step 3: Capture Deployment Outputs

```bash
# Get deployment outputs
DEPLOYMENT_NAME="haymaker-dev-YYYYMMDD-HHMMSS"  # From Step 1
RG_NAME="haymaker-dev-rg"

az deployment group show \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RG_NAME" \
  --query "properties.outputs" -o json > deployment-outputs.json

# Extract key values
FUNCTION_APP_NAME=$(jq -r '.functionAppName.value' deployment-outputs.json)
KEY_VAULT_NAME=$(jq -r '.keyVaultName.value' deployment-outputs.json)

echo "Function App: $FUNCTION_APP_NAME"
echo "Key Vault: $KEY_VAULT_NAME"

# Save for later steps
export FUNCTION_APP_NAME
export KEY_VAULT_NAME
export RG_NAME
```

**Outputs Checklist:**
- [ ] Function App name captured: `______________________`
- [ ] Key Vault name captured: `______________________`
- [ ] Resource Group name verified: `haymaker-dev-rg`

---

## Post-Deployment Validation

### Test 1: Verify Secrets in Key Vault

```bash
# List secrets in Key Vault
az keyvault secret list \
  --vault-name "$KEY_VAULT_NAME" \
  --query "[].name" -o tsv

# Expected output:
# main-sp-client-secret
# anthropic-api-key
# log-analytics-workspace-key
```

**Checklist:**
- [ ] Secret `main-sp-client-secret` exists in Key Vault
- [ ] Secret `anthropic-api-key` exists in Key Vault
- [ ] Secret `log-analytics-workspace-key` exists in Key Vault
- [ ] All secrets created successfully

### Test 2: Verify Key Vault References in Function App

```bash
# Get Function App settings
az functionapp config appsettings list \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query "[?contains(name, 'SECRET') || contains(name, 'API_KEY') || contains(name, 'WORKSPACE_KEY')]" -o table

# Expected output (values should be @Microsoft.KeyVault references, NOT actual secrets):
# Name                              Value
# --------------------------------  -----------------------------------------------------------
# MAIN_SP_CLIENT_SECRET            @Microsoft.KeyVault(VaultName=...;SecretName=main-sp-client-secret)
# ANTHROPIC_API_KEY                 @Microsoft.KeyVault(VaultName=...;SecretName=anthropic-api-key)
# LOG_ANALYTICS_WORKSPACE_KEY       @Microsoft.KeyVault(VaultName=...;SecretName=log-analytics-workspace-key)
```

**Critical Security Check:**
- [ ] `MAIN_SP_CLIENT_SECRET` shows `@Microsoft.KeyVault` reference (NOT the actual secret)
- [ ] `ANTHROPIC_API_KEY` shows `@Microsoft.KeyVault` reference (NOT the actual key)
- [ ] `LOG_ANALYTICS_WORKSPACE_KEY` shows `@Microsoft.KeyVault` reference (NOT the actual key)
- [ ] NO secrets visible in plaintext

### Test 3: Verify RBAC Role Assignment

```bash
# Get Function App Managed Identity
FUNCTION_APP_PRINCIPAL_ID=$(az functionapp identity show \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query principalId -o tsv)

echo "Function App Principal ID: $FUNCTION_APP_PRINCIPAL_ID"

# Get Key Vault resource ID
KEY_VAULT_ID=$(az keyvault show \
  --name "$KEY_VAULT_NAME" \
  --query id -o tsv)

# Verify role assignment
az role assignment list \
  --assignee "$FUNCTION_APP_PRINCIPAL_ID" \
  --scope "$KEY_VAULT_ID" \
  --query "[?roleDefinitionName=='Key Vault Secrets User']" -o table

# Expected output:
# Principal                             RoleDefinitionName         Scope
# ------------------------------------  -------------------------  -----------------------------------------------
# <function-app-principal-id>          Key Vault Secrets User     /subscriptions/.../Microsoft.KeyVault/vaults/...
```

**RBAC Checklist:**
- [ ] Function App has Managed Identity enabled
- [ ] Managed Identity Principal ID retrieved successfully
- [ ] Role assignment exists: "Key Vault Secrets User"
- [ ] Scope matches Key Vault resource ID
- [ ] Principal ID matches Function App identity

### Test 4: Verify Function App Runtime Access

```bash
# Restart Function App to force secret resolution
echo "Restarting Function App to test Key Vault access..."
az functionapp restart \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME"

# Wait for restart
echo "Waiting 30 seconds for Function App to restart..."
sleep 30

# Check Function App state
az functionapp show \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query "state" -o tsv

# Should show: Running
```

**Runtime Checklist:**
- [ ] Function App restarted successfully
- [ ] Function App state: `Running`
- [ ] No restart errors

### Test 5: Check Function App Logs for Key Vault Access

```bash
# Tail Function App logs (watch for errors)
az functionapp log tail \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  | grep -i "keyvault\|secret\|access\|denied\|error" --color=always

# Expected: No errors related to Key Vault access
# Look for successful startup messages
```

**Log Analysis Checklist:**
- [ ] No "KeyVault access denied" errors
- [ ] No "403 Forbidden" errors
- [ ] No "Secret not found" errors
- [ ] Function App started successfully
- [ ] Orchestrator initialized without errors

### Test 6: Azure Portal Validation (Security Critical)

**Manual Steps:**

1. Open Azure Portal: https://portal.azure.com
2. Navigate to: Resource Groups → `haymaker-dev-rg` → Function App (`$FUNCTION_APP_NAME`)
3. Go to: Configuration → Application Settings
4. Locate these settings:
   - `MAIN_SP_CLIENT_SECRET`
   - `ANTHROPIC_API_KEY`
   - `LOG_ANALYTICS_WORKSPACE_KEY`

**Expected Values (MUST show Key Vault references):**
```
@Microsoft.KeyVault(VaultName=haymaker-dev-kv-xxxxx;SecretName=main-sp-client-secret)
@Microsoft.KeyVault(VaultName=haymaker-dev-kv-xxxxx;SecretName=anthropic-api-key)
@Microsoft.KeyVault(VaultName=haymaker-dev-kv-xxxxx;SecretName=log-analytics-workspace-key)
```

**Portal Checklist:**
- [ ] Navigated to Function App Configuration
- [ ] `MAIN_SP_CLIENT_SECRET` shows Key Vault reference (NOT plaintext)
- [ ] `ANTHROPIC_API_KEY` shows Key Vault reference (NOT plaintext)
- [ ] `LOG_ANALYTICS_WORKSPACE_KEY` shows Key Vault reference (NOT plaintext)
- [ ] Screenshot captured for documentation
- [ ] **CRITICAL:** NO secrets visible in plaintext in Azure Portal

### Test 7: GitHub Actions Log Masking

```bash
# View workflow run logs
gh run view --log | grep -i "secret\|api.*key\|workspace.*key" --color=always

# Expected: All secret values should be masked with ***
# GitHub automatically masks secrets from repository secrets
```

**Log Masking Checklist:**
- [ ] Secrets masked in workflow logs (shown as `***`)
- [ ] No actual secret values visible in logs
- [ ] Key Vault secret names visible (acceptable)
- [ ] Key Vault URIs visible (acceptable)

### Test 8: Integration Test - Orchestrator Execution

```bash
# Check if orchestrator is running
az functionapp function list \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  --query "[].{Name:name, Status:properties.config.disabled}" -o table

# Verify timer trigger function exists and is enabled
```

**Integration Checklist:**
- [ ] Orchestrator function exists
- [ ] Timer trigger enabled (not disabled)
- [ ] Function can access secrets (check logs for successful API calls)
- [ ] No runtime errors related to missing secrets

### Test 9: Secret Rotation Test

```bash
# Update a secret in Key Vault
echo "Testing secret rotation..."
az keyvault secret set \
  --vault-name "$KEY_VAULT_NAME" \
  --name anthropic-api-key \
  --value "test-rotated-key-$(date +%s)" \
  --output none

# Restart Function App to pick up new secret
az functionapp restart \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME"

# Wait for restart
sleep 30

# Check logs for successful restart
az functionapp log tail \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RG_NAME" \
  | head -20

# Restore original secret (from GitHub Secrets)
# az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name anthropic-api-key --value "$ORIGINAL_KEY"
```

**Secret Rotation Checklist:**
- [ ] Secret updated in Key Vault
- [ ] Function App restarted
- [ ] New secret picked up automatically
- [ ] No manual code changes required
- [ ] Original secret restored (if testing complete)

---

## Security Validation

### Security Audit Checklist

```bash
# 1. Verify no secrets in git history
git log --all --full-history --source --full-diff -- .env | wc -l
# Expected: 0 (or error if .env never existed)

# 2. Verify no secrets in current code
grep -r "sk-ant-api03" . --exclude-dir=.git --exclude-dir=node_modules
# Expected: No matches (only .env.example with placeholder)

# 3. Verify GitHub Actions log masking
# Already tested in Test 7

# 4. Verify least privilege RBAC
az role assignment list \
  --assignee "$FUNCTION_APP_PRINCIPAL_ID" \
  --all \
  --query "[?roleDefinitionName=='Key Vault Administrator' || roleDefinitionName=='Key Vault Secrets Officer']" -o table
# Expected: Empty table (Function App should NOT have admin roles)

# 5. Verify audit logging enabled
az monitor diagnostic-settings list \
  --resource "$KEY_VAULT_ID" \
  --query "[].{Name:name, Enabled:enabled}" -o table
# Expected: At least one diagnostic setting enabled for audit logs
```

**Security Audit Checklist:**
- [ ] No secrets in git history
- [ ] No hardcoded secrets in code
- [ ] GitHub Actions masks secrets properly
- [ ] Function App has least privilege (Secrets User only, NOT Admin)
- [ ] Key Vault audit logging enabled
- [ ] All secrets stored in Key Vault
- [ ] No secrets visible in Azure Portal
- [ ] Secret rotation tested and working

---

## Performance Validation

### RBAC Propagation Time Test

```bash
# Record deployment timestamps from workflow logs
# Expected:
# - RBAC assignment: [timestamp]
# - Wait start: [timestamp + 0s]
# - Wait end: [timestamp + 60s]
# - Verification: [timestamp + 61s]

# Calculate actual propagation time
# Should be <= 60 seconds for successful deployment
```

**Performance Checklist:**
- [ ] RBAC propagation time recorded: `______ seconds`
- [ ] Wait time adequate (60 seconds)
- [ ] Key Vault access successful after wait
- [ ] No additional delays required

---

## Acceptance Criteria Validation

Final checklist based on IMPLEMENTATION_SPEC.md requirements:

- [ ] `.env` file not tracked by git
- [ ] `.env` file in .gitignore
- [ ] `.env.example` clearly documents local development usage
- [ ] README.md configuration section updated (local vs production)
- [ ] GitHub Actions deploys secrets to Key Vault (not direct injection)
- [ ] Function App uses Key Vault references (@Microsoft.KeyVault syntax)
- [ ] Function App Managed Identity has "Key Vault Secrets User" role
- [ ] Function App successfully reads secrets from Key Vault at runtime
- [ ] Secrets NOT visible in Azure Portal Function App settings
- [ ] No secrets visible in GitHub Actions logs
- [ ] Secret rotation works without code changes
- [ ] RBAC properly configured with 60-second wait for propagation
- [ ] Rollback procedure documented (ROLLBACK_PROCEDURE_REQ4.md)
- [ ] Testing checklist created (this document)
- [ ] All tests passed successfully

---

## Test Results Summary

**Test Date:** __________________
**Tester:** __________________
**Environment:** Dev (haymaker-dev-rg)
**Function App Name:** __________________
**Key Vault Name:** __________________

### Test Results

| Test | Status | Notes |
|------|--------|-------|
| 1. Secrets in Key Vault | ⬜ Pass / ⬜ Fail | |
| 2. Key Vault References | ⬜ Pass / ⬜ Fail | |
| 3. RBAC Role Assignment | ⬜ Pass / ⬜ Fail | |
| 4. Runtime Access | ⬜ Pass / ⬜ Fail | |
| 5. Logs - No Errors | ⬜ Pass / ⬜ Fail | |
| 6. Portal - No Plaintext | ⬜ Pass / ⬜ Fail | |
| 7. Log Masking | ⬜ Pass / ⬜ Fail | |
| 8. Integration Test | ⬜ Pass / ⬜ Fail | |
| 9. Secret Rotation | ⬜ Pass / ⬜ Fail | |
| Security Audit | ⬜ Pass / ⬜ Fail | |

**Overall Status:** ⬜ All Pass / ⬜ Failed (see notes)

**Rollback Required:** ⬜ Yes / ⬜ No

**Next Steps:**
- ⬜ Merge to main branch
- ⬜ Deploy to staging
- ⬜ Update documentation
- ⬜ Close Issue #10 (Requirement 4)
- ⬜ Trigger rollback (if failed)

---

**Last Updated:** 2025-11-17
**Document Version:** 1.0
**Status:** Active
