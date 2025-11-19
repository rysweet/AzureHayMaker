"""Main workflow orchestration for Azure HayMaker.

This module implements the durable orchestration function that coordinates
the complete Azure HayMaker execution workflow across 7 phases:

1. Validation: Verify credentials, APIs, and prerequisites
2. Selection: Randomly select scenarios based on simulation size
3. Provisioning: Create SPs and deploy Container Apps (parallel)
4. Monitoring: Wait 8 hours with periodic status checks
5. Cleanup: Verify cleanup completion
6. Forced Cleanup: Force-delete remaining resources (if needed)
7. Reporting: Generate execution report

Design Pattern: Long-Running Orchestration
- Uses Durable Functions for reliable execution
- Checkpoints progress at each phase
- Handles failures gracefully
- Supports replays (idempotent)

Dependencies:
- orchestrator_app: Shared FunctionApp instance
- activities/*: Activity functions (called by name)
"""

import logging
from datetime import timedelta
from typing import Any

from azure_haymaker.orchestrator.orchestrator_app import app

logger = logging.getLogger(__name__)


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
