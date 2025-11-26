# Windows 365 Cloud PC Provisioning - Implementation Index

## Document Overview

This index provides a complete reference for implementing the W365 Magentic-UI computer use agent deployment system. All modules follow the brick philosophy: single responsibility, clean contracts, production-ready code.

---

## Complete Document Set

### 1. Architecture & Design Documents

| Document | Purpose | Location |
|----------|---------|----------|
| **W365_MAGENTIC_ARCHITECTURE.md** | Complete system architecture, integration points, data flows | `/specs/W365_MAGENTIC_ARCHITECTURE.md` |
| **IMPLEMENTATION_INDEX.md** | This document - implementation roadmap | `/specs/IMPLEMENTATION_INDEX.md` |

### 2. Module Specifications

Each module spec is comprehensive and implementation-ready:

| Module | File | Responsibility | Status |
|--------|------|-----------------|--------|
| **W365 Cloud PC Manager** | `MODULE_W365_MANAGER.md` | Graph API provisioning, policy management, Cloud PC lifecycle | Phase 1 - Core |
| **Magentic-UI Setup Manager** | `MODULE_MAGENTIC_SETUP.md` | Agent installation, configuration, PowerShell remoting | Phase 2 - Setup |
| **Teams Integration Manager** | `MODULE_TEAMS_INTEGRATION.md` | Teams operations, message posting, channel management | Phase 3 - Integration |
| **Browser Automation Tester** | `MODULE_BROWSER_AUTOMATION.md` | Selenium automation, RDP testing, E2E scenarios | Phase 4 - Testing |

---

## Implementation Roadmap

### Phase 1: W365 Cloud PC Manager (1-2 weeks)

**Goal**: Core provisioning via Graph API

**Tasks**:
1. Create `/src/azure_haymaker/provisioning/w365_manager.py`
2. Implement `W365CloudPCManager` class
3. Implement all public methods with retry logic
4. Create data models (CloudPCInfo, ProvisioningResult, etc.)
5. Implement comprehensive logging
6. Write unit tests (90%+ coverage)
7. Integration tests against Graph API beta endpoint

**Files to Create**:
```
/src/azure_haymaker/provisioning/
├── __init__.py
├── models.py          # Data models
├── w365_manager.py    # Main implementation
└── errors.py          # Custom exceptions
```

**Key APIs**:
- `POST /deviceManagement/virtualEndpoint/provisioning_policies`
- `GET /deviceManagement/virtualEndpoint/provisioning_policies`
- `POST /deviceManagement/virtualEndpoint/provisioning_policies/{id}/assignments`
- `GET /deviceManagement/virtualEndpoint/cloudPCs`

**Success Criteria**:
- [ ] All 6 public methods fully implemented
- [ ] Exponential backoff retry working
- [ ] 90-minute provisioning timeout enforced
- [ ] Unit tests passing
- [ ] Integration tests passing (staging tenant)
- [ ] No hardcoded credentials
- [ ] Complete logging with context

---

### Phase 2: Magentic-UI Setup Manager (1-2 weeks)

**Goal**: Automated agent installation on Cloud PCs

**Tasks**:
1. Create `/src/azure_haymaker/provisioning/magentic_ui_setup.py`
2. Implement PSRemoting connection with retry
3. Implement bootstrap (Windows features)
4. Implement package download and signature verification
5. Implement MSI installation
6. Implement configuration and service startup
7. Implement verification health checks
8. Write comprehensive tests

**Files to Create**:
```
/src/azure_haymaker/provisioning/
├── magentic_ui_setup.py    # Main implementation
├── psremoting_client.py    # PSRemoting wrapper
└── package_validator.py    # Signature verification
```

**Key PowerShell Operations**:
```powershell
# Enable features
Enable-WindowsOptionalFeature -FeatureName PowerShell-Remoting -Online -NoRestart

# Transfer files
Copy-Item -Path "agent.msi" -Destination "C:\Temp\" -ToSession $session

# Install
msiexec /i "C:\Temp\agent.msi" /passive /log "C:\Temp\install.log"

# Manage service
New-Service -Name MagenticUIAgent -BinaryPathName "..." -StartupType Automatic
Start-Service -Name MagenticUIAgent
Get-Service -Name MagenticUIAgent
```

**Dependencies**:
- `pypsrp` - PowerShell Remoting
- `cryptography` - Signature verification
- `aiohttp` - Package downloads

**Success Criteria**:
- [ ] Bootstrap completes in <5 minutes
- [ ] Package download with signature verification
- [ ] MSI installation succeeds
- [ ] Configuration files written correctly
- [ ] Service starts and health checks pass
- [ ] Comprehensive error handling
- [ ] Full test coverage

---

### Phase 3: Teams Integration Manager (1 week)

**Goal**: Teams team/channel creation and messaging

**Tasks**:
1. Create `/src/azure_haymaker/provisioning/teams_manager.py`
2. Implement team creation (idempotent)
3. Implement channel creation
4. Implement bulk member addition
5. Implement adaptive card message posting
6. Implement message updates and pinning
7. Write tests

**Files to Create**:
```
/src/azure_haymaker/provisioning/
├── teams_manager.py        # Main implementation
└── adaptive_cards.py       # Card formatting
```

**Key Graph API Operations**:
```python
# Create team
POST /teams
{
  "displayName": "Engineering-Provisioning",
  "description": "...",
  "owners@odata.bind": ["https://graph.microsoft.com/v1.0/users/{id}"]
}

# Create channel
POST /teams/{id}/channels
{
  "displayName": "provisioning-status",
  "description": "...",
  "membershipType": "standard"
}

# Add members
POST /teams/{id}/members
{
  "roles": ["owner"],
  "user@odata.bind": "https://graph.microsoft.com/v1.0/users/{id}"
}

# Post message
POST /teams/{id}/channels/{id}/messages
{
  "body": {"contentType": "html", "content": "..."},
  "attachments": [adaptive_card]
}
```

**Success Criteria**:
- [ ] Team creation idempotent
- [ ] All channels created successfully
- [ ] Bulk member addition with batching
- [ ] Adaptive cards rendered correctly
- [ ] Message updates working
- [ ] Tests passing
- [ ] Comprehensive error handling

---

### Phase 4: Browser Automation Tester (2 weeks)

**Goal**: E2E testing of provisioned infrastructure

**Tasks**:
1. Create `/src/azure_haymaker/testing/browser_automation.py`
2. Implement RDP connection
3. Implement Selenium WebDriver setup
4. Implement all test scenario methods
5. Implement screenshot capture and reporting
6. Implement JSON and HTML report generation
7. Write comprehensive tests

**Files to Create**:
```
/src/azure_haymaker/testing/
├── __init__.py
├── browser_automation.py  # Main implementation
├── test_scenarios.py      # Scenario definitions
├── report_generator.py    # Report formatting
└── rdp_client.py         # RDP connection
```

**Test Scenarios**:
1. M365 Portal Access
2. Teams Chat
3. Email Access (Outlook)
4. SharePoint Sync
5. Agent UI Verification

**Dependencies**:
- `selenium` - Browser automation
- `pyrdp` - RDP client
- `Pillow` - Screenshots
- `jinja2` - HTML reporting

**Success Criteria**:
- [ ] RDP connection working
- [ ] Selenium WebDriver controlling browser
- [ ] All 5 test scenarios implemented
- [ ] Screenshots capturing correctly
- [ ] Reports generating (JSON + HTML)
- [ ] Performance metrics collected
- [ ] Tests passing
- [ ] Error handling robust

---

### Phase 5: Provisioning Orchestrator (1 week)

**Goal**: Coordinate all components

**Tasks**:
1. Create `/src/azure_haymaker/provisioning/orchestrator.py`
2. Implement validation checks
3. Implement provisioning workflow
4. Implement Teams integration
5. Implement E2E testing
6. Implement error handling and rollback
7. Implement reporting and cleanup

**Files to Create**:
```
/src/azure_haymaker/provisioning/
├── orchestrator.py        # Main implementation
├── manifest.py            # Deployment manifest
└── cleanup_manager.py     # Cleanup/rollback
```

**Workflow**:
1. Validate prerequisites
2. Create W365 policies
3. Provision Cloud PCs (parallel)
4. Bootstrap Cloud PCs (parallel)
5. Install Magentic-UI (parallel)
6. Configure agents (parallel)
7. Verify agents ready (parallel)
8. Create Teams team/channels (parallel)
9. Run E2E tests (parallel)
10. Generate reports
11. Publish to Service Bus
12. Store manifest in Storage

**Success Criteria**:
- [ ] Validation catches all issues
- [ ] Provisioning workflow correct
- [ ] Parallel operations working
- [ ] Error handling with rollback
- [ ] Reports comprehensive
- [ ] Manifest accurate
- [ ] Tests passing

---

### Phase 6: Integration with KnowledgeWorkerAgent (1 week)

**Goal**: Connect provisioning to existing worker framework

**Tasks**:
1. Update `KnowledgeWorkerAgent` to support cloud_pc endpoint
2. Update `WorkerIdentity` model if needed
3. Create integration tests
4. Update documentation

**Files to Modify**:
- `/src/azure_haymaker/knowledge_worker/agent.py` - Add cloud_pc endpoint support
- `/src/azure_haymaker/knowledge_worker/models/worker.py` - Update WorkerIdentity if needed
- `/src/azure_haymaker/knowledge_worker/endpoints/cloud_pc.py` - Enhance existing implementation

**Success Criteria**:
- [ ] Agent can work with cloud_pc endpoints
- [ ] Endpoint type correctly detected
- [ ] Agent activities work on Cloud PC
- [ ] Integration tests passing

---

### Phase 7: Full E2E Testing & Validation (1 week)

**Goal**: Production readiness

**Tasks**:
1. Integration testing across all modules
2. Performance testing (provisioning throughput)
3. Failure scenario testing
4. Documentation and runbooks
5. Security review
6. Cost analysis

**Success Criteria**:
- [ ] All integration tests passing
- [ ] Performance acceptable
- [ ] Failure scenarios handled
- [ ] Documentation complete
- [ ] Security review passed
- [ ] Cost estimates accurate

---

## File Structure

### Final Directory Layout

```
/src/azure_haymaker/
├── provisioning/
│   ├── __init__.py
│   ├── models.py                    # All data models
│   ├── errors.py                    # Custom exceptions
│   ├── w365_manager.py              # Phase 1
│   ├── magentic_ui_setup.py         # Phase 2
│   ├── psremoting_client.py         # Phase 2 helper
│   ├── package_validator.py         # Phase 2 helper
│   ├── teams_manager.py             # Phase 3
│   ├── adaptive_cards.py            # Phase 3 helper
│   ├── orchestrator.py              # Phase 5
│   ├── manifest.py                  # Phase 5 helper
│   └── cleanup_manager.py           # Phase 5 helper
├── testing/
│   ├── __init__.py
│   ├── browser_automation.py        # Phase 4
│   ├── test_scenarios.py            # Phase 4 helper
│   ├── report_generator.py          # Phase 4 helper
│   └── rdp_client.py                # Phase 4 helper
├── knowledge_worker/                # Existing
│   ├── agent.py                     # Phase 6 - update
│   ├── endpoints/
│   │   └── cloud_pc.py              # Phase 6 - enhance
│   └── models/
│       └── worker.py                # Phase 6 - update

/tests/
├── test_w365_manager.py             # Phase 1
├── test_magentic_setup.py           # Phase 2
├── test_teams_manager.py            # Phase 3
├── test_browser_automation.py       # Phase 4
├── test_orchestrator.py             # Phase 5
└── integration/
    └── test_e2e_provisioning.py     # Phase 7

/specs/
├── W365_MAGENTIC_ARCHITECTURE.md    # Architecture
├── MODULE_W365_MANAGER.md           # Phase 1 spec
├── MODULE_MAGENTIC_SETUP.md         # Phase 2 spec
├── MODULE_TEAMS_INTEGRATION.md      # Phase 3 spec
├── MODULE_BROWSER_AUTOMATION.md     # Phase 4 spec
└── IMPLEMENTATION_INDEX.md          # This file
```

---

## Key Implementation Decisions

### 1. Async/Await Throughout

All I/O operations are async for scalability:
- Graph API calls: `async def`
- PowerShell remoting: `async def`
- Browser control: `async def`
- Testing: Uses `pytest-asyncio`

### 2. Retry Logic Strategy

Exponential backoff for transient errors:
```
Delay: 2s, 4s, 8s, 16s, 32s (max)
Jitter: ±10%
Max retries: 3-5 depending on operation
```

### 3. Logging Context

Every operation logs with context:
```python
logger.info(
    f"Provisioning Cloud PC: {worker.worker_id} (run: {self.run_id})",
    extra={
        "run_id": self.run_id,
        "worker_id": worker.worker_id,
        "operation": "provision_cloud_pc",
    }
)
```

### 4. Error Isolation

One worker failure doesn't stop provisioning of others. Each worker has independent result tracking.

### 5. Idempotency

All operations should be safe to retry:
- Policy creation: Check existing first
- Team creation: Query by name
- Channel creation: Check if exists
- Member addition: Skip if already member

### 6. Timeouts Enforced

- Cloud PC provisioning: 90 minutes max
- Agent setup: 30 minutes max
- Browser test: 5 minutes per scenario
- Overall orchestration: Configurable deadline

### 7. No Hardcoded Secrets

All credentials from environment or Key Vault:
```python
# Good
password = os.getenv("ADMIN_PASSWORD")  # or from Key Vault

# Never
password = "MySecretPassword123"
```

---

## Testing Requirements Summary

### Unit Test Coverage Targets
- W365 Manager: 90%+
- Magentic Setup: 90%+
- Teams Manager: 85%+
- Browser Automation: 85%+
- Orchestrator: 85%+

### Integration Test Requirements
- Test against real Graph API (staging)
- Test against Cloud PC (staging)
- Test against Teams (production safe)
- Full end-to-end workflow

### Performance Benchmarks
- Single Cloud PC provisioning: <90 minutes
- 5 concurrent Cloud PCs: ~90 minutes
- Agent setup per Cloud PC: <30 minutes
- E2E test suite: <10 minutes
- Overall 25-worker provisioning: <2 hours

---

## Configuration Management

### Environment Variables Required

```bash
# Azure Auth
AZURE_TENANT_ID=your-tenant-id
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_CLIENT_ID=your-app-id
AZURE_CLIENT_SECRET=your-secret

# Graph API
GRAPH_API_ENDPOINT=https://graph.microsoft.com/v1.0

# W365 Provisioning
W365_POLICY_NAME=HayMaker-Policy
W365_CLOUD_PC_SKU=CPC_S_2C_4GB_64GB
W365_IMAGE_ID=MicrosoftWindowsDesktop_windows-ent-cpc_win11-22h2-ent-cpc-m365

# Magentic-UI
MAGENTIC_PACKAGE_URL=https://releases.magentic.io/v1.0.0/agent.msi
MAGENTIC_VERSION=1.0.0

# Teams
TEAMS_TEAM_NAME=Cloud-PC-Deployment
TEAMS_OWNER_UPN=admin@tenant.onmicrosoft.com

# Logging
LOG_LEVEL=INFO

# Storage
STORAGE_ACCOUNT_NAME=your-storage-account
STORAGE_ACCOUNT_KEY=your-storage-key
```

### Key Vault References (Recommended)

```yaml
KeyVault Secrets:
  admin-password: Cloud PC admin password
  agent-signing-cert: Package signing certificate
  service-principal-secret: Graph API service principal secret
```

---

## Deployment Checklist

Before deploying to production:

- [ ] All dependencies installed and pinned
- [ ] Environment variables configured
- [ ] Key Vault secrets populated
- [ ] Graph API permissions granted
- [ ] Test Cloud PC available
- [ ] Service Bus topic created
- [ ] Storage account configured
- [ ] Logging configured and tested
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Load tests successful
- [ ] Security review completed
- [ ] Documentation reviewed
- [ ] Runbooks tested
- [ ] Monitoring and alerts set up

---

## Common Issues & Troubleshooting

### Cloud PC Provisioning Times Out

**Symptoms**: `ProvisioningTimeout` after 90 minutes

**Causes**:
- Insufficient W365 licenses
- Subscription quota exhausted
- Image or SKU invalid
- Network connectivity issues

**Resolution**:
- Check Graph API quota usage: `GET /tenantManagement/quotas`
- Verify licenses: `GET /deviceManagement/deviceLicenses`
- Test connectivity: Verify Cloud PC image and SKU valid
- Increase timeout if provisioning is actually proceeding

### Agent Installation Fails

**Symptoms**: `InstallError` during MSI installation

**Causes**:
- Cloud PC not ready (still provisioning)
- PSRemoting not enabled
- Insufficient disk space
- Installer signature verification failed
- Network download timeout

**Resolution**:
- Verify Cloud PC ready: `get_cloud_pc()` returns status="provisioned"
- Test PSRemoting connection separately
- Check disk space on Cloud PC
- Verify package signature manually
- Check package URL accessibility

### Teams Messages Not Posting

**Symptoms**: `MessagePostError` or messages don't appear

**Causes**:
- Channel not found
- Permission denied
- Message too long (>28KB)
- Rate limit exceeded

**Resolution**:
- Verify channel created: `create_channel()`
- Check Graph API permissions
- Split message if too long
- Implement exponential backoff for rate limits

### Browser Automation Hangs

**Symptoms**: Tests hang on element wait

**Causes**:
- Element selector wrong
- Page not loading
- Element appears after timeout
- RDP connection lost

**Resolution**:
- Verify selector on test page
- Check page loads (check for navigation errors)
- Increase timeout if needed
- Verify RDP connection still active

---

## Cost Estimation

### Per-Worker Cost (Approximate)

| Component | Cost | Duration |
|-----------|------|----------|
| Cloud PC (2vCPU, 4GB, 64GB) | $30-50 | 1 month |
| Agent software | Included | N/A |
| Testing infrastructure | $2-5 | Per test |
| Storage (logs/reports) | $0.10-0.50 | Per deployment |
| **Total per worker** | **$32-56/month** | If left running |

### Optimization Strategies

1. **Delete Cloud PCs After Testing**: Reduce cost to ~$2-5 per deployment
2. **Schedule Provisioning**: Run during off-peak hours
3. **Batch Provisioning**: 5-10 simultaneous workers
4. **Use Dev/Test Subscription**: May have different pricing

### Example: 25-Worker Test Deployment

```
Cloud PCs (1 day): 25 × $2 = $50
Magentic-UI software: Included
Teams operations: Minimal (<$1)
Storage: $0.50-1.00
Testing: $2-5
Total: ~$55-60 for full deployment test
```

---

## Security Considerations

### Data Protection

- All credentials stored in Key Vault
- No secrets in logs or reports
- Connections use TLS/HTTPS
- Cloud PC data encrypted at rest

### Access Control

- Graph API permissions: Least privilege principle
- Service principal: Separate per environment (dev/staging/prod)
- Cloud PC admin account: Limited permissions, unique password
- Teams team: Access restricted to relevant users

### Audit & Compliance

- All API calls logged with user context
- Deployment manifests retained for audit
- Cloud PC activity logged
- Access to Key Vault monitored

---

## Monitoring & Observability

### Key Metrics to Track

```python
# Provisioning metrics
metrics = {
    "provisioning_success_rate": 0.95,  # 95% success
    "provisioning_time_p50": 45,        # 50th percentile in minutes
    "provisioning_time_p95": 85,        # 95th percentile in minutes
    "cloud_pc_provisioning_time_avg": 35,
    "agent_setup_time_avg": 8,
    "e2e_test_pass_rate": 0.90,
    "error_rate": 0.05,
}
```

### Dashboards

Create Azure Monitor dashboard showing:
- Provisioning success/failure rate
- Duration trends
- Error breakdown
- Resource utilization (Cloud PC SKUs, quota usage)
- Cost tracking

### Alerts

Set up alerts for:
- Provisioning failure rate >10%
- Provisioning time >120 minutes
- E2E test failures
- Cloud PC quota exhaustion
- Storage account quota high
- Errors in provisioning logs

---

## Documentation

Create the following documentation:

- [ ] **README.md** - Quick start guide
- [ ] **SETUP.md** - Detailed setup instructions
- [ ] **API.md** - API reference for each module
- [ ] **TROUBLESHOOTING.md** - Common issues and solutions
- [ ] **RUNBOOKS.md** - Operational runbooks
- [ ] **ARCHITECTURE.md** - System architecture details
- [ ] **COST_ANALYSIS.md** - Cost breakdown and optimization

---

## Success Criteria - Final Checklist

### Code Quality
- [ ] All code follows Python style guide (PEP 8)
- [ ] Type hints complete and validated (mypy/pyright)
- [ ] Linting passes (ruff, pylint)
- [ ] No security issues (bandit)
- [ ] Pre-commit hooks configured

### Testing
- [ ] Unit test coverage >90% for all modules
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Performance benchmarks met
- [ ] All failure scenarios tested

### Documentation
- [ ] Module specifications complete
- [ ] API documentation complete
- [ ] Runbooks written
- [ ] Troubleshooting guide written
- [ ] Architecture diagrams created

### Deployment
- [ ] Staging deployment successful
- [ ] Monitoring and alerts configured
- [ ] Cost tracking implemented
- [ ] Security review completed
- [ ] Compliance requirements met

---

## Next Steps

1. **Review Architecture**: Read `W365_MAGENTIC_ARCHITECTURE.md` first
2. **Start Phase 1**: Begin implementing `W365CloudPCManager`
3. **Write Tests First**: TDD approach for reliability
4. **Iterate Quickly**: Each phase 1-2 weeks
5. **Integration Focus**: After Phase 4, focus on integration
6. **Production Readiness**: Phase 7 validation critical

---

## Questions & Support

- Check module specifications for implementation details
- Review existing `cloud_pc.py` for reference implementations
- Consult Graph API documentation for endpoint details
- Test against staging Cloud PC first
- Use comprehensive logging for debugging

---

**Last Updated**: 2025-01-15
**Version**: 1.0.0
**Status**: Implementation Ready
