"""Azure Functions entry point for Azure HayMaker orchestrator.

This module contains thin wrapper functions that are decorated and discovered
by Azure Functions runtime, then delegate to the actual implementations in
the orchestrator module.

Architecture:
- Azure Functions V4 discovers functions by scanning function_app.py
- Decorators MUST be in this file for discovery to work
- Actual implementations live in azure_haymaker.orchestrator modules
- Wrapper functions delegate to implementations
"""

import logging
from typing import Any

import azure.functions as func
from azure.durable_functions import DurableOrchestrationClient

logger = logging.getLogger(__name__)

# Create FunctionApp instance
app = func.FunctionApp()

# =============================================================================
# TIMER TRIGGER - Scheduled orchestration (4x daily)
# =============================================================================


@app.timer_trigger(
    schedule="0 0 0,6,12,18 * * *",
    arg_name="timer_request",
    run_on_startup=False,
)
@app.durable_client_input(client_name="durable_client")
async def haymaker_timer(
    timer_request: Any,
    durable_client: DurableOrchestrationClient,
) -> dict[str, Any]:
    """Timer trigger - delegates to timer_trigger module."""
    from azure_haymaker.orchestrator.timer_trigger import haymaker_timer as impl

    return await impl(timer_request, durable_client)


# =============================================================================
# ORCHESTRATION FUNCTION - Main workflow
# =============================================================================


@app.orchestration_trigger(context_name="context")
async def orchestrate_haymaker_run(context: Any) -> dict[str, Any]:
    """Orchestration function - delegates to workflow_orchestrator module."""
    from azure_haymaker.orchestrator.workflow_orchestrator import (
        orchestrate_haymaker_run as impl,
    )

    return await impl(context)


# =============================================================================
# ACTIVITY FUNCTIONS - Individual workflow steps
# =============================================================================


@app.activity_trigger(input_name="config")
async def validate_environment_activity(config: dict[str, Any]) -> dict[str, Any]:
    """Validation activity - delegates to activities.validation module."""
    from azure_haymaker.orchestrator.activities.validation import (
        validate_environment_activity as impl,
    )

    return await impl(config)


@app.activity_trigger(input_name="config")
async def select_scenarios_activity(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Selection activity - delegates to activities.selection module."""
    from azure_haymaker.orchestrator.activities.selection import (
        select_scenarios_activity as impl,
    )

    return await impl(config)


@app.activity_trigger(input_name="config")
async def create_service_principal_activity(config: dict[str, Any]) -> dict[str, Any]:
    """Service principal activity - delegates to activities.provisioning module."""
    from azure_haymaker.orchestrator.activities.provisioning import (
        create_service_principal_activity as impl,
    )

    return await impl(config)


@app.activity_trigger(input_name="deployment_config")
async def deploy_container_app_activity(deployment_config: dict[str, Any]) -> dict[str, Any]:
    """Deployment activity - delegates to activities.provisioning module."""
    from azure_haymaker.orchestrator.activities.provisioning import (
        deploy_container_app_activity as impl,
    )

    return await impl(deployment_config)


@app.activity_trigger(input_name="agent_config")
async def check_agent_status_activity(agent_config: dict[str, Any]) -> dict[str, Any]:
    """Monitoring activity - delegates to activities.monitoring module."""
    from azure_haymaker.orchestrator.activities.monitoring import (
        check_agent_status_activity as impl,
    )

    return await impl(agent_config)


@app.activity_trigger(input_name="cleanup_config")
async def verify_cleanup_activity(cleanup_config: dict[str, Any]) -> dict[str, Any]:
    """Cleanup verification activity - delegates to activities.cleanup module."""
    from azure_haymaker.orchestrator.activities.cleanup import (
        verify_cleanup_activity as impl,
    )

    return await impl(cleanup_config)


@app.activity_trigger(input_name="cleanup_config")
async def force_cleanup_activity(cleanup_config: dict[str, Any]) -> dict[str, Any]:
    """Force cleanup activity - delegates to activities.cleanup module."""
    from azure_haymaker.orchestrator.activities.cleanup import (
        force_cleanup_activity as impl,
    )

    return await impl(cleanup_config)


@app.activity_trigger(input_name="report_config")
async def generate_report_activity(report_config: dict[str, Any]) -> dict[str, Any]:
    """Report generation activity - delegates to activities.reporting module."""
    from azure_haymaker.orchestrator.activities.reporting import (
        generate_report_activity as impl,
    )

    return await impl(report_config)


# Export app for Azure Functions runtime
__all__ = ["app"]

logger.info("function_app.py loaded with %d registered functions", len(app._function_builders))
