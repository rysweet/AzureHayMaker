# VM Deployment Design - Issue #12

## Executive Summary

Deploy existing 128GB VM infrastructure for Azure HayMaker orchestrator to replace Function App which crashes due to memory exhaustion (SIGABRT exit code 134).

## Problem Statement

**Root Cause**: Azure Functions (Elastic Premium EP3) has 14GB RAM limit. Orchestrator + Azure SDK requires 60-70GB during initialization, causing crashes.

**Solution**: Migrate to dedicated 128GB VM (Standard_E16s_v3) with full memory control.

## Design Decisions

### 1. Infrastructure Approach

**Decision**: Use existing Bicep templates (already written and validated)

**Rationale**:
- Infrastructure code complete in `/infra/bicep/main-vm.bicep`
- VM module complete in `/infra/bicep/modules/orchestrator-vm.bicep`
- GitHub Actions workflow exists and tested
- Follows IaC best practices

**Alternatives Considered**:
- Manual Portal deployment → Rejected (not reproducible)
- Terraform → Rejected (would require rewrite, Bicep already works)

### 2. Deployment Method

**Decision**: GitHub Actions workflow (`.github/workflows/deploy-vm-orchestrator.yml`)

**Rationale**:
- Automated and reproducible
- OIDC authentication (secure, no stored credentials)
- Built-in validation step
- Audit trail in GitHub Actions logs

**Manual Alternative**: Document Azure CLI commands for emergency rollback

### 3. VM Sizing

**Decision**: Standard_E16s_v3 (128GB RAM, 16 vCPU) - already configured

**Rationale**:
- Exceeds 60-70GB requirement with headroom
- Memory-optimized series (E-series)
- Captain's preferred specification (from Issue #15)
- Cost: ~$876/month vs $875/month for 12 Function Apps

### 4. Migration Strategy

**Decision**: Blue-Green deployment approach

**Steps**:
1. Deploy new VM (green) - Function Apps stay running (blue)
2. Setup and test orchestrator on VM
3. Cutover: Update DNS/routing to VM
4. Monitor for 24-48 hours
5. Decommission Function Apps only after validation

**Zero Downtime**: Function Apps continue serving during VM setup

**Rollback**: Keep Function Apps running until VM proven stable

### 5. Security

**Decisions**:
- System-assigned Managed Identity for VM
- SSH key authentication only (no passwords)
- Key Vault Secrets User role for secret access
- NSG allows only HTTPS (443) and SSH (22)

### 6. Monitoring & Observability

**Decisions**:
- Log Analytics workspace for centralized logging
- VM diagnostics enabled
- Custom metrics for memory usage
- Alerts for memory > 100GB threshold

## Implementation Components

### Phase 1: Infrastructure Deployment (Step 8)
```bash
# Trigger GitHub Actions workflow
gh workflow run deploy-vm-orchestrator.yml

# Or manual deployment
az deployment group create \
  --resource-group haymaker-dev-rg \
  --template-file infra/bicep/main-vm.bicep \
  --parameters @infra/bicep/parameters/dev.json
```

**Outputs Captured**:
- VM Name
- Public IP Address
- FQDN
- Principal ID (for RBAC)

### Phase 2: VM Setup (Post-deployment)
```bash
# SSH into VM
ssh azureuser@<vm-ip>

# Clone repository
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker

# Install dependencies
uv sync

# Setup systemd service
sudo cp scripts/orchestrator.service /etc/systemd/system/
sudo systemctl enable orchestrator
sudo systemctl start orchestrator
```

### Phase 3: Verification Testing
- Memory usage monitoring (<128GB)
- Orchestrator startup (no SIGABRT)
- Agent deployment test
- Cosmos DB logging verification
- End-to-end orchestration test

### Phase 4: Cutover
- Update service endpoints to VM
- Monitor for 24-48 hours
- Decommission Function Apps when stable

## Rollback Plan

**Scenario 1: Deployment Fails**
```bash
# Delete resource group deployment
az deployment group delete \
  --resource-group haymaker-dev-rg \
  --name <deployment-name>

# Or delete VM resources individually
az vm delete --name <vm-name> --resource-group haymaker-dev-rg --yes
az network vnet delete --name <vnet-name> --resource-group haymaker-dev-rg
# etc.
```
**Impact**: None - Function Apps still running

**Scenario 2: VM Deployed but Orchestrator Fails**
```bash
# Keep VM for debugging
# Continue using Function Apps
# Fix issues and retry
```
**Impact**: None - Function Apps still running

**Scenario 3: Post-Cutover Issues**
```bash
# Revert DNS/routing to Function Apps
# Investigate VM issues
# Fix and re-cutover
```
**Impact**: Brief service interruption during DNS/routing change (<5 min)

## Success Metrics

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| VM Deployment | Success | Azure Portal verification |
| Memory Usage | <128GB | `free -h` on VM |
| Orchestrator Startup | No crashes | `systemctl status orchestrator` |
| Agent Execution | Success | Test orchestration run |
| Logging | Flows to Cosmos | Query Cosmos DB |
| No SIGABRT | Zero occurrences | System logs grep |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Deployment fails | Low | Low | Bicep validated, rollback easy |
| Insufficient memory | Very Low | High | 128GB >> 70GB required |
| SSH access issues | Low | Low | Portal access available |
| Cost overrun | Low | Low | $876/mo is within budget |
| Network issues | Low | Medium | NSG pre-configured |

## Timeline

- **Deployment**: 15-20 minutes (Bicep execution)
- **VM Setup**: 30-45 minutes (orchestrator installation)
- **Testing**: 2-3 hours (comprehensive verification)
- **Cutover**: 30 minutes (DNS/routing update)
- **Monitoring**: 24-48 hours before decommission

**Total Estimated Time**: 1 day (includes monitoring period)

## Dependencies

- Azure subscription access ✓
- GitHub Actions secrets configured ✓
- Bicep templates validated ✓
- SSH key generated ✓

## Next Steps (Implementation Order)

1. Review this design with architect agent
2. Create deployment validation script
3. Execute deployment via GitHub Actions
4. SSH setup and orchestrator installation
5. Comprehensive testing (Issue #13)
6. Cutover and monitoring
7. Decommission Function Apps

## Philosophy Compliance

- **Ruthless Simplicity**: Use existing Bicep, no unnecessary abstraction
- **Zero-BS Implementation**: No stubs - real deployment, real testing
- **Regeneratable**: Bicep ensures infrastructure can be rebuilt
- **Working Code Only**: Every script must execute successfully

## Related Issues

- **Issue #12**: This design (deployment)
- **Issue #13**: Post-deployment testing and verification
- **Issue #15**: VM sizing (already 128GB in code)
- **Issue #10**: Parent tracking issue

---

**Status**: Design Complete - Ready for Architect Review
**Next**: Architect agent validation and refinement
