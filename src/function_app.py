"""Azure Functions entry point for Azure HayMaker orchestrator.

This module exposes the Azure Functions from the orchestrator module
to the Azure Functions runtime.
"""

# Import the Function App instance from orchestrator
from azure_haymaker.orchestrator import app

# CRITICAL: Import all function modules to trigger decorator execution
# Azure Functions discovers functions by executing decorators at import time
from azure_haymaker.orchestrator import (
    haymaker_timer,  # Timer trigger
    orchestrate_haymaker_run,  # Orchestration function
    # Activity functions
    validate_environment_activity,
    select_scenarios_activity,
    create_service_principal_activity,
    deploy_container_app_activity,
    check_agent_status_activity,
    verify_cleanup_activity,
    force_cleanup_activity,
    generate_report_activity,
)

# Export app AND all functions so Azure Functions runtime can find them
__all__ = [
    "app",
    "haymaker_timer",
    "orchestrate_haymaker_run",
    "validate_environment_activity",
    "select_scenarios_activity",
    "create_service_principal_activity",
    "deploy_container_app_activity",
    "check_agent_status_activity",
    "verify_cleanup_activity",
    "force_cleanup_activity",
    "generate_report_activity",
]
