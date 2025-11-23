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
    # Import all functions from monolithic function_app.py (Issue #28 fix)
    # function_app.py is in src/ directory, import it from parent
    import sys
    from pathlib import Path

    # Add src directory to path
    src_dir = Path(__file__).parent.parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from function_app import (
        app,
        check_agent_status_activity,
        create_service_principal_activity,
        deploy_container_app_activity,
        force_cleanup_activity,
        generate_report_activity,
        haymaker_timer,
        orchestrate_haymaker_run,
        select_scenarios_activity,
        validate_environment_activity,
        verify_cleanup_activity,
    )
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
from .container_deployer import ContainerDeployer
from .container_lifecycle import ContainerLifecycle, delete_container_app
from .container_manager import (
    ContainerAppError,
    ContainerManager,
    ImageSigningError,
    deploy_container_app,
)
from .container_monitor import ContainerMonitor, get_container_status
from .event_bus import (
    EventBusClient,
    parse_resource_events,
    publish_event,
    subscribe_to_agent_logs,
)
from .image_verifier import ImageVerifier, verify_image_signature
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
