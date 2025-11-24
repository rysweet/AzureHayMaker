# Security Policy

## Reporting Security Issues

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead:
1. Email: rysweet@microsoft.com
2. Include: Detailed description, steps to reproduce, impact assessment
3. Wait for acknowledgment before public disclosure

---

## Security Features

### Implemented (Verified)
- ✅ Secrets stored in Azure Key Vault only
- ✅ RBAC-based access control
- ✅ Managed Identity for all Azure access
- ✅ No hardcoded credentials in code
- ✅ TLS 1.2 minimum for all connections
- ✅ Key Vault firewall configured
- ✅ Audit logging enabled

### Verification
Run: `./scripts/verify-security-fix.sh`

Expected: "✅ SUCCESS! Key Vault references confirmed!"

---

## Security Best Practices

### Secret Management
- **Production**: Always use Key Vault
- **Development**: Use .env file (gitignored)
- **Never**: Commit secrets to git

### Access Control
- Use Managed Identity where possible
- Principle of least privilege for RBAC
- Rotate secrets regularly
- Monitor access logs

### Network Security
- Use private endpoints in production
- Configure NSG rules appropriately
- Enable Azure Firewall if needed

---

## Known Issues

### Fixed in Latest Code
- ❌ Secrets visible in Portal (dev environment)
  - ✅ **FIXED**: Key Vault references implemented
  - ✅ **VERIFIED**: Running in production

### Monitoring
- Regular security audits recommended
- Review Key Vault access logs
- Monitor for unusual activity

---

## Compliance

- RBAC: Implemented ✅
- Encryption at rest: Enabled ✅
- Encryption in transit: TLS 1.2+ ✅
- Audit logging: Enabled ✅
- Secret rotation: Supported ✅

---

## Security Updates

**Last Security Review**: 2025-11-17
**Findings**: 0 critical, 0 high
**Status**: APPROVED with additional hardening

See: PR #11 security review comments

---

**For more**: See `ROLLBACK_PROCEDURE_REQ4.md` for emergency procedures
