# Azure HayMaker - Utility Scripts

**Essential automation scripts for infrastructure management and operations**

---

## 📦 Release Management

### release.sh
Create tagged releases with semantic versioning

```bash
./scripts/release.sh 1.0.0           # Create release v1.0.0
./scripts/release.sh 1.0.0 --dry-run # Preview without making changes
```

**What it does**:
- Validates semantic version format
- Ensures clean main branch
- Updates README with version badges
- Creates annotated git tag
- Pushes changes and tag to origin

---

## 🧹 Cleanup & Maintenance

### cleanup-old-function-apps.sh
Remove orphaned Function Apps to save costs

```bash
./scripts/cleanup-old-function-apps.sh
```

### complete-cleanup.sh
Full cleanup of all resources

```bash
./scripts/complete-cleanup.sh
```

### resource-cleanup.py
Python-based resource cleanup utility

```bash
./scripts/resource-cleanup.py
```

---

## 🔒 Security & Configuration

### verify-security-fix.sh
Verify secrets are stored in Key Vault (not visible in Portal)

```bash
./scripts/verify-security-fix.sh
```

**What it checks**:
- Function App settings use `@Microsoft.KeyVault(...)` references
- Secrets are NOT stored directly
- Security fix is working correctly

### backup-key-vault-secrets.sh
Backup Key Vault secret names for disaster recovery

```bash
./scripts/backup-key-vault-secrets.sh
```

### setup-oidc.sh
Configure OIDC authentication

```bash
./scripts/setup-oidc.sh
```

---

## 🚀 Deployment & Infrastructure

### deploy_vm_orchestrator.sh
Deploy VM orchestrator infrastructure

```bash
./scripts/deploy_vm_orchestrator.sh
```

### setup_vm_orchestrator.sh
Setup VM orchestrator environment

```bash
./scripts/setup_vm_orchestrator.sh
```

### trigger_deploy.sh
Trigger deployment workflows

```bash
./scripts/trigger_deploy.sh
```

---

## 📊 Monitoring & Diagnostics

### health-check.sh
Infrastructure health check

```bash
./scripts/health-check.sh
```

### check-infrastructure.sh
List infrastructure resources

```bash
./scripts/check-infrastructure.sh
```

### list-all-resources.sh
Complete inventory of all resources

```bash
./scripts/list-all-resources.sh
```

### estimate-costs.sh
Calculate monthly infrastructure costs

```bash
./scripts/estimate-costs.sh
```

---

## 🛠️ Development Tools

### generate-readme-badges.sh
Generate badges for README

```bash
./scripts/generate-readme-badges.sh
```

---

## 📊 All Scripts

| Script | Purpose | Category |
|--------|---------|----------|
| release.sh | Create tagged releases | Release Management |
| cleanup-old-function-apps.sh | Remove orphaned Function Apps | Cleanup |
| complete-cleanup.sh | Full resource cleanup | Cleanup |
| resource-cleanup.py | Python cleanup utility | Cleanup |
| verify-security-fix.sh | Security validation | Security |
| backup-key-vault-secrets.sh | Backup secret names | Security |
| setup-oidc.sh | Configure OIDC | Security |
| deploy_vm_orchestrator.sh | Deploy VM orchestrator | Deployment |
| setup_vm_orchestrator.sh | Setup VM environment | Deployment |
| trigger_deploy.sh | Trigger deployments | Deployment |
| health-check.sh | Infrastructure health | Monitoring |
| check-infrastructure.sh | List infrastructure | Monitoring |
| list-all-resources.sh | Complete inventory | Monitoring |
| estimate-costs.sh | Calculate costs | Monitoring |
| generate-readme-badges.sh | Generate badges | Development |

**Total**: 15 operational scripts
