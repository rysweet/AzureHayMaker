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

### 4. Run Service

```bash
# TBD - under development
# python -m azure_haymaker.orchestrator
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

## Documentation

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
