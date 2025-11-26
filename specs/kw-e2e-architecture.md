# Knowledge Worker E2E System Architecture

## Document Information

- **Version**: 1.0
- **Date**: 2025-11-26
- **Author**: Architect Agent
- **Issue**: #114 - Build KW simulation system with REAL M365 operations

---

## Executive Summary

This document specifies the architecture for integrating real M365 operations into the Knowledge Worker (KW) simulation system. The design addresses:

1. Real Entra user provisioning via existing `EntraUserManager`
2. Secure credential distribution to workers
3. Cross-worker communication with enforced internal-only boundaries
4. Transport rule enforcement via Exchange Online
5. Comprehensive resource tracking and cleanup

**Critical Design Decision**: Rename `real_m365` flag to `live_mode` throughout the codebase. The term "real" implies the alternative is "fake" or "dishonest", which is misleading - simulation mode is a valid operational mode, not a deceptive one.

---

## System Architecture

### Component Diagram

```
+------------------------------------------------------------------+
|                    KnowledgeWorkerOrchestrator                    |
|  (Deployment lifecycle: setup -> provision -> execute -> cleanup) |
+------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+------------------+  +------------------+  +------------------+
|  SecuritySetup   |  |  UserProvisioner |  |  EndpointManager |
|  - TransportRule |  |  - EntraUserMgr  |  |  - CloudPC       |
|  - GroupManager  |  |  - GroupMembership|  |  - CLIContainer |
+------------------+  +------------------+  +------------------+
         |                    |                    |
         +--------------------+--------------------+
                              |
                              v
+------------------------------------------------------------------+
|                     WorkerCredentialStore                         |
|  (Secure distribution of M365 credentials to worker agents)       |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    KnowledgeWorkerAgent Pool                      |
|  +------------+  +------------+  +------------+  +------------+  |
|  | Worker 001 |  | Worker 002 |  | Worker ... |  | Worker N   |  |
|  | (Legal)    |  | (Engineer) |  | (HR)       |  | (Finance)  |  |
|  +------------+  +------------+  +------------+  +------------+  |
+------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+------------------+  +------------------+  +------------------+
| EmailOperations  |  | TeamsOperations  |  | CalendarOps     |
| - Validated send |  | - Channel post   |  | - Event create  |
| - Inbox read     |  | - Direct chat    |  | - RSVP          |
+------------------+  +------------------+  +------------------+
         |                    |                    |
         +--------------------+--------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    CommunicationValidator                         |
|  (Application-level defense: block all external recipients)       |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    Microsoft Graph API                            |
|  (Authenticated via M365ClientFactory with tenant app)            |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    Exchange Transport Rules                       |
|  (Server-level defense: block external mail at Exchange layer)    |
+------------------------------------------------------------------+
```

### Data Flow: Email Send Operation

```
Worker Agent                    Operations               Validation              M365
    |                              |                        |                     |
    |---(1) send_email()---------->|                        |                     |
    |                              |---(2) validate-------->|                     |
    |                              |     recipients         |                     |
    |                              |<---(3) filtered--------|                     |
    |                              |     recipients         |                     |
    |                              |                        |                     |
    |                              |---(4) Graph API------------------------>|
    |                              |     sendMail          |                     |
    |                              |<---(5) response-----------------------|
    |<---(6) message_id------------|                        |                     |
    |                              |                        |                     |

Defense-in-Depth:
Layer 1: CommunicationValidator (application) - blocks at API call time
Layer 2: Transport Rules (Exchange) - blocks at server delivery time
```

---

## Key Integration Points

### 1. Orchestrator <-> EntraUserManager Integration

**Current State**: `EntraUserManager` exists in `identity/user_manager.py` but is not integrated with the orchestrator.

**Required Changes**:

```python
# orchestrator.py - Add to _phase_provision()

class KnowledgeWorkerOrchestrator:
    def __init__(self, graph_client: GraphServiceClient | None = None):
        self._graph_client = graph_client
        self._user_manager: EntraUserManager | None = None
        self._group_manager: EntraGroupManager | None = None
        # ... existing fields ...

    async def _phase_provision(self, state: DeploymentState) -> None:
        """Provision phase with real Entra users."""
        if state.config.live_mode:
            await self._provision_real_users(state)
        else:
            await self._provision_simulated_users(state)

    async def _provision_real_users(self, state: DeploymentState) -> None:
        """Create actual Entra users via Graph API."""
        # Initialize managers
        self._user_manager = EntraUserManager(
            graph_client=self._graph_client,
            run_id=state.run_id,
            tenant_domain=state.config.tenant_domain,
        )
        self._group_manager = EntraGroupManager(
            graph_client=self._graph_client,
            run_id=state.run_id,
        )

        # Create all-workers security group (for transport rules)
        all_workers_group_id = await self._group_manager.create_all_workers_group()
        state.inventory.register("security_groups", all_workers_group_id)

        # Provision each worker
        for dept, dept_config in state.config.departments.items():
            for i in range(dept_config["count"]):
                identity = await self._user_manager.provision_worker(
                    department=dept,
                    index=i,
                    display_name=self._generate_display_name(dept, i),
                )

                # Add to all-workers group
                await self._group_manager.add_member(
                    all_workers_group_id,
                    identity.entra_object_id
                )

                # Register for cleanup
                state.inventory.register("entra_users", identity.entra_object_id)

                # Create worker agent with real identity
                await self._create_worker_with_identity(state, identity, dept_config)
```

### 2. Worker <-> Credential Distribution

**Current State**: Workers use `M365ClientFactory.create()` which reads from environment variables. This works for single-worker scenarios but not for multi-worker deployments where each worker needs distinct credentials.

**Design Decision**: Use **Application-level authentication with delegated permissions** rather than per-user credentials.

**Rationale**:
- Creating client secrets for 50-300 users is impractical
- Per-user interactive auth requires human intervention
- Application permissions with "on behalf of" delegation is the standard enterprise pattern

**Architecture**:

```python
# New: credential_store.py

class WorkerCredentialStore:
    """Manages credential distribution for multi-worker deployments.

    Uses a single application credential (from environment) with
    delegated permissions to act on behalf of provisioned users.
    """

    def __init__(self, app_credential: ClientSecretCredential):
        self._app_credential = app_credential
        self._worker_tokens: dict[str, str] = {}  # worker_id -> user_object_id

    def register_worker(self, worker_id: str, entra_object_id: str) -> None:
        """Register a worker's Entra identity for Graph API operations."""
        self._worker_tokens[worker_id] = entra_object_id

    def get_user_id_for_worker(self, worker_id: str) -> str:
        """Get the Entra object ID for Graph API calls on behalf of worker."""
        return self._worker_tokens.get(worker_id, "")

    def create_client_for_worker(self, worker_id: str) -> M365Client:
        """Create M365 client that operates on behalf of a specific worker."""
        # All workers share the same app credential
        # But operations target different user mailboxes
        return M365ClientFactory.create()  # App-level auth
```

**Graph API Pattern for Delegated Operations**:

```python
# Operations use worker's entra_object_id to target specific user
async def send_email(self, to: list[str], subject: str, body: str) -> str:
    # This sends FROM the worker's mailbox using app permissions
    await self.client.graph.users.by_user_id(
        self.worker.entra_object_id  # <-- Target specific user
    ).send_mail.post(body=message_data)
```

### 3. Cross-Worker Communication

**Problem**: Workers need to know each other's email addresses to communicate.

**Solution**: Orchestrator maintains a **worker registry** that provides allowed recipients to each agent.

```python
# New: worker_registry.py

class WorkerRegistry:
    """Registry of all workers in a deployment for cross-worker communication."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._workers: dict[str, WorkerIdentity] = {}  # worker_id -> identity

    def register(self, identity: WorkerIdentity) -> None:
        """Register a worker identity."""
        self._workers[identity.worker_id] = identity

    def get_all_upns(self) -> list[str]:
        """Get all worker UPNs for communication validation."""
        return [w.user_principal_name for w in self._workers.values()]

    def get_workers_by_department(self, department: str) -> list[WorkerIdentity]:
        """Get workers in a specific department."""
        return [w for w in self._workers.values() if w.department == department]

    def get_random_recipients(self, exclude: str, count: int = 1) -> list[str]:
        """Get random worker UPNs for activity generation."""
        import random
        candidates = [w.user_principal_name for w in self._workers.values()
                      if w.worker_id != exclude]
        return random.sample(candidates, min(count, len(candidates)))
```

**Integration with Worker Agent**:

```python
# In orchestrator._phase_provision() after all workers created:

# Build registry
worker_registry = WorkerRegistry(state.run_id)
for worker in state.workers:
    worker_registry.register(worker.worker_identity)

# Distribute allowed recipients to all workers
all_upns = worker_registry.get_all_upns()
for worker in state.workers:
    worker.add_allowed_recipients(all_upns)
```

### 4. Transport Rules Enforcement

**Current State**: `TransportRuleManager` exists but has placeholder implementations (Exchange PowerShell not integrated).

**Options**:

| Option | Pros | Cons |
|--------|------|------|
| A. Exchange PowerShell Module | Full feature support | Requires PowerShell runtime |
| B. Exchange Admin Center API | REST-based | Limited documentation |
| C. Security & Compliance API | Microsoft-supported | Complex setup |
| D. Application-level only | No external dependencies | Single point of failure |

**Recommendation**: **Option D with enhanced logging** for initial implementation, with Option A as future enhancement.

**Rationale**:
- The `CommunicationValidator` already blocks external recipients at application level
- Transport rules are defense-in-depth, not primary control
- Exchange PowerShell integration adds significant complexity
- For a demo/testing system, application-level control is sufficient

**Enhanced Implementation**:

```python
# transport_rules.py - Enhanced for live_mode

class TransportRuleManager:
    async def create_internal_only_rule(
        self,
        worker_group_id: str,
        priority: int = 0,
    ) -> str:
        """Create transport rule (or log intent if not integrated)."""
        rule_name = self.RULE_NAME_PATTERN.format(run_id=self.run_id[:8])

        if self._exchange_connected:
            # Full Exchange Online integration (future)
            return await self._create_exchange_rule(rule_name, worker_group_id)
        else:
            # Log the rule that SHOULD be created for manual verification
            logger.warning(
                f"Transport rule creation requires Exchange PowerShell integration. "
                f"Manual rule required:\n"
                f"  Name: {rule_name}\n"
                f"  Condition: SenderMemberOf = {worker_group_id}\n"
                f"  Exception: RecipientDomainIs = {self.tenant_domain}\n"
                f"  Action: RejectMessage with 5.7.1"
            )
            return rule_name  # Return name for tracking even if not created
```

---

## Interface Contracts

### DeploymentConfig (Updated)

```python
@dataclass
class DeploymentConfig:
    """Configuration for a knowledge worker deployment.

    Attributes:
        name: Deployment name
        total_workers: Total number of workers to deploy
        departments: Department configurations
        duration_hours: How long to run activities
        tenant_domain: M365 tenant domain (required for live_mode)
        live_mode: If True, execute real M365 operations against tenant

    Note:
        live_mode requires the following environment variables:
        - KW_TENANT_ID: Azure AD tenant ID
        - KW_APP_ID: Application (client) ID with Graph permissions
        - KW_CLIENT_SECRET: Client secret for application
    """

    name: str = "kw-deployment"
    total_workers: int = 10
    departments: dict[str, dict[str, Any]] = field(default_factory=dict)
    duration_hours: int = 8
    tenant_domain: str = ""
    live_mode: bool = False  # RENAMED from real_m365
```

### WorkerIdentity (Additions)

```python
class WorkerIdentity(BaseModel):
    """Identity of a simulated knowledge worker.

    Additional fields for live_mode:
        password_hash: Hashed password (not stored in plain text)
        license_assigned: Whether M365 license is assigned
        mailbox_provisioned: Whether Exchange mailbox is ready
    """
    # ... existing fields ...

    # Live mode tracking
    password_hash: str = ""  # Only hash stored, never plain text
    license_assigned: bool = False
    mailbox_provisioned: bool = False
```

### New: LiveModeConfig

```python
@dataclass
class LiveModeConfig:
    """Configuration specific to live M365 operations.

    Attributes:
        require_transport_rules: Fail if transport rules can't be created
        skip_license_assignment: Don't assign M365 licenses (use existing)
        cleanup_on_error: Delete resources if deployment fails
        parallel_provisioning_limit: Max concurrent user creations
        activity_delay_seconds: Minimum delay between activities per worker
    """
    require_transport_rules: bool = False  # Warn-only by default
    skip_license_assignment: bool = True   # Manual license assignment assumed
    cleanup_on_error: bool = True
    parallel_provisioning_limit: int = 10  # Graph API rate limit friendly
    activity_delay_seconds: float = 5.0    # Prevent rate limiting
```

---

## Error Handling Strategy

### Provisioning Errors

```python
class ProvisioningError(Exception):
    """Base exception for provisioning failures."""
    pass

class UserProvisioningError(ProvisioningError):
    """Failed to create Entra user."""
    def __init__(self, worker_id: str, reason: str):
        self.worker_id = worker_id
        self.reason = reason
        super().__init__(f"Failed to provision {worker_id}: {reason}")

class InsufficientLicensesError(ProvisioningError):
    """Not enough M365 licenses available."""
    def __init__(self, requested: int, available: int):
        super().__init__(f"Requested {requested} workers but only {available} licenses")
```

### Recovery Strategy

```python
async def _provision_with_recovery(self, state: DeploymentState) -> None:
    """Provision workers with automatic recovery on partial failure."""
    successfully_provisioned: list[WorkerIdentity] = []

    try:
        for worker_spec in self._generate_worker_specs(state.config):
            try:
                identity = await self._user_manager.provision_worker(**worker_spec)
                successfully_provisioned.append(identity)
            except UserProvisioningError as e:
                logger.error(f"Worker provisioning failed: {e}")
                if state.config.live_mode_config.cleanup_on_error:
                    # Continue provisioning remaining workers
                    continue
                else:
                    raise  # Fail fast
    except Exception:
        # Rollback on catastrophic failure
        if state.config.live_mode_config.cleanup_on_error:
            await self._rollback_provisioned_users(successfully_provisioned)
        raise
```

---

## Cleanup/Rollback Strategy

### Resource Deletion Order

The cleanup manager already implements correct deletion order. Key additions for live_mode:

```python
async def cleanup_all(self, inventory: KnowledgeWorkerResourceInventory) -> CleanupReport:
    """Clean up all resources in reverse dependency order.

    Order:
    1. Stop worker activity (cancel async tasks)
    2. Delete container apps (endpoints)
    3. Delete Cloud PCs (endpoints)
    4. Remove transport rules (Exchange)
    5. Delete Teams teams (collaboration)
    6. Delete M365 groups (collaboration)
    7. Delete security groups (identity)
    8. Delete Entra users (identity) - LAST because they may own resources

    Each deletion includes:
    - 3 retry attempts with exponential backoff
    - Idempotent handling (already-deleted = success)
    - Error logging without failing entire cleanup
    """
```

### Orphan Resource Detection

```python
class OrphanResourceDetector:
    """Detects HayMaker resources that weren't properly cleaned up."""

    async def find_orphans(self, tenant_domain: str) -> dict[str, list[str]]:
        """Find all HayMaker resources in the tenant.

        Looks for resources matching patterns:
        - Users: kw-*@{tenant_domain}
        - Groups: kw-* or KW-*
        - Transport rules: HayMaker-*
        """
        orphans = {
            "users": await self._find_orphan_users(tenant_domain),
            "groups": await self._find_orphan_groups(),
            "transport_rules": await self._find_orphan_rules(),
        }
        return orphans

    async def cleanup_orphans(self, orphans: dict[str, list[str]]) -> CleanupReport:
        """Delete detected orphan resources."""
        # Implementation uses same cleanup logic as normal cleanup
```

---

## File Modifications Required

### Existing Files to Modify

| File | Changes |
|------|---------|
| `orchestrator.py` | Rename `real_m365` to `live_mode`, integrate EntraUserManager, add WorkerRegistry |
| `agent.py` | Accept pre-provisioned WorkerIdentity, use credential store |
| `m365_client.py` | Add support for delegated operations (user-targeted API calls) |
| `cleanup/cleanup_manager.py` | Add orphan detection, enhance retry logic |
| `identity/transport_rules.py` | Add logging mode for non-Exchange environments |

### New Files to Create

| File | Purpose |
|------|---------|
| `credential_store.py` | Manage credential distribution to workers |
| `worker_registry.py` | Track all workers for cross-worker communication |
| `live_mode_config.py` | Configuration specific to live M365 operations |
| `orphan_detector.py` | Find and clean up orphaned resources |
| `provisioning_coordinator.py` | Coordinate parallel user provisioning with rate limiting |

---

## Estimated Complexity

### Implementation Effort

| Component | Complexity | Effort (hours) | Dependencies |
|-----------|------------|----------------|--------------|
| Rename `real_m365` to `live_mode` | Low | 2 | None |
| Orchestrator-EntraUserManager integration | Medium | 8 | EntraUserManager |
| WorkerRegistry for cross-worker comm | Low | 4 | None |
| Credential store | Medium | 6 | M365Client |
| Enhanced cleanup with orphan detection | Medium | 6 | CleanupManager |
| Transport rule logging mode | Low | 2 | TransportRuleManager |
| E2E testing and validation | High | 12 | All above |

**Total Estimated Effort**: 40 hours

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Graph API rate limiting | High | Medium | Implement exponential backoff, limit parallel ops |
| Insufficient M365 licenses | Medium | High | Check license availability before provisioning |
| Transport rules not enforced | Low | Medium | Application-level validation as primary defense |
| Cleanup failures leaving orphans | Medium | Medium | Orphan detection and manual cleanup tooling |
| Credential exposure | Low | Critical | Never log/store plain text passwords |

---

## Security Considerations

### Defense in Depth

1. **Application Layer**: `CommunicationValidator` validates all recipients before API calls
2. **Transport Layer**: Exchange rules block external mail at server (when integrated)
3. **Network Layer**: All operations within Azure tenant boundary

### Credential Security

- Application client secret stored in environment variable (not code)
- User passwords generated but never stored in plain text
- No interactive authentication required (pure app-to-app)

### Audit Trail

```python
# All operations logged with:
{
    "timestamp": "ISO8601",
    "worker_id": "kw-abc12345-engi-001",
    "operation": "email_send",
    "target_recipients": ["internal@tenant.onmicrosoft.com"],
    "blocked_recipients": [],  # Any filtered external addresses
    "result": "success|blocked|error",
    "run_id": "kw-abc12345"
}
```

---

## Demo Execution Plan

### Prerequisites

1. Azure tenant with M365 licenses available
2. App registration with required Graph permissions:
   - `User.ReadWrite.All` (create users)
   - `Group.ReadWrite.All` (create groups)
   - `Mail.Send` (send as users)
   - `Calendars.ReadWrite` (create events)
   - `ChannelMessage.Send` (Teams posts)
3. Environment variables configured:
   - `KW_TENANT_ID`
   - `KW_APP_ID`
   - `KW_CLIENT_SECRET`

### Demo Script

```bash
# 1. Create deployment with 10 workers across 4 departments
python -m azure_haymaker.knowledge_worker.cli deploy \
    --name "kw-demo-$(date +%Y%m%d)" \
    --live-mode \
    --tenant-domain "tenant.onmicrosoft.com" \
    --departments engineering:3 legal:2 hr:2 finance:3 \
    --duration-minutes 30

# 2. Monitor activity
python -m azure_haymaker.knowledge_worker.cli status --run-id kw-demo-*

# 3. Cleanup
python -m azure_haymaker.knowledge_worker.cli cleanup --run-id kw-demo-*

# 4. Verify no orphans
python -m azure_haymaker.knowledge_worker.cli scan-orphans \
    --tenant-domain "tenant.onmicrosoft.com"
```

### Evidence Collection

The demo should produce:
1. Screenshot of Entra ID showing created users
2. Screenshot of Exchange showing sent/received emails
3. Log file with all operations and their results
4. Cleanup report showing all resources deleted

---

## Appendix: Naming Conventions

| Resource Type | Pattern | Example |
|--------------|---------|---------|
| Entra User | `kw-{run_id[:8]}-{dept[:4]}-{index:03d}` | `kw-abc12345-engi-001` |
| Security Group | `kw-{run_id[:8]}-all-workers` | `kw-abc12345-all-workers` |
| Team Group | `KW-{run_id[:8]}-{Dept}-Team{N}` | `KW-ABC12345-Engineering-Team1` |
| Transport Rule | `HayMaker-{run_id[:8]}-InternalOnly` | `HayMaker-abc12345-InternalOnly` |
| Container App | `kw-{run_id[:8]}-{worker_id}` | `kw-abc12345-engi-001` |
