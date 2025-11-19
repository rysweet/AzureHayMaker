"""Azure HayMaker orchestration service.

Backward Compatibility Facade:
This module maintains backward compatibility after splitting orchestrator.py
into separate modules. All orchestrator functions and the app instance are
imported from their new locations and re-exported here.

New Module Structure:
- orchestrator_app.py: Shared FunctionApp instance
- timer_trigger.py: Timer trigger function
- workflow_orchestrator.py: Main orchestration function
- activities/: Activity functions organized by phase
  - validation.py: Environment validation
  - selection.py: Scenario selection
  - provisioning.py: SP and container deployment
  - monitoring.py: Agent status monitoring
  - cleanup.py: Cleanup verification and forced cleanup
  - reporting.py: Report generation

Design Pattern: Facade Pattern
- Maintains existing import paths
- Enables gradual migration
- All existing code continues to work
"""

# Conditional imports to avoid azure-functions-durable dependency in test environment
# When running tests, the durable functions decorators cause import errors if the
# azure-functions-durable package is not installed. This try-except allows tests
# to import other orchestrator modules without requiring the full Azure Functions stack.
try:
    # Shared FunctionApp instance
    from .orchestrator_app import app

    # Timer trigger function
    from .timer_trigger import haymaker_timer

    # Orchestration function
    from .workflow_orchestrator import orchestrate_haymaker_run

    # Activity functions
    from .activities.validation import validate_environment_activity
    from .activities.selection import select_scenarios_activity
    from .activities.provisioning import (
        create_service_principal_activity,
        deploy_container_app_activity,
    )
    from .activities.monitoring import check_agent_status_activity
    from .activities.cleanup import force_cleanup_activity, verify_cleanup_activity
    from .activities.reporting import generate_report_activity
except Exception:
    # In test environment without azure-functions-durable, create None placeholders
    # Note: We catch Exception (not just ImportError) because the durable functions
    # decorators raise Exception when the azure-functions-durable package is missing
    app = None
    haymaker_timer = None
    orchestrate_haymaker_run = None
    validate_environment_activity = None
    select_scenarios_activity = None
    create_service_principal_activity = None
    deploy_container_app_activity = None
    check_agent_status_activity = None
    force_cleanup_activity = None
    verify_cleanup_activity = None
    generate_report_activity = None

# Other orchestrator modules (unchanged)
from .container_manager import (
    ContainerAppError,
    ContainerManager,
    ImageSigningError,
    delete_container_app,
    deploy_container_app,
    get_container_status,
    verify_image_signature,
)
from .container_deployer import ContainerDeployer
from .container_lifecycle import ContainerLifecycle
from .container_monitor import ContainerMonitor
from .image_verifier import ImageVerifier
from .event_bus import (
    EventBusClient,
    parse_resource_events,
    publish_event,
    subscribe_to_agent_logs,
)
from .scenario_selector import (
    list_available_scenarios,
    parse_scenario_metadata,
    select_scenarios,
)
from .sp_manager import (
    ServicePrincipalDetails,
    ServicePrincipalError,
    create_service_principal,
    delete_service_principal,
    list_haymaker_service_principals,
    verify_sp_deleted,
)

__all__ = [
    # Orchestrator core
    "app",
    "haymaker_timer",
    "orchestrate_haymaker_run",
    # Activity functions
    "validate_environment_activity",
    "select_scenarios_activity",
    "create_service_principal_activity",
    "deploy_container_app_activity",
    "check_agent_status_activity",
    "verify_cleanup_activity",
    "force_cleanup_activity",
    "generate_report_activity",
    # Event bus
    "EventBusClient",
    "parse_resource_events",
    "publish_event",
    "subscribe_to_agent_logs",
    # Scenario selector
    "list_available_scenarios",
    "parse_scenario_metadata",
    "select_scenarios",
    # Service principal manager
    "ServicePrincipalDetails",
    "ServicePrincipalError",
    "create_service_principal",
    "delete_service_principal",
    "list_haymaker_service_principals",
    "verify_sp_deleted",
    # Container manager
    "ContainerManager",
    "ContainerAppError",
    "ImageSigningError",
    "deploy_container_app",
    "get_container_status",
    "delete_container_app",
    "verify_image_signature",
    "ContainerDeployer",
    "ContainerMonitor",
    "ContainerLifecycle",
    "ImageVerifier",
]
