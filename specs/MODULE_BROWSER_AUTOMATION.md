# Module Specification: Browser Automation & E2E Testing

## Overview

**File Location**: `/src/azure_haymaker/testing/browser_automation.py`

**Responsibility**: Execute automated E2E test scenarios on provisioned Cloud PCs via Selenium, validating Magentic-UI agent capabilities and M365 integrations.

**Status**: E2E testing component (Phase 4)

---

## 1. Purpose & Scope

### What It Does

The BrowserAutomationTester orchestrates browser-based E2E testing:

- **RDP Connection**: Establish remote desktop session to Cloud PC
- **Browser Control**: Launch and control Chrome/Edge via Selenium
- **Navigation**: Automated navigation to M365 applications
- **Interactions**: Click, type, form submission, etc.
- **Verification**: Assert expected behavior and state
- **Screenshot Capture**: Capture key states for reporting
- **Performance Metrics**: Measure page load times, action latencies
- **Report Generation**: JSON and HTML test reports

### What It Does NOT Do

- Unit testing of agent code (separate concern)
- Performance profiling beyond basic metrics
- Security/penetration testing
- Cross-browser compatibility testing (single browser focus)
- Load testing

---

## 2. Class Design

### BrowserAutomationTester

**Principle**: Modular test scenarios, reusable steps, comprehensive logging.

#### Constructor

```python
def __init__(
    self,
    cloud_pc_info: CloudPCInfo,
    browser_type: str = "chrome",  # "chrome" or "edge"
):
    """Initialize browser automation tester.

    Args:
        cloud_pc_info: CloudPCInfo with RDP connection details
        browser_type: Browser to use ("chrome" or "edge")

    Raises:
        ValueError: If cloud_pc_info invalid
    """
```

#### Instance Variables

```python
self.cloud_pc_info: CloudPCInfo
self.browser_type: str
self.rdp_session: Any | None  # RDP session object
self.driver: Any | None  # Selenium WebDriver
self.logger: logging.Logger
self.test_results: list[TestResult] = []
self.screenshots: list[ScreenshotRecord] = []
self.performance_metrics: dict[str, Any] = {}
```

#### Constants

```python
# Timeouts
RDP_CONNECTION_TIMEOUT = 60  # seconds
RDP_CONNECTION_RETRY_MAX = 3
RDP_CONNECTION_RETRY_DELAY = 10

BROWSER_LAUNCH_TIMEOUT = 30  # seconds
ELEMENT_WAIT_TIMEOUT = 10  # seconds
PAGE_LOAD_TIMEOUT = 30  # seconds
TEST_SCENARIO_TIMEOUT = 300  # 5 minutes

# Selenium configuration
SELENIUM_HEADLESS = True
SELENIUM_ARGS = [
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-extensions",
]

# Test data
TEST_DATA = {
    "email": "test@tenant.onmicrosoft.com",
    "test_message": "E2E test message from Magentic-UI automation",
    "test_subject": "[TEST] Magentic-UI E2E Test",
}

# Performance thresholds
PAGE_LOAD_THRESHOLD_MS = 5000  # Warning if >5 sec
ACTION_LATENCY_THRESHOLD_MS = 1000  # Warning if >1 sec

# Screenshot capture
SCREENSHOT_ON_FAILURE = True
SCREENSHOT_ON_SUCCESS = False  # Only on specific steps
SCREENSHOT_DIR_PATTERN = "tests/screenshots/{run_id}"
```

---

## 3. Public Methods

### 1. connect_to_cloud_pc()

**Purpose**: Establish RDP connection to Cloud PC.

**Signature**:
```python
async def connect_to_cloud_pc(self) -> bool:
    """Establish RDP connection to Cloud PC.

    Uses RDP protocol to establish remote session.
    Configures screen resolution and clipboard sharing.

    Returns:
        bool: True if connection successful

    Raises:
        ConnectionError: On connection failures

    Flow:
        1. Validate RDP endpoint (IP address)
        2. Create RDP connection with credentials:
           - hostname: cloud_pc_info.rdp_endpoint
           - username: cloud_pc_info.username
           - password: cloud_pc_info.password
           - screen_size: 1920x1080 (standard)
        3. Wait for session ready (max 60 seconds)
        4. Verify connection by taking screenshot
        5. Return True on success

    Error Handling:
        - Connection refused → Retry with backoff
        - Authentication failed → Fail immediately
        - Timeout → Retry up to 3 times
        - Network unreachable → Retry with exponential backoff

    Side Effects:
        - Establishes network connection to Cloud PC
        - May require Cloud PC to have RDP enabled

    Example:
        >>> connected = await tester.connect_to_cloud_pc()
        >>> if connected:
        ...     print("RDP session established")
    """
```

**Implementation Notes**:

- **RDP Library**: Use `pyrdp` or similar library
- **Session Management**: Keep session alive throughout tests
- **Clipboard**: Enable clipboard sharing for paste operations
- **Resolution**: Use 1920x1080 for consistency
- **Retry**: Implement exponential backoff for connection failures

---

### 2. launch_browser()

**Purpose**: Launch browser (Chrome/Edge) on Cloud PC.

**Signature**:
```python
async def launch_browser(self) -> bool:
    """Launch browser on Cloud PC via RDP session.

    Creates Selenium WebDriver connected to Cloud PC.

    Returns:
        bool: True if browser launched

    Raises:
        BrowserError: On launch failures

    Flow:
        1. Verify Chrome/Edge installed on Cloud PC
        2. Configure WebDriver options:
           - Headless: False (need to see UI for debugging)
           - Disable GPU
           - No sandbox
           - Disable notifications
        3. Create Chrome/Edge WebDriver:
           - Connect to remote display (via RDP)
           - Initialize WebDriver
           - Set timeouts (page load, element find)
        4. Verify browser responsive (navigate to about:blank)
        5. Return True on success

    Error Handling:
        - Chrome not installed → Install Chrome
        - WebDriver port conflict → Try next port
        - Display not available → Error
        - Timeout → Retry

    Example:
        >>> launched = await tester.launch_browser()
        >>> if launched:
        ...     print("Browser ready for testing")
    """
```

**Implementation Notes**:

- **WebDriver**: Use ChromeDriver or EdgeDriver
- **Display**: Run against remote display via RDP
- **Timeouts**: Set implicit wait to ELEMENT_WAIT_TIMEOUT
- **Headless**: Set to False for debugging (need visual feedback)

---

### 3. navigate_to_url()

**Purpose**: Navigate to URL and wait for page load.

**Signature**:
```python
async def navigate_to_url(
    self,
    url: str,
    wait_element: str | None = None,
) -> NavigationResult:
    """Navigate to URL and wait for page load.

    Args:
        url: URL to navigate to
        wait_element: Optional CSS selector to wait for (indicates page loaded)

    Returns:
        NavigationResult:
            - success: bool
            - url_loaded: str (actual URL after navigation)
            - page_title: str
            - load_time_ms: float
            - screenshot: bytes | None

    Raises:
        NavigationError: On navigation failures

    Flow:
        1. Start timer
        2. Call driver.get(url)
        3. If wait_element provided:
           - Wait for element to appear (explicit wait)
           - Max wait: PAGE_LOAD_TIMEOUT
        4. Else:
           - Wait for document.readyState == "complete"
        5. Stop timer, calculate load_time
        6. Extract page title
        7. Capture screenshot if needed
        8. Return NavigationResult

    Error Handling:
        - Timeout → NavigationError
        - Navigation to blank page → Check current URL
        - SSL error → Log warning, continue
        - Redirect loop → Fail with error

    Example:
        >>> result = await tester.navigate_to_url(
        ...     url="https://office.com",
        ...     wait_element="button[data-automation-id='Start']"
        ... )
        >>> if result.success:
        ...     print(f"Page loaded in {result.load_time_ms}ms")
    """
```

**Implementation Notes**:

- **Wait Strategy**: Use explicit waits (WebDriverWait)
- **Page Load**: Monitor document.readyState or specific elements
- **Performance**: Log load times for reporting
- **Screenshot**: Capture after page fully loaded

---

### 4. click_element()

**Purpose**: Click element by selector.

**Signature**:
```python
async def click_element(
    self,
    selector: str,
    selector_type: str = "css",  # "css", "xpath", "id"
) -> ActionResult:
    """Click element by selector.

    Args:
        selector: CSS selector, XPath, or element ID
        selector_type: Type of selector ("css", "xpath", "id")

    Returns:
        ActionResult:
            - success: bool
            - action_latency_ms: float
            - element_found: bool
            - screenshot: bytes | None

    Raises:
        ElementNotFoundError: If element not found after timeout

    Flow:
        1. Start timer
        2. Find element using WebDriverWait:
           - Use EC.presence_of_element_located
           - Max wait: ELEMENT_WAIT_TIMEOUT
        3. Scroll element into view (if needed)
        4. Click element
        5. Stop timer
        6. Capture screenshot if on failure
        7. Return ActionResult

    Error Handling:
        - Element not found → Retry with backoff
        - Element not clickable → Scroll into view, retry
        - Stale element → Retry
        - Timeout → Fail with ElementNotFoundError

    Example:
        >>> result = await tester.click_element(
        ...     selector="button.sign-in",
        ...     selector_type="css"
        ... )
    """
```

**Implementation Notes**:

- **Waits**: Use explicit waits for reliability
- **Scrolling**: Auto-scroll element into view
- **Retry**: Retry on transient failures
- **Timing**: Measure action latency for performance tracking

---

### 5. type_text()

**Purpose**: Type text into element.

**Signature**:
```python
async def type_text(
    self,
    selector: str,
    text: str,
    selector_type: str = "css",
    clear_first: bool = True,
) -> ActionResult:
    """Type text into input element.

    Args:
        selector: Element selector
        text: Text to type
        selector_type: Type of selector
        clear_first: If True, clear field before typing

    Returns:
        ActionResult with action latency

    Flow:
        1. Find and focus element
        2. If clear_first: element.clear()
        3. Type text using send_keys()
        4. Verify text entered
        5. Return ActionResult
    """
```

**Implementation Notes**:

- **Clear**: Use clear() before typing unless clear_first=False
- **Send Keys**: Use Selenium's send_keys() for reliable typing
- **Verification**: Verify text actually entered

---

### 6. verify_element_exists()

**Purpose**: Assert element exists on page.

**Signature**:
```python
async def verify_element_exists(
    self,
    selector: str,
    selector_type: str = "css",
    timeout_seconds: int | None = None,
) -> bool:
    """Verify element exists on page.

    Args:
        selector: Element selector
        selector_type: Type of selector
        timeout_seconds: Wait timeout (default: ELEMENT_WAIT_TIMEOUT)

    Returns:
        bool: True if element found within timeout

    Raises:
        TimeoutException: If not found (caught and returns False)
    """
```

**Implementation Notes**:

- **Non-Fatal**: Returns False on not found (doesn't raise)
- **Wait**: Applies explicit wait with timeout
- **Use**: Perfect for assertions in tests

---

### 7. get_element_text()

**Purpose**: Get text content from element.

**Signature**:
```python
async def get_element_text(
    self,
    selector: str,
    selector_type: str = "css",
) -> str | None:
    """Get text content from element.

    Returns:
        Text content or None if not found
    """
```

---

### 8. run_test_scenario()

**Purpose**: Execute a single test scenario.

**Signature**:
```python
async def run_test_scenario(
    self,
    scenario: BrowserTestScenario,
) -> TestResult:
    """Execute a single test scenario.

    Args:
        scenario: BrowserTestScenario with steps to execute

    Returns:
        TestResult:
            - scenario_name: str
            - status: str ("PASS", "FAIL", "ERROR")
            - start_time: datetime
            - end_time: datetime
            - duration_seconds: float
            - steps: list[StepResult]
            - screenshots: list[ScreenshotRecord]
            - error_message: str | None

    Flow:
        1. Log scenario start
        2. Capture initial screenshot
        3. For each step in scenario.steps:
           - Execute step action
           - Record result
           - Verify expected condition
           - Capture screenshot on failure
           - If any step fails:
             - Mark scenario as FAIL
             - Continue remaining steps
        4. Compare final state to expected state
        5. Return TestResult

    Error Handling:
        - Step fails → Mark as FAIL, continue
        - Exception during step → Mark as ERROR, continue
        - Timeout → Mark as FAIL
        - Network error → Retry step

    Example:
        >>> scenario = BrowserTestScenario(
        ...     name="M365 Portal Access",
        ...     steps=[
        ...         BrowserTestStep(action="navigate", url="https://office.com"),
        ...         BrowserTestStep(action="wait_element", selector="button.sign-in"),
        ...     ]
        ... )
        >>> result = await tester.run_test_scenario(scenario)
        >>> print(f"Result: {result.status}")
    """
```

**Implementation Notes**:

- **Error Isolation**: One step failure doesn't stop test
- **Screenshots**: Capture on failure and after key steps
- **Timing**: Track duration per step and overall
- **Logging**: Detailed logging of each step

---

### 9. Test Scenario Methods

#### verify_m365_access()

```python
async def verify_m365_access(self) -> TestResult:
    """Test: Access M365 portal and authenticate.

    Flow:
        1. Navigate to https://office.com
        2. Wait for M365 home page load
        3. Verify user is authenticated
        4. Verify M365 apps visible (Teams, Outlook, etc.)
        5. Return TestResult

    Success Criteria:
        - Page loads successfully
        - User info visible (no sign-in button)
        - At least 5 M365 apps visible
    """
```

#### verify_teams_chat()

```python
async def verify_teams_chat(self) -> TestResult:
    """Test: Launch Teams and send message.

    Flow:
        1. Navigate to Teams web app (teams.microsoft.com)
        2. Wait for Teams interface
        3. Select deployment status channel
        4. Click message input
        5. Type test message
        6. Send message
        7. Wait for message to appear
        8. Return TestResult

    Success Criteria:
        - Teams loads
        - Channel selected
        - Message appears in chat history
        - Timestamp shows recent
    """
```

#### verify_email_access()

```python
async def verify_email_access(self) -> TestResult:
    """Test: Access Outlook and retrieve emails.

    Flow:
        1. Open Outlook (outlook.office.com)
        2. Wait for mailbox to load
        3. Check inbox count
        4. Verify recent emails displayed
        5. Open a recent email
        6. Verify email content readable
        7. Return TestResult

    Success Criteria:
        - Outlook loads
        - Inbox items visible
        - Email content readable
        - Timestamps correct
    """
```

#### verify_sharepoint_sync()

```python
async def verify_sharepoint_sync(self) -> TestResult:
    """Test: Verify OneDrive and SharePoint access.

    Flow:
        1. Open OneDrive (onedrive.live.com)
        2. Wait for files to load
        3. Verify file sync status
        4. Navigate to team SharePoint
        5. Verify shared documents accessible
        6. Return TestResult

    Success Criteria:
        - OneDrive loads
        - Files visible
        - No sync errors
        - SharePoint accessible
    """
```

#### verify_agent_ui()

```python
async def verify_agent_ui(self) -> TestResult:
    """Test: Launch Magentic-UI agent UI and verify controls.

    Flow:
        1. Locate Magentic-UI app on desktop
        2. Launch application
        3. Wait for UI to appear
        4. Verify all controls visible
        5. Execute sample task
        6. Verify task execution
        7. Check agent logs
        8. Return TestResult

    Success Criteria:
        - Agent UI launches
        - All controls responsive
        - Sample task executes
        - Logs show activity
    """
```

---

### 10. run_all_scenarios()

**Purpose**: Execute all test scenarios and collect results.

**Signature**:
```python
async def run_all_scenarios(
    self,
    scenarios: list[BrowserTestScenario] | None = None,
) -> TestSuiteResult:
    """Execute all test scenarios.

    Args:
        scenarios: List of scenarios to run (default: built-in scenarios)

    Returns:
        TestSuiteResult:
            - total_scenarios: int
            - passed: int
            - failed: int
            - errored: int
            - duration_seconds: float
            - results: list[TestResult]
            - overall_status: str ("PASS", "PARTIAL", "FAIL")

    Flow:
        1. Start timer
        2. For each scenario:
           - Run test scenario
           - Collect result
           - Continue even if scenario fails
        3. Calculate summary stats
        4. Determine overall status
        5. Return TestSuiteResult

    Error Handling:
        - One scenario failure → Continue with others
        - Critical error → May abort remaining scenarios
        - Browser crash → Restart and continue

    Example:
        >>> result = await tester.run_all_scenarios()
        >>> print(f"Passed: {result.passed}, Failed: {result.failed}")
    """
```

**Implementation Notes**:

- **Isolation**: Each scenario runs independently
- **Cleanup**: Close and reopen browser between scenarios
- **Summary**: Aggregate results across all scenarios

---

### 11. generate_test_report()

**Purpose**: Generate JSON and HTML test reports.

**Signature**:
```python
async def generate_test_report(
    self,
    results: TestSuiteResult,
    output_dir: Path,
) -> dict[str, Path]:
    """Generate test reports in multiple formats.

    Args:
        results: TestSuiteResult from test run
        output_dir: Directory to write reports

    Returns:
        dict[str, Path]:
            - "json_report": Path to JSON file
            - "html_report": Path to HTML file
            - "artifacts_dir": Path to screenshots directory

    Flow:
        1. Create output directory if needed
        2. Generate JSON report:
           - Full test results
           - Metrics and timing
           - Error details
           - Metadata
        3. Generate HTML report:
           - Formatted test summary
           - Scenario breakdowns
           - Screenshots embedded
           - Performance charts
        4. Copy screenshots to artifacts dir
        5. Return paths to reports

    Report Contents:
        JSON:
        {
          "run_id": "haymaker-001",
          "timestamp": "2025-01-15T14:30:00Z",
          "duration_seconds": 1234.5,
          "summary": {
            "total": 5,
            "passed": 4,
            "failed": 1
          },
          "scenarios": [...]
        }

        HTML: Formatted report with tables, charts, embedded screenshots

    Example:
        >>> paths = await tester.generate_test_report(
        ...     results=test_results,
        ...     output_dir=Path("reports")
        ... )
        >>> print(f"Reports: {paths}")
    """
```

**Implementation Notes**:

- **JSON**: Machine-readable format for parsing and integration
- **HTML**: Human-readable format for manual review
- **Screenshots**: Embed directly in HTML or link from directory
- **Charts**: Use charting library (Chart.js) for performance graphs

---

### 12. disconnect_from_cloud_pc()

**Purpose**: Close connections and cleanup.

**Signature**:
```python
async def disconnect_from_cloud_pc(self) -> bool:
    """Close RDP connection and cleanup.

    Returns:
        bool: True on successful cleanup

    Flow:
        1. Close Selenium WebDriver
        2. Close RDP session
        3. Clean up temp files
        4. Release resources
        5. Return True
    """
```

**Implementation Notes**:

- **Cleanup**: Always called, even on errors
- **Graceful**: Close connections properly
- **Resources**: Free memory and network resources

---

## 4. Data Models

```python
@dataclass
class BrowserTestStep:
    """Single test step."""
    action: str  # "navigate", "click", "type", "verify_element", etc.
    selector: str | None = None
    selector_type: str = "css"
    value: str | None = None  # For type action
    expected_value: str | None = None
    timeout_seconds: int | None = None
    screenshot: bool = False

@dataclass
class BrowserTestScenario:
    """Test scenario (collection of steps)."""
    name: str
    description: str
    steps: list[BrowserTestStep]
    expected_duration_seconds: int | None = None
    retry_on_failure: bool = False

@dataclass
class StepResult:
    """Result of single step."""
    step: BrowserTestStep
    status: str  # "PASS", "FAIL", "ERROR"
    duration_seconds: float
    error_message: str | None = None
    screenshot: bytes | None = None

@dataclass
class TestResult:
    """Result of one test scenario."""
    scenario_name: str
    status: str  # "PASS", "FAIL", "ERROR"
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    steps: list[StepResult] = field(default_factory=list)
    screenshots: list[ScreenshotRecord] = field(default_factory=list)
    error_message: str | None = None

@dataclass
class TestSuiteResult:
    """Result of all test scenarios."""
    total_scenarios: int
    passed: int
    failed: int
    errored: int
    duration_seconds: float
    results: list[TestResult] = field(default_factory=list)
    overall_status: str = "FAIL"
    performance_metrics: dict[str, float] = field(default_factory=dict)

@dataclass
class ScreenshotRecord:
    """Screenshot record."""
    timestamp: datetime
    scenario: str
    step: int
    reason: str  # "on_failure", "on_success", "checkpoint"
    filename: str
    size_bytes: int

@dataclass
class NavigationResult:
    """Navigation result."""
    success: bool
    url_loaded: str
    page_title: str
    load_time_ms: float
    screenshot: bytes | None = None

@dataclass
class ActionResult:
    """Result of element action."""
    success: bool
    action_latency_ms: float
    element_found: bool
    screenshot: bytes | None = None

@dataclass
class CloudPCInfo:
    """Cloud PC connection details."""
    id: str
    display_name: str
    rdp_endpoint: str  # IP address or hostname
    username: str  # RDP username
    password: str  # RDP password
    status: str  # "provisioned", etc.
```

---

## 5. Built-in Test Scenarios

```python
DEFAULT_SCENARIOS = [
    BrowserTestScenario(
        name="M365 Portal Access",
        description="Verify access to M365 home portal",
        steps=[
            BrowserTestStep(action="navigate", value="https://office.com", screenshot=True),
            BrowserTestStep(action="wait_element", selector="[data-automation-id='Start']"),
            BrowserTestStep(action="verify_element", selector="div[class*='app-item']"),
        ]
    ),
    BrowserTestScenario(
        name="Teams Messaging",
        description="Send message in Teams",
        steps=[
            BrowserTestStep(action="navigate", value="https://teams.microsoft.com"),
            BrowserTestStep(action="wait_element", selector="button[aria-label='Search']"),
            BrowserTestStep(action="verify_element", selector="div[class*='conversation']"),
        ]
    ),
    # ... more scenarios
]
```

---

## 6. Error Handling

### Custom Exceptions

```python
class BrowserAutomationError(Exception):
    """Base browser automation error."""
    pass

class ConnectionError(BrowserAutomationError):
    """RDP connection error."""
    pass

class BrowserError(BrowserAutomationError):
    """Browser launch/control error."""
    pass

class NavigationError(BrowserAutomationError):
    """Page navigation error."""
    pass

class ElementNotFoundError(BrowserAutomationError):
    """Element not found on page."""
    pass

class ActionError(BrowserAutomationError):
    """Element action failed."""
    pass

class TestTimeoutError(BrowserAutomationError):
    """Test scenario timeout."""
    pass
```

---

## 7. Testing Strategy

```python
# Unit tests (with mocked Selenium/RDP)
test_click_element_success()
test_click_element_not_found()
test_type_text_clears_field()
test_navigate_waits_for_element()
test_verify_element_exists()
test_get_element_text()

# Integration tests (against test Cloud PC)
test_end_to_end_m365_access()
test_end_to_end_teams_message()
test_end_to_end_email_access()
test_multiple_scenarios_run()
test_report_generation()
test_screenshot_capture()
```

---

## 8. Success Criteria

- [ ] RDP connection with retry logic
- [ ] Selenium WebDriver control via RDP
- [ ] All test scenarios implemented and working
- [ ] Screenshot capture on key events
- [ ] Performance metrics collection
- [ ] JSON and HTML report generation
- [ ] Error handling and retry logic
- [ ] Unit tests with 85%+ coverage
- [ ] Integration tests passing
- [ ] Complete logging

---

## 9. Dependencies

### Internal
- Data models for test scenarios and results

### External
- `selenium` - WebDriver for browser automation
- `pyrdp` or similar - RDP client
- `Pillow` - Screenshot capture
- `jinja2` - HTML report templating
- `aiohttp` - HTTP requests
- Standard library: `asyncio`, `logging`, `json`, `datetime`

---

## 10. Performance Considerations

- Use headless mode where visual feedback not needed
- Implement connection pooling for Cloud PC
- Cache selectors and elements
- Batch screenshot operations
- Compress screenshots before reporting
- Use parallel scenario execution where possible

---

## 11. Future Enhancements

- [ ] Multi-scenario parallel execution
- [ ] Video recording of test runs
- [ ] Advanced performance profiling
- [ ] Machine learning for flaky test detection
- [ ] Integration with CI/CD pipelines
- [ ] Real-time test status dashboard
- [ ] Automatic screenshot comparison (visual regression)
- [ ] Test coverage metrics
