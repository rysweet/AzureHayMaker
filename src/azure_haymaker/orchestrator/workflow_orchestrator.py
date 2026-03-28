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

Refactored Structure:
- Main orchestration function coordinates all phases (< 50 LOC)
- Helper functions handle each phase (each < 50 LOC)
- Maintains generator pattern for Durable Functions
- Preserves all existing behavior and error handling

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
# HELPER FUNCTIONS - Phase Implementations
# =============================================================================


def _initialize_execution_report(run_id: str, started_at: str) -> dict[str, Any]:
    """Initialize execution report structure.

    Args:
        run_id: Unique run identifier
        started_at: ISO timestamp for run start

    Returns:
        Initial execution report dictionary
    """
    return {
        "run_id": run_id,
        "started_at": started_at,
        "status": "in_progress",
        "phases": {},
    }


def _execute_validation_phase(context: Any, run_id: str, execution_report: dict[str, Any]):
    """Execute Phase 1: Environment validation.

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        execution_report: Execution report to update

    Yields:
        Activity call results

    Returns:
        Tuple of (validation_result, passed: bool)
    """
    logger.info(f"[{run_id}] Starting Phase 1: Validation")

    validation_result = yield context.call_activity("validate_environment_activity", None)

    overall_passed: bool = validation_result["overall_passed"]

    if not overall_passed:
        logger.error(f"[{run_id}] Validation failed: {validation_result}")
        execution_report["status"] = "failed"
        execution_report["failure_reason"] = "environment_validation_failed"

        if "phases" not in execution_report or not isinstance(execution_report["phases"], dict):
            execution_report["phases"] = {}

        phases: dict[str, Any] = execution_report["phases"]  # type: ignore[assignment]
        phases["validation"] = validation_result
        return (validation_result, False)

    if "phases" not in execution_report or not isinstance(execution_report["phases"], dict):
        execution_report["phases"] = {}

    phases = execution_report["phases"]  # type: ignore[assignment]
    phases["validation"] = {"status": "passed", "checks": validation_result["results"]}

    logger.info(f"[{run_id}] Phase 1: Validation passed")
    return (validation_result, True)


def _execute_selection_phase(context: Any, run_id: str, execution_report: dict[str, Any]):
    """Execute Phase 2: Scenario selection.

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        execution_report: Execution report to update

    Yields:
        Activity call results

    Returns:
        Selection result dictionary with scenarios list
    """
    logger.info(f"[{run_id}] Starting Phase 2: Scenario Selection")

    selection_result = yield context.call_activity("select_scenarios_activity", None)

    selected_scenarios = selection_result["scenarios"]
    logger.info(f"[{run_id}] Selected {len(selected_scenarios)} scenarios")

    if "phases" not in execution_report:
        execution_report["phases"] = {}

    phases: dict[str, Any] = execution_report["phases"]  # type: ignore[assignment]
    phases["selection"] = {
        "status": "completed",
        "scenario_count": len(selected_scenarios),
        "scenarios": [s["scenario_name"] for s in selected_scenarios],
    }

    if not selected_scenarios:
        logger.error(f"[{run_id}] No scenarios selected")
        execution_report["status"] = "failed"
        execution_report["failure_reason"] = "no_scenarios_selected"

    return selection_result


def _create_service_principals(context: Any, run_id: str, selected_scenarios: list[dict[str, Any]]):
    """Create service principals in parallel for all scenarios.

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        selected_scenarios: List of selected scenarios

    Yields:
        Parallel task results

    Returns:
        List of SP creation results
    """
    sp_tasks = [
        context.call_activity(
            "create_service_principal_activity",
            {"run_id": run_id, "scenario": scenario},
        )
        for scenario in selected_scenarios
    ]

    sp_results = yield context.task_all(sp_tasks)

    failed_sps = [sp for sp in sp_results if sp["status"] == "failed"]
    if failed_sps:
        logger.warning(f"[{run_id}] {len(failed_sps)} SPs failed to create (will attempt cleanup)")

    successful_sps = [sp for sp in sp_results if sp["status"] == "success"]
    logger.info(
        f"[{run_id}] Created {len(successful_sps)}/{len(selected_scenarios)} service principals"
    )

    return sp_results


def _deploy_containers(
    context: Any,
    run_id: str,
    selected_scenarios: list[dict[str, Any]],
    sp_results: list[dict[str, Any]],
):
    """Deploy Container Apps in parallel for successful SPs.

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        selected_scenarios: List of selected scenarios
        sp_results: Results from SP creation

    Yields:
        Parallel task results

    Returns:
        List of container deployment results
    """
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

    successful_containers = [c for c in container_results if c["status"] == "success"]
    logger.info(
        f"[{run_id}] Deployed {len(successful_containers)}/{len(container_tasks)} container apps"
    )

    return container_results


def _execute_provisioning_phase(
    context: Any,
    run_id: str,
    selected_scenarios: list[dict[str, Any]],
    execution_report: dict[str, Any],
):
    """Execute Phase 3: Provisioning (SPs + Containers in parallel).

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        selected_scenarios: List of selected scenarios
        execution_report: Execution report to update

    Yields:
        Activity and task results

    Returns:
        Dictionary with provisioning results
    """
    logger.info(f"[{run_id}] Starting Phase 3: Provisioning ({len(selected_scenarios)} scenarios)")

    sp_results = yield from _create_service_principals(context, run_id, selected_scenarios)
    container_results = yield from _deploy_containers(
        context, run_id, selected_scenarios, sp_results
    )

    failed_sps = [sp for sp in sp_results if sp["status"] == "failed"]
    successful_sps = [sp for sp in sp_results if sp["status"] == "success"]
    failed_containers = [c for c in container_results if c["status"] == "failed"]
    successful_containers = [c for c in container_results if c["status"] == "success"]

    if "phases" not in execution_report:
        execution_report["phases"] = {}

    phases: dict[str, Any] = execution_report["phases"]  # type: ignore[assignment]
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

    return {
        "sp_results": sp_results,
        "container_results": container_results,
        "successful_sps": successful_sps,
        "successful_containers": successful_containers,
    }


def _execute_monitoring_phase(
    context: Any,
    run_id: str,
    successful_containers: list[dict[str, Any]],
    execution_report: dict[str, Any],
):
    """Execute Phase 4: 8-hour monitoring with periodic checks.

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        successful_containers: List of successfully deployed containers
        execution_report: Execution report to update

    Yields:
        Activity calls and timer waits
    """
    logger.info(f"[{run_id}] Starting Phase 4: Monitoring (8 hours)")

    monitoring_end_time = context.current_utc_datetime + timedelta(hours=8)
    monitoring_status = {"status_checks": [], "log_messages": 0, "resource_count": 0}

    while context.current_utc_datetime < monitoring_end_time:
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

        yield context.create_timer(context.current_utc_datetime + timedelta(minutes=15))

    if "phases" not in execution_report:
        execution_report["phases"] = {}

    phases: dict[str, Any] = execution_report["phases"]  # type: ignore[assignment]
    phases["monitoring"] = monitoring_status

    logger.info(f"[{run_id}] Phase 4: Monitoring completed after 8 hours")


def _execute_cleanup_phases(
    context: Any,
    run_id: str,
    selected_scenarios: list[dict[str, Any]],
    successful_sps: list[dict[str, Any]],
    execution_report: dict[str, Any],
):
    """Execute Phase 5-6: Cleanup verification and forced cleanup if needed.

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        selected_scenarios: List of selected scenarios
        successful_sps: List of successfully created SPs
        execution_report: Execution report to update

    Yields:
        Activity call results
    """
    logger.info(f"[{run_id}] Starting Phase 5: Cleanup Verification")

    cleanup_verification = yield context.call_activity(
        "verify_cleanup_activity",
        {"run_id": run_id, "scenarios": [s["scenario_name"] for s in selected_scenarios]},
    )

    remaining_resources = cleanup_verification["remaining_resources"]
    logger.info(f"[{run_id}] Cleanup verification: {len(remaining_resources)} resources remaining")

    if "phases" not in execution_report:
        execution_report["phases"] = {}

    phases: dict[str, Any] = execution_report["phases"]  # type: ignore[assignment]

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

        phases["cleanup"] = {
            "status": cleanup_result["status"],
            "verification_found": len(remaining_resources),
            "deleted": cleanup_result["deleted_count"],
            "failed": cleanup_result["failed_count"],
        }

        logger.info(
            f"[{run_id}] Forced cleanup completed: {cleanup_result['deleted_count']} deleted, {cleanup_result['failed_count']} failed"
        )
    else:
        logger.info(f"[{run_id}] No remaining resources found. Cleanup verified.")
        phases["cleanup"] = {
            "status": "verified",
            "verification_found": 0,
            "deleted": 0,
            "failed": 0,
        }


def _execute_reporting_phase(
    context: Any,
    run_id: str,
    execution_report: dict[str, Any],
    selected_scenarios: list[dict[str, Any]],
    sp_count: int,
    container_count: int,
):
    """Execute Phase 7: Generate execution report.

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        execution_report: Execution report to include
        selected_scenarios: List of selected scenarios
        sp_count: Number of successful SPs
        container_count: Number of successful containers

    Yields:
        Activity call result

    Returns:
        Report URL string
    """
    logger.info(f"[{run_id}] Starting Phase 7: Report Generation")

    report = yield context.call_activity(
        "generate_report_activity",
        {
            "run_id": run_id,
            "execution_report": execution_report,
            "selected_scenarios": [s["scenario_name"] for s in selected_scenarios],
            "sp_count": sp_count,
            "container_count": container_count,
        },
    )

    return report["report_url"]


def _handle_orchestration_error(
    context: Any, run_id: str, execution_report: dict[str, Any], error: Exception
) -> dict[str, Any]:
    """Handle orchestration errors and update execution report.

    Args:
        context: Durable orchestration context
        run_id: Unique run identifier
        execution_report: Execution report to update
        error: Exception that occurred

    Returns:
        Updated execution report with error details
    """
    logger.error(f"[{run_id}] Orchestration failed with error: {str(error)}", exc_info=True)

    execution_report["status"] = "failed"
    execution_report["error"] = str(error)
    execution_report["ended_at"] = context.current_utc_datetime.isoformat()

    return execution_report


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

    execution_report = _initialize_execution_report(run_id, started_at)

    try:
        # Phase 1: Validation
        _validation_result, passed = yield from _execute_validation_phase(
            context, run_id, execution_report
        )
        if not passed:
            return execution_report

        # Phase 2: Selection
        selection_result = yield from _execute_selection_phase(context, run_id, execution_report)
        if not selection_result["scenarios"]:
            return execution_report

        selected_scenarios = selection_result["scenarios"]

        # Phase 3: Provisioning
        provisioning_result = yield from _execute_provisioning_phase(
            context, run_id, selected_scenarios, execution_report
        )

        # Phase 4: Monitoring
        yield from _execute_monitoring_phase(
            context, run_id, provisioning_result["successful_containers"], execution_report
        )

        # Phase 5-6: Cleanup
        yield from _execute_cleanup_phases(
            context,
            run_id,
            selected_scenarios,
            provisioning_result["successful_sps"],
            execution_report,
        )

        # Phase 7: Reporting
        report_url = yield from _execute_reporting_phase(
            context,
            run_id,
            execution_report,
            selected_scenarios,
            len(provisioning_result["successful_sps"]),
            len(provisioning_result["successful_containers"]),
        )

        execution_report["status"] = "completed"
        execution_report["ended_at"] = context.current_utc_datetime.isoformat()
        execution_report["report_url"] = report_url

        logger.info(f"[{run_id}] Orchestration completed successfully")
        return execution_report

    except Exception as e:
        return _handle_orchestration_error(context, run_id, execution_report, e)


__all__ = [
    "orchestrate_haymaker_run",
]
