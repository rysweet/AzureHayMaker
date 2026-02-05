"""Schedule CRUD route handlers.

Single Responsibility: Schedule management with APScheduler integration.

Public API:
    router: FastAPI router with schedule endpoints
    create_schedule: POST /schedules - Create new schedule
    list_schedules: GET /schedules - List all schedules
    get_schedule: GET /schedules/{id} - Get specific schedule
    update_schedule: PUT /schedules/{id} - Update schedule
    delete_schedule: DELETE /schedules/{id} - Delete schedule
    validate_cron_expression: Validate cron expression string
    schedule_to_entity: Convert Schedule to Table Storage entity
    entity_to_schedule: Convert Table Storage entity to Schedule
    get_next_run_time: Calculate next run time from cron
"""

import contextlib
import json
import logging
import os
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException

from azure_haymaker.models.schedule import (
    Schedule,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
)
from azure_haymaker.orchestrator.auth import require_auth
from azure_haymaker.utils.credentials import get_credential

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])

# Auth dependency type alias
AuthDep = Annotated[dict, Depends(require_auth)]

# Table Storage configuration
SCHEDULE_TABLE_NAME = "Schedules"
SCHEDULE_PARTITION_KEY = "schedule"

# Module-level table client (lazy initialization)
_schedule_table_client = None

# Reference to global scheduler (injected by main app)
_scheduler: AsyncIOScheduler | None = None

# Reference to run_orchestration function (injected by main app)
_run_orchestration_fn = None


def set_scheduler_ref(scheduler: AsyncIOScheduler) -> None:
    """Set reference to global scheduler from main app."""
    global _scheduler
    _scheduler = scheduler


def set_run_orchestration_fn(fn) -> None:
    """Set reference to run_orchestration function from main app."""
    global _run_orchestration_fn
    _run_orchestration_fn = fn


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
        credential = get_credential()
        table_service = TableServiceClient(endpoint=account_url, credential=credential)
        try:
            table_service.create_table_if_not_exists(SCHEDULE_TABLE_NAME)
        except Exception as e:
            logger.warning(f"Could not ensure table exists: {e}")
        _schedule_table_client = table_service.get_table_client(SCHEDULE_TABLE_NAME)
    return _schedule_table_client


def validate_cron_expression(cron_expr: str) -> bool:
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
        parts = cron_expr.strip().split()
        if len(parts) == 6:
            five_field_cron = " ".join(parts[1:])
        elif len(parts) == 5:
            five_field_cron = cron_expr
        else:
            raise ValueError(f"Invalid cron expression: expected 5 or 6 fields, got {len(parts)}")
        croniter(five_field_cron)
        return True
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid cron expression '{cron_expr}': {e}") from e


def schedule_to_entity(schedule: Schedule) -> dict[str, Any]:
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


def entity_to_schedule(entity: dict[str, Any]) -> Schedule:
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


def get_next_run_time(cron_expr: str) -> str | None:
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
    next_run = get_next_run_time(schedule.cron_expression) if schedule.enabled else None
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
        table_client = _get_schedule_table_client()
        entity = table_client.get_entity(
            partition_key=SCHEDULE_PARTITION_KEY,
            row_key=schedule_id,
        )
        schedule = entity_to_schedule(entity)

        if not schedule.enabled:
            logger.info(f"Schedule {schedule_id} is disabled, skipping")
            return

        run_id = str(uuid4())
        logger.info(
            f"Starting scheduled orchestration: run_id={run_id}, "
            f"schedule={schedule.name}, scenarios={schedule.scenarios}, "
            f"scenario_count={schedule.scenario_count}"
        )

        if _run_orchestration_fn:
            await _run_orchestration_fn(
                run_id=run_id,
                skip_validation=False,
                scenario_names=schedule.scenarios,
                scenario_count=schedule.scenario_count,
            )
        else:
            logger.error("run_orchestration function not configured")

    except ResourceNotFoundError:
        logger.error(f"Schedule {schedule_id} not found, removing job")
        if _scheduler:
            with contextlib.suppress(Exception):
                _scheduler.remove_job(f"schedule_{schedule_id}")
    except Exception as e:
        logger.error(f"Failed to run scheduled job {schedule_id}: {e}", exc_info=True)


def _add_scheduler_job(schedule: Schedule) -> None:
    """Add or update APScheduler job for a schedule.

    Args:
        schedule: Schedule model instance
    """
    if not _scheduler:
        logger.warning("Scheduler not configured, cannot add job")
        return

    job_id = f"schedule_{schedule.id}"

    with contextlib.suppress(Exception):
        _scheduler.remove_job(job_id)

    if not schedule.enabled:
        logger.info(f"Schedule {schedule.id} is disabled, not adding job")
        return

    try:
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

        _scheduler.add_job(
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
    if not _scheduler:
        return

    job_id = f"schedule_{schedule_id}"
    try:
        _scheduler.remove_job(job_id)
        logger.info(f"Removed scheduler job: {job_id}")
    except Exception as e:
        logger.debug(f"Job {job_id} not found or already removed: {e}")


async def load_schedules_on_startup() -> None:
    """Load all enabled schedules from storage and add to scheduler."""
    try:
        table_client = _get_schedule_table_client()
        query = f"PartitionKey eq '{SCHEDULE_PARTITION_KEY}'"

        for entity in table_client.query_entities(query_filter=query):
            try:
                schedule = entity_to_schedule(entity)
                if schedule.enabled:
                    _add_scheduler_job(schedule)
            except Exception as e:
                logger.warning(f"Failed to load schedule {entity.get('RowKey')}: {e}")

        logger.info("Loaded schedules from storage")
    except Exception as e:
        logger.warning(f"Could not load schedules from storage: {e}")


# ==============================================================================
# ROUTE HANDLERS
# ==============================================================================


@router.post("", response_model=ScheduleResponse, status_code=201)
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
        validate_cron_expression(request.cron_expression)

        schedule = Schedule(
            name=request.name,
            cron_expression=request.cron_expression,
            scenarios=request.scenarios,
            scenario_count=request.scenario_count,
            enabled=request.enabled,
        )

        table_client = _get_schedule_table_client()
        entity = schedule_to_entity(schedule)
        table_client.create_entity(entity=entity)

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


@router.get("", response_model=list[ScheduleResponse])
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
                schedule = entity_to_schedule(entity)
                schedules.append(_schedule_to_response(schedule))
            except Exception as e:
                logger.warning(f"Failed to parse schedule entity: {e}")
                continue

        schedules.sort(key=lambda s: s.created_at, reverse=True)
        return schedules

    except RuntimeError as e:
        logger.error(f"Storage not configured: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to list schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {e}") from e


@router.get("/{schedule_id}", response_model=ScheduleResponse)
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
        schedule = entity_to_schedule(entity)
        return _schedule_to_response(schedule)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}") from e
    except RuntimeError as e:
        logger.error(f"Storage not configured: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {e}") from e


@router.put("/{schedule_id}", response_model=ScheduleResponse)
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

        try:
            entity = table_client.get_entity(
                partition_key=SCHEDULE_PARTITION_KEY,
                row_key=schedule_id,
            )
        except ResourceNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}") from e

        schedule = entity_to_schedule(entity)
        cron_changed = False

        if request.name is not None:
            schedule.name = request.name
        if request.cron_expression is not None:
            validate_cron_expression(request.cron_expression)
            cron_changed = schedule.cron_expression != request.cron_expression
            schedule.cron_expression = request.cron_expression
        if request.scenarios is not None:
            schedule.scenarios = request.scenarios
        if request.scenario_count is not None:
            schedule.scenario_count = request.scenario_count
        if request.enabled is not None:
            cron_changed = cron_changed or (schedule.enabled != request.enabled)
            schedule.enabled = request.enabled

        updated_entity = schedule_to_entity(schedule)
        table_client.update_entity(entity=updated_entity, mode=UpdateMode.REPLACE)

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


@router.delete("/{schedule_id}", status_code=204)
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

        try:
            table_client.get_entity(
                partition_key=SCHEDULE_PARTITION_KEY,
                row_key=schedule_id,
            )
        except ResourceNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}") from e

        _remove_scheduler_job(schedule_id)

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


__all__ = [
    "router",
    "validate_cron_expression",
    "schedule_to_entity",
    "entity_to_schedule",
    "get_next_run_time",
    "load_schedules_on_startup",
    "set_scheduler_ref",
    "set_run_orchestration_fn",
]
