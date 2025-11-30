# Quick Issue-to-Spec Mapping Guide

**Fast reference: Which spec goes with which issue?**

**Last Updated**: 2025-11-30

---

## P0-Critical Enhancements

### Issue #124: SIEM Telemetry Export Pipeline

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/124

**Implementation Spec**: [`specs/SIEM_TELEMETRY_EXPORT.md`](../specs/SIEM_TELEMETRY_EXPORT.md) (80KB)

**Starter Code**: [`examples/siem_export_starter.py`](../examples/siem_export_starter.py)

**Key Files to Modify**:
- `src/azure_haymaker/knowledge_worker/telemetry/exporter.py` (NEW)
- `src/azure_haymaker/knowledge_worker/telemetry/normalizer.py` (NEW)
- `src/azure_haymaker/knowledge_worker/telemetry/connectors/` (NEW directory)

**Tests Required**:
- `tests/unit/test_siem_export.py` (NEW)
- `tests/unit/test_event_normalizer.py` (NEW)
- `tests/integration/test_siem_connectors.py` (NEW)

**Dependencies**: PR #119 (must merge first)

**Timeline**: 2.5-3.5 weeks

**ROI**: 120% | **Payback**: 5.4 months

---

### Issue #125: Windows VM Security Hardening

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/125

**Implementation Spec**: [`specs/WINDOWS_VM_SECURITY_HARDENING.md`](../specs/WINDOWS_VM_SECURITY_HARDENING.md) (19KB)

**Starter Code**: [`examples/windows_vm_security_starter.py`](../examples/windows_vm_security_starter.py)

**Key Files to Modify**:
- `src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py` (EXISTING - security fixes)

**Tests Required**:
- `tests/security/test_windows_vm_security.py` (NEW)
- Update: `tests/unit/test_windows_vm.py` (EXISTING)

**Dependencies**: None (can start immediately)

**Timeline**: 1-2 weeks

**ROI**: 1,165% | **Payback**: Immediate

**Blocking**: PR #121, PR #123 (this issue blocks them)

---

## P1-High Enhancements

### Issue #126: Multi-Tenant Resource Isolation

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/126

**Implementation Spec**: Documented in [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Full spec TBD

**Key Files to Modify**:
- `src/orchestrator_server.py` (tenant context middleware)
- `src/azure_haymaker/models/` (add tenant_id fields)
- `src/azure_haymaker/orchestrator/` (tenant-aware scheduling)

**Tests Required**:
- `tests/unit/test_multi_tenant.py` (NEW)
- `tests/integration/test_tenant_isolation.py` (NEW)
- `tests/security/test_tenant_isolation.py` (NEW)

**Dependencies**: Architecture review required BEFORE implementation

**Timeline**: 6 weeks

**ROI**: 233% | **Payback**: 3.6 months

---

### Issue #127: Distributed Tracing and Correlation IDs

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/127

**Implementation Spec**: Documented in [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md)

**Key Files to Modify**:
- `src/orchestrator_server.py` (add OpenTelemetry)
- `src/azure_haymaker/agent_base.py` (trace context propagation)
- Requirements: Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-azure-monitor`

**Tests Required**:
- `tests/unit/test_tracing.py` (NEW)
- `tests/integration/test_distributed_traces.py` (NEW)

**Dependencies**: Benefits from #124 (optional)

**Timeline**: 2 weeks

**ROI**: 36% | **Payback**: 8.8 months

---

### Issue #128: Cost Budget Enforcement and Alerts

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/128

**Implementation Spec**: Documented in [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md)

**Key Files to Modify**:
- `src/azure_haymaker/orchestrator/budget_enforcer.py` (NEW)
- `src/orchestrator_server.py` (integrate budget checks)

**Tests Required**:
- `tests/unit/test_budget_enforcer.py` (NEW)
- `tests/integration/test_cost_enforcement.py` (NEW)

**Dependencies**: None

**Timeline**: 1.5 weeks

**ROI**: 184% | **Payback**: 4.2 months

---

### Issue #129: Agent Health Checks and Circuit Breakers

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/129

**Implementation Spec**: Documented in [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md)

**Key Files to Modify**:
- `src/azure_haymaker/agent_base.py` (add /health endpoint)
- `src/azure_haymaker/orchestrator/circuit_breaker.py` (NEW)
- `src/azure_haymaker/orchestrator/health_monitor.py` (NEW)

**Tests Required**:
- `tests/unit/test_circuit_breaker.py` (NEW)
- `tests/unit/test_health_monitor.py` (NEW)
- `tests/integration/test_agent_health.py` (NEW)

**Dependencies**: None

**Timeline**: 2 weeks

---

## P2-Medium Enhancements

### Issue #130: Local Development Mode

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/130

**Implementation Spec**: Documented in [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md)

**Key Files to Create**:
- `src/azure_haymaker/mocks/` (NEW directory)
- `docker-compose.local.yml` (NEW)
- `.env.local.example` (NEW)

**Timeline**: 4 weeks

---

### Issue #131: GitHub Actions Custom Agent

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/131

**Implementation Spec**: Documented in [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md)

**Key Files to Create**:
- `action.yml` (GitHub Action definition)
- `src/github_action/` (NEW directory)

**Timeline**: 2 weeks

---

### Issue #132: Analytics Dashboard with Real-Time Metrics

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/132

**Implementation Spec**: Documented in [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md)

**Key Files to Create**:
- `dashboard/` (NEW directory with React app)
- `src/orchestrator_server.py` (add /ws/metrics WebSocket endpoint)

**Dependencies**: #124 (SIEM export), #127 (Distributed Tracing)

**Timeline**: 3 weeks

---

### Issue #133: Scenario Testing Framework

**GitHub Issue**: https://github.com/rysweet/AzureHayMaker/issues/133

**Implementation Spec**: Documented in [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md)

**Key Files to Create**:
- `tests/scenarios/` (NEW directory)
- `tests/scenarios/base.py` (ScenarioTestCase base class)

**Timeline**: 4 weeks

---

## Quick Start Guide Per Enhancement

### To Start Working on #124 (SIEM Export)

```bash
# 1. Read the spec
cat specs/SIEM_TELEMETRY_EXPORT.md

# 2. Copy starter code
cp examples/siem_export_starter.py src/azure_haymaker/knowledge_worker/telemetry/exporter.py

# 3. Create tests directory
mkdir -p tests/unit

# 4. Write failing test
cat > tests/unit/test_siem_export.py <<'EOF'
import pytest
from azure_haymaker.knowledge_worker.telemetry.exporter import TelemetryEvent, SentinelConnector

def test_sentinel_connector_sends_event():
    # TODO: Write test
    pass
EOF

# 5. Run test (should fail)
pytest tests/unit/test_siem_export.py -v

# 6. Implement feature to make test pass
# Edit: src/azure_haymaker/knowledge_worker/telemetry/exporter.py

# 7. Iterate until all tests pass
```

---

### To Start Working on #125 (VM Security)

```bash
# 1. Read the spec
cat specs/WINDOWS_VM_SECURITY_HARDENING.md

# 2. Review starter code (don't copy - it's educational)
cat examples/windows_vm_security_starter.py

# 3. Review current implementation
cat src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py

# 4. Create security tests first
cat > tests/security/test_windows_vm_security.py <<'EOF'
import pytest

def test_password_not_in_logs():
    # TODO: Verify password never appears in logs
    pass

def test_nsg_blocks_internet_rdp():
    # TODO: Verify NSG rules restrict RDP to Bastion only
    pass
EOF

# 5. Run tests (should fail against current code)
pytest tests/security/test_windows_vm_security.py -v

# 6. Fix the code (Phase 1: Key Vault credentials)
# Edit: src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py
```

---

## File Location Reference

**Where things live**:

```
src/
├── orchestrator_server.py .............. Main FastAPI app
├── azure_haymaker/
│   ├── agent_base.py ................... Agent lifecycle framework
│   ├── knowledge_worker/
│   │   ├── telemetry/
│   │   │   ├── exporter.py ............. Issue #124 (NEW)
│   │   │   ├── normalizer.py ........... Issue #124 (NEW)
│   │   │   └── connectors/ ............. Issue #124 (NEW directory)
│   │   ├── endpoints/
│   │   │   └── windows_vm.py ........... Issue #125 (MODIFY)
│   ├── orchestrator/
│   │   ├── budget_enforcer.py .......... Issue #128 (NEW)
│   │   ├── circuit_breaker.py .......... Issue #129 (NEW)
│   │   └── health_monitor.py ........... Issue #129 (NEW)
│   └── mocks/ .......................... Issue #130 (NEW directory)

tests/
├── unit/ ............................... Unit tests (fast)
├── integration/ ........................ Integration tests (slower)
├── security/ ........................... Security-specific tests
└── scenarios/ .......................... Issue #133 (NEW directory)

docs/
├── ENHANCEMENT_ROADMAP.md .............. Main roadmap
├── EXECUTIVE_SUMMARY.md ................ Leadership overview
└── [27 other strategic documents]

specs/
├── SIEM_TELEMETRY_EXPORT.md ............ Issue #124 spec
├── WINDOWS_VM_SECURITY_HARDENING.md .... Issue #125 spec
└── [3 other analysis documents]

examples/
├── siem_export_starter.py .............. Issue #124 template
└── windows_vm_security_starter.py ...... Issue #125 template
```

---

## Testing Strategy Per Enhancement

| Enhancement | Unit Tests | Integration Tests | E2E Tests | Security Tests |
|-------------|-----------|-------------------|-----------|----------------|
| #124: SIEM | ✅ Required | ✅ Required | ✅ Mandatory | ⚠️ Optional |
| #125: VM Security | ✅ Required | ✅ Required | ✅ Mandatory | ✅ **CRITICAL** |
| #126: Multi-Tenant | ✅ Required | ✅ Required | ✅ Mandatory | ✅ **CRITICAL** |
| #127: Tracing | ✅ Required | ✅ Required | ✅ Mandatory | ⚠️ Optional |
| #128: Cost | ✅ Required | ✅ Required | ✅ Mandatory | ⚠️ Optional |
| #129: Circuit Breakers | ✅ Required | ✅ Required | ✅ Mandatory | ⚠️ Optional |
| #130: Local Dev | ✅ Required | ⚠️ Optional | ✅ Mandatory | ⚠️ Optional |
| #131: GitHub Actions | ✅ Required | ✅ Required | ✅ Mandatory | ⚠️ Optional |
| #132: Dashboard | ✅ Required | ✅ Required | ✅ Mandatory | ⚠️ Optional |
| #133: Testing Framework | ✅ **Meta** | ✅ **Meta** | ✅ **Meta** | ⚠️ Optional |

**Legend**:
- ✅ Required: Must have
- ⚠️ Optional: Nice to have
- ✅ **CRITICAL**: Security-sensitive, comprehensive tests mandatory
- ✅ **Meta**: Testing the testing framework (recursive)

---

## Related Documentation

- [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Strategic overview
- [All Specifications](../specs/README.md) - Complete spec directory
- [Code Examples](../examples/README.md) - Starter templates
- [Implementation Checklist](IMPLEMENTATION_CHECKLIST.md) - Step-by-step guide

---

**Bookmark this page** for quick reference when picking up enhancement work!
