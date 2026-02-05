"""Orchestration service - background orchestration logic.

Single Responsibility: Execute orchestration workflows.

Public API:
    run_scheduled_orchestration: Cron-triggered orchestration
    run_orchestration: Main 6-phase orchestration workflow
"""

import asyncio
import json
import logging
import os
import random
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from azure.keyvault.secrets import SecretClient

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
from azure_haymaker.orchestrator.sp_manager import create_service_principal
from azure_haymaker.orchestrator.validation import validate_environment
from azure_haymaker.orchestrator.webhooks import (
    notify_execution_completed,
    notify_execution_failed,
    notify_execution_started,
)
from azure_haymaker.tracing import TraceContext
from azure_haymaker.tracing.instrumentation import add_span_attributes, traced_async

logger = logging.getLogger(__name__)

# Reference to executions dict (injected by main app)
executions: dict[str, dict[str, Any]] = {}


def set_executions_ref(exec_dict: dict[str, dict[str, Any]]) -> None:
    """Set reference to executions dictionary from main app."""
    global executions
    executions = exec_dict


async def run_scheduled_orchestration():
    """Run scheduled orchestration (triggered by cron)."""
    run_id = str(uuid4())
    logger.info(f"Scheduled execution triggered: run_id={run_id}")
    await run_orchestration(run_id)


@traced_async("run-orchestration")
async def run_orchestration(
    run_id: str,
    skip_validation: bool = False,
    scenario_names: list[str] | None = None,
    scenario_count: int | None = None,
    trace_context: TraceContext | None = None,
    tenant_config: dict[str, Any] | None = None,
):
    """Main orchestration workflow.

    Args:
        run_id: Unique execution run ID
        skip_validation: Skip environment validation (for testing)
        scenario_names: Specific scenarios to run (None = random selection)
        scenario_count: Number of scenarios to select (overrides config)
        trace_context: Optional trace context for distributed tracing
        tenant_config: Optional per-tenant config for multi-tenant execution.
                      Keys: tenant_id, subscription_id, credential, resource_group

    Phases:
    1. Validation: Verify environment
    2. Selection: Select scenarios
    3. Provisioning: Create SPs and deploy containers
    4. Monitoring: Monitor agent execution (8 hours)
    5. Cleanup: Verify and force cleanup
    6. Reporting: Generate report
    """
    if trace_context is None:
        trace_context = TraceContext.create_new(run_id=run_id)

    execution_report = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "status": "running",
        "phases": {},
        "trace_id": trace_context.trace_id,
    }
    executions[run_id] = execution_report

    from opentelemetry import trace as otel_trace

    current_span = otel_trace.get_current_span()
    if current_span.is_recording():
        add_span_attributes(
            current_span,
            **{
                "haymaker.run_id": run_id,
                "haymaker.trace_id": trace_context.trace_id,
            },
        )

    try:
        config = await load_config()

        orchestrator_tenant = os.getenv("AZURE_TENANT_ID", "unknown")

        if tenant_config:
            target_tenant = tenant_config.get("tenant_id", config.target_tenant_id)
            target_subscription = tenant_config.get(
                "subscription_id", config.target_subscription_id
            )
            mode = "multi-tenant"
            logger.info(
                f"[{run_id}] Multi-tenant execution for tenant {target_tenant[:8]}...",
                extra={
                    "run_id": run_id,
                    "target_tenant": target_tenant,
                    "target_subscription": target_subscription,
                    "mode": mode,
                },
            )
        else:
            target_tenant = config.target_tenant_id
            target_subscription = config.target_subscription_id
            mode = "cross-tenant" if config.is_cross_tenant else "single-tenant"
            logger.info(
                f"[{run_id}] Starting orchestration",
                extra={
                    "run_id": run_id,
                    "orchestrator_tenant": orchestrator_tenant,
                    "target_tenant": target_tenant,
                    "target_subscription": target_subscription,
                    "mode": mode,
                    "simulation_size": config.simulation_size.value,
                },
            )

            if config.is_cross_tenant:
                logger.info(
                    f"[{run_id}] Cross-tenant deployment: "
                    f"orchestrator tenant {orchestrator_tenant[:8]}... -> "
                    f"target tenant {target_tenant[:8]}..."
                )

        execution_report["tenant_config"] = {
            "target_tenant": target_tenant,
            "target_subscription": target_subscription,
            "mode": mode,
        }

        # ========================================================================
        # PHASE 1: VALIDATION
        # ========================================================================
        if not skip_validation:
            logger.info(f"[{run_id}] Phase 1: Validation")
            validation_result = await validate_environment(config)

            if not validation_result.overall_passed:
                logger.error(f"[{run_id}] Validation failed")
                execution_report["status"] = "failed"
                execution_report["failure_reason"] = "validation_failed"
                execution_report["phases"]["validation"] = {
                    "status": "failed",
                    "results": [r.model_dump() for r in validation_result.results],
                }
                return

            execution_report["phases"]["validation"] = {
                "status": "passed",
                "checks": [r.model_dump() for r in validation_result.results],
            }
            logger.info(f"[{run_id}] Validation passed")
        else:
            logger.warning(f"[{run_id}] Skipping validation (skip_validation=true)")
            execution_report["phases"]["validation"] = {
                "status": "skipped",
            }

        # ========================================================================
        # PHASE 2: SCENARIO SELECTION
        # ========================================================================
        logger.info(f"[{run_id}] Phase 2: Scenario Selection")

        if scenario_names:
            from azure_haymaker.models.config import SimulationSize

            all_scenarios = select_scenarios(SimulationSize.LARGE)
            scenarios = [s for s in all_scenarios if s.scenario_name in scenario_names]
            if not scenarios:
                logger.error(f"[{run_id}] No matching scenarios found for: {scenario_names}")
                execution_report["status"] = "failed"
                execution_report["failure_reason"] = "no_matching_scenarios"
                return
        else:
            if scenario_count:
                from azure_haymaker.models.config import SimulationSize

                all_scenarios = select_scenarios(SimulationSize.LARGE)
                scenarios = random.sample(all_scenarios, min(scenario_count, len(all_scenarios)))
            else:
                scenarios = select_scenarios(config.simulation_size)

        if not scenarios:
            logger.error(f"[{run_id}] No scenarios selected")
            execution_report["status"] = "failed"
            execution_report["failure_reason"] = "no_scenarios_selected"
            return

        execution_report["phases"]["selection"] = {
            "status": "completed",
            "scenario_count": len(scenarios),
            "scenarios": [s.scenario_name for s in scenarios],
        }
        logger.info(f"[{run_id}] Selected {len(scenarios)} scenarios")

        await notify_execution_started(
            run_id=run_id,
            scenarios=[s.scenario_name for s in scenarios],
            started_at=execution_report["started_at"],
        )

        # ========================================================================
        # PHASE 3: PROVISIONING
        # ========================================================================
        logger.info(f"[{run_id}] Phase 3: Provisioning")

        from azure_haymaker.utils.credentials import get_credential

        credential = get_credential()
        key_vault_client = SecretClient(vault_url=config.key_vault_url, credential=credential)

        sp_tasks = [
            create_service_principal(
                scenario_name=scenario.scenario_name,
                subscription_id=config.target_subscription_id,
                roles=["Contributor", "Reader"],
                key_vault_client=key_vault_client,
                config=config,
            )
            for scenario in scenarios
        ]
        sp_results = await asyncio.gather(*sp_tasks, return_exceptions=True)

        successful_sps = []
        failed_sps = []
        sp_errors = []
        for i, result in enumerate(sp_results):
            if isinstance(result, Exception):
                error_msg = f"{type(result).__name__}: {str(result)}"
                logger.warning(
                    f"[{run_id}] SP creation failed for {scenarios[i].scenario_name}: {error_msg}"
                )
                failed_sps.append(scenarios[i].scenario_name)
                sp_errors.append({"scenario": scenarios[i].scenario_name, "error": error_msg})
            else:
                successful_sps.append((scenarios[i], result))

        logger.info(f"[{run_id}] Created {len(successful_sps)}/{len(scenarios)} service principals")

        container_tasks = [
            deploy_container_app(scenario=scenario, sp=sp_details, config=config)
            for scenario, sp_details in successful_sps
        ]
        container_results = await asyncio.gather(*container_tasks, return_exceptions=True)

        successful_containers = []
        failed_containers = []
        container_errors = []
        for i, result in enumerate(container_results):
            if isinstance(result, Exception):
                error_msg = f"{type(result).__name__}: {str(result)}"
                logger.warning(f"[{run_id}] Container deployment failed: {error_msg}")
                failed_containers.append(successful_sps[i][0].scenario_name)
                container_errors.append(
                    {"scenario": successful_sps[i][0].scenario_name, "error": error_msg}
                )
            else:
                successful_containers.append(result)

        logger.info(
            f"[{run_id}] Deployed {len(successful_containers)}/{len(successful_sps)} containers"
        )

        execution_report["phases"]["provisioning"] = {
            "status": "completed",
            "service_principals": {
                "requested": len(scenarios),
                "created": len(successful_sps),
                "failed": len(failed_sps),
                "errors": sp_errors if sp_errors else None,
            },
            "container_apps": {
                "requested": len(successful_sps),
                "deployed": len(successful_containers),
                "failed": len(failed_containers),
                "errors": container_errors if container_errors else None,
            },
        }

        # ========================================================================
        # PHASE 4: MONITORING (8 hours)
        # ========================================================================
        logger.info(f"[{run_id}] Phase 4: Monitoring (8 hours)")
        container_manager = ContainerManager(config)

        monitoring_status = {
            "status_checks": [],
            "log_messages": 0,
            "resource_count": len(successful_containers),
        }

        for check_num in range(32):  # 8 hours * 4 checks/hour
            await asyncio.sleep(900)  # 15 minutes

            running_count = 0
            completed_count = 0
            failed_count = 0

            for container_id in successful_containers:
                try:
                    container_name = container_id.split("/")[-1]
                    status = await container_manager.get_status(container_name)
                    if status in ["Running", "Processing"]:
                        running_count += 1
                    elif status == "Terminated":
                        completed_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.warning(f"[{run_id}] Failed to check container status: {e}")
                    failed_count += 1

            monitoring_status["status_checks"].append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "running_count": running_count,
                    "completed_count": completed_count,
                    "failed_count": failed_count,
                }
            )

            logger.info(
                f"[{run_id}] Status check {check_num + 1}/32: "
                f"running={running_count}, completed={completed_count}, failed={failed_count}"
            )

        execution_report["phases"]["monitoring"] = monitoring_status
        logger.info(f"[{run_id}] Monitoring completed")

        # ========================================================================
        # PHASE 5: CLEANUP
        # ========================================================================
        logger.info(f"[{run_id}] Phase 5: Cleanup Verification")
        remaining_resources = await query_managed_resources(
            subscription_id=config.target_subscription_id,
            run_id=run_id,
        )

        logger.info(f"[{run_id}] Found {len(remaining_resources)} remaining resources")

        if remaining_resources:
            logger.warning(f"[{run_id}] Starting forced cleanup")
            cleanup_report = await force_delete_resources(
                resources=remaining_resources,
                sp_details=[sp for _, sp in successful_sps],
                kv_client=key_vault_client,
                subscription_id=config.target_subscription_id,
            )

            execution_report["phases"]["cleanup"] = {
                "status": "completed",
                "verification_found": len(remaining_resources),
                "deleted": cleanup_report.total_resources_deleted,
                "failed": len([d for d in cleanup_report.deletions if d.status == "failed"]),
                "sp_deleted": len(cleanup_report.service_principals_deleted),
            }
        else:
            execution_report["phases"]["cleanup"] = {
                "status": "verified",
                "verification_found": 0,
                "deleted": 0,
                "failed": 0,
            }

        # ========================================================================
        # PHASE 6: REPORTING
        # ========================================================================
        logger.info(f"[{run_id}] Phase 6: Report Generation")
        execution_report["status"] = "completed"
        execution_report["ended_at"] = datetime.now(UTC).isoformat()

        try:
            from azure.storage.blob import BlobServiceClient

            blob_service_client = BlobServiceClient(
                account_url=config.storage.account_url,
                credential=credential,
            )
            container_client = blob_service_client.get_container_client("execution-reports")
            blob_client = container_client.get_blob_client(f"{run_id}/report.json")

            blob_client.upload_blob(
                json.dumps(execution_report, indent=2),
                overwrite=True,
            )
            execution_report["report_url"] = blob_client.url
            logger.info(f"[{run_id}] Report stored at {blob_client.url}")
        except Exception as e:
            logger.warning(f"[{run_id}] Failed to store report: {e}")
            execution_report["report_url"] = None

        logger.info(f"[{run_id}] Orchestration completed successfully")

        started = datetime.fromisoformat(execution_report["started_at"])
        ended = datetime.fromisoformat(execution_report["ended_at"])
        duration_hours = (ended - started).total_seconds() / 3600

        await notify_execution_completed(
            run_id=run_id,
            duration_hours=round(duration_hours, 2),
            scenarios_count=len(scenarios),
        )

    except Exception as e:
        logger.error(f"[{run_id}] Orchestration failed: {e}", exc_info=True)
        execution_report["status"] = "failed"
        execution_report["error"] = str(e)
        execution_report["ended_at"] = datetime.now(UTC).isoformat()

        await notify_execution_failed(
            run_id=run_id,
            error=str(e),
            failed_at=execution_report["ended_at"],
        )


__all__ = [
    "run_scheduled_orchestration",
    "run_orchestration",
    "set_executions_ref",
]
