# Azure HayMaker CLI

The `haymaker` command-line interface provides lifecycle management for Knowledge Worker deployments.

## Installation

The CLI is installed automatically with the azure-haymaker package:

```bash
pip install azure-haymaker
# or
uv pip install azure-haymaker
```

## Quick Start

```bash
# Check deployment status
haymaker kw status

# List all deployments
haymaker kw list

# View logs for a deployment
haymaker kw logs --run-id kw-abc12345

# Stop a running deployment
haymaker kw stop --run-id kw-abc12345

# Clean up all resources for a deployment
haymaker kw cleanup --run-id kw-abc12345
```

## Commands

### haymaker kw

Knowledge Worker lifecycle management commands.

#### haymaker kw status

Display status of deployments.

```bash
# Show status of all deployments
haymaker kw status

# Show status of specific deployment
haymaker kw status --run-id kw-abc12345

# JSON output for scripting
haymaker kw status --format json
```

**Options:**
- `--run-id, -r`: Specific deployment run ID
- `--format, -f`: Output format (table, json, yaml). Default: table

#### haymaker kw list

List all known deployments.

```bash
# List all deployments
haymaker kw list

# Limit results
haymaker kw list --limit 5

# JSON output
haymaker kw list --format json
```

**Options:**
- `--limit, -l`: Maximum number of deployments to show. Default: 10
- `--format, -f`: Output format (table, json). Default: table

#### haymaker kw logs

View logs for a deployment.

```bash
# View recent logs
haymaker kw logs --run-id kw-abc12345

# Follow logs in real-time
haymaker kw logs --run-id kw-abc12345 --follow

# Limit log lines
haymaker kw logs --run-id kw-abc12345 --lines 50
```

**Options:**
- `--run-id, -r`: Deployment run ID (required)
- `--follow, -f`: Follow logs in real-time
- `--lines, -n`: Number of lines to show. Default: 100

#### haymaker kw stop

Stop a running deployment.

```bash
# Stop deployment (with confirmation)
haymaker kw stop --run-id kw-abc12345

# Stop without confirmation
haymaker kw stop --run-id kw-abc12345 --yes
```

**Options:**
- `--run-id, -r`: Deployment run ID (required)
- `--yes, -y`: Skip confirmation prompt

#### haymaker kw start

Start or resume a stopped deployment.

```bash
# Start deployment
haymaker kw start --run-id kw-abc12345
```

**Options:**
- `--run-id, -r`: Deployment run ID (required)

#### haymaker kw restart

Restart a deployment (stop then start).

```bash
# Restart deployment
haymaker kw restart --run-id kw-abc12345

# Skip confirmation
haymaker kw restart --run-id kw-abc12345 --yes
```

**Options:**
- `--run-id, -r`: Deployment run ID (required)
- `--yes, -y`: Skip confirmation prompt

#### haymaker kw cleanup

Clean up all resources for a deployment.

```bash
# Cleanup specific deployment
haymaker kw cleanup --run-id kw-abc12345

# Cleanup with dry-run (show what would be deleted)
haymaker kw cleanup --run-id kw-abc12345 --dry-run

# Cleanup all deployments
haymaker kw cleanup --all

# Cleanup deployments older than 24 hours
haymaker kw cleanup --older-than 24h

# Skip confirmation
haymaker kw cleanup --run-id kw-abc12345 --yes
```

**Options:**
- `--run-id, -r`: Specific deployment to clean up
- `--all`: Clean up all deployments
- `--older-than`: Clean up deployments older than duration (e.g., 24h, 7d)
- `--dry-run`: Show what would be deleted without deleting
- `--yes, -y`: Skip confirmation prompt

#### haymaker kw delete-worker

Delete specific workers from a deployment.

```bash
# Delete specific worker
haymaker kw delete-worker --worker-id kw-abc12345-engi-001

# Delete workers by department
haymaker kw delete-worker --run-id kw-abc12345 --department sales

# Skip confirmation
haymaker kw delete-worker --worker-id kw-abc12345-engi-001 --yes
```

**Options:**
- `--worker-id, -w`: Specific worker ID to delete
- `--run-id, -r`: Deployment run ID (with --department)
- `--department, -d`: Delete all workers in department
- `--yes, -y`: Skip confirmation prompt

## Environment Variables

The CLI uses these environment variables for Azure authentication:

- `KW_TENANT_ID`: Azure AD tenant ID
- `KW_APP_ID`: Application (client) ID
- `KW_CLIENT_SECRET`: Client secret

For development without Azure:

- `HAYMAKER_STATE_DIR`: Override state directory (default: ~/.azure_haymaker)

## State Storage

Deployment state is stored in `~/.azure_haymaker/`:

```
~/.azure_haymaker/
├── deployments/
│   └── {run_id}.json    # Deployment configuration and status
└── workers/
    └── {run_id}/
        └── {worker_id}.json  # Worker details
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Resource not found
- `4`: Operation cancelled by user

## Examples

### Complete Lifecycle Example

```bash
# 1. Deploy knowledge workers (via Python API)
# python -c "from azure_haymaker import deploy; deploy()"

# 2. Monitor deployment
haymaker kw status --run-id kw-abc12345

# 3. View activity logs
haymaker kw logs --run-id kw-abc12345 --follow

# 4. Stop when done
haymaker kw stop --run-id kw-abc12345

# 5. Clean up resources
haymaker kw cleanup --run-id kw-abc12345
```

### Scripting Example

```bash
#!/bin/bash
# Cleanup old deployments

# Get deployments older than 7 days
old_deployments=$(haymaker kw list --format json | jq -r '.[] | select(.age_hours > 168) | .run_id')

for run_id in $old_deployments; do
    echo "Cleaning up $run_id..."
    haymaker kw cleanup --run-id "$run_id" --yes
done
```
