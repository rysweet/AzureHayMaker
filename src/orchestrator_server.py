"""Simple FastAPI orchestrator for Azure HayMaker.

NO AZURE FUNCTIONS. NO DURABLE FUNCTIONS. JUST WORKING CODE.

This replaces the Azure Functions implementation with a simple REST API
that can run anywhere - locally, Docker, or Azure Container Apps.

Architecture: Uses modular route handlers from azure_haymaker.orchestrator.routes
for clear separation of concerns and maintainability.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from azure_haymaker.models.execution import MultiTenantExecutionResponse
from azure_haymaker.orchestrator.routes import (
    analytics_router,
    execution_router,
    health_router,
    multi_tenant_router,
    run_orchestration,
    run_scheduled_orchestration,
    schedule_router,
)
from azure_haymaker.orchestrator.routes.analytics_routes import (
    set_executions_ref as set_analytics_executions_ref,
)
from azure_haymaker.orchestrator.routes.execution_routes import (
    set_executions_ref as set_execution_executions_ref,
)
from azure_haymaker.orchestrator.routes.execution_routes import (
    set_run_orchestration_fn as set_execution_run_fn,
)
from azure_haymaker.orchestrator.routes.health_routes import (
    set_executions_ref as set_health_executions_ref,
)
from azure_haymaker.orchestrator.routes.multi_tenant_routes import (
    set_meta_executions_ref,
)
from azure_haymaker.orchestrator.routes.multi_tenant_routes import (
    set_run_orchestration_fn as set_multi_tenant_run_fn,
)
from azure_haymaker.orchestrator.routes.orchestration_service import (
    set_executions_ref as set_service_executions_ref,
)
from azure_haymaker.orchestrator.routes.schedule_routes import (
    load_schedules_on_startup,
    set_scheduler_ref,
)
from azure_haymaker.orchestrator.routes.schedule_routes import (
    set_run_orchestration_fn as set_schedule_run_fn,
)
from azure_haymaker.tracing import init_tracing

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler
scheduler = AsyncIOScheduler()

# Track running executions (shared across route modules)
executions: dict[str, dict[str, Any]] = {}

# Track multi-tenant meta-executions (Phase 3)
meta_executions: dict[str, MultiTenantExecutionResponse] = {}


def _configure_route_modules() -> None:
    """Configure all route modules with shared state references.

    Injects the global executions dict and scheduler into route modules
    so they can access shared state without circular imports.
    """
    # Set executions reference for all modules that need it
    set_health_executions_ref(executions)
    set_execution_executions_ref(executions)
    set_analytics_executions_ref(executions)
    set_service_executions_ref(executions)

    # Set meta_executions reference for multi-tenant module
    set_meta_executions_ref(meta_executions)

    # Set scheduler reference for schedule module
    set_scheduler_ref(scheduler)

    # Set run_orchestration function references
    set_execution_run_fn(run_orchestration)
    set_schedule_run_fn(run_orchestration)
    set_multi_tenant_run_fn(run_orchestration)


async def _load_schedules_with_timeout() -> None:
    """Load schedules with timeout to prevent startup delays."""
    try:
        async with asyncio.timeout(10):  # 10 second timeout
            await load_schedules_on_startup()
    except TimeoutError:
        logger.warning("Schedule loading timed out - will retry later")
    except Exception as e:
        logger.warning(f"Schedule loading failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - starts/stops scheduler."""
    logger.info("Starting orchestrator server")

    # Initialize distributed tracing (optional - depends on connection string)
    init_tracing("azure-haymaker-orchestrator")

    # Configure route modules with shared state
    _configure_route_modules()

    scheduler.start()

    # Schedule default orchestration runs: 4x daily (00:00, 06:00, 12:00, 18:00 UTC)
    scheduler.add_job(
        run_scheduled_orchestration,
        "cron",
        hour="0,6,12,18",
        id="haymaker_orchestration",
    )
    logger.info("Scheduled default orchestration runs: 00:00, 06:00, 12:00, 18:00 UTC")

    # Load user-defined schedules from storage (non-blocking to prevent startup delays)
    # Run in background task to avoid blocking Container Apps health checks
    asyncio.create_task(_load_schedules_with_timeout())

    yield

    logger.info("Shutting down orchestrator server")
    scheduler.shutdown()

    # Shutdown tracing to flush any pending spans
    from azure_haymaker.tracing.core import shutdown_tracing

    shutdown_tracing()


app = FastAPI(title="Azure HayMaker Orchestrator", lifespan=lifespan)

# ==============================================================================
# REGISTER ROUTE MODULES
# ==============================================================================

# Health routes (no prefix - root level endpoints)
app.include_router(health_router)

# API routes (all prefixed with /api)
app.include_router(schedule_router, prefix="/api")
app.include_router(execution_router, prefix="/api")
app.include_router(multi_tenant_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
