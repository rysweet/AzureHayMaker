---
layout: default
title: Home
nav_order: 1
description: "Azure HayMaker - Orchestration service for simulating realistic Azure tenant activity"
permalink: /
---

# Azure HayMaker Documentation
{: .fs-9 }

Orchestration service that simulates realistic Azure tenant activity by deploying and managing 50+ distinct operational scenarios using autonomous goal-seeking agents.
{: .fs-6 .fw-300 }

[Get Started](/AzureHayMaker/getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/rysweet/AzureHayMaker){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## What is Azure HayMaker?

Azure HayMaker generates benign telemetry (the "Hay") in which to hide cybersecurity simulation red team signals (the needle in the haystack). It orchestrates realistic Azure operations through:

- **50+ Azure Scenarios** across 10 technology areas (AI/ML, Analytics, Compute, Containers, Databases, etc.)
- **Autonomous Agents** that self-manage deployments and troubleshoot issues using Claude AI
- **Scheduled Execution** (4x daily for different global regions in a follow-the-sun pattern)
- **Complete Automation** using Azure CLI, Terraform, and Bicep
- **Automatic Cleanup** with resource tracking and forced removal

## Quick Navigation

<div class="code-example" markdown="1">

### Getting Started

| Guide | Description |
|:------|:------------|
| [Quick Start](/AzureHayMaker/getting-started) | Get up and running in 30 minutes |
| [Deployment Guide](/AzureHayMaker/deployment) | Deploy to Azure production |
| [Configuration](/AzureHayMaker/configuration) | Configure environment and secrets |

### Core Documentation

| Section | Description |
|:--------|:------------|
| [Architecture](/AzureHayMaker/architecture/) | System design and components |
| [API Reference](/AzureHayMaker/api/) | REST API endpoints and examples |
| [CLI Guide](/AzureHayMaker/cli/) | Command-line interface usage |
| [Scenarios](/AzureHayMaker/scenarios/) | All 50 operational scenarios |

### Reference

| Resource | Description |
|:---------|:------------|
| [FAQ](/AzureHayMaker/reference/faq) | Frequently asked questions |
| [Troubleshooting](/AzureHayMaker/reference/troubleshooting) | Common issues and solutions |
| [Glossary](/AzureHayMaker/reference/glossary) | Terms and definitions |
| [Best Practices](/AzureHayMaker/reference/best-practices) | Recommended patterns |

</div>

## Architecture Overview

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

## API Quick Start

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

[View Full API Reference](/AzureHayMaker/api/){: .btn .btn-outline }

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

- Ephemeral service principals (created per execution, deleted after)
- Secrets managed via Azure Key Vault
- Least privilege access patterns
- Comprehensive audit logging

## Contributing

We welcome contributions! See the [Contributing Guide](/AzureHayMaker/contributing) for details on:

- Setting up your development environment
- Running tests
- Submitting pull requests
- Code style guidelines

## License

Azure HayMaker is released under the [MIT License](https://github.com/rysweet/AzureHayMaker/blob/main/LICENSE).

---

{: .fs-2 }
Built with [Just the Docs](https://just-the-docs.github.io/just-the-docs/) | [View source on GitHub](https://github.com/rysweet/AzureHayMaker)
