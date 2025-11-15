# Azure HayMaker CLI Guide

Complete guide for using the Azure HayMaker command-line interface.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [Commands](#commands)
- [Output Formats](#output-formats)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Installation

### From PyPI (Recommended)

```bash
pip install haymaker-cli
```

### From Source

```bash
cd cli
pip install -e .
```

### Development Installation

```bash
cd cli
pip install -e ".[dev]"
```

## Configuration

The CLI can be configured using:
1. Configuration file (`~/.haymaker/config.yaml`)
2. Environment variables
3. Command-line options

### Priority Order

1. Command-line options (highest priority)
2. Environment variables
3. Configuration file
4. Default values (lowest priority)

### Configuration File

Create `~/.haymaker/config.yaml`:

```yaml
profiles:
  default:
    endpoint: https://haymaker-dev.azurewebsites.net
    auth:
      type: api_key
      api_key: your-api-key-here

  production:
    endpoint: https://haymaker-prod.azurewebsites.net
    auth:
      type: azure_ad
      tenant_id: your-tenant-id

default_profile: default
```

### Environment Variables

```bash
export HAYMAKER_ENDPOINT=https://haymaker-dev.azurewebsites.net
export HAYMAKER_API_KEY=your-api-key
export HAYMAKER_PROFILE=default
```

### Using the Config Command

```bash
# Set configuration values
haymaker config set endpoint https://haymaker-dev.azurewebsites.net
haymaker config set api-key your-api-key

# Get configuration values
haymaker config get endpoint

# List all configuration
haymaker config list
```

## Authentication

The CLI supports two authentication methods:

### API Key Authentication

Set API key in configuration:

```bash
haymaker config set api-key your-api-key
```

Or use environment variable:

```bash
export HAYMAKER_API_KEY=your-api-key
```

### Azure AD Authentication

The CLI will automatically use Azure CLI credentials:

```bash
# Login to Azure
az login

# Use haymaker CLI
haymaker status
```

Or configure specific tenant:

```bash
haymaker config set tenant-id your-tenant-id
```

## Commands

### Status Command

Show current orchestrator status.

```bash
haymaker status [--format FORMAT]
```

**Options:**
- `--format`: Output format (table, json, yaml)

**Example:**
```bash
haymaker status
haymaker status --format json
```

### Metrics Command

Show execution metrics.

```bash
haymaker metrics [--period PERIOD] [--scenario SCENARIO] [--format FORMAT]
```

**Options:**
- `--period`: Time period (7d, 30d, 90d) - default: 7d
- `--scenario`: Filter by scenario name
- `--format`: Output format (table, json, yaml)

**Examples:**
```bash
# Show metrics for last 7 days
haymaker metrics

# Show metrics for last 30 days
haymaker metrics --period 30d

# Show metrics for specific scenario
haymaker metrics --scenario compute-01

# Output as JSON
haymaker metrics --format json
```

### Agents Commands

List and manage agents.

#### List Agents

```bash
haymaker agents list [--status STATUS] [--limit LIMIT] [--format FORMAT]
```

**Options:**
- `--status`: Filter by status (running, completed, failed)
- `--limit`: Maximum number of results - default: 100
- `--format`: Output format (table, json, yaml)

**Examples:**
```bash
# List all agents
haymaker agents list

# List only running agents
haymaker agents list --status running

# Limit to 50 results
haymaker agents list --limit 50
```

### Logs Command

View agent logs.

```bash
haymaker logs --agent-id AGENT_ID [--tail COUNT] [--follow]
```

**Options:**
- `--agent-id`: Agent ID (required)
- `--tail`: Number of recent log entries - default: 100
- `--follow`, `-f`: Follow logs (stream new entries)

**Examples:**
```bash
# View logs for agent
haymaker logs --agent-id agent-123

# View last 50 log entries
haymaker logs --agent-id agent-123 --tail 50

# Follow logs (stream)
haymaker logs --agent-id agent-123 --follow
```

### Resources Commands

List and manage resources.

#### List Resources

```bash
haymaker resources list [OPTIONS]
```

**Options:**
- `--execution-id`: Filter by execution ID
- `--scenario`: Filter by scenario name
- `--status`: Filter by status (created, deleted)
- `--group-by`: Group results (type, scenario, execution)
- `--limit`: Maximum number of results - default: 100
- `--format`: Output format (table, json, yaml)

**Examples:**
```bash
# List all resources
haymaker resources list

# List resources for scenario
haymaker resources list --scenario compute-01

# List resources grouped by type
haymaker resources list --group-by type

# List resources for specific execution
haymaker resources list --execution-id exec-123
```

### Deploy Command

Deploy scenario on-demand.

```bash
haymaker deploy --scenario SCENARIO [--wait] [--poll-interval SECONDS]
```

**Options:**
- `--scenario`: Scenario name (required)
- `--wait`: Wait for execution to complete
- `--poll-interval`: Polling interval in seconds - default: 30

**Examples:**
```bash
# Deploy scenario
haymaker deploy --scenario compute-01-linux-vm-web-server

# Deploy and wait for completion
haymaker deploy --scenario compute-01 --wait

# Deploy with custom poll interval
haymaker deploy --scenario compute-01 --wait --poll-interval 60
```

### Cleanup Command

Trigger cleanup of resources.

```bash
haymaker cleanup [OPTIONS]
```

**Options:**
- `--execution-id`: Cleanup specific execution
- `--scenario`: Cleanup specific scenario
- `--dry-run`: Show what would be cleaned without deleting

**Examples:**
```bash
# Cleanup all resources (with confirmation)
haymaker cleanup

# Dry run (show what would be cleaned)
haymaker cleanup --dry-run

# Cleanup specific execution
haymaker cleanup --execution-id exec-123

# Cleanup specific scenario
haymaker cleanup --scenario compute-01
```

### Config Commands

Manage CLI configuration.

#### Set Configuration

```bash
haymaker config set KEY VALUE [--profile PROFILE]
```

**Examples:**
```bash
haymaker config set endpoint https://haymaker.azurewebsites.net
haymaker config set api-key your-api-key
haymaker config set tenant-id your-tenant-id
```

#### Get Configuration

```bash
haymaker config get KEY [--profile PROFILE]
```

**Example:**
```bash
haymaker config get endpoint
```

#### List Configuration

```bash
haymaker config list [--profile PROFILE]
```

**Example:**
```bash
haymaker config list
```

## Output Formats

All commands support multiple output formats.

### Table Format (Default)

Human-readable table output with colors.

```bash
haymaker metrics
```

### JSON Format

Machine-readable JSON output.

```bash
haymaker metrics --format json
```

### YAML Format

Human-readable YAML output.

```bash
haymaker metrics --format yaml
```

## Examples

### Monitor Execution Workflow

```bash
# 1. Deploy scenario
haymaker deploy --scenario compute-01

# 2. Check orchestrator status
haymaker status

# 3. List running agents
haymaker agents list --status running

# 4. View agent logs
haymaker logs --agent-id agent-123 --follow

# 5. View resources created
haymaker resources list --scenario compute-01

# 6. Check metrics
haymaker metrics
```

### Cleanup Resources

```bash
# 1. List resources to cleanup
haymaker resources list --status created

# 2. Dry run cleanup
haymaker cleanup --dry-run

# 3. Actual cleanup
haymaker cleanup
```

### Use Different Profiles

```bash
# Configure production profile
haymaker config set endpoint https://haymaker-prod.azurewebsites.net --profile production
haymaker config set api-key prod-key --profile production

# Use production profile
haymaker status --profile production
haymaker metrics --profile production
```

### Automation with JSON Output

```bash
# Get metrics as JSON and parse with jq
haymaker metrics --format json | jq '.success_rate'

# Get active agents
haymaker agents list --format json | jq '.agents[] | select(.status == "running")'

# Get resource count
haymaker resources list --format json | jq '.resources | length'
```

## Troubleshooting

### Configuration Error

**Problem:** `Configuration file not found`

**Solution:**
```bash
# Create configuration
haymaker config set endpoint https://haymaker.azurewebsites.net
haymaker config set api-key your-api-key
```

### Authentication Error

**Problem:** `Authentication failed`

**Solutions:**

1. Check API key:
```bash
haymaker config get api-key
```

2. Re-login to Azure CLI:
```bash
az login
az account show
```

3. Check endpoint URL:
```bash
haymaker config get endpoint
```

### Network Error

**Problem:** `Network unreachable` or `Request timeout`

**Solutions:**

1. Check endpoint is accessible:
```bash
curl https://haymaker.azurewebsites.net/api/status
```

2. Check firewall/proxy settings

3. Increase timeout (in code, not configurable via CLI)

### Command Not Found

**Problem:** `haymaker: command not found`

**Solutions:**

1. Check installation:
```bash
pip show haymaker-cli
```

2. Reinstall:
```bash
pip install --force-reinstall haymaker-cli
```

3. Check PATH:
```bash
echo $PATH
which haymaker
```

## Advanced Usage

### Using with CI/CD

```bash
#!/bin/bash
# CI/CD script example

# Configure via environment variables
export HAYMAKER_ENDPOINT=https://haymaker.azurewebsites.net
export HAYMAKER_API_KEY=$SECRET_API_KEY

# Deploy scenario
haymaker deploy --scenario compute-01 --wait

# Check success
if [ $? -eq 0 ]; then
    echo "Deployment successful"
    exit 0
else
    echo "Deployment failed"
    exit 1
fi
```

### Monitoring Script

```bash
#!/bin/bash
# Monitor agents and send alerts

while true; do
    # Get active agents count
    active=$(haymaker agents list --status running --format json | jq '.agents | length')

    if [ $active -gt 10 ]; then
        echo "High agent count: $active"
        # Send alert
    fi

    sleep 300  # Check every 5 minutes
done
```

## API Documentation

For detailed API documentation, see:
- [API Reference](API.md)
- [Architecture Documentation](ARCHITECTURE.md)

## Support

For issues and questions:
- GitHub Issues: https://github.com/azurehaymaker/azurehaymaker/issues
- Documentation: https://github.com/azurehaymaker/azurehaymaker/tree/main/docs
