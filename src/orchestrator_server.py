"""Simple FastAPI orchestrator for Azure HayMaker.

NO AZURE FUNCTIONS. NO DURABLE FUNCTIONS. JUST WORKING CODE.

This replaces the Azure Functions implementation with a simple REST API
that can run anywhere - locally, Docker, or Azure Container Apps.
"""

import asyncio
import json
import logging
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, HTTPException, Query

from azure_haymaker.models.execution import (
    AnalyticsSummary,
    ExecutionCounts,
    ScenarioStats,
)
from azure_haymaker.orchestrator.cleanup import (
    force_delete_resources,
    query_managed_resources,
)
from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.container_manager import (
    ContainerManager,
    deploy_container_app,
)
from azure_haymaker.orchestrator.cost_query import CostSummary, get_cost_summary
from azure_haymaker.orchestrator.scenario_selector import select_scenarios
from azure_haymaker.orchestrator.sp_manager import create_service_principal
from azure_haymaker.orchestrator.validation import validate_environment
from azure_haymaker.orchestrator.webhooks import (
    notify_execution_completed,
    notify_execution_failed,
    notify_execution_started,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler
scheduler = AsyncIOScheduler()

# Track running executions
executions: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - starts/stops scheduler."""
    logger.info("Starting orchestrator server")
    scheduler.start()

    # Schedule orchestration runs: 4x daily (00:00, 06:00, 12:00, 18:00 UTC)
    scheduler.add_job(
        run_scheduled_orchestration,
        "cron",
        hour="0,6,12,18",
        id="haymaker_orchestration",
    )
    logger.info("Scheduled orchestration runs: 00:00, 06:00, 12:00, 18:00 UTC")

    yield

    logger.info("Shutting down orchestrator server")
    scheduler.shutdown()


app = FastAPI(title="Azure HayMaker Orchestrator", lifespan=lifespan)


# ==============================================================================
# API ENDPOINTS
# ==============================================================================


@app.get("/")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "azure-haymaker-orchestrator",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/metrics")
async def metrics():
    """Get execution metrics."""
    return {
        "executions_total": len(executions),
        "executions_running": len([e for e in executions.values() if e["status"] == "running"]),
        "executions_completed": len([e for e in executions.values() if e["status"] == "completed"]),
        "executions_failed": len([e for e in executions.values() if e["status"] == "failed"]),
    }


@app.get("/api/executions")
async def list_executions():
    """List all executions."""
    return {"executions": list(executions.values())}


@app.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution details."""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    return executions[execution_id]


@app.get("/api/executions/{run_id}/cost", response_model=CostSummary)
async def get_execution_cost(run_id: str):
    """Get cost summary for an execution run.

    Queries Azure Cost Management for costs associated with this run,
    filtered by AzureHayMaker-managed=true and RunId={run_id} tags.

    Note: Azure Cost Management has approximately 24 hours delay before
    cost data becomes available. Recent runs may return empty or partial data.

    Args:
        run_id: Execution run ID

    Returns:
        CostSummary with cost breakdown by resource type and scenario

    Raises:
        HTTPException 404: If run_id is not found in executions
        HTTPException 500: If cost query fails
    """
    # Verify the run exists
    if run_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    try:
        config = await load_config()
        cost_summary = await get_cost_summary(
            subscription_id=config.target_subscription_id,
            run_id=run_id,
        )
        return cost_summary
    except Exception as e:
        logger.error(f"Failed to get cost summary for run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query costs: {str(e)}",
        ) from e


@app.post("/api/execute")
async def execute(request: dict[str, Any] | None = None):
    """Manually trigger an orchestration run."""
    run_id = str(uuid4())
    skip_validation = request.get("skip_validation", False) if request else False
    logger.info(f"Manual execution triggered: run_id={run_id}, skip_validation={skip_validation}")

    # Start orchestration in background
    asyncio.create_task(run_orchestration(run_id, skip_validation=skip_validation))

    return {
        "execution_id": run_id,
        "status": "started",
        "started_at": datetime.now(UTC).isoformat(),
    }


@app.post("/api/validate")
async def validate():
    """Validate environment configuration."""
    try:
        config = await load_config()
        result = await validate_environment(config)
        return {
            "overall_passed": result.overall_passed,
            "results": [r.model_dump() for r in result.results],
        }
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/scenarios")
async def list_scenarios():
    """List available scenarios (small simulation size)."""
    try:
        from azure_haymaker.models.config import SimulationSize

        scenarios = select_scenarios(SimulationSize.SMALL)
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
        logger.error(f"Failed to list scenarios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/analytics", response_model=AnalyticsSummary)
async def get_analytics(
    period: Literal["7d", "30d", "90d"] = Query(
        default="30d",
        description="Time period for analytics (7d, 30d, or 90d)",
    ),
) -> AnalyticsSummary:
    """Get analytics summary for the dashboard.

    Queries Table Storage for execution history and aggregates statistics
    for the specified time period.

    Args:
        period: Time period to analyze (7d, 30d, or 90d)

    Returns:
        AnalyticsSummary with execution counts, success rate, and top scenarios
    """
    try:
        # Parse period to days
        period_days = {"7d": 7, "30d": 30, "90d": 90}[period]
        cutoff_date = datetime.now(UTC) - timedelta(days=period_days)

        # Get Table Storage configuration from environment
        table_storage_account = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        if not table_storage_account:
            logger.warning("TABLE_STORAGE_ACCOUNT_NAME not set, returning empty analytics")
            return AnalyticsSummary(
                period=period,
                executions=ExecutionCounts(total=0, succeeded=0, failed=0),
                success_rate=0.0,
                avg_duration_hours=0.0,
                top_scenarios=[],
            )

        # Connect to Table Storage using managed identity
        credential = DefaultAzureCredential()
        table_service = TableServiceClient(
            endpoint=f"https://{table_storage_account}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service.get_table_client("ExecutionRuns")

        # Query execution history
        # OData filter for records after cutoff date
        # Azure Table Storage OData requires datetime'...' prefix for date comparisons
        cutoff_iso = cutoff_date.isoformat()
        query_filter = f"CreatedAt ge datetime'{cutoff_iso}'"

        # Aggregate statistics
        total_executions = 0
        succeeded_executions = 0
        failed_executions = 0
        total_duration_hours = 0.0
        duration_count = 0
        scenario_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"count": 0, "succeeded": 0, "failed": 0}
        )

        # Track seen execution IDs to avoid double-counting
        # (Table Storage may have multiple rows per execution)
        seen_execution_ids: set[str] = set()

        try:
            entities = table_client.query_entities(query_filter=query_filter)
            for entity in entities:
                execution_id = entity.get("PartitionKey", "")

                # Skip if we've already counted this execution
                if execution_id in seen_execution_ids:
                    continue
                seen_execution_ids.add(execution_id)

                total_executions += 1

                # Count by status
                status = entity.get("Status", "")
                if status in ("completed", "COMPLETED"):
                    succeeded_executions += 1
                elif status in ("failed", "FAILED", "error", "ERROR"):
                    failed_executions += 1

                # Calculate duration if we have timestamps
                created_at_str = entity.get("CreatedAt")
                completed_at_str = entity.get("CompletedAt")
                if created_at_str and completed_at_str:
                    try:
                        created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                        completed_at = datetime.fromisoformat(
                            completed_at_str.replace("Z", "+00:00")
                        )
                        duration = (completed_at - created_at).total_seconds() / 3600
                        if duration > 0:
                            total_duration_hours += duration
                            duration_count += 1
                    except (ValueError, TypeError) as e:
                        logger.debug(
                            f"Failed to parse timestamps for execution {execution_id}: {e}"
                        )

                # Track scenario statistics
                scenarios_json = entity.get("Scenarios", "[]")
                try:
                    scenarios = json.loads(scenarios_json)
                    for scenario_name in scenarios:
                        scenario_stats[scenario_name]["count"] += 1
                        if status in ("completed", "COMPLETED"):
                            scenario_stats[scenario_name]["succeeded"] += 1
                        elif status in ("failed", "FAILED", "error", "ERROR"):
                            scenario_stats[scenario_name]["failed"] += 1
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(
                        f"Failed to parse scenarios JSON for execution {execution_id}: {e}"
                    )

        except Exception as e:
            logger.warning(f"Failed to query Table Storage: {e}")
            # Return empty analytics if table doesn't exist or query fails
            return AnalyticsSummary(
                period=period,
                executions=ExecutionCounts(total=0, succeeded=0, failed=0),
                success_rate=0.0,
                avg_duration_hours=0.0,
                top_scenarios=[],
            )

        # Calculate success rate
        success_rate = (
            succeeded_executions / total_executions if total_executions > 0 else 0.0
        )

        # Calculate average duration
        avg_duration = total_duration_hours / duration_count if duration_count > 0 else 0.0

        # Build top scenarios list (top 10 by execution count)
        top_scenarios = sorted(
            [
                ScenarioStats(
                    name=name,
                    count=stats["count"],
                    success_rate=(
                        stats["succeeded"] / stats["count"]
                        if stats["count"] > 0
                        else 0.0
                    ),
                )
                for name, stats in scenario_stats.items()
            ],
            key=lambda s: s.count,
            reverse=True,
        )[:10]

        return AnalyticsSummary(
            period=period,
            executions=ExecutionCounts(
                total=total_executions,
                succeeded=succeeded_executions,
                failed=failed_executions,
            ),
            success_rate=round(success_rate, 4),
            avg_duration_hours=round(avg_duration, 2),
            top_scenarios=top_scenarios,
        )

    except Exception as e:
        logger.error(f"Failed to get analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==============================================================================
# ORCHESTRATION LOGIC
# ==============================================================================


async def run_scheduled_orchestration():
    """Run scheduled orchestration (triggered by cron)."""
    run_id = str(uuid4())
    logger.info(f"Scheduled execution triggered: run_id={run_id}")
    await run_orchestration(run_id)


async def run_orchestration(run_id: str, skip_validation: bool = False):
    """Main orchestration workflow.

    Phases:
    1. Validation: Verify environment
    2. Selection: Select scenarios
    3. Provisioning: Create SPs and deploy containers
    4. Monitoring: Monitor agent execution (8 hours)
    5. Cleanup: Verify and force cleanup
    6. Reporting: Generate report
    """
    execution_report = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "status": "running",
        "phases": {},
    }
    executions[run_id] = execution_report

    try:
        # ========================================================================
        # PHASE 1: VALIDATION (can be skipped for testing)
        # ========================================================================
        if not skip_validation:
            logger.info(f"[{run_id}] Phase 1: Validation")
            config = await load_config()
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
            config = await load_config()
            execution_report["phases"]["validation"] = {
                "status": "skipped",
            }

        # ========================================================================
        # PHASE 2: SCENARIO SELECTION
        # ========================================================================
        logger.info(f"[{run_id}] Phase 2: Scenario Selection")
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

        # Send webhook notification for execution started
        await notify_execution_started(
            run_id=run_id,
            scenarios=[s.scenario_name for s in scenarios],
            started_at=execution_report["started_at"],
        )

        # ========================================================================
        # PHASE 3: PROVISIONING
        # ========================================================================
        logger.info(f"[{run_id}] Phase 3: Provisioning")
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        key_vault_client = SecretClient(vault_url=config.key_vault_url, credential=credential)

        # Create service principals in parallel
        sp_tasks = [
            create_service_principal(
                scenario_name=scenario.scenario_name,
                subscription_id=config.target_subscription_id,
                roles=["Contributor", "Reader"],
                key_vault_client=key_vault_client,
            )
            for scenario in scenarios
        ]
        sp_results = await asyncio.gather(*sp_tasks, return_exceptions=True)

        # Filter successful SPs
        successful_sps = []
        failed_sps = []
        sp_errors = []  # Track errors for debugging
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

        # Deploy containers in parallel
        container_tasks = [
            deploy_container_app(scenario=scenario, sp=sp_details, config=config)
            for scenario, sp_details in successful_sps
        ]
        container_results = await asyncio.gather(*container_tasks, return_exceptions=True)

        # Filter successful containers
        successful_containers = []
        failed_containers = []
        container_errors = []  # Track errors for debugging
        for i, result in enumerate(container_results):
            if isinstance(result, Exception):
                error_msg = f"{type(result).__name__}: {str(result)}"
                logger.warning(f"[{run_id}] Container deployment failed: {error_msg}")
                failed_containers.append(successful_sps[i][0].scenario_name)
                container_errors.append({"scenario": successful_sps[i][0].scenario_name, "error": error_msg})
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
                "errors": sp_errors if sp_errors else None,  # Surface actual errors in API
            },
            "container_apps": {
                "requested": len(successful_sps),
                "deployed": len(successful_containers),
                "failed": len(failed_containers),
                "errors": container_errors if container_errors else None,  # Surface actual errors
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

        # Monitor for 8 hours, checking every 15 minutes
        for check_num in range(32):  # 8 hours * 4 checks/hour = 32 checks
            await asyncio.sleep(900)  # 15 minutes

            # Check container statuses
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
                f"[{run_id}] Status check {check_num+1}/32: "
                f"running={running_count}, completed={completed_count}, failed={failed_count}"
            )

        execution_report["phases"]["monitoring"] = monitoring_status
        logger.info(f"[{run_id}] Monitoring completed")

        # ========================================================================
        # PHASE 5: CLEANUP VERIFICATION & FORCED CLEANUP
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

        # Store report to blob storage (if configured)
        try:
            from azure.storage.blob import BlobServiceClient

            blob_service_client = BlobServiceClient(
                account_url=config.storage.account_url,
                credential=credential,
            )
            container_client = blob_service_client.get_container_client("execution-reports")
            blob_client = container_client.get_blob_client(f"{run_id}/report.json")

            import json

            await blob_client.upload_blob(
                json.dumps(execution_report, indent=2),
                overwrite=True,
            )
            execution_report["report_url"] = blob_client.url
            logger.info(f"[{run_id}] Report stored at {blob_client.url}")
        except Exception as e:
            logger.warning(f"[{run_id}] Failed to store report: {e}")
            execution_report["report_url"] = None

        logger.info(f"[{run_id}] Orchestration completed successfully")

        # Calculate duration and send completion webhook
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

        # Send failure webhook notification
        await notify_execution_failed(
            run_id=run_id,
            error=str(e),
            failed_at=execution_report["ended_at"],
        )


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
