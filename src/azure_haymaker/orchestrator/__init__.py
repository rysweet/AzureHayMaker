"""Azure HayMaker orchestration service.

This module provides the public API for the orchestrator, including:
- Container management (deployment, monitoring, lifecycle)
- Event bus integration (Service Bus)
- Scenario selection
- Service principal management
- Azure Durable Functions orchestration (timer trigger, workflow, activities)

Architecture:
The orchestrator runs as Azure Durable Functions with:
- Timer trigger: 4x daily (00:00, 06:00, 12:00, 18:00 UTC)
- 7-phase workflow orchestration
- Activity functions for each phase

Module Structure:
- orchestrator_app.py: Shared FunctionApp instance
- timer_trigger.py: Timer trigger for scheduled execution
- workflow_orchestrator.py: Main durable orchestration function
- activities/: Activity functions organized by phase
  - validation.py: Environment validation
  - selection.py: Scenario selection
  - provisioning.py: SP creation and container deployment
  - monitoring.py: Agent status monitoring
  - cleanup.py: Cleanup verification and forced cleanup
  - reporting.py: Report generation
- container_manager.py: Container App deployment and management
- container_deployer.py: Container deployment logic
- container_monitor.py: Container status monitoring
- container_lifecycle.py: Container cleanup/deletion
- event_bus.py: Azure Service Bus integration
- scenario_selector.py: Scenario selection from docs/scenarios/
- sp_manager.py: Service principal lifecycle management
- image_verifier.py: Container image signature verification
- meta_orchestrator.py: Multi-tenant parallel execution (Phase 3)
"""

from . import activities  # noqa: F401
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
from .meta_orchestrator import (
    FailureMode,
    FanOutController,
    MetaExecutionRequest,
    MetaExecutionResult,
    MetaOrchestrator,
    TenantExecutionState,
    TenantExecutionStatus,
)
from .orchestrator_app import app
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
from .timer_trigger import haymaker_timer
from .workflow_orchestrator import orchestrate_haymaker_run

__all__ = [
    # Azure Functions app instance
    "app",
    # Timer trigger
    "haymaker_timer",
    # Workflow orchestration
    "orchestrate_haymaker_run",
    # Meta-orchestrator (Phase 3 multi-tenant)
    "MetaOrchestrator",
    "MetaExecutionRequest",
    "MetaExecutionResult",
    "FanOutController",
    "FailureMode",
    "TenantExecutionState",
    "TenantExecutionStatus",
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
    # Meta-orchestrator (Phase 3)
    "FailureMode",
    "FanOutController",
    "MetaExecutionRequest",
    "MetaExecutionResult",
    "MetaOrchestrator",
    "TenantExecutionState",
    "TenantExecutionStatus",
]
