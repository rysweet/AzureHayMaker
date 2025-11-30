# Project Context: Azure HayMaker

**This file provides project-specific context to Claude Code agents.**

---

## Project: Azure HayMaker (h2)

## Overview

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://rysweet.github.io/AzureHayMaker/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Azure HayMaker** is an orchestration service that simulates realistic Azure tenant activity by deploying and managing 50+ distinct operational scenarios using autonomous goal-seeking agents.

**Mission**: Create benign telemetry (Hay) to hide cybersecurity simulation red team signals (the needle in the haystack).

**Strategic Direction**: See [Enhancement Roadmap](../docs/ENHANCEMENT_ROADMAP.md) for 2025-2026 platform evolution.

---

## Architecture

### Key Components

1. **FastAPI Orchestrator** (`src/orchestrator_server.py`)
   - REST API with APScheduler for cron-based scheduling (4x daily default)
   - Scenario selection, service principal management, container deployment
   - Cost tracking via Azure Cost Management API
   - Analytics dashboard and webhook notifications

2. **Agent Execution Framework** (`src/azure_haymaker/agent_base.py`)
   - Abstract base class providing lifecycle hooks (on_start, on_execute, on_cleanup)
   - 50+ scenario implementations in `src/agents/`
   - Autonomous goal-seeking behavior using Claude AutoMode (Anthropic SDK)
   - 8-hour operation cycles with complete resource cleanup

3. **Knowledge Worker Framework** (`src/azure_haymaker/knowledge_worker/`)
   - M365 activity simulation (email, Teams, calendar, documents)
   - Three-layer architecture: Orchestration → Operations → Identity & Endpoint
   - CLI Container and Windows 365 Cloud PC endpoints
   - Worker personas with realistic activity patterns

4. **Container Manager** (`src/azure_haymaker/orchestrator/container_manager.py`)
   - Deploys agents in Azure Container Apps
   - Image signing verification, monitoring, cleanup enforcement

### Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI + APScheduler + Pydantic v2
- **Testing**: pytest (765+ tests, 100% passing in core modules)
- **Azure SDKs**: identity, mgmt-resource, containerinstance, servicebus, keyvault, tables, msgraph, costmanagement
- **Infrastructure**: Azure Container Apps (agents), Azure App Service (orchestrator), Application Insights (monitoring)
- **Deployment**: Azure CLI, Terraform, Bicep

---

## Development Guidelines

### Code Organization

```
src/
├── orchestrator_server.py          # Main FastAPI application
├── azure_haymaker/
│   ├── agent_base.py               # Agent lifecycle framework
│   ├── knowledge_worker/           # M365 activity simulation
│   ├── orchestrator/               # Orchestrator modules
│   └── models/                     # Pydantic data models
├── agents/                         # 50+ scenario implementations
docs/
├── ENHANCEMENT_ROADMAP.md          # Strategic roadmap (2025-2026)
├── scenarios/                      # 50+ scenario documentation
└── knowledge-worker-framework/     # KW architecture docs
specs/
├── SIEM_TELEMETRY_EXPORT.md       # P0-Critical spec
├── WINDOWS_VM_SECURITY_HARDENING.md # P0-Critical spec
├── ENHANCEMENT_DEPENDENCIES.md     # Dependencies analysis
└── ENHANCEMENT_COST_BENEFIT_ANALYSIS.md # ROI analysis
tests/
├── unit/                           # Unit tests
├── integration/                    # Integration tests
└── security/                       # Security tests
```

### Key Patterns

1. **Autonomous Agents**: Self-managing, goal-seeking agents with Claude AutoMode
2. **Complete Lifecycle**: Deploy → Operate (8 hours) → Cleanup (verified deletion)
3. **Ruthless Simplicity**: No stubs, no placeholders, no TODOs (Zero-BS principle)
4. **Modular Design**: Clear boundaries, self-contained components (bricks & studs philosophy)
5. **Graceful Degradation**: Cascade fallback (Cloud PC → Windows VM → Container)

### Testing Strategy

- **Unit Tests**: 765+ tests, 100% passing in core modules
- **Integration Tests**: Real Azure credentials required (manual validation)
- **Security Tests**: Credential sanitization, injection prevention, path traversal protection
- **E2E Testing**: Mandatory before PR merge (outside-in, user workflow validation)
- **Coverage Targets**: 85-95% across all modules

---

## Domain Knowledge

### Business Context

**Problem**: Red team exercises require benign background telemetry in target Azure tenants to hide malicious activity from SOC analysts and SIEM alerts. Without realistic "noise," security tools easily detect red team operations.

**Solution**: Azure HayMaker generates realistic, scheduled Azure tenant activity across 50+ scenarios (compute, databases, AI/ML, networking, etc.) to create benign telemetry that masks red team signals.

**Users**:
- Red team operators conducting authorized security assessments
- Cybersecurity training organizations
- MSPs and SaaS providers (future with multi-tenant support)

### Key Terminology

- **Hay**: Benign telemetry generated by HayMaker scenarios
- **Needle**: Red team activity hidden within the hay
- **Scenario**: One of 50+ operational patterns (e.g., "compute-01-linux-vm-web-server")
- **Agent**: Autonomous goal-seeking entity that executes a scenario lifecycle
- **Knowledge Worker**: Simulated M365 user generating email, Teams, calendar activity
- **Worker Persona**: Activity pattern (Engineering, Finance, Sales, Executive, Support)
- **Endpoint**: Where agents execute (CLI Container, Windows 365 Cloud PC, Windows VM)
- **Orchestrator**: FastAPI service managing scenario scheduling and execution
- **Run ID**: Unique identifier for an orchestration execution
- **Cleanup**: Forced resource deletion with verification (prevents runaway costs)

---

## Current State & Roadmap

### Production-Ready Features (Today)

✅ 50 operational scenarios across 10 Azure technology areas
✅ Autonomous goal-seeking agents with self-healing
✅ Knowledge Worker framework (2-50 workers, license-dependent)
✅ M365 email & calendar operations (Graph API)
✅ CLI containers for scale (300+ projected)
✅ Cost tracking via Azure Cost Management API
✅ Cron-based scheduling with APScheduler
✅ Analytics dashboard with execution metrics
✅ Complete resource cleanup with forced deletion
✅ Webhook notifications (execution events)

### In-Progress (Open PRs)

🚧 PR #123: Computer Use Knowledge Worker Agents (browser automation with Playwright)
🚧 PR #121: Windows VM fallback for Computer Use Agents (has security issues - 72/100 score)
🚧 PR #119: W365 + M365 E2E with telemetry and graceful degradation
🚧 PR #112: Knowledge Worker CLI commands and e2e validation

### Strategic Roadmap (2025-2026)

See **[docs/ENHANCEMENT_ROADMAP.md](../docs/ENHANCEMENT_ROADMAP.md)** for full details.

**P0-Critical (Immediate)**:
- Issue #124: SIEM Telemetry Export Pipeline (ROI: 120%)
- Issue #125: Windows VM Security Hardening (ROI: 1,165%)

**P1-High (Q1-Q2)**:
- Issue #126: Multi-Tenant Resource Isolation (ROI: 233%)
- Issue #127: Distributed Tracing and Correlation IDs (ROI: 36%)
- Issue #128: Cost Budget Enforcement and Alerts (ROI: 184%)
- Issue #129: Agent Health Checks and Circuit Breakers

**P2-Medium (Q3-Q4)**:
- Local Development Mode (mock Azure services)
- GitHub Actions Custom Agent (HayMaker-as-a-Service)
- Analytics Dashboard with Real-Time Metrics
- Scenario Testing Framework

**Portfolio Investment**: $336K → $1.2M benefits = **267% ROI**

---

## Common Tasks

### Development Workflow

1. **Pick Enhancement**: See [docs/CONTRIBUTING_ENHANCEMENTS.md](../docs/CONTRIBUTING_ENHANCEMENTS.md)
2. **Review Spec**: Read implementation spec from `specs/` directory
3. **Create Branch**: `feat/issue-XXX-brief-description`
4. **Implement**: Follow spec acceptance criteria, write tests first (TDD)
5. **Test Locally**: E2E testing mandatory (outside-in, user workflow)
6. **Commit & PR**: Link to GitHub issue, include test results
7. **Review**: Security review, philosophy compliance, code quality

### Deployment Process

**Orchestrator**:
```bash
cd src
docker build -f Dockerfile.orchestrator -t haymakerorchacr.azurecr.io/haymaker-orchestrator:latest .
az acr login --name haymakerorchacr
docker push haymakerorchacr.azurecr.io/haymaker-orchestrator:latest
# Orchestrator runs automatically in Azure App Service
# Access: https://haymaker-fastapi-app.azurewebsites.net
```

**Knowledge Workers**:
```bash
haymaker kw deploy --workers 5 --department engineering
```

**View Logs**:
```bash
# App Service logs
az webapp log tail --name haymaker-fastapi-app --resource-group haymaker-dev-rg

# Container App logs
az containerapp logs show --name <scenario-name> --resource-group haymaker-dev-rg --follow
```

---

## Important Notes

### Security Considerations

⚠️ **PR #121 has critical security issues** (Score: 72/100):
- Credentials exposed in plaintext (logs)
- Unrestricted NSG rules (RDP from ANY IP)
- Public IPs on all VMs
- No disk encryption, no JIT access

**Action Required**: Fix before merging (see Issue #125, spec at `specs/WINDOWS_VM_SECURITY_HARDENING.md`)

### Known Limitations

- **Single Tenant Only**: Multi-tenant support in roadmap (Issue #126)
- **No SIEM Export**: Core use case blocker (Issue #124)
- **Cost Overruns Possible**: No automatic throttling yet (Issue #128)
- **Limited Observability**: No distributed tracing (Issue #127)

### Development Best Practices

1. **Zero-BS Principle**: No stubs, no TODOs, no placeholders, no swallowed exceptions
2. **Test First**: Write failing tests before implementation (TDD)
3. **E2E Mandatory**: Test like a user would, outside-in (not just unit tests)
4. **Security First**: Never compromise on credential storage, network isolation, encryption
5. **Cost Conscious**: Always verify cleanup, test resource deletion

### Useful Links

- **Enhancement Roadmap**: [docs/ENHANCEMENT_ROADMAP.md](../docs/ENHANCEMENT_ROADMAP.md)
- **Contributing Guide**: [docs/CONTRIBUTING_ENHANCEMENTS.md](../docs/CONTRIBUTING_ENHANCEMENTS.md)
- **Spec Index**: [specs/README.md](../specs/README.md)
- **Full Documentation**: [docs/INDEX.md](../docs/INDEX.md)
- **GitHub Issues**: https://github.com/rysweet/AzureHayMaker/issues

---

## About This File

This file is installed by amplihack to provide project-specific context to AI agents.

**For more about amplihack itself**, see [PROJECT_AMPLIHACK.md](./PROJECT_AMPLIHACK.md).

**Tip**: Keep this file updated as your project evolves. Accurate context leads to better AI assistance.
