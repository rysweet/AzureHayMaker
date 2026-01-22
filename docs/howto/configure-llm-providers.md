# How to Configure LLM Providers

Configure Azure HayMaker to use different LLM providers for content generation.

## Overview

Azure HayMaker supports multiple LLM providers through a unified abstraction layer:

- **Anthropic Claude** - Claude models (claude-3-opus, claude-3-sonnet)
- **Azure OpenAI** - GPT-4 and GPT-4o models via Azure-hosted endpoints
- **Azure AI Foundry** - Open-source models (Llama, Mistral, Phi) via Azure ML inference

## Prerequisites

- Azure subscription with appropriate permissions
- For Azure providers: DefaultAzureCredential or API key authentication
- For Anthropic: Valid API key

## Quick Start

### Option 1: Anthropic Claude (Default)

```bash
# Set API key in environment
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
```

```python
from azure_haymaker.llm import create_llm_client, LLMConfig

config = LLMConfig(
    provider="anthropic",
    model="claude-3-sonnet-20241022",
    api_key=os.environ["ANTHROPIC_API_KEY"]
)
client = create_llm_client(config)
```

### Option 2: Azure OpenAI

```bash
# Set Azure OpenAI configuration
export AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
export AZURE_OPENAI_DEPLOYMENT=gpt-4
export AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

```python
from azure_haymaker.llm import create_llm_client, LLMConfig

config = LLMConfig(
    provider="azure_openai",
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    # Uses DefaultAzureCredential by default if no api_key provided
)
client = create_llm_client(config)
```

### Option 3: Azure AI Foundry

```bash
# Set Azure AI Foundry configuration
export AZURE_AI_FOUNDRY_ENDPOINT=https://<your-endpoint>.inference.ml.azure.com
export AZURE_AI_FOUNDRY_MODEL=Meta-Llama-3-70B-Instruct
```

```python
from azure_haymaker.llm import create_llm_client, LLMConfig

config = LLMConfig(
    provider="azure_ai_foundry",
    endpoint=os.environ["AZURE_AI_FOUNDRY_ENDPOINT"],
    model=os.environ["AZURE_AI_FOUNDRY_MODEL"],
    # Uses DefaultAzureCredential by default
)
client = create_llm_client(config)
```

## Authentication Options

### Azure Managed Identity (Recommended for Production)

Azure providers use `DefaultAzureCredential` automatically when no API key is provided. This supports:

- Managed Identity (in Azure)
- Azure CLI credentials (local development)
- Environment variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`)

```python
# No api_key = uses DefaultAzureCredential
config = LLMConfig(
    provider="azure_openai",
    endpoint="https://myresource.openai.azure.com",
    deployment="gpt-4"
)
```

### API Key Authentication

```python
# Explicit API key
config = LLMConfig(
    provider="azure_openai",
    endpoint="https://myresource.openai.azure.com",
    deployment="gpt-4",
    api_key="your-api-key-here"
)
```

## Configuration via OrchestratorConfig

In the orchestrator configuration, set the LLM provider:

```python
from azure_haymaker.models.config import OrchestratorConfig, LLMConfig

config = OrchestratorConfig(
    llm_config=LLMConfig(
        provider="azure_openai",
        endpoint="https://myresource.openai.azure.com",
        deployment="gpt-4"
    ),
    # ... other config
)
```

## Environment Variable Reference

| Variable | Provider | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic | API key for Anthropic Claude |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI | Deployment name (e.g., gpt-4) |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI | API version (default: 2024-02-15-preview) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | API key (optional if using managed identity) |
| `AZURE_AI_FOUNDRY_ENDPOINT` | Azure AI Foundry | ML inference endpoint |
| `AZURE_AI_FOUNDRY_MODEL` | Azure AI Foundry | Model name |

## Troubleshooting

### "DefaultAzureCredential failed"

Ensure you have valid Azure credentials:

```bash
# Login with Azure CLI
az login

# Or set environment variables
export AZURE_CLIENT_ID=<client-id>
export AZURE_TENANT_ID=<tenant-id>
export AZURE_CLIENT_SECRET=<client-secret>
```

### "Model not found"

Verify the model/deployment exists in your Azure resource:

```bash
# For Azure OpenAI
az cognitiveservices account deployment list \
  --name <resource-name> \
  --resource-group <resource-group>

# For Azure AI Foundry
az ml online-endpoint list --resource-group <resource-group>
```

### Rate Limiting

All providers implement exponential backoff. For high-volume use, consider:

- Multiple deployments
- Adjusting `max_retries` in config
- Using Azure AI Foundry for burst capacity

## See Also

- [LLM Provider API Reference](../reference/llm-providers.md)
- [Configure Anthropic Model](./configure-anthropic-model.md)
- [Architecture Overview](../ARCHITECTURE.md)
