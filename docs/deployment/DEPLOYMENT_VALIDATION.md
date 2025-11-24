# Deployment Validation Guide

**How to verify everything is working correctly**

---

## Quick Validation (5 minutes)

```bash
# Run all validation scripts
./scripts/health-check.sh
./scripts/verify-security-fix.sh
./scripts/check-infrastructure.sh
```

**Expected Results**:
- Key Vault: Succeeded ✅
- Service Bus: Succeeded ✅
- Security: Key Vault references ✅

---

## Detailed Validation

### 1. Infrastructure Health
```bash
./scripts/health-check.sh
```

**Checks**:
- Key Vault provisioning state
- Secret count
- Service Bus status
- Function App state
- API endpoint response

### 2. Security Verification
```bash
./scripts/verify-security-fix.sh
```

**Validates**:
- Secrets use Key Vault references
- No secrets visible in Portal
- RBAC configured correctly

### 3. Resource Inventory
```bash
./scripts/list-all-resources.sh
```

**Reviews**:
- All deployed resources
- Resource types
- Locations
- Identifies duplicates for cleanup

### 4. Cost Estimation
```bash
./scripts/estimate-costs.sh
```

**Calculates**:
- Monthly spend by resource type
- Total monthly cost
- Cleanup savings opportunity

---

## Manual Validation Steps

### Key Vault Secrets
```bash
az keyvault secret list \
  --vault-name haymaker-dev-yow3ex-kv \
  --query "[].name" -o table
```

**Expected Secrets**:
- main-sp-client-secret
- anthropic-api-key
- log-analytics-workspace-key

### Function App Configuration
```bash
az functionapp config appsettings list \
  --name haymaker-dev-yow3ex-func \
  --resource-group haymaker-dev-rg \
  --query "[?starts_with(name, 'ANTHROPIC') || starts_with(name, 'MAIN_SP')].{name:name, value:value}" \
  -o table
```

**Expected**: `@Microsoft.KeyVault(...)` references, NOT actual values

### Service Bus Topics
```bash
az servicebus topic list \
  --namespace-name haymaker-dev-yow3ex-bus \
  --resource-group haymaker-dev-rg \
  -o table
```

**Expected**: `agent-logs` topic exists

---

## CI/CD Validation

### Check Latest Deployment
```bash
gh run list --limit 5
```

**Look for**:
- Deploy to Development workflow
- Success status
- No failures in critical jobs

### View Deployment Logs
```bash
gh run view <run-id> --log
```

---

## Post-Deployment Checklist

- [ ] Key Vault deployed and accessible
- [ ] Secrets stored correctly (no plaintext)
- [ ] Service Bus topics created
- [ ] Storage accounts configured
- [ ] Function App running (or VM if migrated)
- [ ] RBAC roles assigned
- [ ] Network security configured
- [ ] Monitoring enabled
- [ ] Cost within budget

---

## Troubleshooting

**If validation fails**: See `TROUBLESHOOTING.md`

**Common issues**:
- Key Vault firewall blocking access
- RBAC propagation delays (wait 90s)
- Function App memory issues (VM migration needed)
- Missing environment variables

---

## Success Criteria

**Minimum**:
- ✅ Key Vault with secrets
- ✅ Service Bus operational
- ✅ Storage accessible
- ✅ No security warnings

**Complete**:
- ✅ All above +
- ✅ Orchestrator running (VM or Function App)
- ✅ Agents deploying successfully
- ✅ Logs flowing to storage
- ✅ Cost optimized

---

**Run validation after any deployment changes!**
