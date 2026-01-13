# SIEM Telemetry Export Pipeline - Test Guide

## Quick Start

```bash
# Run all SIEM tests
pytest tests/unit/test_siem_exporter.py tests/integration/test_siem_integration.py -v

# Run with coverage report
pytest tests/ --cov=src/azure_haymaker/knowledge_worker/telemetry --cov-report=html -v
```

## Test Organization

```
tests/
├── unit/
│   └── test_siem_exporter.py          # 53 unit tests (68%)
├── integration/
│   └── test_siem_integration.py       # 25 integration tests (32%)
├── TEST_SUMMARY.md                     # Detailed test documentation
└── README.md                           # This file
```

## Running Specific Test Suites

### Unit Tests Only
```bash
pytest tests/unit/test_siem_exporter.py -v
```

### Integration Tests Only
```bash
pytest tests/integration/test_siem_integration.py -v
```

### Specific Test Class
```bash
# Run only SentinelConnector tests
pytest tests/unit/test_siem_exporter.py::TestSentinelConnectorSendEvent -v

# Run only DLQ tests
pytest tests/unit/test_siem_exporter.py::TestTelemetryExporterDLQ -v
```

### Specific Test
```bash
pytest tests/unit/test_siem_exporter.py::TestSentinelConnectorSendEvent::test_send_event_with_retry_on_transient_error -v
```

## Test Markers

All tests use `pytest.mark.skipif` to skip when implementation is not available:

```python
pytestmark = pytest.mark.skipif(
    not EXPORTER_AVAILABLE, reason="SIEM exporter module not available"
)
```

Once implementation exists, tests will automatically run.

## Pytest Configuration

Configuration is in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
```

## Test Coverage Goals

- **Unit Tests**: 60% of total (currently 68% - ✓)
- **Integration Tests**: 30% of total (currently 32% - ✓)
- **E2E Tests**: 10% of total (Phase 2)

## Development Workflow

### TDD Red-Green-Refactor

1. **RED**: Tests are written and failing ✓ (current state)
2. **GREEN**: Implement code to make tests pass (next step)
3. **REFACTOR**: Simplify code while keeping tests green

### Watch Mode (Development)
```bash
# Install pytest-watch
pip install pytest-watch

# Auto-run tests on file changes
ptw tests/ src/azure_haymaker/knowledge_worker/telemetry/
```

## Common Test Patterns

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_my_async_function(self):
    result = await my_async_function()
    assert result == expected
```

### Mocking Azure SDK
```python
with patch("module.path.DefaultAzureCredential") as mock_cred:
    mock_cred.return_value = MagicMock()
    # test code
```

### Testing Retry Logic
```python
mock_client.upload.side_effect = [
    Exception("Retry 1"),
    Exception("Retry 2"),
    None,  # Success
]
```

## Debugging Tests

### Verbose Output
```bash
pytest -vv tests/
```

### Show Print Statements
```bash
pytest -s tests/
```

### Stop on First Failure
```bash
pytest -x tests/
```

### Run Last Failed Tests
```bash
pytest --lf tests/
```

### Full Traceback
```bash
pytest --tb=long tests/
```

## Coverage Reports

### Terminal Report
```bash
pytest tests/ --cov=src/azure_haymaker/knowledge_worker/telemetry --cov-report=term-missing
```

### HTML Report
```bash
pytest tests/ --cov=src/azure_haymaker/knowledge_worker/telemetry --cov-report=html
open htmlcov/index.html
```

### Coverage Requirements

Minimum coverage target: 90% for new code

```bash
pytest tests/ --cov=src/azure_haymaker/knowledge_worker/telemetry --cov-fail-under=90
```

## Test Categories

### By Component
- **TelemetryEvent**: 5 tests
- **SentinelConnector Init**: 3 tests
- **SentinelConnector Lifecycle**: 5 tests
- **SentinelConnector Send**: 7 tests
- **SentinelConnector Batch**: 5 tests
- **SentinelConnector Health**: 4 tests
- **TelemetryExporter Init**: 3 tests
- **TelemetryExporter Lifecycle**: 5 tests
- **TelemetryExporter Emit**: 4 tests
- **TelemetryExporter DLQ**: 4 tests
- **Error Handling**: 5 tests
- **End-to-End**: 3 tests

### By Type
- **Unit**: 53 tests (fast, isolated)
- **Integration**: 25 tests (multi-component)

### By Focus
- **Happy Path**: ~30 tests
- **Error Handling**: ~25 tests
- **Edge Cases**: ~23 tests

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run SIEM Tests
  run: |
    pytest tests/unit/test_siem_exporter.py tests/integration/test_siem_integration.py \
      --cov=src/azure_haymaker/knowledge_worker/telemetry \
      --cov-report=xml \
      --cov-fail-under=90 \
      -v
```

## Test Maintenance

### When to Update Tests

1. **Breaking Changes**: API contract changes
2. **New Features**: Add corresponding tests
3. **Bug Fixes**: Add regression tests
4. **Refactoring**: Tests should still pass

### Test Naming Convention

```
test_<component>_<scenario>_<expected_result>

Examples:
- test_send_event_success
- test_send_event_with_retry_on_transient_error
- test_dlq_enforces_max_size
```

## Dependencies

Required packages (in `pyproject.toml`):
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^9.0.0"
pytest-asyncio = "^1.0.0"
pytest-cov = "^7.0.0"
pytest-mock = "^3.15.0"
```

## Troubleshooting

### Tests Not Running

1. Check virtual environment: `which python`
2. Install dependencies: `pip install -e ".[dev]"`
3. Check pytest installation: `pytest --version`

### Import Errors

1. Ensure project root is in PYTHONPATH
2. Check module paths in imports
3. Verify `__init__.py` files exist

### Async Test Failures

1. Ensure `@pytest.mark.asyncio` decorator
2. Check `asyncio_mode = "auto"` in config
3. Use `AsyncMock` for async methods

### Mock Not Working

1. Verify patch path matches import path
2. Use `new_callable=AsyncMock` for async
3. Check patch is active in test scope

## Performance

All tests should complete in < 10 seconds:
- Unit tests: < 5 seconds
- Integration tests: < 5 seconds

If slower, check for:
- Unnecessary sleep() calls
- Missing mocks (real network calls)
- Large data structures

## Further Reading

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [TDD Methodology](https://en.wikipedia.org/wiki/Test-driven_development)

## Contact

For questions about tests:
1. Read TEST_SUMMARY.md for detailed coverage
2. Check test docstrings for specific test purpose
3. Review existing test patterns as examples
