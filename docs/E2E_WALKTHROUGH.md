# AzureHayMaker End-to-End Walkthrough

**Date**: 2025-11-24
**Version**: 0.1.0
**Status**: Production-Ready FastAPI Orchestrator

This walkthrough demonstrates the complete AzureHayMaker system from installation through agent deployment.

---

## 📋 Prerequisites

- Python 3.11+ (updated from 3.13 requirement)
- Azure CLI authenticated
- Docker installed (for local testing)
- Azure subscription with appropriate permissions

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker

# Install core package
uv pip install -e .

# Install CLI
cd cli
uv pip install -e .
cd ..
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your Azure details
# Required variables:
# - AZURE_TENANT_ID
# - AZURE_SUBSCRIPTION_ID
# - AZURE_CLIENT_ID
# - AZURE_CLIENT_SECRET
# - ANTHROPIC_API_KEY
```

### 3. Test Orchestrator APIs

#### Health Check
```bash
curl https://haymaker-fastapi-app.azurewebsites.net/
# Returns: {"status":"healthy","service":"azure-haymaker-orchestrator",...}
```

#### Validation
```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/validate
# Returns: {"overall_passed":true,"results":[...]}
```

#### Metrics
```bash
curl https://haymaker-fastapi-app.azurewebsites.net/api/metrics
# Returns: {"executions_total":15,"executions_running":1,...}
```

#### Execute Scenario
```bash
curl -X POST https://haymaker-fastapi-app.azurewebsites.net/api/execute \
  -H "Content-Type: application/json" \
  -d '{"scenarios":["compute-01-linux-vm-web-server"], "duration_hours": 1}'
# Returns: {"execution_id":"...","status":"started"}
```

---

## 🏗️ Architecture

**Orchestrator**: FastAPI + APScheduler on Azure App Service (P3V3, 32GB RAM)
**URL**: https://haymaker-fastapi-app.azurewebsites.net
**Image**: haymakerorchacr.azurecr.io/haymaker-orchestrator:final-working

**50 Agent Scenarios** across 10 technology areas ready for deployment.

---

## 🔧 Troubleshooting

### Python Version Fixed
**Was**: Required Python >=3.13
**Now**: Requires Python >=3.11
**Commits**: 3b7cce7, 85a73f3

### Scenarios Directory Fixed
**Issue**: "Scenarios directory not found: /docs/scenarios"
**Fix**: Dockerfile copies to /docs/scenarios at container root
**Commit**: 1cbcc8c

### Authentication Fixed
**Issue**: Key Vault auth failing
**Fix**: Set environment variables in App Service
- MAIN_SP_CLIENT_SECRET
- ANTHROPIC_API_KEY
- LOG_ANALYTICS_WORKSPACE_KEY
- AZURE_CLIENT_ID
- AZURE_CLIENT_SECRET

---

## 📊 Current Status

✅ Working: Health, Validation, Metrics, Execution APIs, Scenario Selection
⏳ In Progress: Service Principal creation, Agent deployment
⚠️ Known Issues: #30 (Functions discovery), #14 (duplicate resources)

---

For full details, see documentation in `/docs/` directory.
