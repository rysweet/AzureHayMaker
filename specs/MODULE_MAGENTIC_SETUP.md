# Module Specification: Magentic-UI Setup Manager

## Overview

**File Location**: `/src/azure_haymaker/provisioning/magentic_ui_setup.py`

**Responsibility**: Automated installation and configuration of Magentic-UI computer use agent on provisioned Cloud PCs via PowerShell remoting.

**Status**: Agent deployment component (Phase 2)

---

## 1. Purpose & Scope

### What It Does

The MagenticUISetupManager orchestrates agent deployment on Windows 365 Cloud PCs:

- **Bootstrap**: Enable required Windows features (PSRemoting, RDP, TLS 1.2)
- **Install**: Download and execute Magentic-UI agent package
- **Configure**: Write configuration files, set environment variables
- **Verify**: Health checks and service startup validation
- **Cleanup**: Service stop and resource cleanup

### What It Does NOT Do

- Cloud PC provisioning (W365CloudPCManager)
- User identity creation (orchestrator)
- Network configuration (Cloud PC network stack)
- Service monitoring (separate agent)

---

## 2. Class Design

### MagenticUISetupManager

**Principle**: Sequential setup with fallback retry mechanisms.

#### Constructor

```python
def __init__(
    self,
    cloud_pc_credentials: PSRemotingCredentials,
    deployment_id: str,
):
    """Initialize setup manager.

    Args:
        cloud_pc_credentials: PSRemotingCredentials with:
            - hostname: Cloud PC hostname or IP
            - username: Local admin username (e.g., "cloudpc\\admin")
            - password: Admin password
            - port: WinRM port (default 5985 or 5986 for TLS)
        deployment_id: Unique ID for this deployment (for logging/tagging)

    Raises:
        ValueError: If credentials missing required fields
    """
```

#### Instance Variables

```python
self.cloud_pc_credentials: PSRemotingCredentials
self.deployment_id: str
self.ps_client: PSRemotingClient | None  # Lazy-initialized
self.logger: logging.Logger
self.setup_state: SetupState  # Tracks what's been done
```

#### Constants

```python
# Windows features to enable
REQUIRED_FEATURES = [
    "PowerShell-Remoting",
    "TLS-1.2",
    "RemoteDesktop",
    "Internet-Explorer",  # For automation testing
]

# Service timeouts
BOOTSTRAP_TIMEOUT_SECONDS = 300
INSTALL_TIMEOUT_SECONDS = 600
CONFIG_TIMEOUT_SECONDS = 300
VERIFY_TIMEOUT_SECONDS = 120

# Retry configuration
MAX_CONNECTION_RETRIES = 5
CONNECTION_RETRY_DELAY_SECONDS = 10
CONNECTION_RETRY_BACKOFF = 2

# Package validation
PACKAGE_SIGNATURE_ALGORITHM = "SHA256"
MIN_PACKAGE_SIZE_MB = 50
MAX_PACKAGE_SIZE_MB = 500

# Service configuration
AGENT_SERVICE_NAME = "MagenticUIAgent"
AGENT_STARTUP_TYPE = "automatic"
AGENT_SERVICE_USER = "NT AUTHORITY\\NETWORK SERVICE"
AGENT_INSTALL_PATH = "C:\\Program Files\\MagenticUI"

# Telemetry
HEARTBEAT_INTERVAL_SECONDS = 60
HEARTBEAT_TIMEOUT_SECONDS = 10
```

---

## 3. Public Methods

### 1. bootstrap_cloud_pc()

**Purpose**: Enable required Windows features and prepare for agent installation.

**Signature**:
```python
async def bootstrap_cloud_pc(
    self,
    verify_only: bool = False,
) -> BootstrapResult:
    """Enable Windows features and prepare Cloud PC for agent.

    Runs with administrative privileges via PSRemoting.
    Idempotent: safe to call multiple times.

    Args:
        verify_only: If True, only verify features (don't enable)

    Returns:
        BootstrapResult:
            - success: bool
            - features_enabled: list[str]
            - features_already_enabled: list[str]
            - errors: list[str]
            - duration_seconds: float
            - restart_required: bool

    Raises:
        PSRemotingError: On connection failures
        BootstrapError: On permanent setup failures

    Flow:
        1. Establish PSRemoting connection (with retry):
           - Try to connect to hostname:port
           - If refused, retry with backoff
           - Max retries: MAX_CONNECTION_RETRIES
        2. Execute PowerShell script to:
           - Check OS version (must be Windows 10/11 build 19xxx+)
           - For each feature in REQUIRED_FEATURES:
             - Check if enabled
             - If not enabled and not verify_only:
               - Enable with Install-WindowsFeature
               - Verify enabled
             - Collect results
        3. Check for restart requirement
        4. Return BootstrapResult

    Error Handling:
        - Connection timeout → Retry with backoff
        - Feature enable fails → Log, continue with other features
        - Restart required → Return success=False, restart_required=True
        - Permission denied → BootstrapError (fail immediately)

    Side Effects:
        - May require Windows restart
        - Enables PowerShell Remoting on Cloud PC
        - Enables RDP (if not already enabled)

    Example:
        >>> result = await manager.bootstrap_cloud_pc()
        >>> if result.success:
        ...     print(f"Enabled: {result.features_enabled}")
        ...     if result.restart_required:
        ...         print("Restart required")
        ... else:
        ...     print(f"Bootstrap failed: {result.errors}")
    """
```

**Implementation Notes**:

- **Connection Retry**: Implement exponential backoff
  - Delay: 10s, 20s, 40s, 80s, 160s
  - Total max: ~5 minutes
- **Feature Enabling**:
  ```powershell
  # PowerShell script to run on Cloud PC
  Enable-WindowsOptionalFeature -FeatureName PowerShell-Remoting -Online -NoRestart
  ```
- **Idempotency**: Check feature state before enabling; skip if already enabled
- **Timeout**: 5 minutes max for bootstrap
- **Logging**: Log each feature enable attempt

---

### 2. download_agent_package()

**Purpose**: Download Magentic-UI package and verify signature.

**Signature**:
```python
async def download_agent_package(
    self,
    package_url: str,
    verify_signature: bool = True,
) -> PackageDownloadResult:
    """Download and verify Magentic-UI package.

    Downloads from URL, validates size and signature.
    Stores locally for transfer to Cloud PC.

    Args:
        package_url: URL to Magentic-UI package (must be HTTPS)
        verify_signature: If True, validate package signature

    Returns:
        PackageDownloadResult:
            - success: bool
            - local_path: Path | None (path to downloaded file)
            - size_mb: float
            - signature_valid: bool | None
            - duration_seconds: float

    Raises:
        PackageError: On download or signature failures

    Flow:
        1. Validate URL (must be HTTPS)
        2. Create temp directory for download
        3. Download package with retries:
           - Max retries: 3
           - Backoff: 5s, 10s, 20s
           - Timeout: 300s per download
        4. Validate size:
           - MIN_PACKAGE_SIZE_MB <= size <= MAX_PACKAGE_SIZE_MB
        5. If verify_signature:
           - Download signature file (package_url + ".sig")
           - Load signing certificate (from config/Key Vault)
           - Verify SHA256 signature
           - Return signature_valid in result
        6. Return PackageDownloadResult

    Error Handling:
        - URL validation fails → PackageError
        - Download timeout → Retry
        - Invalid size → PackageError
        - Signature mismatch → PackageError (if verify_signature=True)
        - Signature file not found → Warning, continue

    Security:
        - Only download from HTTPS URLs
        - Verify signature before using package
        - Store package in secure temp directory
        - Clean up temp files on completion

    Example:
        >>> result = await manager.download_agent_package(
        ...     package_url="https://releases.magenticui.com/v1.0.0/agent.msi",
        ...     verify_signature=True
        ... )
        >>> if result.success:
        ...     print(f"Downloaded: {result.local_path} ({result.size_mb}MB)")
        ... else:
        ...     print(f"Download failed")
    """
```

**Implementation Notes**:

- **URL Validation**: Use urllib.parse to validate HTTPS
- **Download**: Use aiohttp or httpx for async download with progress
- **Signature**: Use cryptography library for RSA/SHA256 verification
- **Cleanup**: Use context manager to ensure temp files cleaned up
- **Resume**: Support resume on partial download

---

### 3. install_agent()

**Purpose**: Transfer package to Cloud PC and execute installer.

**Signature**:
```python
async def install_agent(
    self,
    package_local_path: Path,
    agent_config: MagenticUIConfig,
) -> InstallResult:
    """Transfer and install Magentic-UI agent on Cloud PC.

    Transfers package via SMB, executes MSI installer,
    verifies installation success.

    Args:
        package_local_path: Path to downloaded .msi file
        agent_config: MagenticUIConfig with install parameters

    Returns:
        InstallResult:
            - success: bool
            - install_path: Path | None
            - version: str | None
            - service_installed: bool
            - duration_seconds: float
            - details: dict[str, Any]

    Raises:
        InstallError: On installation failures
        PSRemotingError: On connection failures

    Flow:
        1. Validate package exists and is readable
        2. Establish PSRemoting connection (with retry)
        3. Create install directory on Cloud PC:
           - mkdir C:\Program Files\MagenticUI
           - Set permissions (admin only)
        4. Transfer package via SMB/PSRemoting:
           - Use Copy-Item -ToSession to transfer
           - Monitor transfer progress
           - Verify size on destination
        5. Execute MSI installer via PSRemoting:
           - Command: msiexec /i agent.msi /passive /log install.log
           - Timeout: 600 seconds
           - Monitor installer process
           - Check exit code (0 = success)
        6. Verify installation:
           - Check install path exists
           - Query installed version
           - Check service is registered
        7. Return InstallResult

    Error Handling:
        - Package not found → InstallError
        - Connection lost → Retry with backoff
        - Transfer fails → Retry
        - Installer fails → Log installer output, InstallError
        - Service not registered → Log warning, continue

    Side Effects:
        - Copies 100+ MB to Cloud PC
        - Installs Windows service
        - May trigger Windows updates

    Example:
        >>> result = await manager.install_agent(
        ...     package_local_path=Path("/tmp/agent.msi"),
        ...     agent_config=MagenticUIConfig(...)
        ... )
        >>> if result.success:
        ...     print(f"Installed: {result.version}")
        ... else:
        ...     print(f"Installation failed")
    """
```

**Implementation Notes**:

- **Transfer**: Use PSRemoting Copy-Item for reliable transfer
- **Installation**:
  ```powershell
  # PowerShell script to run on Cloud PC
  $msiPath = "C:\Temp\agent.msi"
  $logPath = "C:\Temp\install.log"
  $exitCode = (Start-Process msiexec -ArgumentList "/i $msiPath /passive /log $logPath" -Wait -PassThru).ExitCode
  Exit $exitCode
  ```
- **Timeout**: 10 minutes for installation
- **Logging**: Capture installer log and return in details
- **Verification**: Query registry for installed version

---

### 4. configure_agent()

**Purpose**: Write configuration and prepare for startup.

**Signature**:
```python
async def configure_agent(
    self,
    agent_config: MagenticUIConfig,
    worker_identity: WorkerIdentity,
) -> ConfigResult:
    """Configure Magentic-UI agent for operation.

    Writes config files, sets environment variables,
    registers with orchestrator.

    Args:
        agent_config: MagenticUIConfig with agent settings
        worker_identity: WorkerIdentity for this agent

    Returns:
        ConfigResult:
            - success: bool
            - config_path: Path | None
            - service_configured: bool
            - telemetry_enabled: bool
            - errors: list[str]
            - duration_seconds: float

    Raises:
        ConfigError: On configuration failures

    Flow:
        1. Generate configuration:
           - Create MagenticUIConfig JSON
           - Include telemetry settings
           - Include API endpoint
           - Include worker identity
        2. Generate environment variables:
           - MAGENTIC_UI_WORKER_ID=worker.worker_id
           - MAGENTIC_UI_DEPLOYMENT_ID=deployment_id
           - MAGENTIC_UI_TELEMETRY_ENABLED=true/false
           - MAGENTIC_UI_LOG_LEVEL=INFO/DEBUG
        3. Write via PSRemoting:
           - Write config.json to install path
           - Write env vars to service startup
           - Set file permissions (admin only read)
        4. Configure Windows service:
           - Service: MagenticUIAgent
           - Set startup type: automatic
           - Set service user: NETWORK SERVICE
           - Set startup parameters from config
        5. Validate configuration:
           - Read back and verify
           - Check service properties
        6. Return ConfigResult

    Error Handling:
        - Config validation fails → ConfigError
        - Write fails → Log, ConfigError
        - Service config fails → Log, continue with warning
        - Invalid worker_identity → ConfigError

    Side Effects:
        - Modifies service startup configuration
        - Creates config files on Cloud PC
        - Sets environment variables

    Example:
        >>> result = await manager.configure_agent(
        ...     agent_config=MagenticUIConfig(...),
        ...     worker_identity=worker
        ... )
        >>> if result.success:
        ...     print("Agent configured and ready for startup")
        ... else:
        ...     print(f"Configuration failed: {result.errors}")
    """
```

**Implementation Notes**:

- **Config Format**: JSON with all settings
- **Validation**: Validate config before writing
- **Service Configuration**:
  ```powershell
  # PowerShell script
  New-Service -Name MagenticUIAgent `
    -DisplayName "Magentic-UI Agent" `
    -BinaryPathName "C:\Program Files\MagenticUI\agent.exe" `
    -StartupType Automatic `
    -StartupUserType NetworkService
  ```
- **Permissions**: Restrict config file to admin read-only
- **Idempotency**: Safe to rerun; overwrites config

---

### 5. start_agent_service()

**Purpose**: Start Magentic-UI agent service.

**Signature**:
```python
async def start_agent_service(
    self,
    timeout_seconds: int | None = None,
) -> ServiceStartResult:
    """Start Magentic-UI agent Windows service.

    Issues start command and waits for service to reach running state.

    Args:
        timeout_seconds: Timeout waiting for service start (default: 120)

    Returns:
        ServiceStartResult:
            - success: bool
            - service_state: str ("Running", "Stopped", "StartPending")
            - duration_seconds: float
            - error_message: str | None

    Raises:
        ServiceError: On start failures

    Flow:
        1. Establish PSRemoting connection
        2. Start service:
           - net start MagenticUIAgent
           - OR: Start-Service MagenticUIAgent
        3. Wait for service running state:
           - Poll service status every 2 seconds
           - Max timeout: 120 seconds
           - Stop polling when Running or timeout
        4. Return ServiceStartResult

    Error Handling:
        - Service not found → ServiceError
        - Start fails → ServiceError with exit code
        - Timeout → ServiceError (still in StartPending)
        - Connection lost → Retry with backoff

    Example:
        >>> result = await manager.start_agent_service()
        >>> if result.success:
        ...     print(f"Service: {result.service_state}")
        ... else:
        ...     print(f"Service start failed: {result.error_message}")
    """
```

**Implementation Notes**:

- **Service Command**:
  ```powershell
  Start-Service -Name MagenticUIAgent -ErrorAction Stop
  ```
- **Status Polling**:
  ```powershell
  Get-Service -Name MagenticUIAgent | Select-Object -ExpandProperty Status
  ```
- **Timeout**: 2 minutes max
- **Retry**: If start fails, may retry service restart

---

### 6. verify_agent_ready()

**Purpose**: Comprehensive verification that agent is ready.

**Signature**:
```python
async def verify_agent_ready(
    self,
    timeout_seconds: int | None = None,
) -> AgentReadyResult:
    """Verify Magentic-UI agent is ready for operations.

    Performs comprehensive health checks including:
    - Service running
    - API responding
    - Heartbeat working
    - Telemetry flowing

    Args:
        timeout_seconds: Timeout for verification (default: 300)

    Returns:
        AgentReadyResult:
            - ready: bool (all checks passed)
            - checks: dict[str, CheckResult]
              - "service_running": bool
              - "api_responding": bool
              - "heartbeat_healthy": bool
              - "telemetry_flowing": bool
            - duration_seconds: float
            - details: dict[str, Any]

    Raises:
        VerificationError: On critical failures

    Flow:
        1. Check service running:
           - Query service status
           - Must be in "Running" state
        2. Check API responding:
           - Make HTTP request to agent API
           - GET /api/health
           - Must return 200 OK
        3. Check heartbeat:
           - Listen for agent heartbeat events
           - Wait up to 60 seconds
           - Must receive at least one heartbeat
        4. Check telemetry:
           - Query Service Bus for recent events
           - Must have events in last 60 seconds
        5. Return AgentReadyResult

    Error Handling:
        - Service not running → ready=False
        - API not responding → Retry with backoff
        - No heartbeat → ready=False (agent not communicating)
        - No telemetry → ready=False (not sending data)

    Example:
        >>> result = await manager.verify_agent_ready()
        >>> if result.ready:
        ...     print("Agent ready for operation")
        ...     for check, passed in result.checks.items():
        ...         print(f"  {check}: {'PASS' if passed else 'FAIL'}")
        ... else:
        ...     print(f"Agent not ready")
    """
```

**Implementation Notes**:

- **Service Check**: Query Windows service status
- **API Check**: Make HTTP call to localhost:agent_api_port/health
- **Heartbeat**: Listen to Service Bus topic for agent heartbeats
- **Telemetry**: Query Service Bus subscription for recent events
- **Timeout**: 5 minutes total, with individual timeouts per check

---

### 7. cleanup_agent()

**Purpose**: Stop agent and cleanup resources.

**Signature**:
```python
async def cleanup_agent(
    self,
    remove_data: bool = True,
) -> CleanupResult:
    """Stop agent service and cleanup resources.

    Stops service, optionally removes data, frees resources.

    Args:
        remove_data: If True, delete config and logs

    Returns:
        CleanupResult:
            - success: bool
            - service_stopped: bool
            - data_removed: bool
            - freed_disk_mb: float
            - duration_seconds: float

    Raises:
        CleanupError: On cleanup failures

    Flow:
        1. Stop service:
           - net stop MagenticUIAgent
           - Wait for stop (up to 30 seconds)
        2. If remove_data:
           - Delete config.json
           - Delete logs
           - Delete temp files
           - Uninstall service (optional)
        3. Return CleanupResult

    Error Handling:
        - Service already stopped → OK
        - Stop timeout → Log warning, continue
        - Delete fails → Log warning, continue

    Example:
        >>> result = await manager.cleanup_agent(remove_data=True)
        >>> if result.success:
        ...     print(f"Freed {result.freed_disk_mb}MB")
        ... else:
        ...     print("Cleanup had errors")
    """
```

**Implementation Notes**:

- **Service Stop**:
  ```powershell
  Stop-Service -Name MagenticUIAgent -Force -ErrorAction SilentlyContinue
  ```
- **Data Removal**: Delete install directory (if requested)
- **Timeout**: 1 minute for service stop
- **Idempotency**: Safe to call multiple times

---

## 4. Error Handling

### Custom Exceptions

```python
class MagenticUISetupError(Exception):
    """Base setup error."""
    pass

class PSRemotingError(MagenticUISetupError):
    """PowerShell Remoting connection error."""
    pass

class BootstrapError(MagenticUISetupError):
    """Windows feature bootstrap error."""
    pass

class PackageError(MagenticUISetupError):
    """Package download/validation error."""
    pass

class InstallError(MagenticUISetupError):
    """Installation error."""
    pass

class ConfigError(MagenticUISetupError):
    """Configuration error."""
    pass

class ServiceError(MagenticUISetupError):
    """Service operation error."""
    pass

class VerificationError(MagenticUISetupError):
    """Verification error."""
    pass

class CleanupError(MagenticUISetupError):
    """Cleanup error."""
    pass
```

### Retry Helpers

```python
async def _retry_psremoting_command(
    self,
    command: str,
    timeout_seconds: int = 300,
    max_retries: int = 3,
) -> tuple[bool, str]:
    """Execute PowerShell command with retry on connection failure."""
    # Retry connection failures, not command failures
    # If command fails, return error immediately
```

---

## 5. Data Models

```python
@dataclass
class PSRemotingCredentials:
    """PowerShell Remoting connection credentials."""
    hostname: str  # Cloud PC hostname or IP
    username: str  # Local admin username
    password: str  # Admin password (from Key Vault)
    port: int = 5985  # WinRM port (5985 HTTP or 5986 HTTPS)
    use_https: bool = False

@dataclass
class MagenticUIConfig:
    """Magentic-UI agent configuration."""
    agent_version: str
    package_url: str
    telemetry_enabled: bool = True
    logging_level: str = "INFO"
    api_endpoint: str = ""
    max_concurrent_tasks: int = 5
    custom_config: dict[str, Any] = field(default_factory=dict)

@dataclass
class BootstrapResult:
    """Bootstrap operation result."""
    success: bool
    features_enabled: list[str] = field(default_factory=list)
    features_already_enabled: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    restart_required: bool = False

@dataclass
class PackageDownloadResult:
    """Package download result."""
    success: bool
    local_path: Path | None = None
    size_mb: float = 0.0
    signature_valid: bool | None = None
    duration_seconds: float = 0.0

@dataclass
class InstallResult:
    """Installation result."""
    success: bool
    install_path: Path | None = None
    version: str | None = None
    service_installed: bool = False
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class ConfigResult:
    """Configuration result."""
    success: bool
    config_path: Path | None = None
    service_configured: bool = False
    telemetry_enabled: bool = False
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

@dataclass
class ServiceStartResult:
    """Service start result."""
    success: bool
    service_state: str = ""
    duration_seconds: float = 0.0
    error_message: str | None = None

@dataclass
class CheckResult:
    """Single verification check result."""
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentReadyResult:
    """Agent readiness verification result."""
    ready: bool
    checks: dict[str, CheckResult] = field(default_factory=dict)
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class CleanupResult:
    """Cleanup operation result."""
    success: bool
    service_stopped: bool = False
    data_removed: bool = False
    freed_disk_mb: float = 0.0
    duration_seconds: float = 0.0
```

---

## 6. Testing Strategy

### Unit Tests

```python
test_bootstrap_success()
test_bootstrap_idempotent()
test_bootstrap_connection_retry()
test_bootstrap_feature_already_enabled()
test_bootstrap_permission_denied()

test_download_package_success()
test_download_package_signature_valid()
test_download_package_signature_invalid()
test_download_package_size_validation()
test_download_package_retry_on_timeout()

test_install_agent_success()
test_install_agent_transfer_fails()
test_install_agent_installer_fails()
test_install_agent_version_check()
test_install_agent_service_registered()

test_configure_agent_success()
test_configure_agent_config_validation()
test_configure_agent_service_configuration()
test_configure_agent_telemetry_settings()

test_start_service_success()
test_start_service_already_running()
test_start_service_timeout()
test_start_service_not_found()

test_verify_agent_ready_all_checks_pass()
test_verify_agent_ready_service_not_running()
test_verify_agent_ready_api_not_responding()
test_verify_agent_ready_no_heartbeat()
test_verify_agent_ready_timeout()

test_cleanup_agent_success()
test_cleanup_agent_idempotent()
test_cleanup_agent_remove_data()
```

### Mocks

```python
@pytest.fixture
def mock_psremoting_client():
    """Mock PSRemoting client."""
    return MagicMock()

@pytest.fixture
def mock_service_bus_client():
    """Mock Service Bus client."""
    return MagicMock()

@pytest.fixture
def manager(mock_psremoting_client):
    """MagenticUISetupManager with mocked dependencies."""
    credentials = PSRemotingCredentials(
        hostname="cloudpc-001",
        username="admin",
        password="test-password"
    )
    return MagenticUISetupManager(credentials, "deploy-001")
```

---

## 7. Success Criteria

- [ ] All public methods implemented with full error handling
- [ ] PSRemoting connection with retry logic
- [ ] Package download and signature verification
- [ ] MSI installation via remote scripting
- [ ] Configuration file generation and validation
- [ ] Windows service management
- [ ] Comprehensive health checks
- [ ] Unit tests with 90%+ coverage
- [ ] Integration tests against real Cloud PC (staging)
- [ ] No hardcoded credentials
- [ ] Complete logging and error reporting
- [ ] Type hints and validation

---

## 8. Dependencies

### Internal
- `azure_haymaker.knowledge_worker.models.worker` - WorkerIdentity
- `azure_haymaker.provisioning.models` - Data models

### External
- `pypsrp` - PowerShell Remoting Protocol
- `cryptography` - Package signature verification
- `aiohttp` or `httpx` - HTTP requests
- `azure.servicebus` - Event listening
- Standard library: `asyncio`, `logging`, `tempfile`, `pathlib`, `json`

---

## 9. Future Enhancements

- [ ] Multi-Cloud PC concurrent setup
- [ ] Automatic Cloud PC image selection
- [ ] Agent health monitoring integration
- [ ] Automated agent updates/patching
- [ ] Configuration templating system
- [ ] Advanced telemetry collection
