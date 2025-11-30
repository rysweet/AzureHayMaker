# Module Specification: W365 Cloud PC Manager

## Overview

**File Location**: `/src/azure_haymaker/provisioning/w365_manager.py`

**Responsibility**: Orchestrate Windows 365 Cloud PC provisioning via Microsoft Graph API `deviceManagement/virtualEndpoint` endpoint.

**Status**: Core provisioning component (Phase 1)

---

## 1. Purpose & Scope

### What It Does

The W365CloudPCManager encapsulates all interactions with the Windows 365 service via Microsoft Graph API beta endpoint:

- **Policy Management**: Create, retrieve, and validate provisioning policies
- **User Assignment**: Assign users to policies (triggers async provisioning)
- **Status Tracking**: Poll for provisioning completion with exponential backoff
- **Cloud PC Retrieval**: Query details of provisioned Cloud PCs
- **Lifecycle Operations**: Delete Cloud PCs and cleanup resources

### What It Does NOT Do

- User/identity creation (handled elsewhere)
- License assignment (prerequisite)
- Network configuration (handled by W365 service)
- Agent installation (separate concern)

---

## 2. Class Design

### W365CloudPCManager

**Principle**: Stateless wrapper around Graph API calls with retry logic.

#### Constructor

```python
def __init__(
    self,
    graph_client: GraphServiceClient,
    run_id: str,
):
    """Initialize manager.

    Args:
        graph_client: Authenticated GraphServiceClient with proper permissions:
            - DeviceManagementConfiguration.Read.All
            - DeviceManagementConfiguration.Write.All
            - DeviceManagementManagedDevices.Read.All
            - DeviceManagementManagedDevices.Write.All
        run_id: Unique identifier for this provisioning run (for resource tagging)

    Raises:
        ValueError: If graph_client is None
    """
```

#### Instance Variables

```python
self.graph_client: GraphServiceClient  # Authenticated client
self.run_id: str  # Run ID for resource tracking
self.logger: logging.Logger  # Logger instance
```

#### Constants

```python
# SKU definitions (from W365 documentation)
DEFAULT_SKU = "CPC_S_2C_4GB_64GB"  # Single user, 2vCPU, 4GB RAM, 64GB

# Gallery image (Windows 11 Enterprise with M365)
DEFAULT_IMAGE = "MicrosoftWindowsDesktop_windows-ent-cpc_win11-22h2-ent-cpc-m365"

# Timeouts and intervals
PROVISIONING_TIMEOUT_MINUTES = 90
PROVISIONING_CHECK_INTERVAL_SECONDS = 60
PROVISIONING_READY_POLL_TIMEOUT = timedelta(minutes=PROVISIONING_TIMEOUT_MINUTES)

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # seconds
MAX_RETRY_DELAY = 30  # seconds
EXPONENTIAL_BASE = 2
RETRY_BACKOFF_JITTER = 0.1  # ±10%

# Policy naming
PROVISIONING_POLICY_NAME_TEMPLATE = "HayMaker-{run_id}-Policy"
CLOUD_PC_NAMING_TEMPLATE = "kw-{run_id[:8]}-%RAND:5%"
```

---

## 3. Public Methods

### 1. ensure_provisioning_policy()

**Purpose**: Get existing or create new provisioning policy.

**Signature**:
```python
async def ensure_provisioning_policy(
    self,
    display_name: str | None = None,
    image_id: str | None = None,
    sku_id: str | None = None,
    tenant_id: str | None = None,
) -> str:
    """Get existing or create provisioning policy.

    Tries to find existing policy first (idempotent).
    If not found, creates new policy with provided parameters.

    Args:
        display_name: Policy display name (default: HayMaker-{run_id}-Policy)
        image_id: Gallery image ID (default: Windows 11 Enterprise)
        sku_id: Cloud PC SKU (default: CPC_S_2C_4GB_64GB)
        tenant_id: Azure AD tenant ID (for Entra join)

    Returns:
        Policy ID (str)

    Raises:
        ProvisioningError: On permanent failures (validation errors, permission denied)
        TimeoutError: On timeout during policy creation polling

    Flow:
        1. Validate inputs (non-empty display_name, valid image/sku)
        2. Query existing policies (filter by display_name)
        3. If found:
           - Log and return policy ID
        4. If not found:
           - Build policy request body
           - POST to /deviceManagement/virtualEndpoint/provisioning policies
           - Wait for async creation to complete (polling with timeout)
           - Return policy ID

    Example:
        >>> manager = W365CloudPCManager(graph_client, "run-001")
        >>> policy_id = await manager.ensure_provisioning_policy(
        ...     display_name="Engineering-Policy",
        ...     image_id="...",
        ...     sku_id="CPC_S_4C_8GB_128GB"
        ... )
        >>> print(f"Using policy: {policy_id}")
    """
```

**Implementation Notes**:

- **Idempotency**: Safe to call multiple times; checks for existing policy by display_name
- **Polling**: Policy creation is async; may need to poll status until "succeeded"
- **Error Handling**:
  - Validation errors (bad image/sku) → ProvisioningError (fail immediately)
  - API errors (timeout, 500) → Retry with exponential backoff
  - Permission denied → ProvisioningError (fail immediately)
- **Logging**: Log all operations with run_id context
- **Timeout**: If creation takes >5 minutes, fail with TimeoutError

---

### 2. provision_cloud_pc()

**Purpose**: Assign user to provisioning policy (triggers async provisioning).

**Signature**:
```python
async def provision_cloud_pc(
    self,
    worker: WorkerIdentity,
    policy_id: str,
) -> ProvisioningResult:
    """Assign user to policy, triggering Cloud PC provisioning.

    This is an async operation. The Cloud PC will be provisioned
    in the background over 30-90 minutes. Use wait_for_provisioning()
    to poll for completion.

    Args:
        worker: WorkerIdentity with user_principal_name
        policy_id: ID of provisioning policy

    Returns:
        ProvisioningResult:
            - success: bool (True if assignment succeeded)
            - resource_id: str | None (assignment ID)
            - metadata:
                - "user_upn": worker UPN
                - "policy_id": policy ID
                - "assignment_timestamp": ISO 8601

    Raises:
        ProvisioningError: On validation failures
        ValueError: If worker.user_principal_name is empty

    Flow:
        1. Validate inputs:
           - worker.user_principal_name is set
           - policy_id is non-empty
        2. Check if user already has Cloud PC (avoid duplicates)
        3. POST assignment to /deviceManagement/virtualEndpoint/provisioning policies/{id}/assignments
        4. Return result with assignment ID

    Side Effects:
        - Triggers async Cloud PC provisioning in W365 backend
        - User will receive email notification

    Example:
        >>> result = await manager.provision_cloud_pc(
        ...     worker=WorkerIdentity(user_principal_name="user@tenant.onmicrosoft.com", ...),
        ...     policy_id="abc123"
        ... )
        >>> if result.success:
        ...     print(f"Provisioning started for {worker.display_name}")
        ... else:
        ...     print(f"Failed: {result.error_message}")
    """
```

**Implementation Notes**:

- **Async Nature**: This method returns immediately; provisioning continues in background
- **Duplicate Check**: Query existing Cloud PCs first to avoid duplicate assignments
- **Error Handling**:
  - Duplicate user → Return success (already provisioned)
  - User not found in tenant → ProvisioningError
  - Policy not found → ProvisioningError
  - Permission denied → ProvisioningError
- **Success Definition**: Assignment record created, not Cloud PC provisioned

---

### 3. wait_for_provisioning()

**Purpose**: Poll for Cloud PC provisioning completion with timeout.

**Signature**:
```python
async def wait_for_provisioning(
    self,
    worker: WorkerIdentity,
    timeout_minutes: int | None = None,
) -> ProvisioningStatus:
    """Poll Graph API until Cloud PC is provisioned or timeout.

    Polls every PROVISIONING_CHECK_INTERVAL_SECONDS (default 60s).
    Stops when status is "provisioned", "failed", or timeout expires.

    Args:
        worker: WorkerIdentity with user_principal_name
        timeout_minutes: Timeout in minutes (default: 90)

    Returns:
        ProvisioningStatus:
            - status: str ("provisioned", "provisioning", "failed", "timeout")
            - cloud_pc_id: str | None (if provisioned)
            - ip_address: str | None (if provisioned)
            - error_message: str | None (if failed)
            - elapsed_minutes: float

    Raises:
        ValueError: If worker.user_principal_name is empty

    Flow:
        1. Calculate deadline = now + timeout_minutes
        2. Loop:
           a. Query /deviceManagement/virtualEndpoint/cloudPCs
              Filter: userPrincipalName eq 'user@tenant.onmicrosoft.com'
           b. If result not found:
              - Log debug, sleep, continue
           c. If found, check status property:
              - "provisioned" → Return ProvisioningStatus(status="provisioned", ...)
              - "provisioning" → Log, sleep, continue
              - "failed" / "error" → Return with error details
           d. If now >= deadline:
              - Return ProvisioningStatus(status="timeout", ...)
           e. Sleep for interval_seconds

    Example:
        >>> status = await manager.wait_for_provisioning(
        ...     worker=worker,
        ...     timeout_minutes=90
        ... )
        >>> if status.status == "provisioned":
        ...     print(f"Cloud PC ready at {status.ip_address}")
        ... elif status.status == "timeout":
        ...     print("Provisioning took too long")
        ... else:
        ...     print(f"Provisioning failed: {status.error_message}")
    """
```

**Implementation Notes**:

- **Poll Interval**: Default 60 seconds (configurable via constant)
- **Status Mapping**:
  - "provisioned" → Success
  - "provisioning" → Continue waiting
  - "failed" / "error" → Failure
  - No status found → Continue waiting (not yet started)
- **Timeout Handling**: Log warning at 50%, 75%, 90% of timeout
- **Error Handling**:
  - API errors → Retry with backoff (up to MAX_RETRIES)
  - After max retries, continue polling (transient errors)
- **Performance**: Avoid excessive polling; 60s interval balances latency vs. API load

---

### 4. get_cloud_pc()

**Purpose**: Retrieve Cloud PC details for a worker.

**Signature**:
```python
async def get_cloud_pc(
    self,
    worker: WorkerIdentity,
) -> CloudPCInfo | None:
    """Get Cloud PC information for a worker.

    Queries Graph API for Cloud PC assigned to worker's UPN.

    Args:
        worker: WorkerIdentity with user_principal_name

    Returns:
        CloudPCInfo | None:
            - id: str (Cloud PC ID in W365)
            - display_name: str
            - status: str ("provisioned", "provisioning", etc.)
            - user_principal_name: str
            - ip_address: str | None
            - managed_device_id: str | None (Intune device ID)
            - rdp_endpoint: str | None (RDP connection string)
            Returns None if not found

    Raises:
        ProvisioningError: On API errors

    Flow:
        1. Query /deviceManagement/virtualEndpoint/cloudPCs
           Filter: userPrincipalName eq 'user@tenant.onmicrosoft.com'
        2. If no results, return None
        3. If multiple results, log warning and return first
        4. Extract fields and return CloudPCInfo

    Example:
        >>> pc = await manager.get_cloud_pc(worker)
        >>> if pc:
        ...     print(f"Cloud PC: {pc.display_name}")
        ...     print(f"Status: {pc.status}")
        ...     print(f"IP: {pc.ip_address}")
        ... else:
        ...     print("Cloud PC not found")
    """
```

**Implementation Notes**:

- **Caching**: Results are not cached; always query Graph API
- **Error Handling**: Return None on not found (don't raise); raise on API errors
- **IP Address**: Only populated after provisioning completes

---

### 5. delete_cloud_pc()

**Purpose**: Delete a Cloud PC.

**Signature**:
```python
async def delete_cloud_pc(
    self,
    cloud_pc_id: str,
) -> bool:
    """Delete a Cloud PC.

    Issues delete request to Graph API.
    Returns immediately (async operation in backend).

    Args:
        cloud_pc_id: Cloud PC ID from W365

    Returns:
        bool: True if delete request accepted, False on error

    Raises:
        ProvisioningError: On permanent failures (not found, forbidden)

    Flow:
        1. DELETE /deviceManagement/virtualEndpoint/cloudPCs/{id}
        2. If successful (204 or 200), return True
        3. If 404 (not found), return True (already deleted)
        4. If other errors, raise ProvisioningError

    Side Effects:
        - Cloud PC will be deleted in background (5-15 minutes)
        - User will receive email notification
        - Any user data will be wiped

    Example:
        >>> success = await manager.delete_cloud_pc("cloudpc-123")
        >>> if success:
        ...     print("Delete request accepted")
        ... else:
        ...     print("Delete failed")
    """
```

**Implementation Notes**:

- **Async Operation**: Returns immediately; deletion continues in backend
- **Idempotent**: Deleting already-deleted Cloud PC is OK (returns True)
- **Error Handling**: Only fail on permission errors or validation errors

---

### 6. list_cloud_pcs_for_run()

**Purpose**: List all Cloud PCs for this run.

**Signature**:
```python
async def list_cloud_pcs_for_run(self) -> list[CloudPCInfo]:
    """List all Cloud PCs for this provisioning run.

    Queries Graph API for all Cloud PCs and filters by run ID
    (via display_name pattern matching).

    Returns:
        List of CloudPCInfo dictionaries

    Raises:
        ProvisioningError: On API errors

    Flow:
        1. Query /deviceManagement/virtualEndpoint/cloudPCs (no filter)
        2. Filter locally:
           - Extract run_id prefix from display_name (kw-{run_id[:8]})
           - Match against self.run_id
        3. Return matching Cloud PCs

    Example:
        >>> pcs = await manager.list_cloud_pcs_for_run()
        >>> for pc in pcs:
        ...     print(f"{pc.display_name}: {pc.status}")
    """
```

**Implementation Notes**:

- **Filtering**: Done locally (Graph API filtering limited)
- **Performance**: May return large result set; paginate if needed
- **Error Handling**: Fail on API errors; return empty list on not found

---

## 4. Error Handling

### Custom Exceptions

```python
class ProvisioningError(Exception):
    """Permanent provisioning failure."""
    pass

class ProvisioningTimeout(Exception):
    """Provisioning timeout exceeded."""
    pass

class ProvisioningRetryable(Exception):
    """Transient error; safe to retry."""
    pass
```

### Retry Strategy

```python
async def _retry_api_call(
    self,
    func: Callable,
    *args,
    **kwargs,
) -> Any:
    """Execute func with exponential backoff retry.

    Args:
        func: Async function to call
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result from func

    Raises:
        ProvisioningError: On permanent failures
        ProvisioningTimeout: If all retries exhausted
    """
    # Implementation:
    # For i in range(MAX_RETRIES):
    #   Try func(*args, **kwargs)
    #   If success, return result
    #   If permanent error (validation, permission), raise ProvisioningError
    #   If transient error, calculate backoff and sleep
    # After max retries, raise ProvisioningTimeout
```

---

## 5. Data Models

### CloudPCInfo

```python
@dataclass
class CloudPCInfo:
    """Cloud PC details from Graph API."""
    id: str
    display_name: str
    status: str
    user_principal_name: str
    ip_address: str | None = None
    managed_device_id: str | None = None
    rdp_endpoint: str | None = None
```

### ProvisioningResult

```python
@dataclass
class ProvisioningResult:
    """Result of a provisioning operation."""
    success: bool
    resource_id: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
```

### ProvisioningStatus

```python
@dataclass
class ProvisioningStatus:
    """Cloud PC provisioning status."""
    status: str  # "provisioned", "provisioning", "failed", "timeout"
    cloud_pc_id: str | None = None
    ip_address: str | None = None
    error_message: str | None = None
    elapsed_minutes: float = 0.0
```

---

## 6. Testing Strategy

### Unit Tests

```python
# Test ensure_provisioning_policy()
test_policy_creation_success()  # Happy path
test_policy_creation_idempotent()  # Returns existing policy
test_policy_creation_invalid_sku()  # Validation error
test_policy_creation_timeout()  # Polling timeout
test_policy_creation_permission_denied()  # Auth error

# Test provision_cloud_pc()
test_provision_user_success()  # Happy path
test_provision_duplicate_user()  # Already provisioned
test_provision_invalid_user()  # User not found
test_provision_invalid_policy()  # Policy not found

# Test wait_for_provisioning()
test_wait_success()  # Cloud PC becomes ready
test_wait_timeout()  # Timeout exceeded
test_wait_failure()  # Cloud PC provisioning fails
test_wait_polling_interval()  # Correct poll interval

# Test get_cloud_pc()
test_get_existing_cloud_pc()  # Happy path
test_get_nonexistent_cloud_pc()  # Returns None
test_get_multiple_cloud_pcs()  # Logs warning, returns first

# Test delete_cloud_pc()
test_delete_success()  # Happy path
test_delete_already_deleted()  # Idempotent
test_delete_permission_denied()  # Auth error

# Test list_cloud_pcs_for_run()
test_list_cloud_pcs()  # Returns filtered list
test_list_empty()  # No Cloud PCs for run
test_list_api_error()  # API error handling
```

### Mock Fixtures

```python
@pytest.fixture
def mock_graph_client():
    """Mock GraphServiceClient."""
    return MagicMock(spec=GraphServiceClient)

@pytest.fixture
def manager(mock_graph_client):
    """W365CloudPCManager instance with mocked client."""
    return W365CloudPCManager(mock_graph_client, "test-run-001")

@pytest.fixture
def sample_worker():
    """Sample WorkerIdentity."""
    return WorkerIdentity(
        worker_id="kw-001",
        display_name="Test Worker",
        user_principal_name="test@tenant.onmicrosoft.com",
        department="engineering",
        persona=WorkerPersona.ENGINEERING,
        endpoint_type=EndpointType.CLOUD_PC,
    )
```

---

## 7. Example Usage

```python
# Initialize
graph_client = get_authenticated_graph_client()
manager = W365CloudPCManager(graph_client, run_id="haymaker-001")

# Ensure provisioning policy exists
policy_id = await manager.ensure_provisioning_policy(
    display_name="Engineering-Policy",
    sku_id="CPC_S_2C_4GB_64GB",
)

# Provision Cloud PC for worker
result = await manager.provision_cloud_pc(
    worker=worker,
    policy_id=policy_id,
)

# Wait for provisioning to complete
status = await manager.wait_for_provisioning(
    worker=worker,
    timeout_minutes=90,
)

if status.status == "provisioned":
    # Get Cloud PC details
    pc = await manager.get_cloud_pc(worker)
    print(f"Cloud PC: {pc.ip_address}")
else:
    print(f"Failed: {status.error_message}")

# Cleanup when done
await manager.delete_cloud_pc(pc.id)
```

---

## 8. Logging

Log all operations with context:

```
INFO: Ensuring provisioning policy: Engineering-Policy (run: haymaker-001)
INFO: Found existing policy: abc123
DEBUG: Checking Cloud PC status for user@tenant.onmicrosoft.com
DEBUG: Status: provisioning (2% complete)
WARNING: Cloud PC provisioning taking longer than expected (>30 min)
ERROR: Cloud PC provisioning failed: insufficient quota
```

---

## 9. Dependencies

### Internal
- `azure_haymaker.knowledge_worker.models.worker` - WorkerIdentity
- `azure_haymaker.provisioning.models` - ProvisioningResult, etc.

### External
- `msgraph.core.GraphServiceClient` - Graph API client
- `azure.identity` - Azure auth
- Standard library: `asyncio`, `logging`, `dataclasses`, `datetime`, `time`

---

## 10. Success Criteria

- [ ] All public methods implemented with full error handling
- [ ] Async/await properly used throughout
- [ ] Exponential backoff retry logic working
- [ ] Timeout handling enforced
- [ ] All methods logged with context
- [ ] Unit tests achieve 90%+ coverage
- [ ] Integration tests pass against Graph API (beta)
- [ ] No hardcoded secrets or credentials
- [ ] Type hints complete and validated
- [ ] Documentation complete

---

## 11. Future Enhancements

- [ ] Implement policy versioning (track policy history)
- [ ] Add metrics/telemetry collection
- [ ] Support for multi-region provisioning
- [ ] Advanced filtering for list_cloud_pcs_for_run()
- [ ] Bulk provisioning optimization
- [ ] Machine learning for optimal SKU selection
