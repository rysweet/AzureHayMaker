# Getting Started: Agent Health Checks and Circuit Breakers (Issue #129)

**Your complete guide to implementing Issue #129**

**Priority**: P1-High | **Effort**: 2 weeks | **ROI**: 150%

---

## What You're Building

Implement health checks, circuit breakers, and automatic recovery to prevent cascading failures when agents fail. Stop wasting resources on stuck/zombie agents.

**Why It Matters**: Production systems need resilience. One failing agent shouldn't bring down the entire system.

**Business Value**: Reduces MTTR from hours to minutes, prevents resource waste from stuck agents.

---

## Before You Start (15 minutes)

### 1. Understand Circuit Breaker Pattern

**Resources**:
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
- Azure SDK resilience: Built into most Azure libraries

### 2. Check Dependencies

```bash
# Verify you have the pybreaker library available or will install it
grep -i "pybreaker\|circuitbreaker" pyproject.toml || echo "Need to add to pyproject.toml"
```

### 3. Review Current Agent Structure

```bash
# Understand how agents currently execute
ls -la src/azure_haymaker/agents/
find src -name "*.py" -path "*/agents/*" | head -10
```

---

## Phase 1: Set Up Structure (Day 1, ~3 hours)

### Create Branch
```bash
git checkout main
git pull origin main
git checkout -b feat/issue-129-circuit-breakers
```

### Create Directory Structure
```bash
mkdir -p src/azure_haymaker/orchestrator/health
touch src/azure_haymaker/orchestrator/health/__init__.py
touch src/azure_haymaker/orchestrator/health/circuit_breaker.py
touch src/azure_haymaker/orchestrator/health/health_monitor.py
touch src/azure_haymaker/orchestrator/health/models.py
```

### Add Dependencies
```bash
# Add to pyproject.toml [project.dependencies]
# pybreaker = "^0.7.0"

uv sync
```

### Create Health Models

**File**: `src/azure_haymaker/orchestrator/health/models.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Literal

class HealthStatus(BaseModel):
    """Agent health status."""
    agent_id: str
    status: Literal["healthy", "degraded", "failing"]
    last_check: datetime
    consecutive_failures: int
    response_time_ms: float
    error_message: str | None = None

class CircuitBreakerState(BaseModel):
    """Circuit breaker state tracking."""
    agent_id: str
    state: Literal["closed", "open", "half_open"]
    failure_count: int
    success_count: int
    last_failure_time: datetime | None = None
    recovery_attempts: int = 0
```

---

## Phase 2: Implement Circuit Breaker (Days 2-3, ~12 hours)

**File**: `src/azure_haymaker/orchestrator/health/circuit_breaker.py`

### Key Methods to Implement

1. **CircuitBreakerWrapper** class:
   - `__call__()` - Wrap agent execution
   - `on_success()` - Reset failure count
   - `on_failure()` - Increment failure count, trip if threshold exceeded
   - `is_open()` - Check if circuit open
   - `try_recover()` - Attempt half-open state

2. **Implementation Structure**:

```python
from datetime import datetime, timedelta
from typing import Callable, Any
import asyncio

class CircuitBreaker:
    """Prevents cascading failures using circuit breaker pattern."""

    def __init__(
        self,
        agent_id: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60
    ):
        self.agent_id = agent_id
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)

        self.state = "closed"  # closed, open, half_open
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    async def execute(self, agent_fn: Callable, *args, **kwargs) -> Any:
        """Execute agent function with circuit breaker protection."""

        # Check if open
        if self.state == "open":
            if self._should_attempt_recovery():
                self.state = "half_open"
            else:
                raise Exception(f"Circuit breaker open for {self.agent_id}")

        try:
            # Execute agent
            result = await agent_fn(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        """Handle successful execution."""
        if self.state == "half_open":
            self.state = "closed"
        self.failure_count = 0
        self.success_count += 1

    def on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time passed to try recovery."""
        if self.last_failure_time is None:
            return False
        return datetime.now() - self.last_failure_time > self.recovery_timeout
```

---

## Phase 3: Implement Health Monitor (Days 4-5, ~12 hours)

**File**: `src/azure_haymaker/orchestrator/health/health_monitor.py`

### Key Features

1. **AgentHealthMonitor** class:
   - `add_agent()` - Register agent for monitoring
   - `check_health()` - Poll single agent
   - `check_all_agents()` - Periodic monitoring loop
   - `get_health_status()` - Get current status
   - `quarantine_agent()` - Disable failing agent

2. **Implementation Structure**:

```python
import asyncio
from datetime import datetime

class AgentHealthMonitor:
    """Monitors agent health and manages circuit breakers."""

    def __init__(self, check_interval_seconds: int = 30):
        self.check_interval = check_interval_seconds
        self.circuit_breakers = {}
        self.health_status = {}
        self.quarantined_agents = set()

    async def check_agent_health(self, agent_id: str) -> HealthStatus:
        """Check single agent health via /health endpoint."""
        # TODO: Implement
        # - Call agent /health endpoint
        # - Measure response time
        # - Track consecutive failures
        # - Update circuit breaker state
        pass

    async def monitor_loop(self):
        """Continuous health monitoring."""
        while True:
            for agent_id in self.circuit_breakers:
                try:
                    status = await self.check_agent_health(agent_id)

                    # Auto-quarantine if failing >50%
                    if status.consecutive_failures > 5:
                        await self.quarantine_agent(agent_id, "repeated failures")

                except Exception as e:
                    # Silently log - don't crash monitor
                    pass

            await asyncio.sleep(self.check_interval)

    async def quarantine_agent(self, agent_id: str, reason: str):
        """Mark agent as quarantined (disabled)."""
        self.quarantined_agents.add(agent_id)
        # TODO: Update Schedule model to mark as quarantined
```

---

## Phase 4: Add /health Endpoint to Agents (Days 6-7, ~10 hours)

### Create Agent Health Mixin

**File**: `src/azure_haymaker/agents/base_agent.py`

```python
@app.get("/health")
async def health_check():
    """Agent health check endpoint."""
    return {
        "status": "healthy",
        "uptime_seconds": get_uptime(),
        "memory_mb": get_memory_usage(),
        "pending_tasks": len(pending_queue),
        "last_execution": get_last_execution_time(),
        "error_rate": calculate_error_rate()
    }
```

### Key Metrics to Track

- Response time (ms)
- Error rate (%)
- Memory usage (MB)
- Pending task count
- Last execution timestamp

---

## Phase 5: Integrate with Orchestrator (Days 8-9, ~10 hours)

**File**: `src/orchestrator_server.py`

### Update Execution Endpoint

```python
from azure_haymaker.orchestrator.health import CircuitBreaker, AgentHealthMonitor

health_monitor = AgentHealthMonitor()

@app.post("/api/execute")
async def execute(request: ExecutionRequest):
    # Check if agent is quarantined
    for agent in request.agents:
        if agent.id in health_monitor.quarantined_agents:
            raise HTTPException(
                status_code=423,
                detail=f"Agent {agent.id} is quarantined due to repeated failures"
            )

    # Wrap execution with circuit breaker
    circuit_breaker = health_monitor.circuit_breakers.get(agent.id)
    try:
        result = await circuit_breaker.execute(
            orchestrate_agents,
            request
        )
        return result
    except Exception as e:
        if "circuit breaker open" in str(e):
            raise HTTPException(status_code=503, detail="Agent unavailable - circuit breaker open")
        raise
```

### Start Health Monitor

```python
@app.on_event("startup")
async def startup():
    # Start monitoring in background
    asyncio.create_task(health_monitor.monitor_loop())
```

### Add Health Status Endpoint

```python
@app.get("/api/health/status")
async def get_health_status():
    """Get health status of all agents."""
    return {
        "agents": health_monitor.health_status,
        "quarantined": list(health_monitor.quarantined_agents),
        "circuit_breakers": {
            agent_id: {
                "state": cb.state,
                "failure_count": cb.failure_count
            }
            for agent_id, cb in health_monitor.circuit_breakers.items()
        }
    }
```

---

## Phase 6: Update Schedule Model (Day 10, ~4 hours)

**File**: `src/azure_haymaker/models/schedule.py`

```python
class Schedule(BaseModel):
    # ... existing fields ...

    # New fields
    status: Literal["active", "quarantined"] = "active"
    quarantine_reason: str | None = None
    failure_rate: float = 0.0
```

---

## Testing

### Unit Tests

**File**: `tests/unit/health/test_circuit_breaker.py`

```python
import pytest
from azure_haymaker.orchestrator.health.circuit_breaker import CircuitBreaker

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Circuit breaker opens after failure threshold."""
    cb = CircuitBreaker("agent-1", failure_threshold=3)

    async def failing_fn():
        raise Exception("Agent failed")

    # Trigger failures
    for _ in range(3):
        try:
            await cb.execute(failing_fn)
        except:
            pass

    # Circuit should be open
    assert cb.state == "open"

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Circuit breaker attempts recovery after timeout."""
    cb = CircuitBreaker("agent-1", failure_threshold=2, recovery_timeout_seconds=1)

    # Open circuit
    cb.on_failure()
    cb.on_failure()
    assert cb.state == "open"

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Should enter half-open
    assert cb._should_attempt_recovery() is True
```

### E2E Testing

```bash
# 1. Start orchestrator
uvicorn orchestrator_server:app

# 2. Check initial health
curl http://localhost:8000/api/health/status

# 3. Simulate agent failure (stop agent container)
docker stop agent-1

# 4. Monitor health endpoint (should show degraded)
for i in {1..10}; do
  curl http://localhost:8000/api/health/status
  sleep 3
done

# 5. Verify circuit breaker opened
# Should see: "state": "open"

# 6. Restart agent
docker start agent-1

# 7. Verify recovery (state -> half_open -> closed)
```

---

## Success Criteria

Before marking complete:

- [ ] CircuitBreaker class working (open/closed/half-open states)
- [ ] /health endpoint implemented on all agents
- [ ] AgentHealthMonitor polling agents every 30 seconds
- [ ] Circuit breaker opens after 5 consecutive failures
- [ ] Auto-recovery after 60 seconds timeout
- [ ] Agents auto-quarantine after repeated failures
- [ ] Health status endpoint returning correct data
- [ ] Unit tests passing (80%+ coverage)
- [ ] E2E test demonstrating failure + recovery
- [ ] Documentation updated

---

## Common Issues & Solutions

**Issue**: Import errors from CircuitBreaker module
**Solution**: Add `__init__.py` files, verify import paths

**Issue**: Health check endpoint timing out
**Solution**: Add timeout to health check calls (e.g., 5 seconds)

**Issue**: Circuit breaker never recovers
**Solution**: Check recovery timeout is configured, verify clock sync

---

## Getting Help

- Comment on Issue #129 for questions
- Review pybreaker documentation: https://github.com/danielfm/pybreaker
- Check related code: `src/azure_haymaker/orchestrator/` existing patterns

---

## Estimated Timeline

**Optimistic**: 1.5 weeks
**Realistic**: 2 weeks
**Pessimistic**: 2.5 weeks

---

**Full Spec**: Issue #129
**Related**: #127 (Distributed Tracing), #128 (Cost Enforcement)

🛡️ **Ready to add resilience? Follow Phase 1 above!**
