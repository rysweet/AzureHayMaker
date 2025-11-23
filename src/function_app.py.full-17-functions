"""Azure Functions entry point for Azure HayMaker orchestrator.

MONOLITHIC PATTERN (Issue #28 Fix):
All function decorators must be in this file for Azure Functions V4 discovery.
The runtime discovers functions by introspecting this module and finding
all @app.* decorated functions.

This approach ensures 100% reliable function discovery by keeping all
decorators in the entry point file where Azure Functions expects them.

Architecture:
- Single FunctionApp instance created in this file
- All 17 functions decorated here (not in separate modules)
  * 1 Timer Trigger: haymaker_timer
  * 1 Orchestrator: orchestrate_haymaker_run
  * 8 Activities: validation, selection, SP creation, container deployment,
                  status checks, cleanup verification, force cleanup, reporting
  * 7 HTTP APIs: execute, get_execution_status, list_agents, get_agent_logs,
                 get_metrics, list_resources, get_resource
- Implementation logic delegates to helper modules for maintainability
- Guaranteed function discovery per Azure Functions documentation
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

# =============================================================================
# FUNCTION APP INSTANCE
# =============================================================================
# Create the single FunctionApp instance that all decorators reference.
# Azure Functions discovers this instance via module introspection.
# =============================================================================

app = func.FunctionApp()

logger = logging.getLogger(__name__)

# =============================================================================
# TIMER TRIGGER - Scheduled orchestration start (4x daily)
# =============================================================================


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


# =============================================================================
# ORCHESTRATION FUNCTION - Main workflow
# =============================================================================


@app.orchestration_trigger(context_name="context")
def orchestrate_haymaker_run(context: Any) -> Any:
    """Main orchestration function for Azure HayMaker execution.

    Coordinates 7 phases:
    1. Validation: Verify credentials, APIs, and prerequisites
    2. Selection: Randomly select scenarios based on simulation size
    3. Provisioning: Create SPs and deploy Container Apps (parallel)
    4. Monitoring: Wait 8 hours with periodic status checks
    5. Cleanup: Verify cleanup completion
    6. Forced Cleanup: Force-delete remaining resources (if needed)
    7. Reporting: Generate execution report

    Args:
        context: Durable orchestration context

    Returns:
        Dictionary with execution summary and cleanup status
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

        overall_passed: bool = validation_result["overall_passed"]
        if not overall_passed:
            logger.error(f"[{run_id}] Validation failed: {validation_result}")
            execution_report["status"] = "failed"
            execution_report["failure_reason"] = "environment_validation_failed"
            if "phases" not in execution_report or not isinstance(execution_report["phases"], dict):
                execution_report["phases"] = {}
            phases: dict[str, Any] = execution_report["phases"]  # type: ignore[assignment]
            phases["validation"] = validation_result
            return execution_report

        if "phases" not in execution_report or not isinstance(execution_report["phases"], dict):
            execution_report["phases"] = {}
        phases = execution_report["phases"]  # type: ignore[assignment]
        phases["validation"] = {
            "status": "passed",
            "checks": validation_result["results"],
        }
        execution_report["phases"] = phases
        logger.info(f"[{run_id}] Phase 1: Validation passed")

        # ========================================================================
        # PHASE 2: SCENARIO SELECTION
        # ========================================================================
        logger.info(f"[{run_id}] Starting Phase 2: Scenario Selection")
        selection_result = yield context.call_activity(
            "select_scenarios_activity",
            None,
        )

        selected_scenarios = selection_result["scenarios"]
        logger.info(f"[{run_id}] Selected {len(selected_scenarios)} scenarios")
        if "phases" not in execution_report:
            execution_report["phases"] = {}
        phases = execution_report["phases"]  # type: ignore[assignment]
        phases["selection"] = {
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
        failed_sps = [sp for sp in sp_results if sp["status"] == "failed"]
        if failed_sps:
            logger.warning(
                f"[{run_id}] {len(failed_sps)} SPs failed to create (will attempt cleanup)"
            )

        successful_sps = [sp for sp in sp_results if sp["status"] == "success"]
        logger.info(
            f"[{run_id}] Created {len(successful_sps)}/{len(selected_scenarios)} service principals"
        )

        # Deploy Container Apps in parallel (only for successful SPs)
        container_tasks = []
        for scenario, sp_result in zip(selected_scenarios, sp_results, strict=False):
            if sp_result["status"] == "success":
                container_tasks.append(
                    context.call_activity(
                        "deploy_container_app_activity",
                        {
                            "run_id": run_id,
                            "scenario": scenario,
                            "sp_details": sp_result["sp_details"],
                        },
                    )
                )

        container_results = yield context.task_all(container_tasks) if container_tasks else []

        failed_containers = [c for c in container_results if c["status"] == "failed"]
        successful_containers = [c for c in container_results if c["status"] == "success"]
        logger.info(
            f"[{run_id}] Deployed {len(successful_containers)}/{len(container_tasks)} container apps"
        )

        if "phases" not in execution_report:
            execution_report["phases"] = {}
        phases = execution_report["phases"]  # type: ignore[assignment]
        phases["provisioning"] = {
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
                    "container_ids": [c["container_id"] for c in successful_containers],
                },
            )

            status_checks: list[dict[str, Any]] = monitoring_status["status_checks"]  # type: ignore[assignment]
            status_checks.append(
                {
                    "timestamp": context.current_utc_datetime.isoformat(),
                    "running_count": check_result["running_count"],
                    "completed_count": check_result["completed_count"],
                }
            )

            # Wait 15 minutes before next check
            yield context.create_timer(context.current_utc_datetime + timedelta(minutes=15))

        if "phases" not in execution_report:
            execution_report["phases"] = {}
        phases = execution_report["phases"]  # type: ignore[assignment]
        phases["monitoring"] = monitoring_status
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

        remaining_resources = cleanup_verification["remaining_resources"]
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
                    "sp_details": [sp["sp_details"] for sp in successful_sps if "sp_details" in sp],
                },
            )

            cleanup_status = cleanup_result["status"]
            deleted_count = cleanup_result["deleted_count"]
            failed_count = cleanup_result["failed_count"]

            if "phases" not in execution_report:
                execution_report["phases"] = {}
            phases = execution_report["phases"]  # type: ignore[assignment]
            phases["cleanup"] = {
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
            if "phases" not in execution_report:
                execution_report["phases"] = {}
            phases = execution_report["phases"]  # type: ignore[assignment]
            phases["cleanup"] = {
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
        execution_report["report_url"] = report["report_url"]

        logger.info(f"[{run_id}] Orchestration completed successfully")
        return execution_report

    except Exception as e:
        logger.error(f"[{run_id}] Orchestration failed with error: {str(e)}", exc_info=True)
        execution_report["status"] = "failed"
        execution_report["error"] = str(e)
        execution_report["ended_at"] = context.current_utc_datetime.isoformat()
        return execution_report


# =============================================================================
# ACTIVITY FUNCTIONS (8 total)
# =============================================================================


@app.activity_trigger(input_name="input_data")
async def validate_environment_activity(input_data: Any) -> dict[str, Any]:
    """Activity: Validate environment prerequisites.

    Checks Azure credentials, Anthropic API, Azure CLI, Key Vault, Service Bus.
    """
    from azure_haymaker.orchestrator.config import load_config
    from azure_haymaker.orchestrator.validation import validate_environment

    try:
        logger.info("Activity: validate_environment - Starting")
        config = await load_config()
        result = await validate_environment(config)
        logger.info("Activity: validate_environment - Completed")
        return {
            "overall_passed": result.overall_passed,
            "results": [r.model_dump() for r in result.results],
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
    """Activity: Select random scenarios for execution based on simulation size."""
    from azure_haymaker.orchestrator.config import load_config
    from azure_haymaker.orchestrator.scenario_selector import select_scenarios

    try:
        logger.info("Activity: select_scenarios - Starting")
        config = await load_config()
        sim_size = config.simulation_size
        scenarios = select_scenarios(sim_size)
        logger.info(f"Activity: select_scenarios - Selected {len(scenarios)} scenarios")
        return {
            "scenarios": [
                {
                    "scenario_name": s.scenario_name,
                    "technology_area": s.technology_area,
                    "scenario_doc_path": s.scenario_doc_path,
                    "agent_path": s.agent_path,
                }
                for s in scenarios
            ]
        }
    except Exception as e:
        logger.error(f"Activity: select_scenarios - Failed: {str(e)}", exc_info=True)
        return {"scenarios": []}


@app.activity_trigger(input_name="params")
async def create_service_principal_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Create service principal for a scenario."""
    from azure_haymaker.orchestrator.config import load_config
    from azure_haymaker.orchestrator.sp_manager import create_service_principal

    try:
        scenario = params.get("scenario", {})
        if not isinstance(scenario, dict):
            scenario = {}
        scenario_name = scenario.get("scenario_name")

        logger.info(f"Activity: create_service_principal - scenario={scenario_name}")

        config = await load_config()
        sub_id = config.target_subscription_id
        key_vault_url = config.key_vault_url

        # Create Key Vault client for secret storage
        credential = DefaultAzureCredential()
        key_vault_client = SecretClient(vault_url=key_vault_url, credential=credential)

        # Assign minimal required roles to service principal
        roles = ["Contributor", "Reader"]

        if not scenario_name:
            raise ValueError("scenario_name is required")

        sp_details = await create_service_principal(
            scenario_name=scenario_name,
            subscription_id=sub_id,
            roles=roles,
            key_vault_client=key_vault_client,
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
    """Activity: Deploy Container App for scenario execution."""
    from azure_haymaker.models.scenario import ScenarioMetadata
    from azure_haymaker.models.service_principal import ServicePrincipalDetails as SPDetailsModel
    from azure_haymaker.orchestrator.config import load_config
    from azure_haymaker.orchestrator.container_manager import deploy_container_app

    try:
        scenario = params.get("scenario", {})
        sp_details = params.get("sp_details", {})
        if not isinstance(scenario, dict):
            scenario = {}
        if not isinstance(sp_details, dict):
            sp_details = {}
        scenario_name = scenario.get("scenario_name")

        logger.info(f"Activity: deploy_container_app - scenario={scenario_name}")

        config = await load_config()

        # Convert created_at string to datetime
        created_at_str = sp_details.get("created_at")
        if created_at_str and isinstance(created_at_str, str):
            created_at_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            created_at_dt = datetime.now(UTC)

        # Validate required fields
        if not scenario_name:
            raise ValueError("scenario_name is required")

        # deploy_container_app returns resource ID string
        container_resource_id = await deploy_container_app(
            scenario=ScenarioMetadata(
                scenario_name=scenario_name,
                scenario_doc_path=scenario.get("scenario_doc_path", ""),
                agent_path=scenario.get("agent_path", ""),
                technology_area=scenario.get("technology_area", ""),
            ),
            sp=SPDetailsModel(
                sp_name=sp_details.get("sp_name", ""),
                client_id=sp_details.get("client_id", ""),
                principal_id=sp_details.get("principal_id", ""),
                secret_reference=sp_details.get("secret_reference", ""),
                created_at=created_at_dt,
                scenario_name=scenario_name,
            ),
            config=config,
        )

        # Extract container name from resource ID
        container_name = container_resource_id.split("/")[-1]

        logger.info(f"Activity: deploy_container_app - Deployed: {container_name}")
        return {
            "status": "success",
            "container_id": container_name,
            "container_name": container_name,
            "resource_id": container_resource_id,
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
    """Activity: Check status of running agents."""
    from azure_haymaker.orchestrator.config import load_config
    from azure_haymaker.orchestrator.container_manager import ContainerManager

    try:
        container_ids = params.get("container_ids", [])

        logger.info(f"Activity: check_agent_status - Checking {len(container_ids)} containers")

        config = await load_config()
        container_manager = ContainerManager(config)

        # Check status of each container
        statuses = {"running": 0, "completed": 0, "failed": 0}
        for container_id in container_ids:
            try:
                status = await container_manager.get_status(container_id)
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
    """Activity: Verify cleanup of resources."""
    from azure_haymaker.orchestrator.cleanup import query_managed_resources
    from azure_haymaker.orchestrator.config import load_config

    try:
        run_id = params.get("run_id")
        scenarios = params.get("scenarios", [])

        logger.info(f"Activity: verify_cleanup - Checking {len(scenarios)} scenarios")

        config = await load_config()
        # Ensure run_id is not None
        if not run_id:
            raise ValueError("run_id is required for cleanup verification")

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
    """Activity: Force cleanup of remaining resources and service principals."""
    from azure_haymaker.models.service_principal import ServicePrincipalDetails as SPDetailsModel
    from azure_haymaker.orchestrator.cleanup import force_delete_resources, query_managed_resources
    from azure_haymaker.orchestrator.config import load_config

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

        # Ensure run_id is not None
        if not run_id:
            raise ValueError("run_id is required for forced cleanup")

        # Query for resources to delete
        remaining_resources = await query_managed_resources(
            subscription_id=config.target_subscription_id,
            run_id=run_id,
        )

        # Create Key Vault client for SP secret deletion
        credential = DefaultAzureCredential()
        key_vault_client = SecretClient(vault_url=config.key_vault_url, credential=credential)

        # Convert sp_details dicts to ServicePrincipalDetails objects
        sp_details_objs = []
        for sp in sp_details_list:
            if not isinstance(sp, dict):
                continue
            created_at_str = sp.get("created_at")
            if created_at_str and isinstance(created_at_str, str):
                created_at_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            else:
                created_at_dt = datetime.now(UTC)

            sp_details_objs.append(
                SPDetailsModel(
                    sp_name=sp.get("sp_name", ""),
                    client_id=sp.get("client_id", ""),
                    principal_id=sp.get("principal_id", ""),
                    secret_reference=sp.get("secret_reference", ""),
                    created_at=created_at_dt,
                    scenario_name=sp.get("scenario_name", "unknown"),
                )
            )

        cleanup_report = await force_delete_resources(
            resources=remaining_resources,
            sp_details=sp_details_objs,
            kv_client=key_vault_client,
            subscription_id=config.target_subscription_id,
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
    """Activity: Generate execution report and store to storage account."""
    from azure_haymaker.orchestrator.config import load_config

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
            account_url=config.storage.account_url,
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
        await blob_client.upload_blob(json.dumps(report, indent=2), overwrite=True)  # type: ignore[misc]

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


# =============================================================================
# HTTP API FUNCTIONS - CLI Access (7 total)
# =============================================================================


@app.route(route="execute", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def execute_scenario(req: func.HttpRequest) -> func.HttpResponse:
    """Execute scenarios on-demand via HTTP POST.

    Request:
        POST /api/execute
        Body: {
            "scenarios": ["scenario-name-1", "scenario-name-2"],
            "duration_hours": 2,
            "tags": {"requester": "user@example.com"}
        }

    Response:
        202 Accepted: {
            "execution_id": "exec-20251115-abc123",
            "status": "queued",
            "scenarios": [...],
            "estimated_completion": "2025-11-15T10:00:00Z",
            "created_at": "2025-11-15T08:00:00Z"
        }

        400 Bad Request: Invalid request body
        404 Not Found: Scenario doesn't exist
        429 Too Many Requests: Rate limit exceeded
        500 Internal Server Error: Server error

    Args:
        req: HTTP request object

    Returns:
        HTTP response with execution details or error
    """
    import re
    from pathlib import Path
    from typing import Literal

    from azure.data.tables import TableClient
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    from pydantic import ValidationError

    from azure_haymaker.models.execution import (
        ExecutionRequest,
        ExecutionResponse,
        OnDemandExecutionStatus,
    )
    from azure_haymaker.orchestrator.config import load_config
    from azure_haymaker.orchestrator.execution_tracker import ExecutionTracker
    from azure_haymaker.orchestrator.rate_limiter import RateLimiter

    def extract_user_from_request(req: func.HttpRequest) -> str:
        """Extract user identifier from request for per-user rate limiting."""
        # Try to get Azure AD principal ID from headers
        principal_id = req.headers.get("x-ms-client-principal-id")
        if principal_id:
            return f"aad:{principal_id}"

        # Try to get API key from header and hash it
        api_key = req.headers.get("x-functions-key")
        if api_key:
            return f"key:{api_key[:8]}"

        # Fallback to IP address
        client_ip = req.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not client_ip:
            client_ip = req.headers.get("x-real-ip", "")

        if not client_ip:
            client_ip = "unknown"

        return f"ip:{client_ip}"

    def get_scenario_path(scenario_name: str) -> Path | None:
        """Get path to scenario document with path traversal protection."""
        # Validate scenario name format (alphanumeric and hyphens only)
        if not re.match(r"^[a-z0-9\-]+$", scenario_name):
            logger.warning(f"Invalid scenario name format: {scenario_name}")
            return None

        # Search in docs/scenarios directory
        project_root = Path(__file__).parent.parent
        scenarios_dir = project_root / "docs" / "scenarios"

        if not scenarios_dir.exists():
            logger.warning(f"Scenarios directory not found: {scenarios_dir}")
            return None

        # Construct expected scenario file path safely
        scenario_file = scenarios_dir / f"{scenario_name}.md"

        # Resolve to absolute path and verify it's within scenarios directory
        try:
            resolved_path = scenario_file.resolve(strict=False)
            scenarios_dir_resolved = scenarios_dir.resolve()

            # Check if resolved path is within scenarios directory
            if not str(resolved_path).startswith(str(scenarios_dir_resolved)):
                logger.warning(f"Path traversal attempt detected: {scenario_name}")
                return None

            # Return path if it exists
            return resolved_path if resolved_path.exists() else None

        except Exception as e:
            logger.error(f"Error resolving scenario path: {e}")
            return None

    def validate_scenarios(scenarios: list[str]) -> tuple[bool, str | None]:
        """Validate that all scenarios exist."""
        missing_scenarios = []

        for scenario_name in scenarios:
            path = get_scenario_path(scenario_name)
            if not path or not path.exists():
                missing_scenarios.append(scenario_name)

        if missing_scenarios:
            error_msg = f"Scenarios not found: {', '.join(missing_scenarios)}"
            return False, error_msg

        return True, None

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                body=json.dumps(
                    {
                        "error": {
                            "code": "INVALID_JSON",
                            "message": "Invalid JSON in request body",
                        }
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        # Validate request with Pydantic
        try:
            execution_request = ExecutionRequest(**body)
        except ValidationError as e:
            return func.HttpResponse(
                body=json.dumps(
                    {
                        "error": {
                            "code": "INVALID_REQUEST",
                            "message": "Request validation failed",
                            "details": e.errors(),
                        }
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        # Validate scenarios exist
        valid, error_msg = validate_scenarios(execution_request.scenarios)
        if not valid:
            return func.HttpResponse(
                body=json.dumps(
                    {
                        "error": {
                            "code": "SCENARIO_NOT_FOUND",
                            "message": error_msg,
                        }
                    }
                ),
                status_code=404,
                mimetype="application/json",
            )

        # Load config
        config = await load_config()

        # Check rate limits
        credential = DefaultAzureCredential()
        rate_limit_table = TableClient(
            endpoint=config.table_storage.account_url,
            table_name="RateLimits",
            credential=credential,
        )

        limiter = RateLimiter(rate_limit_table)

        # Extract user identifier for per-user rate limiting
        user_id = extract_user_from_request(req)

        # Check global, per-user, and per-scenario limits
        rate_limit_checks: list[tuple[Literal["global", "scenario", "user"], str]] = [
            ("global", "default"),
            ("user", user_id),
        ]
        for scenario in execution_request.scenarios:
            rate_limit_checks.append(("scenario", scenario))

        rate_limit_result = await limiter.check_multiple_limits(rate_limit_checks)

        if not rate_limit_result.allowed:
            return func.HttpResponse(
                body=json.dumps(
                    {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded. Try again in {rate_limit_result.retry_after} seconds.",
                        },
                        "retry_after": rate_limit_result.retry_after,
                    }
                ),
                status_code=429,
                mimetype="application/json",
                headers={"Retry-After": str(rate_limit_result.retry_after)},
            )

        # Create execution record
        execution_table = TableClient(
            endpoint=config.table_storage.account_url,
            table_name="Executions",
            credential=credential,
        )

        tracker = ExecutionTracker(execution_table)

        execution_id = await tracker.create_execution(
            scenarios=execution_request.scenarios,
            duration_hours=execution_request.duration_hours,
            tags=execution_request.tags,
        )

        # Enqueue execution request to Service Bus
        service_bus_client = ServiceBusClient(
            fully_qualified_namespace=f"{config.service_bus_namespace}.servicebus.windows.net",
            credential=credential,
        )

        async with service_bus_client:  # type: ignore[misc]
            sender = service_bus_client.get_queue_sender(queue_name="execution-requests")
            async with sender:  # type: ignore[misc]
                message_body = {
                    "execution_id": execution_id,
                    "scenarios": execution_request.scenarios,
                    "duration_hours": execution_request.duration_hours,
                    "tags": execution_request.tags,
                    "requested_at": datetime.now(UTC).isoformat(),
                }

                message = ServiceBusMessage(json.dumps(message_body))
                await sender.send_messages(message)  # type: ignore[misc]

        logger.info(f"Execution request queued: {execution_id}")

        # Build response
        now = datetime.now(UTC)
        estimated_completion = now + timedelta(hours=execution_request.duration_hours)

        response = ExecutionResponse(
            execution_id=execution_id,
            status=OnDemandExecutionStatus.QUEUED,
            scenarios=execution_request.scenarios,
            estimated_completion=estimated_completion,
            created_at=now,
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=202,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to process execution request: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to process execution request",
                    }
                }
            ),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="executions/{execution_id}", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def get_execution_status(req: func.HttpRequest) -> func.HttpResponse:
    """Get execution status via HTTP GET.

    Request:
        GET /api/executions/{execution_id}

    Response:
        200 OK: {
            "execution_id": "exec-20251115-abc123",
            "status": "running",
            "scenarios": [...],
            "created_at": "2025-11-15T08:00:00Z",
            "started_at": "2025-11-15T08:05:00Z",
            "progress": {
                "completed": 1,
                "running": 1,
                "failed": 0,
                "total": 2
            },
            "resources_created": 15
        }

        404 Not Found: Execution doesn't exist
        500 Internal Server Error: Server error

    Args:
        req: HTTP request object with execution_id in route

    Returns:
        HTTP response with execution status or error
    """
    from azure.data.tables import TableClient

    from azure_haymaker.orchestrator.config import load_config
    from azure_haymaker.orchestrator.execution_tracker import ExecutionTracker

    try:
        # Extract execution_id from route
        execution_id = req.route_params.get("execution_id")

        if not execution_id:
            return func.HttpResponse(
                body=json.dumps(
                    {
                        "error": {
                            "code": "MISSING_EXECUTION_ID",
                            "message": "Execution ID is required",
                        }
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        # Load config
        config = await load_config()

        # Query execution status
        credential = DefaultAzureCredential()
        execution_table = TableClient(
            endpoint=config.table_storage.account_url,
            table_name="Executions",
            credential=credential,
        )

        tracker = ExecutionTracker(execution_table)

        try:
            status = await tracker.get_execution_status(execution_id)

            return func.HttpResponse(
                body=status.model_dump_json(),
                status_code=200,
                mimetype="application/json",
            )

        except Exception:
            # Log detailed error internally but return generic message
            logger.error(f"Execution not found: {execution_id}", exc_info=True)
            return func.HttpResponse(
                body=json.dumps(
                    {
                        "error": {
                            "code": "EXECUTION_NOT_FOUND",
                            "message": "Execution not found",
                        }
                    }
                ),
                status_code=404,
                mimetype="application/json",
            )

    except Exception as e:
        logger.error(f"Failed to get execution status: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to get execution status",
                    }
                }
            ),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="agents", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def list_agents(req: func.HttpRequest) -> func.HttpResponse:
    """List all agents.

    Query Parameters:
        status: Optional status filter (running, completed, failed)
        limit: Maximum number of results (default: 100)

    Response:
        200 OK: {
            "agents": [
                {
                    "agent_id": str,
                    "scenario": str,
                    "status": str,
                    "started_at": str (ISO 8601),
                    "completed_at": str (ISO 8601) | null,
                    "progress": str | null,
                    "error": str | null
                }
            ]
        }

        500 Internal Server Error: Server error

    Example:
        GET /api/agents
        GET /api/agents?status=running
        GET /api/agents?limit=50
    """
    import os

    from azure.data.tables import TableServiceClient
    from pydantic import BaseModel

    class AgentInfo(BaseModel):
        """Agent information."""

        agent_id: str
        scenario: str
        status: str
        started_at: datetime
        completed_at: datetime | None = None
        progress: str | None = None
        error: str | None = None

    def sanitize_odata_value(value: str) -> str:
        """Sanitize input for OData query filters."""
        return str(value).replace("'", "''")

    async def query_agents_from_table(
        table_client,
        status_filter: str | None = None,
        limit: int = 100,
    ) -> list[AgentInfo]:
        """Query agents from Table Storage."""
        agents = []

        try:
            # Build query filter
            query_filter = None
            if status_filter:
                query_filter = f"status eq '{sanitize_odata_value(status_filter)}'"

            # Query table
            entities = table_client.query_entities(
                query_filter=query_filter,
                select=[
                    "agent_id",
                    "scenario",
                    "status",
                    "started_at",
                    "completed_at",
                    "progress",
                    "error",
                ],
            )

            # Convert to AgentInfo models
            for entity in entities:
                if len(agents) >= limit:
                    break

                try:
                    agent = AgentInfo(
                        agent_id=entity.get("agent_id", entity.get("RowKey", "unknown")),
                        scenario=entity.get("scenario", "unknown"),
                        status=entity.get("status", "unknown"),
                        started_at=entity.get("started_at", datetime.now()),
                        completed_at=entity.get("completed_at"),
                        progress=entity.get("progress"),
                        error=entity.get("error"),
                    )
                    agents.append(agent)
                except Exception as e:
                    logger.warning(f"Error parsing agent entity: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error querying agents from table: {e}")
            raise

        return agents

    try:
        # Parse query parameters
        status_filter = req.params.get("status")
        limit = int(req.params.get("limit", "100"))

        # Get Table Storage configuration
        table_account_name = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        table_name = os.getenv("AGENTS_TABLE_NAME", "agents")

        if not table_account_name:
            logger.error("TABLE_STORAGE_ACCOUNT_NAME not configured")
            return func.HttpResponse(
                body='{"error": "Agents storage not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Create Table Storage client (using managed identity)
        credential = DefaultAzureCredential()
        table_service_client = TableServiceClient(
            endpoint=f"https://{table_account_name}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service_client.get_table_client(table_name)

        # Query agents
        agents = await query_agents_from_table(
            table_client,
            status_filter=status_filter,
            limit=limit,
        )

        # Build response
        response = {"agents": [agent.model_dump(mode="json") for agent in agents]}

        return func.HttpResponse(
            body=str(response),
            status_code=200,
            mimetype="application/json",
        )

    except ValueError as e:
        logger.warning(f"Invalid parameter in list_agents: {e}")
        return func.HttpResponse(
            body='{"error": {"code": "INVALID_PARAMETER", "message": "Invalid request parameter"}}',
            status_code=400,
            mimetype="application/json",
        )
    except Exception:
        logger.exception("Error listing agents")
        return func.HttpResponse(
            body='{"error": {"code": "INTERNAL_ERROR", "message": "Failed to list agents"}}',
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="agents/{agent_id}/logs", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def get_agent_logs(req: func.HttpRequest) -> func.HttpResponse:
    """Get logs for an agent.

    Path Parameters:
        agent_id: Agent ID

    Query Parameters:
        tail: Number of recent log entries (default: 100)
        since: ISO 8601 timestamp to get logs after (for --follow mode)

    Response:
        200 OK: {
            "logs": [
                {
                    "timestamp": str (ISO 8601),
                    "level": str,
                    "message": str,
                    "agent_id": str,
                    "source": str
                }
            ]
        }

        404 Not Found: Agent not found
        500 Internal Server Error: Server error

    Example:
        GET /api/agents/agent-123/logs
        GET /api/agents/agent-123/logs?tail=50
        GET /api/agents/agent-123/logs?since=2025-11-17T12:00:00Z
    """
    import os

    from azure.cosmos import CosmosClient
    from pydantic import BaseModel

    class LogEntry(BaseModel):
        """Log entry."""

        timestamp: str
        level: str
        message: str
        agent_id: str
        source: str = "agent"

    async def query_logs_from_cosmosdb(
        agent_id: str,
        tail: int = 100,
        since_timestamp: str | None = None,
    ) -> list[LogEntry]:
        """Query logs from Cosmos DB."""
        logs = []

        try:
            # Initialize Cosmos DB client
            cosmos_endpoint = os.getenv("COSMOSDB_ENDPOINT")
            if not cosmos_endpoint:
                logger.error("COSMOSDB_ENDPOINT not configured")
                return logs

            credential = DefaultAzureCredential()
            cosmos_client = CosmosClient(cosmos_endpoint, credential)
            database = cosmos_client.get_database_client("haymaker")
            container = database.get_container_client("agent-logs")

            # Build query
            if since_timestamp:
                query = """
                    SELECT * FROM c
                    WHERE c.agent_id = @agent_id
                    AND c.timestamp > @since_timestamp
                    ORDER BY c.timestamp DESC
                """
                parameters = [
                    {"name": "@agent_id", "value": agent_id},
                    {"name": "@since_timestamp", "value": since_timestamp},
                ]
            else:
                query = """
                    SELECT TOP @limit * FROM c
                    WHERE c.agent_id = @agent_id
                    ORDER BY c.timestamp DESC
                """
                parameters = [
                    {"name": "@agent_id", "value": agent_id},
                    {"name": "@limit", "value": tail},
                ]

            # Execute query
            items = list(
                container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=agent_id,
                    enable_cross_partition_query=False,
                )
            )

            # Convert to LogEntry objects
            for item in items:
                log_entry = LogEntry(
                    timestamp=item.get("timestamp", ""),
                    level=item.get("level", "INFO"),
                    message=item.get("message", ""),
                    agent_id=item.get("agent_id", ""),
                    source=item.get("source", "agent"),
                )
                logs.append(log_entry)

            logger.info(f"Retrieved {len(logs)} logs for agent {agent_id}")

        except Exception as e:
            logger.error(f"Error querying logs from Cosmos DB: {e}")
            raise

        return logs

    try:
        # Parse path parameter
        agent_id = req.route_params.get("agent_id")

        if not agent_id:
            return func.HttpResponse(
                body='{"error": "agent_id is required"}',
                status_code=400,
                mimetype="application/json",
            )

        # Parse query parameters
        tail = int(req.params.get("tail", "100"))
        since_timestamp = req.params.get("since")

        # Query logs from Cosmos DB
        logs = await query_logs_from_cosmosdb(
            agent_id=agent_id, tail=tail, since_timestamp=since_timestamp
        )

        # Format response
        response_data = {
            "logs": [
                {
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "message": log.message,
                    "agent_id": log.agent_id,
                    "source": log.source,
                }
                for log in logs
            ]
        }

        return func.HttpResponse(
            body=json.dumps(response_data), status_code=200, mimetype="application/json"
        )

    except ValueError as e:
        logger.warning(f"Invalid parameter in get_agent_logs: {e}")
        return func.HttpResponse(
            body='{"error": {"code": "INVALID_PARAMETER", "message": "Invalid request parameter"}}',
            status_code=400,
            mimetype="application/json",
        )
    except Exception:
        logger.exception("Error retrieving agent logs")
        return func.HttpResponse(
            body='{"error": {"code": "INTERNAL_ERROR", "message": "Failed to retrieve agent logs"}}',
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="metrics", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def get_metrics(req: func.HttpRequest) -> func.HttpResponse:
    """Get aggregated execution metrics.

    Query Parameters:
        period: Time period (7d, 30d, 90d) - default: 7d
        scenario: Optional scenario name filter

    Response:
        200 OK: {
            "total_executions": int,
            "active_agents": int,
            "total_resources": int,
            "last_execution": str (ISO 8601) | null,
            "success_rate": float,
            "period": str,
            "scenarios": [
                {
                    "scenario_name": str,
                    "run_count": int,
                    "success_count": int,
                    "fail_count": int,
                    "avg_duration_hours": float | null
                }
            ]
        }

        400 Bad Request: Invalid query parameters
        500 Internal Server Error: Server error

    Example:
        GET /api/metrics?period=30d
        GET /api/metrics?period=7d&scenario=compute-01
    """
    import os

    from azure.cosmos import CosmosClient
    from pydantic import BaseModel, Field

    class ScenarioMetrics(BaseModel):
        """Per-scenario metrics."""

        scenario_name: str
        run_count: int
        success_count: int
        fail_count: int
        avg_duration_hours: float | None = None

    class MetricsSummary(BaseModel):
        """Metrics summary response."""

        total_executions: int
        active_agents: int
        total_resources: int
        last_execution: datetime | None = None
        success_rate: float
        period: str = "7d"
        scenarios: list[ScenarioMetrics] = Field(default_factory=list)

    def parse_period(period: str) -> timedelta:
        """Parse period string to timedelta."""
        if period.endswith("d"):
            try:
                days = int(period[:-1])
                return timedelta(days=days)
            except ValueError:
                raise ValueError(
                    f"Invalid period format: {period}. Must be like '7d', '30d', '90d'"
                ) from None
        else:
            raise ValueError(f"Invalid period format: {period}. Must be like '7d', '30d', '90d'")

    async def query_cosmos_metrics(
        cosmos_client: CosmosClient,
        database_name: str,
        container_name: str,
        start_time: datetime,
        scenario_filter: str | None = None,
    ) -> dict[str, Any]:
        """Query metrics from Cosmos DB."""
        database = cosmos_client.get_database_client(database_name)
        container = database.get_container_client(container_name)

        # Build query
        query = """
            SELECT
                c.scenario_name,
                c.status,
                c.started_at,
                c.completed_at,
                c.execution_id
            FROM c
            WHERE c.started_at >= @start_time
        """

        params: list[dict[str, object]] = [
            {"name": "@start_time", "value": start_time.isoformat()}
        ]

        if scenario_filter:
            query += " AND c.scenario_name = @scenario"
            params.append({"name": "@scenario", "value": scenario_filter})

        # Execute query
        items = list(
            container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )

        # Aggregate metrics
        scenario_stats: dict[str, dict[str, Any]] = {}
        total_executions = len(items)
        success_count = 0
        last_execution = None

        for item in items:
            scenario_name = item.get("scenario_name", "unknown")
            status = item.get("status", "unknown")
            started_at = item.get("started_at")
            completed_at = item.get("completed_at")

            # Track scenario stats
            if scenario_name not in scenario_stats:
                scenario_stats[scenario_name] = {
                    "run_count": 0,
                    "success_count": 0,
                    "fail_count": 0,
                    "total_duration": 0,
                    "duration_count": 0,
                }

            stats = scenario_stats[scenario_name]
            stats["run_count"] += 1

            if status == "completed":
                stats["success_count"] += 1
                success_count += 1
            elif status == "failed":
                stats["fail_count"] += 1

            # Calculate duration
            if started_at and completed_at:
                try:
                    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    duration = (end - start).total_seconds() / 3600  # hours
                    stats["total_duration"] += duration
                    stats["duration_count"] += 1
                except (ValueError, AttributeError):
                    pass

            # Track latest execution
            if started_at:
                try:
                    execution_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    if last_execution is None or execution_time > last_execution:
                        last_execution = execution_time
                except (ValueError, AttributeError):
                    pass

        # Build scenario metrics
        scenario_metrics = []
        for scenario_name, stats in scenario_stats.items():
            avg_duration = None
            if stats["duration_count"] > 0:
                avg_duration = stats["total_duration"] / stats["duration_count"]

            scenario_metrics.append(
                ScenarioMetrics(
                    scenario_name=scenario_name,
                    run_count=stats["run_count"],
                    success_count=stats["success_count"],
                    fail_count=stats["fail_count"],
                    avg_duration_hours=avg_duration,
                )
            )

        # Sort by run count (descending)
        scenario_metrics.sort(key=lambda x: int(x.run_count), reverse=True)  # type: ignore[arg-type,return-value]

        # Calculate success rate
        success_rate = success_count / total_executions if total_executions > 0 else 0.0

        return {
            "total_executions": total_executions,
            "success_count": success_count,
            "success_rate": success_rate,
            "last_execution": last_execution,
            "scenario_metrics": scenario_metrics,
        }

    try:
        # Parse query parameters
        period = req.params.get("period", "7d")
        scenario_filter = req.params.get("scenario")

        # Validate period
        try:
            period_delta = parse_period(period)
        except ValueError as e:
            return func.HttpResponse(
                body=str(e),
                status_code=400,
                mimetype="application/json",
            )

        # Calculate start time
        start_time = datetime.now(UTC) - period_delta

        # Get Cosmos DB configuration from environment
        cosmos_endpoint = os.getenv("COSMOSDB_ENDPOINT")
        cosmos_database = os.getenv("COSMOSDB_DATABASE", "haymaker")
        cosmos_container = os.getenv("COSMOSDB_METRICS_CONTAINER", "execution_metrics")

        if not cosmos_endpoint:
            logger.error("COSMOSDB_ENDPOINT not configured")
            return func.HttpResponse(
                body='{"error": "Metrics database not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Create Cosmos DB client (using managed identity)
        credential = DefaultAzureCredential()
        cosmos_client = CosmosClient(cosmos_endpoint, credential)

        # Query metrics
        metrics_data = await query_cosmos_metrics(
            cosmos_client,
            cosmos_database,
            cosmos_container,
            start_time,
            scenario_filter,
        )

        # Get active agents count (query from Table Storage or return 0)
        active_agents = 0
        total_resources = 0

        # Build response
        summary = MetricsSummary(
            total_executions=metrics_data["total_executions"],
            active_agents=active_agents,
            total_resources=total_resources,
            last_execution=metrics_data["last_execution"],
            success_rate=metrics_data["success_rate"],
            period=period,
            scenarios=metrics_data["scenario_metrics"],
        )

        return func.HttpResponse(
            body=summary.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.exception("Error retrieving metrics")
        return func.HttpResponse(
            body=f'{{"error": "{str(e)}"}}',
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="resources", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def list_resources(req: func.HttpRequest) -> func.HttpResponse:
    """List all resources.

    Query Parameters:
        execution_id: Optional execution ID filter
        scenario: Optional scenario filter
        status: Optional status filter (created, deleted)
        limit: Maximum number of results (default: 100)

    Response:
        200 OK: {
            "resources": [
                {
                    "id": str,
                    "name": str,
                    "type": str,
                    "scenario": str,
                    "execution_id": str,
                    "created_at": str (ISO 8601),
                    "deleted_at": str (ISO 8601) | null,
                    "status": str,
                    "tags": {
                        "key": "value"
                    }
                }
            ]
        }

        500 Internal Server Error: Server error

    Example:
        GET /api/resources
        GET /api/resources?scenario=compute-01
        GET /api/resources?execution_id=exec-123
        GET /api/resources?status=created
    """
    import os

    from azure.data.tables import TableServiceClient
    from pydantic import BaseModel, Field

    class ResourceInfo(BaseModel):
        """Resource information."""

        id: str
        name: str
        type: str
        scenario: str
        execution_id: str
        created_at: datetime
        deleted_at: datetime | None = None
        status: str = "created"
        tags: dict[str, str] = Field(default_factory=dict)

    async def query_resources_from_table(
        table_client,
        execution_id: str | None = None,
        scenario: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ResourceInfo]:
        """Query resources from Table Storage."""
        resources = []

        try:
            # Build query filter
            filters = []

            if execution_id:
                filters.append(f"execution_id eq '{execution_id}'")

            if scenario:
                filters.append(f"scenario eq '{scenario}'")

            if status:
                filters.append(f"status eq '{status}'")

            query_filter = " and ".join(filters) if filters else None

            # Query table
            entities = table_client.query_entities(
                query_filter=query_filter,
                select=[
                    "resource_id",
                    "resource_name",
                    "resource_type",
                    "scenario",
                    "execution_id",
                    "created_at",
                    "deleted_at",
                    "status",
                ],
            )

            # Convert to ResourceInfo models
            for entity in entities:
                if len(resources) >= limit:
                    break

                try:
                    # Parse tags from entity
                    tags = {}
                    for key, value in entity.items():
                        if key.startswith("tag_"):
                            tag_name = key[4:]  # Remove 'tag_' prefix
                            tags[tag_name] = value

                    resource = ResourceInfo(
                        id=entity.get("resource_id", entity.get("RowKey", "unknown")),
                        name=entity.get("resource_name", "unknown"),
                        type=entity.get("resource_type", "unknown"),
                        scenario=entity.get("scenario", "unknown"),
                        execution_id=entity.get("execution_id", "unknown"),
                        created_at=entity.get("created_at", datetime.now()),
                        deleted_at=entity.get("deleted_at"),
                        status=entity.get("status", "created"),
                        tags=tags,
                    )
                    resources.append(resource)
                except Exception as e:
                    logger.warning(f"Error parsing resource entity: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error querying resources from table: {e}")
            raise

        return resources

    try:
        # Parse query parameters
        execution_id = req.params.get("execution_id")
        scenario = req.params.get("scenario")
        status = req.params.get("status")
        limit = int(req.params.get("limit", "100"))

        # Get Table Storage configuration
        table_account_name = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        table_name = os.getenv("RESOURCES_TABLE_NAME", "resources")

        if not table_account_name:
            logger.error("TABLE_STORAGE_ACCOUNT_NAME not configured")
            return func.HttpResponse(
                body='{"error": "Resources storage not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Create Table Storage client (using managed identity)
        credential = DefaultAzureCredential()
        table_service_client = TableServiceClient(
            endpoint=f"https://{table_account_name}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service_client.get_table_client(table_name)

        # Query resources
        resources = await query_resources_from_table(
            table_client,
            execution_id=execution_id,
            scenario=scenario,
            status=status,
            limit=limit,
        )

        # Build response
        response = {"resources": [resource.model_dump(mode="json") for resource in resources]}

        return func.HttpResponse(
            body=str(response),
            status_code=200,
            mimetype="application/json",
        )

    except ValueError as e:
        return func.HttpResponse(
            body=f'{{"error": "Invalid parameter: {str(e)}"}}',
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logger.exception("Error listing resources")
        return func.HttpResponse(
            body=f'{{"error": "{str(e)}"}}',
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="resources/{resource_id}", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def get_resource(req: func.HttpRequest) -> func.HttpResponse:
    """Get details for a specific resource.

    Path Parameters:
        resource_id: Resource ID

    Response:
        200 OK: ResourceInfo object
        404 Not Found: Resource not found
        500 Internal Server Error: Server error

    Example:
        GET /api/resources/resource-123
    """
    import os

    from azure.data.tables import TableServiceClient
    from pydantic import BaseModel, Field

    class ResourceInfo(BaseModel):
        """Resource information."""

        id: str
        name: str
        type: str
        scenario: str
        execution_id: str
        created_at: datetime
        deleted_at: datetime | None = None
        status: str = "created"
        tags: dict[str, str] = Field(default_factory=dict)

    try:
        # Parse path parameter
        resource_id = req.route_params.get("resource_id")

        if not resource_id:
            return func.HttpResponse(
                body='{"error": "resource_id is required"}',
                status_code=400,
                mimetype="application/json",
            )

        # Get Table Storage configuration
        table_account_name = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        table_name = os.getenv("RESOURCES_TABLE_NAME", "resources")

        if not table_account_name:
            logger.error("TABLE_STORAGE_ACCOUNT_NAME not configured")
            return func.HttpResponse(
                body='{"error": "Resources storage not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Create Table Storage client (using managed identity)
        credential = DefaultAzureCredential()
        table_service_client = TableServiceClient(
            endpoint=f"https://{table_account_name}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service_client.get_table_client(table_name)

        # Query specific resource
        try:
            entity = table_client.get_entity(
                partition_key="resources",  # Assuming all resources use same partition
                row_key=resource_id,
            )

            # Parse tags
            tags = {}
            for key, value in entity.items():
                if key.startswith("tag_"):
                    tag_name = key[4:]
                    tags[tag_name] = value

            # Build resource info
            resource = ResourceInfo(
                id=entity.get("resource_id", resource_id),
                name=entity.get("resource_name", "unknown"),
                type=entity.get("resource_type", "unknown"),
                scenario=entity.get("scenario", "unknown"),
                execution_id=entity.get("execution_id", "unknown"),
                created_at=entity.get("created_at", datetime.now()),
                deleted_at=entity.get("deleted_at"),
                status=entity.get("status", "created"),
                tags=tags,
            )

            return func.HttpResponse(
                body=resource.model_dump_json(),
                status_code=200,
                mimetype="application/json",
            )

        except Exception:
            logger.warning(f"Resource not found: {resource_id}")
            return func.HttpResponse(
                body='{"error": "Resource not found"}',
                status_code=404,
                mimetype="application/json",
            )

    except Exception as e:
        logger.exception("Error retrieving resource")
        return func.HttpResponse(
            body=f'{{"error": "{str(e)}"}}',
            status_code=500,
            mimetype="application/json",
        )
