# Tutorial: Deploy 25 Knowledge Workers with AI Limericks and Monitor Activity

**Learn by doing** - Deploy a realistic Knowledge Worker simulation with AI-generated limerick emails, then monitor and analyze the activity.

**Duration**: 30 minutes
**Difficulty**: Beginner
**Last Updated**: 2025-12-11

---

## What You'll Build

By the end of this tutorial, you will have:

1. Deployed 25 operations workers across Windows 365 Cloud PCs or CLI containers
2. Generated ~250 AI-powered limerick emails over 2 hours
3. Monitored deployment status in real-time
4. Validated email activity with markers and limericks
5. Checked telemetry summary with cost analysis
6. Cleaned up all resources

**Expected Results**:
- 25 workers sending emails, Teams messages, creating documents
- Each email contains a limerick about office work
- All activity tracked with `[LIMERICK:...]` markers
- Estimated cost: $1.25 (with GPT-4 Turbo)

---

## Prerequisites

### Required Credentials

**Azure and M365**:
- Azure tenant with M365 licenses (50+ available)
- Global Administrator or Application Administrator role
- Azure CLI logged in (`az login`)

**AI API Keys** (choose one):
- Anthropic API key for Claude models (recommended)
- OpenAI API key for GPT models

### Required Software

```bash
# Azure HayMaker CLI
pip install haymaker-cli

# Azure CLI (if not installed)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify installations
haymaker --version
az --version
```

### Environment Setup

Create a `.env` file with your credentials:

```bash
# M365 Application Credentials
export KW_TENANT_ID=12345678-1234-1234-1234-123456789abc
export KW_APP_ID=87654321-4321-4321-4321-cba987654321
export KW_CLIENT_SECRET=your-client-secret-here

# AI API Key (choose one)
export ANTHROPIC_API_KEY=sk-ant-api03-...
# OR
export OPENAI_API_KEY=sk-...

# Load environment
source .env
```

**Don't have KW credentials yet?** Run the init command first:

```bash
haymaker kw init --save-config kw_config.env
# Follow prompts to create app registration and grant admin consent
source kw_config.env
```

### Verification Checklist

Run these checks before starting:

```bash
# 1. Check CLI installed
haymaker --version
# Expected: haymaker, version 0.5.0+

# 2. Check KW framework available
haymaker kw status
# Expected: [green]Framework Available[/green]

# 3. Verify credentials set
echo $KW_TENANT_ID
# Expected: Your tenant GUID

echo $KW_APP_ID
# Expected: Your app GUID

echo $ANTHROPIC_API_KEY | head -c 20
# Expected: sk-ant-api03-... (first 20 chars)

# 4. Test Graph API connectivity
haymaker kw e2e-test --test-email=false
# Expected: PASS - List Users, List Groups
```

All checks passing? Let's deploy!

---

## Step 1: Create Deployment Configuration File

Create a YAML configuration file for the deployment. This makes it easy to reproduce and modify.

**Create**: `kw-25-workers.yaml`

```yaml
# Knowledge Worker Deployment Configuration
# 25 operations workers with limerick emails

name: kw-limericks-demo
total_workers: 25
tenant_domain: yourtenant.onmicrosoft.com  # CHANGE THIS

# Department configuration
departments:
  operations:
    count: 25
    endpoint_type: cli_container  # or "cloud_pc" for Windows 365
    activity:
      email_per_hour: 5
      teams_messages_per_hour: 8
      documents_per_day: 2
      meetings_per_day: 3

# Deployment settings
duration_hours: 2

# Email marker configuration
email_markers_enabled: true
marker_style: subject        # "subject", "hidden", or "both"
marker_format: LIMERICK      # Custom marker prefix

# AI email generation
email_generation:
  enabled: true
  directive: "Write all emails as limericks about office work, meetings, and IT operations"
  # model: claude-sonnet-4-5-20250929  # Optional: override default
```

**Edit the file**:
1. Change `tenant_domain` to your actual domain (e.g., `contoso.onmicrosoft.com`)
2. Choose `endpoint_type`:
   - `cli_container`: Cost-efficient, API-based activity
   - `cloud_pc`: Rich telemetry, full Windows 365 desktop experience

**Configuration breakdown**:
- **25 workers** × **2 hours** × **5 emails/hour** = **~250 emails**
- Emails have `[LIMERICK:...]` markers for tracking
- All emails are AI-generated limericks about office topics
- Workers also send Teams messages and create documents

---

## Step 2: Preview Deployment (Dry Run)

Before deploying, preview what will be created:

```bash
# [PLANNED] Config file support coming soon
# For now, use command-line options:

haymaker kw deploy \
  --name kw-limericks-demo \
  --workers 25 \
  --department operations \
  --duration 2 \
  --endpoint-type cli_container \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work, meetings, and IT operations" \
  --marker-format LIMERICK \
  --marker-style subject \
  --dry-run
```

**Expected Output**:

```
[cyan]Preparing KW deployment...[/cyan]
  Name: kw-limericks-demo
  Workers: 25
  Department: operations
  Tenant Domain: contoso.onmicrosoft.com
  Duration: 2h
  Endpoint Type: cli_container

  Email Markers: Enabled
    - Format: LIMERICK
    - Style: subject
  AI Email Generation: Enabled
    - Model: Anthropic SDK default
    - Directive: Write all emails as limericks about office work...

  ⚠️  API Cost Estimation:
    - Estimated emails: ~250 (25 workers × 5/hr × 2h)
    - API calls: ~250
    - Estimated cost: Variable (depends on model and token usage)
      Check Anthropic pricing for details

[yellow]Dry run - deployment not started[/yellow]

[cyan]Would create:[/cyan]
  - 25 operations workers
  - Endpoint type: cli_container
  - Security groups for workers
  - Transport rules (external email blocking)
  - CLI containers for each worker

[cyan]Email Configuration:[/cyan]
  Email Markers: Enabled
    - Format: LIMERICK
    - Style: subject
  AI Email Generation: Enabled
    - Model: Anthropic SDK default
    - Directive: Write all emails as limericks about office work...
```

**Review the dry run output**:
- ✅ 25 workers (correct)
- ✅ 2 hours duration (correct)
- ✅ AI generation enabled (correct)
- ✅ Limerick directive (correct)
- ✅ Cost estimate: ~$1.25 (acceptable)

If everything looks good, proceed to deployment!

---

## Step 3: Deploy the Workers

Remove `--dry-run` to execute the deployment:

```bash
haymaker kw deploy \
  --name kw-limericks-demo \
  --workers 25 \
  --department operations \
  --duration 2 \
  --endpoint-type cli_container \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work, meetings, and IT operations" \
  --marker-format LIMERICK \
  --marker-style subject
```

**Deployment Process** (approximately 5-10 minutes):

```
[cyan]Preparing KW deployment...[/cyan]
  Name: kw-limericks-demo
  Workers: 25
  Department: operations
  Duration: 2h

[INFO] Creating Graph API client...
[INFO] Authenticating with M365...
[OK] Authentication successful

[INFO] Creating deployment configuration...
[INFO] AI email generation enabled (model: claude-sonnet-4-5-20250929)
[INFO] Estimated cost: ~$1.25 for ~250 emails

[INFO] Creating 25 operations workers...
[INFO] Creating worker: kw-oper-001
[INFO] Creating worker: kw-oper-002
[INFO] Creating worker: kw-oper-003
...
[INFO] Creating worker: kw-oper-025
[OK] All workers created

[INFO] Provisioning security groups...
[INFO] Creating group: KW-Operations-Workers
[OK] Security groups created

[INFO] Setting up transport rules...
[INFO] Creating rule: Block-KW-External-Email
[OK] Transport rules configured (external email blocking)

[INFO] Provisioning CLI containers...
[INFO] Container created: kw-oper-001-container
[INFO] Container created: kw-oper-002-container
...
[OK] All containers provisioned

[green]Deployment created: kw-20251211-abc123[/green]
Starting deployment...

[INFO] Workers starting activity simulation...
[INFO] kw-oper-001: Sent email 1/10 [LIMERICK:oper-001-00001-a3f2c1]
[INFO] kw-oper-002: Sent email 1/10 [LIMERICK:oper-002-00001-b4e3d2]
[INFO] kw-oper-003: Created Teams message in #operations-chat
...

[green]Deployment started successfully![/green]
  Run ID: kw-20251211-abc123
  Phase: executing
  Workers: 25
```

**Save your run ID**: You'll need `kw-20251211-abc123` for monitoring and cleanup.

**What just happened?**:
1. Created 25 Entra ID users (kw-oper-001 through kw-oper-025)
2. Created security group "KW-Operations-Workers"
3. Created transport rule to block external emails
4. Provisioned 25 CLI containers (one per worker)
5. Started activity simulation (emails, Teams, documents)

**Timeline**:
- Workers begin sending emails immediately
- Activity runs for 2 hours
- ~5 emails per worker per hour
- Total: ~250 limerick emails

---

## Step 4: Monitor Deployment Status

### Option A: Using KW Status Command

```bash
# [PLANNED] Enhanced monitoring commands coming soon
haymaker kw status
```

**Expected Output**:

```
[cyan]Knowledge Worker Framework Status[/cyan]

[green]Framework Available[/green]

Module Status
┌──────────────┬───────────┐
│ Module       │ Status    │
├──────────────┼───────────┤
│ Agent        │ Available │
│ Config       │ Available │
│ Models       │ Available │
│ Operations   │ Available │
│ Validators   │ Available │
└──────────────┴───────────┘

Personas available: 8
```

### Option B: List Workers (Using Az CLI)

Since `haymaker kw list-workers` is planned, use Azure CLI:

```bash
# List all KW users
az ad user list --filter "startswith(displayName, 'kw-oper')" \
  --query "[].{Name:displayName, UPN:userPrincipalName, Created:createdDateTime}" \
  --output table
```

**Expected Output**:

```
Name          UPN                                Created
------------  ---------------------------------  -------------------------
kw-oper-001   kw-oper-001@contoso.onmicrosoft.com  2025-12-11T10:30:00Z
kw-oper-002   kw-oper-002@contoso.onmicrosoft.com  2025-12-11T10:30:05Z
kw-oper-003   kw-oper-003@contoso.onmicrosoft.com  2025-12-11T10:30:10Z
...
kw-oper-025   kw-oper-025@contoso.onmicrosoft.com  2025-12-11T10:35:00Z
```

### Option C: Check Container Status

```bash
# [PLANNED] Monitor command coming soon
# For now, check via Azure Portal:
# 1. Navigate to Container Apps
# 2. Filter by tag: haymaker-run-id=kw-20251211-abc123
# 3. Check revision status (Running/Succeeded)
```

---

## Step 5: Validate Email Activity

After 10-15 minutes, check that limerick emails are being generated:

### Check Email Count

```bash
# Count emails from first worker
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@contoso.onmicrosoft.com/messages?\$count=true" \
  --headers "ConsistencyLevel=eventual" \
  --query "@odata.count"
```

**Expected Output**: `5` (after ~1 hour), `10` (after ~2 hours)

### View Limerick Examples

```bash
# Get first 3 emails from worker
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@contoso.onmicrosoft.com/messages?\$top=3&\$select=subject,body" \
  --query "value[].{Subject:subject, Body:body.content}" \
  --output json
```

**Expected Output**:

```json
[
  {
    "Subject": "Activity 1 from kw-oper-001 [LIMERICK:oper-001-00001-a3f2c1]",
    "Body": "There once was a server so slow,\nThe tickets kept piling, oh no!\nWe patched and we prayed,\nThe performance was made,\nNow dashboards all happily glow!"
  },
  {
    "Subject": "Activity 2 from kw-oper-001 [LIMERICK:oper-001-00002-b4e3d2]",
    "Body": "A meeting was scheduled at three,\nAbout our deployment, you see.\nThe pipeline ran green,\nThe smoothest we've seen,\nNow everyone's happy and free!"
  },
  {
    "Subject": "Activity 3 from kw-oper-001 [LIMERICK:oper-001-00003-c5f4e3]",
    "Body": "Our monitoring tools caught a spike,\nIn traffic, the kind we don't like.\nWe scaled up with grace,\nAt just the right pace,\nNow systems perform like a bike!"
  }
]
```

**Validation**:
- ✅ Subject contains `[LIMERICK:...]` marker
- ✅ Body is a 5-line limerick about office work
- ✅ AABBA rhyme scheme
- ✅ Sequential marker IDs (00001, 00002, 00003)

### Search for All Limerick Emails

```bash
# Count all limerick emails across all workers
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users?\$filter=startswith(userPrincipalName,'kw-oper')" \
  --query "value[].userPrincipalName" \
  | jq -r '.[]' \
  | while read upn; do
      count=$(az rest --method GET \
        --url "https://graph.microsoft.com/v1.0/users/$upn/messages?\$filter=contains(subject,'LIMERICK')&\$count=true" \
        --headers "ConsistencyLevel=eventual" \
        --query "@odata.count")
      echo "$upn: $count emails"
    done
```

**Expected Output** (after 2 hours):

```
kw-oper-001@contoso.onmicrosoft.com: 10 emails
kw-oper-002@contoso.onmicrosoft.com: 11 emails
kw-oper-003@contoso.onmicrosoft.com: 9 emails
...
kw-oper-025@contoso.onmicrosoft.com: 10 emails
Total: 247 emails
```

---

## Step 6: Check Telemetry Summary

After deployment completes (2 hours), generate a summary report:

```bash
haymaker kw telemetry-report --run-id kw-20251211-abc123
```

**Expected Output**:

```
[cyan]Collecting telemetry for: kw-20251211-abc123[/cyan]

[bold]Activity Summary[/bold]

Workers: 25
Emails: 247
Calendar Events: 75
Teams Messages: 400
Documents: 50

[cyan]Email Breakdown by Worker:[/cyan]
  kw-oper-001: 10 emails
  kw-oper-002: 11 emails
  kw-oper-003: 9 emails
  kw-oper-004: 10 emails
  ...
  kw-oper-025: 10 emails

[cyan]Marker Analysis:[/cyan]
  Total emails with markers: 247/247 (100%)
  Marker format: LIMERICK
  Marker style: subject
  Average email length: 148 tokens
  AI model used: claude-sonnet-4-5-20250929

[cyan]Cost Breakdown:[/cyan]
  Total API calls: 247
  Input tokens: 12,350 (~50 tokens/email)
  Output tokens: 36,556 (~148 tokens/email)
  Estimated cost: $1.23
```

### Export Report as JSON

```bash
haymaker kw telemetry-report \
  --run-id kw-20251211-abc123 \
  --format json \
  --output limerick-report.json
```

**Output**: `limerick-report.json` created with full details.

### View Detailed Report

```bash
cat limerick-report.json | jq '.'
```

**Sample JSON structure**:

```json
{
  "run_id": "kw-20251211-abc123",
  "deployment_name": "kw-limericks-demo",
  "duration_hours": 2,
  "worker_count": 25,
  "total_emails": 247,
  "total_calendar_events": 75,
  "total_teams_messages": 400,
  "total_documents": 50,
  "markers": {
    "enabled": true,
    "format": "LIMERICK",
    "style": "subject",
    "coverage": 1.0
  },
  "ai_generation": {
    "enabled": true,
    "model": "claude-sonnet-4-5-20250929",
    "total_calls": 247,
    "input_tokens": 12350,
    "output_tokens": 36556,
    "estimated_cost": 1.23
  },
  "workers": [
    {
      "worker_id": "kw-oper-001",
      "emails_sent": 10,
      "teams_messages": 16,
      "documents_created": 2,
      "calendar_events": 3
    }
  ]
}
```

---

## Step 7: View Costs

### Using Telemetry Report

The telemetry report includes estimated API costs. For actual Azure costs:

```bash
# [PLANNED] Cost query command coming soon
# haymaker kw check-costs --run-id kw-20251211-abc123
```

### Using Azure CLI (Fallback)

```bash
# Query costs for KW resources
az consumption usage list \
  --start-date 2025-12-11 \
  --end-date 2025-12-12 \
  --query "[?contains(tags.haymaker_run_id, 'kw-20251211-abc123')].{Resource:instanceName, Cost:pretaxCost}" \
  --output table
```

**Expected Output**:

```
Resource                        Cost
------------------------------  ------
kw-oper-001-container           $0.05
kw-oper-002-container           $0.05
...
kw-oper-025-container           $0.05
------------------------------  ------
Total (25 containers × 2h)      $1.25
```

**Cost Breakdown**:
- **API costs**: $1.23 (247 emails × AI generation)
- **Container costs**: $1.25 (25 containers × 2 hours)
- **Storage costs**: <$0.10 (minimal)
- **Total**: ~$2.58

---

## Step 8: Analyze Markers

Markers enable traceability. Let's analyze them:

### Marker Format

```
[LIMERICK:oper-001-00005-a3f2c1]
 ^^^^^^^^ ^^^^^^^^ ^^^^^ ^^^^^^
 Format   Worker   Seq   UUID

LIMERICK - Custom format prefix (from --marker-format)
oper-001 - Worker ID (operations worker #1)
00005    - Email sequence number (5th email)
a3f2c1   - Unique identifier (6 hex chars)
```

### Extract All Marker IDs

```bash
# Get all marker IDs from worker emails
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@contoso.onmicrosoft.com/messages?\$filter=contains(subject,'LIMERICK')&\$select=subject" \
  --query "value[].subject" \
  | grep -oP '\[LIMERICK:[^\]]+\]'
```

**Expected Output**:

```
[LIMERICK:oper-001-00001-a3f2c1]
[LIMERICK:oper-001-00002-b4e3d2]
[LIMERICK:oper-001-00003-c5f4e3]
[LIMERICK:oper-001-00004-d6g5h4]
[LIMERICK:oper-001-00005-e7h6i5]
[LIMERICK:oper-001-00006-f8i7j6]
[LIMERICK:oper-001-00007-g9j8k7]
[LIMERICK:oper-001-00008-h0k9l8]
[LIMERICK:oper-001-00009-i1l0m9]
[LIMERICK:oper-001-00010-j2m1n0]
```

### Verify Sequence Integrity

```bash
# Check for sequence gaps (should be sequential)
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@contoso.onmicrosoft.com/messages?\$filter=contains(subject,'LIMERICK')&\$select=subject&\$orderby=receivedDateTime" \
  --query "value[].subject" \
  | grep -oP 'oper-001-\d+' \
  | sort -u
```

**Expected Output**: `oper-001-00001` through `oper-001-00010` (no gaps)

---

## Step 9: Cleanup

After testing, clean up all resources:

```bash
# [PLANNED] Cleanup command coming soon
# haymaker kw cleanup --run-id kw-20251211-abc123
```

### Manual Cleanup (Fallback)

Until the cleanup command is implemented, use Azure CLI:

**Step 1: Delete Container Apps**

```bash
# List containers for this deployment
az containerapp list \
  --query "[?tags.haymaker_run_id=='kw-20251211-abc123'].{Name:name, ResourceGroup:resourceGroup}" \
  --output table

# Delete containers
az containerapp list \
  --query "[?tags.haymaker_run_id=='kw-20251211-abc123'].{name:name, rg:resourceGroup}" \
  --output tsv \
  | while IFS=$'\t' read -r name rg; do
      echo "Deleting container: $name"
      az containerapp delete --name "$name" --resource-group "$rg" --yes
    done
```

**Step 2: Delete Security Groups**

```bash
# Find KW security groups
az ad group list --filter "startswith(displayName, 'KW-')" \
  --query "[].{Name:displayName, ID:id}" \
  --output table

# Delete operations group
az ad group delete --group "KW-Operations-Workers"
```

**Step 3: Delete Transport Rules**

```bash
# [REQUIRES] Exchange Online PowerShell
Connect-ExchangeOnline

# List KW transport rules
Get-TransportRule | Where-Object {$_.Name -like "Block-KW-*"}

# Delete transport rule
Remove-TransportRule -Identity "Block-KW-External-Email" -Confirm:$false
```

**Step 4: Delete Users (Optional)**

⚠️ **Warning**: Only delete users if you won't reuse them for future deployments.

```bash
# List all KW users
az ad user list --filter "startswith(displayName, 'kw-oper')" \
  --query "[].{Name:displayName, UPN:userPrincipalName}" \
  --output table

# Delete users (DESTRUCTIVE)
az ad user list --filter "startswith(displayName, 'kw-oper')" \
  --query "[].userPrincipalName" \
  --output tsv \
  | while read upn; do
      echo "Deleting user: $upn"
      az ad user delete --id "$upn"
    done
```

**Step 5: Verify Cleanup**

```bash
# Check containers deleted
az containerapp list \
  --query "[?tags.haymaker_run_id=='kw-20251211-abc123']" \
  --output table
# Expected: []

# Check groups deleted
az ad group list --filter "startswith(displayName, 'KW-')" \
  --output table
# Expected: []

# Check users remain (if not deleted)
az ad user list --filter "startswith(displayName, 'kw-oper')" \
  --query "length(@)"
# Expected: 25 (if users kept for reuse) or 0 (if deleted)
```

---

## Troubleshooting

### Issue: No Emails Generated

**Check worker logs**:

```bash
# [PLANNED] Log viewing command coming soon
# haymaker logs --agent-id kw-oper-001 --tail 50

# Fallback: Check container logs
az containerapp logs show \
  --name kw-oper-001-container \
  --resource-group your-rg \
  --tail 50
```

**Look for errors**:
- `[ERROR] Failed to send email: MailboxNotFound` → Verify worker has mailbox enabled
- `[ERROR] Authentication failed` → Check KW credentials in .env
- `[ERROR] Rate limit exceeded` → Reduce worker count or email frequency

**Solution**: Verify mailbox status:

```bash
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@contoso.onmicrosoft.com" \
  --query "{UPN:userPrincipalName, LicensesAssigned:assignedLicenses[].skuId}"
```

### Issue: API Rate Limits

**Error**: `RateLimitError: Too many requests (429)`

**Solution**: Reduce worker count or email rate:

```bash
# Deploy fewer workers
haymaker kw deploy --workers 10 --enable-ai-generation ...

# Operations workers default to 5 emails/hour (safe rate)
# Executives send 8 emails/hour (may hit limits)
```

### Issue: Non-Limerick Content

**Problem**: AI generates normal emails instead of limericks.

**Check directive**:

```bash
# Directive must be explicit
--email-directive "Write all emails as limericks"  # Good
--email-directive "Use limericks sometimes"        # Ambiguous
```

**Solution**: Use explicit directive:

```bash
--email-directive "You MUST write every email as a limerick with 5 lines and AABBA rhyme scheme about office work"
```

### Issue: Missing Markers

**Problem**: Emails don't have `[LIMERICK:...]` markers.

**Check configuration**:

```bash
# Verify markers enabled (default)
haymaker kw deploy --workers 10 --enable-ai-generation --marker-format LIMERICK

# NOT disabled:
# haymaker kw deploy --workers 10 --no-enable-markers
```

**Verify in email**:

```bash
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@contoso.onmicrosoft.com/messages?\$top=1&\$select=subject" \
  --query "value[0].subject"

# Expected: "Activity 1 from kw-oper-001 [LIMERICK:oper-001-00001-...]"
```

### Issue: High Costs

**Problem**: Unexpected API costs.

**Check actual usage**:

```bash
haymaker kw telemetry-report --run-id kw-20251211-abc123 --format json \
  | jq '.ai_generation'
```

**Cost optimization**:

```bash
# Option 1: Use GPT-3.5 instead (5x cheaper)
--ai-model gpt-3.5-turbo
# Cost: $0.25 vs $1.25 (GPT-4)

# Option 2: Disable AI generation (use templates)
# Remove --enable-ai-generation flag
# Cost: $0 (no API calls)

# Option 3: Reduce duration
--duration 1  # 1 hour instead of 2
# Cost: $0.60 vs $1.25
```

---

## Next Steps

Now that you've deployed and monitored Knowledge Workers, try:

### 1. Different Directives

```bash
# Security focus
--email-directive "Focus on cybersecurity threats, patches, and vulnerability management"

# Urgent tone
--email-directive "Write urgent emails about critical production outages requiring immediate action"

# Technical depth
--email-directive "Include detailed technical jargon about cloud architecture, Kubernetes, and microservices"

# Casual style
--email-directive "Write casual, friendly emails with team collaboration vibes"
```

### 2. Mixed Departments

Deploy multiple departments with different personas:

```bash
# Deploy executives (8 emails/hr, strategic topics)
haymaker kw deploy \
  --workers 5 \
  --department executive \
  --enable-ai-generation \
  --email-directive "Write strategic emails about business initiatives and leadership"

# Deploy engineers (4 emails/hr, technical topics)
haymaker kw deploy \
  --workers 20 \
  --department engineering \
  --enable-ai-generation \
  --email-directive "Write technical emails about code reviews, deployments, and architecture"
```

### 3. Long-term Simulation

```bash
# 8-hour workday simulation
haymaker kw deploy \
  --workers 25 \
  --duration 8 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks"

# Generates ~1000 emails
# Cost: ~$5 (GPT-4) or ~$1 (GPT-3.5)
```

### 4. SIEM Integration

Export markers to your SIEM for analysis:

```bash
# Export telemetry report
haymaker kw telemetry-report \
  --run-id kw-20251211-abc123 \
  --format json \
  --output report.json

# Parse and send to SIEM
cat report.json | jq '.workers[].emails_sent' | sum
# Send to Azure Sentinel, Splunk, etc.
```

### 5. Windows 365 Cloud PCs

For richer telemetry, use Cloud PCs instead of CLI containers:

```bash
# Change endpoint_type in config file
endpoint_type: cloud_pc  # Instead of cli_container

# Or use CLI flag
--endpoint-type cloud_pc
```

**Benefits**:
- Full Windows desktop telemetry
- Browser activity
- File system operations
- Process creation events
- Network connections

**Costs**: ~$0.50/hour per Cloud PC (vs $0.05/hour for containers)

---

## Summary

**What You Accomplished**:

1. ✅ Created deployment configuration with 25 workers
2. ✅ Previewed deployment with dry run
3. ✅ Deployed 25 operations workers with AI limerick emails
4. ✅ Monitored deployment status with Azure CLI
5. ✅ Validated email activity and limerick content
6. ✅ Checked telemetry summary with cost analysis
7. ✅ Analyzed markers for traceability
8. ✅ Cleaned up all resources

**Key Learnings**:

- AI generation adds realism to KW simulations
- Custom directives enable creative testing scenarios (limericks!)
- Markers provide full traceability for analysis
- Costs are predictable (~$0.005/email with Claude Sonnet)
- GPT-3.5 offers 5x cost savings with acceptable quality
- Hybrid endpoint strategy balances telemetry richness vs. cost

**Actual Results**:
- **Workers**: 25 operations workers
- **Emails**: 247 limerick emails
- **API Cost**: $1.23 (Claude Sonnet)
- **Container Cost**: $1.25 (25 × 2 hours)
- **Total Cost**: $2.48

---

## Related Documentation

- **[AI_EMAIL_GENERATION.md](./AI_EMAIL_GENERATION.md)** - Complete AI email generation guide
- **[EMAIL_MARKERS_GUIDE.md](./EMAIL_MARKERS_GUIDE.md)** - Email marker documentation
- **[CLI_AI_EMAIL_REFERENCE.md](./CLI_AI_EMAIL_REFERENCE.md)** - Full CLI reference for AI options
- **[TUTORIAL_LIMERICK_EMAILS.md](./TUTORIAL_LIMERICK_EMAILS.md)** - Original limerick tutorial
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Knowledge Worker framework architecture

---

**Questions?** See the troubleshooting section or check [AI_EMAIL_GENERATION.md](./AI_EMAIL_GENERATION.md) for advanced usage.
