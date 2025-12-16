---
title: "Windows 365 + M365 E2E Demo with Telemetry Collection"
description: "Complete end-to-end demonstration of Cloud PC provisioning, activity simulation, and telemetry collection"
last_updated: 2025-11-26
doc_type: howto
owner: knowledge-worker-framework
---

# Windows 365 + M365 E2E Demo

Complete end-to-end demonstration of the Knowledge Worker Framework with Windows 365 Cloud PCs and M365 telemetry collection. This guide shows how to provision Cloud PCs, simulate realistic M365 activity, collect telemetry, and generate rich reports.

## Quick Start

```bash
# Set credentials
export KW_TENANT_ID="your-tenant-id"
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-secret"

# Run E2E demo
python provision_w365_e2e.py
```

**Expected output**:
```
======================================================================
PROVISIONING WINDOWS 365 CLOUD PCs
======================================================================

[1/5] Checking for Cloud PC provisioning policies...
[2/5] Creating 2 KW users with E5 licenses...
  ✓ w365.engineer1@tenant.onmicrosoft.com
  ✓ w365.sales1@tenant.onmicrosoft.com
[3/5] Creating Teams team for KW workers...
  ✓ M365 group created
  ✓ Teams team created
  ✓ Added 2 members to team
[4/5] Current status:
  Users: 2
  Teams team: team-id
[5/5] Windows 365 Cloud PC provisioning:
  Status: Architecture complete, ready when licenses + permissions available

✓ Results saved to w365_setup_results.json
```

## Contents

- [What This Demo Does](#what-this-demo-does)
- [Permission Requirements](#permission-requirements)
- [Graceful Degradation](#graceful-degradation)
- [Running the Demo](#running-the-demo)
- [Understanding the Workflow](#understanding-the-workflow)
- [Outputs and Reports](#outputs-and-reports)
- [Troubleshooting](#troubleshooting)

---

## What This Demo Does

The E2E demo showcases the complete Knowledge Worker Activity Framework with Cloud PC integration:

### Phase 1: Identity and Licensing (2 Workers)

Creates 2 knowledge workers with M365 E5 licenses:

```python
# Worker identities created
workers = [
    "w365.engineer1@tenant.onmicrosoft.com",  # Engineering persona
    "w365.sales1@tenant.onmicrosoft.com",     # Sales persona
]
```

**Why 2 workers?** The tenant has exactly 2 E5 licenses available. The demo works within this constraint to provide realistic demonstration.

### Phase 2: M365 Setup

**Teams Integration**:
- Creates M365 group: "KW W365 Test Team"
- Creates Teams team from group
- Adds both workers as members
- Creates channels: "Projects", "Random"
- Posts welcome messages

### Phase 3: Cloud PC Provisioning (Optional)

**With CloudPC.ReadWrite.All permission**:
- Creates provisioning policy
- Provisions 2 Cloud PCs (one per worker)
- Waits for provisioning (30-90 minutes)
- Assigns Cloud PCs to workers

**Without CloudPC.ReadWrite.All permission** (Graceful Degradation):
- Logs permission requirement
- Continues with M365 activity simulation
- Uses mock Cloud PC data for reports
- **Everything else works normally**

### Phase 4: Activity Simulation

Workers perform realistic M365 activities:

```python
# Email activity
await send_email(
    from_user="w365.engineer1@tenant.onmicrosoft.com",
    to_user="w365.sales1@tenant.onmicrosoft.com",
    subject="Project Status Update",
    body="Engineering sprint update..."
)

# Calendar activity
await create_meeting(
    organizer="w365.sales1@tenant.onmicrosoft.com",
    attendees=["w365.engineer1@tenant.onmicrosoft.com"],
    subject="Q1 Planning Meeting",
    duration_hours=1
)

# Teams activity
await post_teams_message(
    team_id="kw-team-id",
    channel_id="Projects",
    from_user="w365.engineer1@tenant.onmicrosoft.com",
    content="Sprint retrospective notes posted"
)
```

### Phase 5: Telemetry Collection

Collects comprehensive M365 activity telemetry:

```python
from azure_haymaker.knowledge_worker.telemetry import M365TelemetryCollector

collector = M365TelemetryCollector(graph_client, run_id)

# Collect per worker
emails = await collector.get_emails_for_worker(worker)
calendar = await collector.get_calendar_events_for_worker(worker)
teams = await collector.get_teams_messages_for_worker(worker, team_id, channel_id)

# Aggregate run summary
summary = await collector.get_run_summary(workers)
```

**Telemetry collected**:
- Email messages sent/received (subject, sender, recipients, timestamp)
- Calendar events (subject, organizer, attendees, start/end times, location)
- Teams messages (content, sender, team/channel, timestamp)

### Phase 6: Report Generation

Generates multiple output formats:

1. **Console Report** (Rich library formatting)
2. **JSON Export** (`w365_telemetry_report.json`)
3. **PowerPoint Report** (`w365_telemetry_report.pptx`) - Coming soon

---

## Permission Requirements

### Minimum Required (Demo Works Today)

These permissions are **already granted** and sufficient for E2E demo:

| Permission | Scope | Purpose |
|------------|-------|---------|
| `User.ReadWrite.All` | Delegated | Create/manage worker identities |
| `Group.ReadWrite.All` | Delegated | Create M365 groups and Teams |
| `Team.Create` | Delegated | Create Teams teams |
| `TeamMember.ReadWrite.All` | Delegated | Add members to teams |
| `ChannelMessage.Send` | Delegated | Post Teams messages |
| `Mail.ReadWrite` | Delegated | Send emails, read mailboxes |
| `Calendars.ReadWrite` | Delegated | Create calendar events |

**Result**: Full E2E demo works **except** Cloud PC provisioning uses mock data.

### Optional for Cloud PC Provisioning

This permission requires admin consent and is **not yet granted**:

| Permission | Scope | Purpose | Impact Without |
|------------|-------|---------|----------------|
| `CloudPC.ReadWrite.All` | Application | Provision Cloud PCs | Mock provisioning data used |

**Graceful Degradation**: Demo continues normally without this permission, using simulated Cloud PC data for reports.

---

## Graceful Degradation

The framework handles missing Cloud PC permissions gracefully:

### With CloudPC.ReadWrite.All Permission

```python
# Real Cloud PC provisioning
policy_id = await cloudpc_manager.ensure_provisioning_policy()
cloud_pc_id = await cloudpc_manager.provision_cloud_pc(worker, policy_id)
ready = await cloudpc_manager.wait_for_provisioning(worker, timeout_minutes=90)

if ready:
    print(f"Cloud PC provisioned: {cloud_pc_id}")
    # Assign to worker for activity simulation
```

**Timeline**: 30-90 minutes for provisioning

### Without CloudPC.ReadWrite.All Permission (Default)

```python
# Graceful fallback to mock provisioning
try:
    policy_id = await cloudpc_manager.ensure_provisioning_policy()
except PermissionError as e:
    logger.info("CloudPC permission not available, using mock provisioning")

    # Mock Cloud PC data
    mock_cloud_pc = {
        "id": f"mock-cloudpc-{worker.worker_id}",
        "status": "provisioned",
        "display_name": f"Mock-{worker.display_name}",
        "provisioning_time": "instant",
    }

    # Continue with M365 activity simulation
    # All telemetry collection works normally
```

**Timeline**: Instant, demo continues immediately

### What Works Without Cloud PC Permission

**Fully functional**:
- Worker identity creation
- M365 E5 license assignment
- Teams team creation and member management
- Email sending and receiving
- Calendar event creation
- Teams message posting
- **All telemetry collection** (email, calendar, Teams)
- JSON and PPTX report generation

**Mock data used for**:
- Cloud PC provisioning status
- Cloud PC display names
- Cloud PC managed device IDs

**Impact**: Reports show realistic M365 activity telemetry with simulated Cloud PC metadata. Perfect for demonstrating the framework's capabilities while waiting for Cloud PC permissions.

---

## Running the Demo

### Prerequisites

1. **Azure AD App Registration**

```bash
# Application (client) ID
KW_APP_ID="12345678-1234-1234-1234-123456789abc"

# Directory (tenant) ID
KW_TENANT_ID="87654321-4321-4321-4321-210987654321"

# Client secret
KW_CLIENT_SECRET="your-secret-value"
```

2. **Microsoft 365 E5 Licenses**

Requirement: **2 E5 licenses available** in tenant

Check license availability:

```bash
# Via Azure Portal
# Navigate to: Azure AD > Licenses > All products
# Verify: Microsoft 365 E5 has at least 2 available licenses
```

3. **Python Environment**

```bash
# Install dependencies
pip install azure-haymaker

# Or from source
pip install -e .
```

### Run the Demo

```bash
# Set environment variables
export KW_TENANT_ID="your-tenant-id"
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-secret"

# Run E2E demo
python provision_w365_e2e.py
```

### Demo Phases and Timing

| Phase | Duration | Description |
|-------|----------|-------------|
| Identity Setup | 30 seconds | Create 2 workers with E5 licenses |
| Teams Setup | 45 seconds | Create team, channels, add members |
| Cloud PC Check | 5 seconds | Check permissions (instant mock fallback) |
| Activity Simulation | 2 minutes | Send emails, create meetings, post messages |
| Telemetry Collection | 30 seconds | Collect all M365 activity data |
| Report Generation | 15 seconds | Generate JSON and console reports |
| **Total** | **~4 minutes** | **Complete E2E demo** |

**With Cloud PC provisioning**: Add 30-90 minutes for Cloud PC provisioning phase.

---

## Understanding the Workflow

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Identity & Licensing                                         │
│    - Create 2 workers with E5 licenses                          │
│    - Provision Entra ID users                                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. M365 Setup                                                   │
│    - Create M365 group: "KW W365 Test Team"                     │
│    - Create Teams team with channels                            │
│    - Add workers as team members                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Cloud PC Provisioning (Optional)                             │
│    ┌──────────────────────────────────────────────────────┐    │
│    │ With CloudPC.ReadWrite.All:                          │    │
│    │   - Create provisioning policy                       │    │
│    │   - Provision 2 Cloud PCs                            │    │
│    │   - Wait 30-90 minutes                               │    │
│    └──────────────────────────────────────────────────────┘    │
│    ┌──────────────────────────────────────────────────────┐    │
│    │ Without CloudPC.ReadWrite.All (Graceful):            │    │
│    │   - Log permission requirement                       │    │
│    │   - Use mock Cloud PC data                           │    │
│    │   - Continue immediately                             │    │
│    └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Activity Simulation                                          │
│    - Worker 1 (Engineer): Send project updates via email       │
│    - Worker 2 (Sales): Create sales meetings                   │
│    - Both: Post Teams messages in channels                     │
│    - Both: Accept/update calendar events                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Telemetry Collection                                         │
│    - Query email activity via Graph API                         │
│    - Query calendar events via Graph API                        │
│    - Query Teams messages via Graph API                         │
│    - Aggregate per-worker and run-level metrics                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Report Generation                                            │
│    - Console report (Rich library formatting)                   │
│    - JSON export: w365_telemetry_report.json                    │
│    - PowerPoint report: w365_telemetry_report.pptx (planned)    │
└─────────────────────────────────────────────────────────────────┘
```

### Code Structure

```python
# Main E2E demo script
provision_w365_e2e.py
    ├── Identity creation (EntraUserManager)
    ├── Teams setup (TeamsIntegration)
    ├── Cloud PC provisioning (Windows365CloudPCManager)
    │   └── Graceful degradation on permission error
    ├── Activity simulation (worker agents)
    ├── Telemetry collection (M365TelemetryCollector)
    └── Report generation (JSON/PPTX)

# Core modules
src/azure_haymaker/knowledge_worker/
    ├── identity/user_manager.py         # Worker provisioning
    ├── teams_integration.py              # Teams management
    ├── endpoints/cloud_pc.py             # Cloud PC provisioning
    ├── telemetry/m365_telemetry.py       # Telemetry collection
    └── models/worker.py                  # Worker identity model

# Tests
tests/
    ├── unit/test_cloud_pc.py             # Cloud PC unit tests
    ├── unit/test_m365_telemetry.py       # Telemetry unit tests
    └── integration/test_cloud_pc_integration.py  # E2E integration tests
```

---

## Outputs and Reports

### Console Report (Rich Formatting)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Windows 365 + M365 E2E Demo Report                              ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Run ID: abc12345-def6-7890-ghij-klmnopqrstuv                     ┃
┃ Timestamp: 2025-11-26 14:30:00 UTC                               ┃
┃ Duration: 4 minutes 12 seconds                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Workers Provisioned: 2
┌────────────────────────────────────┬─────────────┬──────────────┐
│ Worker                             │ Persona     │ Endpoint     │
├────────────────────────────────────┼─────────────┼──────────────┤
│ w365.engineer1@tenant.com          │ Engineering │ Mock Cloud PC│
│ w365.sales1@tenant.com             │ Sales       │ Mock Cloud PC│
└────────────────────────────────────┴─────────────┴──────────────┘

M365 Activity Summary
┌─────────────────┬───────┬──────────┬────────┐
│ Worker          │ Email │ Calendar │ Teams  │
├─────────────────┼───────┼──────────┼────────┤
│ Engineer 1      │   12  │    4     │   8    │
│ Sales 1         │   15  │    6     │   5    │
├─────────────────┼───────┼──────────┼────────┤
│ Total           │   27  │   10     │   13   │
└─────────────────┴───────┴──────────┴────────┘

Telemetry Collection Status: ✓ Success
Reports Generated:
  • w365_setup_results.json
  • w365_telemetry_report.json
  • w365_telemetry_report.pptx (planned)
```

### JSON Export

```json
{
  "run_id": "abc12345-def6-7890-ghij-klmnopqrstuv",
  "timestamp": "2025-11-26T14:30:00Z",
  "duration_seconds": 252,
  "workers": [
    {
      "worker_id": "kw-abc12345-001",
      "display_name": "W365 Engineer 1",
      "user_principal_name": "w365.engineer1@tenant.onmicrosoft.com",
      "persona": "engineering",
      "endpoint_type": "mock_cloud_pc",
      "activity": {
        "email_count": 12,
        "calendar_count": 4,
        "teams_count": 8
      }
    },
    {
      "worker_id": "kw-abc12345-002",
      "display_name": "W365 Sales 1",
      "user_principal_name": "w365.sales1@tenant.onmicrosoft.com",
      "persona": "sales",
      "endpoint_type": "mock_cloud_pc",
      "activity": {
        "email_count": 15,
        "calendar_count": 6,
        "teams_count": 5
      }
    }
  ],
  "aggregated_metrics": {
    "total_workers": 2,
    "total_emails": 27,
    "total_calendar_events": 10,
    "total_teams_messages": 13
  },
  "cloud_pc_status": "mock_provisioning_used",
  "cloud_pc_permission": false,
  "notes": "Demo completed successfully using graceful degradation for Cloud PC provisioning"
}
```

### PowerPoint Report (Planned)

**Slides**:
1. **Title Slide**: Windows 365 + M365 E2E Demo Results
2. **Executive Summary**: Key metrics, worker count, activity summary
3. **Worker Details**: Per-worker breakdown with charts
4. **Email Activity**: Timeline chart, top senders/recipients
5. **Calendar Activity**: Meeting frequency, organizer distribution
6. **Teams Activity**: Message volume by channel, participation rates
7. **Technical Details**: Provisioning status, permissions, next steps

**Generation**:
```python
# Coming soon
from azure_haymaker.knowledge_worker.reporting import PPTXReportGenerator

generator = PPTXReportGenerator()
generator.create_e2e_report(
    telemetry_data=summary,
    output_path="w365_telemetry_report.pptx"
)
```

---

## Troubleshooting

### Permission Errors

**Symptom**: `403 Forbidden` when creating users or teams

**Solution**:
```bash
# Verify app permissions
az ad app permission list --id $KW_APP_ID

# Required permissions
User.ReadWrite.All
Group.ReadWrite.All
Team.Create

# Grant admin consent if missing
az ad app permission admin-consent --id $KW_APP_ID
```

### License Quota Exceeded

**Symptom**: `License quota exceeded` when creating workers

**Cause**: Fewer than 2 E5 licenses available in tenant

**Solution**:
```python
# Option 1: Reduce worker count in demo script
workers = 1  # Use only 1 worker

# Option 2: Purchase additional E5 licenses
# Azure Portal > Microsoft 365 Admin > Billing > Purchase services
```

### Cloud PC Permission Not Available

**Symptom**: `CloudPC permission not available, using mock provisioning`

**This is expected and normal!** The demo uses graceful degradation:

```python
# Behavior:
# 1. Demo attempts Cloud PC provisioning
# 2. Permission check fails (CloudPC.ReadWrite.All not granted)
# 3. Demo logs informational message
# 4. Demo continues with mock Cloud PC data
# 5. All M365 activity works normally
# 6. Reports generated successfully

# No action needed - this is working as designed
```

**To enable real Cloud PC provisioning**:
1. Request `CloudPC.ReadWrite.All` permission from tenant admin
2. Admin grants permission via Azure Portal
3. Re-run demo - Cloud PC provisioning will work

**Timeline**: Permission approval may take days/weeks. Use mock provisioning in the meantime.

### Teams Team Creation Fails

**Symptom**: `Failed to create Teams team from group`

**Cause**: Teams provisioning can take 5-15 minutes after group creation

**Solution**:
```python
# Add delay between group creation and Teams creation
await asyncio.sleep(60)  # Wait 60 seconds

# Retry with exponential backoff
for attempt in range(5):
    try:
        team_id = await teams_mgr.create_team_from_group(group_id)
        break
    except Exception as e:
        if attempt < 4:
            await asyncio.sleep(2 ** attempt * 10)
        else:
            raise
```

### Telemetry Collection Returns Empty Results

**Symptom**: All telemetry counts are 0

**Cause**: Activity simulation may not have completed before collection

**Solution**:
```python
# Add delay between activity simulation and telemetry collection
await simulate_worker_activity(workers)

# Wait for Graph API indexing
await asyncio.sleep(30)

# Collect telemetry
summary = await collector.get_run_summary(workers)
```

### JSON Export File Permission Error

**Symptom**: `PermissionError: [Errno 13] Permission denied: 'w365_setup_results.json'`

**Cause**: File is open in another program or lacks write permissions

**Solution**:
```bash
# Close file if open
# Or save to different location
python provision_w365_e2e.py --output-dir ./reports/
```

---

## Related Documentation

- [Windows 365 Cloud PC Provisioning](./WINDOWS365_CLOUD_PC.md) - Detailed Cloud PC provisioning guide
- [M365 Telemetry Collection](./M365_TELEMETRY.md) - Telemetry collection API reference
- [Knowledge Worker Framework Architecture](./ARCHITECTURE.md) - Overall framework design
- [Identity and Licensing](./IDENTITY_LICENSING.md) - User provisioning and license management

---

## Next Steps

After running the E2E demo:

1. **Analyze Results**
   - Review JSON export: `w365_setup_results.json`
   - Examine telemetry data: `w365_telemetry_report.json`
   - Verify worker activity in Microsoft 365 admin portal

2. **Request Cloud PC Permissions** (Optional)
   - Submit request for `CloudPC.ReadWrite.All` permission
   - Provide business justification (realistic testing, desktop telemetry)
   - Re-run demo after approval for full Cloud PC provisioning

3. **Scale Up** (When More Licenses Available)
   - Increase worker count beyond 2
   - Test hybrid endpoint strategy (Cloud PC + CLI containers)
   - Run extended scenarios (days/weeks of activity)

4. **Integrate with Haymaker Orchestration**
   - Connect to Azure Container Apps orchestrator
   - Schedule recurring knowledge worker simulations
   - Enable automated telemetry collection and reporting

---

## Appendix: Environment Variables

Complete list of environment variables used in E2E demo:

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `KW_TENANT_ID` | Yes | Azure AD tenant ID | `87654321-4321-4321-4321-210987654321` |
| `KW_APP_ID` | Yes | Azure AD app registration ID | `12345678-1234-1234-1234-123456789abc` |
| `KW_CLIENT_SECRET` | Yes | App registration client secret | `your-secret-value` |
| `KW_DOMAIN` | No | M365 domain (default: from tenant) | `tenant.onmicrosoft.com` |
| `KW_RUN_ID` | No | Custom run ID (default: generated UUID) | `custom-run-123` |
| `KW_WORKER_COUNT` | No | Number of workers (default: 2) | `2` |

```bash
# Example .env file
KW_TENANT_ID=87654321-4321-4321-4321-210987654321
KW_APP_ID=12345678-1234-1234-1234-123456789abc
KW_CLIENT_SECRET=your-secret-value
KW_DOMAIN=tenant.onmicrosoft.com
```

**Security Note**: Never commit `.env` files to version control. Use Azure Key Vault for production credentials.
