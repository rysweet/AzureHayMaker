# Knowledge Worker Deployment Tutorial

Complete guide to deploying and monitoring Knowledge Workers with email generation and tracking.

## Prerequisites

### Required Permissions

The deployment requires an Azure AD application with these Graph API permissions:

1. **Directory.Read.All** - Read service principals
2. **User.ReadWrite.All** - Create users
3. **AppRoleAssignment.ReadWrite.All** - Grant permissions
4. **Mail.ReadWrite** - Access mailboxes
5. **Mail.Send** - Send email on behalf of users

**Note**: The PermissionGranter automatically grants these permissions during deployment.

### Environment Variables

```bash
export KW_TENANT_ID="your-tenant-id"
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-client-secret"
export ANTHROPIC_API_KEY="your-anthropic-key"  # Optional, for AI email generation
```

## Deploy 5 Workers

### Using Python Script

```bash
python scripts/deploy_5_workers_now.py
```

**Output**:
```
🏴‍☠️ Knowledge Worker Deployment - 5 Workers
======================================================================

1️⃣  Authenticating with Microsoft Graph...
   ✅ Authenticated

2️⃣  Creating deployment configuration...
   Name: kw-5-test-20251212-0209
   Workers: 5
   Departments: engineering (3), sales (2)
   AI Generation: True
   Email Markers: True

3️⃣  Initializing Knowledge Worker Orchestrator...
   ✅ Orchestrator initialized

4️⃣  Creating deployment...
   ✅ Deployment created: kw-250569d9

5️⃣  Starting deployment...
   ✅ DEPLOYMENT STARTED SUCCESSFULLY!
```

### Using CLI with Config File

```bash
haymaker kw deploy --config-file examples/kw-deployments/kw-5-test-limericks.yaml
```

## Monitor Deployment

### List Workers

```bash
haymaker kw list-workers --run-id kw-250569d9
```

**Output**:
```
                        Workers for kw-250569d9
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Worker ID      ┃ Display Name   ┃ Persona     ┃ Department  ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ kw-kw-25056-e… │ KW Engineering │ engineering │ engineering │
│ kw-kw-25056-e… │ KW Engineering │ engineering │ engineering │
│ kw-kw-25056-e… │ KW Engineering │ engineering │ engineering │
│ kw-kw-25056-s… │ KW Sales 1     │ sales       │ sales       │
│ kw-kw-25056-s… │ KW Sales 2     │ sales       │ sales       │
└────────────────┴────────────────┴─────────────┴─────────────┘

Total: 5 workers
```

### Check Telemetry

```bash
haymaker kw check-telemetry --run-id kw-250569d9
```

**Output**:
```
   Telemetry Summary for kw-250569d9
┏━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric          ┃ Count ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Workers         │     5 │
│ Emails          │    28 │
│ Calendar Events │    12 │
│ Teams Messages  │    45 │
└─────────────────┴───────┘
```

### List Resources

```bash
haymaker kw list-resources --run-id kw-250569d9
```

**Output**:
```
Resources for kw-250569d9

Entra Users: 5
Security Groups: 1
Endpoints: 5 (all cli_container, all running)
```

## Scale to 25 Workers

### Config File

```yaml
# examples/kw-deployments/kw-25-test.yaml
name: "kw-25-deployment"
total_workers: 25
tenant_domain: "your-tenant.onmicrosoft.com"
duration_hours: 2

departments:
  engineering:
    count: 5
    endpoint_type: "windows_vm"
  sales:
    count: 15
    endpoint_type: "cli_container"
  executive:
    count: 5
    endpoint_type: "cli_container"

email_generation:
  enabled: true
  directive: "Include a humorous limerick about working in the age of AI"
```

### Deploy

```bash
haymaker kw deploy --config-file examples/kw-deployments/kw-25-test.yaml
```

### Monitor

```bash
haymaker kw list-workers --run-id {RUN_ID}
```

**Output** (25 workers):
```
Total: 25 workers
- Engineering: 5 (windows_vm)
- Sales: 15 (cli_container)
- Executive: 5 (cli_container)
```

## Troubleshooting

### Permission Errors

If you see "Authorization_RequestDenied" errors, verify all 5 permissions are granted:

```bash
# Check current permissions
az ad app permission list --id {YOUR_APP_ID}

# The PermissionGranter will auto-grant missing permissions during deployment
```

### E5 License Availability

Check available licenses:

```bash
az rest --method GET --uri "https://graph.microsoft.com/v1.0/subscribedSkus" \
  --query "value[?contains(skuPartNumber,'E5')].{sku:skuPartNumber,total:prepaidUnits.enabled,consumed:consumedUnits}"
```

### Mailbox Provisioning

Mailboxes take 15-30 minutes to provision after license assignment. This is normal Exchange Online behavior.

## Key Features

- **Automated Permission Granting**: PermissionGranter handles all Graph API permissions
- **Multi-Department**: Configure different activity patterns per department
- **Mixed Endpoints**: Combine Windows VMs and CLI containers
- **AI Email Generation**: Optional Claude-powered email content with custom directives
- **Email Markers**: Track emails with run-id and worker-id markers
- **Monitoring**: Rich CLI commands for deployment tracking

## Next Steps

See `haymaker kw --help` for all available commands.
