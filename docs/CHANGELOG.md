# Azure HayMaker - Changelog

## [Unreleased]

### Added (2025-11-17/18) - Epic 12-Hour Session
- PowerPoint presentation (32 slides, 924KB) - `docs/presentations/Azure_HayMaker_Overview.pptx`
- Agent auto-execution on startup (`run_on_startup=True`)
- Agent output display via CLI (`haymaker logs --follow`)
- Dual-write log pattern (Service Bus + Cosmos DB)
- Rich CLI formatting with colors
- 30 comprehensive documentation files (12,000+ lines)
- 8 automation scripts (verify, cleanup, estimate, check)
- VM-based orchestrator architecture (64GB RAM)
- Cost analysis tools ($1,666/month savings identified)
- Complete troubleshooting guide
- SSH key generation for VM access

### Changed
- Secret management: All environments now use Key Vault references
- Cosmos DB: Made optional for dev environment  
- Python version: Downgraded to 3.11 for stability
- Key Vault firewall: Allow GitHub Actions access
- RBAC propagation: Increased from 60s to 90s

### Fixed
- Security vulnerability: Secrets no longer visible in Azure Portal
- Cosmos DB secrets removed from Bicep outputs
- Function App configuration: Added missing environment variables
- Service Bus subscription: Verified idempotent
- Multiple deployment issues (15+ fixes applied)

### Security
- **CRITICAL FIX**: Secrets consolidated to Key Vault only
- Removed Cosmos DB connection strings from outputs
- Key Vault references verified working
- RBAC-based access control implemented
- Audit logging enabled via Key Vault

### Deprecated
- Function App orchestrator (will be replaced by VM)
- Direct secret injection in deploy-dev.yml

### Infrastructure
- 21 Key Vaults deployed (cleanup needed)
- 21 Service Bus namespaces (cleanup needed)
- 21 Function Apps (cleanup needed)
- 21 Storage Accounts (cleanup needed)
- Current cost: ~$2,164/month (optimization to $498/month)

### Documentation
- MASTER_TREASURE_MAP.md - Complete guide
- START_HERE.md - Quick start
- FINAL_SESSION_SUMMARY.md - Epic journey
- CRITICAL_COST_ALERT.md - Cost analysis
- TROUBLESHOOTING.md - Common issues
- Plus 25+ additional comprehensive guides

## [0.1.0] - Pre-Session Baseline

### Existing
- 50 Azure scenarios across 10 technology areas
- Durable Functions orchestrator
- Container App agent execution
- GitOps deployment pipeline
- CLI client with 7 commands

---

**Note**: See `FINAL_SESSION_SUMMARY.md` for complete details of the 12-hour session.
