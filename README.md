# Azure HayMaker

Generate benign service telemetry for Azure Tenant simulation.

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
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_CLIENT_ID="your-client-id"
export KEY_VAULT_URL="https://your-keyvault.vault.azure.net"
export SIMULATION_SIZE="small"
# ... more variables (see .env.example)
```

**Configuration Priority Order:**
1. Environment variables (explicit override) - highest priority
2. Azure Key Vault (production secrets)
3. .env file (local development only) - lowest priority

### 3. Run Tests

```bash
pytest
```

### 4. Run Service

```bash
# TBD - under development
# python -m azure_haymaker.orchestrator
```

**Security Note:** The .env file should only be used for local development. Production deployments must use Azure Key Vault for secrets management.

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
