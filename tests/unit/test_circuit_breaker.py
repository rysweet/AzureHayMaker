"""Unit tests for circuit breaker implementation.

Tests cover:
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure tracking and thresholds
- Success recovery
- Timeout-based recovery
- Thread safety
- Registry operations
"""

import threading
import time

import pytest

from azure_haymaker.exceptions import CircuitOpenError
from azure_haymaker.orchestrator.circuit_breaker import (
    AgentCircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)

# =============================================================================
# CircuitState Tests
# =============================================================================


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_state_values(self):
        """States should have expected string values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_state_is_string_enum(self):
        """CircuitState should be usable as string."""
        assert str(CircuitState.CLOSED) == "CircuitState.CLOSED"
        assert CircuitState.CLOSED == "closed"


# =============================================================================
# CircuitBreakerConfig Tests
# =============================================================================


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig dataclass."""

    def test_default_values(self):
        """Config should have sensible defaults."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout_seconds == 300
        assert config.half_open_max_calls == 1

    def test_custom_values(self):
        """Config should accept custom values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=1,
            timeout_seconds=60,
            half_open_max_calls=2,
        )
        assert config.failure_threshold == 3
        assert config.success_threshold == 1
        assert config.timeout_seconds == 60
        assert config.half_open_max_calls == 2


# =============================================================================
# AgentCircuitBreaker Core Tests
# =============================================================================


class TestAgentCircuitBreakerInitialization:
    """Tests for circuit breaker initialization."""

    def test_initial_state_is_closed(self):
        """New circuit breaker should start in CLOSED state."""
        breaker = AgentCircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True
        assert breaker.is_open is False

    def test_uses_default_config(self):
        """Circuit breaker should use default config if none provided."""
        breaker = AgentCircuitBreaker("test")
        assert breaker.config.failure_threshold == 5

    def test_accepts_custom_config(self):
        """Circuit breaker should accept custom config."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = AgentCircuitBreaker("test", config=config)
        assert breaker.config.failure_threshold == 3

    def test_initial_metrics_are_zero(self):
        """Initial metrics should all be zero."""
        breaker = AgentCircuitBreaker("test")
        metrics = breaker.metrics
        assert metrics.failure_count == 0
        assert metrics.success_count == 0
        assert metrics.total_failures == 0
        assert metrics.total_successes == 0
        assert metrics.open_count == 0


# =============================================================================
# State Transition Tests
# =============================================================================


class TestStateTransitions:
    """Tests for circuit breaker state transitions."""

    @pytest.fixture
    def breaker(self):
        """Create a circuit breaker with low thresholds for testing."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1,  # Short timeout for testing
        )
        return AgentCircuitBreaker("test", config)

    @pytest.mark.asyncio
    async def test_closed_to_open_on_failures(self, breaker):
        """Circuit should open after reaching failure threshold."""

        # Create a failing function
        async def failing_func():
            raise ValueError("Test failure")

        # Fail up to threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Circuit should now be open
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open is True

    @pytest.mark.asyncio
    async def test_open_rejects_calls(self, breaker):
        """Open circuit should reject calls with CircuitOpenError."""
        # Force circuit open
        breaker.force_open()

        async def test_func():
            return "should not reach"

        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.call(test_func)

        assert "test" in str(exc_info.value)
        assert exc_info.value.circuit_name == "test"

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self, breaker):
        """Circuit should transition to HALF_OPEN after timeout."""
        breaker.force_open()
        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        # Access state to trigger timeout check
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self):
        """Circuit should close after success threshold in HALF_OPEN."""
        # Use config with higher half_open_max_calls to allow consecutive calls
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1,
            half_open_max_calls=3,  # Allow multiple calls in half-open
        )
        breaker = AgentCircuitBreaker("test-close", config)

        breaker.force_open()
        time.sleep(1.1)  # Wait for HALF_OPEN

        async def success_func():
            return "success"

        # First success
        result1 = await breaker.call(success_func)
        assert result1 == "success"

        # Still in HALF_OPEN after one success (need 2 for threshold)
        assert breaker.state == CircuitState.HALF_OPEN

        # Second success should close the circuit
        result2 = await breaker.call(success_func)
        assert result2 == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self, breaker):
        """Circuit should reopen immediately on failure in HALF_OPEN."""
        breaker.force_open()
        time.sleep(1.1)  # Wait for HALF_OPEN
        assert breaker.state == CircuitState.HALF_OPEN

        async def failing_func():
            raise ValueError("Test failure")

        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        # Should be back to OPEN
        assert breaker.state == CircuitState.OPEN


# =============================================================================
# Success and Failure Recording Tests
# =============================================================================


class TestSuccessFailureRecording:
    """Tests for success and failure recording."""

    @pytest.fixture
    def breaker(self):
        """Create circuit breaker with default config."""
        return AgentCircuitBreaker("test")

    @pytest.mark.asyncio
    async def test_success_increments_metrics(self, breaker):
        """Successful calls should increment success metrics."""

        async def success_func():
            return "result"

        await breaker.call(success_func)

        metrics = breaker.metrics
        assert metrics.total_successes == 1
        assert metrics.total_failures == 0
        assert metrics.failure_count == 0

    @pytest.mark.asyncio
    async def test_failure_increments_metrics(self, breaker):
        """Failed calls should increment failure metrics."""

        async def failing_func():
            raise ValueError("Test")

        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        metrics = breaker.metrics
        assert metrics.total_failures == 1
        assert metrics.total_successes == 0
        assert metrics.failure_count == 1
        assert metrics.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, breaker):
        """Success should reset consecutive failure count."""

        async def failing_func():
            raise ValueError("Test")

        async def success_func():
            return "result"

        # Record some failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.metrics.failure_count == 2

        # Success resets consecutive failures
        await breaker.call(success_func)
        assert breaker.metrics.failure_count == 0
        assert breaker.metrics.total_failures == 2  # Total unchanged


# =============================================================================
# Synchronous Function Tests
# =============================================================================


class TestSyncFunctionSupport:
    """Tests for synchronous function support."""

    @pytest.mark.asyncio
    async def test_sync_function_works(self):
        """Circuit breaker should work with sync functions."""
        breaker = AgentCircuitBreaker("test")

        def sync_func(x, y):
            return x + y

        result = await breaker.call(sync_func, 1, 2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_sync_failure_recorded(self):
        """Sync function failures should be recorded."""
        breaker = AgentCircuitBreaker("test")

        def sync_failing():
            raise RuntimeError("Sync error")

        with pytest.raises(RuntimeError):
            await breaker.call(sync_failing)

        assert breaker.metrics.total_failures == 1


# =============================================================================
# Reset and Force Open Tests
# =============================================================================


class TestResetAndForceOpen:
    """Tests for reset and force_open methods."""

    def test_reset_clears_state(self):
        """Reset should return circuit to initial state."""
        breaker = AgentCircuitBreaker("test")
        breaker.force_open()
        assert breaker.state == CircuitState.OPEN

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.metrics.failure_count == 0
        assert breaker.metrics.open_count == 0

    def test_force_open_opens_circuit(self):
        """Force open should immediately open circuit."""
        breaker = AgentCircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED

        breaker.force_open()
        assert breaker.state == CircuitState.OPEN
        assert breaker.metrics.open_count == 1


# =============================================================================
# Serialization Tests
# =============================================================================


class TestSerialization:
    """Tests for circuit breaker serialization."""

    def test_to_dict_includes_all_fields(self):
        """to_dict should include all relevant state."""
        breaker = AgentCircuitBreaker("test-breaker")
        data = breaker.to_dict()

        assert data["name"] == "test-breaker"
        assert data["state"] == "closed"
        assert "config" in data
        assert "metrics" in data
        assert data["config"]["failure_threshold"] == 5
        assert data["metrics"]["total_failures"] == 0

    def test_to_dict_after_failures(self):
        """to_dict should reflect failure state."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = AgentCircuitBreaker("test", config)
        breaker.force_open()

        data = breaker.to_dict()
        assert data["state"] == "open"
        assert data["metrics"]["open_count"] == 1


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_state_access(self):
        """Multiple threads should safely access state."""
        breaker = AgentCircuitBreaker("test")
        results = []
        errors = []

        def access_state():
            try:
                for _ in range(100):
                    _ = breaker.state
                    _ = breaker.metrics
                results.append(True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_state) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10


# =============================================================================
# CircuitBreakerRegistry Tests
# =============================================================================


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    def test_get_or_create_new(self):
        """get_or_create should create new breaker if not exists."""
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("agent-1")

        assert breaker is not None
        assert breaker.name == "agent-1"

    def test_get_or_create_returns_existing(self):
        """get_or_create should return same instance for same name."""
        registry = CircuitBreakerRegistry()
        breaker1 = registry.get_or_create("agent-1")
        breaker2 = registry.get_or_create("agent-1")

        assert breaker1 is breaker2

    def test_get_returns_none_if_not_exists(self):
        """get should return None if breaker doesn't exist."""
        registry = CircuitBreakerRegistry()
        breaker = registry.get("nonexistent")

        assert breaker is None

    def test_get_returns_existing(self):
        """get should return existing breaker."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("agent-1")
        breaker = registry.get("agent-1")

        assert breaker is not None
        assert breaker.name == "agent-1"

    def test_get_all_returns_all_breakers(self):
        """get_all should return all registered breakers."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("agent-1")
        registry.get_or_create("agent-2")

        all_breakers = registry.get_all()
        assert len(all_breakers) == 2
        assert "agent-1" in all_breakers
        assert "agent-2" in all_breakers

    def test_get_open_circuits_empty(self):
        """get_open_circuits should return empty list when none open."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("agent-1")

        open_circuits = registry.get_open_circuits()
        assert open_circuits == []

    def test_get_open_circuits_returns_open(self):
        """get_open_circuits should return names of open circuits."""
        registry = CircuitBreakerRegistry()
        breaker1 = registry.get_or_create("agent-1")
        registry.get_or_create("agent-2")

        breaker1.force_open()

        open_circuits = registry.get_open_circuits()
        assert "agent-1" in open_circuits
        assert "agent-2" not in open_circuits

    def test_reset_all(self):
        """reset_all should reset all breakers."""
        registry = CircuitBreakerRegistry()
        breaker1 = registry.get_or_create("agent-1")
        breaker2 = registry.get_or_create("agent-2")

        breaker1.force_open()
        breaker2.force_open()

        registry.reset_all()

        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED

    def test_remove_breaker(self):
        """remove should delete breaker from registry."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("agent-1")

        assert registry.remove("agent-1") is True
        assert registry.get("agent-1") is None
        assert registry.remove("agent-1") is False  # Already removed

    def test_custom_default_config(self):
        """Registry should use custom default config."""
        custom_config = CircuitBreakerConfig(failure_threshold=10)
        registry = CircuitBreakerRegistry(default_config=custom_config)
        breaker = registry.get_or_create("agent-1")

        assert breaker.config.failure_threshold == 10

    def test_to_dict_summary(self):
        """to_dict should include summary statistics."""
        registry = CircuitBreakerRegistry()
        breaker1 = registry.get_or_create("agent-1")
        registry.get_or_create("agent-2")

        breaker1.force_open()

        data = registry.to_dict()
        assert data["summary"]["total"] == 2
        assert data["summary"]["open"] == 1
        assert data["summary"]["closed"] == 1


# =============================================================================
# Exception Tests
# =============================================================================


class TestCircuitOpenError:
    """Tests for CircuitOpenError exception."""

    def test_error_contains_circuit_info(self):
        """CircuitOpenError should contain circuit information."""
        error = CircuitOpenError(
            "Circuit is open",
            circuit_name="test-circuit",
            state="open",
        )

        assert error.circuit_name == "test-circuit"
        assert error.state == "open"
        assert "test-circuit" in str(error) or "Circuit is open" in str(error)

    def test_error_details(self):
        """CircuitOpenError should have details dict."""
        error = CircuitOpenError(
            "Circuit is open",
            circuit_name="test",
            state="open",
        )

        assert error.details["circuit_name"] == "test"
        assert error.details["state"] == "open"
