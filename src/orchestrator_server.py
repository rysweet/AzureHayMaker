"""Simple FastAPI orchestrator for Azure HayMaker.

NO AZURE FUNCTIONS. NO DURABLE FUNCTIONS. JUST WORKING CODE.

This replaces the Azure Functions implementation with a simple REST API
that can run anywhere - locally, Docker, or Azure Container Apps.
"""

import asyncio
import contextlib
import json
import logging
import os
import random
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from croniter import croniter
from fastapi import Depends, FastAPI, HTTPException, Query

from azure_haymaker.models.execution import (
    AnalyticsSummary,
    ExecutionCounts,
    ScenarioStats,
)
from azure_haymaker.models.schedule import (
    Schedule,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
)
from azure_haymaker.orchestrator.auth import require_auth
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

# Auth dependency type alias (module-level singleton to satisfy B008)
AuthDep = Annotated[dict, Depends(require_auth)]

# Global scheduler
scheduler = AsyncIOScheduler()

# Track running executions
executions: dict[str, dict[str, Any]] = {}

# Schedule table client (initialized on startup)
_schedule_table_client = None
SCHEDULE_TABLE_NAME = "Schedules"
SCHEDULE_PARTITION_KEY = "schedule"


def _get_schedule_table_client():
    """Get or create the schedule table client.

    Returns:
        TableClient for schedule storage

    Raises:
        RuntimeError: If table storage is not configured
    """
    global _schedule_table_client
    if _schedule_table_client is None:
        table_storage_account = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        if not table_storage_account:
            raise RuntimeError(
                "TABLE_STORAGE_ACCOUNT_NAME environment variable not set. "
                "Schedule storage requires Azure Table Storage configuration."
            )
        account_url = f"https://{table_storage_account}.table.core.windows.net"
        credential = DefaultAzureCredential()
        table_service = TableServiceClient(endpoint=account_url, credential=credential)
        # Create table if not exists
        try:
            table_service.create_table_if_not_exists(SCHEDULE_TABLE_NAME)
        except Exception as e:
            logger.warning(f"Could not ensure table exists: {e}")
        _schedule_table_client = table_service.get_table_client(SCHEDULE_TABLE_NAME)
    return _schedule_table_client


def _validate_cron_expression(cron_expr: str) -> bool:
    """Validate a cron expression using croniter.

    Args:
        cron_expr: Cron expression string (5 or 6 fields supported).
                   6-field format: second minute hour day month weekday
                   5-field format: minute hour day month weekday (seconds default to 0)

    Returns:
        True if valid, raises ValueError otherwise

    Raises:
        ValueError: If the cron expression is invalid
    """
    try:
        # APScheduler uses 6-field cron (second minute hour day month weekday)
        # croniter uses 5-field by default, so we need to handle this
        parts = cron_expr.strip().split()
        if len(parts) == 6:
            # Remove seconds field for croniter validation
            five_field_cron = " ".join(parts[1:])
        elif len(parts) == 5:
            five_field_cron = cron_expr
        else:
            raise ValueError(f"Invalid cron expression: expected 5 or 6 fields, got {len(parts)}")
        # Validate with croniter
        croniter(five_field_cron)
        return True
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid cron expression '{cron_expr}': {e}") from e


def _schedule_to_entity(schedule: Schedule) -> dict[str, Any]:
    """Convert Schedule model to Table Storage entity.

    Args:
        schedule: Schedule model instance

    Returns:
        Dictionary suitable for Table Storage
    """
    return {
        "PartitionKey": SCHEDULE_PARTITION_KEY,
        "RowKey": schedule.id,
        "Name": schedule.name,
        "CronExpression": schedule.cron_expression,
        "Scenarios": json.dumps(schedule.scenarios) if schedule.scenarios else None,
        "ScenarioCount": schedule.scenario_count,
        "Enabled": schedule.enabled,
        "CreatedAt": schedule.created_at.isoformat(),
    }


def _entity_to_schedule(entity: dict[str, Any]) -> Schedule:
    """Convert Table Storage entity to Schedule model.

    Args:
        entity: Table Storage entity dictionary

    Returns:
        Schedule model instance
    """
    scenarios_json = entity.get("Scenarios")
    scenarios = json.loads(scenarios_json) if scenarios_json else None

    created_at_str = entity.get("CreatedAt", "")
    if created_at_str:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    else:
        created_at = datetime.now(UTC)

    return Schedule(
        id=entity["RowKey"],
        name=entity["Name"],
        cron_expression=entity["CronExpression"],
        scenarios=scenarios,
        scenario_count=entity.get("ScenarioCount", 5),
        enabled=entity.get("Enabled", True),
        created_at=created_at,
    )


def _get_next_run_time(cron_expr: str) -> str | None:
    """Get the next run time for a cron expression.

    Args:
        cron_expr: Cron expression string

    Returns:
        ISO format string of next run time, or None if invalid
    """
    try:
        parts = cron_expr.strip().split()
        five_field_cron = " ".join(parts[1:]) if len(parts) == 6 else cron_expr
        cron = croniter(five_field_cron, datetime.now(UTC))
        next_time = cron.get_next(datetime)
        return next_time.isoformat()
    except Exception:
        return None


def _schedule_to_response(schedule: Schedule) -> ScheduleResponse:
    """Convert Schedule model to ScheduleResponse with next run time.

    Args:
        schedule: Schedule model instance

    Returns:
        ScheduleResponse with computed next_run field
    """
    next_run = _get_next_run_time(schedule.cron_expression) if schedule.enabled else None
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        cron_expression=schedule.cron_expression,
        scenarios=schedule.scenarios,
        scenario_count=schedule.scenario_count,
        enabled=schedule.enabled,
        created_at=schedule.created_at,
        next_run=next_run,
    )


async def _run_scheduled_job(schedule_id: str) -> None:
    """Execute orchestration for a specific schedule.

    Args:
        schedule_id: ID of the schedule triggering this run
    """
    logger.info(f"Schedule {schedule_id} triggered orchestration")
    try:
        # Load schedule to get parameters
        table_client = _get_schedule_table_client()
        entity = table_client.get_entity(
            partition_key=SCHEDULE_PARTITION_KEY,
            row_key=schedule_id,
        )
        schedule = _entity_to_schedule(entity)

        if not schedule.enabled:
            logger.info(f"Schedule {schedule_id} is disabled, skipping")
            return

        run_id = str(uuid4())
        logger.info(
            f"Starting scheduled orchestration: run_id={run_id}, "
            f"schedule={schedule.name}, scenarios={schedule.scenarios}, "
            f"scenario_count={schedule.scenario_count}"
        )

        # Run orchestration with schedule parameters
        await run_orchestration(
            run_id=run_id,
            skip_validation=False,
            scenario_names=schedule.scenarios,
            scenario_count=schedule.scenario_count,
        )

    except ResourceNotFoundError:
        logger.error(f"Schedule {schedule_id} not found, removing job")
        with contextlib.suppress(Exception):
            scheduler.remove_job(f"schedule_{schedule_id}")
    except Exception as e:
        logger.error(f"Failed to run scheduled job {schedule_id}: {e}", exc_info=True)


def _add_scheduler_job(schedule: Schedule) -> None:
    """Add or update APScheduler job for a schedule.

    Args:
        schedule: Schedule model instance
    """
    job_id = f"schedule_{schedule.id}"

    # Remove existing job if present
    with contextlib.suppress(Exception):
        scheduler.remove_job(job_id)

    if not schedule.enabled:
        logger.info(f"Schedule {schedule.id} is disabled, not adding job")
        return

    try:
        # Parse cron expression (APScheduler uses 6 fields)
        parts = schedule.cron_expression.strip().split()
        if len(parts) == 6:
            second, minute, hour, day, month, day_of_week = parts
        elif len(parts) == 5:
            second = "0"
            minute, hour, day, month, day_of_week = parts
        else:
            logger.error(f"Invalid cron expression for schedule {schedule.id}")
            return

        trigger = CronTrigger(
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )

        scheduler.add_job(
            _run_scheduled_job,
            trigger,
            args=[schedule.id],
            id=job_id,
            name=f"Schedule: {schedule.name}",
            replace_existing=True,
        )
        logger.info(f"Added scheduler job for schedule {schedule.id}: {schedule.name}")
    except Exception as e:
        logger.error(f"Failed to add scheduler job for {schedule.id}: {e}")


def _remove_scheduler_job(schedule_id: str) -> None:
    """Remove APScheduler job for a schedule.

    Args:
        schedule_id: Schedule ID
    """
    job_id = f"schedule_{schedule_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Removed scheduler job: {job_id}")
    except Exception as e:
        logger.debug(f"Job {job_id} not found or already removed: {e}")


async def _load_schedules_on_startup() -> None:
    """Load all enabled schedules from storage and add to scheduler."""
    try:
        table_client = _get_schedule_table_client()
        query = f"PartitionKey eq '{SCHEDULE_PARTITION_KEY}'"

        for entity in table_client.query_entities(query_filter=query):
            try:
                schedule = _entity_to_schedule(entity)
                if schedule.enabled:
                    _add_scheduler_job(schedule)
            except Exception as e:
                logger.warning(f"Failed to load schedule {entity.get('RowKey')}: {e}")

        logger.info("Loaded schedules from storage")
    except Exception as e:
        logger.warning(f"Could not load schedules from storage: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - starts/stops scheduler."""
    logger.info("Starting orchestrator server")
    scheduler.start()

    # Schedule default orchestration runs: 4x daily (00:00, 06:00, 12:00, 18:00 UTC)
    scheduler.add_job(
        run_scheduled_orchestration,
        "cron",
        hour="0,6,12,18",
        id="haymaker_orchestration",
    )
    logger.info("Scheduled default orchestration runs: 00:00, 06:00, 12:00, 18:00 UTC")

    # Load user-defined schedules from storage
    await _load_schedules_on_startup()

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


@app.get("/api/status")
async def status(_: AuthDep):
    """Get orchestrator status. Requires authentication."""
    running = [e for e in executions.values() if e["status"] == "running"]
    return {
        "status": "running" if running else "idle",
        "service": "azure-haymaker-orchestrator",
        "timestamp": datetime.now(UTC).isoformat(),
        "executions_active": len(running),
        "executions_total": len(executions),
    }


@app.get("/api/metrics")
async def metrics(_: AuthDep):
    """Get execution metrics. Requires authentication."""
    return {
        "executions_total": len(executions),
        "executions_running": len([e for e in executions.values() if e["status"] == "running"]),
        "executions_completed": len([e for e in executions.values() if e["status"] == "completed"]),
        "executions_failed": len([e for e in executions.values() if e["status"] == "failed"]),
    }


@app.get("/api/executions")
async def list_executions(_: AuthDep):
    """List all executions. Requires authentication."""
    return {"executions": list(executions.values())}


@app.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str, _: AuthDep):
    """Get execution details. Requires authentication."""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    return executions[execution_id]


@app.get("/api/executions/{run_id}/cost", response_model=CostSummary)
async def get_execution_cost(run_id: str, _: AuthDep):
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
async def execute(_: AuthDep, request: dict[str, Any] | None = None):
    """Manually trigger an orchestration run. Requires authentication."""
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
async def validate(_: AuthDep):
    """Validate environment configuration. Requires authentication."""
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
async def list_scenarios(_: AuthDep):
    """List available scenarios (small simulation size). Requires authentication."""
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


@app.get("/api/resources")
async def list_resources(
    _: AuthDep,
    execution_id: str | None = Query(None, description="Filter by execution ID"),
    scenario: str | None = Query(None, description="Filter by scenario name"),
    status: str | None = Query(None, description="Filter by status (created/deleted)"),
    limit: int = Query(100, description="Maximum number of results"),
):
    """List all HayMaker-managed resources in the tenant. Requires authentication.

    Queries Azure Resource Graph for all resources tagged with AzureHayMaker-managed=true.

    Args:
        execution_id: Optional filter by execution ID
        scenario: Optional filter by scenario name
        status: Optional filter by status
        limit: Maximum results (default 100)

    Returns:
        List of resources with metadata
    """
    try:
        config = await load_config()
        resources = await query_managed_resources(
            subscription_id=config.target_subscription_id,
            run_id=execution_id if execution_id else None,
        )

        # Apply filters
        filtered_resources = resources
        if scenario:
            filtered_resources = [
                r for r in filtered_resources if scenario.lower() in r.name.lower()
            ]
        if status:
            # Status filter not implemented in query_managed_resources yet
            pass

        # Limit results
        filtered_resources = filtered_resources[:limit]

        # Convert to response format
        return {
            "resources": [
                {
                    "id": r.resource_id,
                    "name": r.name,
                    "type": r.resource_type,
                    "resourceGroup": r.resource_group,
                    "location": r.location,
                    "tags": r.tags,
                }
                for r in filtered_resources
            ],
            "count": len(filtered_resources),
            "total_found": len(resources),
        }
    except Exception as e:
        logger.error(f"Failed to list resources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/analytics", response_model=AnalyticsSummary)
async def get_analytics(
    _: AuthDep,
    period: Literal["7d", "30d", "90d"] = Query(
        default="30d",
        description="Time period for analytics (7d, 30d, or 90d)",
    ),
) -> AnalyticsSummary:
    """Get analytics summary for the dashboard. Requires authentication.

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
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
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
        success_rate = succeeded_executions / total_executions if total_executions > 0 else 0.0

        # Calculate average duration
        avg_duration = total_duration_hours / duration_count if duration_count > 0 else 0.0

        # Build top scenarios list (top 10 by execution count)
        top_scenarios = sorted(
            [
                ScenarioStats(
                    name=name,
                    count=stats["count"],
                    success_rate=(
                        stats["succeeded"] / stats["count"] if stats["count"] > 0 else 0.0
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
# SCHEDULE API ENDPOINTS
# ==============================================================================


@app.post("/api/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(request: ScheduleCreate, _: AuthDep):
    """Create a new execution schedule. Requires authentication.

    Creates a schedule that will trigger orchestration runs based on a cron expression.
    The schedule is persisted to Azure Table Storage and an APScheduler job is created.

    Args:
        request: Schedule creation request with name, cron expression, and options

    Returns:
        Created schedule with generated ID and next run time

    Raises:
        HTTPException: 400 if cron expression is invalid, 500 on storage errors
    """
    try:
        # Validate cron expression
        _validate_cron_expression(request.cron_expression)

        # Create schedule model
        schedule = Schedule(
            name=request.name,
            cron_expression=request.cron_expression,
            scenarios=request.scenarios,
            scenario_count=request.scenario_count,
            enabled=request.enabled,
        )

        # Persist to Table Storage
        table_client = _get_schedule_table_client()
        entity = _schedule_to_entity(schedule)
        table_client.create_entity(entity=entity)

        # Add to APScheduler if enabled
        if schedule.enabled:
            _add_scheduler_job(schedule)

        logger.info(f"Created schedule: {schedule.id} - {schedule.name}")
        return _schedule_to_response(schedule)

    except ValueError as e:
        logger.warning(f"Invalid schedule request: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        logger.error(f"Storage not configured: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {e}") from e


@app.get("/api/schedules", response_model=list[ScheduleResponse])
async def list_schedules(_: AuthDep):
    """List all execution schedules. Requires authentication.

    Returns:
        List of all schedules with their current status and next run times
    """
    try:
        table_client = _get_schedule_table_client()
        query = f"PartitionKey eq '{SCHEDULE_PARTITION_KEY}'"

        schedules = []
        for entity in table_client.query_entities(query_filter=query):
            try:
                schedule = _entity_to_schedule(entity)
                schedules.append(_schedule_to_response(schedule))
            except Exception as e:
                logger.warning(f"Failed to parse schedule entity: {e}")
                continue

        # Sort by created_at descending
        schedules.sort(key=lambda s: s.created_at, reverse=True)
        return schedules

    except RuntimeError as e:
        logger.error(f"Storage not configured: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to list schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {e}") from e


@app.get("/api/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: str, _: AuthDep):
    """Get a specific schedule by ID. Requires authentication.

    Args:
        schedule_id: Unique schedule identifier

    Returns:
        Schedule details with next run time

    Raises:
        HTTPException: 404 if schedule not found
    """
    try:
        table_client = _get_schedule_table_client()
        entity = table_client.get_entity(
            partition_key=SCHEDULE_PARTITION_KEY,
            row_key=schedule_id,
        )
        schedule = _entity_to_schedule(entity)
        return _schedule_to_response(schedule)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}") from e
    except RuntimeError as e:
        logger.error(f"Storage not configured: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {e}") from e


@app.put("/api/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: str, request: ScheduleUpdate, _: AuthDep):
    """Update an existing schedule. Requires authentication.

    Allows partial updates - only provided fields will be modified.
    If the cron_expression is changed, the APScheduler job will be re-scheduled.

    Args:
        schedule_id: Unique schedule identifier
        request: Schedule update request with optional fields

    Returns:
        Updated schedule with next run time

    Raises:
        HTTPException: 400 if cron expression is invalid, 404 if not found
    """
    try:
        table_client = _get_schedule_table_client()

        # Get existing schedule
        try:
            entity = table_client.get_entity(
                partition_key=SCHEDULE_PARTITION_KEY,
                row_key=schedule_id,
            )
        except ResourceNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}") from e

        schedule = _entity_to_schedule(entity)

        # Track if cron expression changes (need to re-schedule job)
        cron_changed = False

        # Apply partial updates
        if request.name is not None:
            schedule.name = request.name
        if request.cron_expression is not None:
            _validate_cron_expression(request.cron_expression)
            cron_changed = schedule.cron_expression != request.cron_expression
            schedule.cron_expression = request.cron_expression
        if request.scenarios is not None:
            schedule.scenarios = request.scenarios
        if request.scenario_count is not None:
            schedule.scenario_count = request.scenario_count
        if request.enabled is not None:
            cron_changed = cron_changed or (schedule.enabled != request.enabled)
            schedule.enabled = request.enabled

        # Update in Table Storage
        updated_entity = _schedule_to_entity(schedule)
        table_client.update_entity(entity=updated_entity, mode="replace")

        # Re-schedule APScheduler job if cron or enabled state changed
        if cron_changed:
            _add_scheduler_job(schedule)

        logger.info(f"Updated schedule: {schedule.id} - {schedule.name}")
        return _schedule_to_response(schedule)

    except ValueError as e:
        logger.warning(f"Invalid schedule update request: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Storage not configured: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to update schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {e}") from e


@app.delete("/api/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str, _: AuthDep):
    """Delete a schedule. Requires authentication.

    Removes the schedule from storage and cancels any pending APScheduler jobs.

    Args:
        schedule_id: Unique schedule identifier

    Raises:
        HTTPException: 404 if schedule not found
    """
    try:
        table_client = _get_schedule_table_client()

        # Verify schedule exists
        try:
            table_client.get_entity(
                partition_key=SCHEDULE_PARTITION_KEY,
                row_key=schedule_id,
            )
        except ResourceNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}") from e

        # Remove from APScheduler
        _remove_scheduler_job(schedule_id)

        # Delete from Table Storage
        table_client.delete_entity(
            partition_key=SCHEDULE_PARTITION_KEY,
            row_key=schedule_id,
        )

        logger.info(f"Deleted schedule: {schedule_id}")
        return None

    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Storage not configured: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to delete schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {e}") from e


# ==============================================================================
# ORCHESTRATION LOGIC
# ==============================================================================


async def run_scheduled_orchestration():
    """Run scheduled orchestration (triggered by cron)."""
    run_id = str(uuid4())
    logger.info(f"Scheduled execution triggered: run_id={run_id}")
    await run_orchestration(run_id)


async def run_orchestration(
    run_id: str,
    skip_validation: bool = False,
    scenario_names: list[str] | None = None,
    scenario_count: int | None = None,
):
    """Main orchestration workflow.

    Args:
        run_id: Unique execution run ID
        skip_validation: Skip environment validation (for testing)
        scenario_names: Specific scenarios to run (None = random selection)
        scenario_count: Number of scenarios to select (overrides config)

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

        # Use schedule-provided scenarios or select based on config
        if scenario_names:
            # Filter to specific scenarios requested by schedule
            from azure_haymaker.models.config import SimulationSize

            all_scenarios = select_scenarios(SimulationSize.LARGE)  # Get all available
            scenarios = [s for s in all_scenarios if s.scenario_name in scenario_names]
            if not scenarios:
                logger.error(f"[{run_id}] No matching scenarios found for: {scenario_names}")
                execution_report["status"] = "failed"
                execution_report["failure_reason"] = "no_matching_scenarios"
                return
        else:
            # Random selection based on scenario_count or config
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
                f"[{run_id}] Status check {check_num + 1}/32: "
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
