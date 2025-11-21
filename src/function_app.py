"""Azure Functions entry point for Azure HayMaker orchestrator.

MONOLITHIC PATTERN (Issue #28 Fix):
All function decorators must be in this file for Azure Functions V4 discovery.
The runtime discovers functions by introspecting this module and finding
all @app.* decorated functions.

This approach ensures 100% reliable function discovery by keeping all
decorators in the entry point file where Azure Functions expects them.

Architecture:
- Single FunctionApp instance created in this file
- All 10 functions decorated here (not in separate modules)
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
