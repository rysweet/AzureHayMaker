# Knowledge Worker Real M365 Integration Specification

**Version**: 1.0
**Status**: Requirements Specification
**Created**: 2025-11-26
**Author**: PromptWriter Agent

---

## Executive Summary

This specification defines the requirements for connecting Knowledge Worker (KW) agents to real Microsoft 365 operations. Currently, the KW framework has complete M365 operation classes (`EmailOperations`, `CalendarOperations`, `TeamsOperations`, `DocumentOperations`) but the orchestrator and agent run in LOCAL SIMULATION mode only.

The goal is to bridge this gap so that KW agents can perform actual M365 operations using the existing infrastructure created by `haymaker kw init` and validated by `haymaker kw e2e-test`.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Desired End State](#2-desired-end-state)
3. [Gap Analysis](#3-gap-analysis)
4. [Detailed Requirements](#4-detailed-requirements)
5. [Acceptance Criteria](#5-acceptance-criteria)
6. [Technical Design Constraints](#6-technical-design-constraints)
7. [Success Criteria for E2E Validation](#7-success-criteria-for-e2e-validation)
8. [Risk Assessment](#8-risk-assessment)
9. [Implementation Phases](#9-implementation-phases)

---

## 1. Current State Analysis

### 1.1 What Works (PRODUCTION READY)

| Component | Location | Status | Description |
|-----------|----------|--------|-------------|
| `haymaker kw init` | `cli/src/haymaker_cli/kw/commands.py:79` | WORKING | Creates Azure Entra app registration with Graph API permissions |
| `haymaker kw e2e-test` | `cli/src/haymaker_cli/kw/commands.py:712` | WORKING | Validates Graph API connectivity - sends real emails, creates calendar events |
| `EmailOperations` | `src/azure_haymaker/knowledge_worker/operations/email.py` | IMPLEMENTED | Full Graph API email operations (send, read, reply, forward, organize) |
| `CalendarOperations` | `src/azure_haymaker/knowledge_worker/operations/calendar.py` | IMPLEMENTED | Full Graph API calendar operations (create event, respond, update, cancel, list) |
| `TeamsOperations` | `src/azure_haymaker/knowledge_worker/operations/teams.py` | IMPLEMENTED | Full Graph API Teams operations (channel post, chat, reply, react) |
| `DocumentOperations` | `src/azure_haymaker/knowledge_worker/operations/documents.py` | IMPLEMENTED | Full Graph API document operations (create, upload, share, download) |
| `CommunicationValidator` | `src/azure_haymaker/knowledge_worker/operations/validators.py` | IMPLEMENTED | Internal-only recipient validation |
| `M365OperationBase` | `src/azure_haymaker/knowledge_worker/operations/base.py` | IMPLEMENTED | Rate limiting, logging, validation base class |
| `WorkerIdentity` | `src/azure_haymaker/knowledge_worker/models/worker.py` | IMPLEMENTED | Full worker identity model with `entra_object_id` field |
| `KnowledgeWorkerConfig` | `src/azure_haymaker/knowledge_worker/agent.py` | IMPLEMENTED | Has `tenant_domain`, `m365_app_id`, `m365_cert_thumbprint` fields |

### 1.2 What Does NOT Work (SIMULATION ONLY)

| Component | Location | Issue | Impact |
|-----------|----------|-------|--------|
| `KnowledgeWorkerOrchestrator` | `src/azure_haymaker/knowledge_worker/orchestrator.py` | Lines 9-15 explicitly state "LOCAL SIMULATION only" | Does not provision real Entra users or connect to M365 |
| `_run_worker_simulation()` | `orchestrator.py:421-451` | Contains `await asyncio.sleep(1)` instead of real M365 operations | Workers never actually perform M365 activities |
| `KnowledgeWorkerAgent.on_start()` | `agent.py:226-253` | M365 client initialization skipped if no `m365_app_id` | No Graph API client created |
| `_load_allowed_recipients()` | `agent.py:350-366` | Returns empty set, no actual Entra query | No recipient validation against real users |
| `_phase_setup()` | `orchestrator.py:319-334` | Only logs, no actual infrastructure creation | Transport rules, groups not created |
| `_phase_provision()` | `orchestrator.py:336-392` | Creates in-memory workers only | No Entra users provisioned |
| `_phase_execute()` | `orchestrator.py:394-419` | Calls simulation instead of real M365 | No actual M365 activities performed |

### 1.3 Current Flow (Simulation)

```
haymaker kw deploy
    |
    v
KnowledgeWorkerOrchestrator.start_deployment()
    |
    +-- _phase_setup() -> Logs only (NO security groups, NO transport rules)
    |
    +-- _phase_provision() -> In-memory workers (NO Entra users)
    |
    +-- _phase_execute()
            |
            +-- _run_worker_simulation()
                    |
                    +-- asyncio.sleep(1) -> DONE (NO M365 operations)
```

---

## 2. Desired End State

### 2.1 Target Architecture

```
haymaker kw deploy --real-m365
    |
    v
KnowledgeWorkerOrchestrator.start_deployment()
    |
    +-- _phase_setup()
    |       |
    |       +-- Create security group for all workers
    |       +-- Create transport rules blocking external email
    |       +-- Verify app registration permissions
    |
    +-- _phase_provision()
    |       |
    |       +-- Create Entra users via Graph API
    |       +-- Add users to security groups
    |       +-- Populate allowed_recipients from Entra
    |
    +-- _phase_execute()
            |
            +-- For each worker:
                    |
                    +-- KnowledgeWorkerAgent.on_start()
                    |       +-- Initialize GraphServiceClient
                    |       +-- Create EmailOperations, TeamsOperations, etc.
                    |
                    +-- ActivityScheduler.run()
                            |
                            +-- EmailOperations.send_email() -> REAL EMAIL
                            +-- TeamsOperations.post_to_channel() -> REAL TEAMS
                            +-- CalendarOperations.create_event() -> REAL CALENDAR
                            +-- DocumentOperations.create_document() -> REAL ONEDRIVE
```

### 2.2 Capabilities to Deliver

1. **Real Entra User Provisioning**: Workers have actual M365 identities
2. **Real Email Operations**: Send/receive/organize emails via Graph API
3. **Real Teams Operations**: Post to channels, send DMs via Graph API
4. **Real Calendar Operations**: Create events with attendees via Graph API
5. **Real Document Operations**: Create/share documents in OneDrive via Graph API
6. **Safety Controls**: Transport rules + agent validation ensure internal-only comms
7. **Full Cleanup**: All provisioned resources deletable via `haymaker kw cleanup`

---

## 3. Gap Analysis

### 3.1 Missing Components

| Gap | Current | Needed | Priority |
|-----|---------|--------|----------|
| Graph API Client Factory | Agent tries to create `GraphServiceClient` but lacks proper credential setup | Factory method that creates authenticated client from config | HIGH |
| Entra User Creation | Not implemented in orchestrator | Integration with `EntraUserManager` | HIGH |
| M365 Client Injection | Operations classes require `M365Client` but none provided | Dependency injection or factory pattern | HIGH |
| Allowed Recipients Loading | Returns empty set | Query Entra for all workers in run | MEDIUM |
| Activity Scheduler | Not connected to operations | Create `ActivityScheduler` that uses operations | HIGH |
| Transport Rule Management | Not implemented | Integration with `TransportRuleManager` | MEDIUM |
| Credential Configuration | Uses cert path `/secrets/{thumbprint}.pem` | Support env vars for client secret or managed identity | HIGH |

### 3.2 Code Changes Required

#### 3.2.1 `KnowledgeWorkerAgent` (agent.py)

**Current Issue**: `_initialize_m365_client()` (lines 299-336) tries certificate auth but:
- Hardcodes cert path to `/secrets/{thumbprint}.pem`
- Does not support client secret authentication (used by `kw init`)
- Never actually called because `m365_app_id` is often empty

**Required Changes**:
1. Support client secret authentication (matching `e2e-test` implementation)
2. Support environment variable configuration (`KW_APP_ID`, `KW_CLIENT_SECRET`, `KW_TENANT_ID`)
3. Create operations instances (`EmailOperations`, etc.) with the initialized client

#### 3.2.2 `KnowledgeWorkerOrchestrator` (orchestrator.py)

**Current Issue**: All phases are simulation stubs

**Required Changes**:
1. `_phase_setup()`: Create security group, transport rules
2. `_phase_provision()`: Create real Entra users, populate identities
3. `_phase_execute()`: Call `worker.on_start()`, run `ActivityScheduler`
4. `cleanup_deployment()`: Delete all created resources

#### 3.2.3 New Component: `M365ClientFactory`

**Purpose**: Create authenticated Graph API clients from configuration

```python
class M365ClientFactory:
    @staticmethod
    def create_from_config(config: KnowledgeWorkerConfig) -> GraphServiceClient:
        """Create Graph client from worker config or environment."""
        # Support multiple auth methods:
        # 1. Environment variables (KW_APP_ID, KW_CLIENT_SECRET, KW_TENANT_ID)
        # 2. Certificate auth (m365_cert_thumbprint)
        # 3. Managed identity (for container apps)
```

#### 3.2.4 New Component: `ActivityScheduler` Integration

**Purpose**: Schedule and execute M365 operations according to persona patterns

The architecture document (ARCHITECTURE.md, lines 1983-2080) already defines this but it needs to be connected to the real operations classes.

---

## 4. Detailed Requirements

### 4.1 Functional Requirements

#### FR-001: Client Secret Authentication Support
**Description**: The system MUST support client secret authentication matching the `e2e-test` implementation.

**Rationale**: `haymaker kw init` creates an app registration with a client secret. Workers must be able to authenticate using this secret.

**Implementation**:
```python
from azure.identity import ClientSecretCredential
credential = ClientSecretCredential(
    tenant_id=os.environ.get("KW_TENANT_ID"),
    client_id=os.environ.get("KW_APP_ID"),
    client_secret=os.environ.get("KW_CLIENT_SECRET"),
)
client = GraphServiceClient(credential)
```

#### FR-002: Real Email Operations
**Description**: Workers MUST be able to send real emails to other workers within the tenant.

**Acceptance Criteria**:
- Email appears in recipient's inbox within 60 seconds
- Sender shown as worker's display name
- Subject and body match parameters
- Email is saved to sender's Sent Items

**Existing Code**: `EmailOperations.send_email()` in `operations/email.py:87-177`

#### FR-003: Real Calendar Event Creation
**Description**: Workers MUST be able to create calendar events with attendees.

**Acceptance Criteria**:
- Event appears on organizer's calendar
- Invitation sent to attendees
- Online meeting link created if `is_online=True`
- Event ID returned for tracking

**Existing Code**: `CalendarOperations.create_event()` in `operations/calendar.py:92-185`

#### FR-004: Real Teams Messaging
**Description**: Workers MUST be able to post to Teams channels and send direct messages.

**Acceptance Criteria**:
- Channel posts visible in specified channel
- Direct messages delivered to recipient's chat
- Message content matches parameters

**Existing Code**: `TeamsOperations.post_to_channel()`, `send_chat_message()` in `operations/teams.py`

#### FR-005: Real Document Operations
**Description**: Workers MUST be able to create and share documents in OneDrive.

**Acceptance Criteria**:
- Document created in specified folder
- Document accessible via OneDrive
- Sharing invitations sent to specified recipients

**Existing Code**: `DocumentOperations.create_document()`, `share_with_team()` in `operations/documents.py`

#### FR-006: Internal-Only Communication Enforcement
**Description**: All communications MUST be validated to ensure internal-only recipients.

**Acceptance Criteria**:
- External email addresses blocked at agent level
- External recipients filtered from CC/BCC
- Warning logged for any blocked external attempts
- Transport rules provide server-side backup

**Existing Code**: `CommunicationValidator` in `operations/validators.py`

#### FR-007: Worker Identity from Entra
**Description**: Worker `entra_object_id` MUST be populated from actual Entra user creation.

**Rationale**: All Graph API operations use `entra_object_id` to identify the user context.

**Existing Code**: `EntraUserManager` in `identity/user_manager.py` (needs integration)

### 4.2 Non-Functional Requirements

#### NFR-001: Rate Limiting
**Description**: M365 operations MUST implement rate limiting to avoid Graph API throttling.

**Current Implementation**: `M365OperationBase._rate_limit()` pauses every 100 operations

**Enhancement**: Implement exponential backoff on 429 responses

#### NFR-002: Error Handling
**Description**: All M365 operations MUST handle Graph API errors gracefully.

**Requirements**:
- Log detailed error information
- Retry transient errors (429, 503)
- Report failures without crashing worker
- Continue operation on non-critical failures

#### NFR-003: Observability
**Description**: All M365 operations MUST be logged for debugging and monitoring.

**Current Implementation**: `M365OperationBase._log_operation()` and `_log_error()` methods

#### NFR-004: Configuration Flexibility
**Description**: The system MUST support multiple authentication methods.

**Methods to Support**:
1. Client Secret via environment variables (primary for local development)
2. Certificate authentication (for container apps)
3. Managed Identity (for Azure-hosted containers)

---

## 5. Acceptance Criteria

### 5.1 End-to-End Test Scenarios

#### AC-001: Single Worker Email Test
```gherkin
Given a deployed KW worker with valid M365 credentials
When the worker sends an email to another internal user
Then the email MUST appear in the recipient's inbox
And the email MUST be saved to the sender's Sent Items
And the operation MUST complete within 60 seconds
```

#### AC-002: Multi-Worker Communication Test
```gherkin
Given 3 deployed KW workers in the same team
When Worker A sends an email to Workers B and C
Then both B and C MUST receive the email
And only internal recipients are allowed
```

#### AC-003: Calendar Event with Attendees
```gherkin
Given 2 deployed KW workers
When Worker A creates a meeting inviting Worker B
Then the event MUST appear on Worker A's calendar
And Worker B MUST receive a meeting invitation
And the event MUST include a Teams meeting link
```

#### AC-004: Teams Channel Post
```gherkin
Given a deployed KW worker with Teams team membership
When the worker posts to a channel
Then the message MUST appear in the channel
And the worker's display name MUST be shown as author
```

#### AC-005: Document Creation and Sharing
```gherkin
Given 2 deployed KW workers
When Worker A creates a document and shares with Worker B
Then the document MUST exist in Worker A's OneDrive
And Worker B MUST receive a sharing notification
And Worker B MUST be able to access the document
```

#### AC-006: External Recipient Blocking
```gherkin
Given a deployed KW worker
When the worker attempts to email an external address
Then the email MUST be blocked at the agent level
And a warning MUST be logged
And no email MUST be sent
```

### 5.2 CLI Validation Commands

```bash
# Deploy with real M365 (new flag)
haymaker kw deploy --name test-real --workers 3 --real-m365

# Verify workers can communicate
haymaker kw verify-comms --run-id <run_id>

# Check activity logs
haymaker kw logs --run-id <run_id> --worker <worker_id>

# Cleanup all resources
haymaker kw cleanup --run-id <run_id>
```

---

## 6. Technical Design Constraints

### 6.1 Authentication Architecture

The solution MUST use the same authentication approach as `e2e-test`:

```python
# From cli/src/haymaker_cli/kw/commands.py:796-801
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

credential = ClientSecretCredential(
    tenant_id=tenant_id,
    client_id=app_id,
    client_secret=client_secret,
)
client = GraphServiceClient(credential)
```

### 6.2 Existing Class Contracts

All operations classes expect an `M365Client` with a `.graph` property:

```python
# From operations/base.py:21-31
class M365Client(Protocol):
    @property
    def graph(self) -> Any:
        """Access to Microsoft Graph client."""
        ...
```

The `GraphServiceClient` from `msgraph-sdk` satisfies this contract.

### 6.3 Worker Identity Requirements

Operations classes use `self.worker.entra_object_id` for all API calls:

```python
# From email.py:154-156
result = await self.client.graph.users.by_user_id(
    self.worker.entra_object_id
).send_mail.post(...)
```

Therefore, `WorkerIdentity.entra_object_id` MUST be populated before operations can execute.

### 6.4 Recipient Validation Contract

The `CommunicationValidator` validates against:
1. `tenant_domain` - domain suffix match
2. `allowed_upns` - explicit allowlist

Both MUST be configured for proper internal-only enforcement.

---

## 7. Success Criteria for E2E Validation

### 7.1 Minimum Viable Validation

A successful implementation MUST pass all these checks:

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Email send | `haymaker kw e2e-test --test-email --sender user1 --recipient user2` | PASS - Email sent |
| Calendar create | `haymaker kw e2e-test --test-calendar --sender user1` | PASS - Event created |
| User list | `haymaker kw e2e-test --test-groups` | PASS - Groups listed |
| Full deployment | `haymaker kw deploy --real-m365 --workers 3` | Workers created, activities logged |
| Activity verification | `haymaker kw verify-comms --run-id <id>` | All workers sent at least 1 email |
| Cleanup | `haymaker kw cleanup --run-id <id>` | All resources deleted |

### 7.2 Extended Validation

For production readiness:

| Check | Description | Metric |
|-------|-------------|--------|
| 10-worker test | Deploy 10 workers for 1 hour | >90% activities succeed |
| 50-worker test | Deploy 50 workers for 4 hours | >85% activities succeed |
| Rate limiting | Run at maximum frequency | No 429 errors after backoff |
| Cleanup verification | List orphaned resources | 0 orphaned resources |

---

## 8. Risk Assessment

### 8.1 Security Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| External email leak | HIGH - Compliance violation | 3-layer defense: Transport rules + Agent validation + Allowed list |
| Credential exposure | HIGH - Account compromise | Environment variables, Key Vault, no hardcoded secrets |
| Orphaned resources | MEDIUM - Cost/security | Tag-based cleanup, orphan detection |

### 8.2 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Graph API rate limiting | MEDIUM - Activity failures | Exponential backoff, rate limiting |
| Authentication failures | HIGH - Workers non-functional | Validate credentials before deployment |
| Teams permission issues | MEDIUM - Teams features broken | Pre-flight permission check |

### 8.3 Complexity Assessment

**Overall Complexity**: MEDIUM-HIGH

- Existing operations code is complete and well-structured
- Main work is integration/wiring, not new feature development
- Authentication setup already proven by `e2e-test`
- Risk areas: Entra user provisioning at scale, Teams operations permissions

**Estimated Effort**: 3-5 days for core integration, 2-3 days for testing/hardening

---

## 9. Implementation Phases

### Phase 1: Client Factory & Authentication (Day 1)

**Deliverables**:
1. `M365ClientFactory` class supporting client secret auth
2. Environment variable configuration (`KW_APP_ID`, `KW_CLIENT_SECRET`, `KW_TENANT_ID`)
3. Update `KnowledgeWorkerAgent._initialize_m365_client()` to use factory
4. Unit tests for authentication

**Validation**: Agent can create authenticated `GraphServiceClient`

### Phase 2: Operations Integration (Day 2)

**Deliverables**:
1. Create operations instances in `KnowledgeWorkerAgent.on_start()`
2. Expose operations via agent properties (`agent.email_ops`, etc.)
3. Test individual operations against real M365

**Validation**: `agent.email_ops.send_email()` sends real email

### Phase 3: Orchestrator Integration (Days 3-4)

**Deliverables**:
1. Update `_phase_setup()` to create security group
2. Update `_phase_provision()` to create Entra users (or use existing)
3. Update `_phase_execute()` to run real activity scheduler
4. Add `--real-m365` flag to `haymaker kw deploy`

**Validation**: `haymaker kw deploy --real-m365 --workers 3` creates workers and sends emails

### Phase 4: Activity Scheduler (Day 4)

**Deliverables**:
1. Create `ActivityScheduler` class
2. Integrate with persona-based activity patterns
3. Connect to operations classes

**Validation**: Workers perform varied activities over time according to persona

### Phase 5: Cleanup & Hardening (Day 5)

**Deliverables**:
1. Full cleanup implementation in `cleanup_deployment()`
2. Error handling and retry logic
3. Observability improvements
4. Documentation updates

**Validation**: Full E2E test suite passes

---

## Appendix A: Key File Locations

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `src/azure_haymaker/knowledge_worker/agent.py` | Worker agent class | 299-336 (M365 init) |
| `src/azure_haymaker/knowledge_worker/orchestrator.py` | Deployment orchestration | 319-451 (phases) |
| `src/azure_haymaker/knowledge_worker/operations/email.py` | Email operations | 87-177 (send) |
| `src/azure_haymaker/knowledge_worker/operations/calendar.py` | Calendar operations | 92-185 (create event) |
| `src/azure_haymaker/knowledge_worker/operations/teams.py` | Teams operations | 88-169 (channel post) |
| `src/azure_haymaker/knowledge_worker/operations/documents.py` | Document operations | 90-127 (create) |
| `src/azure_haymaker/knowledge_worker/operations/base.py` | Base operation class | 60-75 (init), 136-151 (rate limit) |
| `src/azure_haymaker/knowledge_worker/identity/user_manager.py` | Entra user management | Entire file |
| `cli/src/haymaker_cli/kw/commands.py` | CLI commands | 712-943 (e2e-test) |

---

## Appendix B: Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `KW_APP_ID` | Azure app (client) ID from `kw init` | Yes |
| `KW_CLIENT_SECRET` | Client secret from `kw init` | Yes |
| `KW_TENANT_ID` | Azure tenant ID | Yes |
| `KW_TENANT_DOMAIN` | Tenant domain (e.g., `contoso.onmicrosoft.com`) | Yes |

---

## Appendix C: Sequence Diagram

```
User                  CLI                    Orchestrator              Agent                 Graph API
  |                    |                          |                      |                       |
  |-- kw deploy ------>|                          |                      |                       |
  |                    |-- create_deployment() -->|                      |                       |
  |                    |                          |-- _phase_setup() --->|                       |
  |                    |                          |         |            |                       |
  |                    |                          |         |-- Create security group ---------->|
  |                    |                          |         |<------------------------------- OK-|
  |                    |                          |         |                                    |
  |                    |                          |-- _phase_provision() -->|                   |
  |                    |                          |         |               |                   |
  |                    |                          |         |-- Create Entra users ------------>|
  |                    |                          |         |<---------------------- user_ids --|
  |                    |                          |         |                                   |
  |                    |                          |         |-- Create KnowledgeWorkerAgent --->|
  |                    |                          |                      |                      |
  |                    |                          |-- _phase_execute() ->|                      |
  |                    |                          |                      |-- on_start() ------->|
  |                    |                          |                      |       |              |
  |                    |                          |                      |       |-- Create GraphServiceClient
  |                    |                          |                      |       |-- Create EmailOperations
  |                    |                          |                      |       |-- Create TeamsOperations
  |                    |                          |                      |<------+              |
  |                    |                          |                      |                      |
  |                    |                          |                      |-- run_activities() ->|
  |                    |                          |                      |       |              |
  |                    |                          |                      |       |-- send_email() ---------->|
  |                    |                          |                      |       |<---------------- msg_id --|
  |                    |                          |                      |       |                           |
  |                    |                          |                      |       |-- create_event() -------->|
  |                    |                          |                      |       |<-------------- event_id --|
  |                    |                          |                      |       |                           |
  |                    |                          |                      |<------+                           |
  |<-- deployment_id --|                          |                      |                                   |
```

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-26 | PromptWriter Agent | Initial specification |
