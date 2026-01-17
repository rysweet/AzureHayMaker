# Orchestrator Routes Module

This module contains the HTTP route handlers for the Azure HayMaker Orchestrator API.
Each module is a self-contained "brick" following the project philosophy.

## Architecture

```
routes/
├── __init__.py              # Exports all routers for FastAPI include
├── health_routes.py         # Health, status, and infrastructure endpoints
├── schedule_routes.py       # Schedule CRUD operations with APScheduler integration
├── execution_routes.py      # Execution management and cost endpoints
├── multi_tenant_routes.py   # Multi-tenant parallel execution endpoints
├── analytics_routes.py      # Analytics and metrics endpoints
└── orchestration_service.py # Background orchestration logic (non-route)
```

## Module Responsibilities

### health_routes.py
**Single Responsibility**: Server health, status, and infrastructure queries.

Public API:
- `GET /` - Health check (unauthenticated)
- `GET /api/status` - Orchestrator status
- `GET /api/resources` - List HayMaker-managed Azure resources
- `GET /api/agents` - List agent executions

### schedule_routes.py
**Single Responsibility**: Schedule CRUD operations and APScheduler integration.

Public API:
- `POST /api/schedules` - Create a new schedule
- `GET /api/schedules` - List all schedules
- `GET /api/schedules/{id}` - Get a specific schedule
- `PUT /api/schedules/{id}` - Update a schedule
- `DELETE /api/schedules/{id}` - Delete a schedule

Internal Functions:
- Cron expression validation
- Table Storage entity conversion
- APScheduler job management

### execution_routes.py
**Single Responsibility**: Execution lifecycle management.

Public API:
- `GET /api/executions` - List all executions
- `GET /api/executions/{id}` - Get execution details
- `GET /api/executions/{id}/cost` - Get execution cost summary
- `POST /api/execute` - Trigger manual execution
- `POST /api/validate` - Validate environment configuration
- `GET /api/scenarios` - List available scenarios

### multi_tenant_routes.py
**Single Responsibility**: Multi-tenant parallel execution orchestration.

Public API:
- `POST /api/execute/multi-tenant` - Execute across multiple tenants
- `GET /api/executions/{id}/tenants` - Get multi-tenant execution status
- `GET /api/meta-executions` - List all multi-tenant executions

### analytics_routes.py
**Single Responsibility**: Metrics and analytics aggregation.

Public API:
- `GET /api/metrics` - Get execution metrics
- `GET /api/analytics` - Get analytics summary (7d/30d/90d periods)

### orchestration_service.py
**Single Responsibility**: Background orchestration workflow execution.

Public API:
- `run_scheduled_orchestration()` - Run orchestration triggered by cron
- `run_orchestration()` - Main orchestration workflow (6 phases)

## Usage

The main `orchestrator_server.py` imports and includes all routers:

```python
from azure_haymaker.orchestrator.routes import (
    health_router,
    schedule_router,
    execution_router,
    multi_tenant_router,
    analytics_router,
)

app.include_router(health_router)
app.include_router(schedule_router, prefix="/api")
app.include_router(execution_router, prefix="/api")
app.include_router(multi_tenant_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
```

## Philosophy Compliance

Each module follows the Brick Philosophy:
- **Self-contained**: All related functions grouped together
- **Single responsibility**: ONE clear purpose per module
- **Clear public API**: Exports defined via `__all__`
- **Regeneratable**: Can be rebuilt from this specification

## Dependencies

All route modules depend on:
- FastAPI's `APIRouter` for route registration
- `AuthDep` from `azure_haymaker.orchestrator.auth` for authentication
- Pydantic models from `azure_haymaker.models.*`

The orchestration service depends on:
- Various orchestrator submodules (config, validation, cleanup, etc.)
- Azure SDK clients for resource management
