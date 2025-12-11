---
layout: default
title: Home
nav_order: 1
description: "Azure HayMaker - Orchestration service for simulating realistic Azure tenant activity"
permalink: /
---

<div class="hero" markdown="0">
  <h1>Azure HayMaker</h1>
  <p>Generate realistic Azure tenant activity with 50+ autonomous scenarios across AI/ML, Compute, Containers, Databases, and more.</p>
  <div class="hero-buttons">
    <a href="/AzureHayMaker/getting-started" class="btn btn-primary">Get Started</a>
    <a href="https://github.com/rysweet/AzureHayMaker" class="btn btn-secondary">View on GitHub</a>
  </div>
</div>

<div class="stats fade-in" markdown="0">
  <div class="stat">
    <div class="stat-value">50+</div>
    <div class="stat-label">Scenarios</div>
  </div>
  <div class="stat">
    <div class="stat-value">10</div>
    <div class="stat-label">Categories</div>
  </div>
  <div class="stat">
    <div class="stat-value">4x</div>
    <div class="stat-label">Daily Runs</div>
  </div>
  <div class="stat">
    <div class="stat-value">100%</div>
    <div class="stat-label">Automated</div>
  </div>
</div>

---

## What is Azure HayMaker?

Azure HayMaker generates benign telemetry (the "Hay") in which to hide cybersecurity simulation red team signals (the needle in the haystack). It orchestrates realistic Azure operations through autonomous goal-seeking agents.

<div class="feature-grid" markdown="0">
  <div class="feature-card">
    <span class="feature-icon">🤖</span>
    <h3>Autonomous Agents</h3>
    <p>Self-managing deployments powered by Claude AI that troubleshoot issues automatically.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">📊</span>
    <h3>50+ Scenarios</h3>
    <p>Comprehensive coverage across AI/ML, Compute, Containers, Databases, and more.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">🌍</span>
    <h3>Follow-the-Sun</h3>
    <p>4x daily execution across global regions for realistic activity patterns.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">🔒</span>
    <h3>Security First</h3>
    <p>Ephemeral service principals, Key Vault secrets, and least-privilege access.</p>
  </div>
</div>

---

## Quick Start

<div class="quick-links" markdown="0">
  <a href="/AzureHayMaker/getting-started" class="quick-link">
    <span class="icon">🚀</span>
    <span>Get Started</span>
  </a>
  <a href="/AzureHayMaker/deployment" class="quick-link">
    <span class="icon">☁️</span>
    <span>Deploy to Azure</span>
  </a>
  <a href="/AzureHayMaker/cli/" class="quick-link">
    <span class="icon">💻</span>
    <span>CLI Guide</span>
  </a>
  <a href="/AzureHayMaker/reporting-telemetry/" class="quick-link">
    <span class="icon">📊</span>
    <span>Reports & Metrics</span>
  </a>
  <a href="/AzureHayMaker/api/" class="quick-link">
    <span class="icon">🔌</span>
    <span>API Reference</span>
  </a>
</div>

### API Quick Start

```bash
# Health check
curl https://haymaker-fastapi-app.azurewebsites.net/

# List available scenarios
curl https://haymaker-fastapi-app.azurewebsites.net/api/scenarios

# Execute a scenario
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{"scenarios":["compute-01-linux-vm-web-server"],"duration_hours":1}'

# Check execution status
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions/{execution_id}
```

---

## Architecture Overview

The orchestrator ([orchestrator_server.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/orchestrator_server.py)) coordinates scenario execution:

```
                    ┌─────────────────────────────────────────┐
                    │        Azure HayMaker Orchestrator      │
                    │  (FastAPI Service on Azure App Service) │
                    └─────────────────┬───────────────────────┘
                                      │
                    ┌─────────────────┼───────────────────────┐
                    │                 │                       │
              ┌─────▼─────┐     ┌─────▼─────┐          ┌─────▼─────┐
              │  Scenario │     │  Scenario │    ...   │  Scenario │
              │  Agent 1  │     │  Agent 2  │          │  Agent N  │
              │ (Container│     │ (Container│          │ (Container│
              │   App)    │     │   App)    │          │   App)    │
              └─────┬─────┘     └─────┬─────┘          └─────┬─────┘
                    │                 │                       │
                    └─────────────────┼───────────────────────┘
                                      │
                              ┌───────▼───────┐
                              │ Azure Tenant  │
                              │  Resources    │
                              └───────────────┘
```

[View Full Architecture](/AzureHayMaker/architecture/){: .btn .btn-outline }

---

## Scenario Categories

Azure HayMaker includes 50 scenarios across 10 technology areas:

| Category | Count | Examples |
|:---------|:------|:---------|
| [AI & Machine Learning](/AzureHayMaker/scenarios/ai-ml/) | 5 | Cognitive Services, Azure OpenAI, ML Workspace |
| [Analytics](/AzureHayMaker/scenarios/analytics/) | 5 | Synapse, Databricks, Power BI |
| [Compute](/AzureHayMaker/scenarios/compute/) | 5 | VMs, App Service, Azure Functions |
| [Containers](/AzureHayMaker/scenarios/containers/) | 5 | AKS, Container Apps, Container Instances |
| [Databases](/AzureHayMaker/scenarios/databases/) | 5 | Cosmos DB, PostgreSQL, Redis |
| [Hybrid + Multicloud](/AzureHayMaker/scenarios/hybrid/) | 5 | Azure Arc, Site Recovery |
| [Identity](/AzureHayMaker/scenarios/identity/) | 5 | Entra ID, RBAC, Conditional Access |
| [Networking](/AzureHayMaker/scenarios/networking/) | 5 | VNets, Load Balancer, VPN Gateway |
| [Security](/AzureHayMaker/scenarios/security/) | 5 | Key Vault, NSGs, Security Center |
| [Web Apps](/AzureHayMaker/scenarios/webapps/) | 5 | Static Web Apps, App Service, API Management |

[Browse All Scenarios](/AzureHayMaker/scenarios/){: .btn .btn-outline }

---

## Knowledge Worker Framework

Simulate 50-300 knowledge workers performing realistic M365 activities (email, Teams, documents, calendar).

| Resource | Description |
|:---------|:------------|
| [Tutorial: Deploy & Monitor 25 Workers](https://github.com/rysweet/AzureHayMaker/blob/main/docs/knowledge-worker-framework/TUTORIAL_DEPLOY_AND_MONITOR.md) | End-to-end tutorial: Deploy 25 workers with AI limerick emails |
| [AI Email Generation Guide](https://github.com/rysweet/AzureHayMaker/blob/main/docs/knowledge-worker-framework/AI_EMAIL_GENERATION.md) | Complete guide to AI-powered email content generation |
| [Email Markers Guide](https://github.com/rysweet/AzureHayMaker/blob/main/docs/knowledge-worker-framework/EMAIL_MARKERS_GUIDE.md) | Track and filter emails with embedded markers |
| [Architecture](https://github.com/rysweet/AzureHayMaker/blob/main/docs/knowledge-worker-framework/ARCHITECTURE.md) | Framework design and component overview |
| [Windows 365 E2E Demo](https://github.com/rysweet/AzureHayMaker/blob/main/docs/knowledge-worker-framework/WINDOWS365_E2E_DEMO.md) | Full Windows 365 Cloud PC demonstration |

**Getting Started**:
```bash
# Install CLI
pip install haymaker-cli

# Initialize KW app registration
haymaker kw init --save-config kw_config.env

# Deploy 25 workers with AI limericks
haymaker kw deploy \
  --workers 25 \
  --department operations \
  --duration 2 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work" \
  --marker-format LIMERICK
```

---

## Key Features

{: .note }
> All agents are **goal-seeking** - they autonomously resolve problems encountered during execution using Claude AI.

### Zero-BS Philosophy

Every component implements real functionality with no stubs, TODOs, or placeholders. The system is production-ready and fully operational.

### Complete Resource Lifecycle

1. **Deployment** - Automated resource provisioning with tagged resources
2. **Operations** - 8-hour operational period generating realistic telemetry
3. **Cleanup** - Complete resource deletion with verification

### Security First

- Ephemeral service principals (created per execution, deleted after) - see [sp_manager.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/sp_manager.py)
- Secrets managed via Azure Key Vault - see [keyvault.bicep](https://github.com/rysweet/AzureHayMaker/blob/main/infra/bicep/modules/keyvault.bicep)
- Least privilege access patterns
- Comprehensive audit logging - see [event_bus.py](https://github.com/rysweet/AzureHayMaker/blob/main/src/azure_haymaker/orchestrator/event_bus.py)

---

## Documentation

<div class="quick-links" markdown="0">
  <a href="/AzureHayMaker/architecture/" class="quick-link">
    <span class="icon">🏗️</span>
    <span>Architecture</span>
  </a>
  <a href="/AzureHayMaker/scenarios/" class="quick-link">
    <span class="icon">📋</span>
    <span>Scenarios</span>
  </a>
  <a href="/AzureHayMaker/reporting-telemetry/" class="quick-link">
    <span class="icon">📊</span>
    <span>Reporting & Telemetry</span>
  </a>
  <a href="/AzureHayMaker/reference/faq" class="quick-link">
    <span class="icon">❓</span>
    <span>FAQ</span>
  </a>
  <a href="/AzureHayMaker/reference/troubleshooting" class="quick-link">
    <span class="icon">🔧</span>
    <span>Troubleshooting</span>
  </a>
</div>

### How-To Guides

Task-focused guides for specific operations:

- [Configure Anthropic Model](/AzureHayMaker/howto/configure-anthropic-model) - Select and configure Claude models for AI email generation

---

## Contributing

We welcome contributions! See the [Contributing Guide](/AzureHayMaker/contributing) for details on:

- Setting up your development environment
- Running tests
- Submitting pull requests
- Code style guidelines

---

## License

Azure HayMaker is released under the [MIT License](https://github.com/rysweet/AzureHayMaker/blob/main/LICENSE).

---

{: .fs-2 }
Built with [Just the Docs](https://just-the-docs.github.io/just-the-docs/) | [View source on GitHub](https://github.com/rysweet/AzureHayMaker)
