# Windows 365 Cloud PC Provisioning with Magentic-UI Computer Use Agent

## Executive Summary

This specification defines a complete, production-ready architecture for provisioning Windows 365 Cloud PCs with Magentic-UI computer use agent deployment. The system integrates:

1. **W365 Graph API Management** - Cloud PC provisioning via Microsoft Graph API (deviceManagement/virtualEndpoint)
2. **Magentic-UI Agent Setup** - Automated deployment of computer use agents on provisioned Cloud PCs
3. **Teams Integration** - Dynamic team/channel creation and message posting for activity tracking
4. **Browser Automation Testing** - Comprehensive E2E test scenarios for agent capabilities

### Core Design Philosophy

- **Zero-BS Implementation**: All components perform real work, no stubs or placeholders
- **Modular Bricks**: Single-responsibility components with clean contracts
- **Production-Ready**: Error handling, timeouts, retry logic, and comprehensive logging
- **Cost-Optimized**: Efficient resource allocation and cleanup

---

## 1. System Architecture

### 1.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (Main Entry Point)                        │
│                                                                           │
│  ┌───────────────┐  ┌─────────────────┐  ┌────────────────────────┐   │
│  │ 1. Validation │→ │ 2. W365 Setup   │→ │ 3. Agent Deploy       │   │
│  │ - Credentials │  │ - Policies      │  │ - Magentic-UI setup   │   │
│  │ - Quotas      │  │ - Provisioning  │  │ - Automation scripts  │   │
│  │ - Permissions │  │ - User assign   │  │ - Verify readiness    │   │
│  └───────────────┘  └─────────────────┘  └────────┬─────────────┘   │
│                                                     │                  │
│  ┌────────────────────────────────────────────────────┐              │
│  │ 4. Teams Integration (Parallel)                    │              │
│  │ - Create teams/channels                            │              │
│  │ - Configure team owners                            │              │
│  │ - Post deployment messages                         │              │
│  └────────────────────────────────────────────────────┘              │
│                                                     │                  │
│  ┌────────────────────────────────────────────────────┐              │
│  │ 5. E2E Testing (Parallel)                          │              │
│  │ - Browser automation                               │              │
│  │ - Agent capability validation                      │              │
│  │ - Generate test reports                            │              │
│  └────────────────────────────────────────────────────┘              │
│                                                     │                  │
│  ┌────────────────────────────────────────────────────┐              │
│  │ 6. Monitoring & Cleanup (On-Demand)                │              │
│  │ - Health checks                                    │              │
│  │ - Resource cleanup                                 │              │
│  │ - Cost optimization                                │              │
│  └────────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE WORKER ECOSYSTEM                             │
│                                                                           │
│  ┌──────────────────────┐  ┌──────────────────────┐                   │
│  │ KnowledgeWorkerAgent │  │ W365CloudPCManager   │                   │
│  │                      │  │                      │                   │
│  │ - M365 activities    │◄─┤ - Graph API mgmt     │                   │
│  │ - Email/Teams ops    │  │ - Provisioning      │                   │
│  │ - Calendar events    │  │ - Status tracking   │                   │
│  └──────────────────────┘  └──────┬───────────────┘                   │
│                                    │                                    │
│                                    v                                    │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                   W365 Setup Module                               │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │ │
│  │  │ Policy Manager   │  │ Provisioning     │  │ User Manager │  │ │
│  │  │                  │  │ Manager          │  │              │  │ │
│  │  │ - Create/get     │  │ - Track status   │  │ - Assign     │  │ │
│  │  │   policies       │  │ - Handle retries │  │ - Cleanup    │  │ │
│  │  │ - Manage SKUs    │  │ - Await ready    │  │ - Validate   │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│                                    v                                    │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              Magentic-UI Setup Module                             │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │ │
│  │  │ Bootstrap Config │  │ Agent Installer  │  │ PSRemoting   │  │ │
│  │  │                  │  │                  │  │ Setup        │  │ │
│  │  │ - Download pkg   │  │ - Copy files     │  │ - Enable     │  │ │
│  │  │ - Verify sigs    │  │ - Run scripts    │  │ - Verify     │  │ │
│  │  │ - Config files   │  │ - Start service  │  │ - Secure     │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│                                    v                                    │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              Teams Integration Module                             │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │ │
│  │  │ Team Manager     │  │ Channel Manager  │  │ Message      │  │ │
│  │  │                  │  │                  │  │ Poster       │  │ │
│  │  │ - Create team    │  │ - Standard chs   │  │ - Format     │  │ │
│  │  │ - Assign members │  │ - Custom chs     │  │ - Post       │  │ │
│  │  │ - Set policies   │  │ - Pinned msgs    │  │ - Validate   │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│                                    v                                    │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │            Browser Automation & E2E Testing Module               │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │ │
│  │  │ Selenium Manager │  │ Test Scenarios   │  │ Report Gen   │  │ │
│  │  │                  │  │                  │  │              │  │ │
│  │  │ - Connect to     │  │ - M365 access    │  │ - Metrics    │  │
│  │  │   Cloud PC       │  │ - Teams usage    │  │ - Screenshots│  │
│  │  │ - Navigate sites │  │ - Email ops      │  │ - JSON report│  │
│  │  │ - Verify actions │  │ - Calendar sync  │  │ - Artifacts  │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│                            ↓                                             │
│                   Microsoft Graph API                                   │
│                   Cloud PC endpoints                                    │
│                   Teams endpoints                                       │
│                   RDP/Remote Desktop                                    │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Specifications

### Module 1: W365 Cloud PC Manager (Enhanced)

**File**: `/src/azure_haymaker/provisioning/w365_manager.py`

#### Purpose
Orchestrates Windows 365 Cloud PC provisioning, policy management, and lifecycle operations via Microsoft Graph API.

#### Contract

**Inputs**:
- `graph_client`: Authenticated Microsoft Graph client
- `run_id`: Unique run identifier for resource tracking
- `policy_config`: CloudPCPolicyConfig with provisioning parameters
- `worker_identities`: List of WorkerIdentity objects to provision

**Outputs**:
- Cloud PC ID and status information
- Policy ID and configuration
- Provisioning status tracking

**Side Effects**:
- Creates/updates provisioning policies in W365
- Assigns users to provisioning policies (triggers async provisioning)
- Queries Graph API for status tracking
- Publishes provisioning events to Service Bus

#### Dependencies
- `msgraph.core.GraphServiceClient` - Microsoft Graph API client
- `azure_haymaker.knowledge_worker.models.worker` - WorkerIdentity models
- `azure.servicebus.ServiceBusClient` - Event publishing
- Standard Python: `asyncio`, `logging`, `dataclasses`

#### Key Design Decisions

1. **Async-First**: All I/O operations are async-compatible
2. **Policy Reuse**: Check for existing policies before creating new ones
3. **Timeout Handling**: 90-minute default provisioning timeout with configurable intervals
4. **Error Recovery**: Retry logic for transient failures, clear error propagation for permanent issues
5. **Stateless Design**: No internal state persistence; client orchestration manages flow

#### Public API

```python
class W365CloudPCManager:
    async def ensure_provisioning_policy(
        self,
        display_name: str | None = None,
        image_id: str | None = None,
        sku_id: str | None = None,
    ) -> str:
        """Get existing or create new provisioning policy."""

    async def provision_cloud_pc(
        self,
        worker: WorkerIdentity,
        policy_id: str,
    ) -> ProvisioningResult:
        """Assign user to policy (triggers async provisioning)."""

    async def wait_for_provisioning(
        self,
        worker: WorkerIdentity,
        timeout_minutes: int | None = None,
    ) -> ProvisioningStatus:
        """Poll for provisioning completion."""

    async def get_cloud_pc(
        self,
        worker: WorkerIdentity,
    ) -> CloudPCInfo | None:
        """Retrieve Cloud PC details."""

    async def list_cloud_pcs_for_run(self) -> list[CloudPCInfo]:
        """List all Cloud PCs for this run."""

    async def delete_cloud_pc(self, cloud_pc_id: str) -> bool:
        """Delete a Cloud PC."""
```

#### Test Requirements

- Unit tests for all async methods with mocked Graph client
- Integration tests against Graph API (beta endpoint)
- Timeout handling validation
- Error recovery and retry logic verification
- Policy reuse scenario testing
- Concurrent provisioning of multiple Cloud PCs

---

### Module 2: Magentic-UI Setup Manager

**File**: `/src/azure_haymaker/provisioning/magentic_ui_setup.py`

#### Purpose
Manages installation and configuration of Magentic-UI computer use agents on provisioned Cloud PCs via PowerShell remoting.

#### Contract

**Inputs**:
- `cloud_pc_info`: Cloud PC connection details (IP, hostname, credentials)
- `agent_config`: MagenticUIConfig with agent parameters
- `package_url`: Download URL for Magentic-UI package
- `deployment_id`: Unique deployment identifier

**Outputs**:
- Setup status (success/failure)
- Agent verification report
- Connection strings and endpoints
- Telemetry configuration

**Side Effects**:
- Establishes PowerShell remoting sessions to Cloud PC
- Downloads and installs Magentic-UI package
- Creates system services for agent startup
- Enables Windows features (RDP, PSRemoting, etc.)
- Configures agent configuration files
- Restarts services as needed

#### Dependencies
- `pypsrp` - PowerShell Remoting Protocol
- `azure.identity` - Azure credential management
- `requests` - Package downloads
- Standard Python: `asyncio`, `logging`, `tempfile`, `subprocess`

#### Key Design Decisions

1. **Remote PowerShell**: Use PSRemoting for OS-level operations
2. **Sequential Setup**: Boot order critical (enable features → install → configure → start)
3. **Fallback Mechanisms**: Retry failed connection attempts, exponential backoff
4. **Script Signing**: Verify package signatures before execution
5. **Idempotent Operations**: Can safely re-run setup without side effects

#### Public API

```python
class MagenticUISetupManager:
    async def bootstrap_cloud_pc(
        self,
        cloud_pc_info: CloudPCInfo,
    ) -> BootstrapResult:
        """Enable required Windows features and prepare for agent install."""

    async def install_agent(
        self,
        cloud_pc_info: CloudPCInfo,
        package_url: str,
        verify_signature: bool = True,
    ) -> InstallResult:
        """Download and install Magentic-UI agent package."""

    async def configure_agent(
        self,
        cloud_pc_info: CloudPCInfo,
        agent_config: MagenticUIConfig,
    ) -> ConfigResult:
        """Apply configuration and prepare for startup."""

    async def verify_agent_ready(
        self,
        cloud_pc_info: CloudPCInfo,
        timeout_seconds: int = 300,
    ) -> bool:
        """Verify agent is running and responsive."""

    async def cleanup_agent(
        self,
        cloud_pc_info: CloudPCInfo,
    ) -> bool:
        """Stop agent service and cleanup resources."""
```

#### Test Requirements

- PowerShell remoting connection validation
- Package download and signature verification
- Installation idempotency testing
- Configuration file generation and validation
- Service startup and health verification
- Error handling for unreachable Cloud PCs
- Cleanup procedure validation

---

### Module 3: Teams Integration Manager

**File**: `/src/azure_haymaker/provisioning/teams_manager.py`

#### Purpose
Creates Teams teams/channels and posts provisioning messages for deployment tracking and coordination.

#### Contract

**Inputs**:
- `graph_client`: Authenticated Microsoft Graph client
- `team_config`: TeamsConfig with team parameters
- `members`: List of member identities to add
- `deployment_info`: Deployment details for message content

**Outputs**:
- Created team ID and channel IDs
- Message post IDs (for future reference/updates)
- Team URL for member access

**Side Effects**:
- Creates new Teams team (if not exists)
- Creates standard and custom channels
- Adds members to team
- Posts formatted messages with deployment status
- Updates pinned messages as status changes

#### Dependencies
- `msgraph.core.GraphServiceClient` - Microsoft Graph API
- `azure_haymaker.knowledge_worker.models.team` - Team models
- Standard Python: `asyncio`, `logging`, `json`, `datetime`

#### Key Design Decisions

1. **Idempotent Team Creation**: Check for existing team by name before creating
2. **Rich Message Formatting**: Use adaptive cards for deployment status
3. **Channel Organization**: Separate channels for provisioning, testing, alerts
4. **Member Management**: Async bulk member addition with error handling
5. **Message Threading**: Group related updates in message threads

#### Public API

```python
class TeamsManager:
    async def ensure_team_exists(
        self,
        team_name: str,
        description: str | None = None,
    ) -> str:
        """Get existing or create new team."""

    async def create_channel(
        self,
        team_id: str,
        channel_name: str,
        description: str | None = None,
    ) -> str:
        """Create a channel in the team."""

    async def add_team_members(
        self,
        team_id: str,
        member_upns: list[str],
    ) -> AddMembersResult:
        """Add members to team."""

    async def post_deployment_message(
        self,
        team_id: str,
        channel_id: str,
        deployment_info: DeploymentInfo,
    ) -> str:
        """Post formatted deployment message."""

    async def update_provisioning_status(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        status: str,
        details: dict[str, Any],
    ) -> bool:
        """Update existing message with new status."""

    async def pin_message(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
    ) -> bool:
        """Pin important message to channel."""
```

#### Test Requirements

- Team creation and retrieval
- Duplicate team handling
- Channel creation with various configurations
- Member addition with error handling
- Message posting with rich formatting
- Message updates and pinning
- Error scenarios (invalid team/channel IDs, permission issues)

---

### Module 4: Browser Automation Testing Module

**File**: `/src/azure_haymaker/testing/browser_automation.py`

#### Purpose
Executes automated E2E test scenarios on provisioned Cloud PCs using Selenium, validating Magentic-UI agent capabilities and M365 integrations.

#### Contract

**Inputs**:
- `cloud_pc_info`: Cloud PC connection details (RDP endpoint)
- `test_scenarios`: List of BrowserTestScenario objects
- `timeout_seconds`: Test execution timeout

**Outputs**:
- Test results (pass/fail/error for each scenario)
- Screenshots of key states
- Execution logs and metrics
- JSON test report

**Side Effects**:
- Establishes RDP connection to Cloud PC
- Launches Chrome/Edge browser instances
- Navigates to M365 applications
- Performs automated interactions (clicks, typing, waits)
- Captures screenshots on key events
- Collects performance metrics

#### Dependencies
- `selenium.webdriver` - Browser automation
- `pyautogui` - GUI automation fallback
- `Pillow` - Screenshot capture
- `requests` - API calls for validation
- Standard Python: `asyncio`, `logging`, `json`, `time`

#### Key Design Decisions

1. **Headless Where Possible**: Run Chrome in headless mode for performance
2. **Explicit Waits**: Use explicit waits instead of hardcoded sleeps
3. **Screenshot on Failure**: Capture state when tests fail
4. **Scenario Composition**: Build complex scenarios from simple, reusable steps
5. **Performance Tracking**: Measure page load times, action latencies

#### Public API

```python
class BrowserAutomationTester:
    async def connect_to_cloud_pc(
        self,
        cloud_pc_info: CloudPCInfo,
    ) -> bool:
        """Establish RDP connection to Cloud PC."""

    async def run_test_scenario(
        self,
        scenario: BrowserTestScenario,
    ) -> TestResult:
        """Execute a single test scenario."""

    async def run_all_scenarios(
        self,
        scenarios: list[BrowserTestScenario],
    ) -> TestSuiteResult:
        """Execute all scenarios and collect results."""

    async def verify_m365_access(self) -> M365AccessResult:
        """Test: Access M365 portal and verify authentication."""

    async def verify_teams_chat(self) -> TeamsChatResult:
        """Test: Send Teams chat message and verify delivery."""

    async def verify_email_access(self) -> EmailAccessResult:
        """Test: Access Outlook and retrieve recent emails."""

    async def verify_sharepoint_sync(self) -> SharePointResult:
        """Test: Verify OneDrive sync and SharePoint access."""

    async def verify_agent_ui(self) -> AgentUIResult:
        """Test: Launch Magentic-UI agent UI and verify controls."""

    async def generate_test_report(
        self,
        results: TestSuiteResult,
        output_dir: Path,
    ) -> Path:
        """Generate JSON and HTML test reports."""

    async def disconnect_from_cloud_pc(self) -> bool:
        """Close RDP connection and cleanup."""
```

#### Test Scenarios (Implemented)

1. **M365 Portal Access**
   - Navigate to Office 365 home
   - Verify user identity
   - Check installed apps

2. **Teams Messaging**
   - Open Teams desktop client
   - Send test message
   - Verify message delivery

3. **Email Operations**
   - Open Outlook web
   - Check inbox count
   - Send test email
   - Verify in sent items

4. **SharePoint Sync**
   - Verify OneDrive sync status
   - Navigate to team SharePoint
   - Access shared documents

5. **Agent UI Verification**
   - Launch Magentic-UI agent UI
   - Verify all controls respond
   - Execute sample task
   - Verify logging

#### Test Requirements

- RDP connection stability
- Selenium WebDriver initialization
- Element location and interaction
- Wait strategy effectiveness
- Screenshot capture on events
- Error handling for missing elements
- Report generation with correct metrics
- Screenshot and log artifact collection

---

### Module 5: Provisioning Orchestrator

**File**: `/src/azure_haymaker/provisioning/orchestrator.py`

#### Purpose
High-level orchestrator coordinating W365 provisioning, agent setup, Teams integration, and E2E testing in correct sequence with proper error handling and rollback.

#### Contract

**Inputs**:
- `provisioning_config`: W365ProvisioningConfig (all settings)
- `workers`: List of WorkerIdentity objects to provision
- `credentials`: Service principal credentials

**Outputs**:
- Provisioning status report (JSON)
- Deployment manifest (all created resources)
- Test results summary
- Cost estimation for created resources

**Side Effects**:
- Coordinates all provisioning activities
- Publishes events to Service Bus
- Creates resources across Azure
- Modifies Cloud PC configurations
- Installs and configures agents
- Creates Teams teams/channels
- Executes E2E tests

#### Dependencies
- All above modules
- `azure.servicebus.ServiceBusClient` - Event publishing
- `azure_haymaker.knowledge_worker` - Worker models
- Standard Python: `asyncio`, `logging`, `json`, `datetime`

#### Key Design Decisions

1. **Orchestration Pattern**: Main orchestrator, parallel where safe (Teams + E2E testing)
2. **State Management**: Maintain provisioning manifest for rollback capability
3. **Event Publishing**: Emit events at key milestones
4. **Error Isolation**: Failure in testing doesn't block deployment
5. **Timeout Protection**: Absolute timeout for entire provisioning flow

#### Public API

```python
class ProvisioningOrchestrator:
    def __init__(self, config: W365ProvisioningConfig):
        """Initialize orchestrator with configuration."""

    async def validate_prerequisites(self) -> ValidationResult:
        """Check credentials, quotas, permissions."""

    async def provision_workers(
        self,
        workers: list[WorkerIdentity],
    ) -> ProvisioningReport:
        """Execute full provisioning workflow."""

    async def provision_single_worker(
        self,
        worker: WorkerIdentity,
    ) -> SingleWorkerProvisioningResult:
        """Provision one worker (reusable component)."""

    async def run_e2e_tests(
        self,
        deployment_manifest: DeploymentManifest,
    ) -> TestSuiteResult:
        """Execute E2E tests on provisioned infrastructure."""

    async def publish_deployment_report(
        self,
        report: ProvisioningReport,
    ) -> bool:
        """Post report to Teams and Service Bus."""

    async def cleanup_failed_deployments(
        self,
        failed_workers: list[str],
    ) -> CleanupResult:
        """Rollback resources for failed workers."""

    async def get_provisioning_status(
        self,
        run_id: str,
    ) -> ProvisioningStatus:
        """Query current provisioning status."""
```

#### Flow (Sequence Diagram)

```
User / Orchestrator
    │
    ├─► validate_prerequisites()
    │       │
    │       ├─ Check graph_client auth
    │       ├─ Verify quota limits
    │       ├─ Check W365 licenses
    │       └─ Return: ValidationResult
    │
    ├─► provision_workers(worker_list)
    │       │
    │       ├─ Parallel: For each worker
    │       │       │
    │       │       ├─ ensure_provisioning_policy()
    │       │       │   │
    │       │       │   ├─ Check existing policies
    │       │       │   ├─ Create if needed
    │       │       │   └─ Return: policy_id
    │       │       │
    │       │       ├─ provision_cloud_pc()
    │       │       │   │
    │       │       │   ├─ Assign user to policy
    │       │       │   └─ Return: assignment_result
    │       │       │
    │       │       ├─ wait_for_provisioning()
    │       │       │   │
    │       │       │   ├─ Poll Graph API (every 60s)
    │       │       │   ├─ Timeout: 90 minutes
    │       │       │   └─ Return: ready_status
    │       │       │
    │       │       ├─ bootstrap_cloud_pc()
    │       │       │   │
    │       │       │   ├─ Enable Windows features
    │       │       │   ├─ Setup PSRemoting
    │       │       │   └─ Return: bootstrap_result
    │       │       │
    │       │       ├─ install_agent()
    │       │       │   │
    │       │       │   ├─ Download package
    │       │       │   ├─ Verify signature
    │       │       │   ├─ Run installer
    │       │       │   └─ Return: install_result
    │       │       │
    │       │       ├─ configure_agent()
    │       │       │   │
    │       │       │   ├─ Write config files
    │       │       │   ├─ Set environment vars
    │       │       │   └─ Return: config_result
    │       │       │
    │       │       ├─ verify_agent_ready()
    │       │       │   │
    │       │       │   ├─ Check service status
    │       │       │   ├─ Verify connectivity
    │       │       │   └─ Return: ready_bool
    │       │       │
    │       │       └─ Add to successful_workers
    │       │           OR
    │       │           Add to failed_workers + store error
    │       │
    │       ├─ Parallel: Teams integration
    │       │       │
    │       │       ├─ ensure_team_exists()
    │       │       ├─ create_channel() × 3
    │       │       │   ├─ "provisioning-status"
    │       │       │   ├─ "agent-testing"
    │       │       │   └─ "alerts"
    │       │       │
    │       │       ├─ add_team_members()
    │       │       │
    │       │       └─ post_deployment_message()
    │       │
    │       ├─ Parallel: E2E Testing
    │       │       │
    │       │       ├─ run_all_scenarios()
    │       │       │   ├─ M365 portal access
    │       │       │   ├─ Teams chat
    │       │       │   ├─ Email operations
    │       │       │   ├─ SharePoint sync
    │       │       │   └─ Agent UI verification
    │       │       │
    │       │       └─ generate_test_report()
    │       │
    │       └─ Return: ProvisioningReport
    │
    ├─► publish_deployment_report()
    │       │
    │       ├─ Post to Teams
    │       ├─ Publish to Service Bus
    │       └─ Store manifest in Storage
    │
    └─ Complete with ProvisioningReport
```

#### Test Requirements

- Validation checks for missing credentials
- Quota limit enforcement
- Proper sequencing of provisioning steps
- Timeout enforcement at orchestrator level
- Rollback on partial failures
- Event publishing verification
- Report generation with correct metadata
- Error handling for transient and permanent failures

---

## 3. Data Models

### 3.1 Configuration Models

```python
# W365 Provisioning Configuration
@dataclass
class W365ProvisioningConfig:
    """Windows 365 provisioning parameters."""
    provisioning_policy_name: str
    image_id: str = "MicrosoftWindowsDesktop_windows-ent-cpc_win11-22h2-ent-cpc-m365"
    sku_id: str = "CPC_S_2C_4GB_64GB"
    provisioning_timeout_minutes: int = 90
    provisioning_check_interval_seconds: int = 60
    auto_assign_licenses: bool = True

# Magentic-UI Configuration
@dataclass
class MagenticUIConfig:
    """Magentic-UI agent configuration."""
    agent_version: str  # e.g., "1.0.0"
    package_url: str  # Download URL
    telemetry_enabled: bool = True
    logging_level: str = "INFO"
    api_endpoint: str = ""  # Agent control API
    max_concurrent_tasks: int = 5

# Teams Configuration
@dataclass
class TeamsConfig:
    """Teams integration configuration."""
    team_name: str
    team_description: str
    owner_upns: list[str]
    member_upns: list[str]
    channels: list[str] = field(default_factory=lambda: [
        "provisioning-status", "agent-testing", "alerts"
    ])

# Full Provisioning Configuration
@dataclass
class W365ProvisioningConfig:
    """Complete provisioning configuration."""
    run_id: str
    target_subscription_id: str
    target_tenant_id: str
    w365_config: W365Config
    agent_config: MagenticUIConfig
    teams_config: TeamsConfig
    enable_e2e_testing: bool = True
    e2e_test_timeout_seconds: int = 3600
    enable_teams_integration: bool = True
    cleanup_on_failure: bool = True
```

### 3.2 Result Models

```python
# Provisioning Results
@dataclass
class ProvisioningResult:
    """Result of a single provisioning step."""
    success: bool
    resource_id: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

# Cloud PC Info
@dataclass
class CloudPCInfo:
    """Cloud PC details."""
    id: str
    display_name: str
    status: str  # "provisioned", "provisioning", "failed", etc.
    user_principal_name: str
    ip_address: str | None = None
    managed_device_id: str | None = None
    rdp_endpoint: str | None = None

# Deployment Manifest
@dataclass
class DeploymentManifest:
    """Record of all created resources."""
    run_id: str
    timestamp: datetime
    created_resources: list[ResourceRecord]
    cloud_pcs: dict[str, CloudPCInfo]
    teams: dict[str, str]  # team_name -> team_id
    channels: dict[str, list[str]]  # team_id -> list of channel_ids
    agents: dict[str, AgentDeploymentInfo]

# Provisioning Report
@dataclass
class ProvisioningReport:
    """Final provisioning report."""
    run_id: str
    total_workers: int
    successful: int
    failed: int
    duration_minutes: float
    manifest: DeploymentManifest
    test_results: TestSuiteResult | None
    errors: list[ProvisioningError]
    cost_estimate_usd: float
```

---

## 4. Error Handling Strategy

### 4.1 Error Categories

| Category | Examples | Handling |
|----------|----------|----------|
| **Authentication** | Invalid credentials, expired tokens | Fail fast, no retry |
| **Quota/Limits** | Out of W365 licenses, subscription quota | Fail fast, report to user |
| **Transient** | Timeout, rate limit, temporary API error | Exponential backoff retry |
| **Service** | Cloud PC provision fails, API unavailable | Retry with backoff, timeout |
| **Configuration** | Invalid policy config, bad template | Fail fast, validate early |
| **Resource** | Cloud PC deleted externally, network issue | Handle gracefully, continue |

### 4.2 Retry Strategy

```
Transient errors (timeout, rate limit):
  Max retries: 3
  Base delay: 2s
  Backoff: exponential (2^n)
  Max delay: 30s
  Jitter: ±10%

Service errors (provisioning fails):
  Max retries: 5
  Base delay: 5s
  Backoff: exponential
  Max delay: 60s
  Circuit breaker: if > 5 consecutive failures, skip worker
```

### 4.3 Cleanup on Failure

When provisioning fails for a worker:

1. **Immediate**: Stop any running operations for that worker
2. **Async**: Delete Cloud PC (if partially provisioned)
3. **Async**: Remove from Teams (if added)
4. **Log**: Record failure details for debugging
5. **Continue**: Process remaining workers (failure isolation)

---

## 5. Integration Points

### 5.1 Existing KnowledgeWorkerAgent

The provisioning system integrates with KnowledgeWorkerAgent:

```python
# After provisioning, worker agent receives:
worker_agent = KnowledgeWorkerAgent(
    worker_config=KnowledgeWorkerConfig(
        endpoint_type="cloud_pc",  # New: was "cli_container"
        endpoint_id=cloud_pc_id,
        # ... other config
    )
)

# Agent can now:
# - Connect to provisioned Cloud PC
# - Access rich Windows telemetry
# - Run browser-based M365 activities
# - Leverage agent capabilities (GUI automation)
```

### 5.2 Service Bus Integration

Provisioning events published to Service Bus:

- `w365.provisioning.started` - Provisioning workflow initiated
- `w365.provisioning.policy-created` - Policy created
- `w365.cloud-pc.provisioned` - Cloud PC ready
- `w365.agent.installed` - Magentic-UI agent installed
- `w365.agent.verified` - Agent verified ready
- `w365.teams.team-created` - Teams team created
- `w365.testing.started` - E2E testing started
- `w365.testing.completed` - Testing finished with results
- `w365.provisioning.completed` - Full provisioning complete

### 5.3 Storage Integration

Artifacts stored in Azure Storage:

- `/deployments/{run_id}/manifest.json` - Full deployment record
- `/deployments/{run_id}/report.json` - Final provisioning report
- `/deployments/{run_id}/tests/` - Test results and screenshots
- `/deployments/{run_id}/logs/` - Provisioning logs
- `/deployments/{run_id}/config/` - Configuration snapshots

---

## 6. Performance & Scalability

### 6.1 Provisioning Throughput

```
Sequential bottleneck: Cloud PC provisioning (90 min timeout)
Parallel opportunities:
  - Multiple Cloud PCs (different users)
  - Teams setup (parallel to provisioning)
  - E2E testing (parallel to provisioning)

Throughput estimate (1 subscription):
  - 5-10 simultaneous Cloud PCs (licensing dependent)
  - ~500-600 minutes (5-10 in parallel) = 50-60 minutes wall-clock

Cost optimization:
  - Delete unused Cloud PCs immediately after testing
  - Use Dev/Test subscription for non-production
  - Schedule provisioning during off-peak hours
```

### 6.2 Resource Limits

| Resource | Limit | Mitigation |
|----------|-------|-----------|
| W365 Licenses | Per subscription | Check quota before provisioning |
| Graph API Rate Limit | 2000 req/min (per tenant) | Batch requests, implement backoff |
| Cloud PC Cores | Per subscription | Check CPU quota in target subscription |
| Storage Space | Per Cloud PC SKU | Monitor and clean up test files |

---

## 7. Security Considerations

### 7.1 Credential Management

- Use Azure Managed Identity where possible
- Store secrets in Key Vault, never in config files
- Rotate service principal credentials regularly
- Log all API calls with redacted sensitive data

### 7.2 Cloud PC Security

- Cloud PCs should not access external networks (isolated)
- Use conditional access policies for M365 access
- Enable MFA on all Cloud PC user accounts
- Encrypt all data in transit (RDP, PowerShell)

### 7.3 Agent Security

- Verify package signatures before installation
- Run agent with least-privilege service account
- Enable process isolation and sandboxing
- Audit all agent actions

---

## 8. Testing Strategy

### 8.1 Unit Tests

- Mocked Graph API client
- Configuration validation
- Data model serialization
- Error handling logic
- Timeout behavior

### 8.2 Integration Tests

- Real Graph API (beta endpoint)
- Policy and Cloud PC operations
- PowerShell remoting
- Teams API calls
- Selenium browser automation

### 8.3 E2E Tests

- Full provisioning workflow
- Multi-worker provisioning
- Error recovery and cleanup
- Cost tracking
- Report generation

### 8.4 Performance Tests

- Provisioning latency (per step)
- Concurrent provisioning scaling
- API rate limit handling
- Storage artifact sizes

---

## 9. Success Metrics

### 9.1 Provisioning Metrics

- `provisioning_success_rate` - % of workers provisioned successfully
- `provisioning_time_minutes` - Total time from start to complete
- `cloud_pc_provisioning_time_minutes` - Time to reach "provisioned" state
- `agent_setup_time_minutes` - Time to install and verify agent
- `teams_setup_time_minutes` - Time to create team and channels
- `e2e_test_completion_rate` - % of tests that completed
- `error_rate` - % of provisioning failures

### 9.2 Quality Metrics

- `test_pass_rate` - % of E2E tests passing
- `cloud_pc_availability` - % of Cloud PCs in "provisioned" state
- `agent_startup_success` - % of agents starting correctly
- `manifest_accuracy` - Manifest matches actual resources

### 9.3 Cost Metrics

- `total_cost_usd` - All resources created
- `cost_per_worker_usd` - Average cost per provisioned worker
- `storage_cost_usd` - Storage for artifacts
- `compute_cost_usd` - Cloud PC and testing infrastructure

---

## 10. Deployment Checklist

- [ ] Verify Graph API credentials (read + write to deviceManagement)
- [ ] Check W365 licenses in target subscription
- [ ] Verify Service Bus connectivity and topic creation
- [ ] Test PowerShell remoting to sample Cloud PC
- [ ] Validate Magentic-UI package URL and signatures
- [ ] Test Teams API permissions (team creation, messaging)
- [ ] Validate Selenium WebDriver and browser compatibility
- [ ] Verify Storage account and blob containers exist
- [ ] Test Service Bus event publishing
- [ ] Load configuration from environment or Key Vault
- [ ] Run validation suite before provisioning
- [ ] Set up monitoring and alerting
- [ ] Document runbook for troubleshooting

---

## 11. Implementation Order

1. **Phase 1**: W365CloudPCManager (core provisioning)
2. **Phase 2**: MagenticUISetupManager (agent deployment)
3. **Phase 3**: TeamsManager (integration)
4. **Phase 4**: BrowserAutomationTester (E2E testing)
5. **Phase 5**: ProvisioningOrchestrator (coordination)
6. **Phase 6**: Integration with KnowledgeWorkerAgent
7. **Phase 7**: Full E2E testing and validation

---

## Conclusion

This architecture provides a complete, production-ready Windows 365 Cloud PC provisioning system with Magentic-UI agent deployment. Each module is independently testable and can be integrated incrementally.

The design prioritizes:
- **Reliability** - Comprehensive error handling and retry logic
- **Observability** - Rich logging and event publishing
- **Modularity** - Clean separation of concerns
- **Scalability** - Efficient resource utilization
- **Security** - Credential management and access controls

Implementation should follow the phased approach with validation at each stage.
