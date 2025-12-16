# Knowledge Worker Framework Documentation

Documentation for the Knowledge Worker Activity Framework - simulate 50-300 knowledge workers performing realistic M365 activities.

---

## Getting Started

**New to Knowledge Workers?** Start here:

1. **[Tutorial: Deploy & Monitor 25 Workers](./TUTORIAL_DEPLOY_AND_MONITOR.md)** - Complete end-to-end tutorial with AI limerick emails
2. **[Tutorial: Limerick Emails](./TUTORIAL_LIMERICK_EMAILS.md)** - Quick tutorial focused on AI-generated limericks
3. **[Architecture](./ARCHITECTURE.md)** - Framework design and component overview

---

## Core Documentation

### Configuration and Setup

- **[AI Email Generation Guide](./AI_EMAIL_GENERATION.md)** - Complete guide to AI-powered email content generation
- **[Email Markers Guide](./EMAIL_MARKERS_GUIDE.md)** - Track and filter emails with embedded markers
- **[CLI AI Email Reference](./CLI_AI_EMAIL_REFERENCE.md)** - Full CLI reference for AI email options
- **[Security](./SECURITY.md)** - Security controls and safety mechanisms

### Endpoint Strategies

- **[Windows 365 Cloud PC](./WINDOWS365_CLOUD_PC.md)** - Windows 365 endpoint documentation
- **[Windows 365 E2E Demo](./WINDOWS365_E2E_DEMO.md)** - Complete Windows 365 demonstration
- **[Windows VM Fallback](./WINDOWS_VM_FALLBACK.md)** - Alternative Windows VM deployment
- **[Computer Use Agents](./COMPUTER_USE_AGENTS.md)** - Anthropic Computer Use API integration

### Specifications

- **[KW Real M365 Specification](./KW_REAL_M365_SPECIFICATION.md)** - Complete M365 integration specification
- **[Research Notes](./RESEARCH_NOTES.md)** - Design decisions and research findings

---

## Quick Start

### Prerequisites

```bash
# Install CLI
pip install haymaker-cli

# Initialize KW app registration
haymaker kw init --save-config kw_config.env
source kw_config.env

# Verify setup
haymaker kw status
```

### Deploy Workers

```bash
# Deploy 25 workers with AI limericks (2 hours)
haymaker kw deploy \
  --workers 25 \
  --department operations \
  --duration 2 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work" \
  --marker-format LIMERICK

# Monitor deployment (save the run ID)
# Run ID: kw-20251211-abc123
```

### Monitor Activity

```bash
# Check telemetry summary
haymaker kw telemetry-report --run-id kw-20251211-abc123

# View email samples (using Azure CLI)
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@tenant.com/messages?\$top=3" \
  --query "value[].{Subject:subject, Body:body.content}"
```

---

## Documentation by Use Case

### Tutorials (Learning)

Start here if you're new:

- [Tutorial: Deploy & Monitor 25 Workers](./TUTORIAL_DEPLOY_AND_MONITOR.md) - **Recommended starting point**
- [Tutorial: Limerick Emails](./TUTORIAL_LIMERICK_EMAILS.md) - Quick focused tutorial

### How-To Guides (Tasks)

Solve specific problems:

- [AI Email Generation Guide](./AI_EMAIL_GENERATION.md) - Generate AI-powered emails
- [Email Markers Guide](./EMAIL_MARKERS_GUIDE.md) - Track emails with markers
- [Windows 365 E2E Demo](./WINDOWS365_E2E_DEMO.md) - Deploy Cloud PC endpoints

### Reference (Information)

Look up details:

- [CLI AI Email Reference](./CLI_AI_EMAIL_REFERENCE.md) - Complete CLI options
- [KW Real M365 Specification](./KW_REAL_M365_SPECIFICATION.md) - API specifications

### Explanation (Understanding)

Understand concepts:

- [Architecture](./ARCHITECTURE.md) - Framework design
- [Security](./SECURITY.md) - Safety mechanisms
- [Research Notes](./RESEARCH_NOTES.md) - Design decisions

---

## Common Workflows

### Testing SIEM Integration

```bash
# Deploy with hidden markers
haymaker kw deploy \
  --workers 10 \
  --duration 4 \
  --marker-style hidden \
  --marker-format SIEM-TEST

# Export telemetry
haymaker kw telemetry-report \
  --run-id kw-20251211-abc123 \
  --format json \
  --output siem-test.json
```

See: [Email Markers Guide](./EMAIL_MARKERS_GUIDE.md)

### Red Team Simulation

```bash
# Deploy realistic workers (no visible markers)
haymaker kw deploy \
  --workers 50 \
  --department engineering \
  --duration 8 \
  --enable-ai-generation \
  --marker-style hidden \
  --endpoint-type cloud_pc
```

See: [Windows 365 Cloud PC](./WINDOWS365_CLOUD_PC.md)

### Cost Optimization

```bash
# Use cheaper model and containers
haymaker kw deploy \
  --workers 100 \
  --duration 8 \
  --enable-ai-generation \
  --ai-model gpt-3.5-turbo \
  --endpoint-type cli_container
```

See: [AI Email Generation Guide](./AI_EMAIL_GENERATION.md)

---

## Architecture Overview

```
Knowledge Worker Framework
├── Identity Layer (Entra users, groups, transport rules)
├── M365 Operations (email, Teams, documents, calendar)
├── Endpoint Layer (Windows 365, CLI containers)
└── Orchestrator (deployment lifecycle management)
```

See: [Architecture](./ARCHITECTURE.md)

---

## Features

- **Realistic M365 Activity**: Email, Teams, documents, calendar events
- **AI-Powered Content**: Generate contextual emails with Claude or GPT
- **Distinct Endpoints**: Each worker operates from unique machine identity
- **Team Organization**: Workers grouped by department with security boundaries
- **Internal-Only**: Multiple safety layers prevent external communications
- **Full Cleanup**: All resources tagged and deletable at any time
- **Hybrid Endpoints**: Balance cost vs telemetry richness

---

## Support

**Issues?** Check troubleshooting sections:
- [Tutorial: Deploy & Monitor](./TUTORIAL_DEPLOY_AND_MONITOR.md#troubleshooting)
- [AI Email Generation Guide](./AI_EMAIL_GENERATION.md#troubleshooting)
- [Email Markers Guide](./EMAIL_MARKERS_GUIDE.md#troubleshooting)

**Questions?** See:
- [Architecture](./ARCHITECTURE.md) - Design and concepts
- [Research Notes](./RESEARCH_NOTES.md) - Decisions and rationale

---

## Contributing

See the main [Contributing Guide](../CONTRIBUTING.md) for Azure HayMaker.

---

## License

Azure HayMaker is released under the [MIT License](../../LICENSE).
