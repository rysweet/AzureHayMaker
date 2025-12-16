# [PLANNED - Implementation Pending]

# Tutorial: Deploy 25 Workers with Limerick Emails

**Purpose**: Step-by-step guide to deploy Knowledge Workers generating limerick emails for testing and demos.

**Last Updated**: 2025-12-10
**Status**: Planned Feature
**Difficulty**: Beginner
**Duration**: 15 minutes

---

## What You'll Learn

By the end of this tutorial, you'll be able to:
1. Configure AI email generation
2. Deploy 25 Knowledge Workers
3. Customize email content with directives
4. Track emails using markers
5. View generated limericks
6. Estimate and control costs

---

## Prerequisites

**Required**:
- Azure HayMaker CLI installed (`pip install haymaker-cli`)
- Azure tenant with M365 licenses
- Knowledge Worker app configured (`haymaker kw init`)
- OpenAI or Anthropic API key

**Environment Variables** (set these first):
```bash
# M365 credentials
export KW_TENANT_ID=your-tenant-id
export KW_APP_ID=your-app-id
export KW_CLIENT_SECRET=your-client-secret

# AI API key (choose one)
export OPENAI_API_KEY=sk-...        # For GPT models
# OR
export ANTHROPIC_API_KEY=sk-ant-... # For Claude models
```

**Check Setup**:
```bash
# Verify CLI installed
haymaker --version
# Output: haymaker, version 0.5.0

# Verify KW framework available
haymaker kw status
# Output: [green]Framework Available[/green]

# Verify credentials set
echo $KW_TENANT_ID
# Output: abc123-...
```

**Get API Keys**:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys

---

## Step 1: Understand the Goal

We'll deploy **25 operations workers** that generate **limerick emails** for 2 hours.

**Why Limericks?**
- Unique and easy to identify
- Fun demo scenario
- Tests AI generation capabilities
- Distinctive for filtering in logs

**Expected Output**:
- ~250 limerick emails over 2 hours
- Each email tracked with markers
- Cost: ~$2.50 (GPT-4) or ~$0.50 (GPT-3.5)

---

## Step 2: Preview the Deployment (Dry Run)

First, see what will be created without actually deploying:

```bash
haymaker kw deploy \
  --workers 25 \
  --department operations \
  --duration 2 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work and meetings" \
  --marker-format LIMERICK \
  --dry-run
```

**Expected Output**:
```
[cyan]Preparing KW deployment...[/cyan]
  Name: test-deployment
  Workers: 25
  Department: operations
  Tenant Domain: test.onmicrosoft.com
  Duration: 2h
  Endpoint Type: cli_container

[yellow]Dry run - deployment not started[/yellow]

[cyan]Would create:[/cyan]
  - 25 operations workers
  - Endpoint type: cli_container
  - Security groups for workers
  - Transport rules (external email blocking)
  - CLI containers for each worker

[cyan]AI Email Configuration:[/cyan]
  - AI Generation: Enabled
  - Model: gpt-4-turbo (auto-selected)
  - Directive: Write all emails as limericks about office work and meetings
  - Estimated emails: ~250 (5 per hour × 25 workers × 2 hours)
  - Estimated cost: $2.50

[cyan]Marker Configuration:[/cyan]
  - Markers: Enabled
  - Style: subject (visible in subject line)
  - Format: LIMERICK
  - Example: [LIMERICK:oper-001-00005-a3f2c1]
```

**Review**:
- ✅ 25 workers (correct)
- ✅ 2 hour duration (correct)
- ✅ AI generation enabled (correct)
- ✅ Limerick directive (correct)
- ✅ Cost estimate: $2.50 (acceptable)

---

## Step 3: Deploy the Workers

Remove `--dry-run` to execute the deployment:

```bash
haymaker kw deploy \
  --workers 25 \
  --department operations \
  --duration 2 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work and meetings" \
  --marker-format LIMERICK
```

**What Happens**:

```
[cyan]Preparing KW deployment...[/cyan]
  Name: test-deployment
  Workers: 25
  Department: operations
  Duration: 2h

[INFO] Creating Graph API client...
[INFO] Authenticating with M365...
[OK] Authentication successful

[INFO] Creating deployment configuration...
[INFO] AI email generation enabled (model: gpt-4-turbo)
[INFO] Estimated cost: ~$2.50 for ~250 emails

[INFO] Creating 25 operations workers...
[INFO] Creating worker: kw-oper-001
[INFO] Creating worker: kw-oper-002
...
[INFO] Creating worker: kw-oper-025
[OK] All workers created

[INFO] Provisioning security groups...
[OK] Security groups created

[INFO] Setting up transport rules...
[OK] Transport rules configured (external email blocking)

[INFO] Provisioning CLI containers...
[INFO] Container created: kw-oper-001-container
...
[OK] All containers provisioned

[green]Deployment created: kw-20251210-abc123[/green]
Starting deployment...

[INFO] Workers starting activity simulation...
[INFO] kw-oper-001: Sent email 1/10 [LIMERICK:oper-001-00001-a3f2c1]
[INFO] kw-oper-002: Sent email 1/10 [LIMERICK:oper-002-00001-b4e3d2]
...

[green]Deployment started successfully![/green]
  Run ID: kw-20251210-abc123
  Phase: running
  Workers: 25
```

**Timeline**:
- Workers start immediately
- Emails sent throughout 2-hour duration
- Average 5 emails per worker per hour
- Total runtime: 2 hours

---

## Step 4: Monitor Email Generation

Watch the deployment in real-time:

```bash
# View overall status
haymaker kw status

# View specific worker logs
haymaker logs --agent-id kw-oper-001 --follow

# View last 50 log entries
haymaker logs --agent-id kw-oper-001 --tail 50
```

**Example Log Output**:
```
[2025-12-10 15:30:45] INFO: Worker kw-oper-001 starting activity
[2025-12-10 15:32:12] INFO: Generating email 1 with AI (directive: limericks)
[2025-12-10 15:32:15] DEBUG: AI response received (148 tokens)
[2025-12-10 15:32:16] INFO: Sending email to kw-oper-008@tenant.com
[2025-12-10 15:32:17] OK: Email sent [LIMERICK:oper-001-00001-a3f2c1]
[2025-12-10 15:32:17] INFO: Email activity complete (sequence: 1)

[2025-12-10 15:45:23] INFO: Generating email 2 with AI (directive: limericks)
[2025-12-10 15:45:26] DEBUG: AI response received (152 tokens)
[2025-12-10 15:45:27] INFO: Sending email to kw-oper-015@tenant.com
[2025-12-10 15:45:28] OK: Email sent [LIMERICK:oper-001-00002-c5f4e3]
```

---

## Step 5: View Generated Limericks

After 10-15 minutes, check the actual generated emails:

**Option A: Using Azure CLI + Graph API**

```bash
# Query emails from first worker
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@tenant.com/messages?\$top=5" \
  --query "value[].{Subject:subject, Body:body.content}"
```

**Example Output**:
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

**Option B: Using Outlook Web**

1. Navigate to: https://outlook.office.com
2. Sign in as any KW worker (e.g., kw-oper-001@tenant.com)
3. Check inbox for received limericks
4. Look for `[LIMERICK:...]` markers in subjects

**Option C: Using PowerShell**

```powershell
# Connect to Exchange Online
Connect-ExchangeOnline

# Search for limerick emails
Search-Mailbox -Identity "kw-oper-001" -SearchQuery "subject:LIMERICK" -TargetMailbox "admin@tenant.com" -TargetFolder "LimerickSearch"

# View results in admin mailbox
```

---

## Step 6: Analyze Markers

Filter and count limerick emails using markers:

```bash
# Count emails with LIMERICK marker
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@tenant.com/messages?\$filter=contains(subject,'LIMERICK')" \
  --query "value | length(@)"

# Output: 10  (after 2 hours)

# Get all marker IDs
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@tenant.com/messages?\$filter=contains(subject,'LIMERICK')" \
  --query "value[].subject" | grep -oP '\[LIMERICK:[^\]]+\]'

# Output:
# [LIMERICK:oper-001-00001-a3f2c1]
# [LIMERICK:oper-001-00002-b4e3d2]
# [LIMERICK:oper-001-00003-c5f4e3]
# ...
```

**Marker Breakdown**:
```
[LIMERICK:oper-001-00005-a3f2c1]
 ^^^^^^^^ ^^^^^^^^ ^^^^^ ^^^^^^
 Format   Worker   Seq   UUID

LIMERICK - Custom format prefix (from --marker-format)
oper-001 - Worker ID (operations worker #1)
00005    - Email sequence number (5th email)
a3f2c1   - Unique identifier (6 hex chars)
```

---

## Step 7: Generate Telemetry Report

After deployment completes (2 hours), generate a summary:

```bash
haymaker kw telemetry-report --run-id kw-20251210-abc123
```

**Example Output**:
```
[cyan]Collecting telemetry for: kw-20251210-abc123[/cyan]

[bold]Activity Summary[/bold]

Workers: 25
Emails: 247
Calendar Events: 0
Teams Messages: 0
Documents: 0

[cyan]Email Breakdown by Worker:[/cyan]
  kw-oper-001: 10 emails
  kw-oper-002: 11 emails
  kw-oper-003: 9 emails
  ...
  kw-oper-025: 10 emails

[cyan]Marker Analysis:[/cyan]
  Total emails with markers: 247/247 (100%)
  Marker format: LIMERICK
  Average email length: 152 tokens
  AI model used: gpt-4-turbo

[cyan]Cost Breakdown:[/cyan]
  Total API calls: 247
  Input tokens: 12,350 (~50 tokens/email)
  Output tokens: 37,544 (~152 tokens/email)
  Estimated cost: $2.47
```

**Export as JSON**:
```bash
haymaker kw telemetry-report \
  --run-id kw-20251210-abc123 \
  --format json \
  --output limerick-report.json

# Output saved: limerick-report.json
```

---

## Step 8: Cleanup (Optional)

After testing, clean up the deployment:

```bash
# Clean up all resources from this deployment
haymaker cleanup --execution-id kw-20251210-abc123

# Confirm cleanup
# [yellow]This will delete:[/yellow]
#   - 25 worker containers
#   - Security groups
#   - Transport rules (if not shared)
# Continue? [y/N]: y

# [INFO] Deleting containers...
# [INFO] Removing security groups...
# [OK] Cleanup complete
```

**What Gets Deleted**:
- CLI containers for all workers
- Security groups created for this deployment
- Transport rules (if not used by other deployments)

**What Persists**:
- Worker user accounts (can be reused)
- Generated emails (remain in mailboxes)
- Telemetry logs

---

## Cost Analysis

Let's verify the actual costs:

**Estimated Costs** (from Step 2):
- 25 workers × 2 hours × 5 emails/hour = 250 emails
- 250 emails × $0.01/email (GPT-4) = $2.50

**Actual Costs** (from Step 7):
- 247 emails generated
- 12,350 input tokens + 37,544 output tokens
- GPT-4 Turbo pricing:
  - Input: $10/1M tokens → $0.12
  - Output: $30/1M tokens → $1.13
- **Total: $1.25** (cheaper than estimate!)

**Why Cheaper?**
- Some workers sent fewer emails (randomization)
- Efficient prompt engineering (shorter inputs)
- Limericks are concise (shorter outputs)

**Cost Optimization**:
```bash
# Use GPT-3.5 Turbo instead (5x cheaper)
haymaker kw deploy \
  --workers 25 \
  --duration 2 \
  --enable-ai-generation \
  --ai-model gpt-3.5-turbo \
  --email-directive "Write all emails as limericks about office work and meetings" \
  --marker-format LIMERICK

# Estimated cost: $0.25 (vs $1.25 with GPT-4)
```

---

## Variations

### Different Marker Styles

**Hidden Markers** (realistic appearance):
```bash
haymaker kw deploy \
  --workers 25 \
  --duration 2 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work" \
  --marker-style hidden \
  --marker-format LIMERICK

# Emails look normal, markers in HTML metadata
```

**Both Markers** (maximum tracking):
```bash
haymaker kw deploy \
  --workers 25 \
  --duration 2 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work" \
  --marker-style both \
  --marker-format LIMERICK

# Visible marker + hidden metadata
```

### Different Departments

**Engineering Limericks**:
```bash
haymaker kw deploy \
  --workers 10 \
  --department engineering \
  --enable-ai-generation \
  --email-directive "Write limericks about coding, bugs, and deployments"
```

**Executive Limericks**:
```bash
haymaker kw deploy \
  --workers 5 \
  --department executive \
  --enable-ai-generation \
  --email-directive "Write limericks about strategy, budgets, and leadership"
```

### Longer Duration

**8-hour deployment** (full workday):
```bash
haymaker kw deploy \
  --workers 25 \
  --duration 8 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks" \
  --marker-format LIMERICK

# Generates ~1000 limerick emails
# Cost: ~$10 (GPT-4) or ~$2 (GPT-3.5)
```

---

## Troubleshooting

### Issue: No Emails Generated

**Check**:
```bash
# View worker logs
haymaker logs --agent-id kw-oper-001 --tail 50

# Look for errors:
# [ERROR] Failed to send email: MailboxNotFound
```

**Solution**: Verify workers have mailboxes enabled
```bash
# Check mailbox status
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001"
```

---

### Issue: API Rate Limits

**Error**: `RateLimitError: Too many requests`

**Solution**: Reduce worker count or use slower rate
```bash
# Reduce from 25 to 10 workers
haymaker kw deploy --workers 10 --enable-ai-generation ...

# Operations workers send 5 emails/hour (safe rate)
```

---

### Issue: Non-Limerick Content

**Problem**: AI generates normal emails instead of limericks

**Check Directive**:
```bash
# Directive must be clear and specific
--email-directive "Write all emails as limericks"  # Good
--email-directive "Use limericks sometimes"        # Ambiguous
```

**Solution**: Use explicit directive
```bash
--email-directive "You must write every email as a limerick with 5 lines and AABBA rhyme scheme about office work"
```

---

### Issue: Missing Markers

**Problem**: Emails don't have `[LIMERICK:...]` markers

**Check**:
```bash
# Verify markers enabled (default)
haymaker kw deploy --workers 10 --enable-ai-generation --marker-format LIMERICK

# NOT disabled
# haymaker kw deploy --workers 10 --enable-ai-generation --no-enable-markers
```

**Verify in Email**:
```bash
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-oper-001@tenant.com/messages?\$top=1" \
  --query "value[0].subject"

# Expected: "Activity 1 from kw-oper-001 [LIMERICK:oper-001-00001-...]"
```

---

## Next Steps

Now that you've deployed limerick emails, try:

1. **Different Directives**: Security topics, technical jargon, casual tone
2. **Mixed Departments**: Deploy multiple departments with different styles
3. **Long-term Simulation**: 8-hour or multi-day deployments
4. **SIEM Integration**: Export markers to your SIEM for analysis
5. **Cost Optimization**: Compare GPT-3.5 vs GPT-4 quality/cost

**Related Tutorials**:
- [AI_EMAIL_GENERATION.md](./AI_EMAIL_GENERATION.md) - Complete AI email guide
- [EMAIL_MARKERS_GUIDE.md](./EMAIL_MARKERS_GUIDE.md) - Marker documentation

---

## Summary

**What You Did**:
1. ✅ Configured AI email generation with custom directive
2. ✅ Deployed 25 operations workers for 2 hours
3. ✅ Generated ~250 limerick emails
4. ✅ Tracked emails with LIMERICK markers
5. ✅ Analyzed telemetry and costs
6. ✅ Cleaned up resources

**Key Takeaways**:
- AI generation adds realism to KW simulations
- Custom directives enable creative testing scenarios
- Markers provide traceability
- Costs are predictable (~$0.01/email with GPT-4)
- GPT-3.5 offers 5x cost savings with slight quality reduction

**Actual Cost**: $1.25 (247 emails with GPT-4 Turbo)

---

**Questions?** See [AI_EMAIL_GENERATION.md](./AI_EMAIL_GENERATION.md) for troubleshooting and advanced usage.
