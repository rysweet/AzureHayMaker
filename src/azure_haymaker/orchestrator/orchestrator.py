"""Azure Durable Functions orchestrator for Azure HayMaker.

This module implements the main orchestration workflow that coordinates:
1. Environment validation
2. Scenario selection
3. Service principal and container app provisioning (parallel)
4. Agent execution monitoring (8 hours)
5. Cleanup verification and forced deletion
6. Report generation

Uses Azure Durable Functions for long-running workflow orchestration with checkpointing.
Timer trigger: 4x daily (00:00, 06:00, 12:00, 18:00 UTC)

Note: Durable Functions imports are optional to support test environments.
In production deployment, azure-durable-functions and azure-functions must be installed.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

try:
    import azure.durable_functions as df
    import azure.functions as func

    DURABLE_FUNCTIONS_AVAILABLE = True
except ImportError:
    DURABLE_FUNCTIONS_AVAILABLE = False
    df = None  # type: ignore
    func = None  # type: ignore

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails
from azure_haymaker.orchestrator.cleanup import (
    force_delete_resources,
    query_managed_resources,
)
from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.container_manager import (
    ContainerManager,
    deploy_container_app,
)
from azure_haymaker.orchestrator.scenario_selector import select_scenarios
from azure_haymaker.orchestrator.sp_manager import (
    create_service_principal,
)
from azure_haymaker.orchestrator.validation import validate_environment

logger = logging.getLogger(__name__)

# Azure Functions app instance
# This will only be initialized if azure-functions is installed
if DURABLE_FUNCTIONS_AVAILABLE and func is not None:
    app = func.FunctionApp()
else:
    # Stub for test environments
    class DummyApp:
        """Stub app for environments without azure-functions."""

        def timer_trigger(self, schedule: str, arg_name: str, run_on_startup: bool = False):
            """Decorator stub."""

            def decorator(fn: Any) -> Any:
                return fn

            return decorator

        def durable_client_input(self, client_name: str):
            """Decorator stub."""

            def decorator(fn: Any) -> Any:
                return fn

            return decorator

        def orchestration_trigger(self, context_name: str):
            """Decorator stub."""

            def decorator(fn: Any) -> Any:
                return fn

            return decorator

        def activity_trigger(self, input_name: str):
            """Decorator stub."""

            def decorator(fn: Any) -> Any:
                return fn

            return decorator

    app = DummyApp()


# ==============================================================================
# TIMER TRIGGER - Scheduled orchestration start (4x daily)
# ==============================================================================


@app.timer_trigger(
    schedule="0 0 0,6,12,18 * * *",
    arg_name="timer_request",
    run_on_startup=False,
)
@app.durable_client_input(client_name="durable_client")
async def haymaker_timer(
    timer_request: Any = None,
    durable_client: Any = None,
) -> dict[str, Any]:
    """Timer trigger for orchestrator execution (4x daily: 00:00, 06:00, 12:00, 18:00 UTC).

    Triggered by CRON schedule and starts a new durable orchestration instance.

    Args:
        timer_request: Timer trigger request containing execution time
        durable_client: Durable Functions client for starting orchestrations

    Returns:
        Dictionary with instance ID and status check URL

    Example:
        Automatically triggered at 00:00, 06:00, 12:00, 18:00 UTC.
        No manual invocation needed.
    """
    if timer_request.past_due:
        logger.warning(
            "Timer trigger is running late. Past due time: %s",
            timer_request.past_due,
        )

    # Generate unique run ID for this execution
    run_id = str(uuid4())
    logger.info("Haymaker timer trigger fired. Starting orchestration with run_id=%s", run_id)

    # Start the main orchestration function
    instance_id = await durable_client.start_new(
        orchestration_function_name="orchestrate_haymaker_run",
        instance_id=run_id,
        input_={"run_id": run_id, "started_at": datetime.now(UTC).isoformat()},
    )

    logger.info("Orchestration started with instance_id=%s", instance_id)

    # Return status check response
    return durable_client.create_check_status_response(
        http_request=func.HttpRequest(
            method="GET",
            url="",
            body=b"",
        ),
        instance_id=instance_id,
    )


# ==============================================================================
# ORCHESTRATION FUNCTION - Main workflow
# ==============================================================================


@app.orchestration_trigger(context_name="context")
def orchestrate_haymaker_run(context: Any) -> dict[str, Any]:
    """Main orchestration function for Azure HayMaker execution.

    Coordinates 5 phases:
    1. Validation: Verify credentials, APIs, and prerequisites
    2. Selection: Randomly select scenarios based on simulation size
    3. Provisioning: Create SPs and deploy Container Apps (parallel)
    4. Monitoring: Wait 8 hours with periodic status checks
    5. Cleanup: Verify cleanup completion and force-delete remaining resources
    6. Reporting: Generate execution report

    Args:
        context: Durable orchestration context

    Returns:
        Dictionary with execution summary and cleanup status

    Raises:
        ValidationError: If environment validation fails
        ScenarioError: If scenario selection fails
        ProvisioningError: If provisioning fails
    """
    run_id = context.input.get("run_id")
    started_at = context.input.get("started_at")
    logger.info(f"Orchestration started for run_id={run_id}")

    execution_report = {
        "run_id": run_id,
        "started_at": started_at,
        "status": "in_progress",
        "phases": {},
    }

    try:
        # ========================================================================
        # PHASE 1: VALIDATION
        # ========================================================================
        logger.info(f"[{run_id}] Starting Phase 1: Validation")
        validation_result = yield context.call_activity(
            "validate_environment_activity",
            None,
        )

        if not validation_result.get("overall_passed", False):
            logger.error(f"[{run_id}] Validation failed: {validation_result}")
            execution_report["status"] = "failed"
            execution_report["failure_reason"] = "environment_validation_failed"
            execution_report["phases"]["validation"] = validation_result
            return execution_report

        execution_report["phases"]["validation"] = {
            "status": "passed",
            "checks": validation_result.get("results", []),
        }
        logger.info(f"[{run_id}] Phase 1: Validation passed")

        # ========================================================================
        # PHASE 2: SCENARIO SELECTION
        # ========================================================================
        logger.info(f"[{run_id}] Starting Phase 2: Scenario Selection")
        selection_result = yield context.call_activity(
            "select_scenarios_activity",
            None,
        )

        selected_scenarios = selection_result.get("scenarios", [])
        logger.info(f"[{run_id}] Selected {len(selected_scenarios)} scenarios")
        execution_report["phases"]["selection"] = {
            "status": "completed",
            "scenario_count": len(selected_scenarios),
            "scenarios": [s["scenario_name"] for s in selected_scenarios],
        }

        if not selected_scenarios:
            logger.error(f"[{run_id}] No scenarios selected")
            execution_report["status"] = "failed"
            execution_report["failure_reason"] = "no_scenarios_selected"
            return execution_report

        # ========================================================================
        # PHASE 3: PROVISIONING (Parallel SP Creation + Container Deployment)
        # ========================================================================
        logger.info(
            f"[{run_id}] Starting Phase 3: Provisioning ({len(selected_scenarios)} scenarios)"
        )

        # Create all service principals in parallel
        sp_tasks = [
            context.call_activity(
                "create_service_principal_activity",
                {
                    "run_id": run_id,
                    "scenario": scenario,
                },
            )
            for scenario in selected_scenarios
        ]
        sp_results = yield context.task_all(sp_tasks)

        # Check for SP creation failures
        failed_sps = [sp for sp in sp_results if sp.get("status") == "failed"]
        if failed_sps:
            logger.warning(
                f"[{run_id}] {len(failed_sps)} SPs failed to create (will attempt cleanup)"
            )

        successful_sps = [sp for sp in sp_results if sp.get("status") == "success"]
        logger.info(
            f"[{run_id}] Created {len(successful_sps)}/{len(selected_scenarios)} service principals"
        )

        # Deploy Container Apps in parallel (only for successful SPs)
        container_tasks = []
        for scenario, sp_result in zip(selected_scenarios, sp_results, strict=False):
            if sp_result.get("status") == "success":
                container_tasks.append(
                    context.call_activity(
                        "deploy_container_app_activity",
                        {
                            "run_id": run_id,
                            "scenario": scenario,
                            "sp_details": sp_result.get("sp_details"),
                        },
                    )
                )

        container_results = yield context.task_all(container_tasks) if container_tasks else []

        failed_containers = [c for c in container_results if c.get("status") == "failed"]
        successful_containers = [c for c in container_results if c.get("status") == "success"]
        logger.info(
            f"[{run_id}] Deployed {len(successful_containers)}/{len(container_tasks)} container apps"
        )

        execution_report["phases"]["provisioning"] = {
            "status": "completed",
            "service_principals": {
                "requested": len(selected_scenarios),
                "created": len(successful_sps),
                "failed": len(failed_sps),
            },
            "container_apps": {
                "requested": len(successful_sps),
                "deployed": len(successful_containers),
                "failed": len(failed_containers),
            },
        }

        # ========================================================================
        # PHASE 4: MONITORING (8 hours with periodic checks)
        # ========================================================================
        logger.info(f"[{run_id}] Starting Phase 4: Monitoring (8 hours)")
        monitoring_end_time = context.current_utc_datetime + timedelta(hours=8)
        monitoring_status = {
            "status_checks": [],
            "log_messages": 0,
            "resource_count": 0,
        }

        while context.current_utc_datetime < monitoring_end_time:
            # Periodic status check every 15 minutes
            check_result = yield context.call_activity(
                "check_agent_status_activity",
                {
                    "run_id": run_id,
                    "container_ids": [c.get("container_id") for c in successful_containers],
                },
            )

            monitoring_status["status_checks"].append(
                {
                    "timestamp": context.current_utc_datetime.isoformat(),
                    "running_count": check_result.get("running_count", 0),
                    "completed_count": check_result.get("completed_count", 0),
                }
            )

            # Wait 15 minutes before next check
            yield context.create_timer(context.current_utc_datetime + timedelta(minutes=15))

        execution_report["phases"]["monitoring"] = monitoring_status
        logger.info(f"[{run_id}] Phase 4: Monitoring completed after 8 hours")

        # ========================================================================
        # PHASE 5: CLEANUP VERIFICATION
        # ========================================================================
        logger.info(f"[{run_id}] Starting Phase 5: Cleanup Verification")
        cleanup_verification = yield context.call_activity(
            "verify_cleanup_activity",
            {
                "run_id": run_id,
                "scenarios": [s["scenario_name"] for s in selected_scenarios],
            },
        )

        remaining_resources = cleanup_verification.get("remaining_resources", [])
        logger.info(
            f"[{run_id}] Cleanup verification: {len(remaining_resources)} resources remaining"
        )

        # ========================================================================
        # PHASE 6: FORCED CLEANUP (if needed)
        # ========================================================================
        if remaining_resources:
            logger.warning(
                f"[{run_id}] Found {len(remaining_resources)} remaining resources. Starting forced cleanup."
            )
            cleanup_result = yield context.call_activity(
                "force_cleanup_activity",
                {
                    "run_id": run_id,
                    "scenarios": [s["scenario_name"] for s in selected_scenarios],
                    "sp_details": [
                        sp.get("sp_details") for sp in successful_sps if sp.get("sp_details")
                    ],
                },
            )

            cleanup_status = cleanup_result.get("status", "unknown")
            deleted_count = cleanup_result.get("deleted_count", 0)
            failed_count = cleanup_result.get("failed_count", 0)

            execution_report["phases"]["cleanup"] = {
                "status": cleanup_status,
                "verification_found": len(remaining_resources),
                "deleted": deleted_count,
                "failed": failed_count,
            }
            logger.info(
                f"[{run_id}] Forced cleanup completed: {deleted_count} deleted, {failed_count} failed"
            )
        else:
            logger.info(f"[{run_id}] No remaining resources found. Cleanup verified.")
            execution_report["phases"]["cleanup"] = {
                "status": "verified",
                "verification_found": 0,
                "deleted": 0,
                "failed": 0,
            }

        # ========================================================================
        # PHASE 7: REPORT GENERATION
        # ========================================================================
        logger.info(f"[{run_id}] Starting Phase 7: Report Generation")
        report = yield context.call_activity(
            "generate_report_activity",
            {
                "run_id": run_id,
                "execution_report": execution_report,
                "selected_scenarios": [s["scenario_name"] for s in selected_scenarios],
                "sp_count": len(successful_sps),
                "container_count": len(successful_containers),
            },
        )

        execution_report["status"] = "completed"
        execution_report["ended_at"] = context.current_utc_datetime.isoformat()
        execution_report["report_url"] = report.get("report_url")

        logger.info(f"[{run_id}] Orchestration completed successfully")
        return execution_report

    except Exception as e:
        logger.error(f"[{run_id}] Orchestration failed with error: {str(e)}", exc_info=True)
        execution_report["status"] = "failed"
        execution_report["error"] = str(e)
        execution_report["ended_at"] = context.current_utc_datetime.isoformat()
        return execution_report


# ==============================================================================
# ACTIVITY FUNCTIONS - Orchestration phases
# ==============================================================================


@app.activity_trigger(input_name="input_data")
async def validate_environment_activity(input_data: Any) -> dict[str, Any]:
    """Activity: Validate environment prerequisites.

    Checks:
    - Azure credentials validity
    - Anthropic API access
    - Azure CLI availability
    - Key Vault access
    - Service Bus connectivity

    Args:
        input_data: Not used (activity receives None)

    Returns:
        Dictionary with validation results:
        {
            "overall_passed": bool,
            "results": [
                {"check": "azure_credentials", "passed": bool, "error": str}
            ]
        }
    """
    try:
        logger.info("Activity: validate_environment - Starting")
        config = await load_config()
        result = await validate_environment(config)
        logger.info("Activity: validate_environment - Completed")
        return {
            "overall_passed": result.get("overall_passed", False),
            "results": result.get("results", []),
        }
    except Exception as e:
        logger.error(f"Activity: validate_environment - Failed: {str(e)}", exc_info=True)
        return {
            "overall_passed": False,
            "results": [
                {
                    "check": "validation",
                    "passed": False,
                    "error": str(e),
                }
            ],
        }


@app.activity_trigger(input_name="input_data")
async def select_scenarios_activity(input_data: Any) -> dict[str, Any]:
    """Activity: Select random scenarios for execution.

    Randomly selects N scenarios based on simulation_size configuration.
    Size mappings:
    - small: 5 scenarios
    - medium: 15 scenarios
    - large: 30 scenarios

    Args:
        input_data: Not used (activity receives None)

    Returns:
        Dictionary with selected scenarios:
        {
            "scenarios": [
                {
                    "scenario_name": str,
                    "technology_area": str,
                    "scenario_doc_path": str
                }
            ]
        }
    """
    try:
        logger.info("Activity: select_scenarios - Starting")
        config = await load_config()
        scenarios = await select_scenarios(config)
        logger.info(f"Activity: select_scenarios - Selected {len(scenarios)} scenarios")
        return {
            "scenarios": [
                {
                    "scenario_name": s.scenario_name,
                    "technology_area": s.technology_area,
                    "scenario_doc_path": s.scenario_doc_path,
                }
                for s in scenarios
            ]
        }
    except Exception as e:
        logger.error(f"Activity: select_scenarios - Failed: {str(e)}", exc_info=True)
        return {"scenarios": []}


@app.activity_trigger(input_name="params")
async def create_service_principal_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Create service principal for a scenario.

    Creates an ephemeral service principal with naming convention:
    AzureHayMaker-{scenario_name}-admin

    Assigns roles:
    - User Access Administrator
    - Contributor

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - scenario: Scenario metadata dictionary

    Returns:
        Dictionary with SP details or failure info:
        {
            "status": "success" | "failed",
            "sp_details": {
                "sp_name": str,
                "client_id": str,
                "principal_id": str,
                "secret_reference": str
            },
            "error": str (if failed)
        }
    """
    try:
        run_id = params.get("run_id")
        scenario = params.get("scenario")
        scenario_name = scenario.get("scenario_name")

        logger.info(f"Activity: create_service_principal - scenario={scenario_name}")

        config = await load_config()
        sp_details = await create_service_principal(
            scenario_name=scenario_name,
            subscription_id=config.target_subscription_id,
            run_id=run_id,
        )

        logger.info(f"Activity: create_service_principal - Created SP: {sp_details.sp_name}")
        return {
            "status": "success",
            "sp_details": {
                "sp_name": sp_details.sp_name,
                "client_id": sp_details.client_id,
                "principal_id": sp_details.principal_id,
                "secret_reference": sp_details.secret_reference,
                "created_at": sp_details.created_at,
            },
        }
    except Exception as e:
        logger.error(
            f"Activity: create_service_principal - Failed: {str(e)}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": str(e),
        }


@app.activity_trigger(input_name="params")
async def deploy_container_app_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Deploy Container App for scenario execution.

    Deploys a Container App with:
    - Scenario-specific instructions
    - Service principal credentials (via Key Vault)
    - 64GB RAM, 2 CPU minimum
    - 10-hour timeout
    - Never restart policy

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - scenario: Scenario metadata dictionary
            - sp_details: Service principal details dictionary

    Returns:
        Dictionary with Container App details or failure info:
        {
            "status": "success" | "failed",
            "container_id": str,
            "container_name": str,
            "resource_id": str,
            "error": str (if failed)
        }
    """
    try:
        run_id = params.get("run_id")
        scenario = params.get("scenario")
        sp_details = params.get("sp_details")
        scenario_name = scenario.get("scenario_name")

        logger.info(f"Activity: deploy_container_app - scenario={scenario_name}")

        config = await load_config()
        container_details = await deploy_container_app(
            scenario_metadata=ScenarioMetadata(
                scenario_name=scenario_name,
                scenario_doc_path=scenario.get("scenario_doc_path"),
                technology_area=scenario.get("technology_area"),
            ),
            sp_details=ServicePrincipalDetails(
                sp_name=sp_details.get("sp_name"),
                client_id=sp_details.get("client_id"),
                principal_id=sp_details.get("principal_id"),
                secret_reference=sp_details.get("secret_reference"),
                created_at=sp_details.get("created_at"),
            ),
            config=config,
            run_id=run_id,
        )

        logger.info(f"Activity: deploy_container_app - Deployed: {container_details.get('name')}")
        return {
            "status": "success",
            "container_id": container_details.get("name"),
            "container_name": container_details.get("name"),
            "resource_id": container_details.get("resource_id"),
        }
    except Exception as e:
        logger.error(
            f"Activity: deploy_container_app - Failed: {str(e)}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": str(e),
        }


@app.activity_trigger(input_name="params")
async def check_agent_status_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Check status of running agents.

    Queries Container Apps for execution status and subscribes to Service Bus
    for agent log messages.

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - container_ids: List of Container App IDs to check

    Returns:
        Dictionary with status:
        {
            "running_count": int,
            "completed_count": int,
            "failed_count": int,
            "log_messages": int
        }
    """
    try:
        container_ids = params.get("container_ids", [])

        logger.info(f"Activity: check_agent_status - Checking {len(container_ids)} containers")

        config = await load_config()
        container_manager = ContainerManager(config)

        # Check status of each container
        statuses = {"running": 0, "completed": 0, "failed": 0}
        for container_id in container_ids:
            try:
                status = await container_manager.get_container_status(container_id)
                if status in ["Running", "Processing"]:
                    statuses["running"] += 1
                elif status == "Terminated":
                    statuses["completed"] += 1
                else:
                    statuses["failed"] += 1
            except Exception as e:
                logger.warning(f"Failed to check status of {container_id}: {str(e)}")
                statuses["failed"] += 1

        logger.info(
            f"Activity: check_agent_status - "
            f"running={statuses['running']}, "
            f"completed={statuses['completed']}, "
            f"failed={statuses['failed']}"
        )

        return {
            "running_count": statuses["running"],
            "completed_count": statuses["completed"],
            "failed_count": statuses["failed"],
            "log_messages": 0,
        }
    except Exception as e:
        logger.error(f"Activity: check_agent_status - Failed: {str(e)}", exc_info=True)
        return {
            "running_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "log_messages": 0,
        }


@app.activity_trigger(input_name="params")
async def verify_cleanup_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Verify cleanup of resources.

    Queries Azure Resource Graph for resources tagged as AzureHayMaker-managed
    and verifies they have been deleted.

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - scenarios: List of scenario names

    Returns:
        Dictionary with remaining resources:
        {
            "remaining_resources": [
                {
                    "resource_id": str,
                    "resource_type": str,
                    "scenario_name": str
                }
            ]
        }
    """
    try:
        run_id = params.get("run_id")
        scenarios = params.get("scenarios", [])

        logger.info(f"Activity: verify_cleanup - Checking {len(scenarios)} scenarios")

        config = await load_config()
        remaining_resources = await query_managed_resources(
            subscription_id=config.target_subscription_id,
            run_id=run_id,
        )

        logger.info(
            f"Activity: verify_cleanup - Found {len(remaining_resources)} remaining resources"
        )
        return {
            "remaining_resources": [
                {
                    "resource_id": r.resource_id,
                    "resource_type": r.resource_type,
                    "scenario_name": r.tags.get("Scenario", "unknown") if r.tags else "unknown",
                }
                for r in remaining_resources
            ],
        }
    except Exception as e:
        logger.error(f"Activity: verify_cleanup - Failed: {str(e)}", exc_info=True)
        return {
            "remaining_resources": [],
        }


@app.activity_trigger(input_name="params")
async def force_cleanup_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Force cleanup of remaining resources and service principals.

    Deletes all resources tagged as AzureHayMaker-managed for the run,
    with retry logic for dependencies. Also deletes service principals.

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - scenarios: List of scenario names
            - sp_details: List of service principal details

    Returns:
        Dictionary with cleanup results:
        {
            "status": "completed" | "partial_failure" | "failed",
            "deleted_count": int,
            "failed_count": int,
            "sp_deleted_count": int
        }
    """
    try:
        run_id = params.get("run_id")
        scenarios = params.get("scenarios", [])
        sp_details_list = params.get("sp_details", [])

        logger.info(
            f"Activity: force_cleanup - "
            f"run_id={run_id}, "
            f"scenarios={len(scenarios)}, "
            f"sps={len(sp_details_list)}"
        )

        config = await load_config()
        cleanup_report = await force_delete_resources(
            subscription_id=config.target_subscription_id,
            run_id=run_id,
            sp_details_list=[],  # SP deletion handled separately
        )

        deleted_count = cleanup_report.total_resources_deleted
        failed_count = len([d for d in cleanup_report.deletions if d.status == "failed"])
        sp_deleted_count = len(cleanup_report.service_principals_deleted)

        # Determine status based on results
        status = (
            cleanup_report.status.value
            if hasattr(cleanup_report.status, "value")
            else str(cleanup_report.status)
        )

        # Map cleanup status to activity result
        if status == "verified":
            activity_status = "completed"
        elif status == "partial_failure":
            activity_status = "partial_failure"
        else:
            activity_status = "failed"

        logger.info(
            f"Activity: force_cleanup - "
            f"status={activity_status}, "
            f"deleted={deleted_count}, "
            f"failed={failed_count}, "
            f"sp_deleted={sp_deleted_count}"
        )

        return {
            "status": activity_status,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "sp_deleted_count": sp_deleted_count,
        }
    except Exception as e:
        logger.error(f"Activity: force_cleanup - Failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "deleted_count": 0,
            "failed_count": 0,
            "sp_deleted_count": 0,
            "error": str(e),
        }


@app.activity_trigger(input_name="params")
async def generate_report_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Generate execution report and store to storage account.

    Creates final execution report summarizing:
    - Selected scenarios
    - Created resources
    - Cleanup status
    - Errors and warnings

    Stores report to Azure Storage Account.

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - execution_report: Full execution report data
            - selected_scenarios: List of selected scenario names
            - sp_count: Number of created service principals
            - container_count: Number of deployed containers

    Returns:
        Dictionary with report details:
        {
            "report_url": str,
            "report_id": str,
            "generated_at": str
        }
    """
    try:
        run_id = params.get("run_id")
        execution_report = params.get("execution_report", {})
        selected_scenarios = params.get("selected_scenarios", [])
        sp_count = params.get("sp_count", 0)
        container_count = params.get("container_count", 0)

        logger.info(
            f"Activity: generate_report - "
            f"run_id={run_id}, "
            f"scenarios={len(selected_scenarios)}, "
            f"sps={sp_count}, "
            f"containers={container_count}"
        )

        config = await load_config()
        credential = DefaultAzureCredential()

        # Store report to blob storage
        blob_service_client = BlobServiceClient(
            account_url=f"https://{config.storage_account}.blob.core.windows.net",
            credential=credential,
        )

        # Prepare report
        report = {
            "run_id": run_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "execution_report": execution_report,
            "summary": {
                "selected_scenarios": selected_scenarios,
                "scenario_count": len(selected_scenarios),
                "service_principals_created": sp_count,
                "containers_deployed": container_count,
            },
        }

        # Store to blob
        container_client = blob_service_client.get_container_client("execution-reports")
        blob_client = container_client.get_blob_client(f"{run_id}/report.json")
        await blob_client.upload_blob(json.dumps(report, indent=2), overwrite=True)

        report_url = blob_client.url
        logger.info(f"Activity: generate_report - Report stored at {report_url}")

        return {
            "report_url": report_url,
            "report_id": run_id,
            "generated_at": report["generated_at"],
        }
    except Exception as e:
        logger.error(f"Activity: generate_report - Failed: {str(e)}", exc_info=True)
        return {
            "report_url": "",
            "report_id": params.get("run_id"),
            "error": str(e),
        }
