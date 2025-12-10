# Knowledge Worker Email Markers Guide

**Purpose**: Add custom markers and metadata to Knowledge Worker emails for tracking, testing, and analysis.

**Last Updated**: 2025-12-10
**Status**: Implementation Guide

---

## Table of Contents

1. [Overview](#overview)
2. [Marker Patterns](#marker-patterns)
3. [Implementation Options](#implementation-options)
4. [Quick Start](#quick-start)
5. [Advanced Customization](#advanced-customization)
6. [Telemetry Integration](#telemetry-integration)

---

## Overview

Knowledge Worker emails are generated in `orchestrator.py` (lines 584-585). By default, emails use simple content:

```python
subject = f"Activity {activity_count + 1} from {worker_id}"
body = f"<p>Automated activity generated at {datetime.now(UTC).isoformat()}</p>"
```

**Use Cases for Markers**:
- 🔍 **Testing**: Track specific test scenarios
- 📊 **Analytics**: Correlate emails with activity logs
- 🎯 **Red Team Ops**: Identify benign haymaker traffic vs. red team signals
- 🔬 **SIEM Testing**: Validate detection rules with known markers

---

## Marker Patterns

### Pattern 1: Visible Subject Markers

**Best for**: Quick visual identification, testing, debugging

```python
subject = f"Activity {activity_count + 1} from {worker_id} [TEST-ID:abc-123]"
```

**Example Email Subject**:
```
Activity 5 from kw-engi-001 [TEST-ID:run-20251210-005]
```

### Pattern 2: Hidden HTML Metadata

**Best for**: Stealth markers, production use, SIEM parsing

```python
body = f"""<p>Automated activity generated at {datetime.now(UTC).isoformat()}</p>
<p style="font-size:0;color:white;">
[METADATA:run_id=run-123|worker_id={worker_id}|activity_type=email|sequence={activity_count}]
</p>"""
```

**Result**: Marker invisible to users, parseable by email clients

### Pattern 3: X-Header Metadata (Advanced)

**Best for**: Email infrastructure analysis, SMTP tracking

```python
# Note: Requires Graph API sendMail with internetMessageHeaders
message_data["internetMessageHeaders"] = [
    {"name": "X-HayMaker-RunID", "value": run_id},
    {"name": "X-HayMaker-Worker", "value": worker_id},
    {"name": "X-HayMaker-Type", "value": "test-email"},
]
```

### Pattern 4: UUID-Based Activity IDs

**Best for**: Unique tracking, log correlation

```python
from uuid import uuid4

activity_id = f"{worker_id}-{activity_count:05d}-{uuid4().hex[:8]}"
subject = f"Activity {activity_count + 1} from {worker_id} [ID:{activity_id}]"
```

---

## Implementation Options

### Option A: Patch `orchestrator.py` (EASIEST)

**File**: `src/azure_haymaker/knowledge_worker/orchestrator.py`
**Lines**: 579-590

**Original Code**:
```python
if activity_type == "email":
    recipients = worker.get_allowed_recipients()
    if recipients:
        to = [random.choice(recipients)]
        subject = f"Activity {activity_count + 1} from {worker_id}"
        body = f"<p>Automated activity generated at {datetime.now(UTC).isoformat()}</p>"

        await worker.send_email(to=to, subject=subject, body=body)
        logger.info(f"Worker {worker_id} sent email to {to[0]}")
```

**Enhanced with Markers**:
```python
if activity_type == "email":
    recipients = worker.get_allowed_recipients()
    if recipients:
        to = [random.choice(recipients)]

        # Generate unique marker
        from uuid import uuid4
        run_id = getattr(self, 'current_run_id', 'unknown')
        activity_id = f"{worker_id.replace('kw-', '')}-{activity_count:05d}-{uuid4().hex[:6]}"

        # Add visible marker to subject
        subject = f"Activity {activity_count + 1} from {worker_id} [MARKER:{activity_id}]"

        # Add hidden metadata to body
        timestamp = datetime.now(UTC).isoformat()
        body = f"""<p>Automated activity generated at {timestamp}</p>
<p style="font-size:1px;color:white;display:none;">
[METADATA:run_id={run_id}|worker_id={worker_id}|activity_id={activity_id}|sequence={activity_count}|type=email_send|timestamp={timestamp}]
</p>"""

        await worker.send_email(to=to, subject=subject, body=body)
        logger.info(f"Worker {worker_id} sent email with marker {activity_id} to {to[0]}")
```

**Result**: Every email includes both visible and hidden markers

---

### Option B: Add Configuration Parameter

**File**: `src/azure_haymaker/knowledge_worker/orchestrator.py`
**Add to DeploymentConfig** (line 75):

```python
@dataclass
class DeploymentConfig:
    name: str = "kw-deployment"
    total_workers: int = 10
    departments: dict[str, dict[str, Any]] = field(default_factory=dict)
    duration_hours: int = 8
    tenant_domain: str = ""
    m365_app_id: str = ""

    # NEW: Marker configuration
    enable_email_markers: bool = True
    marker_format: str = "MARKER"  # "MARKER", "TEST-ID", "RUN", etc.
    include_metadata: bool = True
```

**Usage in orchestrator** (line 584):

```python
if self.config.enable_email_markers:
    from uuid import uuid4
    marker_id = f"{worker_id}-{activity_count}-{uuid4().hex[:6]}"
    subject = f"Activity {activity_count + 1} from {worker_id} [{self.config.marker_format}:{marker_id}]"
else:
    subject = f"Activity {activity_count + 1} from {worker_id}"
```

**Deploy with markers enabled**:
```python
config = DeploymentConfig(
    total_workers=25,
    enable_email_markers=True,
    marker_format="TEST-ID",
    include_metadata=True,
    ...
)
```

---

### Option C: Per-Worker Custom Markers

**Use Case**: Different marker patterns per department/worker type

**Enhanced deployment config**:
```python
departments={
    "engineering": {
        "count": 5,
        "endpoint_type": "windows_vm",
        "marker_prefix": "ENG",  # NEW
        "activity": {...},
    },
    "operations": {
        "count": 20,
        "endpoint_type": "cli_container",
        "marker_prefix": "OPS",  # NEW
        "activity": {...},
    },
}
```

**Implementation** (orchestrator.py line 584):
```python
dept_config = self.config.departments.get(worker.department, {})
marker_prefix = dept_config.get("marker_prefix", "KW")
marker_id = f"{marker_prefix}-{worker_id}-{activity_count:05d}"
subject = f"Activity {activity_count + 1} from {worker_id} [ID:{marker_id}]"
```

**Result**:
- Engineering emails: `[ID:ENG-kw-engi-001-00005]`
- Operations emails: `[ID:OPS-kw-oper-001-00005]`

---

## Quick Start

### 1. Simple Patch (5 minutes)

Edit `/home/azureuser/src/AzureHayMaker/src/azure_haymaker/knowledge_worker/orchestrator.py`:

```bash
# Line 584-585, replace with:
```

```python
# Generate unique marker
from uuid import uuid4
activity_id = f"{worker_id}-{activity_count:05d}-{uuid4().hex[:6]}"
subject = f"Activity {activity_count + 1} from {worker_id} [TEST-ID:{activity_id}]"
body = f"""<p>Automated activity generated at {datetime.now(UTC).isoformat()}</p>
<p style="display:none;">[METADATA:worker={worker_id}|seq={activity_count}|id={activity_id}]</p>"""
```

### 2. Test Locally

```bash
# Deploy with markers
python deploy_25_workers.py

# Check email logs for markers
tail -f /var/log/haymaker/orchestrator.log | grep MARKER
```

### 3. Query Emails with Markers

```bash
# Using Azure CLI + Graph API
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/kw-user@tenant.com/messages?\$filter=contains(subject,'TEST-ID')" \
  --query "value[].{Subject:subject, Received:receivedDateTime}"
```

---

## Advanced Customization

### Example 1: Red Team Scenario Markers

**Use Case**: Mark specific emails for red team payload delivery

```python
# In orchestrator.py
red_team_emails = [588, 1234, 2891]  # Specific activity numbers

if activity_count in red_team_emails:
    marker = f"REDTEAM-PAYLOAD-{activity_count}"
else:
    marker = f"BENIGN-{activity_count}"

subject = f"Activity {activity_count + 1} from {worker_id} [{marker}]"
```

### Example 2: Campaign-Based Markers

**Use Case**: Track multiple test campaigns over time

```python
# In DeploymentConfig
campaign_id: str = "Q1-2025-SIEM-TEST"

# In orchestrator
subject = f"Activity {activity_count + 1} [{self.config.campaign_id}-{activity_id}]"
```

### Example 3: Time-Based Markers

**Use Case**: Identify activity time windows

```python
from datetime import datetime, UTC

hour_marker = datetime.now(UTC).strftime("%Y%m%d-%H")
subject = f"Activity {activity_count + 1} from {worker_id} [TIME:{hour_marker}]"
```

---

## Telemetry Integration

### Capture Markers in Logs

**File**: `src/azure_haymaker/knowledge_worker/operations/email.py` (line 163-171)

**Add marker extraction**:
```python
import re

# Extract marker from subject if present
marker_match = re.search(r'\[(TEST-ID|MARKER|ID):([^\]]+)\]', subject)
marker = marker_match.group(2) if marker_match else None

self._log_operation(
    "email_send",
    {
        "to": valid_to,
        "subject": subject[:50],
        "cc_count": len(valid_cc),
        "bcc_count": len(valid_bcc),
        "test_marker": marker,  # NEW - captured marker
    },
)
```

### Query Telemetry by Marker

```python
from azure_haymaker.knowledge_worker.telemetry import M365TelemetryCollector

collector = M365TelemetryCollector(graph_client, run_id)
emails = await collector.get_emails_for_worker(worker)

# Filter emails with specific markers
marked_emails = [e for e in emails if "TEST-ID:" in e.subject]
```

### Export Markers to SIEM

**JSON Export**:
```python
{
  "email_id": "AAMkAGI...",
  "subject": "Activity 5 from kw-engi-001 [TEST-ID:engi-001-00005-a3f2c1]",
  "sender": "kw-engi-001@tenant.onmicrosoft.com",
  "marker": "engi-001-00005-a3f2c1",
  "timestamp": "2025-12-10T17:30:00Z",
  "worker_id": "kw-engi-001",
  "activity_sequence": 5
}
```

---

## Marker Format Reference

| Format | Example | Use Case |
|--------|---------|----------|
| `[TEST-ID:abc-123]` | `[TEST-ID:eng-001-00005-a3f2c1]` | General testing |
| `[MARKER:xyz]` | `[MARKER:run-20251210-005]` | Deployment tracking |
| `[RUN:id]` | `[RUN:prod-deployment-123]` | Run correlation |
| `[CAMPAIGN:name]` | `[CAMPAIGN:Q1-SIEM-TEST]` | Campaign grouping |
| `[SEQ:n]` | `[SEQ:00142]` | Activity sequence |
| `[TIME:ts]` | `[TIME:20251210-1730]` | Time window |
| `[DEPT:name]` | `[DEPT:ENG]` | Department |
| `[TYPE:category]` | `[TYPE:BENIGN]` | Classification |

---

## Best Practices

✅ **DO**:
- Keep markers concise (< 50 chars)
- Use consistent format across deployment
- Include timestamp or sequence number
- Log markers for correlation
- Test marker visibility in different email clients

❌ **DON'T**:
- Include sensitive data in markers
- Use special characters that break email parsing
- Make markers too long (affects subject line display)
- Forget to document marker format
- Mix marker formats inconsistently

---

## Example: Complete Implementation

Save as `deploy_25_workers_with_markers.py`:

```python
#!/usr/bin/env python3
"""Deploy 25 KW with custom email markers."""

import asyncio
from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from azure_haymaker.knowledge_worker import DeploymentConfig, KnowledgeWorkerOrchestrator

async def main():
    # ... (auth setup)

    config = DeploymentConfig(
        name="kw-25-marked",
        total_workers=25,
        departments={
            "engineering": {
                "count": 5,
                "endpoint_type": "windows_vm",
                "marker_prefix": "ENG",  # Custom marker prefix
            },
            "operations": {
                "count": 20,
                "endpoint_type": "cli_container",
                "marker_prefix": "OPS",
            },
        },
    )

    orchestrator = KnowledgeWorkerOrchestrator(graph_client)
    run_id = orchestrator.create_deployment(config)
    await orchestrator.start_deployment(run_id)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Summary

**Location**: `src/azure_haymaker/knowledge_worker/orchestrator.py` (lines 584-585)

**Simplest Approach**: Patch lines 584-585 to include marker in subject

**Production Approach**: Add `enable_email_markers` to `DeploymentConfig`

**Stealth Approach**: Use hidden HTML metadata instead of subject markers

**All approaches** allow tracking, correlation, and identification of Knowledge Worker emails for testing and analysis.

---

## Related Documentation

- [Knowledge Worker Architecture](./ARCHITECTURE.md)
- [M365 Telemetry Collection](./M365_TELEMETRY.md)
- [SIEM Integration](./SIEM_TELEMETRY_EXPORT.md)
