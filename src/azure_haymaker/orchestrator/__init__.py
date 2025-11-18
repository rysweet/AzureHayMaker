"""Azure HayMaker orchestration service."""

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
# Conditional import of orchestrator to avoid azure-functions-durable dependency in tests
try:
    from .orchestrator import (
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
    # Orchestrator imports skipped (azure-functions-durable not available)
    app = None
    haymaker_timer = None
    orchestrate_haymaker_run = None
    validate_environment_activity = None
    select_scenarios_activity = None
    create_service_principal_activity = None
    deploy_container_app_activity = None
    check_agent_status_activity = None
    verify_cleanup_activity = None
    force_cleanup_activity = None
    generate_report_activity = None
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
    "EventBusClient",
    "parse_resource_events",
    "publish_event",
    "subscribe_to_agent_logs",
    "list_available_scenarios",
    "parse_scenario_metadata",
    "select_scenarios",
    "ServicePrincipalDetails",
    "ServicePrincipalError",
    "create_service_principal",
    "delete_service_principal",
    "list_haymaker_service_principals",
    "verify_sp_deleted",
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
