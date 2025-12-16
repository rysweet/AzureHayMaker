# Knowledge Worker Activity Framework Architecture

**Version**: 1.0
**Status**: Design Specification
**Last Updated**: 2025-01-25

## Executive Summary

The Knowledge Worker Activity Framework extends Azure HayMaker to simulate 50-300 knowledge workers performing everyday M365 activities (email, Teams, documents). This generates realistic benign telemetry for cybersecurity analysis and security product testing.

The design follows HayMaker's proven patterns:
- Goal-seeking agents extending `AgentBase`
- Container Apps execution model
- Tag-based resource tracking
- Orchestrated workflow with cleanup guarantees

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component Architecture](#2-component-architecture)
3. [Scenario Organization](#3-scenario-organization)
4. [Identity Management](#4-identity-management)
5. [M365 Operations Module](#5-m365-operations-module)
6. [Endpoint Strategy](#6-endpoint-strategy)
7. [Communication Safety Controls](#7-communication-safety-controls)
8. [Resource Tracking and Cleanup](#8-resource-tracking-and-cleanup)
9. [Execution Model](#9-execution-model)
10. [Implementation Roadmap](#10-implementation-roadmap)

---

## 1. Architecture Overview

### High-Level Architecture

```
+-----------------------------------------------------------------------------------+
|                              Azure HayMaker Orchestrator                          |
|  +-----------------------------------------------------------------------------+  |
|  |                    Knowledge Worker Workflow Orchestrator                   |  |
|  |  [Phase 1: Setup] -> [Phase 2: Provision] -> [Phase 3: Execute] -> [Cleanup]|  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
                                        |
            +---------------------------+---------------------------+
            |                           |                           |
            v                           v                           v
+---------------------+     +---------------------+     +---------------------+
|   Identity Layer    |     |   M365 Operations   |     |   Endpoint Layer    |
|  - Entra Users      |     |  - Email Module     |     |  - Windows 365 PCs  |
|  - Security Groups  |     |  - Teams Module     |     |  - CLI Containers   |
|  - Transport Rules  |     |  - Documents Module |     |  - Activity Agents  |
+---------------------+     |  - Calendar Module  |     +---------------------+
                            +---------------------+
                                        |
                                        v
                        +-------------------------------+
                        |     M365 CLI (PnP) Layer     |
                        |  - Graph API Operations       |
                        |  - Certificate Auth           |
                        |  - Rate Limiting              |
                        +-------------------------------+
```

### Design Principles

1. **Internal-Only Communications**: All email/Teams traffic stays within the tenant
2. **Distinct Endpoints**: Activity originates from unique machine identities
3. **Team Boundaries**: Workers organized into security-scoped groups
4. **Full Cleanup**: All resources deletable at any time
5. **Cost Optimization**: Hybrid endpoint strategy balances telemetry richness vs. cost

---

## 2. Component Architecture

### 2.1 Class Hierarchy

The framework extends HayMaker's existing `AgentBase` class:

```
AgentBase (existing)
    |
    +-- KnowledgeWorkerAgent (new)
            |
            +-- EmailActivityAgent
            +-- TeamsActivityAgent
            +-- DocumentActivityAgent
            +-- CalendarActivityAgent
            |
            +-- KnowledgeWorkerOrchestratorAgent (coordinates workers)
```

### 2.2 Core Components

```python
# Location: src/azure_haymaker/knowledge_worker/

knowledge_worker/
    __init__.py
    agent.py                    # KnowledgeWorkerAgent base class
    orchestrator.py             # KnowledgeWorkerOrchestrator
    models/
        __init__.py
        worker.py               # WorkerIdentity, WorkerConfig
        team.py                 # Team, TeamConfig
        activity.py             # ActivitySpec, ActivityResult
    operations/
        __init__.py
        email.py                # EmailOperations
        teams.py                # TeamsOperations
        documents.py            # DocumentOperations
        calendar.py             # CalendarOperations
        base.py                 # M365OperationBase
    endpoints/
        __init__.py
        cloud_pc.py             # Windows365CloudPC provisioning
        cli_container.py        # M365 CLI container deployment
        manager.py              # EndpointManager
    identity/
        __init__.py
        user_manager.py         # EntraUserManager
        group_manager.py        # EntraGroupManager
        transport_rules.py      # TransportRuleManager
    cleanup/
        __init__.py
        cleanup_manager.py      # KnowledgeWorkerCleanup
```

### 2.3 KnowledgeWorkerAgent Class

```python
# src/azure_haymaker/knowledge_worker/agent.py

from azure_haymaker.agent_base import AgentBase, AgentConfig
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

@dataclass
class KnowledgeWorkerConfig(AgentConfig):
    """Configuration for a knowledge worker agent."""

    # Worker identity
    worker_id: str = ""
    display_name: str = ""
    department: str = ""
    persona: str = ""

    # Team membership
    team_id: str = ""
    team_name: str = ""

    # Activity configuration
    activity_types: list[str] = field(default_factory=list)
    activity_frequency_minutes: int = 30

    # Endpoint configuration
    endpoint_type: str = "cli_container"  # "cli_container" or "cloud_pc"
    endpoint_id: str = ""

    # M365 credentials
    m365_app_id: str = ""
    m365_cert_thumbprint: str = ""


class KnowledgeWorkerAgent(AgentBase):
    """Base class for knowledge worker activity agents.

    Extends AgentBase to add M365 activity capabilities including:
    - Email send/receive/organize operations
    - Teams messaging and channel operations
    - Document creation and collaboration
    - Calendar event management

    Each worker executes activities from a distinct endpoint identity.
    """

    def __init__(
        self,
        worker_config: KnowledgeWorkerConfig,
        prompt_path: Path | None = None,
    ):
        super().__init__(prompt_path)
        self.worker_config = worker_config
        self._m365_client: Any = None
        self._allowed_recipients: set[str] = set()

    def get_config(self) -> AgentConfig:
        """Return the worker configuration."""
        return self.worker_config

    def on_start(self) -> None:
        """Initialize M365 client and load allowed recipients."""
        super().on_start()
        self._initialize_m365_client()
        self._load_allowed_recipients()

    def on_execute(self) -> int:
        """Execute knowledge worker activities."""
        # Activity execution is handled by specialized subclasses
        # or by the activity scheduler
        return super().on_execute()

    def on_cleanup(self, exit_code: int) -> None:
        """Disconnect M365 client and report metrics."""
        self._disconnect_m365_client()
        super().on_cleanup(exit_code)

    def _initialize_m365_client(self) -> None:
        """Initialize M365 CLI connection with certificate auth."""
        # Implementation connects to M365 using PnP CLI
        pass

    def _load_allowed_recipients(self) -> None:
        """Load allowed recipient list for communication safety."""
        # Only internal tenant users/groups are allowed
        pass

    def _disconnect_m365_client(self) -> None:
        """Disconnect M365 CLI session."""
        pass

    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient is in allowed list (internal only)."""
        return recipient.lower() in self._allowed_recipients
```

### 2.4 Models

```python
# src/azure_haymaker/knowledge_worker/models/worker.py

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class WorkerPersona(str, Enum):
    """Knowledge worker persona types."""
    EXECUTIVE = "executive"
    LEGAL = "legal"
    ENGINEERING = "engineering"
    HR = "hr"
    FINANCE = "finance"
    SALES = "sales"
    OPERATIONS = "operations"
    MARKETING = "marketing"

class EndpointType(str, Enum):
    """Endpoint type for worker activity."""
    CLOUD_PC = "cloud_pc"
    CLI_CONTAINER = "cli_container"

class WorkerIdentity(BaseModel):
    """Identity of a simulated knowledge worker."""

    worker_id: str = Field(..., description="Unique worker identifier")
    display_name: str = Field(..., description="Display name in Entra")
    user_principal_name: str = Field(..., description="UPN for M365 login")
    department: str = Field(..., description="Department/team name")
    persona: WorkerPersona = Field(..., description="Worker persona type")

    # Entra identifiers
    entra_object_id: str = Field(default="", description="Entra object ID")

    # Endpoint assignment
    endpoint_type: EndpointType = Field(
        default=EndpointType.CLI_CONTAINER,
        description="Type of endpoint for this worker"
    )
    endpoint_id: str = Field(default="", description="Assigned endpoint ID")

    # Team membership
    team_ids: list[str] = Field(default_factory=list)
    security_group_ids: list[str] = Field(default_factory=list)

    # Tracking
    created_at: datetime | None = None
    last_activity_at: datetime | None = None

class WorkerConfig(BaseModel):
    """Configuration for worker activity patterns."""

    # Activity frequency
    email_per_hour: int = Field(default=5, ge=0, le=50)
    teams_messages_per_hour: int = Field(default=10, ge=0, le=100)
    documents_per_day: int = Field(default=3, ge=0, le=20)
    meetings_per_day: int = Field(default=4, ge=0, le=15)

    # Activity variation
    activity_variance_percent: int = Field(
        default=30,
        ge=0,
        le=100,
        description="Random variation in activity frequency"
    )

    # Working hours (UTC)
    work_start_hour: int = Field(default=8, ge=0, le=23)
    work_end_hour: int = Field(default=17, ge=0, le=23)

    # Communication preferences
    preferred_communication: str = Field(
        default="teams",
        description="Primary communication channel"
    )
```

```python
# src/azure_haymaker/knowledge_worker/models/team.py

from pydantic import BaseModel, Field
from datetime import datetime

class Team(BaseModel):
    """Team of knowledge workers with shared context."""

    team_id: str = Field(..., description="Unique team identifier")
    team_name: str = Field(..., description="Team display name")
    department: str = Field(..., description="Department classification")

    # Entra identifiers
    security_group_id: str = Field(default="", description="Entra security group ID")
    m365_group_id: str = Field(default="", description="M365 unified group ID")
    teams_team_id: str = Field(default="", description="Microsoft Teams team ID")

    # Members
    member_ids: list[str] = Field(default_factory=list)
    manager_ids: list[str] = Field(default_factory=list)

    # Cross-team communication
    allowed_peer_team_ids: list[str] = Field(
        default_factory=list,
        description="Teams allowed for cross-team communication"
    )

    # Shared resources
    sharepoint_site_id: str = Field(default="")
    shared_mailbox: str = Field(default="")

    # Tracking
    created_at: datetime | None = None
    run_id: str = Field(default="", description="HayMaker run ID")

class TeamConfig(BaseModel):
    """Configuration for team creation and management."""

    # Team size
    min_members: int = Field(default=3, ge=1)
    max_members: int = Field(default=15, le=50)
    manager_ratio: float = Field(default=0.1, ge=0, le=0.5)

    # Cross-team rules
    cross_team_communication_enabled: bool = True
    max_peer_teams: int = Field(default=3, ge=0, le=10)
```

---

## 3. Scenario Organization

### 3.1 Hierarchical Structure

```
Knowledge Worker Deployment
    |
    +-- Organization (run-level container)
    |       |
    |       +-- Department (Legal, Engineering, HR, etc.)
    |               |
    |               +-- Team (group of 3-15 workers)
    |                       |
    |                       +-- Worker (individual identity)
```

### 3.2 Department Configuration

Each department has characteristic activity patterns:

| Department | Email/hr | Teams/hr | Docs/day | Meetings/day | Cross-team |
|------------|----------|----------|----------|--------------|------------|
| Executive  | 8        | 5        | 2        | 6            | High       |
| Legal      | 6        | 3        | 8        | 3            | Medium     |
| Engineering| 4        | 15       | 5        | 4            | Medium     |
| HR         | 10       | 8        | 4        | 5            | High       |
| Finance    | 7        | 4        | 6        | 4            | Medium     |
| Sales      | 12       | 10       | 3        | 8            | High       |
| Operations | 5        | 12       | 4        | 3            | Medium     |
| Marketing  | 8        | 8        | 6        | 5            | High       |

### 3.3 Scenario Definition

```python
# src/azure_haymaker/knowledge_worker/scenarios/default_scenario.py

from azure_haymaker.knowledge_worker.models.team import TeamConfig

DEFAULT_DEPLOYMENT = {
    "name": "knowledge-worker-50",
    "description": "50 knowledge workers across 8 departments",
    "total_workers": 50,
    "departments": {
        "executive": {
            "team_count": 1,
            "workers_per_team": 3,
            "endpoint_type": "cloud_pc",  # Rich telemetry for executives
            "config": {
                "email_per_hour": 8,
                "teams_messages_per_hour": 5,
                "documents_per_day": 2,
                "meetings_per_day": 6,
            }
        },
        "engineering": {
            "team_count": 2,
            "workers_per_team": 8,
            "endpoint_type": "cli_container",  # Cost-efficient
            "config": {
                "email_per_hour": 4,
                "teams_messages_per_hour": 15,
                "documents_per_day": 5,
                "meetings_per_day": 4,
            }
        },
        "sales": {
            "team_count": 2,
            "workers_per_team": 6,
            "endpoint_type": "cli_container",
            "config": {
                "email_per_hour": 12,
                "teams_messages_per_hour": 10,
                "documents_per_day": 3,
                "meetings_per_day": 8,
            }
        },
        # ... additional departments
    },
    "cross_team_rules": {
        "executive": ["engineering", "sales", "hr", "finance"],
        "engineering": ["executive", "operations"],
        "sales": ["executive", "marketing", "operations"],
        # ... additional rules
    }
}
```

### 3.4 Worker Assignment Algorithm

```python
def assign_workers_to_scenarios(
    total_workers: int,
    department_configs: dict,
    endpoint_budget: dict,  # cloud_pc: 10, cli_container: 290
) -> list[WorkerAssignment]:
    """
    Assign workers to departments and endpoints based on:
    1. Department weights (from config)
    2. Endpoint budget constraints
    3. Team size requirements
    """
    assignments = []

    # Calculate department weights
    total_weight = sum(
        cfg.get("weight", 1) for cfg in department_configs.values()
    )

    # Distribute workers by weight, respecting endpoint budget
    cloud_pc_remaining = endpoint_budget.get("cloud_pc", 0)

    for dept, cfg in department_configs.items():
        dept_workers = int(
            total_workers * (cfg.get("weight", 1) / total_weight)
        )

        # Assign endpoint types
        if cfg.get("endpoint_type") == "cloud_pc" and cloud_pc_remaining > 0:
            cloud_pc_count = min(dept_workers, cloud_pc_remaining)
            cloud_pc_remaining -= cloud_pc_count
            cli_count = dept_workers - cloud_pc_count
        else:
            cloud_pc_count = 0
            cli_count = dept_workers

        # Create assignments
        for i in range(dept_workers):
            assignments.append(WorkerAssignment(
                department=dept,
                endpoint_type="cloud_pc" if i < cloud_pc_count else "cli_container",
                team_index=i // cfg.get("workers_per_team", 5),
            ))

    return assignments
```

---

## 4. Identity Management

### 4.1 Identity Architecture

```
+----------------------------------+
|        Entra ID Tenant           |
+----------------------------------+
|                                  |
|  +----------------------------+  |
|  |    HayMaker App Registration |  |
|  |  - Application Permissions   |  |
|  |  - Certificate Auth          |  |
|  +----------------------------+  |
|              |                   |
|              v                   |
|  +----------------------------+  |
|  |    Knowledge Worker Users    |  |
|  |  - kw-{run_id}-{dept}-{n}   |  |
|  |  - No interactive login     |  |
|  +----------------------------+  |
|              |                   |
|  +----------------------------+  |
|  |    Security Groups           |  |
|  |  - kw-{run_id}-{dept}-team-n|  |
|  |  - kw-{run_id}-all-workers  |  |
|  +----------------------------+  |
|              |                   |
|  +----------------------------+  |
|  |    Transport Rules           |  |
|  |  - Block external email     |  |
|  |  - Route all internal       |  |
|  +----------------------------+  |
|                                  |
+----------------------------------+
```

### 4.2 User Provisioning

```python
# src/azure_haymaker/knowledge_worker/identity/user_manager.py

from msgraph.graph_service_client import GraphServiceClient
from msgraph.generated.models.user import User
from typing import AsyncIterator

class EntraUserManager:
    """Manages Entra ID user provisioning for knowledge workers."""

    NAMING_PATTERN = "kw-{run_id}-{dept}-{index:03d}"
    UPN_DOMAIN = "haymakertenant.onmicrosoft.com"  # Configure per tenant

    def __init__(
        self,
        graph_client: GraphServiceClient,
        run_id: str,
        tenant_domain: str,
    ):
        self.graph_client = graph_client
        self.run_id = run_id
        self.tenant_domain = tenant_domain

    async def provision_worker(
        self,
        department: str,
        index: int,
        display_name: str,
    ) -> WorkerIdentity:
        """Provision a single knowledge worker user in Entra."""

        # Generate naming
        username = self.NAMING_PATTERN.format(
            run_id=self.run_id[:8],
            dept=department[:4].lower(),
            index=index,
        )
        upn = f"{username}@{self.tenant_domain}"

        # Create user via Graph API
        user = User()
        user.account_enabled = True
        user.display_name = display_name
        user.mail_nickname = username
        user.user_principal_name = upn
        user.password_profile = {
            "force_change_password_next_sign_in": False,
            "password": self._generate_secure_password(),
        }
        user.department = department

        # Add HayMaker tags as extension attributes
        # (Entra ID doesn't support arbitrary tags, use extension attributes)

        created_user = await self.graph_client.users.post(user)

        return WorkerIdentity(
            worker_id=username,
            display_name=display_name,
            user_principal_name=upn,
            department=department,
            entra_object_id=created_user.id,
            persona=self._persona_from_department(department),
        )

    async def provision_batch(
        self,
        workers: list[dict],
    ) -> AsyncIterator[WorkerIdentity]:
        """Provision multiple workers with rate limiting."""

        # Graph API batch limit: 20 requests per batch
        # Rate limit: 10,000 requests per 10 minutes

        for worker in workers:
            identity = await self.provision_worker(
                department=worker["department"],
                index=worker["index"],
                display_name=worker["display_name"],
            )
            yield identity

            # Rate limiting (simple approach)
            await asyncio.sleep(0.1)  # 10 per second max

    async def delete_worker(self, entra_object_id: str) -> bool:
        """Delete a knowledge worker user from Entra."""
        try:
            await self.graph_client.users.by_user_id(entra_object_id).delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete user {entra_object_id}: {e}")
            return False

    async def list_workers(self, run_id: str) -> list[WorkerIdentity]:
        """List all workers for a given run."""
        # Filter by displayName pattern or extension attribute
        filter_query = f"startswith(mailNickname, 'kw-{run_id[:8]}')"
        users = await self.graph_client.users.get(
            request_configuration={"query_parameters": {"filter": filter_query}}
        )
        return [self._user_to_identity(u) for u in users.value]
```

### 4.3 Permission Model

**Application Permissions Required (Entra App Registration)**:

| Permission | Type | Purpose |
|------------|------|---------|
| `User.ReadWrite.All` | Application | Create/manage worker users |
| `Group.ReadWrite.All` | Application | Create/manage security groups |
| `Mail.Send` | Application | Send email as workers |
| `Mail.ReadWrite` | Application | Read/organize email |
| `ChannelMessage.Send` | Application | Post Teams messages |
| `Files.ReadWrite.All` | Application | Document operations |
| `Calendars.ReadWrite` | Application | Calendar operations |
| `CloudPC.ReadWrite.All` | Application | Windows 365 provisioning |
| `DeviceManagementConfiguration.ReadWrite.All` | Application | Cloud PC policies |

**Certificate-Based Authentication**:

```python
# Authentication flow for M365 operations
from azure.identity import CertificateCredential

credential = CertificateCredential(
    tenant_id=config.tenant_id,
    client_id=config.app_client_id,
    certificate_path="/secrets/haymaker-m365-cert.pem",
)

graph_client = GraphServiceClient(credential)
```

### 4.4 Naming Conventions

| Resource Type | Pattern | Example |
|---------------|---------|---------|
| User | `kw-{run_id[:8]}-{dept[:4]}-{index:03d}` | `kw-abc12345-engi-001` |
| Security Group | `kw-{run_id[:8]}-{dept}-team-{n}` | `kw-abc12345-engineering-team-1` |
| All Workers Group | `kw-{run_id[:8]}-all-workers` | `kw-abc12345-all-workers` |
| M365 Group | `KW-{RunId[:8]}-{Dept}-Team{N}` | `KW-ABC12345-Engineering-Team1` |
| Transport Rule | `HayMaker-{run_id[:8]}-InternalOnly` | `HayMaker-abc12345-InternalOnly` |

---

## 5. M365 Operations Module

### 5.1 Module Architecture

```
operations/
    base.py          # Abstract base for all M365 operations
    email.py         # Email send, receive, organize
    teams.py         # Teams messaging, channels
    documents.py     # SharePoint/OneDrive documents
    calendar.py      # Calendar events, meetings
    m365_client.py   # M365 CLI wrapper
```

### 5.2 Base Operation Class

```python
# src/azure_haymaker/knowledge_worker/operations/base.py

from abc import ABC, abstractmethod
from typing import Any
import logging

logger = logging.getLogger(__name__)

class M365OperationBase(ABC):
    """Abstract base class for M365 operations.

    All M365 operations must:
    1. Validate recipients are internal-only
    2. Rate limit API calls
    3. Log operations for telemetry
    4. Handle Graph API errors gracefully
    """

    def __init__(
        self,
        worker_identity: WorkerIdentity,
        m365_client: M365Client,
        allowed_recipients: set[str],
    ):
        self.worker = worker_identity
        self.client = m365_client
        self.allowed_recipients = allowed_recipients
        self._operation_count = 0

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the M365 operation."""
        pass

    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient is in allowed list."""
        normalized = recipient.lower().strip()
        if normalized not in self.allowed_recipients:
            logger.warning(
                f"Blocked external recipient: {recipient} "
                f"(worker: {self.worker.worker_id})"
            )
            return False
        return True

    def validate_recipients(self, recipients: list[str]) -> list[str]:
        """Filter recipients to only allowed internal addresses."""
        return [r for r in recipients if self.validate_recipient(r)]

    async def _rate_limit(self) -> None:
        """Apply rate limiting between operations."""
        self._operation_count += 1
        if self._operation_count % 100 == 0:
            await asyncio.sleep(1)  # Pause every 100 operations
```

### 5.3 Email Operations

```python
# src/azure_haymaker/knowledge_worker/operations/email.py

from azure_haymaker.knowledge_worker.operations.base import M365OperationBase
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress

class EmailOperations(M365OperationBase):
    """Email operations using Graph API.

    Supported operations:
    - Send email (to, cc, bcc)
    - Read inbox
    - Organize (move to folders)
    - Reply/forward
    """

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        importance: str = "normal",
    ) -> str | None:
        """Send email from worker to internal recipients only.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body (HTML supported)
            cc: Optional CC recipients
            importance: low, normal, or high

        Returns:
            Message ID if sent, None if blocked
        """
        # Validate all recipients are internal
        valid_to = self.validate_recipients(to)
        valid_cc = self.validate_recipients(cc or [])

        if not valid_to:
            logger.warning(
                f"Email blocked: no valid recipients "
                f"(worker: {self.worker.worker_id}, subject: {subject})"
            )
            return None

        # Build message
        message = Message()
        message.subject = subject
        message.body = ItemBody(content=body, content_type="html")
        message.to_recipients = [
            Recipient(email_address=EmailAddress(address=addr))
            for addr in valid_to
        ]
        if valid_cc:
            message.cc_recipients = [
                Recipient(email_address=EmailAddress(address=addr))
                for addr in valid_cc
            ]
        message.importance = importance

        # Send via Graph API
        await self._rate_limit()
        result = await self.client.graph.users.by_user_id(
            self.worker.entra_object_id
        ).send_mail.post(message=message, save_to_sent_items=True)

        logger.info(
            f"Email sent: {self.worker.worker_id} -> {valid_to}, "
            f"subject: {subject[:50]}"
        )

        return result.id if result else None

    async def read_inbox(
        self,
        count: int = 10,
        unread_only: bool = False,
    ) -> list[dict]:
        """Read messages from worker's inbox."""

        filter_query = "isRead eq false" if unread_only else None

        await self._rate_limit()
        messages = await self.client.graph.users.by_user_id(
            self.worker.entra_object_id
        ).mail_folders.by_mail_folder_id("inbox").messages.get(
            request_configuration={
                "query_parameters": {
                    "top": count,
                    "filter": filter_query,
                    "orderby": "receivedDateTime desc",
                }
            }
        )

        return [
            {
                "id": m.id,
                "subject": m.subject,
                "from": m.from_.email_address.address if m.from_ else None,
                "received": m.received_date_time,
                "is_read": m.is_read,
            }
            for m in (messages.value or [])
        ]

    async def move_to_folder(
        self,
        message_id: str,
        folder_name: str,
    ) -> bool:
        """Move message to specified folder."""

        # Get or create folder
        folder_id = await self._get_or_create_folder(folder_name)

        await self._rate_limit()
        await self.client.graph.users.by_user_id(
            self.worker.entra_object_id
        ).messages.by_message_id(message_id).move.post(
            destination_id=folder_id
        )

        return True

    async def reply(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
    ) -> str | None:
        """Reply to a message."""

        await self._rate_limit()

        if reply_all:
            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).messages.by_message_id(message_id).reply_all.post(
                comment=body
            )
        else:
            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).messages.by_message_id(message_id).reply.post(
                comment=body
            )

        return message_id
```

### 5.4 Teams Operations

```python
# src/azure_haymaker/knowledge_worker/operations/teams.py

class TeamsOperations(M365OperationBase):
    """Microsoft Teams messaging operations.

    Supported operations:
    - Post to channel
    - Send direct message (chat)
    - Reply to thread
    - React to message
    """

    async def post_to_channel(
        self,
        team_id: str,
        channel_id: str,
        content: str,
        mentions: list[str] | None = None,
    ) -> str | None:
        """Post message to Teams channel.

        Args:
            team_id: Teams team ID
            channel_id: Channel ID within the team
            content: Message content (HTML supported)
            mentions: List of user IDs to @mention

        Returns:
            Message ID if posted
        """
        # Validate mentioned users are internal
        if mentions:
            mentions = [m for m in mentions if self.validate_recipient(m)]

        # Build message body with mentions
        body = ChatMessageBody(content=content, content_type="html")

        if mentions:
            body.content = self._add_mentions(content, mentions)

        message = ChatMessage(body=body)

        await self._rate_limit()
        result = await self.client.graph.teams.by_team_id(
            team_id
        ).channels.by_channel_id(
            channel_id
        ).messages.post(message)

        logger.info(
            f"Teams channel post: {self.worker.worker_id} -> "
            f"team:{team_id}/channel:{channel_id}"
        )

        return result.id if result else None

    async def send_chat_message(
        self,
        recipient_id: str,
        content: str,
    ) -> str | None:
        """Send direct chat message to another worker."""

        if not self.validate_recipient(recipient_id):
            return None

        # Get or create 1:1 chat
        chat_id = await self._get_or_create_chat(recipient_id)

        message = ChatMessage(
            body=ChatMessageBody(content=content, content_type="text")
        )

        await self._rate_limit()
        result = await self.client.graph.chats.by_chat_id(
            chat_id
        ).messages.post(message)

        return result.id if result else None

    async def reply_to_thread(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        content: str,
    ) -> str | None:
        """Reply to existing Teams thread."""

        message = ChatMessage(
            body=ChatMessageBody(content=content, content_type="text")
        )

        await self._rate_limit()
        result = await self.client.graph.teams.by_team_id(
            team_id
        ).channels.by_channel_id(
            channel_id
        ).messages.by_chat_message_id(
            message_id
        ).replies.post(message)

        return result.id if result else None
```

### 5.5 Document Operations

```python
# src/azure_haymaker/knowledge_worker/operations/documents.py

class DocumentOperations(M365OperationBase):
    """SharePoint/OneDrive document operations.

    Supported operations:
    - Create document (Word, Excel, PowerPoint)
    - Upload file
    - Share with team members
    - Download/read document
    """

    async def create_document(
        self,
        name: str,
        content: bytes,
        folder_path: str = "Documents",
        content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ) -> str | None:
        """Create document in worker's OneDrive."""

        await self._rate_limit()

        # Upload to OneDrive
        result = await self.client.graph.users.by_user_id(
            self.worker.entra_object_id
        ).drive.root.item_with_path(
            f"{folder_path}/{name}"
        ).content.put(content)

        logger.info(
            f"Document created: {self.worker.worker_id} -> {folder_path}/{name}"
        )

        return result.id if result else None

    async def share_with_team(
        self,
        item_id: str,
        team_members: list[str],
        permission: str = "read",  # read, write, owner
    ) -> bool:
        """Share document with team members."""

        # Validate all recipients are internal
        valid_members = self.validate_recipients(team_members)

        if not valid_members:
            return False

        # Create sharing invitation
        for member in valid_members:
            await self._rate_limit()
            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).drive.items.by_drive_item_id(
                item_id
            ).invite.post(
                recipients=[{"email": member}],
                roles=[permission],
                require_sign_in=True,
            )

        return True

    async def upload_to_sharepoint(
        self,
        site_id: str,
        library_name: str,
        file_name: str,
        content: bytes,
    ) -> str | None:
        """Upload document to SharePoint site."""

        await self._rate_limit()

        # Get drive for document library
        drives = await self.client.graph.sites.by_site_id(
            site_id
        ).drives.get()

        library_drive = next(
            (d for d in drives.value if d.name == library_name),
            None
        )

        if not library_drive:
            logger.warning(f"Library not found: {library_name}")
            return None

        # Upload file
        result = await self.client.graph.drives.by_drive_id(
            library_drive.id
        ).root.item_with_path(file_name).content.put(content)

        return result.id if result else None
```

### 5.6 Calendar Operations

```python
# src/azure_haymaker/knowledge_worker/operations/calendar.py

class CalendarOperations(M365OperationBase):
    """Calendar and meeting operations.

    Supported operations:
    - Create event
    - Accept/decline invitation
    - Update event
    - Cancel event
    """

    async def create_event(
        self,
        subject: str,
        start_time: datetime,
        end_time: datetime,
        attendees: list[str],
        location: str | None = None,
        is_online: bool = True,
        body: str = "",
    ) -> str | None:
        """Create calendar event with internal attendees only."""

        # Validate all attendees are internal
        valid_attendees = self.validate_recipients(attendees)

        if not valid_attendees:
            logger.warning(
                f"Event blocked: no valid attendees "
                f"(worker: {self.worker.worker_id})"
            )
            return None

        event = Event()
        event.subject = subject
        event.start = DateTimeTimeZone(
            date_time=start_time.isoformat(),
            time_zone="UTC"
        )
        event.end = DateTimeTimeZone(
            date_time=end_time.isoformat(),
            time_zone="UTC"
        )
        event.attendees = [
            Attendee(
                email_address=EmailAddress(address=addr),
                type="required"
            )
            for addr in valid_attendees
        ]

        if location:
            event.location = Location(display_name=location)

        if is_online:
            event.is_online_meeting = True
            event.online_meeting_provider = "teamsForBusiness"

        if body:
            event.body = ItemBody(content=body, content_type="html")

        await self._rate_limit()
        result = await self.client.graph.users.by_user_id(
            self.worker.entra_object_id
        ).calendar.events.post(event)

        logger.info(
            f"Event created: {self.worker.worker_id} -> {subject}, "
            f"attendees: {valid_attendees}"
        )

        return result.id if result else None

    async def respond_to_invitation(
        self,
        event_id: str,
        response: str,  # accept, tentative, decline
        comment: str = "",
    ) -> bool:
        """Respond to meeting invitation."""

        await self._rate_limit()

        if response == "accept":
            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).events.by_event_id(event_id).accept.post(
                comment=comment,
                send_response=True
            )
        elif response == "tentative":
            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).events.by_event_id(event_id).tentatively_accept.post(
                comment=comment,
                send_response=True
            )
        elif response == "decline":
            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).events.by_event_id(event_id).decline.post(
                comment=comment,
                send_response=True
            )

        return True
```

---

## 6. Endpoint Strategy

### 6.1 Hybrid Approach

The framework uses a hybrid endpoint strategy to balance telemetry richness against cost:

| Endpoint Type | Count | Cost/month | Telemetry Richness | Use Case |
|---------------|-------|------------|-------------------|----------|
| Windows 365 Cloud PC | 10-50 | $20-50/user | High (full desktop) | Executives, key personas |
| M365 CLI Container | 50-250 | ~$5/container | Medium (API only) | Scale workers |

### 6.2 Windows 365 Cloud PC Provisioning

```python
# src/azure_haymaker/knowledge_worker/endpoints/cloud_pc.py

from msgraph.graph_service_client import GraphServiceClient

class Windows365CloudPCManager:
    """Provisions and manages Windows 365 Cloud PCs for workers.

    Uses Graph API Beta endpoint for Cloud PC management:
    - Provisioning policies
    - Device provisioning
    - User assignment
    """

    PROVISIONING_POLICY_NAME = "HayMaker-KnowledgeWorker-Policy"

    def __init__(
        self,
        graph_client: GraphServiceClient,
        run_id: str,
    ):
        self.graph_client = graph_client
        self.run_id = run_id

    async def ensure_provisioning_policy(
        self,
        display_name: str = PROVISIONING_POLICY_NAME,
        image_id: str = "MicrosoftWindowsDesktop_windows-ent-cpc_win11-22h2-ent-cpc-m365",
        sku_id: str = "CPC_S_2C_4GB_64GB",  # 2 vCPU, 4GB RAM, 64GB storage
    ) -> str:
        """Create or get provisioning policy for Cloud PCs."""

        # Check if policy exists
        policies = await self.graph_client.device_management.virtual_endpoint.provisioning_policies.get()

        existing = next(
            (p for p in (policies.value or []) if p.display_name == display_name),
            None
        )

        if existing:
            return existing.id

        # Create new policy
        policy = CloudPcProvisioningPolicy()
        policy.display_name = display_name
        policy.description = f"HayMaker Knowledge Worker Policy - Run {self.run_id}"
        policy.provisioning_type = "dedicated"
        policy.image_id = image_id
        policy.image_type = "gallery"
        policy.domain_join_configuration = {
            "type": "azureADJoin",  # Azure AD joined (no hybrid)
        }
        policy.microsoft_managed_desktop = None  # Not using MMD

        result = await self.graph_client.device_management.virtual_endpoint.provisioning_policies.post(policy)

        return result.id

    async def provision_cloud_pc(
        self,
        worker: WorkerIdentity,
        policy_id: str,
    ) -> str:
        """Provision a Cloud PC for a worker.

        Args:
            worker: Worker identity to assign Cloud PC
            policy_id: Provisioning policy ID

        Returns:
            Cloud PC ID
        """
        # Assign user to provisioning policy group
        # Cloud PCs are automatically provisioned when user is added to policy group

        # Get policy group
        policy = await self.graph_client.device_management.virtual_endpoint.provisioning_policies.by_cloud_pc_provisioning_policy_id(
            policy_id
        ).get()

        # Add user to assignment group
        # This triggers automatic provisioning

        # Note: In practice, provisioning takes 30-60 minutes
        # The framework should poll for status

        logger.info(
            f"Cloud PC provisioning initiated for worker: {worker.worker_id}"
        )

        return f"cloudpc-{worker.worker_id}"

    async def wait_for_provisioning(
        self,
        worker: WorkerIdentity,
        timeout_minutes: int = 90,
    ) -> bool:
        """Wait for Cloud PC to be provisioned and ready."""

        start_time = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)

        while datetime.now() - start_time < timeout:
            # Check provisioning status
            cloud_pcs = await self.graph_client.device_management.virtual_endpoint.cloud_p_cs.get(
                request_configuration={
                    "query_parameters": {
                        "filter": f"userPrincipalName eq '{worker.user_principal_name}'"
                    }
                }
            )

            if cloud_pcs.value:
                pc = cloud_pcs.value[0]
                if pc.status == "provisioned":
                    logger.info(f"Cloud PC ready for {worker.worker_id}")
                    return True
                elif pc.status in ["failed", "error"]:
                    logger.error(f"Cloud PC provisioning failed for {worker.worker_id}")
                    return False

            await asyncio.sleep(60)  # Check every minute

        logger.warning(f"Cloud PC provisioning timeout for {worker.worker_id}")
        return False

    async def delete_cloud_pc(
        self,
        cloud_pc_id: str,
    ) -> bool:
        """Delete a Cloud PC."""
        try:
            await self.graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id(
                cloud_pc_id
            ).delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete Cloud PC {cloud_pc_id}: {e}")
            return False
```

### 6.3 CLI Container Deployment

```python
# src/azure_haymaker/knowledge_worker/endpoints/cli_container.py

from azure_haymaker.orchestrator.container_deployer import ContainerDeployer

class M365CLIContainerManager:
    """Manages M365 CLI containers for knowledge worker activity.

    Each container runs M365 CLI (PnP) with certificate authentication,
    executing worker activities via Graph API calls.
    """

    CONTAINER_IMAGE = "haymakerorchacr.azurecr.io/kw-m365-cli:latest"

    def __init__(
        self,
        config: OrchestratorConfig,
        run_id: str,
    ):
        self.config = config
        self.run_id = run_id
        self.deployer = ContainerDeployer(config)

    async def deploy_worker_container(
        self,
        worker: WorkerIdentity,
        activity_config: WorkerConfig,
    ) -> str:
        """Deploy a container for a knowledge worker.

        The container runs M365 CLI with:
        - Certificate authentication
        - Worker identity configuration
        - Activity schedule

        Args:
            worker: Worker identity
            activity_config: Activity patterns for this worker

        Returns:
            Container App resource ID
        """

        container_name = f"kw-{self.run_id[:8]}-{worker.worker_id}"

        # Build environment variables
        env_vars = {
            "WORKER_ID": worker.worker_id,
            "WORKER_UPN": worker.user_principal_name,
            "WORKER_DEPARTMENT": worker.department,
            "WORKER_PERSONA": worker.persona.value,
            "TEAM_IDS": ",".join(worker.team_ids),
            "M365_APP_ID": self.config.m365_app_client_id,
            "M365_TENANT_ID": self.config.target_tenant_id,
            # Certificate mounted from Key Vault
            "M365_CERT_PATH": "/secrets/m365-cert.pem",
            # Activity configuration
            "EMAIL_PER_HOUR": str(activity_config.email_per_hour),
            "TEAMS_MESSAGES_PER_HOUR": str(activity_config.teams_messages_per_hour),
            "DOCUMENTS_PER_DAY": str(activity_config.documents_per_day),
            "MEETINGS_PER_DAY": str(activity_config.meetings_per_day),
            "WORK_START_HOUR": str(activity_config.work_start_hour),
            "WORK_END_HOUR": str(activity_config.work_end_hour),
        }

        # Deploy container
        resource_id = await self._deploy_container_app(
            name=container_name,
            image=self.CONTAINER_IMAGE,
            env_vars=env_vars,
            cpu="0.25",
            memory="0.5Gi",
        )

        logger.info(
            f"CLI container deployed for worker: {worker.worker_id} -> {resource_id}"
        )

        return resource_id

    async def deploy_batch(
        self,
        workers: list[tuple[WorkerIdentity, WorkerConfig]],
        max_parallel: int = 10,
    ) -> list[str]:
        """Deploy containers for multiple workers in parallel."""

        resource_ids = []

        # Deploy in batches
        for i in range(0, len(workers), max_parallel):
            batch = workers[i:i + max_parallel]

            tasks = [
                self.deploy_worker_container(worker, config)
                for worker, config in batch
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, str):
                    resource_ids.append(result)
                else:
                    logger.error(f"Container deployment failed: {result}")

        return resource_ids
```

### 6.4 Container Image Specification

The M365 CLI container image:

```dockerfile
# Dockerfile for kw-m365-cli

FROM mcr.microsoft.com/azure-cli:latest

# Install Node.js (required for M365 CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install M365 CLI (PnP)
RUN npm install -g @pnp/cli-microsoft365

# Install Python dependencies
RUN pip install azure-identity msgraph-sdk aiohttp

# Copy worker activity script
COPY worker_activity.py /app/worker_activity.py
COPY activity_scheduler.py /app/activity_scheduler.py

WORKDIR /app

# Run activity scheduler
CMD ["python", "activity_scheduler.py"]
```

---

## 7. Communication Safety Controls

### 7.1 Defense in Depth

The framework implements multiple layers of safety controls to ensure NO external communications:

```
Layer 1: Exchange Transport Rules (Server-side)
    |
    v
Layer 2: Agent-Level Validation (Application)
    |
    v
Layer 3: Allowed Recipient List (Runtime)
    |
    v
Layer 4: Graph API Permissions (API Scope)
```

### 7.2 Exchange Transport Rules

```python
# src/azure_haymaker/knowledge_worker/identity/transport_rules.py

class TransportRuleManager:
    """Manages Exchange Online transport rules for internal-only mail."""

    RULE_NAME_PATTERN = "HayMaker-{run_id}-InternalOnly"

    async def create_internal_only_rule(
        self,
        run_id: str,
        worker_group_id: str,
    ) -> str:
        """Create transport rule blocking external email for workers.

        This rule:
        1. Applies to all users in the worker security group
        2. Blocks outbound email to external recipients
        3. Allows email only within the organization

        Args:
            run_id: HayMaker run ID
            worker_group_id: Security group containing all workers

        Returns:
            Rule ID
        """

        rule_name = self.RULE_NAME_PATTERN.format(run_id=run_id[:8])

        # Use Exchange Online PowerShell via Graph API
        # This creates a mail flow rule (transport rule)

        rule_definition = {
            "name": rule_name,
            "comments": f"HayMaker Knowledge Worker internal-only rule - {run_id}",
            "priority": 0,  # Highest priority
            "enabled": True,
            "conditions": {
                # Apply to messages from the worker group
                "senderMemberOf": [worker_group_id],
                # Going to external recipients
                "recipientDomainIs": ["!*"],  # Not internal domain
            },
            "actions": {
                # Block and notify sender
                "rejectMessage": {
                    "enhancedStatusCode": "5.7.1",
                    "rejectReason": "External email blocked for HayMaker workers",
                },
            },
            "exceptions": {
                # Allow internal domain
                "recipientDomainIs": [self.tenant_domain],
            },
        }

        # Note: Actual implementation uses Exchange Online PowerShell module
        # or Security & Compliance Center API

        logger.info(f"Created transport rule: {rule_name}")

        return rule_name

    async def verify_rule_active(self, rule_name: str) -> bool:
        """Verify transport rule is active and enforcing."""
        # Query Exchange Online for rule status
        pass

    async def delete_rule(self, rule_name: str) -> bool:
        """Delete transport rule during cleanup."""
        pass
```

### 7.3 Agent-Level Validation

Every M365 operation validates recipients before execution:

```python
class CommunicationValidator:
    """Validates all communications are internal-only."""

    def __init__(
        self,
        tenant_domain: str,
        allowed_upns: set[str],
    ):
        self.tenant_domain = tenant_domain.lower()
        self.allowed_upns = {upn.lower() for upn in allowed_upns}

    def is_internal(self, recipient: str) -> bool:
        """Check if recipient is internal to the tenant."""
        recipient = recipient.lower().strip()

        # Check if in allowed list
        if recipient in self.allowed_upns:
            return True

        # Check domain
        if "@" in recipient:
            domain = recipient.split("@")[1]
            return domain == self.tenant_domain

        return False

    def filter_recipients(self, recipients: list[str]) -> list[str]:
        """Filter list to only internal recipients."""
        return [r for r in recipients if self.is_internal(r)]

    def validate_or_raise(self, recipients: list[str]) -> None:
        """Validate recipients or raise exception."""
        external = [r for r in recipients if not self.is_internal(r)]
        if external:
            raise ExternalRecipientError(
                f"External recipients blocked: {external}"
            )
```

### 7.4 Allowed Recipient List

At runtime, each worker loads the complete list of valid internal recipients:

```python
async def load_allowed_recipients(
    graph_client: GraphServiceClient,
    run_id: str,
) -> set[str]:
    """Load all allowed internal recipients for this run.

    Returns:
        Set of lowercase email addresses/UPNs allowed as recipients
    """
    allowed = set()

    # 1. Load all workers in this run
    workers = await list_workers_for_run(graph_client, run_id)
    for worker in workers:
        allowed.add(worker.user_principal_name.lower())

    # 2. Load team shared mailboxes
    teams = await list_teams_for_run(graph_client, run_id)
    for team in teams:
        if team.shared_mailbox:
            allowed.add(team.shared_mailbox.lower())

    # 3. Add any distribution groups
    groups = await list_groups_for_run(graph_client, run_id)
    for group in groups:
        if group.mail:
            allowed.add(group.mail.lower())

    return allowed
```

---

## 8. Resource Tracking and Cleanup

### 8.1 Tagging Convention

All resources are tagged for tracking and cleanup:

| Tag Key | Value | Purpose |
|---------|-------|---------|
| `AzureHayMaker-managed` | `true` | Identifies managed resources |
| `RunId` | `{uuid}` | Associates with specific run |
| `Component` | `knowledge-worker` | Identifies framework |
| `WorkerId` | `{worker_id}` | Worker association |
| `Department` | `{dept}` | Department grouping |
| `TeamId` | `{team_id}` | Team association |
| `CreatedAt` | `{iso_timestamp}` | Creation timestamp |

### 8.2 Resource Inventory

```python
# src/azure_haymaker/knowledge_worker/cleanup/cleanup_manager.py

class KnowledgeWorkerResourceInventory:
    """Tracks all resources created by the Knowledge Worker framework."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.resources: dict[str, list[str]] = {
            "entra_users": [],
            "security_groups": [],
            "m365_groups": [],
            "teams_teams": [],
            "cloud_pcs": [],
            "container_apps": [],
            "transport_rules": [],
            "sharepoint_sites": [],
        }

    def register(self, resource_type: str, resource_id: str) -> None:
        """Register a created resource."""
        if resource_type in self.resources:
            self.resources[resource_type].append(resource_id)

    def get_all(self) -> dict[str, list[str]]:
        """Get all registered resources."""
        return self.resources.copy()

    def to_json(self) -> str:
        """Serialize inventory to JSON for storage."""
        return json.dumps({
            "run_id": self.run_id,
            "resources": self.resources,
            "created_at": datetime.now(UTC).isoformat(),
        })

    @classmethod
    def from_json(cls, data: str) -> "KnowledgeWorkerResourceInventory":
        """Deserialize from JSON."""
        parsed = json.loads(data)
        inventory = cls(parsed["run_id"])
        inventory.resources = parsed["resources"]
        return inventory
```

### 8.3 Cleanup Manager

```python
class KnowledgeWorkerCleanupManager:
    """Manages cleanup of all Knowledge Worker resources.

    Cleanup order (reverse of creation):
    1. Stop container apps
    2. Delete container apps
    3. Delete Cloud PCs
    4. Remove transport rules
    5. Delete Teams teams
    6. Delete M365 groups
    7. Delete security groups
    8. Delete Entra users
    """

    def __init__(
        self,
        graph_client: GraphServiceClient,
        container_client: ContainerAppsAPIClient,
        run_id: str,
    ):
        self.graph_client = graph_client
        self.container_client = container_client
        self.run_id = run_id

    async def cleanup_all(
        self,
        inventory: KnowledgeWorkerResourceInventory,
    ) -> CleanupReport:
        """Clean up all resources in the inventory.

        Args:
            inventory: Resource inventory from the run

        Returns:
            CleanupReport with results
        """
        report = CleanupReport(run_id=self.run_id)

        # 1. Stop and delete container apps
        for container_id in inventory.resources.get("container_apps", []):
            result = await self._delete_container_app(container_id)
            report.record(container_id, result)

        # 2. Delete Cloud PCs
        for cloud_pc_id in inventory.resources.get("cloud_pcs", []):
            result = await self._delete_cloud_pc(cloud_pc_id)
            report.record(cloud_pc_id, result)

        # 3. Remove transport rules
        for rule_name in inventory.resources.get("transport_rules", []):
            result = await self._delete_transport_rule(rule_name)
            report.record(rule_name, result)

        # 4. Delete Teams teams
        for team_id in inventory.resources.get("teams_teams", []):
            result = await self._delete_teams_team(team_id)
            report.record(team_id, result)

        # 5. Delete M365 groups
        for group_id in inventory.resources.get("m365_groups", []):
            result = await self._delete_m365_group(group_id)
            report.record(group_id, result)

        # 6. Delete security groups
        for group_id in inventory.resources.get("security_groups", []):
            result = await self._delete_security_group(group_id)
            report.record(group_id, result)

        # 7. Delete Entra users (last, as they may own resources)
        for user_id in inventory.resources.get("entra_users", []):
            result = await self._delete_entra_user(user_id)
            report.record(user_id, result)

        return report

    async def _delete_entra_user(self, user_id: str) -> bool:
        """Delete Entra user with retry logic."""
        try:
            await self.graph_client.users.by_user_id(user_id).delete()
            logger.info(f"Deleted Entra user: {user_id}")
            return True
        except ResourceNotFoundError:
            # Already deleted
            return True
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    async def _delete_cloud_pc(self, cloud_pc_id: str) -> bool:
        """Delete Windows 365 Cloud PC."""
        try:
            await self.graph_client.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id(
                cloud_pc_id
            ).delete()
            logger.info(f"Deleted Cloud PC: {cloud_pc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Cloud PC {cloud_pc_id}: {e}")
            return False
```

### 8.4 Orphan Resource Detection

```python
async def detect_orphan_resources(
    graph_client: GraphServiceClient,
    expected_run_ids: list[str],
) -> list[Resource]:
    """Detect orphaned Knowledge Worker resources.

    Finds resources that:
    1. Have HayMaker tags
    2. Don't belong to any known run

    Used for cleanup verification and leak detection.
    """
    orphans = []

    # Query users with HayMaker naming pattern
    users = await graph_client.users.get(
        request_configuration={
            "query_parameters": {
                "filter": "startswith(mailNickname, 'kw-')"
            }
        }
    )

    for user in (users.value or []):
        # Extract run ID from naming convention
        parts = user.mail_nickname.split("-")
        if len(parts) >= 2:
            run_id = parts[1]
            if run_id not in expected_run_ids:
                orphans.append(Resource(
                    resource_id=user.id,
                    resource_type="entra_user",
                    resource_name=user.display_name,
                ))

    return orphans
```

---

## 9. Execution Model

### 9.1 Workflow Orchestration

```
+------------------------------------------------------------------------------+
|                    Knowledge Worker Orchestration Workflow                   |
+------------------------------------------------------------------------------+
|                                                                              |
|  Phase 1: Setup (30 minutes)                                                 |
|  +------------------------------------------------------------------------+  |
|  | - Create HayMaker app registration (if not exists)                     |  |
|  | - Upload certificate to Key Vault                                      |  |
|  | - Create "all-workers" security group                                  |  |
|  | - Create transport rule blocking external email                        |  |
|  +------------------------------------------------------------------------+  |
|                                    |                                         |
|                                    v                                         |
|  Phase 2: Identity Provisioning (15 minutes)                                 |
|  +------------------------------------------------------------------------+  |
|  | - Create Entra users for each worker                                   |  |
|  | - Create security groups for each team                                 |  |
|  | - Add workers to team groups                                           |  |
|  | - Create M365 unified groups for Teams                                 |  |
|  +------------------------------------------------------------------------+  |
|                                    |                                         |
|                                    v                                         |
|  Phase 3: Endpoint Provisioning (60-90 minutes)                             |
|  +------------------------------------------------------------------------+  |
|  | - Provision Cloud PCs for designated workers (parallel)                |  |
|  | - Deploy CLI containers for remaining workers (parallel)               |  |
|  | - Wait for all endpoints to be ready                                   |  |
|  +------------------------------------------------------------------------+  |
|                                    |                                         |
|                                    v                                         |
|  Phase 4: Activity Execution (8+ hours)                                      |
|  +------------------------------------------------------------------------+  |
|  | - Workers execute activities based on persona                          |  |
|  | - Activity scheduler manages timing and variation                      |  |
|  | - Periodic health checks                                               |  |
|  | - Telemetry collection                                                 |  |
|  +------------------------------------------------------------------------+  |
|                                    |                                         |
|                                    v                                         |
|  Phase 5: Cleanup (30 minutes)                                              |
|  +------------------------------------------------------------------------+  |
|  | - Stop all containers                                                  |  |
|  | - Deprovision Cloud PCs                                                |  |
|  | - Remove transport rules                                               |  |
|  | - Delete groups and users                                              |  |
|  | - Verify cleanup complete                                              |  |
|  +------------------------------------------------------------------------+  |
|                                                                              |
+------------------------------------------------------------------------------+
```

### 9.2 Activity Scheduler

```python
# src/azure_haymaker/knowledge_worker/scheduler.py

class ActivityScheduler:
    """Schedules and executes worker activities over time.

    Features:
    - Configurable activity frequencies
    - Working hours awareness
    - Random variation for realism
    - Rate limiting for API protection
    """

    def __init__(
        self,
        worker: WorkerIdentity,
        config: WorkerConfig,
        operations: dict[str, M365OperationBase],
    ):
        self.worker = worker
        self.config = config
        self.operations = operations
        self._running = False

    async def run(self, duration_hours: int = 8) -> ActivityReport:
        """Run activity scheduler for specified duration.

        Args:
            duration_hours: How long to run activities

        Returns:
            ActivityReport with execution statistics
        """
        self._running = True
        end_time = datetime.now() + timedelta(hours=duration_hours)
        report = ActivityReport(worker_id=self.worker.worker_id)

        while self._running and datetime.now() < end_time:
            # Check if within working hours
            if not self._is_working_hours():
                await asyncio.sleep(300)  # Check every 5 minutes
                continue

            # Schedule next activities
            activities = self._plan_next_hour()

            for activity in activities:
                if not self._running:
                    break

                try:
                    result = await self._execute_activity(activity)
                    report.record_success(activity.type, result)
                except Exception as e:
                    report.record_failure(activity.type, str(e))

                # Wait for next activity
                await asyncio.sleep(activity.wait_seconds)

        return report

    def _plan_next_hour(self) -> list[PlannedActivity]:
        """Plan activities for the next hour."""
        activities = []

        # Add email activities
        email_count = self._vary_count(self.config.email_per_hour)
        for _ in range(email_count):
            activities.append(PlannedActivity(
                type="email",
                action=random.choice(["send", "read", "reply", "organize"]),
                wait_seconds=random.randint(60, 3600 // email_count),
            ))

        # Add Teams activities
        teams_count = self._vary_count(self.config.teams_messages_per_hour)
        for _ in range(teams_count):
            activities.append(PlannedActivity(
                type="teams",
                action=random.choice(["channel_post", "chat", "reply", "react"]),
                wait_seconds=random.randint(30, 3600 // teams_count),
            ))

        # Shuffle for natural distribution
        random.shuffle(activities)

        return activities

    def _vary_count(self, base: int) -> int:
        """Apply random variation to activity count."""
        variance = self.config.activity_variance_percent / 100
        min_count = int(base * (1 - variance))
        max_count = int(base * (1 + variance))
        return random.randint(min_count, max_count)

    def _is_working_hours(self) -> bool:
        """Check if current time is within working hours."""
        current_hour = datetime.now(UTC).hour
        return self.config.work_start_hour <= current_hour < self.config.work_end_hour
```

### 9.3 Concurrency Model

```python
class KnowledgeWorkerOrchestrator:
    """Orchestrates multiple knowledge workers concurrently.

    Manages:
    - Worker lifecycle (start, monitor, stop)
    - Resource allocation
    - Rate limiting across workers
    - Health monitoring
    """

    MAX_CONCURRENT_WORKERS = 50
    HEALTH_CHECK_INTERVAL = 300  # 5 minutes

    async def run_workers(
        self,
        workers: list[tuple[WorkerIdentity, WorkerConfig]],
        duration_hours: int = 8,
    ) -> OrchestratorReport:
        """Run all workers concurrently.

        Args:
            workers: List of (identity, config) tuples
            duration_hours: Execution duration

        Returns:
            Aggregated report from all workers
        """
        report = OrchestratorReport()

        # Create worker tasks
        tasks = []
        for worker, config in workers:
            task = asyncio.create_task(
                self._run_single_worker(worker, config, duration_hours)
            )
            tasks.append(task)

            # Rate limit worker starts
            await asyncio.sleep(1)

        # Wait for all workers with health monitoring
        health_task = asyncio.create_task(
            self._health_monitor(tasks)
        )

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        health_task.cancel()

        # Aggregate reports
        for result in results:
            if isinstance(result, ActivityReport):
                report.add_worker_report(result)
            else:
                report.add_error(str(result))

        return report

    async def _health_monitor(
        self,
        tasks: list[asyncio.Task],
    ) -> None:
        """Monitor worker health and restart failed workers."""
        while True:
            await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)

            for task in tasks:
                if task.done() and task.exception():
                    logger.error(f"Worker task failed: {task.exception()}")
                    # Could implement restart logic here
```

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

- [ ] Create `knowledge_worker/` module structure
- [ ] Implement `KnowledgeWorkerAgent` base class
- [ ] Implement core models (WorkerIdentity, Team, WorkerConfig)
- [ ] Implement `EntraUserManager` for user provisioning
- [ ] Implement `EntraGroupManager` for security groups
- [ ] Unit tests for all foundation components

### Phase 2: M365 Operations (Week 3-4)

- [ ] Implement `EmailOperations` class
- [ ] Implement `TeamsOperations` class
- [ ] Implement `DocumentOperations` class
- [ ] Implement `CalendarOperations` class
- [ ] Implement `CommunicationValidator`
- [ ] Integration tests with M365 tenant

### Phase 3: Endpoint Layer (Week 5-6)

- [ ] Implement `M365CLIContainerManager`
- [ ] Create M365 CLI container image
- [ ] Implement `Windows365CloudPCManager`
- [ ] Implement `EndpointManager` coordination
- [ ] Test endpoint provisioning workflows

### Phase 4: Orchestration (Week 7-8)

- [ ] Implement `ActivityScheduler`
- [ ] Implement `KnowledgeWorkerOrchestrator`
- [ ] Implement workflow phases (setup, provision, execute, cleanup)
- [ ] Integrate with existing HayMaker orchestrator
- [ ] Implement transport rule management

### Phase 5: Testing & Hardening (Week 9-10)

- [ ] End-to-end testing with 50 workers
- [ ] Scale testing with 300 workers
- [ ] Security audit of communication controls
- [ ] Performance optimization
- [ ] Documentation and runbooks

---

## Appendix A: API Reference

### Configuration Schema

```yaml
# knowledge-worker-config.yaml

name: "production-kw-deployment"
run_id: "${RUN_ID}"  # Auto-generated or specified

tenant:
  tenant_id: "${AZURE_TENANT_ID}"
  domain: "haymakertenant.onmicrosoft.com"

m365_app:
  client_id: "${M365_APP_CLIENT_ID}"
  certificate_thumbprint: "${M365_CERT_THUMBPRINT}"

deployment:
  total_workers: 100
  endpoint_budget:
    cloud_pc: 10
    cli_container: 90

departments:
  executive:
    weight: 5
    endpoint_type: cloud_pc
    activity:
      email_per_hour: 8
      teams_per_hour: 5

  engineering:
    weight: 30
    endpoint_type: cli_container
    activity:
      email_per_hour: 4
      teams_per_hour: 15

# ... additional departments

cross_team_rules:
  executive: [engineering, sales, hr]
  engineering: [executive, operations]
  # ...

safety:
  transport_rule_enabled: true
  validate_recipients: true
  block_external: true

cleanup:
  auto_cleanup: true
  cleanup_delay_minutes: 30
```

### CLI Commands

```bash
# Initialize a new Knowledge Worker deployment
haymaker kw init --config knowledge-worker-config.yaml

# Provision workers (identities only)
haymaker kw provision --run-id abc12345

# Start worker activity
haymaker kw start --run-id abc12345 --duration 8h

# Monitor running workers
haymaker kw status --run-id abc12345

# Stop workers
haymaker kw stop --run-id abc12345

# Cleanup all resources
haymaker kw cleanup --run-id abc12345 --force

# List orphaned resources
haymaker kw list-orphans
```

---

## Appendix B: Cost Estimates

### Monthly Cost Breakdown (100 Workers)

| Component | Quantity | Unit Cost | Monthly Total |
|-----------|----------|-----------|---------------|
| Windows 365 Cloud PC (2vCPU/4GB) | 10 | $31/user | $310 |
| Container Apps (0.25 vCPU) | 90 | ~$3/container | $270 |
| Entra ID P1 (for dynamic groups) | 100 | $6/user | $600 |
| Container Registry | 1 | $5 | $5 |
| Key Vault | 1 | ~$1 | $1 |
| **Total** | | | **~$1,186/month** |

### Cost Optimization Strategies

1. **Use spot containers** for CLI workers when available
2. **Auto-scale Cloud PCs** to zero during non-working hours
3. **Batch deployments** during off-peak to reduce provisioning time
4. **Share Entra P1 licenses** with existing organization licenses

---

## Appendix C: Security Considerations

### Threat Model

| Threat | Mitigation |
|--------|------------|
| External email leak | Transport rules + agent validation + allowed list |
| Credential exposure | Certificate auth, Key Vault secrets, no passwords in code |
| Resource persistence | Tag-based cleanup, orphan detection, forced cleanup |
| Privilege escalation | Scoped permissions, dedicated app registration |
| Cross-tenant access | Tenant-bound app registration, single-tenant mode |

### Security Checklist

- [ ] Transport rule blocks all external email
- [ ] All recipients validated against internal list
- [ ] Certificate authentication (no client secrets in containers)
- [ ] All resources tagged for cleanup
- [ ] Orphan detection runs daily
- [ ] App registration uses least-privilege permissions
- [ ] Audit logs enabled for M365 operations
- [ ] Network isolation for CLI containers (VNet integration)

---

## References

1. [Microsoft Graph API - Users](https://learn.microsoft.com/en-us/graph/api/resources/user)
2. [Microsoft Graph API - Groups](https://learn.microsoft.com/en-us/graph/api/resources/group)
3. [Microsoft Graph API - Teams](https://learn.microsoft.com/en-us/graph/api/resources/team)
4. [Windows 365 Graph API](https://learn.microsoft.com/en-us/graph/api/resources/cloudpc)
5. [M365 CLI (PnP)](https://pnp.github.io/cli-microsoft365/)
6. [Exchange Online Transport Rules](https://learn.microsoft.com/en-us/exchange/security-and-compliance/mail-flow-rules/mail-flow-rules)
7. [Azure HayMaker Architecture](/home/azureuser/src/h2/docs/ARCHITECTURE.md)
