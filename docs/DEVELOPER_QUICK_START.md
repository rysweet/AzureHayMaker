# Developer Quick Start Guide

This guide walks you through setting up your own Azure HayMaker development environment and deploying your first orchestrator and workload.

## Prerequisites

Before you begin, ensure you have:

### Required Tools

| Tool | Version | Installation |
|------|---------|--------------|
| **Azure CLI** | 2.50+ | `curl -sL https://aka.ms/InstallAzureCLIDeb \| sudo bash` |
| **GitHub CLI** | 2.0+ | `sudo apt install gh` or [gh releases](https://github.com/cli/cli/releases) |
| **Python** | 3.11+ | System package or pyenv |
| **uv** | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Git** | 2.30+ | System package |

### AI Service (Choose One)

You'll need access to an AI service for knowledge worker content generation:

**Option A: Azure AI Foundry (Recommended)**
```bash
# Create Azure AI resource in Azure Portal or CLI
az cognitiveservices account create \
  --name my-ai-service \
  --resource-group my-rg \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Deploy a model (e.g., gpt-4o)
az cognitiveservices account deployment create \
  --name my-ai-service \
  --resource-group my-rg \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-05-13" \
  --model-format OpenAI
```

**Option B: Anthropic Claude**
- Sign up at [console.anthropic.com](https://console.anthropic.com)
- Create an API key
- Set `ANTHROPIC_API_KEY` in your `.env` file

**Option C: OpenAI Direct**
- Sign up at [platform.openai.com](https://platform.openai.com)
- Create an API key
- Set `OPENAI_API_KEY` in your `.env` file

---

## Step 1: Azure Credentials Setup

### 1.1 Create a Service Principal

Each developer needs their own Service Principal for isolated deployments:

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "Your Subscription Name"

# Create a Service Principal with Contributor access
az ad sp create-for-rbac \
  --name "haymaker-dev-$(whoami)" \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv) \
  --sdk-auth
```

Save the output - you'll need these values:

```json
{
  "clientId": "a1ebf78f-xxxx-xxxx-xxxx-939641d2f28d",
  "clientSecret": "abc123...",
  "subscriptionId": "9b00bc5e-xxxx-xxxx-xxxx-02a9d9277b16",
  "tenantId": "3cd87a41-xxxx-xxxx-xxxx-cefdecd9a2d1"
}
```

### 1.2 Create OIDC Federated Credentials (Optional but Recommended)

For secretless GitHub Actions authentication:

```bash
# Get your Service Principal Object ID
SP_OBJECT_ID=$(az ad sp show --id "a1ebf78f-xxxx-xxxx-xxxx-939641d2f28d" --query id -o tsv)

# Create federated credential for main branch
az ad app federated-credential create \
  --id $SP_OBJECT_ID \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/AzureHayMaker:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Create federated credential for pull requests
az ad app federated-credential create \
  --id $SP_OBJECT_ID \
  --parameters '{
    "name": "github-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/AzureHayMaker:pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

---

## Step 2: Clone Repository and Configure Environment

### 2.1 Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/AzureHayMaker.git
cd AzureHayMaker
```

### 2.2 Install Dependencies

```bash
# Install Python dependencies
uv sync --all-extras

# Install pre-commit hooks
pre-commit install
```

### 2.3 Create Your .env File

Create a `.env` file in the repository root:

```bash
cat > .env << 'EOF'
# Azure Credentials (from Step 1)
AZURE_TENANT_ID=3cd87a41-xxxx-xxxx-xxxx-cefdecd9a2d1
AZURE_SUBSCRIPTION_ID=9b00bc5e-xxxx-xxxx-xxxx-02a9d9277b16
AZURE_CLIENT_ID=a1ebf78f-xxxx-xxxx-xxxx-939641d2f28d
MAIN_SP_CLIENT_SECRET=abc123...  # Only needed if not using OIDC

# Deployment Configuration
NAMING_PREFIX=jsmith              # Use your username or initials
ENVIRONMENT=dev
LOCATION=westus2
SIMULATION_SIZE=small             # small, medium, large

# AI Service (choose one)
# Option A: Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://my-ai-service.openai.azure.com/
AZURE_OPENAI_API_KEY=abc123...
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Option B: Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Option C: OpenAI
OPENAI_API_KEY=sk-...
EOF
```

### 2.4 Authenticate GitHub CLI

```bash
gh auth login
```

---

## Step 3: Deploy Your First Orchestrator

### 3.1 Trigger the Deployment Workflow

Use the provided script to deploy your isolated stack:

```bash
# Make the script executable
chmod +x scripts/trigger_deploy.sh

# Deploy with your naming prefix
./scripts/trigger_deploy.sh --name jsmith --watch
```

Or trigger directly with `gh`:

```bash
source .env

gh workflow run deploy-dev-stack.yml \
  -f naming_prefix="jsmith" \
  -f environment="dev" \
  -f location="westus2" \
  -f simulation_size="small" \
  -f azure_tenant_id="$AZURE_TENANT_ID" \
  -f azure_subscription_id="$AZURE_SUBSCRIPTION_ID" \
  -f azure_client_id="$AZURE_CLIENT_ID"

# Watch the deployment
gh run watch
```

### 3.2 What Gets Deployed

The workflow creates these resources in your isolated resource group:

| Resource | Name Pattern | Purpose |
|----------|--------------|---------|
| **Resource Group** | `haymaker-jsmith-dev-rg` | Contains all resources |
| **Container Registry** | `hmjsmithdev<hash>` | Stores orchestrator image |
| **Container App Environment** | `haymaker-fastapi-cae` | Runs container apps |
| **Container App** | `haymaker-fastapi-orch` | The orchestrator service |
| **Key Vault** | `haymaker-dev-<id>-kv` | Stores secrets |
| **Service Bus** | `haymaker-dev-<id>-bus` | Message queue |
| **Storage Account** | `haymakerdv<id>` | Table storage for state |
| **Log Analytics** | `haymaker-dev-<id>-logs` | Logging and monitoring |

### 3.3 Verify Deployment

After the workflow completes (~10-15 minutes):

```bash
# Get the orchestrator URL
FQDN=$(az containerapp show \
  --name haymaker-fastapi-orch \
  --resource-group haymaker-jsmith-dev-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv)

# Test health endpoint
curl https://$FQDN/
```

Expected response:
```json
{"status":"healthy","service":"azure-haymaker-orchestrator","timestamp":"2026-01-28T16:31:30.411584+00:00"}
```

---

## Step 4: Using the Haymaker CLI

The Haymaker CLI lets you manage Knowledge Worker deployments.

### 4.1 List Deployments

```bash
uv run haymaker kw list
```

Example output:
```
run_id       name             status   phase         worker_count
-----------  ---------------  -------  ------------  ------------
kw-68be9954  deployment-2     pending  initializing  0           
kw-8d029eb9  deployment-1     pending  initializing  0           
kw-f673db1c  test-deployment  pending  initializing  0           
```

### 4.2 Check Deployment Status

```bash
# All deployments
uv run haymaker kw status

# Specific deployment
uv run haymaker kw status --run-id kw-68be9954

# JSON output for scripting
uv run haymaker kw status --format json
```

Example output:
```
? kw-68be9954: pending (initializing)
  Workers: 0
  Started: None
```

### 4.3 Start a Deployment

```bash
uv run haymaker kw start --run-id kw-68be9954
```

Example output:
```
Deployment kw-68be9954 started.
```

### 4.4 Monitor Running Deployment

```bash
# Check status
uv run haymaker kw status --run-id kw-68be9954

# View logs
uv run haymaker kw logs --run-id kw-68be9954 --lines 50

# Follow logs in real-time
uv run haymaker kw logs --run-id kw-68be9954 --follow
```

### 4.5 Stop and Cleanup

```bash
# Stop a running deployment
uv run haymaker kw stop --run-id kw-68be9954

# Clean up resources
uv run haymaker kw cleanup --run-id kw-68be9954
```

### 4.6 CLI Command Reference

| Command | Description |
|---------|-------------|
| `haymaker kw list` | List all deployments |
| `haymaker kw status` | Show status of all or specific deployment |
| `haymaker kw start --run-id <id>` | Start a deployment |
| `haymaker kw stop --run-id <id>` | Stop a running deployment |
| `haymaker kw restart --run-id <id>` | Restart a deployment |
| `haymaker kw logs --run-id <id>` | View deployment logs |
| `haymaker kw cleanup --run-id <id>` | Clean up deployment resources |
| `haymaker kw delete-worker --run-id <id>` | Delete specific workers |

---

## Step 5: Cleanup

When you're done developing, clean up your Azure resources:

```bash
# Delete the entire resource group
az group delete --name haymaker-jsmith-dev-rg --yes --no-wait

# Check deletion status
az group show --name haymaker-jsmith-dev-rg --query "properties.provisioningState" 2>/dev/null || echo "Deleted"
```

> **Note**: Container App Environments can take 10-15 minutes to fully delete.

---

## Troubleshooting

### Deployment Stuck at "pending (initializing)"

Check if `AZURE_CLIENT_ID` is set in the container:

```bash
az containerapp show \
  --name haymaker-fastapi-orch \
  --resource-group haymaker-jsmith-dev-rg \
  --query "properties.template.containers[0].env[?name=='AZURE_CLIENT_ID']"
```

If missing, redeploy via the GitHub workflow.

### Container App Not Starting

Check container logs:

```bash
az containerapp logs show \
  --name haymaker-fastapi-orch \
  --resource-group haymaker-jsmith-dev-rg \
  --tail 50
```

### OIDC Authentication Failing

Verify federated credentials are configured correctly:

```bash
az ad app federated-credential list --id $AZURE_CLIENT_ID
```

### GitHub Workflow Not Triggering

Ensure the workflow exists on the default branch (main):

```bash
gh workflow list
```

---

## Next Steps

- [Knowledge Worker Framework Documentation](knowledge-worker-framework/README.md)
- [Azure Infrastructure Scenarios](scenarios/)
- [CLI Reference](CLI.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md)

---

## Quick Reference Card

```bash
# Deploy your stack
./scripts/trigger_deploy.sh --name myname --watch

# Check health
curl https://haymaker-fastapi-orch.<your-env>.azurecontainerapps.io/

# List deployments
uv run haymaker kw list

# Start a deployment
uv run haymaker kw start --run-id <id>

# Check status
uv run haymaker kw status

# View logs
uv run haymaker kw logs --run-id <id> --follow

# Cleanup
az group delete --name haymaker-myname-dev-rg --yes
```
