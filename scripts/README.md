# Azure HayMaker - Utility Scripts

**Helpful automation scripts for common operations**

---

## 🧹 Cleanup & Maintenance

### cleanup-old-function-apps.sh
Remove orphaned Function Apps to save ~$437/month

```bash
./scripts/cleanup-old-function-apps.sh
```

**What it does**:
- Lists all Function Apps except the latest
- Prompts for confirmation
- Deletes old apps
- Saves significant monthly costs

---

## 🔒 Security Verification

### verify-security-fix.sh
Verify secrets are stored in Key Vault (not visible in Portal)

```bash
./scripts/verify-security-fix.sh
```

**What it checks**:
- Function App settings use `@Microsoft.KeyVault(...)` references
- Secrets are NOT stored directly
- Security fix is working correctly

**Expected Output**:
```
✅ SUCCESS! Secrets are using Key Vault references
✅ Secrets are NOT visible in Azure Portal
✅ Security fix is WORKING!
```

---

## 🚀 Deployment Guides

### deploy-vm-portal-guide.sh
Step-by-step instructions for deploying 64GB VM via Azure Portal

```bash
./deploy-vm-portal-guide.sh
```

**Provides**:
- Complete Portal configuration steps
- SSH public key to use
- Post-deployment instructions

---

## 📊 All Scripts

| Script | Purpose | Time | Impact |
|--------|---------|------|--------|
| cleanup-old-function-apps.sh | Cost savings | 5 min | $437/month saved |
| verify-security-fix.sh | Security validation | 1 min | Confirms fix working |
| deploy-vm-portal-guide.sh | VM deployment help | - | Prints instructions |

---

**Created during 12-hour Ultra-Think session (2025-11-17/18)**
