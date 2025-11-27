# HayMaker Telemetry & Reporting Test Suite

This directory contains comprehensive Test-Driven Development (TDD) tests for the HayMaker telemetry and reporting system.

## Quick Stats

- **Test Files**: 15 files
- **Test Methods**: 317 tests
- **Coverage Goal**: >80% for unit tests
- **Test Distribution**: 60% Unit, 30% Integration, 10% E2E

## Directory Structure

```
tests/
├── README.md                        # This file
├── TEST_SUMMARY.md                  # Detailed test documentation
├── fixtures/                        # Test data and utilities
│   ├── __init__.py
│   └── sample_data.py              # Reusable test data generators
├── telemetry/                       # Telemetry module tests (104 tests)
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_collector.py           # TelemetryCollector (30 tests)
│   ├── test_config.py              # TelemetryConfig (19 tests)
│   ├── test_models.py              # Data models (27 tests)
│   └── test_storage.py             # TelemetryStorage (28 tests)
├── reports/                         # Reports module tests (80 tests)
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_data.py                # ReportDataProcessor (28 tests)
│   ├── test_generator.py           # ReportGenerator (30 tests)
│   └── test_models.py              # Report models (22 tests)
├── ui/                              # UI module tests (50 tests)
│   ├── __init__.py
│   ├── test_dashboard.py           # Dashboard (26 tests)
│   └── test_widgets.py             # Widgets (24 tests)
└── integration/                     # Integration tests (83 tests)
    ├── __init__.py
    ├── test_cli_commands.py        # CLI integration (42 tests)
    ├── test_report_generation.py   # Report workflows (21 tests)
    └── test_telemetry_collection.py # Collection workflows (20 tests)
```

## Running Tests

### Prerequisites

Install development dependencies:

```bash
cd /home/azureuser/src/AzureHayMaker/worktrees/feat/issue-116-reporting-telemetry/cli
uv pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/telemetry/ tests/reports/ tests/ui/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific module
pytest tests/telemetry/test_collector.py -v

# Specific test
pytest tests/telemetry/test_collector.py::TestTelemetryCollector::test_collector_collect_once_success -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/ --cov=haymaker_cli --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

### Run Async Tests

Many tests use `pytest-asyncio` for async functionality:

```bash
pytest tests/telemetry/test_collector.py -v --asyncio-mode=auto
```

## Expected Behavior (TDD)

### Before Implementation
All tests should **FAIL** with import errors because the implementation doesn't exist yet. This is correct and expected!

```
ModuleNotFoundError: No module named 'haymaker_cli.telemetry.collector'
```

### During Implementation
Tests should gradually pass as you implement each module:

1. Models pass first (no external dependencies)
2. Config passes next (simple logic)
3. Storage passes (filesystem I/O)
4. Collector passes (API integration)
5. Report processing passes (data analysis)
6. Report generation passes (HTML/CSV/JSON)
7. UI components pass (Textual widgets)
8. CLI commands pass (Click integration)
9. Integration tests pass (everything works together)

### After Implementation
All 317 tests should pass:

```bash
pytest tests/ -v
======================== 317 passed in 10.23s =========================
```

## Test Organization

### Unit Tests (60% - 204 tests)

Unit tests test individual functions and classes in isolation with mocked dependencies.

**Fast**: Each test should run in milliseconds.
**Isolated**: No real API calls, no real filesystem I/O (use tmp_path).
**Focused**: One assertion per test when possible.

Examples:
- `test_execution_record_valid_data` - Tests ExecutionRecord accepts valid input
- `test_storage_save_executions` - Tests TelemetryStorage saves to file
- `test_calculate_kpis_basic` - Tests KPI calculation logic

### Integration Tests (30% - 83 tests)

Integration tests test how components work together.

**Moderate Speed**: Tests may take seconds.
**Real Interactions**: Uses temp directories, may use docker-compose for orchestrator.
**End-to-End Flows**: Tests complete workflows.

Examples:
- `test_full_collection_cycle` - API → Collector → Storage
- `test_full_report_generation_cycle` - Storage → Processor → Generator → HTML
- `test_collect_and_report_pipeline` - Complete telemetry → report workflow

### Fixtures (Shared Test Data)

All fixtures are defined in `conftest.py` files:

**Telemetry Fixtures** (`tests/telemetry/conftest.py`):
- `mock_api_client` - Mock orchestrator API
- `telemetry_storage_dir` - Temporary storage directory
- `sample_telemetry_files` - Pre-populated test files

**Report Fixtures** (`tests/reports/conftest.py`):
- `mock_telemetry_storage` - Mock storage with data
- `report_output_dir` - Temporary output directory
- `mock_jinja2_env` - Mock template environment

**Sample Data** (`tests/fixtures/sample_data.py`):
- `sample_execution_data()` - Generate test executions
- `sample_agent_data()` - Generate test agents
- `sample_kpi_data()` - Generate test KPIs

## Key Test Patterns

### Arrange-Act-Assert (AAA)

```python
def test_storage_save_executions(telemetry_storage_dir):
    """Test TelemetryStorage saves execution records."""
    # Arrange
    storage = TelemetryStorage(telemetry_storage_dir)
    executions = sample_execution_data(count=5)

    # Act
    storage.save_executions(executions)

    # Assert
    executions_file = telemetry_storage_dir / "executions.jsonl"
    assert executions_file.exists()
```

### Parametrized Tests

```python
@pytest.mark.parametrize("status,expected", [
    ("completed", True),
    ("failed", True),
    ("invalid", False),
])
def test_status_validation(status, expected):
    """Test status field validation."""
    # Test implementation
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_collector_collect_once(mock_api_client, tmp_path):
    """Test async collection."""
    collector = TelemetryCollector(mock_api_client, storage)
    result = await collector.collect_once()
    assert result.success is True
```

### Mocking

```python
def test_report_generation(mock_telemetry_storage):
    """Test with mocked storage."""
    generator = ReportGenerator(mock_telemetry_storage, output_dir)
    report = generator.generate_summary_report()

    # Verify mock was called
    mock_telemetry_storage.load_executions.assert_called_once()
```

## Testing Best Practices

### Do's

✅ **Test behavior, not implementation**
```python
# Good: Tests what it does
def test_kpi_calculates_success_rate():
    kpis = calculate_kpis(data)
    assert kpis["success_rate"] == 80.0

# Bad: Tests how it does it
def test_kpi_uses_division():
    assert "/ total" in inspect.getsource(calculate_kpis)
```

✅ **Use descriptive test names**
```python
# Good
def test_collector_handles_api_timeout_gracefully()

# Bad
def test_collector_1()
```

✅ **Test edge cases**
```python
def test_storage_handles_empty_data()
def test_storage_handles_corrupted_json()
def test_storage_handles_permission_error()
```

✅ **One assertion per test (when practical)**
```python
def test_execution_record_has_id():
    record = ExecutionRecord(...)
    assert record.id == "exec-001"

def test_execution_record_has_status():
    record = ExecutionRecord(...)
    assert record.status == "completed"
```

### Don'ts

❌ **Don't test external libraries**
```python
# Bad: Testing Pydantic itself
def test_pydantic_validates_types():
    # Pydantic already has tests
```

❌ **Don't have hidden test dependencies**
```python
# Bad: test_b depends on test_a running first
def test_a():
    global data
    data = load_data()

def test_b():
    assert data is not None  # Fails if test_a doesn't run
```

❌ **Don't use sleep in tests**
```python
# Bad
def test_async_operation():
    start_operation()
    time.sleep(5)  # Slow and flaky
    assert is_complete()

# Good: Use proper async testing
@pytest.mark.asyncio
async def test_async_operation():
    await start_operation()
    assert await is_complete()
```

## Debugging Failed Tests

### Run Single Test
```bash
pytest tests/telemetry/test_collector.py::TestTelemetryCollector::test_collector_collect_once_success -v
```

### Show Print Statements
```bash
pytest tests/ -v -s
```

### Drop into Debugger on Failure
```bash
pytest tests/ --pdb
```

### Show Full Diff
```bash
pytest tests/ -vv
```

### Run Last Failed Tests
```bash
pytest tests/ --lf
```

## Common Issues

### ImportError: No module named 'haymaker_cli.telemetry'

**Expected before implementation!** The tests are designed to fail initially. Start implementing the modules and tests will pass.

### asyncio.run() cannot be called from a running event loop

Use `pytest-asyncio` and mark tests with `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None
```

### Fixture not found

Make sure `conftest.py` is in the correct location:
- `tests/telemetry/conftest.py` for telemetry fixtures
- `tests/reports/conftest.py` for report fixtures

### Tests pass individually but fail together

Check for test interdependence. Each test should be independent:

```python
# Use fixtures or setUp/tearDown
@pytest.fixture
def clean_state():
    # Set up clean state
    yield
    # Clean up after test
```

## Contributing New Tests

When adding new functionality:

1. **Write tests first** (TDD approach)
2. **Add to appropriate test file** (or create new one)
3. **Use existing fixtures** when possible
4. **Follow naming conventions**: `test_<component>_<scenario>_<result>`
5. **Add docstrings** explaining what's being tested
6. **Test happy path AND edge cases**
7. **Update TEST_SUMMARY.md** if adding new test files

## CI/CD Integration

Tests should run in CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    cd cli
    uv pip install -e ".[dev]"
    pytest tests/ --cov=haymaker_cli --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [Pydantic Testing Guide](https://docs.pydantic.dev/latest/usage/validation_errors/)
- [Click Testing](https://click.palletsprojects.com/en/8.1.x/testing/)
- [Textual Testing](https://textual.textualize.io/guide/testing/)

## Questions?

See `TEST_SUMMARY.md` for detailed documentation of each test file and test case.

---

**Remember**: These tests are your specification. They define what the system should do. Let them guide your implementation! 🧪
