"""Simple FastAPI orchestrator for Azure HayMaker.

NO AZURE FUNCTIONS. NO DURABLE FUNCTIONS. JUST WORKING CODE.

This replaces the Azure Functions implementation with a simple REST API
that can run anywhere - locally, Docker, or Azure Container Apps.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException

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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        for i, result in enumerate(sp_results):
            if isinstance(result, Exception):
                logger.warning(
                    f"[{run_id}] SP creation failed for {scenarios[i].scenario_name}: {result}"
                )
                failed_sps.append(scenarios[i].scenario_name)
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
        for i, result in enumerate(container_results):
            if isinstance(result, Exception):
                logger.warning(f"[{run_id}] Container deployment failed: {result}")
                failed_containers.append(successful_sps[i][0].scenario_name)
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
            },
            "container_apps": {
                "requested": len(successful_sps),
                "deployed": len(successful_containers),
                "failed": len(failed_containers),
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

    except Exception as e:
        logger.error(f"[{run_id}] Orchestration failed: {e}", exc_info=True)
        execution_report["status"] = "failed"
        execution_report["error"] = str(e)
        execution_report["ended_at"] = datetime.now(UTC).isoformat()


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
