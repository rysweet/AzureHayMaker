"""Orchestrator route modules.

This package contains decomposed route handlers from orchestrator_server.py.
Each module is a self-contained brick following single-responsibility principle.

Public API (the "studs"):
    health_router: Health, status, and infrastructure endpoints
    schedule_router: Schedule CRUD operations
    execution_router: Execution management endpoints
    multi_tenant_router: Multi-tenant execution endpoints
    analytics_router: Analytics and metrics endpoints
    run_orchestration: Main orchestration workflow function
    run_scheduled_orchestration: Cron-triggered orchestration

Module Configuration:
    Each route module provides set_*_ref() functions to inject shared state.
    Call these from the main app during startup to configure dependencies.
"""

from .analytics_routes import router as analytics_router
from .execution_routes import router as execution_router
from .health_routes import router as health_router
from .multi_tenant_routes import router as multi_tenant_router
from .orchestration_service import run_orchestration, run_scheduled_orchestration
from .schedule_routes import router as schedule_router

__all__ = [
    # Route routers
    "analytics_router",
    "execution_router",
    "health_router",
    "multi_tenant_router",
    "schedule_router",
    # Orchestration service functions
    "run_orchestration",
    "run_scheduled_orchestration",
]
