# Engineering Simulation Tests

Comprehensive test suite for the Software Engineering Team Simulation framework (Part 3).

## Test Organization

```
tests/
├── unit/                          # Unit tests (fast, isolated)
│   └── engineering/
│       ├── bricks/               # Brick tests
│       │   ├── test_base.py     # Base framework tests
│       │   ├── test_commit.py   # CommitBrick tests
│       │   ├── test_pull_request.py
│       │   ├── test_review.py
│       │   ├── test_ci_pipeline.py
│       │   └── test_merge.py
│       ├── workflows/            # Workflow tests
│       │   └── test_composition.py
│       ├── clients/              # Client tests
│       │   └── test_github_client.py
│       └── conftest.py          # Engineering-specific fixtures
├── integration/                   # Integration tests
│   └── engineering/
│       └── test_feature_workflow.py
├── e2e/                          # End-to-end tests
│   └── engineering/
│       └── test_three_team_sprint.py
└── conftest.py                   # Global fixtures

## Running Tests

### Run all tests
```bash
pytest

### Run unit tests only
```bash
pytest tests/unit/

### Run engineering simulation tests
```bash
pytest tests/unit/engineering/

### Run specific test file
```bash
pytest tests/unit/engineering/bricks/test_commit.py

### Run tests by marker
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# E2E tests (slow)
pytest -m e2e

# Skip slow tests
pytest -m "not slow"

### Run with coverage
```bash
pytest --cov=azure_haymaker.engineering_sim --cov-report=html

### Run tests in parallel (requires pytest-xdist)
```bash
pytest -n auto

## Test Categories

### Unit Tests (`tests/unit/`)
- **Fast**: <100ms per test
- **Isolated**: No external dependencies
- **Mocked**: GitHub API mocked
- **Coverage**: 90%+ target

### Integration Tests (`tests/integration/`)
- **Medium speed**: <5s per test
- **Multi-component**: Tests workflows end-to-end
- **Mocked external APIs**: GitHub still mocked
- **Coverage**: Key workflows validated

### E2E Tests (`tests/e2e/`)
- **Slow**: 10s+ per test
- **Complete scenarios**: Full sprint simulations
- **Optional real API**: Can use real GitHub (gated)
- **Coverage**: User scenarios work correctly

## Test Markers

Tests are marked for easy filtering:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_github_api` - Requires real GitHub API
- `@pytest.mark.asyncio` - Async tests

## Fixtures

### Global Fixtures (`tests/conftest.py`)
- Azure SDK mocks
- Common test utilities

### Engineering Fixtures (`tests/unit/engineering/conftest.py`)
- `mock_github_client` - Mocked GitHubClient
- `sample_brick_context` - Pre-configured BrickContext
- `sample_team_config` - Team configuration dict
- `mock_workflow` - Mocked Workflow
- `mock_brick` - Mocked WorkflowBrick

## TDD Approach

These tests were written **BEFORE** implementation (Test-Driven Development):

1. **Red**: Tests fail (no implementation)
2. **Green**: Implement to make tests pass
3. **Refactor**: Improve code while keeping tests green

### Current State: RED
All tests will FAIL until implementation is complete. This is intentional and expected.

## Running Tests Against Real GitHub API

Some integration tests support real GitHub API (gated behind environment variables):

```bash
# Set required environment variables
export GITHUB_TOKEN="your_github_token"
export GITHUB_TEST_ORG="your_test_org"
export GITHUB_TEST_REPO="your_test_repo"

# Run tests marked with requires_github_api
pytest -m requires_github_api

## Coverage Goals

- **Unit tests**: 90%+ coverage of brick logic
- **Integration tests**: Key workflows validated end-to-end
- **E2E tests**: User scenarios work correctly

### Current Coverage Target
```
Module                                Coverage
=====================================  ========
engineering_sim/bricks/base.py        95%
engineering_sim/bricks/commit.py      90%
engineering_sim/bricks/pull_request.py 90%
engineering_sim/bricks/review.py      90%
engineering_sim/bricks/ci_pipeline.py 90%
engineering_sim/bricks/merge.py       90%
engineering_sim/workflow.py           92%
engineering_sim/github_client.py      88%
engineering_sim/sprint.py             85%
-------------------------------------
TOTAL                                 90%+
```

## CI/CD Integration

Tests run automatically in CI:

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pytest tests/unit/ -m "not slow"
          pytest tests/integration/ -m "not requires_github_api"

  test-slow:
    runs-on: ubuntu-latest
    steps:
      - name: Run slow tests
        run: pytest -m slow

  test-e2e:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - name: Run E2E tests
        run: pytest tests/e2e/
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Debugging Tests

### Run specific test with verbose output
```bash
pytest tests/unit/engineering/bricks/test_commit.py::TestCommitBrickExecution::test_execute_creates_commit -vv

### Run with debugger on failure
```bash
pytest --pdb

### Run with print statements visible
```bash
pytest -s

### Run with detailed traceback
```bash
pytest --tb=long

## Writing New Tests

When adding new bricks or features:

1. **Write tests first** (TDD)
2. **Follow naming conventions**: `test_<feature>_<scenario>`
3. **Use appropriate markers**: `@pytest.mark.unit`, etc.
4. **Mock external dependencies**: Use fixtures
5. **Test edge cases**: Empty inputs, errors, boundaries
6. **Document expected behavior**: Clear docstrings

### Example Test Template

```python
"""Unit tests for NewBrick.

Tests cover:
- Initialization
- Validation
- Execution
- Error handling
- Edge cases
"""

import pytest
from azure_haymaker.engineering_sim.bricks.new_brick import NewBrick

class TestNewBrickValidation:
    """Test NewBrick validation logic."""

    def test_validate_requires_something(self, mock_github_client):
        \"\"\"Test validate() requires specific context.\"\"\"
        brick = NewBrick(github_client=mock_github_client)
        context = BrickContext(...)

        assert brick.validate(context) is True

class TestNewBrickExecution:
    \"\"\"Test NewBrick execute() method.\"\"\"

    @pytest.mark.asyncio
    async def test_execute_does_something(self, mock_github_client):
        \"\"\"Test execute() performs expected action.\"\"\"
        brick = NewBrick(github_client=mock_github_client)
        context = BrickContext(...)

        result = await brick.execute(context)

        assert result.success is True
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Pytest-cov](https://pytest-cov.readthedocs.io/)
- [TDD Guide](https://testdriven.io/test-driven-development/)
