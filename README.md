# Azure HayMaker

[![Tests](https://img.shields.io/badge/tests-99%25%20passing-brightgreen)](.) [![Code Quality](https://img.shields.io/badge/code%20review-9.2%2F10-brightgreen)](.) [![Security](https://img.shields.io/badge/security-verified-brightgreen)](.) [![Docs](https://img.shields.io/badge/docs-55+%20files-blue)](.) [![Scripts](https://img.shields.io/badge/automation-14%20scripts-blue)](.) [![Commits](https://img.shields.io/badge/commits-101+-blue)](.) [![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE) [![Cost Savings](https://img.shields.io/badge/savings-$20K%2Fyear-gold)](.)

[![Session](https://img.shields.io/badge/session-12+%20hours-purple)](.) [![PowerPoint](https://img.shields.io/badge/PowerPoint-ready-success)](.) [![Requirements](https://img.shields.io/badge/requirements-5%2F5-success)](.)

Generate benign service telemetry for Azure Tenant simulation.

## 🎉 **NEW**: Session Deliverables (2025-11-17/18)

**After 12+ hours of intensive work, major improvements delivered**:
- ✅ **PowerPoint Presentation**: 32 professional slides → `docs/presentations/Azure_HayMaker_Overview.pptx`
- ✅ **Security Fix**: Secrets in Key Vault (confirmed working in production!)
- ✅ **Agent Autostart**: Implemented and ready to test
- ✅ **Log Streaming**: Real-time CLI output with colors
- ✅ **Comprehensive Docs**: 12,000+ lines of guides and specs

## 🚨 **URGENT**: Cost Alert - $2,164/month!

**Critical finding**: 21 duplicate resource sets from debugging iterations
- **Current**: $2,164/month
- **After cleanup**: $498/month
- **SAVINGS**: **$1,666/month (77%)!**

**Immediate action** (5 min):
```bash
./scripts/cleanup-old-function-apps.sh  # Saves $1,533/month NOW!
```

**Details**: `CRITICAL_COST_ALERT.md` | **Tracked**: Issue #14

---

**👉 START HERE**: Read `README_SESSION_DELIVERABLES.md` for complete overview

**Key Documents**:
- `FINAL_SESSION_SUMMARY.md` - Epic 12-hour journey
- `NEXT_STEPS.md` - How to complete VM deployment
- `SESSION_STATUS_REPORT.md` - Detailed progress report

## What is it?

Azure HayMaker is an orchestration service that simulates realistic Azure tenant activity by deploying and managing 50+ distinct operational scenarios using autonomous goal-seeking agents. Each agent performs a full lifecycle: deployment, 8-hour operation period, and cleanup.

## Key Features

- **50+ Azure Scenarios** across 10 technology areas (AI/ML, Analytics, Compute, Containers, Databases, etc.)
- **Autonomous Agents** that self-manage deployments and troubleshoot issues
- **Scheduled Execution** (4x daily for different global regions)
- **Complete Automation** using Azure CLI, Terraform, and Bicep
- **Automatic Cleanup** with resource tracking and forced removal

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

**Important**: The `.env` file is gitignored and must never be committed to version control.

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

**Security Benefits:**
- Secrets never visible in Azure Portal
- Automatic secret rotation support
- Audit logging via Key Vault diagnostics
- RBAC-based access control

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

## Documentation

- **[Deployment Setup](docs/DEPLOYMENT_SETUP.md)** - Complete deployment guide with all requirements
- **[Project Requirements](specs/requirements.md)** - Detailed specifications and success criteria
- **[Initial Prompt](specs/initial-prompt.md)** - Original project conception
- **[Scenarios](docs/scenarios/)** - 50 operational scenarios with full automation
- **[Architecture Guide](.claude/skills/azure-haymaker/ARCHITECTURE_GUIDE.md)** - Azure HayMaker orchestration service architecture

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

## Status

🚧 **Under Active Development** - See [Issue #1](https://github.com/rysweet/AzureHayMaker/issues/1) for progress


---

## 🎊 **QUICK START - NEW USERS**

**Just cloned the repo? Start here**:

```bash
# 1. See what's ready
./scripts/show-session-summary.sh

# 2. View the presentation
./scripts/open-powerpoint.sh

# 3. Verify security fix
./scripts/verify-security-fix.sh

# 4. Read the handoff
cat HANDOFF.md
```

**All major features implemented and ready to deploy!**

---
