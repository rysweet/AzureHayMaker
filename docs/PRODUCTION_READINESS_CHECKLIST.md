# Production Readiness Checklist

**Purpose**: Verify Azure HayMaker is production-ready before deploying to customer environments.

**Last Updated**: 2025-11-30

---

## ⚠️ CURRENT STATUS: NOT PRODUCTION READY

**Blockers**:
- 🔴 **Issue #125**: Windows VM Security Hardening (P0-Critical)
- 🔴 **Issue #124**: SIEM Telemetry Export (P0-Critical for red team use case)

**Merge PR #119 first** to unblock Issue #124.

---

## Security Checklist

### Critical Security Requirements

- [ ] **Credentials in Key Vault** - No plaintext passwords in code/logs
  - 🔴 **BLOCKED**: Issue #125 (Windows VM credentials exposed)
  - Files: `src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py`

- [ ] **Network Security** - Restricted NSG rules, no public IPs
  - 🔴 **BLOCKED**: Issue #125 (RDP from ANY IP, public IPs on all VMs)
  - Files: `src/azure_haymaker/knowledge_worker/endpoints/windows_vm.py`

- [ ] **Disk Encryption** - Azure Disk Encryption enabled
  - 🔴 **BLOCKED**: Issue #125 (VMs not encrypted)

- [ ] **JIT Access** - Just-In-Time VM access configured
  - 🔴 **BLOCKED**: Issue #125 (No JIT policies)

- [ ] **SIEM Integration** - Telemetry exported to customer SIEM
  - 🔴 **BLOCKED**: Issue #124 (No SIEM export capability)
  - **Impact**: Core use case not functional

- [ ] **Security Scanning** - No hardcoded secrets detected
  - ✅ **PASS**: pre-commit hooks check for secrets

- [ ] **Azure AD Authentication** - Orchestrator API requires auth
  - ✅ **PASS**: `src/azure_haymaker/orchestrator/auth.py` implemented

---

## Infrastructure Checklist

### Required Services

- [ ] **Azure Container Apps** - Agent execution environment
  - ✅ Configured in `infra/bicep/`
  - ⚠️ Verify capacity limits for target scale

- [ ] **Azure App Service** - Orchestrator hosting
  - ✅ Deployed at `haymaker-fastapi-app.azurewebsites.net`
  - ⚠️ Verify SKU supports expected load

- [ ] **Azure Key Vault** - Secrets management
  - ⚠️ **REQUIRED**: Issue #125 (not yet integrated for VM passwords)
  - ✅ Used for M365 credentials

- [ ] **Azure Bastion** - Secure VM access
  - 🔴 **MISSING**: Issue #125 (currently using public IPs + unrestricted NSG)

- [ ] **Application Insights** - Monitoring and telemetry
  - ✅ Configured
  - ⚠️ Verify distributed tracing (Issue #127)

- [ ] **Azure Table Storage** - Schedule persistence
  - ✅ Configured for schedules

- [ ] **Azure Cost Management** - Cost tracking
  - ✅ Implemented in `src/azure_haymaker/orchestrator/cost_query.py`
  - ⚠️ 24-hour delay limitation

---

## Operational Checklist

### Monitoring & Alerting

- [ ] **Cost Budget Alerts** - Automatic throttling when budget exceeded
  - 🔴 **MISSING**: Issue #128 (no budget enforcement)
  - **Risk**: Runaway costs possible

- [ ] **Agent Health Monitoring** - Detect stuck/failed agents
  - 🔴 **MISSING**: Issue #129 (no health checks or circuit breakers)
  - **Risk**: Resource waste from zombie agents

- [ ] **Distributed Tracing** - End-to-end request correlation
  - 🔴 **MISSING**: Issue #127 (no OpenTelemetry integration)
  - **Risk**: Difficult to debug failures

- [ ] **Webhook Notifications** - Execution event alerts
  - ✅ **PASS**: Implemented in `src/azure_haymaker/orchestrator/webhooks.py`

- [ ] **Application Insights Queries** - Custom dashboards
  - ⚠️ **PARTIAL**: Basic queries exist, needs enhancement
  - See: Issue #132 (Analytics Dashboard)

---

## Functionality Checklist

### Core Features

- [ ] **50+ Scenarios** - All operational scenarios working
  - ✅ **PASS**: 50 scenarios documented and implemented
  - ⚠️ Verify: Manual testing of each scenario recommended

- [ ] **Knowledge Worker Framework** - M365 activity simulation
  - ⚠️ **PARTIAL**: PR #119 adds telemetry (needs merge)
  - ⚠️ **PARTIAL**: PR #123 adds Computer Use (depends on #125)

- [ ] **Autonomous Agents** - Self-healing and goal-seeking
  - ✅ **PASS**: Agent base class with lifecycle hooks
  - ⚠️ Verify: Circuit breakers needed (Issue #129)

- [ ] **Complete Cleanup** - Resource deletion verified
  - ✅ **PASS**: Forced deletion fallback implemented
  - ✅ **PASS**: Resource tracking with tags

- [ ] **Cost Tracking** - Azure Cost Management integration
  - ✅ **PASS**: Implemented
  - ⚠️ Limitation: 24-hour delay

- [ ] **Scheduling** - Cron-based execution
  - ✅ **PASS**: APScheduler with croniter validation
  - ⚠️ Verify: Single scheduler instance (no HA)

---

## Red Team Use Case Checklist

### Mission-Critical Requirements

- [ ] **SIEM Export** - Hay telemetry appears in target SIEM
  - 🔴 **BLOCKED**: Issue #124 (core use case blocker)
  - **Impact**: Cannot fulfill primary mission without this

- [ ] **Realistic Telemetry** - Indistinguishable from real users
  - ⚠️ **PARTIAL**: M365 operations realistic (PR #119)
  - ⚠️ **PARTIAL**: Computer Use adds browser telemetry (PR #123)
  - ✅ **PASS**: 50 Azure scenarios provide diverse activity

- [ ] **Scheduled Activity** - Follow-the-sun rotation
  - ✅ **PASS**: Configurable cron schedules
  - ⚠️ Verify: Time zone coverage adequate

- [ ] **Volume & Diversity** - Sufficient hay to mask needles
  - ⚠️ **VERIFY**: Scale testing needed (>10 concurrent scenarios)
  - See: Issue #133 (Scenario Testing Framework)

---

## Performance Checklist

### Scale Requirements

- [ ] **Concurrent Scenarios** - Support 10+ parallel scenarios
  - ⚠️ **UNTESTED**: No performance benchmarks exist
  - See: Issue #133 (Testing Framework includes performance tests)

- [ ] **Knowledge Workers** - Support 50-300 workers
  - ⚠️ **PROJECTED**: 300 workers = ~4.5 min deployment
  - ⚠️ **TESTED**: Up to 50 workers successfully deployed

- [ ] **API Response Time** - <1s for orchestrator endpoints
  - ⚠️ **UNTESTED**: No load testing performed
  - See: Issue #127 (Distributed Tracing will expose latency)

- [ ] **Resource Limits** - Azure quotas adequate
  - ⚠️ **VERIFY**: Container Apps quota (default: 10 per region)
  - ⚠️ **VERIFY**: Service Principal limit

---

## Documentation Checklist

### Required Documentation

- [x] **README.md** - Quick start and overview
- [x] **Architecture Documentation** - System design
- [x] **Deployment Guide** - How to deploy
- [x] **API Documentation** - Endpoint specifications
- [x] **Scenario Documentation** - All 50 scenarios documented
- [x] **Enhancement Roadmap** - Strategic direction
- [ ] **Runbook** - Operational procedures
  - 🔴 **MISSING**: Incident response, troubleshooting procedures
- [ ] **Security Policy** - Vulnerability reporting
  - ⚠️ **PARTIAL**: `docs/SECURITY.md` exists, needs update

---

## Compliance Checklist

### Regulatory & Standards

- [ ] **SOC 2 Type II** - Required for enterprise customers
  - 🔴 **BLOCKED**: Issue #125 (security vulnerabilities)
  - 🔴 **BLOCKED**: Issue #127 (audit trail gaps)

- [ ] **CIS Azure Foundations** - Security baseline
  - 🔴 **BLOCKED**: Issue #125 (NSG rules violate CIS)

- [ ] **NIST Cybersecurity Framework** - Security controls
  - 🔴 **BLOCKED**: Issue #125 (credential management violates NIST)

- [ ] **GDPR Compliance** - Data privacy (if applicable)
  - ⚠️ **VERIFY**: Multi-tenant data isolation (Issue #126)

---

## Production Deployment Decision

### Go/No-Go Criteria

**MUST HAVE (Blocking)**:
- 🔴 Issue #125: Windows VM Security Hardening - **CRITICAL**
- 🔴 Issue #124: SIEM Telemetry Export - **CRITICAL for use case**

**SHOULD HAVE (Strongly Recommended)**:
- 🟡 Issue #128: Cost Budget Enforcement - **Financial risk**
- 🟡 Issue #127: Distributed Tracing - **Operational visibility**
- 🟡 Issue #129: Circuit Breakers - **Reliability**

**NICE TO HAVE**:
- Issue #126: Multi-Tenant Isolation
- Issue #130: Local Dev Mode
- Analytics Dashboard
- Testing Framework

### Current Recommendation

**Status**: 🔴 **NOT PRODUCTION READY**

**Minimum Required Actions**:
1. ✅ Merge PR #119 (ready now)
2. 🔴 Complete Issue #125 (1-2 weeks)
3. 🔴 Complete Issue #124 (2.5-3.5 weeks)
4. 🟡 Complete Issue #128 (1.5 weeks) - **Strongly recommended**

**Timeline to Production**: 6-8 weeks minimum

---

## Production Deployment Phases

### Phase 1: Security Foundation (Weeks 1-3)
**Target**: Address critical security issues

- [ ] Merge PR #119
- [ ] Complete Issue #125 (Windows VM Security)
- [ ] Security audit passing
- [ ] Penetration testing completed

**Go/No-Go**: Security score >90/100

---

### Phase 2: Core Use Case (Weeks 4-6)
**Target**: Enable SIEM export

- [ ] Complete Issue #124 (SIEM Export)
- [ ] Azure Sentinel connector verified
- [ ] End-to-end red team exercise successful
- [ ] Telemetry appearing in target SIEM

**Go/No-Go**: SIEM export working with 3 connectors

---

### Phase 3: Operational Readiness (Weeks 7-8)
**Target**: Production-grade operations

- [ ] Complete Issue #128 (Cost Budget Enforcement)
- [ ] Complete Issue #127 (Distributed Tracing)
- [ ] Monitoring dashboards configured
- [ ] Runbook created

**Go/No-Go**: Cost controls working, traces visible

---

### Phase 4: Production Deployment (Week 9)
**Target**: Deploy to production

- [ ] All previous phases complete
- [ ] Load testing passed
- [ ] Disaster recovery tested
- [ ] Customer acceptance testing

**Go/No-Go**: All critical and high-priority items resolved

---

## Verification Commands

Run these before declaring production-ready:

```bash
# 1. All tests passing
pytest

# 2. No security vulnerabilities
ruff check . --select S
bandit -r src/

# 3. No hardcoded secrets
pre-commit run detect-secrets --all-files

# 4. Cost tracking working
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions/{id}/cost

# 5. Health check passing
curl https://haymaker-fastapi-app.azurewebsites.net/

# 6. Scenarios listed
curl https://haymaker-fastapi-app.azurewebsites.net/api/scenarios
```

---

## Sign-Off

Production deployment requires sign-off from:

- [ ] **Security Team** - Security issues resolved (#125)
- [ ] **Architecture Team** - Design approved (especially #126 if deployed)
- [ ] **Engineering Lead** - Code quality verified
- [ ] **Product Owner** - Use case validated (#124 SIEM export working)
- [ ] **Finance** - Cost controls in place (#128)

---

## Related Documentation

- [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Strategic plan
- [Roadmap Status](ROADMAP_STATUS.md) - Current progress
- [Deployment Guide](DEPLOYMENT_SETUP.md) - How to deploy
- [Security Fixes](SECURITY_FIXES.md) - Security improvements

---

**Use this checklist before every production deployment to ensure quality and security standards are met.**
