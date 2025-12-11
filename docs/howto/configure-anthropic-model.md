---
layout: default
title: Configure Anthropic Model
parent: How-To Guides
nav_order: 5
description: "Configure which Claude model to use for AI email generation"
---

# Configure Anthropic Model for AI Email Generation
{: .no_toc }

Configure which Claude model the Knowledge Worker framework uses for AI-powered email generation.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Quick Start

Set the model name via environment variable:

```bash
# Use Claude 3.5 Sonnet (default)
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Deploy knowledge workers with AI emails
haymaker kw deploy \
  --workers 25 \
  --enable-ai-generation \
  --department engineering
```

The specified model will be used for all AI email generation during the deployment.

---

## Configuration Methods

The Anthropic model name can be configured three ways (in priority order):

1. **Environment variable** (highest priority)
2. **.env file** (local development)
3. **Default value** (claude-sonnet-4-5-20250929)

### Environment Variable

Set `ANTHROPIC_MODEL` before running the CLI:

```bash
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
haymaker kw deploy --workers 10 --enable-ai-generation
```

**Validation**: The CLI validates the model name and displays it at startup:

```
[INFO] AI email generation enabled
[INFO] Model: claude-sonnet-4-5-20250929
[INFO] Estimated cost: ~$2.50 for 200 emails
```

### .env File

For local development, add to your `.env` file:

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

Load the file with the haymaker CLI:

```bash
haymaker kw deploy --workers 10 --enable-ai-generation --env-file .env
```

### Default Value

If not specified, the CLI uses `claude-sonnet-4-5-20250929` automatically:

```bash
# Uses default model
haymaker kw deploy --workers 10 --enable-ai-generation
```

---

## Supported Models

### Current Production Models

These Claude models are tested and supported for AI email generation:

| Model Name | Model ID | Use Case | Cost (per 1M tokens) |
|:-----------|:---------|:---------|:---------------------|
| Claude 3.5 Sonnet (Oct 2024) | `claude-sonnet-4-5-20250929` | **Recommended** - Best balance of quality and cost | Input: $3.00, Output: $15.00 |
| Claude 3.5 Sonnet (Jun 2024) | `claude-3-5-sonnet-20240620` | Previous version, still supported | Input: $3.00, Output: $15.00 |
| Claude 3 Opus | `claude-3-opus-20240229` | Highest quality, slowest, most expensive | Input: $15.00, Output: $75.00 |
| Claude 3 Sonnet | `claude-3-sonnet-20240229` | Good balance, legacy | Input: $3.00, Output: $15.00 |
| Claude 3 Haiku | `claude-3-haiku-20240307` | Fastest, cheapest, lower quality | Input: $0.25, Output: $1.25 |

**Default**: `claude-sonnet-4-5-20250929` provides excellent email quality at reasonable cost.

### Example Configurations

```bash
# High quality for important demonstrations
export ANTHROPIC_MODEL=claude-3-opus-20240229
haymaker kw deploy --workers 50 --enable-ai-generation

# Cost-optimized for large-scale testing
export ANTHROPIC_MODEL=claude-3-haiku-20240307
haymaker kw deploy --workers 200 --enable-ai-generation

# Recommended production setting
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
haymaker kw deploy --workers 100 --enable-ai-generation
```

---

## Finding Model Names

### Official Anthropic Documentation

Current model names are listed in the [Anthropic API documentation](https://docs.anthropic.com/en/docs/models-overview):

1. Visit https://docs.anthropic.com/en/docs/models-overview
2. Find the "Model Names" section
3. Copy the exact model ID (e.g., `claude-sonnet-4-5-20250929`)

### Check Available Models

The haymaker CLI validates model names against the Anthropic API. Invalid names produce clear error messages:

```bash
export ANTHROPIC_MODEL=invalid-model-name
haymaker kw deploy --workers 10 --enable-ai-generation

# Output:
# [ERROR] Invalid Anthropic model: invalid-model-name
# [ERROR] See https://docs.anthropic.com/en/docs/models-overview for valid models
```

---

## Updating for New Models

When Anthropic releases new models, update your configuration:

### Step 1: Find the New Model ID

Check Anthropic's [model documentation](https://docs.anthropic.com/en/docs/models-overview) for the latest release:

```
New Model: Claude 3.5 Sonnet (December 2024)
Model ID: claude-3-5-sonnet-20241215
```

### Step 2: Update Configuration

Update your environment variable or `.env` file:

```bash
# Update environment variable
export ANTHROPIC_MODEL=claude-3-5-sonnet-20241215

# Or update .env file
echo "ANTHROPIC_MODEL=claude-3-5-sonnet-20241215" >> .env
```

### Step 3: Verify

Deploy a small test to confirm the model works:

```bash
haymaker kw deploy \
  --workers 5 \
  --duration 1 \
  --enable-ai-generation \
  --email-directive "Test email for new model"

# Check logs for confirmation:
# [INFO] Model: claude-3-5-sonnet-20241215
# [INFO] Email generation test: SUCCESS
```

### Step 4: Update Default (Optional)

If you want to update the default for your team, modify your shared `.env.example` file:

```bash
# .env.example
ANTHROPIC_MODEL=claude-3-5-sonnet-20241215
```

Commit this change so team members get the new default:

```bash
git add .env.example
git commit -m "Update default Anthropic model to claude-3-5-sonnet-20241215"
git push
```

---

## Cost Estimation

The CLI estimates costs before deployment. Different models have different pricing:

### Cost Comparison

For a typical 25-worker deployment with 200 emails over 2 hours:

| Model | Estimated Cost | Email Quality |
|:------|:--------------|:-------------|
| Claude 3 Haiku | ~$0.25 | Good |
| Claude 3 Sonnet | ~$2.50 | Very Good |
| Claude 3.5 Sonnet | ~$2.50 | Excellent |
| Claude 3 Opus | ~$12.50 | Outstanding |

**Example CLI Output**:

```bash
haymaker kw deploy --workers 25 --enable-ai-generation

# Output:
# [INFO] AI email generation enabled
# [INFO] Model: claude-sonnet-4-5-20250929
# [INFO] Estimated emails: 200
# [INFO] Estimated cost: ~$2.50
# [INFO] Proceed? (y/n):
```

### Cost Controls

Limit costs with deployment duration and worker count:

```bash
# Short test run (~$0.50)
haymaker kw deploy \
  --workers 10 \
  --duration 1 \
  --enable-ai-generation

# Full simulation (~$10.00)
haymaker kw deploy \
  --workers 100 \
  --duration 4 \
  --enable-ai-generation
```

---

## Troubleshooting

### Model Name Not Recognized

**Problem**: `Invalid model name: claude-3-5-sonnet-latest`

**Solution**: Use exact model IDs from Anthropic documentation. Aliases like "latest" are not supported:

```bash
# Wrong - using alias
export ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# Correct - using exact ID
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

### API Key Issues

**Problem**: `API key invalid for model claude-3-opus-20240229`

**Solution**: Verify your API key has access to the requested model:

```bash
# Check your API key tier at https://console.anthropic.com/settings/plans
# Some models require specific API tiers

# Fallback to widely-available model
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

### Cost Overruns

**Problem**: Deployment cost exceeded budget

**Solution**: Use cheaper models for testing, reserve expensive models for production:

```bash
# Development testing - use Haiku
export ANTHROPIC_MODEL=claude-3-haiku-20240307
haymaker kw deploy --workers 100 --duration 2

# Production demo - use Sonnet
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
haymaker kw deploy --workers 50 --duration 4
```

### Outdated Model

**Problem**: `Model deprecated: claude-3-sonnet-20240229`

**Solution**: Update to the latest model version:

```bash
# Check Anthropic docs for current models
# https://docs.anthropic.com/en/docs/models-overview

# Update to latest Sonnet
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

---

## Production Deployment

For Azure Function App deployments, set the model via Application Settings:

### Azure Portal

1. Navigate to Function App → Configuration → Application Settings
2. Add new setting:
   - **Name**: `ANTHROPIC_MODEL`
   - **Value**: `claude-sonnet-4-5-20250929`
3. Click "Save" and restart the Function App

### Azure CLI

```bash
az functionapp config appsettings set \
  --name haymaker-func \
  --resource-group haymaker-rg \
  --settings ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

### Bicep Template

Add to your `main.bicep` file:

```bicep
resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: functionAppName
  properties: {
    siteConfig: {
      appSettings: [
        {
          name: 'ANTHROPIC_API_KEY'
          value: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/anthropic-api-key/)'
        }
        {
          name: 'ANTHROPIC_MODEL'
          value: 'claude-sonnet-4-5-20250929'
        }
      ]
    }
  }
}
```

Deploy the updated infrastructure:

```bash
az deployment group create \
  --resource-group haymaker-rg \
  --template-file infra/bicep/main.bicep \
  --parameters anthropicModelName=claude-sonnet-4-5-20250929
```

---

## Related Documentation

- [AI Email Generation Guide](/AzureHayMaker/knowledge-worker-framework/ai-email-generation) - Complete guide to AI-powered email generation
- [Knowledge Worker Tutorial](/AzureHayMaker/knowledge-worker-framework/tutorial) - End-to-end tutorial for deploying workers
- [CLI Environment Variables](/AzureHayMaker/cli/#environment-variables) - All CLI configuration options
- [Cost Management](/AzureHayMaker/howto/manage-costs) - Managing Azure HayMaker costs

---

## Additional Resources

- **Anthropic Models Overview**: https://docs.anthropic.com/en/docs/models-overview
- **Claude API Pricing**: https://www.anthropic.com/pricing
- **Anthropic Console**: https://console.anthropic.com/
- **Release Notes**: https://docs.anthropic.com/en/release-notes/overview
