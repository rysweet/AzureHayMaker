# Knowledge Worker Deployment Configurations

This directory contains example configuration files for Knowledge Worker deployments.

## Overview

Configuration files allow you to define complex multi-department KW deployments with different endpoint types, activity patterns, and settings. Files can be in YAML or JSON format.

## Available Examples

### kw-simple.json
A simple 5-worker deployment using CLI containers. Good for testing and learning.

**Usage:**
```bash
haymaker kw deploy --config-file examples/kw-deployments/kw-simple.json
```

**Configuration:**
- 5 engineering workers
- CLI containers (lightweight)
- 2 hour duration
- Basic email markers

### kw-25-mixed.yaml
A realistic 25-worker deployment across 3 departments with mixed endpoint types.

**Usage:**
```bash
haymaker kw deploy --config-file examples/kw-deployments/kw-25-mixed.yaml
```

**Configuration:**
- 10 engineering workers (Windows VMs)
- 10 sales workers (CLI containers)
- 5 executive workers (Windows VMs)
- 8 hour duration
- Customized activity patterns per department

## Configuration File Format

### Required Fields

```yaml
name: "deployment-name"
total_workers: 25
tenant_domain: "your-tenant.onmicrosoft.com"
duration_hours: 8

departments:
  department_name:
    count: 10
    endpoint_type: "cli_container"  # or "windows_vm" or "cloud_pc"
    activity:
      email_per_hour: 4
      teams_messages_per_hour: 10
      documents_per_day: 3
      meetings_per_day: 4
```

### Optional Fields

```yaml
# Email markers for tracking
email_markers_enabled: true
marker_style: "subject"  # "subject", "hidden", or "both"
marker_format: "MARKER"

# AI email generation (requires ANTHROPIC_API_KEY)
email_generation:
  enabled: false
  directive: null  # Optional custom directive
```

## CLI Overrides

You can override any configuration value from the command line:

```bash
# Override duration
haymaker kw deploy --config-file config.yaml --duration 4

# Override worker count
haymaker kw deploy --config-file config.yaml --workers 50

# Override marker format
haymaker kw deploy --config-file config.yaml --marker-format "TEST-ID"

# Enable AI generation
haymaker kw deploy --config-file config.yaml --enable-ai-generation
```

CLI arguments always take precedence over config file values.

## Dry Run

Test your configuration without actually deploying:

```bash
haymaker kw deploy --config-file config.yaml --dry-run
```

This shows:
- What resources would be created
- Configuration sources ([file] or [cli])
- Estimated costs and activity levels

## Endpoint Types

### cli_container
- Lightweight Docker containers
- Microsoft 365 CLI for operations
- Most cost-effective
- Best for: High-volume testing, email/calendar focus

### windows_vm
- Full Windows Server VMs
- Complete M365 desktop apps
- Higher cost, fuller experience
- Best for: Realistic simulation, document operations

### cloud_pc
- Windows 365 Cloud PCs
- Full Windows 11 experience
- Highest cost, most realistic
- Best for: Executive simulation, full M365 suite

## Multi-Department Deployments

You can deploy workers across multiple departments with different configurations:

```yaml
departments:
  engineering:
    count: 10
    endpoint_type: "cli_container"
    activity:
      email_per_hour: 4
      teams_messages_per_hour: 15
      documents_per_day: 5
      meetings_per_day: 4

  sales:
    count: 15
    endpoint_type: "windows_vm"
    activity:
      email_per_hour: 12
      teams_messages_per_hour: 10
      documents_per_day: 3
      meetings_per_day: 8
```

Each department can have:
- Different worker counts
- Different endpoint types
- Different activity patterns
- Different personas (affects behavior)

## Activity Patterns

Adjust these based on your testing needs:

- **email_per_hour**: Emails sent per hour (1-20 typical)
- **teams_messages_per_hour**: Teams messages per hour (5-20 typical)
- **documents_per_day**: Documents created/modified per day (1-10 typical)
- **meetings_per_day**: Calendar events created per day (2-10 typical)

Higher values = more M365 telemetry but higher API costs.

## Environment Variables

Required for actual deployment (not needed for dry-run):

```bash
export KW_TENANT_ID="your-tenant-id"
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-client-secret"

# Optional: For AI email generation
export ANTHROPIC_API_KEY="your-api-key"
```

Get these from `haymaker kw init`.

## Tips

1. **Start small**: Use `kw-simple.json` for first tests
2. **Use dry-run**: Always test with `--dry-run` first
3. **Monitor costs**: Check Azure and API usage regularly
4. **Adjust activity**: Start with low rates, increase as needed
5. **Mixed endpoints**: Use containers for most workers, VMs for key roles
6. **Test overrides**: Verify CLI overrides work before production

## Troubleshooting

**Config not loading:**
- Check file path is correct
- Verify file extension (.yaml, .yml, or .json)
- Validate YAML/JSON syntax

**Validation errors:**
- Check all required fields are present
- Verify total_workers matches sum of department counts
- Ensure endpoint types are valid

**Deployment fails:**
- Verify environment variables are set
- Check Azure credentials with `haymaker kw status`
- Review tenant domain matches your M365 tenant

## Creating Your Own Configs

1. Copy an example file
2. Update `tenant_domain` to your tenant
3. Adjust worker counts and departments
4. Customize activity patterns
5. Test with `--dry-run`
6. Deploy!

See the main documentation for more details on the Knowledge Worker framework.
