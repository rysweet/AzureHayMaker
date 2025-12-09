## Cross-Tenant Orchestration Test Suite

Comprehensive test suite for cross-tenant orchestration following Test Driven Development (TDD) methodology.

### Overview

This test suite implements the **RED-GREEN-REFACTOR** TDD cycle:

1. **RED**: Tests written FIRST (they FAIL initially)
2. **GREEN**: Implement code to make tests PASS
3. **REFACTOR**: Improve code while keeping tests passing

### Test Organization

```
tests/
├── fixtures/
│   ├── tenant_configs.py        # Sample configuration data
│   ├── mock_clients.py          # Mock Azure SDK clients
│   └── test_data.py             # Sample test data
├── unit/
│   ├── orchestrator/
│   │   ├── test_multi_tenant_config.py         # Configuration models (29 tests)
│   │   ├── test_tenant_auth.py                  # Authentication/credentials (17 tests)
│   │   └── services/
│   │       └── test_tenant_storage.py           # Storage partitioning (15 tests)
│   └── cli/
│       └── test_tenant_commands.py              # CLI commands (25 tests)
├── integration/
│   ├── orchestrator/
│   │   ├── test_meta_orchestrator.py            # Meta-orchestration (12 tests)
│   │   └── test_cross_tenant_auth.py            # E2E authentication (8 tests)
│   └── test_multi_tenant_e2e.py                 # Full E2E workflows (10 tests)
├── security/
│   └── test_tenant_isolation.py                 # Security isolation (15 tests)
└── README_CROSS_TENANT_TESTS.md                 # This file
```

### Test Coverage Breakdown

#### Unit Tests (60%)

**Configuration Models** (`test_multi_tenant_config.py`):
- TenantContext validation (7 tests)
- TargetTenantConfig validation (10 tests)
- MetaOrchestratorConfig validation (12 tests)

**Tenant Authentication** (`test_tenant_auth.py`):
- Credential retrieval from Key Vault (3 tests)
- Credential caching (3 tests)
- Credential validation (2 tests)
- Credential storage and rotation (3 tests)
- TenantCredential model (3 tests)

**Storage Partitioning** (`test_tenant_storage.py`):
- TenantAwareBlobClient (5 tests)
- TenantAwareTableClient (3 tests)
- TenantAwareCosmosClient (4 tests)
- Single-tenant mode compatibility (3 tests)

**CLI Commands** (`test_tenant_commands.py`):
- `haymaker orch tenant add` (5 tests)
- `haymaker orch tenant list` (4 tests)
- `haymaker orch tenant status` (4 tests)
- `haymaker orch tenant update` (5 tests)
- `haymaker orch tenant remove` (4 tests)

#### Integration Tests (30%)

**Meta-Orchestrator** (`test_meta_orchestrator.py`):
- Configuration loading (2 tests)
- Credential validation (parallel) (2 tests)
- Tenant filtering (enabled/disabled) (2 tests)
- Child orchestrator spawning (2 tests)
- Concurrency control (2 tests)
- Result aggregation (2 tests)

**Cross-Tenant Authentication** (`test_cross_tenant_auth.py`):
- Infrastructure SP authentication (2 tests)
- Target tenant credential retrieval (2 tests)
- Target tenant SP authentication (2 tests)
- Service principal creation (1 test)
- RBAC permission verification (1 test)

**End-to-End Workflows** (`test_multi_tenant_e2e.py`):
- Complete multi-tenant orchestration (3 tests)
- Resource creation in multiple tenants (2 tests)
- Storage partitioning verification (2 tests)
- Meta-report generation (1 test)
- Migration from single to multi-tenant (2 tests)

#### Security Tests (10%)

**Tenant Isolation** (`test_tenant_isolation.py`):
- Blob Storage isolation (3 tests)
- Table Storage isolation (1 test)
- Cosmos DB isolation (1 test)
- Credential isolation (2 tests)
- SQL/NoSQL injection prevention (4 tests)

### Running Tests

#### Run All Tests

```bash
pytest tests/ -v
```

#### Run by Test Type

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Security tests only
pytest tests/security/ -v -m security
```

#### Run Specific Test Files

```bash
# Configuration tests
pytest tests/unit/orchestrator/test_multi_tenant_config.py -v

# Authentication tests
pytest tests/unit/orchestrator/test_tenant_auth.py -v

# Storage tests
pytest tests/unit/orchestrator/services/test_tenant_storage.py -v

# Isolation tests
pytest tests/security/test_tenant_isolation.py -v
```

#### Run with Coverage

```bash
# All tests with coverage
pytest tests/ --cov=azure_haymaker.orchestrator --cov-report=html

# Unit tests with coverage
pytest tests/unit/ --cov=azure_haymaker.orchestrator --cov-report=term-missing
```

#### Run Specific Test

```bash
pytest tests/unit/orchestrator/test_multi_tenant_config.py::TestTenantContext::test_tenant_context_creation_with_valid_data_succeeds -v
```

### Test Markers

Tests are marked with the following pytest markers:

- `@pytest.mark.asyncio` - Async tests requiring pytest-asyncio
- `@pytest.mark.integration` - Integration tests (slower, may require resources)
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.slow` - Slow-running tests (E2E scenarios)

Filter by marker:

```bash
# Run only async tests
pytest -m asyncio

# Skip integration tests
pytest -m "not integration"

# Run only security tests
pytest -m security
```

### Test Fixtures

#### Configuration Fixtures (`fixtures/tenant_configs.py`)

- `sample_tenant_context()` - Valid TenantContext
- `sample_target_tenant_config()` - Valid TargetTenantConfig
- `sample_meta_orchestrator_config()` - Valid MetaOrchestratorConfig
- `sample_multi_tenant_config()` - Complete multi-tenant config
- `invalid_tenant_context_non_uuid()` - Invalid tenant_id
- `invalid_target_tenant_invalid_cron()` - Invalid cron expression
- `disabled_tenant_config()` - Disabled tenant config

#### Mock Clients (`fixtures/mock_clients.py`)

- `MockKeyVaultClient` - Mock Azure Key Vault
- `MockBlobClient` - Mock Azure Blob Storage
- `MockTableClient` - Mock Azure Table Storage
- `MockCosmosClient` - Mock Azure Cosmos DB
- `MockDurableFunctionsContext` - Mock Durable Functions orchestrator
- `create_mock_credential()` - Mock DefaultAzureCredential
- `create_sample_tenant_credentials()` - Sample tenant credentials

#### Test Data (`fixtures/test_data.py`)

- `sample_execution_run()` - Execution run data
- `sample_resource_event()` - Resource creation event
- `sample_blob_data(tenant_id)` - Tenant-prefixed blob data
- `sample_table_entity(tenant_id, run_id)` - Table entity with partition key
- `sample_cosmos_document(tenant_id)` - Cosmos document with tenant_id
- `sample_orchestration_status()` - Orchestration status
- `sample_meta_report()` - Meta-orchestration report

### TDD Workflow

#### Phase 1: RED (Tests Fail)

All tests are written BEFORE implementation. Tests will fail with `ImportError` or `AttributeError`:

```bash
$ pytest tests/unit/orchestrator/test_multi_tenant_config.py -v

FAILED - ImportError: cannot import name 'TenantContext'
```

This is **EXPECTED** and **CORRECT** for TDD!

#### Phase 2: GREEN (Implement to Pass)

Implement the minimum code required to make tests pass:

1. Create models in `src/azure_haymaker/orchestrator/models.py`
2. Implement `TenantContext`, `TargetTenantConfig`, `MetaOrchestratorConfig`
3. Run tests again:

```bash
$ pytest tests/unit/orchestrator/test_multi_tenant_config.py -v

tests/unit/orchestrator/test_multi_tenant_config.py::TestTenantContext::test_tenant_context_creation_with_valid_data_succeeds PASSED
...
============================= 29 passed in 0.45s =============================
```

#### Phase 3: REFACTOR (Improve Code)

Refactor implementation while keeping tests green:

- Extract common validation logic
- Improve error messages
- Add type hints
- Optimize performance

Run tests after each refactor to ensure nothing breaks.

### Test Quality Standards

All tests follow these quality standards:

1. **Independent**: No shared state between tests
2. **Deterministic**: Same input always produces same output
3. **Fast**: Unit tests < 100ms, integration tests < 1s
4. **Descriptive**: Clear test names explaining what is tested
5. **Assertion Messages**: Clear failure messages
6. **Arrange-Act-Assert**: Standard test structure
7. **Mock External Dependencies**: No real Azure calls in unit tests

### Example Test Pattern

```python
@pytest.mark.asyncio
async def test_tenant_context_creation_with_valid_data_succeeds(self):
    """Test that TenantContext can be created with valid data."""
    # Arrange - Set up test data
    data = sample_tenant_context()

    # Act - Execute the function being tested
    context = TenantContext(**data)

    # Assert - Verify expected outcomes
    assert context.tenant_id is not None
    assert context.tenant_name == "test-tenant"
    assert context.subscription_id is not None
    assert context.region == "eastus"
```

### Coverage Goals

- **Overall Coverage**: ≥ 85%
- **Critical Paths**: 100% (authentication, tenant isolation)
- **Configuration Models**: 100%
- **Storage Services**: ≥ 90%
- **CLI Commands**: ≥ 80%

### Continuous Integration

Tests run automatically on:

- Pull request creation/update
- Merge to main branch
- Release creation

CI pipeline stages:

1. **Lint & Format**: Ruff formatting and linting
2. **Type Check**: Pyright static type checking
3. **Unit Tests**: Fast unit tests (< 2 minutes)
4. **Integration Tests**: Integration tests (< 5 minutes)
5. **Security Tests**: Security-focused tests
6. **Coverage Report**: Generate and publish coverage report

### Known Issues and Limitations

#### Expected Failures (TDD RED Phase)

All tests will initially fail with import errors. This is correct behavior for TDD.

#### Mock Limitations

- Mock clients simulate Azure SDK behavior but don't test actual Azure interactions
- Integration tests should use Azure emulators or test subscriptions
- Security tests verify isolation logic but not Azure-level security

#### Test Data

- All UUIDs and credentials in tests are randomly generated
- Do not use production credentials in tests
- Test data should be sanitized before committing

### Contributing

When adding new tests:

1. **Follow TDD**: Write test first, then implement
2. **Use Fixtures**: Reuse existing fixtures where possible
3. **Add Documentation**: Docstring explaining what is tested
4. **Update README**: Add test to appropriate section
5. **Run Full Suite**: Ensure all tests still pass

### Troubleshooting

#### Tests Won't Run

```bash
# Install test dependencies
uv pip install -e ".[dev]"

# Verify pytest is installed
pytest --version
```

#### Import Errors

```bash
# Ensure PYTHONPATH includes src/
export PYTHONPATH="${PYTHONPATH}:src"

# Or use pytest.ini pythonpath setting
```

#### Async Test Failures

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Verify async mode in pytest.ini
cat pytest.ini | grep asyncio_mode
```

### Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-mock Documentation](https://pytest-mock.readthedocs.io/)
- [TDD Best Practices](https://martinfowler.com/bliki/TestDrivenDevelopment.html)

---

**Last Updated**: 2025-12-09
**Test Suite Version**: 1.0.0
**Total Tests**: 131
**Status**: RED (awaiting implementation)
