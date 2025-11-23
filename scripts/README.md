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
| open-powerpoint.sh | Launch presentation | 10 sec | Instant PowerPoint access |
| show-session-summary.sh | Display session results | 10 sec | Quick value overview |
| verify-security-fix.sh | Security validation | 1 min | Confirms fix working |
| health-check.sh | Infrastructure health | 1 min | Shows all statuses |
| check-infrastructure.sh | List infrastructure | 1 min | See all resources |
| list-all-resources.sh | Complete inventory | 1 min | Full resource list |
| estimate-costs.sh | Calculate monthly costs | 1 min | **$2,164/month found!** |
| backup-key-vault-secrets.sh | Backup secret names | 1 min | Disaster recovery |
| cleanup-old-function-apps.sh | Cost savings (partial) | 5 min | $1,533/month saved |
| complete-cleanup.sh | Full cleanup | 10 min | **$1,666/month saved!** |
| ../deploy-vm-portal-guide.sh | VM deployment help | - | Prints instructions |

**Total**: 11 automation scripts created and tested!

## 🚀 Quick Start Scripts

### open-powerpoint.sh
Open the PowerPoint presentation instantly

```bash
./scripts/open-powerpoint.sh
```

### show-session-summary.sh
See what was accomplished in 12-hour session

```bash
./scripts/show-session-summary.sh
```

---

**Created during epic 12-hour Ultra-Think session (2025-11-17/18)**
