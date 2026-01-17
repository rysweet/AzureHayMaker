"""Circuit breaker implementation for agent health management.

Provides circuit breaker pattern to protect against cascading failures
when agents become unhealthy. Tracks failure rates and automatically
opens/closes circuits based on configurable thresholds.

Philosophy:
- Thread-safe state management
- Simple, self-contained implementation (no external dependencies)
- Clear state transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED

Public API (the "studs"):
    CircuitState: Enum of circuit states
    CircuitBreakerConfig: Configuration dataclass
    AgentCircuitBreaker: Main circuit breaker implementation
"""

import asyncio
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states.

    CLOSED: Normal operation, requests pass through
    OPEN: Circuit is open, requests fail immediately
    HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes in half-open to close circuit
        timeout_seconds: Seconds to wait before transitioning from OPEN to HALF_OPEN
        half_open_max_calls: Maximum concurrent calls allowed in HALF_OPEN state
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 300
    half_open_max_calls: int = 1


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracked by the circuit breaker.

    Attributes:
        failure_count: Current consecutive failures (resets on success)
        success_count: Successes in HALF_OPEN state
        total_failures: All-time failure count
        total_successes: All-time success count
        last_failure_time: Timestamp of most recent failure
        last_state_change: Timestamp of most recent state transition
        open_count: Number of times circuit has opened
    """

    failure_count: int = 0
    success_count: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_failure_time: datetime | None = None
    last_state_change: datetime | None = None
    open_count: int = 0


class AgentCircuitBreaker:
    """Thread-safe circuit breaker for agent operations.

    Implements the circuit breaker pattern to prevent cascading failures.
    When failures exceed the threshold, the circuit opens and subsequent
    calls fail fast without executing the underlying function.

    Example:
        >>> config = CircuitBreakerConfig(failure_threshold=3)
        >>> breaker = AgentCircuitBreaker("my-agent", config)
        >>> result = await breaker.call(async_function, arg1, arg2)
        >>> print(breaker.state)  # CircuitState.CLOSED
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker (typically agent/scenario name)
            config: Configuration options, uses defaults if not provided
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._metrics = CircuitBreakerMetrics()
        self._lock = threading.RLock()
        self._half_open_calls = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout transition."""
        with self._lock:
            self._check_timeout_transition()
            return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics snapshot."""
        with self._lock:
            return CircuitBreakerMetrics(
                failure_count=self._metrics.failure_count,
                success_count=self._metrics.success_count,
                total_failures=self._metrics.total_failures,
                total_successes=self._metrics.total_successes,
                last_failure_time=self._metrics.last_failure_time,
                last_state_change=self._metrics.last_state_change,
                open_count=self._metrics.open_count,
            )

    @property
    def is_closed(self) -> bool:
        """Check if circuit is in CLOSED state."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is in OPEN state."""
        return self.state == CircuitState.OPEN

    def _check_timeout_transition(self) -> None:
        """Check if OPEN circuit should transition to HALF_OPEN.

        Must be called with lock held.
        """
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.config.timeout_seconds:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state.

        Must be called with lock held.

        Args:
            new_state: Target state to transition to
        """
        if self._state == new_state:
            return

        self._state = new_state
        self._metrics.last_state_change = datetime.now(UTC)

        if new_state == CircuitState.OPEN:
            self._opened_at = time.monotonic()
            self._metrics.open_count += 1
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._metrics.success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._metrics.failure_count = 0
            self._opened_at = None

    def _record_success(self) -> None:
        """Record a successful call.

        Must be called with lock held.
        """
        self._metrics.total_successes += 1
        self._metrics.failure_count = 0

        if self._state == CircuitState.HALF_OPEN:
            self._metrics.success_count += 1
            if self._metrics.success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, error: Exception | None = None) -> None:
        """Record a failed call.

        Must be called with lock held.

        Args:
            error: The exception that caused the failure (for logging)
        """
        self._metrics.total_failures += 1
        self._metrics.failure_count += 1
        self._metrics.last_failure_time = datetime.now(UTC)

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN reopens the circuit
            self._transition_to(CircuitState.OPEN)
        elif (
            self._state == CircuitState.CLOSED
            and self._metrics.failure_count >= self.config.failure_threshold
        ):
            self._transition_to(CircuitState.OPEN)

    def _can_execute(self) -> bool:
        """Check if execution is allowed in current state.

        Must be called with lock held.

        Returns:
            True if execution is allowed
        """
        self._check_timeout_transition()

        if self._state == CircuitState.CLOSED:
            return True
        elif self._state == CircuitState.OPEN:
            return False
        elif self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        return False

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func if successful

        Raises:
            CircuitOpenError: If circuit is open and call is rejected
            Exception: Any exception raised by func (also recorded as failure)
        """
        from azure_haymaker.exceptions import CircuitOpenError

        with self._lock:
            if not self._can_execute():
                raise CircuitOpenError(
                    f"Circuit breaker '{self.name}' is open",
                    circuit_name=self.name,
                    state=self._state.value,
                )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            with self._lock:
                self._record_success()

            return result

        except Exception as e:
            with self._lock:
                self._record_failure(e)
            raise

    def reset(self) -> None:
        """Reset circuit breaker to initial CLOSED state.

        Use with caution - typically called when manually recovering
        or during testing.
        """
        with self._lock:
            self._state = CircuitState.CLOSED
            self._metrics = CircuitBreakerMetrics()
            self._half_open_calls = 0
            self._opened_at = None

    def force_open(self) -> None:
        """Force circuit to OPEN state.

        Useful for manual intervention or maintenance.
        """
        with self._lock:
            self._transition_to(CircuitState.OPEN)

    def to_dict(self) -> dict[str, Any]:
        """Serialize circuit breaker state to dictionary.

        Returns:
            Dictionary representation of current state
        """
        with self._lock:
            self._check_timeout_transition()
            return {
                "name": self.name,
                "state": self._state.value,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "success_threshold": self.config.success_threshold,
                    "timeout_seconds": self.config.timeout_seconds,
                    "half_open_max_calls": self.config.half_open_max_calls,
                },
                "metrics": {
                    "failure_count": self._metrics.failure_count,
                    "success_count": self._metrics.success_count,
                    "total_failures": self._metrics.total_failures,
                    "total_successes": self._metrics.total_successes,
                    "last_failure_time": (
                        self._metrics.last_failure_time.isoformat()
                        if self._metrics.last_failure_time
                        else None
                    ),
                    "last_state_change": (
                        self._metrics.last_state_change.isoformat()
                        if self._metrics.last_state_change
                        else None
                    ),
                    "open_count": self._metrics.open_count,
                },
            }


@dataclass
class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.

    Provides centralized access to circuit breakers by name,
    with automatic creation using default configuration.

    Example:
        >>> registry = CircuitBreakerRegistry()
        >>> breaker = registry.get_or_create("agent-1")
        >>> all_breakers = registry.get_all()
    """

    default_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _breakers: dict[str, AgentCircuitBreaker] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> AgentCircuitBreaker:
        """Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker identifier
            config: Optional config, uses default if not provided

        Returns:
            Circuit breaker for the given name
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = AgentCircuitBreaker(
                    name=name,
                    config=config or self.default_config,
                )
            return self._breakers[name]

    def get(self, name: str) -> AgentCircuitBreaker | None:
        """Get circuit breaker by name if it exists.

        Args:
            name: Circuit breaker identifier

        Returns:
            Circuit breaker if found, None otherwise
        """
        with self._lock:
            return self._breakers.get(name)

    def get_all(self) -> dict[str, AgentCircuitBreaker]:
        """Get all registered circuit breakers.

        Returns:
            Dictionary of name to circuit breaker
        """
        with self._lock:
            return dict(self._breakers)

    def get_open_circuits(self) -> list[str]:
        """Get names of all circuits currently in OPEN state.

        Returns:
            List of circuit breaker names with open circuits
        """
        with self._lock:
            return [
                name
                for name, breaker in self._breakers.items()
                if breaker.state == CircuitState.OPEN
            ]

    def reset_all(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()

    def remove(self, name: str) -> bool:
        """Remove a circuit breaker from the registry.

        Args:
            name: Circuit breaker identifier

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                return True
            return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize all circuit breakers to dictionary.

        Returns:
            Dictionary with all circuit breaker states
        """
        with self._lock:
            return {
                "default_config": {
                    "failure_threshold": self.default_config.failure_threshold,
                    "success_threshold": self.default_config.success_threshold,
                    "timeout_seconds": self.default_config.timeout_seconds,
                    "half_open_max_calls": self.default_config.half_open_max_calls,
                },
                "circuit_breakers": {
                    name: breaker.to_dict() for name, breaker in self._breakers.items()
                },
                "summary": {
                    "total": len(self._breakers),
                    "open": len(self.get_open_circuits()),
                    "closed": sum(
                        1 for b in self._breakers.values() if b.state == CircuitState.CLOSED
                    ),
                    "half_open": sum(
                        1 for b in self._breakers.values() if b.state == CircuitState.HALF_OPEN
                    ),
                },
            }


__all__ = [
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "AgentCircuitBreaker",
    "CircuitBreakerRegistry",
]
