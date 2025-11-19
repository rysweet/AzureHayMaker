# Pre-Deployment Checklist

**Use this before any deployment**

---

## ✅ Before Deploying

### Configuration
- [ ] .env file configured (local)
- [ ] GitHub Secrets set (CI/CD)
- [ ] Azure subscription selected
- [ ] Resource group created
- [ ] Service principal created with correct roles

### Code Quality
- [ ] All tests passing (`uv run pytest`)
- [ ] Linting clean (`uv run ruff check .`)
- [ ] Type checking clean (`uv run pyright`)
- [ ] Security scan clean
- [ ] No TODO/FIXME in production code

### Documentation
- [ ] README updated
- [ ] CHANGELOG updated
- [ ] API docs current
- [ ] Architecture diagrams reflect changes

### Infrastructure
- [ ] Bicep templates validate (`az bicep build`)
- [ ] Parameters files correct
- [ ] Resource names unique
- [ ] Tags applied consistently

### Security
- [ ] No secrets in code
- [ ] Key Vault configured
- [ ] RBAC roles assigned
- [ ] Network security reviewed

### Cost
- [ ] Cost estimate reviewed
- [ ] Budget alerts configured
- [ ] Cleanup plan exists
- [ ] Resource sizing appropriate

---

## ✅ During Deployment

- [ ] Monitor deployment logs
- [ ] Check for errors
- [ ] Verify each stage completes
- [ ] Note any warnings

---

## ✅ After Deployment

### Validation
- [ ] Run `./scripts/health-check.sh`
- [ ] Run `./scripts/verify-security-fix.sh`
- [ ] Check infrastructure: `./scripts/check-infrastructure.sh`
- [ ] Estimate costs: `./scripts/estimate-costs.sh`

### Testing
- [ ] Smoke tests pass
- [ ] Integration tests pass
- [ ] End-to-end validation
- [ ] Performance acceptable

### Documentation
- [ ] Update DEPLOYMENT_STATUS.md
- [ ] Document any issues encountered
- [ ] Update troubleshooting guide if needed

---

**Use this checklist for every deployment!**
