# AI-Generated Knowledge Worker Emails

**Purpose**: Generate realistic email content using AI models to enhance Knowledge Worker simulations with context-appropriate messaging.

**Last Updated**: 2025-12-11

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [CLI Options](#cli-options)
4. [Common Use Cases](#common-use-cases)
5. [Email Markers](#email-markers)
6. [Cost Management](#cost-management)
7. [Troubleshooting](#troubleshooting)

---

## Overview

By default, Knowledge Worker emails use simple templated content. AI email generation adds realistic, contextual email bodies that match worker personas (engineering, legal, HR, etc.) for more authentic telemetry.

**Default Email**:
```
Subject: Activity 5 from kw-engi-001
Body: Automated activity generated at 2025-12-10T15:30:00Z
```

**AI-Generated Email**:
```
Subject: Activity 5 from kw-engi-001 [MARKER:engi-001-00005]
Body: Hi team, I've pushed the latest updates to the authentication
service. The new token validation logic should address the timeout
issues we saw in staging. Let me know if you spot any problems...
```

**When to Use AI Generation**:
- Creating realistic M365 telemetry for SIEM testing
- Simulating specific communication patterns
- Red team operations requiring authentic haymaker traffic
- Testing content filtering or DLP policies

---

## Quick Start

Enable AI-generated emails with a single flag:

```bash
# Deploy with AI emails (default GPT-4 Turbo)
haymaker kw deploy \
  --workers 25 \
  --department operations \
  --enable-ai-generation

# Output:
# [INFO] AI email generation enabled (model: gpt-4-turbo)
# [INFO] Estimated cost: ~$2.50 for 200 emails
# [INFO] Creating 25 operations workers...
# [INFO] Deployment created: kw-20251210-abc123
```

The workers will generate contextual emails matching their department persona throughout the deployment duration.

---

## CLI Options

### Core Options

#### `--enable-ai-generation`

Enable AI-powered email content generation.

```bash
haymaker kw deploy --workers 10 --enable-ai-generation
```

**Default**: Disabled (uses template emails)
**Cost**: ~$0.01-0.02 per email depending on model
**Required**: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` environment variable

---

#### `--email-directive "text"`

Custom instructions for AI email generation. Overrides default persona-based prompts.

```bash
# Generate emails as limericks
haymaker kw deploy \
  --workers 25 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office topics"

# Generate security-themed emails
haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation \
  --email-directive "Focus on cybersecurity topics and compliance questions"

# Simulate urgent project communication
haymaker kw deploy \
  --workers 5 \
  --enable-ai-generation \
  --email-directive "Write urgent emails about a critical production incident"
```

**Default**: Persona-specific prompt (e.g., "Write as an engineering professional")
**Length**: Maximum 500 characters
**Examples**: See [Common Use Cases](#common-use-cases)

---

#### Model Configuration

Configure which Anthropic Claude model to use for email generation.

**Environment Variable**:
```bash
# Set model via environment variable (recommended)
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation
```

**Configuration File**:
```bash
# Or set in .env file
echo "ANTHROPIC_MODEL=claude-sonnet-4-5-20250929" >> .env

haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation \
  --env-file .env
```

**Default**: `claude-sonnet-4-5-20250929`

**Supported Models**:
- `claude-sonnet-4-5-20250929` (recommended - best balance)
- `claude-3-5-sonnet-20240620` (previous version)
- `claude-3-opus-20240229` (highest quality, most expensive)
- `claude-3-sonnet-20240229` (legacy)
- `claude-3-haiku-20240307` (fastest, cheapest)

**Cost Comparison**:
| Model | Cost per Email | Quality | Speed |
|-------|---------------|---------|-------|
| claude-3-haiku | ~$0.002 | Good | Fast |
| claude-3-sonnet | ~$0.015 | Very Good | Medium |
| claude-3-5-sonnet | ~$0.015 | Excellent | Medium |
| claude-3-opus | ~$0.075 | Outstanding | Slow |

**See Also**: [Configure Anthropic Model](/AzureHayMaker/howto/configure-anthropic-model) - Complete guide to model selection and configuration

---

### Email Marker Options

Email markers help track and identify AI-generated emails. See [EMAIL_MARKERS_GUIDE.md](./EMAIL_MARKERS_GUIDE.md) for details.

#### `--enable-markers` / `--no-enable-markers`

Control email marker injection.

```bash
# Enable markers (default)
haymaker kw deploy --workers 10 --enable-ai-generation --enable-markers

# Disable markers
haymaker kw deploy --workers 10 --enable-ai-generation --no-enable-markers
```

**Default**: Enabled
**Purpose**: Track emails for testing and analysis

---

#### `--marker-style [subject|hidden|both]`

Choose marker visibility style.

```bash
# Markers in subject only (default)
haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation \
  --marker-style subject

# Hidden markers in HTML body
haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation \
  --marker-style hidden

# Both visible and hidden markers
haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation \
  --marker-style both
```

**Default**: `subject`

**Examples**:
- `subject`: `Activity 5 from kw-engi-001 [MARKER:engi-001-00005]`
- `hidden`: Invisible HTML metadata in body
- `both`: Marker in subject + hidden metadata

---

#### `--marker-format TEXT`

Customize marker format prefix.

```bash
# Use TEST-ID prefix
haymaker kw deploy \
  --workers 25 \
  --enable-ai-generation \
  --marker-format TEST-ID

# Use custom prefix for red team ops
haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation \
  --marker-format BENIGN-RT-2025Q1
```

**Default**: `MARKER`
**Pattern**: `[{FORMAT}:{worker-id}-{sequence}-{uuid}]`

**Examples**:
- `MARKER`: `[MARKER:engi-001-00005-a3f2c1]`
- `TEST-ID`: `[TEST-ID:engi-001-00005-a3f2c1]`
- `RUN`: `[RUN:engi-001-00005-a3f2c1]`

---

## Common Use Cases

### 1. Standard Deployment with AI Emails

Deploy 25 workers generating contextual emails based on department.

```bash
haymaker kw deploy \
  --workers 25 \
  --department operations \
  --duration 8 \
  --enable-ai-generation

# Output:
# [INFO] AI email generation enabled (model: gpt-4-turbo)
# [INFO] Operations workers will generate work-appropriate emails
# [INFO] Estimated cost: ~$2.00 for ~200 emails over 8 hours
# [INFO] Creating 25 operations workers...
```

**Expected Emails**: IT operations topics, incident responses, system updates

---

### 2. Limerick Emails (Fun Testing)

Generate all emails as limericks for easy identification.

```bash
haymaker kw deploy \
  --workers 25 \
  --department marketing \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work and meetings"

# Example generated email:
# Subject: Activity 12 from kw-mark-007 [MARKER:mark-007-00012]
# Body:
# There once was a meeting at three,
# About our new campaign strategy,
# The budget looks tight,
# But the creative's just right,
# Let's launch it next week, all agree!
```

**Use Case**: Unique testing scenario, easy to filter in logs, entertaining demos

---

### 3. Security-Focused Content

Generate emails about security topics for SIEM/DLP testing.

```bash
haymaker kw deploy \
  --workers 10 \
  --department legal \
  --enable-ai-generation \
  --email-directive "Focus on data privacy, compliance, and security policies"

# Example generated email:
# Subject: Activity 8 from kw-lega-003
# Body:
# Team, I've reviewed the GDPR compliance documentation for our
# new data retention policy. We need to ensure all PII is properly
# classified and retention schedules are documented. Can we schedule
# a review meeting this week?
```

**Use Case**: Testing DLP rules, content filtering, security alerting

---

### 4. High-Volume with Cost Optimization

Deploy many workers using cheaper model.

```bash
haymaker kw deploy \
  --workers 100 \
  --department operations \
  --duration 4 \
  --enable-ai-generation \
  --ai-model gpt-3.5-turbo

# Estimated cost: ~$0.80 for ~400 emails (vs ~$4.00 with GPT-4)
```

**Tradeoff**: Lower cost, slightly less realistic content

---

### 5. Red Team with Stealth Markers

Generate benign traffic with hidden markers.

```bash
haymaker kw deploy \
  --workers 50 \
  --enable-ai-generation \
  --email-directive "Write typical office emails about projects and meetings" \
  --marker-style hidden \
  --marker-format BENIGN

# Emails appear completely normal with no visible markers
# Hidden metadata allows post-analysis filtering
```

**Use Case**: Create haymaker traffic that blends seamlessly with production

---

## Email Markers

Email markers help identify and track AI-generated emails. They're automatically added when `--enable-markers` is used (default).

### Marker Structure

```
[{FORMAT}:{worker-id}-{sequence}-{uuid}]

Example: [MARKER:engi-001-00005-a3f2c1]
```

**Components**:
- `FORMAT`: Customizable prefix (default: MARKER)
- `worker-id`: Worker identifier (e.g., engi-001)
- `sequence`: Email sequence number (5-digit, zero-padded)
- `uuid`: Short unique identifier (6 hex chars)

### Querying Emails by Marker

```bash
# Using Azure CLI + Graph API
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-user@tenant.com/messages?\$filter=contains(subject,'MARKER')" \
  --query "value[].{Subject:subject, Received:receivedDateTime}"

# Output:
# [
#   {
#     "Subject": "Activity 5 from kw-engi-001 [MARKER:engi-001-00005-a3f2c1]",
#     "Received": "2025-12-10T15:30:00Z"
#   },
#   ...
# ]
```

See [EMAIL_MARKERS_GUIDE.md](./EMAIL_MARKERS_GUIDE.md) for complete marker documentation.

---

## Cost Management

AI email generation incurs API costs. Estimate costs before deployment.

### Cost Calculator

```python
# Average emails per worker per hour by department
emails_per_hour = {
    "executive": 8,
    "legal": 6,
    "engineering": 4,
    "hr": 10,
    "finance": 7,
    "sales": 12,
    "operations": 5,
    "marketing": 8,
}

# Cost per email by model
cost_per_email = {
    "gpt-3.5-turbo": 0.002,
    "gpt-4-turbo": 0.01,
    "gpt-4o": 0.015,
    "claude-3-5-sonnet": 0.015,
}

# Example: 25 operations workers, 8 hours, GPT-4 Turbo
workers = 25
duration = 8
emails = workers * duration * emails_per_hour["operations"]  # 1000 emails
total_cost = emails * cost_per_email["gpt-4-turbo"]  # ~$10.00

# Using GPT-3.5 instead: ~$2.00
```

### Real-World Examples

| Scenario | Workers | Duration | Model | Emails | Cost |
|----------|---------|----------|-------|--------|------|
| Small test | 5 | 1h | gpt-4-turbo | ~20 | $0.20 |
| Medium deployment | 25 | 4h | gpt-4-turbo | ~500 | $5.00 |
| Large deployment | 100 | 8h | gpt-3.5-turbo | ~4000 | $8.00 |
| Red team simulation | 50 | 8h | claude-3-5-sonnet | ~2000 | $30.00 |

### Cost Optimization Tips

1. **Use GPT-3.5 for high-volume**: 5x cheaper, still realistic
2. **Shorter durations for testing**: 1-2 hours instead of 8
3. **Fewer workers initially**: Validate before scaling
4. **Set API budgets**: Configure OpenAI/Anthropic spending limits

### Monitoring Costs

Check API usage during deployment:

```bash
# OpenAI usage (requires API key)
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Anthropic usage (via dashboard)
# Visit: https://console.anthropic.com/settings/usage
```

---

## Troubleshooting

### Missing API Key

**Problem**: `Error: ANTHROPIC_API_KEY not found`

**Solution**: Set API key environment variable

```bash
# For Anthropic (Claude)
export ANTHROPIC_API_KEY=sk-ant-...

# For OpenAI (GPT)
export OPENAI_API_KEY=sk-...

# Verify
haymaker kw deploy --workers 5 --enable-ai-generation
```

**Where to get keys**:
- Anthropic: https://console.anthropic.com/settings/keys
- OpenAI: https://platform.openai.com/api-keys

---

### Rate Limit Errors

**Problem**: `RateLimitError: Requests per minute exceeded`

**Solution**: Reduce worker count or use slower email rate

```bash
# Reduce workers
haymaker kw deploy --workers 10 --enable-ai-generation  # Instead of 50

# Workers automatically space out emails to avoid rate limits
# Operations workers: ~5 emails/hour (safe)
# Sales workers: ~12 emails/hour (may hit limits at scale)
```

**Rate Limits**:
- OpenAI Tier 1: 500 requests/min (sufficient for <100 workers)
- Anthropic: 50 requests/min (sufficient for <25 workers)

---

### Email Generation Failures

**Problem**: Some emails fall back to templates

**Solution**: Check logs for API errors

```bash
# View deployment logs
haymaker logs --agent-id kw-engi-001 --tail 50

# Look for:
# [WARN] AI generation failed for email 42: API timeout
# [INFO] Falling back to template email
```

**Common causes**:
- Network timeouts: Retry automatically
- API quota exceeded: Upgrade API tier
- Invalid directive: Check `--email-directive` format

---

### Unexpected Costs

**Problem**: API costs higher than expected

**Solution**: Check actual email volume

```bash
# Query sent emails
haymaker kw telemetry-report --run-id kw-20251210-abc123

# Output shows actual email count vs expected
# Workers: 25
# Emails: 1247  # Higher than expected (25 * 8 * 5 = 1000)
# Reason: Some workers sent extra emails due to randomization
```

**Prevention**: Use `--duration 1` for testing, monitor first hour

---

### Model Not Found

**Problem**: `Error: Model gpt-4o not available`

**Solution**: Check API tier and model availability

```bash
# List available models
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data[].id'

# Use supported model
haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation \
  --ai-model gpt-4-turbo  # Widely available
```

---

### Marker Parsing Issues

**Problem**: SIEM not detecting markers

**Solution**: Verify marker format and style

```bash
# Deploy with explicit marker config
haymaker kw deploy \
  --workers 5 \
  --enable-ai-generation \
  --marker-style subject \
  --marker-format TEST

# Query one email to verify format
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-engi-001@tenant.com/messages?\$top=1" \
  --query "value[0].subject"

# Expected: "Activity 1 from kw-engi-001 [TEST:engi-001-00001-abc123]"
```

---

## Related Documentation

- [EMAIL_MARKERS_GUIDE.md](./EMAIL_MARKERS_GUIDE.md) - Comprehensive marker documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Knowledge Worker architecture
- [../CLI_GUIDE.md](../CLI_GUIDE.md) - Complete CLI reference

---

## API Integration

For programmatic deployments using AI generation:

```python
from azure_haymaker.knowledge_worker import (
    DeploymentConfig,
    KnowledgeWorkerOrchestrator,
)

config = DeploymentConfig(
    name="ai-email-test",
    total_workers=25,
    departments={
        "operations": {
            "count": 25,
            "endpoint_type": "cli_container",
            "ai_email_config": {  # NEW: AI email configuration
                "enabled": True,
                "directive": "Write emails as limericks",
                "model": "gpt-4-turbo",
            },
            "marker_config": {  # NEW: Marker configuration
                "enabled": True,
                "style": "subject",
                "format": "MARKER",
            },
        }
    },
    duration_hours=8,
)

# Deploy
orchestrator = KnowledgeWorkerOrchestrator(graph_client)
run_id = orchestrator.create_deployment(config)
await orchestrator.start_deployment(run_id)
```

---

## Security Considerations

**API Key Protection**:
- Store keys in environment variables, never in code
- Use Azure Key Vault in production
- Rotate keys regularly

**Content Filtering**:
- AI models have built-in safety filters
- Inappropriate content requests will be rejected
- Test directives before large deployments

**Data Privacy**:
- Email content sent to AI APIs (OpenAI/Anthropic)
- Do not include real PII in email directives
- Review API provider terms of service

---

## Summary

**Enable AI emails**: Add `--enable-ai-generation` flag

**Custom content**: Use `--email-directive "instructions"`

**Cost control**: Use `--ai-model gpt-3.5-turbo` for lower costs

**Track emails**: Markers enabled by default (`--marker-format TEXT`)

**Estimate costs**: ~$0.01/email (GPT-4) or ~$0.002/email (GPT-3.5)

AI-generated emails create realistic M365 telemetry for testing SIEM, DLP, and security tools.
