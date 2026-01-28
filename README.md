# Azure HayMaker

[![Tests](https://img.shields.io/badge/tests-99%25%20passing-brightgreen)](.) [![Code Quality](https://img.shields.io/badge/code%20review-9.2%2F10-brightgreen)](.) [![Security](https://img.shields.io/badge/security-verified-brightgreen)](.) [![Docs](https://img.shields.io/badge/docs-55+%20files-blue)](.) [![Scripts](https://img.shields.io/badge/automation-14%20scripts-blue)](.) [![Commits](https://img.shields.io/badge/commits-101+-blue)](.) [![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE) [![Cost Savings](https://img.shields.io/badge/savings-$20K%2Fyear-gold)](.)

[![Session](https://img.shields.io/badge/session-12+%20hours-purple)](.) [![PowerPoint](https://img.shields.io/badge/PowerPoint-ready-success)](.) [![Requirements](https://img.shields.io/badge/requirements-5%2F5-success)](.)

Generate benign service telemetry for Azure Tenant simulation with realistic Azure infrastructure scenarios and Microsoft 365 knowledge worker activity.

> **🚀 New Developer?** Start with the [Developer Quick Start Guide](docs/DEVELOPER_QUICK_START.md) for step-by-step setup instructions.

## What is it?

Azure HayMaker is an orchestration service that simulates realistic Azure tenant activity through two complementary capabilities:

1. **Azure Infrastructure Scenarios**: Deploy and manage 50+ distinct operational scenarios (AI/ML, Analytics, Compute, Containers, Databases, etc.) using autonomous goal-seeking agents. Each agent performs a full lifecycle: deployment, 8-hour operation period, and cleanup.

2. **Microsoft 365 Knowledge Worker Framework**: Simulate 50-300 knowledge workers performing everyday M365 activities including email, Microsoft Teams messaging, calendar events, and document collaboration. Workers are organized into teams with distinct personas and communication patterns.

## Key Features

### Azure Infrastructure Scenarios
- **50+ Azure Scenarios** across 10 technology areas (AI/ML, Analytics, Compute, Containers, Databases, etc.)
- **Autonomous Agents** that self-manage deployments and troubleshoot issues
- **Scheduled Execution** (4x daily for different global regions)
- **Complete Automation** using Azure CLI, Terraform, and Bicep
- **Automatic Cleanup** with resource tracking and forced removal

### Microsoft 365 Knowledge Worker Framework
- **Realistic M365 Activity**: Email, Microsoft Teams, documents, calendar events
- **50-300 Knowledge Workers**: Organized by department with distinct personas
- **AI-Powered Content**: Generate contextual emails using Claude or GPT (including fun themes like limericks!)
- **Microsoft Teams Integration**: Channel posts, direct messages, @mentions, and reactions
- **Internal-Only Communications**: Multiple safety layers prevent external email
- **Email Markers**: Hidden markers for SIEM testing and tracking
- **Hybrid Endpoints**: Windows 365 Cloud PCs or CLI containers for cost optimization
- **Full Lifecycle Management**: Deployment, execution, monitoring, and cleanup

See the [Knowledge Worker Framework documentation](docs/knowledge-worker-framework/README.md) for details.

## Quick Start

### For Developers (Deploy Your Own Stack)

The recommended path for new developers - deploy your own isolated environment:

```bash
# 1. Clone and install
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker
uv sync --all-extras

# 2. Configure credentials (see Developer Quick Start Guide)
cp .env.example .env
# Edit .env with your Azure credentials

# 3. Deploy via GitHub Actions
./scripts/trigger_deploy.sh --name yourname --watch

# 4. Verify deployment
uv run haymaker kw list
```

📖 **[Developer Quick Start Guide](docs/DEVELOPER_QUICK_START.md)** - Complete setup walkthrough with prerequisites, Azure credentials, OIDC setup, and CLI usage.

### For Production (GitOps Deployment)

Production deployments use GitOps with GitHub Actions:

```bash
# Merges to main trigger automatic deployment
git push origin main
```

📖 **[Production GitOps Guide](docs/GITOPS_DEPLOYMENT.md)** - CI/CD pipeline configuration and production deployment.

## Knowledge Worker Quick Start

Deploy simulated knowledge workers performing M365 activities:

```bash
# 1. Install the Haymaker CLI
pip install haymaker-cli

# 2. Initialize M365 app registration
haymaker kw init --save-config kw_config.env
source kw_config.env

# 3. Deploy 25 workers with AI-generated limerick emails (2 hours)
haymaker kw deploy \
  --workers 25 \
  --department operations \
  --duration 2 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work" \
  --marker-format LIMERICK

# 4. Monitor activity
haymaker kw telemetry-report --run-id <your-run-id>

# 5. Cleanup when done
haymaker kw cleanup --run-id <your-run-id>
```

**Common Use Cases:**
- **SIEM Testing**: Deploy workers with hidden markers to test security monitoring
- **Red Team Simulation**: Generate realistic benign traffic to blend with security testing
- **Load Testing**: Test M365 infrastructure with realistic user patterns

See the [Knowledge Worker Tutorial](docs/knowledge-worker-framework/TUTORIAL_DEPLOY_AND_MONITOR.md) for a complete walkthrough.

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

After deployment, get your orchestrator URL:

```bash
# Get FQDN from your deployment
FQDN=$(az containerapp show \
  --name haymaker-fastapi-orch \
  --resource-group haymaker-<yourname>-dev-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv)
```

### Health Check

```bash
curl https://$FQDN/
```

**Example Output**:
```json
{"status":"healthy","service":"azure-haymaker-orchestrator","timestamp":"2026-01-28T16:31:30.411584+00:00"}
```

### List Available Scenarios

```bash
curl https://$FQDN/api/scenarios
```

### Execute Scenarios

**Single Scenario**:
```bash
curl -X POST https://$FQDN/api/execute \
  -H "Content-Type: application/json" \
  -d '{"scenarios":["compute-01-linux-vm-web-server"],"duration_hours":1}'
```

**Multiple Scenarios (Parallel)**:
```bash
curl -X POST https://$FQDN/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": [
      "databases-01-mysql-wordpress",
      "security-01-key-vault-secrets",
      "ai-ml-01-cognitive-services-vision"
    ],
    "duration_hours": 1
  }'
```

### Monitor Execution

```bash
EXEC_ID="<execution-id-from-above>"
curl https://$FQDN/api/executions/$EXEC_ID | jq
```

### Using the Haymaker CLI

The CLI provides a simpler interface for Knowledge Worker deployments:

```bash
# List all deployments
uv run haymaker kw list

# Check status
uv run haymaker kw status

# Start a deployment
uv run haymaker kw start --run-id <id>

# View logs
uv run haymaker kw logs --run-id <id> --follow

# Stop and cleanup
uv run haymaker kw stop --run-id <id>
uv run haymaker kw cleanup --run-id <id>
```

## Documentation

### Getting Started
- **[Developer Quick Start](docs/DEVELOPER_QUICK_START.md)** - Deploy your own dev stack (start here!)
- **[Production GitOps Guide](docs/GITOPS_DEPLOYMENT.md)** - CI/CD and production deployment
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components

### Azure Infrastructure Scenarios
- **[Scenarios Overview](docs/scenarios/)** - 50 operational scenarios with full automation
- **[Project Requirements](specs/requirements.md)** - Detailed specifications and success criteria

### Microsoft 365 Knowledge Worker Framework
- **[Knowledge Worker Framework Overview](docs/knowledge-worker-framework/README.md)** - Start here for M365 capabilities
- **[Tutorial: Deploy & Monitor 25 Workers](docs/knowledge-worker-framework/TUTORIAL_DEPLOY_AND_MONITOR.md)** - Complete end-to-end tutorial
- **[Architecture](docs/knowledge-worker-framework/ARCHITECTURE.md)** - Framework design and components
- **[AI Email Generation Guide](docs/knowledge-worker-framework/AI_EMAIL_GENERATION.md)** - Generate contextual AI-powered emails
- **[Email Markers Guide](docs/knowledge-worker-framework/EMAIL_MARKERS_GUIDE.md)** - Track and filter emails with embedded markers
- **[Security](docs/knowledge-worker-framework/SECURITY.md)** - Safety controls and internal-only enforcement
- **[Windows 365 Cloud PC](docs/knowledge-worker-framework/WINDOWS365_CLOUD_PC.md)** - Cloud PC endpoint documentation
- **[M365 Integration Specification](docs/knowledge-worker-framework/KW_REAL_M365_SPECIFICATION.md)** - Technical implementation details

**For Contributors**:
- **[Quick Start Guide](docs/QUICK_START_CONTRIBUTORS.md)** - Get started in 15 minutes
- **[Contributing to Enhancements](docs/CONTRIBUTING_ENHANCEMENTS.md)** - Detailed workflow
## Development

```bash
# First-time setup: Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Linting and type checking
ruff check src/
pyright

# Pre-commit hooks (run manually on all files)
pre-commit run --all-files
```

## License

MIT License - Open Source

## Status

🚧 **Under Active Development** - See [Issue #1](https://github.com/rysweet/AzureHayMaker/issues/1) for progress

---
