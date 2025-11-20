"""Azure Functions entry point for Azure HayMaker orchestrator.

This module imports the FunctionApp instance and all decorated functions
from the orchestrator module, making them discoverable by Azure Functions runtime.

CRITICAL: Must import the SAME app instance that decorators used, not create new one.
"""

# Import app instance (created in orchestrator_app.py)
from azure_haymaker.orchestrator.orchestrator_app import app

# Import all decorated function modules to execute decorators
# These imports trigger the @app.timer_trigger, @app.orchestration_trigger,
# and @app.activity_trigger decorators, registering functions with the app instance
from azure_haymaker.orchestrator.timer_trigger import haymaker_timer
from azure_haymaker.orchestrator.workflow_orchestrator import orchestrate_haymaker_run
from azure_haymaker.orchestrator.activities.validation import (
    validate_environment_activity,
)
from azure_haymaker.orchestrator.activities.selection import select_scenarios_activity
from azure_haymaker.orchestrator.activities.provisioning import (
    create_service_principal_activity,
    deploy_container_app_activity,
)
from azure_haymaker.orchestrator.activities.monitoring import check_agent_status_activity
from azure_haymaker.orchestrator.activities.cleanup import (
    force_cleanup_activity,
    verify_cleanup_activity,
)
from azure_haymaker.orchestrator.activities.reporting import generate_report_activity

# No __all__ needed - Azure Functions discovers via app instance introspection
