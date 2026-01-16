"""Azure HayMaker orchestration service.

This module provides the public API for the orchestrator, including:
- Container management (deployment, monitoring, lifecycle)
- Event bus integration (Service Bus)
- Scenario selection
- Service principal management

Architecture:
The orchestrator runs as a FastAPI application on Azure Container Apps (128GB RAM).
Scheduling is handled via KEDA CRON triggers (4x daily).
See orchestrator_server.py for the main FastAPI application.

Module Structure:
- container_manager.py: Container App deployment and management
- container_deployer.py: Container deployment logic
- container_monitor.py: Container status monitoring
- container_lifecycle.py: Container cleanup/deletion
- event_bus.py: Azure Service Bus integration
- scenario_selector.py: Scenario selection from docs/scenarios/
- sp_manager.py: Service principal lifecycle management
- image_verifier.py: Container image signature verification
"""

# Container management modules
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
