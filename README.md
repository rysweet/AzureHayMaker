# Azure HayMaker

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://rysweet.github.io/AzureHayMaker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Roadmap](https://img.shields.io/badge/roadmap-2025--2026-green)](docs/ENHANCEMENT_ROADMAP.md)
[![Portfolio ROI](https://img.shields.io/badge/portfolio%20ROI-267%25-brightgreen)](specs/ENHANCEMENT_COST_BENEFIT_ANALYSIS.md)

<!-- VERSION_BADGES_START -->
[![Latest Release](https://img.shields.io/github/v/release/rysweet/AzureHayMaker?label=release)](https://github.com/rysweet/AzureHayMaker/releases/latest)
[![Development](https://img.shields.io/badge/dev-main-orange)](https://github.com/rysweet/AzureHayMaker/tree/main)

> **Version Links:**
> - [Latest Stable Release](https://github.com/rysweet/AzureHayMaker/releases/latest) - Recommended for production
> - [Development Branch (main)](https://github.com/rysweet/AzureHayMaker/tree/main) - Latest features, may be unstable
<!-- VERSION_BADGES_END -->

> **[View Full Documentation](https://rysweet.github.io/AzureHayMaker/)** - Complete guides, API reference, and 50+ scenario docs

## What is it?

Azure HayMaker is an orchestration service that simulates realistic Azure tenant activity by deploying and managing 50+ distinct operational scenarios using autonomous goal-seeking agents. Each agent performs a full lifecycle: deployment, 8-hour operation period, and cleanup, in a follow-the-sun rotation.  The goal is the creation of benign telemetry (Hay) in which to hide cybersecurity simulation red team signals (the needle in the haystack).

## Key Features

- **50+ Azure Scenarios** across 10 technology areas (AI/ML, Analytics, Compute, Containers, Databases, etc.)
- **Autonomous Agents** that self-manage deployments and troubleshoot issues
- **Cross-Tenant Orchestration** - Manage workloads across multiple Azure tenants from a single orchestrator
- **Scheduled Execution** with configurable cron-based schedules (default: 4x daily)
- **Complete Automation** using Azure CLI, Terraform, and Bicep
- **Automatic Cleanup** with resource tracking and forced removal
- **Analytics Dashboard** with execution statistics and success rates
- **Cost Tracking** via Azure Cost Management API integration
- **Webhook Notifications** for execution events (started, completed, failed)

## Knowledge Worker Framework

The **Knowledge Worker Activity Framework** extends Azure HayMaker to simulate 50-300 knowledge workers performing everyday Microsoft 365 activities. This generates realistic benign telemetry for cybersecurity analysis and security product testing.

### What It Does

- **Simulates Realistic M365 Activity**: Workers send emails, post Teams messages, create documents, and schedule meetings
- **Distinct Endpoints**: Each worker operates from a unique machine identity (Windows 365 Cloud PC or CLI container)
- **Team-Based Organization**: Workers are organized into departments (Executive, Legal, Engineering, HR, Finance, Sales, Operations, Marketing)
- **Internal-Only Communications**: All activity stays within your tenant - multiple safety layers prevent external communications
- **Full Cleanup**: All resources (users, groups, endpoints) are tagged and can be deleted at any time

### Key Capabilities

- **Email Operations**: Send, read, reply, organize (via Microsoft Graph API)
- **Teams Collaboration**: Channel posts, direct messages, thread replies, reactions
- **Document Management**: Create and share Word/Excel/PowerPoint documents
- **Calendar Events**: Schedule meetings, accept/decline invitations

### Hybrid Endpoint Strategy

- **Windows 365 Cloud PCs**: Rich telemetry with full desktop activity (10-50 workers) - ideal for executives and key personas
- **M365 CLI Containers**: Cost-efficient API-based activity (50-250 workers) - ideal for scale

### Learn More

- **[Knowledge Worker Architecture](docs/knowledge-worker-framework/ARCHITECTURE.md)** - Complete framework design
- **[Windows 365 E2E Demo](docs/knowledge-worker-framework/WINDOWS365_E2E_DEMO.md)** - End-to-end demonstration
- **[SIEM Telemetry Export](docs/knowledge-worker-framework/SIEM_TELEMETRY_EXPORT.md)** - Export activity to Azure Sentinel

## Cross-Tenant Orchestration

Azure HayMaker supports **cross-tenant orchestration**, enabling you to manage workloads across multiple Azure tenants from a centralized orchestrator. This is ideal for:

- **Managed Service Providers (MSPs)**: Manage 5-50+ customer tenants from a single control plane
- **Enterprise IT**: Separate dev/test/prod environments across distinct tenants
- **Security Testing**: Generate isolated telemetry across organizational boundaries

### Key Capabilities

- **Tenant Isolation**: Complete resource and credential separation per tenant
- **Concurrent Execution**: Run scenarios in multiple tenants simultaneously
- **Centralized Management**: Single CLI/API to control all tenants
- **Secure Credentials**: All credentials stored in Azure Key Vault
- **Aggregate Monitoring**: Unified view of all tenant operations

### Quick Start: Multi-Tenant Setup

```bash
# Add first target tenant
haymaker orch tenant add \
  --name customer-a \
  --tenant-id <tenant-id> \
  --subscription-id <subscription-id> \
  --keyvault-prefix tenant-a

# Add second target tenant
haymaker orch tenant add \
  --name customer-b \
  --tenant-id <tenant-id> \
  --subscription-id <subscription-id> \
  --keyvault-prefix tenant-b

# Start orchestration across all tenants
haymaker orch start --all-tenants
```

### Documentation

- **[Cross-Tenant Orchestration Guide](docs/guides/cross-tenant-orchestration.md)** - Complete setup and configuration guide
- **[First Multi-Tenant Setup Tutorial](docs/tutorials/first-multi-tenant-setup.md)** - 30-minute step-by-step tutorial
- **[Multi-Tenant CLI Commands](docs/cli/multi-tenant-commands.md)** - Complete CLI reference
- **[Multi-Tenant Configuration](docs/configuration/multi-tenant-config.md)** - Configuration schema and examples
- **[Cross-Tenant Security Guide](docs/security/cross-tenant-security.md)** - Security architecture and best practices

## Quick Start

### 1. Install Dependencies

```bash
uv sync --all-extras
```

### 2. Configure Environment

**Option A: Using .env file (recommended for local development)**

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
# DO NOT commit .env to git!
```

**Option B: Using environment variables**

```bash
cp .env.example .env
# Edit .env and fill in your values
```

### 3. Run Tests

```bash
pytest
```

### 4. Deploy and Run Orchestrator

See [DEPLOYMENT_SETUP.md](docs/DEPLOYMENT_SETUP.md) for complete deployment guide.

**Quick Start**:
```bash
# Build Docker image
cd src
docker build -f Dockerfile.orchestrator -t haymakerorchacr.azurecr.io/haymaker-orchestrator:latest .

# Push to ACR
az acr login --name haymakerorchacr
docker push haymakerorchacr.azurecr.io/haymaker-orchestrator:latest

# Orchestrator runs automatically in Azure App Service
# Access at: https://haymaker-fastapi-app.azurewebsites.net
```

## Configuration

Azure HayMaker uses different secret management approaches for local development vs production:

### Local Development

Secrets are loaded from `.env` file:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your Azure credentials and Anthropic API key

3. Run locally:
   ```bash
   cd src
   uv run func start
   ```

### Production (Azure Function App)

Secrets are managed securely via Azure Key Vault:

1. **Deployment**: GitHub Actions injects secrets to Key Vault
   ```bash
   az keyvault secret set --vault-name <keyvault> --name anthropic-api-key --value "$SECRET"
   ```

2. **Runtime**: Function App uses Key Vault references
   ```bicep
   {
     name: 'ANTHROPIC_API_KEY'
     value: '@Microsoft.KeyVault(VaultName=mykeyvault;SecretName=anthropic-api-key)'
   }
   ```

3. **Access**: Function App Managed Identity has "Key Vault Secrets User" role

### Configuration Priority

The application loads configuration in this order:

1. **Local Development**: `.env` file (gitignored)
2. **Production**: Azure Key Vault (via references)

Environment variables are NOT used in production to avoid accidental secret exposure.

## Using the Orchestrator API

### Health Check

```bash
curl https://haymaker-fastapi-app.azurewebsites.net/
```

**Example Output**:
```json
{"status":"healthy","service":"azure-haymaker-orchestrator","timestamp":"2025-11-25T04:52:18.754691+00:00"}
```

### List Available Scenarios

```bash
curl https://haymaker-fastapi-app.azurewebsites.net/api/scenarios
```

**Example Output**:
```json
{
  "scenarios": [
    {
      "scenario_name": "compute-01-linux-vm-web-server",
      "technology_area": "Compute",
      "scenario_doc_path": "/docs/scenarios/compute-01-linux-vm-web-server.md"
    },
    // ... 49 more scenarios
  ]
}
```

### Execute Scenarios

**Single Scenario**:
```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{"scenarios":["compute-01-linux-vm-web-server"],"duration_hours":1}'
```

**Example Output**:
```json
{
  "execution_id": "3e598ac3-7b1b-46a6-8ddc-5986734e13fc",
  "status": "started",
  "started_at": "2025-11-25T04:52:29.217706+00:00"
}
```

**Multiple Scenarios (Parallel)**:
```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": [
      "databases-01-mysql-wordpress",
      "security-01-key-vault-secrets",
      "ai-ml-01-cognitive-services-vision",
      "networking-01-virtual-network",
      "webapps-01-static-website"
    ],
    "duration_hours": 1
  }'
```

### Monitor Execution

```bash
# Get execution status
EXEC_ID="3e598ac3-7b1b-46a6-8ddc-5986734e13fc"
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions/$EXEC_ID | jq
```

**Example Output**:
```json
{
  "run_id": "3e598ac3-7b1b-46a6-8ddc-5986734e13fc",
  "started_at": "2025-11-25T04:52:29.217706+00:00",
  "status": "running",
  "phases": {
    "validation": {"status": "skipped"},
    "selection": {
      "status": "completed",
      "scenario_count": 5,
      "scenarios": ["compute-01-linux-vm-web-server", ...]
    },
    "provisioning": {
      "status": "completed",
      "service_principals": {
        "requested": 5,
        "created": 5,
        "failed": 0
      },
      "container_apps": {
        "requested": 5,
        "deployed": 5,
        "failed": 0
      }
    }
  }
}
```

### View Production Logs

**App Service Logs**:
```bash
# Stream live logs
az webapp log tail \
  --name haymaker-fastapi-app \
  --resource-group haymaker-dev-rg

# Download logs
az webapp log download \
  --name haymaker-fastapi-app \
  --resource-group haymaker-dev-rg \
  --log-file haymaker-logs.zip
```

**Container App Logs**:
```bash
# List running containers
az containerapp list \
  --resource-group haymaker-dev-rg \
  --query '[?properties.runningStatus==`Running`].name' \
  -o table

# View specific container logs
az containerapp logs show \
  --name compute-01-linux-vm-web-server \
  --resource-group haymaker-dev-rg \
  --follow
```

**Application Insights Queries**:
```kusto
// View orchestrator health
requests
| where cloud_RoleName == "haymaker-fastapi-app"
| where name == "GET /"
| where timestamp > ago(1h)
| summarize
    HealthChecks = count(),
    Successes = countif(resultCode == "200")
| extend SuccessRate = (Successes * 100.0) / HealthChecks

// Track scenario executions
traces
| where message contains "Orchestration completed successfully"
| where timestamp > ago(7d)
| summarize count() by bin(timestamp, 1d)
```

### Check Metrics

```bash
curl https://haymaker-fastapi-app.azurewebsites.net/api/metrics | jq
```

**Example Output**:
```json
{
  "executions_total": 7,
  "executions_running": 2,
  "executions_completed": 5,
  "executions_failed": 0
}
```

### Analytics Dashboard

```bash
# Get analytics for last 30 days (default)
curl https://haymaker-fastapi-app.azurewebsites.net/api/analytics | jq

# Get analytics for specific period (7d, 30d, 90d)
curl "https://haymaker-fastapi-app.azurewebsites.net/api/analytics?period=7d" | jq
```

**Example Output**:
```json
{
  "period": "30d",
  "executions": {
    "total": 120,
    "succeeded": 115,
    "failed": 5
  },
  "success_rate": 0.9583,
  "avg_duration_hours": 8.2,
  "top_scenarios": [
    {"name": "compute-01-linux-vm-web-server", "count": 30, "success_rate": 1.0},
    {"name": "databases-01-mysql-wordpress", "count": 28, "success_rate": 0.96}
  ]
}
```

### Cost Query

```bash
# Get cost summary for an execution
EXEC_ID="3e598ac3-7b1b-46a6-8ddc-5986734e13fc"
curl https://haymaker-fastapi-app.azurewebsites.net/api/executions/$EXEC_ID/cost | jq
```

**Note**: Azure Cost Management has ~24 hour delay before cost data becomes available.

### Schedule Management

Create custom execution schedules with cron expressions:

```bash
# Create a new schedule
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekday Morning Run",
    "cron_expression": "0 9 * * 1-5",
    "scenario_count": 10,
    "enabled": true
  }'

# List all schedules
curl https://haymaker-fastapi-app.azurewebsites.net/api/schedules | jq

# Update a schedule
curl -X PUT https://haymaker-fastapi-app.azurewebsites.net/api/schedules/{schedule_id} \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Delete a schedule
curl -X DELETE https://haymaker-fastapi-app.azurewebsites.net/api/schedules/{schedule_id}
```

### Webhook Notifications

Configure webhooks to receive execution event notifications. Set the `WEBHOOK_URL` environment variable:

```bash
# Events sent to webhook:
# - execution.started: When orchestration begins
# - execution.completed: When orchestration finishes successfully
# - execution.failed: When orchestration fails
```

## Documentation

- **[Deployment Setup](docs/DEPLOYMENT_SETUP.md)** - Complete deployment guide with all requirements
- **[Enhancement Roadmap](docs/ENHANCEMENT_ROADMAP.md)** - Strategic roadmap for 2025-2026 platform evolution
- **[Contributing to Enhancements](docs/CONTRIBUTING_ENHANCEMENTS.md)** - Quick-start guide for enhancement contributors
- **[Project Requirements](specs/requirements.md)** - Detailed specifications and success criteria
- **[Initial Prompt](specs/initial-prompt.md)** - Original project conception
- **[Scenarios](docs/scenarios/)** - 50 operational scenarios with full automation
- **[Architecture Guide](.claude/skills/azure-haymaker/ARCHITECTURE_GUIDE.md)** - Azure HayMaker orchestration service architecture

## 🗺️ Enhancement Roadmap 2025-2026

> ### ⭐ **NEW: Complete Strategic Roadmap Available**
>
> Azure HayMaker has a comprehensive 12-month enhancement roadmap with **10 prioritized enhancements** delivering **$1.2M in business value** from a **$336K investment** (**267% ROI**).
>
> **Start here**: [Executive Summary](docs/EXECUTIVE_SUMMARY.md) - 10-minute business case
>
> **All 10 enhancements have**: GitHub issue, implementation spec, getting started guide, ROI calculation, and timeline.

### Quick Access to Enhancements

| Enhancement | Priority | ROI | Issue | Getting Started |
|-------------|----------|-----|-------|-----------------|
| SIEM Telemetry Export | P0 🔴 | 120% | [#124](https://github.com/rysweet/AzureHayMaker/issues/124) | [Guide](docs/GETTING_STARTED_124_SIEM_EXPORT.md) |
| Windows VM Security | P0 🔴 | 1,165% | [#125](https://github.com/rysweet/AzureHayMaker/issues/125) | [Guide](docs/GETTING_STARTED_125_VM_SECURITY.md) |
| Multi-Tenant Isolation | P1 🟡 | 233% | [#126](https://github.com/rysweet/AzureHayMaker/issues/126) | [Guide](docs/GETTING_STARTED_126_MULTI_TENANT.md) |
| Distributed Tracing | P1 🟡 | 36% | [#127](https://github.com/rysweet/AzureHayMaker/issues/127) | [Guide](docs/GETTING_STARTED_127_DISTRIBUTED_TRACING.md) |
| Cost Budget Enforcement | P1 🟡 | 184% | [#128](https://github.com/rysweet/AzureHayMaker/issues/128) | [Guide](docs/GETTING_STARTED_128_COST_ENFORCEMENT.md) |
| Plus 5 more P1/P2 enhancements... | | | [View All](https://github.com/rysweet/AzureHayMaker/issues?q=label%3Aenhancement) | [See Roadmap](docs/ENHANCEMENT_ROADMAP.md) |

### Planning & Strategy

**Key Documents**:
- **[Enhancement Roadmap](docs/ENHANCEMENT_ROADMAP.md)** - Complete strategic plan (2025-2026)
- **[Visual Roadmap](docs/VISUAL_ROADMAP.md)** - Mermaid diagrams and timeline
- **[Quick Reference Card](docs/ENHANCEMENT_QUICK_REFERENCE.md)** - One-page stakeholder summary
- **[Implementation Specs](specs/README.md)** - Technical specifications for all enhancements
- **[GitHub Issues](https://github.com/rysweet/AzureHayMaker/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)** - Track progress
- **[Milestones](https://github.com/rysweet/AzureHayMaker/milestones)** - Quarterly goals (Q1-Q4 2026)

**For Contributors**:
- **[Quick Start Guide](docs/QUICK_START_CONTRIBUTORS.md)** - Get started in 15 minutes
- **[Contributing to Enhancements](docs/CONTRIBUTING_ENHANCEMENTS.md)** - Detailed workflow

## Development

```bash
# Run tests
pytest

# Linting and type checking
ruff check .
pyright

# Pre-commit hooks
pre-commit run --all-files
```

## License

MIT License - Open Source
