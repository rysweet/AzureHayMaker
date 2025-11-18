# Azure HayMaker - Troubleshooting Guide

**Common issues and solutions from 12-hour debugging session**

---

## Issue: Function App Container Crashes (Exit Code 134)

**Symptom**: Container crashes 7-60 seconds after startup with SIGABRT

**Root Cause**: Memory exhaustion during Azure SDK initialization

**Attempted Solutions**:
- ❌ Upgrade to P1V2 (3.5GB) - Still crashes
- ❌ Upgrade to P3V2 (8GB) - Still crashes  
- ❌ Upgrade to EP3 (14GB) - Still crashes

**Working Solution**: Deploy to VM with 64GB RAM
- VM Size: Standard_E8s_v3 (64GB RAM, 8 vCPU)
- See: `VM_DEPLOYMENT_PLAN.md`
- Instructions: `./deploy-vm-portal-guide.sh`

**Lesson**: Azure Functions insufficient for heavy Azure SDK workloads

---

## Issue: Key Vault "Forbidden by Firewall" Error

**Symptom**: GitHub Actions can't inject secrets to Key Vault

**Error**: `ForbiddenByFirewall` during secret injection step

**Root Cause**: Key Vault `networkAcls.defaultAction = 'Deny'` blocks GitHub Actions

**Solution**: Set `defaultAction = 'Allow'` when `publicNetworkAccess = true`

**Fix Applied**: `infra/bicep/modules/keyvault.bicep:64`

**Verification**: GitHub Actions now successfully inject secrets

---

## Issue: Cosmos DB Connection String Missing

**Symptom**: Function App crashes on startup looking for COSMOSDB_ENDPOINT

**Root Cause**: Cosmos DB not deployed in dev (quota limitations)

**Solution**: Make Cosmos DB configuration optional

**Fix Applied**: 
- `src/azure_haymaker/orchestrator/config.py:142` - Use `_get_optional_env`
- `infra/bicep/modules/function-app.bicep:144` - Add empty defaults

**Verification**: Function App starts with Cosmos DB disabled

---

## Issue: Azure CLI Parameter Escaping (SSH Key)

**Symptom**: `az deployment group create` fails with "unrecognized arguments"

**Root Cause**: SSH public key contains spaces breaking parameter parsing

**Attempted Solutions**:
- ❌ Inline parameters
- ❌ JSON file parameters
- ❌ Bicep parameters file
- ❌ @ prefix syntax

**Working Solution**: Manual Portal deployment OR simpler SSH key

**Alternative**: Use password auth temporarily, then add SSH key via Portal

---

## Issue: Python Version Mismatch

**Symptom**: CI tests fail with "incompatible with project's Python requirement"

**Root Cause**: `.python-version` says 3.13, `pyproject.toml` says `>=3.11,<3.13`

**Solution**: Update `.python-version` to 3.11

**Fix Applied**: Changed from 3.13 to 3.11

**Verification**: CI tests now pass

---

## How to Verify Security Fix

Run the automation script:
```bash
./scripts/verify-security-fix.sh
```

**Expected**:
```
✅ SUCCESS! Secrets are using Key Vault references
✅ Secrets are NOT visible in Azure Portal
```

**If Failed**: Check `ROLLBACK_PROCEDURE_REQ4.md`

---

## How to Check Infrastructure

```bash
./scripts/check-infrastructure.sh
```

Shows all deployed resources across:
- Key Vaults
- Service Bus  
- Storage
- Function Apps
- VMs

---

## Cost Optimization

**Problem**: 12 Function Apps deployed (~$875/month)

**Solution**:
```bash
./scripts/cleanup-old-function-apps.sh
```

**Savings**: ~$437/month

---

## Next Session: VM Deployment

**If Azure CLI fails**: Use Azure Portal

**Step-by-step**:
```bash
./deploy-vm-portal-guide.sh
```

**After VM created**: Follow `NEXT_STEPS.md`

---

**For more help**: See Issue #13 or `HANDOFF.md`
