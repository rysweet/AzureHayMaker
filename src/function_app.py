"""Azure Functions entry point for Azure HayMaker orchestrator.

This module imports the FunctionApp instance and all decorated functions
DIRECTLY from their source modules, bypassing __init__.py's try-except that
sets everything to None on any import error.

CRITICAL: Import directly from submodules, not from __init__.py facade!
"""

# Import app instance directly from orchestrator_app.py
from azure_haymaker.orchestrator.orchestrator_app import app

# Import decorated functions DIRECTLY from their source modules
# This bypasses __init__.py's try-except that sets functions to None
from azure_haymaker.orchestrator.timer_trigger import haymaker_timer
from azure_haymaker.orchestrator.workflow_orchestrator import orchestrate_haymaker_run
from azure_haymaker.orchestrator.activities.validation import validate_environment_activity
from azure_haymaker.orchestrator.activities.selection import select_scenarios_activity
from azure_haymaker.orchestrator.activities.provisioning import (
    create_service_principal_activity,
    deploy_container_app_activity,
)
from azure_haymaker.orchestrator.activities.monitoring import check_agent_status_activity
from azure_haymaker.orchestrator.activities.cleanup import (
    verify_cleanup_activity,
    force_cleanup_activity,
)
from azure_haymaker.orchestrator.activities.reporting import generate_report_activity

# Azure Functions discovers app via FunctionRegister type inspection
# All decorated functions are already registered on app instance via decorator execution
