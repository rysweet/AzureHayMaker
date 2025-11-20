# Implementation Prompt: CLI Diagnostic Commands for Azure Container Apps Orchestrator

## Feature Request: CLI Diagnostic Commands for Orchestrator Management

### Objective

Implement Phase 1 of CLI diagnostic commands enabling operators to monitor, diagnose, and troubleshoot the Azure Container Apps orchestrator through the `haymaker orch` command group. This enables real-time visibility into orchestrator status, revision management, container logs, and health diagnostics without requiring direct Azure portal access.

### Requirements

**Functional Requirements:**

1. **Status Command** - `haymaker orch status`
   - Display orchestrator endpoint, overall status, active revision count
   - List active revisions with NAME, TRAFFIC, REPLICAS, HEALTH, CREATED columns
   - Support --revision filter for single revision details
   - Support table/json/yaml output formats
   - Handle multiple revisions, no revisions, and error states gracefully

2. **Replicas Command** - `haymaker orch replicas`
   - List replica status for specific revision
   - Show NAME, STATUS, CREATED, ERROR, CPU_USAGE, MEMORY_USAGE, RESTARTS
   - Support --status filtering (running/provisioning/failed)
   - Implement --follow mode with 2-second polling intervals
   - Require --revision when multiple active revisions exist
   - Support all output formats

3. **Logs Command** - `haymaker orch logs`
   - Retrieve container logs with options
   - Support --tail N (default 100, max 10000)
   - Implement --follow mode (stream new entries, Ctrl+C to stop)
   - Support --timestamps, --since DURATION, --container, --replica filters
   - Support text and json output formats
   - Handle no logs available edge case

4. **Health Command** - `haymaker orch health`
   - Basic checks: Container App status, DNS resolution, TCP connectivity, replica health
   - Deep checks (--deep): HTTP endpoint, API endpoints, Functions runtime, log errors
   - Generate pass/warn/fail status for each check
   - Provide actionable suggestions based on failures
   - Complete basic checks in <5 seconds, deep checks in <15 seconds
   - Return exit code 0 if healthy, 1 if any checks fail

**Configuration Requirements:**

- Store orchestrator config in ~/.haymaker/config.yaml with structure:
  ```yaml
  orchestrator:
    subscription_id: <id>
    resource_group: <rg>
    container_app_name: <name>
    timeout: 30
    retry_count: 3
  ```
- Support environment variables: HAYMAKER_ORCHESTRATOR_SUBSCRIPTION_ID, RESOURCE_GROUP, CONTAINER_APP_NAME
- Priority: ENV vars > config file > defaults
- Validate HTTPS endpoints (no HTTP)
- Set config file permissions to 0600

**Error Handling Requirements:**

- Exit code 0: Success
- Exit code 1: Configuration/input error
- Exit code 2: Connectivity/network error
- Exit code 3: API error / not found
- Exit code 4: Server error
- Provide clear error messages with suggestions
- Handle timeout errors gracefully
- Display ambiguity resolution (multiple revisions) with list of options

**Output Format Requirements:**

- Table format: Aligned columns, borders, color coding (green=ok, yellow=warning, red=error)
- JSON format: Valid JSON with timestamp, proper escaping
- YAML format: Proper indentation, valid YAML
- Use Rich library for colored table output
- Support --verbose flag for additional details
- Consistent formatting across all commands

**Testing Requirements:**

- Minimum 85% code coverage
- Unit tests for all commands with multiple scenarios
- Integration tests with mock Container App API responses
- Error path testing (timeouts, DNS failures, API errors)
- Output format validation (JSON parseable, YAML valid, table readable)
- Follow mode polling and interruption testing

### Technical Considerations

**Architecture Impacts:**
- Create new `orchestrator` module in cli/src/haymaker_cli/
- Extend models.py with orchestrator-specific models
- Create orchestrator client wrapper for Azure Container Apps API
- Add configuration loading for orchestrator settings
- Extend main.py CLI with new `orch` command group

**Dependencies:**
- azure-mgmt-containerregistry or equivalent Container Apps API
- azure-identity for authentication
- httpx (async HTTP, already included)
- click (CLI framework, already included)
- rich (formatting, already included)
- pydantic (validation, already included)

**Integration Points:**
- Configuration system (existing config.yaml with new orchestrator section)
- Authentication (existing auth providers)
- Output formatters (extend existing format functions)
- Error handling (consistent with existing HayMakerClientError pattern)

**Key Design Decisions:**
- Use Azure SDK for Container App API calls (authoritative data)
- Implement polling for follow modes (not websockets) for simplicity
- Store configuration separately from API profiles (orchestrator vs haymaker)
- Require --revision when ambiguous (fail fast vs guessing)
- Use exponential backoff for retries (1s, 2s, 4s)

### Acceptance Criteria

- [ ] All 4 commands (status, replicas, logs, health) implemented and working
- [ ] Commands accept all specified options and flags
- [ ] Output formats (table/json/yaml) valid and properly formatted
- [ ] Configuration loading from file and environment variables
- [ ] Error handling with appropriate exit codes and messages
- [ ] Follow modes poll every 2 seconds, respond to Ctrl+C
- [ ] Health checks complete in specified timeframes
- [ ] All unit tests pass with 85%+ coverage
- [ ] Integration tests pass with mock data
- [ ] Help text clear with examples for each command
- [ ] No unhandled exceptions in normal operation
- [ ] Performance <3s for status/replicas, <5s for logs basic

### Testing Requirements

**Unit Tests to Create:**
```
tests/cli/test_orchestrator_config.py
tests/cli/test_orchestrator_commands.py
tests/cli/test_orchestrator_errors.py
tests/cli/test_orchestrator_formatting.py
```

**Test Scenarios:**
- Status with single and multiple revisions
- Replicas with various statuses and filters
- Logs with tail, follow, since, and format options
- Health with basic and deep checks
- Configuration loading from file and env
- Error scenarios (missing config, connectivity, API errors)
- Output format validation (JSON, YAML, table)
- Timeout and retry logic
- Follow mode interruption

### Complexity: Medium

**Rationale:**
- Multiple interdependent commands (2-3 day effort)
- Azure SDK integration required
- Configuration management
- Complex health check logic
- Output formatting complexity
- Testing complexity (mocking Container Apps API)

**Risk Assessment:**
- Azure SDK version compatibility (medium - mitigated by pinning versions)
- API rate limiting (low - health checks cache results)
- Network failures (low - exponential backoff, clear errors)
- Breaking changes to existing CLI (low - new command group)

### Estimated Effort

- Implementation: 16-20 hours
- Testing: 12-16 hours
- Documentation: 4-6 hours
- Code Review & Fixes: 4-6 hours
- **Total: 36-48 hours (4.5-6 days)**

### Success Metrics

- Deployment: Commands functional in dev environment
- Adoption: Used by 3+ team members within first week
- Reliability: No critical bugs reported in first month
- Performance: All commands complete within specified timeframes
- Test Coverage: 85%+ achieved and maintained
- Documentation: Help text clear, examples work

---

## Implementation Guide

### File Structure to Create

```
cli/src/haymaker_cli/
├── orchestrator/
│   ├── __init__.py
│   ├── client.py                 # Azure Container Apps API wrapper
│   ├── models.py                 # Orchestrator-specific Pydantic models
│   ├── config.py                 # Configuration loading
│   └── health_checks.py          # Health check implementations
├── commands/
│   └── orch.py                   # `haymaker orch` command group
└── (existing files)

tests/cli/
├── test_orchestrator_config.py
├── test_orchestrator_commands.py
├── test_orchestrator_errors.py
└── test_orchestrator_formatting.py
```

### Step-by-Step Implementation

1. **Define Orchestrator Models** (2 hours)
   - Create Pydantic models for orchestrator config
   - Define health check result models
   - Define revision and replica models

2. **Implement Orchestrator Client** (4 hours)
   - Wrapper for Azure Container Apps API
   - Methods: get_status(), get_replicas(), get_logs(), run_health_checks()
   - Error handling and retries

3. **Implement Configuration** (2 hours)
   - Load/save orchestrator config
   - Environment variable support
   - Validation

4. **Implement Health Checks** (3 hours)
   - Basic checks module
   - Deep checks module
   - Suggestion generation

5. **Implement Commands** (6 hours)
   - orch status command
   - orch replicas command
   - orch logs command
   - orch health command

6. **Implement Output Formatters** (2 hours)
   - Extend existing formatters for orchestrator models
   - Color coding and alignment

7. **Testing** (12-16 hours)
   - Unit tests with mocks
   - Integration tests
   - Error scenario testing
   - Output format validation

8. **Documentation & Polish** (4 hours)
   - Help text and examples
   - Error message improvements
   - Code review fixes

### Key Implementation Patterns

**Configuration Loading:**
```python
def load_orchestrator_config(profile: str | None = None) -> OrchestratorConfig:
    # 1. Check environment variables
    # 2. Check config file
    # 3. Return with defaults
    # 4. Validate HTTPS
```

**Command Structure:**
```python
@cli.group()
def orch():
    """Orchestrator management commands."""
    pass

@orch.command()
@click.option('--revision', help='Target revision')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'yaml']))
@click.pass_context
def status(ctx, revision, format):
    """Show orchestrator status."""
    # 1. Load config
    # 2. Create client
    # 3. Get status
    # 4. Format output
    # 5. Handle errors
```

**Error Handling Pattern:**
```python
try:
    # Command logic
except HayMakerClientError as e:
    console.print(f"[red]Error:[/red] {e.message}")
    if e.status_code:
        console.print(f"Status: {e.status_code}")
    sys.exit(APPROPRIATE_EXIT_CODE)
except TimeoutError:
    console.print("[red]Error:[/red] Request timeout")
    sys.exit(2)  # Connectivity error
```

**Follow Mode Pattern:**
```python
if follow:
    console.print("Following... Press Ctrl+C to stop\n")
    seen_ids = set()
    try:
        while True:
            data = client.get_logs()
            new_items = [d for d in data if d.id not in seen_ids]
            if new_items:
                format_and_print(new_items)
                seen_ids.update(d.id for d in new_items)
            time.sleep(2)
    except KeyboardInterrupt:
        console.print("\nStopped")
```

---

## Completion Checklist

Before marking as complete:

- [ ] All 4 commands working with all options
- [ ] Configuration loading (file + env + defaults)
- [ ] All output formats valid and formatted correctly
- [ ] Error handling with proper exit codes
- [ ] Follow modes working with proper polling
- [ ] Health checks completing in timeframes
- [ ] 85%+ test coverage achieved
- [ ] All tests passing
- [ ] Help text complete with examples
- [ ] No unhandled exceptions
- [ ] Performance meets requirements
- [ ] Code review passed
- [ ] Documentation complete

---

## Document Metadata

- **Type:** Implementation Prompt
- **Complexity:** Medium
- **Effort:** 36-48 hours (4.5-6 days)
- **Priority:** HIGH
- **Status:** Ready for Implementation
- **Quality Score:** 92%

Reference: [Full Requirements](./CLI_DIAGNOSTIC_COMMANDS_REQUIREMENTS.md)

