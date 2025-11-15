# Azure HayMaker CLI

Command-line interface for Azure HayMaker service management.

## Installation

```bash
pip install haymaker-cli
```

Or install from source:

```bash
cd cli
pip install -e .
```

## Quick Start

### Configuration

Create a configuration file at `~/.haymaker/config.yaml`:

```yaml
profiles:
  default:
    endpoint: https://haymaker-dev.azurewebsites.net
    auth:
      type: api_key
      key: your-api-key-here

  production:
    endpoint: https://haymaker-prod.azurewebsites.net
    auth:
      type: azure_ad
      tenant_id: your-tenant-id
```

Or use environment variables:

```bash
export HAYMAKER_ENDPOINT=https://haymaker-dev.azurewebsites.net
export HAYMAKER_API_KEY=your-api-key-here
```

Or configure via CLI:

```bash
haymaker config set endpoint https://haymaker-dev.azurewebsites.net
haymaker config set api-key your-api-key-here
```

### Usage

Check orchestrator status:

```bash
haymaker status
```

View execution metrics:

```bash
haymaker metrics
haymaker metrics --period 30d
haymaker metrics --format json
```

List running agents:

```bash
haymaker agents list
haymaker agents list --status running
```

View agent logs:

```bash
haymaker logs --agent-id agent-123
haymaker logs --agent-id agent-123 --follow
haymaker logs --agent-id agent-123 --tail 100
```

List all resources:

```bash
haymaker resources list
haymaker resources list --group-by type
haymaker resources list --scenario compute-01
```

Execute scenario on-demand:

```bash
haymaker deploy --scenario compute-01-linux-vm-web-server
haymaker deploy --scenario compute-01 --wait
```

Trigger cleanup:

```bash
haymaker cleanup
haymaker cleanup --execution-id exec-123
haymaker cleanup --dry-run
```

## Commands

### Status Commands

- `haymaker status` - Show current orchestrator status

### Execution Commands

- `haymaker deploy` - Deploy scenario on-demand
- `haymaker metrics` - Show execution metrics

### Agent Commands

- `haymaker agents list` - List all agents
- `haymaker logs` - Stream agent logs

### Resource Commands

- `haymaker resources list` - List all resources

### Cleanup Commands

- `haymaker cleanup` - Force cleanup of resources

### Configuration Commands

- `haymaker config set <key> <value>` - Set configuration value
- `haymaker config get <key>` - Get configuration value
- `haymaker config list` - List all configuration

## Output Formats

All commands support multiple output formats:

```bash
# Table format (default)
haymaker metrics

# JSON format
haymaker metrics --format json

# YAML format
haymaker metrics --format yaml
```

## Authentication

### API Key Authentication

Set API key in config file or environment variable:

```bash
export HAYMAKER_API_KEY=your-api-key
```

### Azure AD Authentication

The CLI will automatically use Azure CLI credentials if available:

```bash
az login
haymaker status
```

Or specify tenant ID explicitly:

```yaml
auth:
  type: azure_ad
  tenant_id: your-tenant-id
```

## Profiles

Use different profiles for different environments:

```bash
# Use default profile
haymaker status

# Use specific profile
haymaker status --profile production

# Switch default profile
haymaker config set-profile production
```

## Examples

### Monitor execution workflow

```bash
# Deploy scenario
haymaker deploy --scenario compute-01 --wait

# Check status
haymaker status

# View logs
haymaker logs --agent-id agent-123 --follow

# View resources created
haymaker resources list --scenario compute-01

# View metrics
haymaker metrics
```

### Cleanup resources

```bash
# List resources to cleanup
haymaker resources list --status created

# Dry-run cleanup
haymaker cleanup --dry-run

# Actual cleanup
haymaker cleanup

# Force cleanup specific execution
haymaker cleanup --execution-id exec-123
```

## Development

### Setup development environment

```bash
cd cli
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
pytest -v
pytest --cov
```

### Lint and type check

```bash
ruff check .
pyright
```

## License

MIT
