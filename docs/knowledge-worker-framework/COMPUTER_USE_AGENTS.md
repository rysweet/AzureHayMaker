---
title: "Computer Use Knowledge Worker Agents"
description: "Browser automation agents for M365 web apps on Windows VMs"
last_updated: 2025-11-30
doc_type: reference
owner: knowledge-worker-framework
---

# Computer Use Knowledge Worker Agents

Computer Use Knowledge Worker Agents enable browser-based automation of Microsoft 365 web applications on Windows VMs. These agents execute realistic workflows (sending emails, Teams messages, document access) through Playwright browser automation, generating rich telemetry for security testing, EDR validation, and activity simulation.

## Overview

### What Are Computer Use Agents?

Computer Use Agents are knowledge worker automation agents that operate through a browser rather than APIs. Instead of calling the Microsoft Graph API directly, they:

1. **Connect to Windows VMs** via WinRM (Windows Remote Management)
2. **Deploy agent code** and dependencies (Python, Playwright, Chromium)
3. **Launch browsers** on the VM and navigate to M365 web apps
4. **Execute workflows** by interacting with web UIs (clicking buttons, filling forms)
5. **Generate telemetry** through realistic desktop activity patterns

### Why Computer Use Instead of API?

| Feature | API Agents | Computer Use Agents |
|---------|-----------|---------------------|
| **Telemetry Richness** | API logs only | Browser + OS + network logs |
| **EDR Detection** | No process activity | Real browser processes, file I/O |
| **User Behavior** | Instantaneous API calls | Human-like interaction timing |
| **Authentication** | OAuth tokens | Interactive browser login |
| **Desktop Logs** | None | Process execution, network connections |
| **Cost** | $ (Low) | $$ (Medium) |

**Use Cases**:
- **Security Product Testing**: Test EDR agents, DLP policies on real desktop activity
- **Incident Investigation**: Generate forensic artifacts (browser cache, cookies, history)
- **Realistic Simulations**: Mimic human users with mouse movements, typing delays
- **Web-Only Features**: Automate actions not available via API

### Hybrid Agent Strategy

The Knowledge Worker Framework uses a **three-tier endpoint strategy**:

```
┌─────────────────────────────────────────────────────────────┐
│ Endpoint Strategy (100 workers example)                     │
├─────────────────────────────────────────────────────────────┤
│ 10 Computer Use Agents (Windows VMs)                        │
│   - High-value targets (executives, admins)                 │
│   - Browser automation + OS telemetry                        │
│   - Cost: ~$150/month (Standard_B2ms VMs)                   │
├─────────────────────────────────────────────────────────────┤
│ 15 Cloud PC Agents (Windows 365)                            │
│   - Rich desktop telemetry without compute costs            │
│   - Full Windows event logs                                 │
│   - Cost: ~$465/month                                        │
├─────────────────────────────────────────────────────────────┤
│ 75 CLI Container Agents                                     │
│   - API-only activity, no desktop telemetry                 │
│   - Scale workers for volume                                │
│   - Cost: ~$150/month                                        │
└─────────────────────────────────────────────────────────────┘
Total: $765/month vs. $1,500 (all VMs) or $3,100 (all Cloud PCs)
```

---

## Architecture

### System Components

```
┌────────────────────────────────────────────────────────────────┐
│ KnowledgeWorkerOrchestrator                                    │
│                                                                │
│  • Provisions Windows VMs for Computer Use workers             │
│  • Deploys agent code via AgentDeployer                        │
│  • Assigns workflows to agents                                 │
│  • Collects telemetry from VM logs                             │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│ WinRMConnection                                                │
│                                                                │
│  • Establishes WinRM session to Windows VM                     │
│  • Executes remote PowerShell commands                         │
│  • Transfers files to/from VM                                  │
│  • Manages authentication (username/password or cert)          │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│ AgentDeployer                                                  │
│                                                                │
│  • Transfers agent code to C:\haymaker\agent\                  │
│  • Installs Python dependencies (playwright, aiohttp)          │
│  • Installs Playwright browsers (chromium)                     │
│  • Configures environment variables                            │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│ ComputerUseKnowledgeWorkerAgent                                │
│  (extends KnowledgeWorkerAgent)                                │
│                                                                │
│  • Launches Playwright browser on VM                           │
│  • Executes workflows (EmailWorkflow, TeamsMessageWorkflow)    │
│  • Logs activity to C:\haymaker\logs\                          │
│  • Reports completion status to orchestrator                   │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│ BrowserAutomation                                              │
│                                                                │
│  • Playwright Page abstraction                                │
│  • M365 authentication handling                                │
│  • Web element interaction (click, fill, wait)                 │
│  • Screenshot capture on errors                                │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│ Workflows (EmailWorkflow, TeamsMessageWorkflow)                │
│                                                                │
│  • Define automation sequences                                 │
│  • Navigate M365 web apps                                      │
│  • Interact with UI elements                                   │
│  • Validate success/failure                                    │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│ TelemetryCollector                                             │
│                                                                │
│  • Retrieves agent logs from VM                                │
│  • Collects browser logs (console, network)                    │
│  • Captures Windows event logs (process execution)             │
│  • Aggregates telemetry for analysis                           │
└────────────────────────────────────────────────────────────────┘
```

### Execution Flow

```
1. Orchestrator provisions Windows VM
   ├── Creates VM with public IP
   ├── Configures WinRM over HTTPS
   └── Opens firewall for port 5986

2. AgentDeployer installs agent
   ├── Connects via WinRMConnection
   ├── Transfers agent code to C:\haymaker\agent\
   ├── Runs: pip install playwright aiohttp
   └── Runs: playwright install chromium

3. Agent executes workflows
   ├── Launches Chromium browser (headless mode)
   ├── Navigates to https://outlook.office.com
   ├── Authenticates with worker credentials
   ├── EmailWorkflow: Composes and sends email
   ├── TeamsMessageWorkflow: Sends Teams chat
   └── Logs activity to C:\haymaker\logs\agent.log

4. TelemetryCollector retrieves logs
   ├── Downloads agent logs via WinRM
   ├── Queries Windows event logs (Event ID 4688)
   ├── Retrieves browser cache and history
   └── Uploads to Azure Blob Storage

5. Orchestrator cleanup
   ├── Stops agent processes
   ├── Deletes VM resources
   └── Archives telemetry for analysis
```

---

## Quick Start

### Minimal Example

```python
from azure_haymaker.knowledge_worker.agent import ComputerUseKnowledgeWorkerAgent
from azure_haymaker.knowledge_worker.connection import WinRMConnection
from azure_haymaker.knowledge_worker.workflows import EmailWorkflow
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

# Step 1: Define worker identity
worker = WorkerIdentity(
    worker_id="cu-001",
    display_name="Alice Engineer",
    user_principal_name="alice.engineer@tenant.onmicrosoft.com",
    password="SecurePassword123!",
    department="engineering",
)

# Step 2: Connect to Windows VM
connection = WinRMConnection(
    hostname="20.185.45.123",
    username="vmadmin",
    password="VmPassword123!",
    port=5986,
    use_https=True,
)

# Step 3: Deploy agent
from azure_haymaker.knowledge_worker.deployment import AgentDeployer

deployer = AgentDeployer(connection)
await deployer.deploy_agent(
    agent_code_path="/local/agent/",
    destination_path="C:\\haymaker\\agent\\",
)

# Step 4: Create agent instance
agent = ComputerUseKnowledgeWorkerAgent(
    worker=worker,
    connection=connection,
    headless=True,  # Run browser in headless mode
)

# Step 5: Execute email workflow
workflow = EmailWorkflow(
    recipient="bob@tenant.onmicrosoft.com",
    subject="Project Update",
    body="Here's the latest status on the project.",
)

result = await agent.execute_workflow(workflow)

print(f"Workflow status: {result.status}")
print(f"Duration: {result.duration_seconds}s")
print(f"Logs: {result.log_path}")
```

**Expected output**:
```
Workflow status: success
Duration: 12.5s
Logs: C:\haymaker\logs\cu-001_email_20251130_143022.log
```

---

## API Reference

### WinRMConnection

Manages WinRM connections to Windows VMs for remote command execution.

#### Constructor

```python
WinRMConnection(
    hostname: str,
    username: str,
    password: str | None = None,
    certificate_path: str | None = None,
    port: int = 5986,
    use_https: bool = True,
    verify_ssl: bool = True,
)
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `hostname` | str | Yes | - | VM IP address or DNS name |
| `username` | str | Yes | - | Windows username (e.g., "vmadmin") |
| `password` | str | No | None | Windows password |
| `certificate_path` | str | No | None | Path to client certificate (alternative to password) |
| `port` | int | No | 5986 | WinRM port (5985=HTTP, 5986=HTTPS) |
| `use_https` | bool | No | True | Use HTTPS transport |
| `verify_ssl` | bool | No | True | Verify SSL certificates |

**Example**:
```python
# Password authentication
conn = WinRMConnection(
    hostname="20.185.45.123",
    username="vmadmin",
    password="SecurePassword123!",
)

# Certificate authentication
conn = WinRMConnection(
    hostname="20.185.45.123",
    username="vmadmin",
    certificate_path="/certs/client.pem",
)
```

#### Methods

##### `execute_command()`

Execute a PowerShell command on the remote VM.

```python
async def execute_command(
    command: str,
    timeout_seconds: int | None = None,
) -> CommandResult
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `command` | str | Yes | - | PowerShell command to execute |
| `timeout_seconds` | int | No | 300 | Command timeout (5 minutes default) |

**Returns**: `CommandResult` with fields:
- `stdout: str` - Standard output
- `stderr: str` - Standard error
- `exit_code: int` - Exit code (0 = success)
- `duration_seconds: float` - Execution time

**Example**:
```python
# Simple command
result = await conn.execute_command("Get-Process | Select-Object -First 5")
print(result.stdout)

# Output:
# Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id  SI ProcessName
# -------  ------    -----      -----     ------     --  -- -----------
#     123      12     2345      12345       1.23   1234   0 chrome
#     456      23     3456      23456       2.34   2345   0 python
```

**Raises**:
- `WinRMConnectionError`: Connection failed
- `CommandTimeoutError`: Command exceeded timeout
- `CommandExecutionError`: Command returned non-zero exit code

##### `upload_file()`

Upload a file from local machine to VM.

```python
async def upload_file(
    local_path: str,
    remote_path: str,
) -> bool
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `local_path` | str | Yes | Local file path |
| `remote_path` | str | Yes | Destination path on VM (Windows format) |

**Returns**: `bool` - True if successful

**Example**:
```python
success = await conn.upload_file(
    local_path="/home/user/agent.py",
    remote_path="C:\\haymaker\\agent\\agent.py",
)
# Returns: True
```

##### `download_file()`

Download a file from VM to local machine.

```python
async def download_file(
    remote_path: str,
    local_path: str,
) -> bool
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `remote_path` | str | Yes | File path on VM |
| `local_path` | str | Yes | Local destination path |

**Returns**: `bool` - True if successful

**Example**:
```python
success = await conn.download_file(
    remote_path="C:\\haymaker\\logs\\agent.log",
    local_path="/tmp/agent.log",
)
# Returns: True
```

##### `test_connection()`

Test WinRM connection without executing commands.

```python
async def test_connection() -> bool
```

**Returns**: `bool` - True if connection successful

**Example**:
```python
if await conn.test_connection():
    print("Connection OK")
else:
    print("Connection failed")
```

---

### AgentDeployer

Deploys agent code and dependencies to Windows VMs.

#### Constructor

```python
AgentDeployer(
    connection: WinRMConnection,
    agent_code_path: str | None = None,
)
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `connection` | WinRMConnection | Yes | - | WinRM connection to VM |
| `agent_code_path` | str | No | "./agent/" | Path to agent source code |

**Example**:
```python
deployer = AgentDeployer(
    connection=my_connection,
    agent_code_path="/src/azure_haymaker/knowledge_worker/agent/",
)
```

#### Methods

##### `deploy_agent()`

Deploy agent code and install dependencies.

```python
async def deploy_agent(
    destination_path: str | None = None,
    install_dependencies: bool = True,
) -> DeploymentResult
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `destination_path` | str | No | "C:\\haymaker\\agent\\" | Destination on VM |
| `install_dependencies` | bool | No | True | Install Python packages |

**Returns**: `DeploymentResult` with fields:
- `success: bool` - Deployment succeeded
- `agent_path: str` - Agent installation path
- `python_version: str` - Python version on VM
- `playwright_version: str` - Playwright version
- `duration_seconds: float` - Deployment time

**Example**:
```python
result = await deployer.deploy_agent(
    destination_path="C:\\haymaker\\agent\\",
    install_dependencies=True,
)

print(f"Deployed to: {result.agent_path}")
print(f"Python: {result.python_version}")
print(f"Playwright: {result.playwright_version}")
```

**Expected output**:
```
Deployed to: C:\haymaker\agent\
Python: 3.11.5
Playwright: 1.40.0
```

**Deployment steps**:
1. Create destination directory
2. Upload agent source files (`.py` files)
3. Install Python packages: `pip install playwright aiohttp`
4. Install Playwright browsers: `playwright install chromium`
5. Verify installation

##### `verify_deployment()`

Verify agent deployment is functional.

```python
async def verify_deployment(
    agent_path: str,
) -> bool
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_path` | str | Yes | Agent installation path |

**Returns**: `bool` - True if agent can execute

**Example**:
```python
is_ready = await deployer.verify_deployment("C:\\haymaker\\agent\\")
# Returns: True
```

**Verification checks**:
- Python is installed and accessible
- Agent files exist at destination
- Playwright is installed
- Chromium browser is available

---

### ComputerUseKnowledgeWorkerAgent

Main agent class for executing browser-based workflows on Windows VMs.

#### Constructor

```python
ComputerUseKnowledgeWorkerAgent(
    worker: WorkerIdentity,
    connection: WinRMConnection,
    headless: bool = True,
    log_level: str = "INFO",
)
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `worker` | WorkerIdentity | Yes | - | Worker identity (credentials, persona) |
| `connection` | WinRMConnection | Yes | - | Connection to Windows VM |
| `headless` | bool | No | True | Run browser in headless mode |
| `log_level` | str | No | "INFO" | Logging level (DEBUG/INFO/WARNING) |

**Example**:
```python
agent = ComputerUseKnowledgeWorkerAgent(
    worker=my_worker,
    connection=my_connection,
    headless=True,
    log_level="DEBUG",
)
```

#### Methods

##### `execute_workflow()`

Execute a workflow (email, Teams message, document access).

```python
async def execute_workflow(
    workflow: BaseWorkflow,
) -> WorkflowResult
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workflow` | BaseWorkflow | Yes | Workflow to execute (EmailWorkflow, TeamsMessageWorkflow) |

**Returns**: `WorkflowResult` with fields:
- `status: str` - "success" or "failure"
- `duration_seconds: float` - Execution time
- `log_path: str` - Path to log file on VM
- `screenshot_path: str | None` - Screenshot on error
- `error_message: str | None` - Error details if failed

**Example**:
```python
workflow = EmailWorkflow(
    recipient="bob@tenant.onmicrosoft.com",
    subject="Meeting Reminder",
    body="Don't forget our 2pm meeting.",
)

result = await agent.execute_workflow(workflow)

if result.status == "success":
    print(f"Email sent in {result.duration_seconds}s")
else:
    print(f"Failed: {result.error_message}")
    print(f"Screenshot: {result.screenshot_path}")
```

**Workflow execution steps**:
1. Launch Playwright browser on VM
2. Navigate to M365 web app (Outlook Web, Teams Web)
3. Authenticate with worker credentials
4. Execute workflow-specific actions (compose email, send message)
5. Verify success (check sent items, delivery status)
6. Log activity and close browser

##### `get_logs()`

Retrieve agent logs from VM.

```python
async def get_logs(
    log_path: str | None = None,
) -> str
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `log_path` | str | No | Auto-detect | Path to log file on VM |

**Returns**: `str` - Log file contents

**Example**:
```python
logs = await agent.get_logs()
print(logs)
```

**Expected output**:
```
2025-11-30 14:30:22 INFO Starting EmailWorkflow
2025-11-30 14:30:25 INFO Navigating to https://outlook.office.com
2025-11-30 14:30:28 INFO Authenticated as alice.engineer@tenant.onmicrosoft.com
2025-11-30 14:30:30 INFO Composing email to bob@tenant.onmicrosoft.com
2025-11-30 14:30:34 INFO Email sent successfully
2025-11-30 14:30:35 INFO Workflow completed in 12.5s
```

##### `stop()`

Stop agent and cleanup resources.

```python
async def stop() -> None
```

**Example**:
```python
await agent.stop()
```

**Cleanup actions**:
- Close browser processes
- Delete temporary files
- Archive logs
- Disconnect WinRM session

---

### BrowserAutomation

Low-level browser automation utilities built on Playwright.

#### Constructor

```python
BrowserAutomation(
    connection: WinRMConnection,
    headless: bool = True,
)
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `connection` | WinRMConnection | Yes | - | WinRM connection to VM |
| `headless` | bool | No | True | Headless mode |

**Example**:
```python
browser = BrowserAutomation(
    connection=my_connection,
    headless=True,
)
```

#### Methods

##### `launch()`

Launch Chromium browser on VM.

```python
async def launch() -> Page
```

**Returns**: `Page` - Playwright page object

**Example**:
```python
page = await browser.launch()
await page.goto("https://outlook.office.com")
```

##### `authenticate_m365()`

Authenticate to Microsoft 365 web apps.

```python
async def authenticate_m365(
    page: Page,
    username: str,
    password: str,
) -> bool
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | Page | Yes | Playwright page |
| `username` | str | Yes | User principal name |
| `password` | str | Yes | Password |

**Returns**: `bool` - True if authentication succeeded

**Example**:
```python
page = await browser.launch()
await page.goto("https://outlook.office.com")

success = await browser.authenticate_m365(
    page=page,
    username="alice.engineer@tenant.onmicrosoft.com",
    password="SecurePassword123!",
)

if success:
    print("Authenticated successfully")
```

**Authentication flow**:
1. Wait for login page to load
2. Fill username field
3. Click "Next" button
4. Fill password field
5. Click "Sign in" button
6. Handle MFA if configured
7. Wait for redirect to app

##### `wait_for_element()`

Wait for web element to appear.

```python
async def wait_for_element(
    page: Page,
    selector: str,
    timeout_ms: int | None = None,
) -> ElementHandle
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | Page | Yes | - | Playwright page |
| `selector` | str | Yes | - | CSS selector |
| `timeout_ms` | int | No | 30000 | Timeout in milliseconds |

**Returns**: `ElementHandle` - Web element

**Example**:
```python
# Wait for "New message" button
new_msg_btn = await browser.wait_for_element(
    page=page,
    selector="button[aria-label='New message']",
    timeout_ms=10000,
)
await new_msg_btn.click()
```

##### `take_screenshot()`

Capture screenshot on VM.

```python
async def take_screenshot(
    page: Page,
    path: str,
) -> str
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | Page | Yes | Playwright page |
| `path` | str | Yes | Destination path on VM |

**Returns**: `str` - Screenshot path

**Example**:
```python
screenshot_path = await browser.take_screenshot(
    page=page,
    path="C:\\haymaker\\screenshots\\error.png",
)
# Returns: "C:\haymaker\screenshots\error.png"
```

---

## Workflow Definitions

### EmailWorkflow

Compose and send email via Outlook Web.

#### Constructor

```python
EmailWorkflow(
    recipient: str,
    subject: str,
    body: str,
    attachments: list[str] | None = None,
)
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `recipient` | str | Yes | - | Recipient email address |
| `subject` | str | Yes | - | Email subject |
| `body` | str | Yes | - | Email body (plain text) |
| `attachments` | list[str] | No | None | Attachment file paths on VM |

**Example**:
```python
workflow = EmailWorkflow(
    recipient="bob@tenant.onmicrosoft.com",
    subject="Q4 Report",
    body="Attached is the Q4 financial report.",
    attachments=["C:\\Users\\alice\\Documents\\Q4_Report.pdf"],
)

result = await agent.execute_workflow(workflow)
```

#### Automation Steps

1. Navigate to https://outlook.office.com
2. Click "New message" button
3. Fill "To" field with recipient
4. Fill subject field
5. Fill body field
6. Upload attachments (if any)
7. Click "Send" button
8. Wait for "Message sent" confirmation
9. Verify in "Sent Items" folder

#### Expected Duration

- Without attachments: 8-12 seconds
- With attachments: 15-25 seconds

---

### TeamsMessageWorkflow

Send Teams chat message via Teams Web.

#### Constructor

```python
TeamsMessageWorkflow(
    recipient: str,
    message: str,
    message_type: str = "chat",
)
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `recipient` | str | Yes | - | Recipient email or display name |
| `message` | str | Yes | - | Message text |
| `message_type` | str | No | "chat" | "chat" or "channel" |

**Example**:
```python
workflow = TeamsMessageWorkflow(
    recipient="bob@tenant.onmicrosoft.com",
    message="Can you review the PR when you get a chance?",
    message_type="chat",
)

result = await agent.execute_workflow(workflow)
```

#### Automation Steps

1. Navigate to https://teams.microsoft.com
2. Click "New chat" button
3. Search for recipient
4. Select recipient from results
5. Type message in input field
6. Click "Send" button
7. Wait for message to appear in chat history

#### Expected Duration

- 10-15 seconds

---

### DocumentAccessWorkflow

Open and view document in SharePoint/OneDrive.

#### Constructor

```python
DocumentAccessWorkflow(
    document_url: str,
    view_duration_seconds: int = 30,
)
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `document_url` | str | Yes | - | SharePoint/OneDrive document URL |
| `view_duration_seconds` | int | No | 30 | Time to keep document open |

**Example**:
```python
workflow = DocumentAccessWorkflow(
    document_url="https://tenant.sharepoint.com/sites/Engineering/Shared%20Documents/Design_Spec.docx",
    view_duration_seconds=45,
)

result = await agent.execute_workflow(workflow)
```

#### Automation Steps

1. Navigate to document URL
2. Wait for document to load in Office Online
3. Scroll through document (simulate reading)
4. Wait for specified duration
5. Close document

#### Expected Duration

- Based on `view_duration_seconds` parameter + 5-10s overhead

---

## Deployment Guide

### Orchestrator Integration

Computer Use Agents are deployed automatically by the `KnowledgeWorkerOrchestrator` during the provisioning phase.

#### Endpoint Selection Logic

```python
# In KnowledgeWorkerOrchestrator

def determine_endpoint_type(worker: WorkerIdentity) -> EndpointType:
    """Determine endpoint type based on worker persona."""

    # Computer Use agents for:
    # - Executives (high-value targets)
    # - IT admins (privileged access testing)
    # - Security analysts (EDR validation)

    computer_use_personas = {
        WorkerPersona.EXECUTIVE,
        WorkerPersona.IT_ADMIN,
        WorkerPersona.SECURITY_ANALYST,
    }

    if worker.persona in computer_use_personas:
        return EndpointType.WINDOWS_VM_COMPUTER_USE

    # Random sampling: 5% of other workers
    import random
    if random.random() < 0.05:
        return EndpointType.WINDOWS_VM_COMPUTER_USE

    # Default to Cloud PC or CLI container
    return determine_default_endpoint(worker)
```

#### VM Provisioning

```python
async def provision_computer_use_vm(
    worker: WorkerIdentity,
    resource_group: str,
    location: str,
) -> VmInfo:
    """Provision Windows VM for Computer Use agent."""

    vm_name = f"kw-cu-{worker.worker_id[:8]}"

    # Create VM with Windows Server 2022
    vm_result = await compute_client.virtual_machines.begin_create_or_update(
        resource_group_name=resource_group,
        vm_name=vm_name,
        parameters={
            "location": location,
            "hardware_profile": {
                "vm_size": "Standard_B2ms",  # 2 vCPU, 8GB RAM
            },
            "storage_profile": {
                "image_reference": {
                    "publisher": "MicrosoftWindowsServer",
                    "offer": "WindowsServer",
                    "sku": "2022-datacenter",
                    "version": "latest",
                },
                "os_disk": {
                    "create_option": "FromImage",
                    "managed_disk": {
                        "storage_account_type": "Premium_LRS",
                    },
                },
            },
            "os_profile": {
                "computer_name": vm_name,
                "admin_username": "vmadmin",
                "admin_password": generate_secure_password(),
                "windows_configuration": {
                    "enable_automatic_updates": True,
                    "provision_vm_agent": True,
                },
            },
            "network_profile": {
                "network_interfaces": [
                    {"id": nic_id}
                ],
            },
        },
    )

    # Configure WinRM
    await configure_winrm(vm_name, resource_group)

    # Get public IP
    public_ip = await get_vm_public_ip(vm_name, resource_group)

    return VmInfo(
        vm_name=vm_name,
        public_ip=public_ip,
        username="vmadmin",
        password=password,
    )
```

#### Agent Deployment

```python
async def deploy_computer_use_agent(
    worker: WorkerIdentity,
    vm_info: VmInfo,
) -> ComputerUseKnowledgeWorkerAgent:
    """Deploy agent to provisioned VM."""

    # Connect to VM
    connection = WinRMConnection(
        hostname=vm_info.public_ip,
        username=vm_info.username,
        password=vm_info.password,
    )

    # Test connection
    if not await connection.test_connection():
        raise DeploymentError(f"Cannot connect to VM {vm_info.vm_name}")

    # Deploy agent code
    deployer = AgentDeployer(connection)
    result = await deployer.deploy_agent(
        destination_path="C:\\haymaker\\agent\\",
        install_dependencies=True,
    )

    if not result.success:
        raise DeploymentError(f"Agent deployment failed: {result.error_message}")

    # Create agent instance
    agent = ComputerUseKnowledgeWorkerAgent(
        worker=worker,
        connection=connection,
        headless=True,
    )

    return agent
```

#### Batch Deployment Example

```python
async def deploy_computer_use_agents(
    workers: list[WorkerIdentity],
    resource_group: str,
    location: str,
) -> list[ComputerUseKnowledgeWorkerAgent]:
    """Deploy Computer Use agents for all workers."""

    agents = []

    # Provision VMs in parallel (with rate limiting)
    vm_tasks = [
        provision_computer_use_vm(worker, resource_group, location)
        for worker in workers
    ]
    vm_infos = await asyncio.gather(*vm_tasks)

    print(f"Provisioned {len(vm_infos)} VMs")

    # Deploy agents sequentially (avoid overloading VMs)
    for worker, vm_info in zip(workers, vm_infos):
        try:
            agent = await deploy_computer_use_agent(worker, vm_info)
            agents.append(agent)
            print(f"Deployed agent for {worker.display_name}")
        except DeploymentError as e:
            print(f"Failed to deploy {worker.display_name}: {e}")

    return agents
```

---

## Telemetry Collection

### What Telemetry Is Generated?

Computer Use Agents generate three types of telemetry:

1. **Agent Logs** - Workflow execution logs
2. **Browser Logs** - Network requests, console messages
3. **Windows Event Logs** - Process execution, authentication

#### Agent Logs

```
C:\haymaker\logs\agent.log

2025-11-30 14:30:22 INFO [cu-001] Starting EmailWorkflow
2025-11-30 14:30:25 INFO [cu-001] Navigating to https://outlook.office.com
2025-11-30 14:30:28 INFO [cu-001] Authenticated as alice.engineer@tenant.onmicrosoft.com
2025-11-30 14:30:30 INFO [cu-001] Composing email to bob@tenant.onmicrosoft.com
2025-11-30 14:30:34 INFO [cu-001] Email sent successfully
2025-11-30 14:30:35 INFO [cu-001] Workflow completed in 12.5s
```

#### Browser Logs

```
C:\haymaker\logs\browser_network.log

[2025-11-30 14:30:25] GET https://outlook.office.com -> 200
[2025-11-30 14:30:26] GET https://outlook.office.com/owa/service.svc/s/GetSessionData -> 200
[2025-11-30 14:30:30] POST https://outlook.office.com/owa/service.svc/s/SendMessage -> 200
```

#### Windows Event Logs

```
Event ID 4688 (Process Creation)
Process: C:\Program Files\Python311\python.exe
Command Line: python.exe C:\haymaker\agent\agent.py --workflow=email
User: vmadmin
Time: 2025-11-30 14:30:22

Event ID 4688 (Process Creation)
Process: C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
Command Line: "msedge.exe" --headless --remote-debugging-port=9222
User: vmadmin
Time: 2025-11-30 14:30:24
```

### Collecting Telemetry

#### TelemetryCollector Class

```python
from azure_haymaker.knowledge_worker.telemetry import TelemetryCollector

collector = TelemetryCollector(connection=my_connection)

# Collect agent logs
agent_logs = await collector.collect_agent_logs(
    log_path="C:\\haymaker\\logs\\agent.log"
)

# Collect browser logs
browser_logs = await collector.collect_browser_logs(
    log_path="C:\\haymaker\\logs\\browser_network.log"
)

# Collect Windows event logs (Event ID 4688)
event_logs = await collector.collect_windows_events(
    event_id=4688,
    time_range_hours=1,
)

# Upload all telemetry to Azure Blob Storage
await collector.upload_telemetry(
    storage_account="haymakertelemetry",
    container="knowledge-worker-logs",
    run_id="abc12345-def6-7890-ghij-klmnopqrstuv",
)
```

#### Telemetry Storage Structure

```
Azure Blob Storage: haymakertelemetry/knowledge-worker-logs/

/abc12345-def6-7890-ghij-klmnopqrstuv/
  /agents/
    /cu-001/
      agent.log
      browser_network.log
      browser_console.log
    /cu-002/
      agent.log
      browser_network.log
  /windows_events/
    cu-001_event_4688.json
    cu-002_event_4688.json
  /screenshots/
    cu-001_error_20251130_143045.png
```

#### Querying Telemetry

```python
# Download telemetry for analysis
from azure.storage.blob import BlobServiceClient

blob_client = BlobServiceClient.from_connection_string(conn_str)
container = blob_client.get_container_client("knowledge-worker-logs")

run_prefix = "abc12345-def6-7890-ghij-klmnopqrstuv"
blobs = container.list_blobs(name_starts_with=run_prefix)

for blob in blobs:
    print(f"Found: {blob.name}")

    # Download specific log
    if "agent.log" in blob.name:
        blob_client = container.get_blob_client(blob.name)
        log_content = blob_client.download_blob().readall().decode()
        print(log_content)
```

---

## Troubleshooting

### WinRM Connection Failures

**Symptom**: `WinRMConnectionError: Cannot connect to 20.185.45.123:5986`

**Causes**:
1. WinRM not configured on VM
2. Firewall blocking port 5986
3. Incorrect credentials
4. SSL certificate verification failure

**Solutions**:

#### 1. Verify WinRM is Running

```python
# Connect to VM via Azure Portal (Serial Console or Bastion)
# Run in PowerShell:
Get-Service WinRM

# Should show:
# Status   Name               DisplayName
# ------   ----               -----------
# Running  WinRM              Windows Remote Management
```

#### 2. Configure WinRM HTTPS

```powershell
# Enable WinRM with HTTPS
winrm quickconfig -transport:https

# Create self-signed certificate
$cert = New-SelfSignedCertificate -DnsName "vm-hostname" -CertStoreLocation Cert:\LocalMachine\My
New-Item -Path WSMan:\localhost\Listener -Transport HTTPS -Address * -CertificateThumbPrint $cert.Thumbprint -Force

# Allow WinRM through firewall
New-NetFirewallRule -DisplayName "WinRM HTTPS" -Direction Inbound -LocalPort 5986 -Protocol TCP -Action Allow
```

#### 3. Disable SSL Verification (Development Only)

```python
# Only for testing with self-signed certificates
connection = WinRMConnection(
    hostname="20.185.45.123",
    username="vmadmin",
    password="SecurePassword123!",
    verify_ssl=False,  # WARNING: Not for production
)
```

#### 4. Test Connection Manually

```bash
# Test WinRM from Linux/Mac
pip install pywinrm

python3 -c "
from winrm import Session
s = Session('20.185.45.123', auth=('vmadmin', 'SecurePassword123!'), transport='ssl', server_cert_validation='ignore')
r = s.run_cmd('ipconfig')
print(r.std_out)
"
```

---

### Browser Automation Errors

**Symptom**: `PlaywrightError: Chromium browser not found`

**Cause**: Playwright not installed or installation incomplete.

**Solution**:

```python
# Reinstall Playwright browsers
deployer = AgentDeployer(connection)
result = await connection.execute_command(
    "cd C:\\haymaker\\agent && playwright install chromium"
)

if result.exit_code == 0:
    print("Chromium installed successfully")
else:
    print(f"Installation failed: {result.stderr}")
```

---

### Authentication Failures

**Symptom**: `AuthenticationError: Failed to sign in to M365`

**Causes**:
1. Incorrect worker credentials
2. MFA required but not configured
3. Conditional Access policy blocking sign-in
4. Password expired

**Solutions**:

#### 1. Verify Credentials

```python
# Test credentials manually
from azure_haymaker.knowledge_worker.auth import verify_m365_credentials

is_valid = await verify_m365_credentials(
    username="alice.engineer@tenant.onmicrosoft.com",
    password="SecurePassword123!",
)

if is_valid:
    print("Credentials are valid")
else:
    print("Invalid credentials")
```

#### 2. Disable MFA for Test Users

```bash
# In Azure AD Portal:
# Users > alice.engineer > Authentication methods > Require multi-factor authentication: No

# Or via PowerShell:
Connect-MsolService
Set-MsolUser -UserPrincipalName alice.engineer@tenant.onmicrosoft.com -StrongAuthenticationRequirements @()
```

#### 3. Configure Conditional Access Exception

```
Azure AD > Security > Conditional Access > New Policy
- Name: "Allow HayMaker Agents"
- Users: Include group "HayMaker-Test-Users"
- Conditions: IP ranges = VM subnet (10.0.1.0/24)
- Grant: Grant access (no MFA required)
```

---

### Performance Issues

**Symptom**: Workflows taking >30 seconds to complete.

**Causes**:
1. VM under-provisioned (CPU, memory)
2. Network latency between VM and M365
3. Browser running in non-headless mode (slower)
4. Too many concurrent workflows on single VM

**Solutions**:

#### 1. Use Larger VM SKU

```python
# Upgrade from Standard_B2ms (2 vCPU, 8GB) to Standard_B4ms (4 vCPU, 16GB)
vm_parameters["hardware_profile"]["vm_size"] = "Standard_B4ms"
```

#### 2. Enable Headless Mode

```python
# Headless mode is 2-3x faster
agent = ComputerUseKnowledgeWorkerAgent(
    worker=worker,
    connection=connection,
    headless=True,  # Critical for performance
)
```

#### 3. Limit Concurrent Workflows

```python
# Don't run too many workflows simultaneously on one VM
import asyncio

semaphore = asyncio.Semaphore(3)  # Max 3 workflows at once

async def execute_with_limit(agent, workflow):
    async with semaphore:
        return await agent.execute_workflow(workflow)

tasks = [execute_with_limit(agent, wf) for wf in workflows]
results = await asyncio.gather(*tasks)
```

---

### Log Retrieval Failures

**Symptom**: `TelemetryCollector` returns empty logs.

**Cause**: Log files not created or wrong path.

**Solution**:

```python
# List files in log directory
result = await connection.execute_command(
    "Get-ChildItem C:\\haymaker\\logs\\ | Select-Object Name, Length"
)
print(result.stdout)

# Expected output:
# Name                    Length
# ----                    ------
# agent.log                12345
# browser_network.log       5678
# browser_console.log       3456

# If empty, check agent is writing logs:
result = await connection.execute_command(
    "Get-Content C:\\haymaker\\agent\\config.py | Select-String -Pattern 'LOG_PATH'"
)
print(result.stdout)
```

---

## Security Best Practices

### Credential Management

**Never hardcode credentials** in agent code or configuration files.

#### Use Azure Key Vault

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Retrieve worker password from Key Vault
credential = DefaultAzureCredential()
vault_url = "https://haymaker-kv.vault.azure.net/"
client = SecretClient(vault_url=vault_url, credential=credential)

worker_password = client.get_secret("worker-alice-password").value

worker = WorkerIdentity(
    worker_id="cu-001",
    user_principal_name="alice.engineer@tenant.onmicrosoft.com",
    password=worker_password,  # From Key Vault
)
```

#### Use Managed Identity for VM Authentication

```python
# Instead of password, use certificate-based auth
from azure.identity import ManagedIdentityCredential

credential = ManagedIdentityCredential()

# WinRM with certificate
connection = WinRMConnection(
    hostname=vm_public_ip,
    username="vmadmin",
    certificate_path="/certs/vm_cert.pem",  # From Key Vault
)
```

---

### WinRM Security

#### Use HTTPS Only

```python
# Always use HTTPS (port 5986), never HTTP (port 5985)
connection = WinRMConnection(
    hostname=vm_ip,
    username=username,
    password=password,
    port=5986,  # HTTPS
    use_https=True,
)
```

#### Restrict Network Access

```python
# Configure NSG to allow WinRM only from orchestrator subnet
from azure.mgmt.network import NetworkManagementClient

nsg_rule = {
    "name": "AllowWinRMFromOrchestrator",
    "priority": 100,
    "direction": "Inbound",
    "access": "Allow",
    "protocol": "Tcp",
    "source_address_prefix": "10.0.0.0/24",  # Orchestrator subnet
    "destination_address_prefix": "*",
    "source_port_range": "*",
    "destination_port_range": "5986",
}

await network_client.security_rules.begin_create_or_update(
    resource_group_name=resource_group,
    network_security_group_name=nsg_name,
    security_rule_name="AllowWinRMFromOrchestrator",
    security_rule_parameters=nsg_rule,
)
```

---

### Input Validation

#### Validate Workflow Parameters

```python
def validate_email_workflow(workflow: EmailWorkflow) -> None:
    """Validate email workflow parameters before execution."""

    # Validate recipient
    if "@" not in workflow.recipient:
        raise ValueError(f"Invalid recipient email: {workflow.recipient}")

    # Prevent email bomb
    if len(workflow.body) > 100000:
        raise ValueError("Email body too large (max 100KB)")

    # Prevent directory traversal in attachments
    for attachment in workflow.attachments or []:
        if ".." in attachment or attachment.startswith("/"):
            raise ValueError(f"Invalid attachment path: {attachment}")

# Use before executing
try:
    validate_email_workflow(my_workflow)
    result = await agent.execute_workflow(my_workflow)
except ValueError as e:
    print(f"Validation error: {e}")
```

---

### Least Privilege

#### Use Dedicated VM Admin Account

```python
# Don't use domain admin or global admin
# Create dedicated local admin account for agent operations

# In VM provisioning:
vm_parameters["os_profile"]["admin_username"] = "haymaker-agent"
vm_parameters["os_profile"]["admin_password"] = generate_secure_password()

# Restrict account to:
# - Cannot sign in interactively
# - Cannot access Azure resources
# - Only WinRM access
```

---

## Examples

### Complete End-to-End Example

```python
import asyncio
from azure_haymaker.knowledge_worker.agent import ComputerUseKnowledgeWorkerAgent
from azure_haymaker.knowledge_worker.connection import WinRMConnection
from azure_haymaker.knowledge_worker.deployment import AgentDeployer
from azure_haymaker.knowledge_worker.workflows import EmailWorkflow, TeamsMessageWorkflow
from azure_haymaker.knowledge_worker.telemetry import TelemetryCollector
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity, WorkerPersona

async def main():
    # Step 1: Define worker
    worker = WorkerIdentity(
        worker_id="cu-exec-001",
        display_name="Alex Executive",
        user_principal_name="alex.executive@tenant.onmicrosoft.com",
        password="SecurePassword123!",
        department="executive",
        persona=WorkerPersona.EXECUTIVE,
    )

    # Step 2: Connect to Windows VM (already provisioned)
    connection = WinRMConnection(
        hostname="20.185.45.123",
        username="vmadmin",
        password="VmPassword123!",
        port=5986,
        use_https=True,
    )

    print("Testing connection...")
    if not await connection.test_connection():
        print("Connection failed!")
        return
    print("Connection OK")

    # Step 3: Deploy agent
    print("Deploying agent...")
    deployer = AgentDeployer(connection)
    deployment_result = await deployer.deploy_agent(
        destination_path="C:\\haymaker\\agent\\",
        install_dependencies=True,
    )

    if not deployment_result.success:
        print(f"Deployment failed: {deployment_result.error_message}")
        return

    print(f"Agent deployed to: {deployment_result.agent_path}")
    print(f"Python: {deployment_result.python_version}")
    print(f"Playwright: {deployment_result.playwright_version}")

    # Step 4: Create agent instance
    agent = ComputerUseKnowledgeWorkerAgent(
        worker=worker,
        connection=connection,
        headless=True,
        log_level="INFO",
    )

    # Step 5: Execute workflows
    workflows = [
        EmailWorkflow(
            recipient="bob@tenant.onmicrosoft.com",
            subject="Q4 Budget Review",
            body="Please review the attached Q4 budget proposal.",
        ),
        TeamsMessageWorkflow(
            recipient="charlie@tenant.onmicrosoft.com",
            message="Can you join the executive meeting at 3pm?",
        ),
    ]

    for workflow in workflows:
        print(f"\nExecuting: {workflow.__class__.__name__}")
        result = await agent.execute_workflow(workflow)

        if result.status == "success":
            print(f"✓ Completed in {result.duration_seconds:.1f}s")
            print(f"  Log: {result.log_path}")
        else:
            print(f"✗ Failed: {result.error_message}")
            if result.screenshot_path:
                print(f"  Screenshot: {result.screenshot_path}")

    # Step 6: Collect telemetry
    print("\nCollecting telemetry...")
    collector = TelemetryCollector(connection)

    agent_logs = await collector.collect_agent_logs()
    print(f"Collected {len(agent_logs)} bytes of agent logs")

    event_logs = await collector.collect_windows_events(
        event_id=4688,
        time_range_hours=1,
    )
    print(f"Collected {len(event_logs)} process execution events")

    # Upload to Azure Blob Storage
    await collector.upload_telemetry(
        storage_account="haymakertelemetry",
        container="knowledge-worker-logs",
        run_id="test-run-001",
    )
    print("Telemetry uploaded to Azure Blob Storage")

    # Step 7: Cleanup
    print("\nCleaning up...")
    await agent.stop()
    print("Agent stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output**:
```
Testing connection...
Connection OK
Deploying agent...
Agent deployed to: C:\haymaker\agent\
Python: 3.11.5
Playwright: 1.40.0

Executing: EmailWorkflow
✓ Completed in 11.2s
  Log: C:\haymaker\logs\cu-exec-001_email_20251130_150022.log

Executing: TeamsMessageWorkflow
✓ Completed in 13.5s
  Log: C:\haymaker\logs\cu-exec-001_teams_20251130_150035.log

Collecting telemetry...
Collected 4567 bytes of agent logs
Collected 15 process execution events
Telemetry uploaded to Azure Blob Storage

Cleaning up...
Agent stopped
```

---

### Multi-Agent Orchestration

```python
async def orchestrate_multiple_agents():
    """Deploy and run multiple Computer Use agents in parallel."""

    # Define workers
    workers = [
        WorkerIdentity(
            worker_id=f"cu-{i:03d}",
            display_name=f"Worker {i}",
            user_principal_name=f"worker{i}@tenant.onmicrosoft.com",
            password=f"Password{i}!",
            department="engineering",
        )
        for i in range(5)
    ]

    # VM connection info (pre-provisioned)
    vm_ips = [
        "20.185.45.123",
        "20.185.45.124",
        "20.185.45.125",
        "20.185.45.126",
        "20.185.45.127",
    ]

    # Deploy agents in parallel
    async def deploy_agent(worker, vm_ip):
        connection = WinRMConnection(
            hostname=vm_ip,
            username="vmadmin",
            password="VmPassword123!",
        )

        deployer = AgentDeployer(connection)
        await deployer.deploy_agent()

        return ComputerUseKnowledgeWorkerAgent(
            worker=worker,
            connection=connection,
            headless=True,
        )

    print("Deploying agents...")
    deploy_tasks = [
        deploy_agent(worker, vm_ip)
        for worker, vm_ip in zip(workers, vm_ips)
    ]
    agents = await asyncio.gather(*deploy_tasks)
    print(f"Deployed {len(agents)} agents")

    # Execute workflows in parallel
    print("Executing workflows...")
    workflow = EmailWorkflow(
        recipient="team@tenant.onmicrosoft.com",
        subject="Daily Standup",
        body="Here's my status update for today.",
    )

    workflow_tasks = [
        agent.execute_workflow(workflow)
        for agent in agents
    ]
    results = await asyncio.gather(*workflow_tasks)

    # Report results
    success_count = sum(1 for r in results if r.status == "success")
    print(f"\nResults: {success_count}/{len(results)} succeeded")

    # Cleanup all agents
    print("Cleaning up...")
    cleanup_tasks = [agent.stop() for agent in agents]
    await asyncio.gather(*cleanup_tasks)

asyncio.run(orchestrate_multiple_agents())
```

---

## Related Documentation

- [Knowledge Worker Framework Architecture](./ARCHITECTURE.md) - Overall framework design
- [Windows 365 Cloud PC Provisioning](./WINDOWS365_CLOUD_PC.md) - Cloud PC endpoint alternative
- [Windows VM Fallback Strategy](./WINDOWS_VM_FALLBACK.md) - Cascade fallback for resilient provisioning
- [Endpoint Strategy Comparison](./ARCHITECTURE.md#6-endpoint-strategy) - Detailed endpoint comparison

---

## Appendix: Dependencies

### Python Packages

```
# Agent requirements.txt
playwright==1.40.0
aiohttp==3.9.0
pywinrm==0.4.3
```

### VM Software Requirements

```
Windows Server 2022 Datacenter
Python 3.11.5
PowerShell 5.1
.NET Framework 4.8
Edge WebView2 Runtime (for Playwright)
```

### Installation Script

```powershell
# install_agent_deps.ps1
# Run on Windows VM to prepare for agent deployment

# Install Python 3.11
$pythonUrl = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
Invoke-WebRequest -Uri $pythonUrl -OutFile "C:\Temp\python-installer.exe"
Start-Process -FilePath "C:\Temp\python-installer.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait

# Upgrade pip
python -m pip install --upgrade pip

# Install agent packages
pip install playwright aiohttp

# Install Playwright browsers
playwright install chromium

# Create agent directory
New-Item -ItemType Directory -Path "C:\haymaker\agent" -Force
New-Item -ItemType Directory -Path "C:\haymaker\logs" -Force

# Configure WinRM HTTPS
winrm quickconfig -transport:https -quiet

Write-Host "Agent dependencies installed successfully"
```

---

## Appendix: Performance Benchmarks

### Workflow Execution Times

| Workflow | Headless Mode | Headed Mode | Notes |
|----------|--------------|-------------|-------|
| EmailWorkflow (no attachments) | 8-12s | 15-20s | Authentication cached after first run |
| EmailWorkflow (with attachment) | 15-25s | 25-35s | Upload time depends on file size |
| TeamsMessageWorkflow | 10-15s | 18-25s | Search for recipient adds 3-5s |
| DocumentAccessWorkflow (30s view) | 35-40s | 40-50s | Load time depends on document size |

### Resource Usage

| VM SKU | vCPU | RAM | Concurrent Workflows | CPU Usage | Memory Usage |
|--------|------|-----|---------------------|-----------|--------------|
| Standard_B2s | 2 | 4GB | 1 | 40-60% | 2-3GB |
| Standard_B2ms | 2 | 8GB | 3 | 60-80% | 4-6GB |
| Standard_B4ms | 4 | 16GB | 5 | 50-70% | 8-12GB |

**Recommendation**: Use **Standard_B2ms** for 1-3 concurrent workflows per VM.

---

## Appendix: Cost Analysis

### VM Costs (Pay-as-you-go, East US)

| VM SKU | vCPU | RAM | Storage | USD/Hour | USD/Month* | Use Case |
|--------|------|-----|---------|----------|------------|----------|
| Standard_B2s | 2 | 4GB | 30GB | $0.0416 | ~$30 | Single agent, sequential workflows |
| Standard_B2ms | 2 | 8GB | 30GB | $0.0832 | ~$60 | 1-3 concurrent workflows |
| Standard_B4ms | 4 | 16GB | 30GB | $0.166 | ~$120 | 3-5 concurrent workflows |

*Assumes 24/7 operation. Use Azure Reserved Instances for 30-40% savings.

### Cost Comparison: 100 Workers

| Strategy | VMs | Cloud PCs | Containers | Monthly Cost |
|----------|-----|-----------|------------|--------------|
| **All Computer Use VMs** | 100 | 0 | 0 | $6,000 |
| **All Cloud PCs** | 0 | 100 | 0 | $3,100 |
| **All Containers** | 0 | 0 | 100 | $200 |
| **Hybrid (10/15/75)** | 10 | 15 | 75 | $765 |

**Recommendation**: Use **hybrid strategy** with 10% Computer Use VMs for high-value workers, 15% Cloud PCs for desktop telemetry, 75% containers for scale.

---

**Last updated**: 2025-11-30
**Maintainer**: Azure HayMaker Team
**Status**: Production-ready
