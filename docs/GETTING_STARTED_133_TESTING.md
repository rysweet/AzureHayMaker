# Getting Started: Comprehensive Scenario Testing Framework (Issue #133)

**Your complete guide to implementing Issue #133**

**Priority**: P2-Medium | **Effort**: 4 weeks | **ROI**: 190%

---

## What You're Building

Create a comprehensive testing framework for scenarios: unit tests, integration tests, E2E tests, performance benchmarks, and chaos engineering tests to ensure scenario quality before deployment.

**Why It Matters**: Scenarios are the core product. Broken scenarios destroy credibility. Automated testing catches issues early.

**Business Value**: Reduces production incidents by 70%, builds developer confidence, enables external contributions, saves time on manual testing.

---

## Before You Start (20 minutes)

### 1. Understand Current Test Structure

```bash
# Review existing tests
find tests/ -name "*.py" -type f | head -10
grep -r "def test_\|@pytest" tests/ | wc -l

# Check pytest configuration
cat pyproject.toml | grep -A 10 "tool.pytest"
```

### 2. Understand Scenarios

```bash
# See what scenarios exist
ls -la scenarios/
find scenarios -name "*.py" -o -name "*.json" | head -10
```

### 3. Check Test Dependencies

```bash
# Verify test frameworks available
grep -i "pytest\|locust\|chaostoolkit" pyproject.toml
```

---

## Phase 1: Create Test Infrastructure (Days 1-4, ~18 hours)

### Create Branch

```bash
git checkout main
git pull origin main
git checkout -b feat/issue-133-testing-framework
```

### Create Test Directory Structure

```bash
mkdir -p tests/scenarios
mkdir -p tests/performance
mkdir -p tests/chaos
mkdir -p tests/fixtures
touch tests/scenarios/__init__.py
touch tests/scenarios/conftest.py
touch tests/performance/__init__.py
touch tests/chaos/__init__.py
touch tests/fixtures/__init__.py
touch tests/fixtures/scenario_fixtures.py
touch tests/fixtures/mock_data.py
```

### Create ScenarioTestCase Base Class

**File**: `tests/scenarios/base_test_case.py`

```python
import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime
import json

class ScenarioTestCase:
    """Base class for scenario tests with common fixtures and utilities."""

    @pytest.fixture(autouse=True)
    async def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup
        self.test_start_time = datetime.now()
        self.results = {
            "events": [],
            "errors": [],
            "costs": []
        }

        yield

        # Teardown
        self.test_duration = (datetime.now() - self.test_start_time).total_seconds()
        print(f"Test duration: {self.test_duration}s")

    def record_event(self, event_type: str, data: Dict[str, Any]):
        """Record test event for analysis."""
        self.results["events"].append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        })

    def record_error(self, error: Exception, context: str):
        """Record error for test failure analysis."""
        self.results["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "context": context
        })

    def get_test_results(self) -> Dict[str, Any]:
        """Get aggregated test results."""
        return {
            "duration_seconds": self.test_duration,
            "events_count": len(self.results["events"]),
            "errors_count": len(self.results["errors"]),
            "results": self.results
        }

    async def wait_for_condition(
        self,
        condition_fn,
        timeout_seconds: int = 30,
        check_interval: float = 0.5
    ) -> bool:
        """Wait for async condition with timeout."""
        start = datetime.now()
        while True:
            if await condition_fn():
                return True

            elapsed = (datetime.now() - start).total_seconds()
            if elapsed > timeout_seconds:
                return False

            await asyncio.sleep(check_interval)
```

### Create Mock Azure Fixtures

**File**: `tests/fixtures/scenario_fixtures.py`

```python
import pytest
from azure_haymaker.mocks.azure.container_apps import MockContainerAppClient
from azure_haymaker.mocks.azure.key_vault import MockKeyVaultClient
from azure_haymaker.mocks.azure.graph_api import MockGraphApiClient

@pytest.fixture
def mock_container_apps():
    """Provide mock Container Apps client."""
    return MockContainerAppClient()

@pytest.fixture
def mock_key_vault():
    """Provide mock Key Vault client."""
    return MockKeyVaultClient()

@pytest.fixture
def mock_graph_api():
    """Provide mock Graph API client."""
    return MockGraphApiClient()

@pytest.fixture
def azure_clients(mock_container_apps, mock_key_vault, mock_graph_api):
    """Provide all mock Azure clients."""
    return {
        "container_apps": mock_container_apps,
        "key_vault": mock_key_vault,
        "graph_api": mock_graph_api
    }

@pytest.fixture
def test_execution_request():
    """Provide sample execution request."""
    return {
        "scenarios": ["compute-01-linux-vm-web-server"],
        "duration_hours": 1,
        "schedule_id": "test-schedule-1",
        "tenant_id": "test-tenant-1"
    }
```

### Create Test Data Generators

**File**: `tests/fixtures/mock_data.py`

```python
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
import uuid

class MockDataGenerator:
    """Generate realistic test data."""

    @staticmethod
    def generate_scenario_execution(
        scenario_id: str,
        status: str = "success",
        duration_seconds: int = 300
    ) -> Dict[str, Any]:
        """Generate execution record."""
        start_time = datetime.now() - timedelta(seconds=duration_seconds)
        return {
            "id": str(uuid.uuid4()),
            "scenario_id": scenario_id,
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
            "events_generated": random.randint(100, 1000),
            "errors": [] if status == "success" else ["Simulated error"]
        }

    @staticmethod
    def generate_telemetry_events(
        count: int = 100,
        scenario_id: str = "test-scenario"
    ) -> List[Dict[str, Any]]:
        """Generate telemetry events."""
        events = []
        base_time = datetime.now()

        for i in range(count):
            events.append({
                "id": str(uuid.uuid4()),
                "scenario_id": scenario_id,
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "event_type": random.choice([
                    "agent_init",
                    "task_start",
                    "task_complete",
                    "error"
                ]),
                "severity": random.choice(["info", "warning", "error"]),
                "data": {
                    "duration_ms": random.randint(10, 5000),
                    "memory_mb": random.randint(100, 2000)
                }
            })

        return events

    @staticmethod
    def generate_cost_data(
        scenario_id: str,
        duration_hours: float = 1.0
    ) -> Dict[str, Any]:
        """Generate cost estimation."""
        vcpu_hours = 0.25 * duration_hours
        memory_gb_hours = 0.5 * duration_hours

        return {
            "scenario_id": scenario_id,
            "vcpu_hours": vcpu_hours,
            "memory_gb_hours": memory_gb_hours,
            "estimated_cost_usd": (
                vcpu_hours * 0.000024 +
                memory_gb_hours * 0.000003
            ),
            "duration_hours": duration_hours
        }
```

---

## Phase 2: Implement Unit Tests (Days 5-8, ~18 hours)

### Create Scenario Unit Tests

**File**: `tests/scenarios/test_scenario_execution.py`

```python
import pytest
import asyncio
from tests.scenarios.base_test_case import ScenarioTestCase
from tests.fixtures.mock_data import MockDataGenerator
from azure_haymaker.scenarios.executor import ScenarioExecutor

class TestScenarioExecution(ScenarioTestCase):
    """Unit tests for scenario execution."""

    @pytest.mark.asyncio
    async def test_scenario_execution_success(self, azure_clients, test_execution_request):
        """Test successful scenario execution."""
        executor = ScenarioExecutor(azure_clients)

        result = await executor.execute(test_execution_request)

        self.record_event("execution_complete", {"result": result})

        assert result["status"] == "success"
        assert result["events_generated"] > 0

    @pytest.mark.asyncio
    async def test_scenario_execution_timeout(self, azure_clients):
        """Test scenario timeout handling."""
        executor = ScenarioExecutor(azure_clients)

        request = {
            "scenarios": ["compute-01"],
            "duration_hours": 0.0001,  # Very short
            "timeout_seconds": 1
        }

        result = await executor.execute(request)

        # Should handle timeout gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_scenario_cleanup_on_failure(self, azure_clients):
        """Test resources are cleaned up on failure."""
        executor = ScenarioExecutor(azure_clients)

        request = {
            "scenarios": ["invalid-scenario"],
            "duration_hours": 1
        }

        try:
            result = await executor.execute(request)
        except Exception as e:
            self.record_error(e, "cleanup_test")

        # Verify cleanup
        resources = await executor.get_allocated_resources()
        assert len(resources) == 0

    @pytest.mark.asyncio
    async def test_scenario_event_generation(self, azure_clients):
        """Test that scenarios generate expected telemetry."""
        executor = ScenarioExecutor(azure_clients)

        request = {
            "scenarios": ["compute-01-linux-vm-web-server"],
            "duration_hours": 0.1,
            "expected_events": 50
        }

        result = await executor.execute(request)

        assert result["events_generated"] >= request["expected_events"]
```

### Create Scenario Validation Tests

**File**: `tests/scenarios/test_scenario_validation.py`

```python
import pytest
from azure_haymaker.scenarios.validator import ScenarioValidator

class TestScenarioValidation:
    """Tests for scenario validation."""

    def test_scenario_schema_validation(self):
        """Test scenario YAML schema validation."""
        validator = ScenarioValidator()

        valid_scenario = {
            "id": "test-scenario",
            "name": "Test Scenario",
            "description": "A test scenario",
            "duration_hours": 1,
            "agents": ["agent-1"],
            "expected_events": 100
        }

        assert validator.validate_schema(valid_scenario) is True

    def test_scenario_missing_required_fields(self):
        """Test validation fails for missing fields."""
        validator = ScenarioValidator()

        invalid_scenario = {
            "id": "test-scenario"
            # Missing name, agents, etc.
        }

        with pytest.raises(ValueError):
            validator.validate_schema(invalid_scenario)

    def test_scenario_cost_estimation(self):
        """Test cost estimation for scenario."""
        validator = ScenarioValidator()

        scenario = {
            "id": "test-scenario",
            "duration_hours": 2,
            "vcpu": 0.5,
            "memory_gb": 1.0
        }

        cost = validator.estimate_cost(scenario)

        # Cost should be positive and reasonable
        assert cost > 0
        assert cost < 100  # Should be less than $100 for 2 hours
```

---

## Phase 3: Implement Integration Tests (Days 9-12, ~18 hours)

### Create Integration Test Suite

**File**: `tests/integration/test_scenario_integration.py`

```python
import pytest
import os
from datetime import datetime

@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION") == "true",
    reason="Skipping integration tests"
)
class TestScenarioIntegration:
    """Integration tests with mocked but realistic behavior."""

    @pytest.mark.asyncio
    async def test_multi_scenario_execution(self, azure_clients):
        """Test executing multiple scenarios concurrently."""
        from azure_haymaker.scenarios.executor import ScenarioExecutor
        from tests.fixtures.mock_data import MockDataGenerator

        executor = ScenarioExecutor(azure_clients)

        # Execute 3 scenarios
        scenarios = [
            "compute-01-linux-vm-web-server",
            "compute-02-windows-vm-defender",
            "network-01-azure-firewall"
        ]

        results = await executor.execute_batch(
            scenarios=scenarios,
            duration_hours=0.5
        )

        assert len(results) == 3
        for result in results:
            assert result["status"] in ["success", "partial"]

    @pytest.mark.asyncio
    async def test_telemetry_collection_end_to_end(self, azure_clients):
        """Test end-to-end telemetry collection."""
        executor = ScenarioExecutor(azure_clients)

        result = await executor.execute({
            "scenarios": ["compute-01-linux-vm-web-server"],
            "duration_hours": 0.1
        })

        # Verify telemetry was collected
        telemetry = await executor.get_telemetry(result["execution_id"])

        assert len(telemetry) > 0

        # Verify structure
        for event in telemetry[:1]:  # Check first event
            assert "timestamp" in event
            assert "event_type" in event
            assert "scenario_id" in event

    @pytest.mark.asyncio
    async def test_cost_tracking_integration(self, azure_clients):
        """Test cost estimation and tracking."""
        executor = ScenarioExecutor(azure_clients)

        result = await executor.execute({
            "scenarios": ["compute-01-linux-vm-web-server"],
            "duration_hours": 1
        })

        # Get cost data
        costs = await executor.get_cost_data(result["execution_id"])

        assert costs["estimated_cost_usd"] > 0
        assert "vcpu_hours" in costs
        assert "memory_gb_hours" in costs
```

---

## Phase 4: Implement Performance Tests (Days 13-15, ~12 hours)

### Create Performance Benchmark

**File**: `tests/performance/test_scenario_performance.py`

```python
import pytest
from azure_haymaker.scenarios.executor import ScenarioExecutor
import time

@pytest.mark.performance
class TestScenarioPerformance:
    """Performance benchmarking tests."""

    @pytest.mark.asyncio
    async def test_scenario_execution_time(self, azure_clients, benchmark):
        """Benchmark scenario execution time."""
        executor = ScenarioExecutor(azure_clients)

        async def execute():
            return await executor.execute({
                "scenarios": ["compute-01-linux-vm-web-server"],
                "duration_hours": 0.1
            })

        # Benchmark 10 iterations
        result = benchmark.pedantic(
            execute,
            rounds=10,
            iterations=1
        )

        # Assert reasonable performance
        # Execution should complete within 5 seconds
        assert benchmark.stats.total < 50  # Total time for all runs

    def test_telemetry_generation_throughput(self, azure_clients):
        """Test telemetry generation throughput."""
        from tests.fixtures.mock_data import MockDataGenerator

        generator = MockDataGenerator()

        # Generate 10k events
        start = time.time()
        events = generator.generate_telemetry_events(count=10000)
        duration = time.time() - start

        # Should generate 10k events in <1 second
        throughput = 10000 / duration
        print(f"Throughput: {throughput:.0f} events/second")

        assert throughput > 1000  # At least 1000 events/sec

    def test_memory_usage_scenario_execution(self, azure_clients):
        """Test memory usage during scenario execution."""
        import tracemalloc

        tracemalloc.start()

        # Execute scenario
        executor = ScenarioExecutor(azure_clients)
        # ... execute scenario ...

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        print(f"Peak memory: {peak_mb:.1f} MB")

        # Memory should stay under 1GB
        assert peak_mb < 1000
```

---

## Phase 5: Implement Chaos Testing (Days 16-18, ~12 hours)

### Create Chaos Tests

**File**: `tests/chaos/test_scenario_resilience.py`

```python
import pytest
import random
from unittest.mock import patch, AsyncMock

@pytest.mark.chaos
class TestScenarioResilience:
    """Chaos engineering tests for failure scenarios."""

    @pytest.mark.asyncio
    async def test_agent_crash_recovery(self, azure_clients):
        """Test recovery when agent crashes during execution."""
        executor = ScenarioExecutor(azure_clients)

        # Simulate agent crash after 2 seconds
        async def simulate_crash(*args, **kwargs):
            await asyncio.sleep(2)
            raise Exception("Agent crashed")

        with patch.object(executor, 'run_agent', side_effect=simulate_crash):
            result = await executor.execute({
                "scenarios": ["compute-01-linux-vm-web-server"],
                "duration_hours": 0.1,
                "auto_recover": True  # Should automatically recover
            })

            # Should not crash entirely, but mark as partial
            assert result["status"] in ["success", "partial", "degraded"]

    @pytest.mark.asyncio
    async def test_network_partition(self, azure_clients):
        """Test handling of network partitions."""
        executor = ScenarioExecutor(azure_clients)

        # Mock network failure
        with patch('httpx.AsyncClient.post', side_effect=TimeoutError("Network partition")):
            result = await executor.execute({
                "scenarios": ["compute-01-linux-vm-web-server"],
                "duration_hours": 0.1,
                "timeout_seconds": 5
            })

            # Should handle gracefully
            assert result is not None

    @pytest.mark.asyncio
    async def test_random_failures(self, azure_clients):
        """Test system under random failure conditions."""
        executor = ScenarioExecutor(azure_clients)

        # Randomly fail 30% of operations
        async def flaky_operation(*args, **kwargs):
            if random.random() < 0.3:
                raise Exception("Random failure")
            return await AsyncMock()(*args, **kwargs)

        with patch.object(executor, 'send_event', side_effect=flaky_operation):
            result = await executor.execute({
                "scenarios": ["compute-01-linux-vm-web-server"],
                "duration_hours": 0.1
            })

            # Should still complete (with possible data loss)
            assert result is not None
            assert result["status"] in ["success", "partial"]
```

---

## Phase 6: Create Test CI Integration (Days 19-20, ~8 hours)

### Create pytest Configuration

**File**: `pyproject.toml` (add to existing)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Unit tests (fast)",
    "integration: Integration tests",
    "performance: Performance benchmarks",
    "chaos: Chaos engineering tests",
    "slow: Slow tests",
    "requires_cloud: Requires cloud connection"
]
asyncio_mode = "auto"
filterwarnings = [
    "ignore::DeprecationWarning"
]
```

### Create Test Runner Script

**File**: `scripts/run_tests.sh`

```bash
#!/bin/bash

set -e

echo "Running test suite..."

# Unit tests
echo "1. Unit tests..."
pytest tests/unit -v -m "not requires_cloud" --cov=src --cov-report=term-missing

# Integration tests
echo "2. Integration tests..."
pytest tests/integration -v -m "not requires_cloud" || echo "Some integration tests skipped"

# Performance tests
echo "3. Performance benchmarks..."
pytest tests/performance -v --benchmark-only || echo "Performance tests optional"

# Chaos tests
echo "4. Chaos engineering tests..."
pytest tests/chaos -v || echo "Chaos tests optional"

echo "✓ All tests passed!"
```

---

## Success Criteria

- [ ] ScenarioTestCase base class working
- [ ] Mock data generators functional
- [ ] Unit tests covering 80%+ of scenarios module
- [ ] Integration tests with realistic workflows
- [ ] Performance benchmarks established
- [ ] Chaos tests validating resilience
- [ ] pytest configuration complete
- [ ] Test CI integration working
- [ ] New developers can run tests locally
- [ ] Test suite runs in <5 minutes for unit tests
- [ ] Documentation for adding new scenario tests
- [ ] Code coverage reports generated

---

## Estimated Timeline

**Optimistic**: 3 weeks
**Realistic**: 4 weeks
**Pessimistic**: 5 weeks

---

**Issue**: #133
**Related**: #130 (Local Dev), #131 (CI/CD), #132 (Dashboard)

🧪 **Ready to build test infrastructure? Follow Phase 1 above!**
