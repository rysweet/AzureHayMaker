# Getting Started: SIEM Telemetry Export (Issue #124)

**Your complete guide to implementing Issue #124**

**Priority**: P0-Critical | **Effort**: 2.5-3.5 weeks | **ROI**: 120%

---

## What You're Building

Stream M365 and Azure telemetry from HayMaker to external SIEM platforms (Sentinel, Splunk, Syslog).

**Why It Matters**: Core use case - red team exercises require "hay" telemetry to appear in target SIEM.

---

## Before You Start (15 minutes)

### 1. Read the Spec
📄 **Full Specification**: [`specs/SIEM_TELEMETRY_EXPORT.md`](../specs/SIEM_TELEMETRY_EXPORT.md) (80KB)

**Key sections to focus on**:
- Architecture Overview (pages 1-5)
- Component Design (pages 6-15)
- Sentinel Connector (pages 16-25) ← **START HERE**
- Testing Strategy (pages 60-65)

### 2. Check Dependencies
⚠️ **BLOCKER**: PR #119 must be merged first

```bash
# Verify PR #119 is merged
gh pr view 119 --json state,mergedAt

# If not merged yet, either:
# Option A: Wait for merge (recommended)
# Option B: Work on tests/design while waiting
```

### 3. Review Starter Code
📝 **Template**: [`examples/siem_export_starter.py`](../examples/siem_export_starter.py)

```bash
# Review the skeleton implementation
cat examples/siem_export_starter.py

# Note the TODOs - these are your implementation tasks
grep -n "TODO" examples/siem_export_starter.py
```

---

## Phase 1: Set Up (Day 1, ~2 hours)

### Create Branch
```bash
git checkout main
git pull origin main
git checkout -b feat/issue-124-siem-export
```

### Create Directory Structure
```bash
mkdir -p src/azure_haymaker/knowledge_worker/telemetry/connectors
touch src/azure_haymaker/knowledge_worker/telemetry/exporter.py
touch src/azure_haymaker/knowledge_worker/telemetry/normalizer.py
touch src/azure_haymaker/knowledge_worker/telemetry/connectors/__init__.py
touch src/azure_haymaker/knowledge_worker/telemetry/connectors/sentinel.py
```

### Copy Starter Code
```bash
cp examples/siem_export_starter.py src/azure_haymaker/knowledge_worker/telemetry/exporter.py
```

### Install Dependencies
```bash
# Add to pyproject.toml
# [project.dependencies]
# "azure-monitor-ingestion" = "^1.0.0"  # For Sentinel
# "requests" = "^2.31.0"  # For Splunk HEC

uv sync
```

---

## Phase 2: Write Tests First (Days 2-3, ~12 hours)

**Test-Driven Development**: Write tests BEFORE implementation

### Create Test Files
```bash
mkdir -p tests/unit/telemetry
touch tests/unit/telemetry/__init__.py
touch tests/unit/telemetry/test_siem_export.py
touch tests/unit/telemetry/test_event_normalizer.py
touch tests/unit/telemetry/test_sentinel_connector.py
```

### Write Failing Tests

**`tests/unit/telemetry/test_sentinel_connector.py`**:
```python
import pytest
from azure_haymaker.knowledge_worker.telemetry.exporter import TelemetryEvent
from azure_haymaker.knowledge_worker.telemetry.connectors.sentinel import SentinelConnector

@pytest.fixture
def sample_event():
    return TelemetryEvent(
        timestamp="2025-11-30T12:00:00Z",
        event_type="email_sent",
        source="M365",
        severity="info",
        data={"from": "user@example.com", "to": "recipient@example.com"},
        worker_id="worker-001",
        run_id="run-12345"
    )

def test_sentinel_connector_connect():
    """Test Sentinel connector establishes connection."""
    connector = SentinelConnector(
        workspace_id="test-workspace",
        shared_key="test-key"
    )
    # TODO: Should connect successfully
    assert connector is not None

@pytest.mark.asyncio
async def test_sentinel_connector_send_event(sample_event):
    """Test sending single event to Sentinel."""
    connector = SentinelConnector(
        workspace_id="test-workspace",
        shared_key="test-key"
    )
    await connector.connect()

    # Should send successfully
    result = await connector.send_event(sample_event)
    assert result is True

# Add 10-15 more test cases...
```

### Run Tests (Should Fail)
```bash
pytest tests/unit/telemetry/test_sentinel_connector.py -v
# Expected: FAIL (implementation doesn't exist yet)
```

---

## Phase 3: Implement Sentinel Connector (Days 4-8, ~30 hours)

**Focus on Sentinel first** (Azure-native, highest priority)

### Implement SentinelConnector

**File**: `src/azure_haymaker/knowledge_worker/telemetry/connectors/sentinel.py`

**Steps**:
1. Implement `__init__()` - Initialize HTTP client, auth
2. Implement `connect()` - Validate workspace, test connectivity
3. Implement `send_event()` - POST to Data Collector API
4. Implement `send_batch()` - Batch up to 10,000 events
5. Implement `disconnect()` - Cleanup
6. Implement `health_check()` - Verify connector working

**See spec pages 16-25 for detailed code examples**

### Run Tests Continuously
```bash
# After each method implementation
pytest tests/unit/telemetry/test_sentinel_connector.py::test_METHOD_NAME -v

# When all unit tests pass
pytest tests/unit/telemetry/ -v
```

---

## Phase 4: Implement Event Normalizer (Days 9-10, ~12 hours)

**File**: `src/azure_haymaker/knowledge_worker/telemetry/normalizer.py`

**Methods to implement**:
- `to_cef(event)` - Convert to Common Event Format
- `to_json_ecs(event)` - Convert to JSON/ECS format
- `to_syslog(event)` - Convert to RFC 5424 Syslog

**See spec pages 26-35 for format examples**

---

## Phase 5: Implement Main Exporter (Days 11-12, ~12 hours)

**File**: `src/azure_haymaker/knowledge_worker/telemetry/exporter.py`

**Features**:
- Load configuration
- Initialize connectors
- Route events to connectors
- Retry logic with exponential backoff
- Circuit breaker for failing connectors
- Dead letter queue for failed events

---

## Phase 6: Integration Testing (Days 13-14, ~10 hours)

### Create Integration Tests
```bash
touch tests/integration/test_siem_integration.py
```

### Test with Real Sentinel Workspace
```python
@pytest.mark.integration
async def test_end_to_end_sentinel():
    """Test actual export to real Sentinel workspace."""
    # Requires: SENTINEL_WORKSPACE_ID and SENTINEL_SHARED_KEY env vars

    connector = SentinelConnector(
        workspace_id=os.getenv("SENTINEL_WORKSPACE_ID"),
        shared_key=os.getenv("SENTINEL_SHARED_KEY")
    )

    # Send test event
    event = create_test_event()
    result = await connector.send_event(event)
    assert result is True

    # Verify in Sentinel (may require API query)
```

---

## Phase 7: E2E Testing (Day 15, ~6 hours) - MANDATORY

**Test like a user would use it**:

### Scenario 1: Basic Export
```bash
# Start orchestrator
cd src && uvicorn orchestrator_server:app

# Trigger Knowledge Worker execution
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"scenarios":["compute-01-linux-vm-web-server"],"duration_hours":1}'

# Verify telemetry exported to Sentinel
# - Log into Azure Portal
# - Open Log Analytics workspace
# - Query: HayMakerTelemetry_CL | take 100
# - Verify events appear with correct schema
```

### Scenario 2: High Volume
```bash
# Test 10K events/sec throughput
# Run load test script (create if needed)
python tests/load/test_siem_export_volume.py

# Verify:
# - All events delivered (99.9%+ SLA)
# - Latency <1 second (p95)
# - No events in dead letter queue
```

### Document Results
Save E2E test results for PR description.

---

## Phase 8: Documentation (Day 16, ~4 hours)

### Update Documentation
- [ ] API documentation for `/api/siem/` endpoints
- [ ] Configuration guide (how to configure connectors)
- [ ] Troubleshooting guide (common issues)
- [ ] Update main README if user-facing

### Update Spec (if deviations)
Document any implementation decisions that differ from original spec.

---

## Phase 9: Create PR (Day 17, ~2 hours)

### Commit Changes
```bash
git add .
git commit -m "feat: Implement SIEM telemetry export (#124)

- Add TelemetryExporter with pluggable connector interface
- Implement SentinelConnector with Data Collector API
- Add EventNormalizer with CEF/JSON/Syslog formats
- Implement retry logic and circuit breaker
- Add dead letter queue for failed events
- Comprehensive test coverage (unit + integration + E2E)

Tested with real Azure Sentinel workspace:
- 10,000+ events/sec throughput ✅
- <1s latency (p95) ✅
- 99.9%+ delivery SLA ✅

Closes #124"

git push origin feat/issue-124-siem-export
```

### Create PR
```bash
gh pr create \
  --title "feat: Implement SIEM Telemetry Export" \
  --body "Closes #124

See implementation spec: specs/SIEM_TELEMETRY_EXPORT.md

## E2E Test Results
[Paste test output showing success]

## Screenshots
[Optional: Screenshots of events in Sentinel]
"
```

---

## Success Criteria Checklist

Before marking complete:

- [ ] Azure Sentinel connector working
- [ ] Splunk HEC connector working (Phase 2)
- [ ] Syslog connector working (Phase 2)
- [ ] CEF/JSON/Syslog formats supported
- [ ] <1s latency in real-time mode (p95)
- [ ] 10K events/sec throughput demonstrated
- [ ] 99.9% delivery SLA achieved
- [ ] Dead letter queue handling failures
- [ ] Unit tests passing (85%+ coverage)
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Security scan clean
- [ ] Code review approved
- [ ] Documentation updated

---

## Common Issues & Solutions

**Issue**: Import errors from telemetry module
**Solution**: Add `__init__.py` files, update imports in `__init__.py`

**Issue**: Sentinel API returns 403 Forbidden
**Solution**: Check workspace shared key is correct, verify Key Vault reference

**Issue**: Events not appearing in Sentinel
**Solution**: Check Log Analytics workspace ID, verify firewall rules, check retention

**Issue**: Performance tests failing (not reaching 10K/sec)
**Solution**: Use batch sending, enable compression, check network latency

---

## Getting Help

- **Comment on Issue #124**: Ask questions
- **Check spec**: Pages 60-65 have troubleshooting guide
- **Review examples**: Look at existing telemetry code in KW framework
- **GitHub Discussions**: Post technical questions

---

## Estimated Timeline

**Optimistic**: 2.5 weeks (experienced developer, no blockers)
**Realistic**: 3 weeks (average developer, normal blockers)
**Pessimistic**: 3.5 weeks (learning curve, unexpected issues)

**Budget accordingly** and communicate if behind schedule.

---

**Full Spec**: [`specs/SIEM_TELEMETRY_EXPORT.md`](../specs/SIEM_TELEMETRY_EXPORT.md)
**Issue**: [#124](https://github.com/rysweet/AzureHayMaker/issues/124)
**Milestone**: [Q1 2026](https://github.com/rysweet/AzureHayMaker/milestone/1)

🚀 **Ready to start? Follow Phase 1 above!**
