"""Timer trigger for Azure HayMaker orchestrator.

This module contains the timer trigger function that starts orchestration runs
4 times daily (00:00, 06:00, 12:00, 18:00 UTC).

The timer trigger:
1. Generates a unique run ID
2. Starts a new durable orchestration instance
3. Returns a status check response

Design Pattern: Timer-Initiated Orchestration
- CRON schedule triggers execution
- Creates unique run ID for tracking
- Delegates to durable orchestration for workflow
- Returns immediately with status check URL

Dependencies:
- orchestrator_app: Shared FunctionApp instance
- workflow_orchestrator: Main orchestration function (referenced by name)
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import azure.functions as func

from azure_haymaker.orchestrator.orchestrator_app import app

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
    # NOTE: Function name must match @app.orchestration_trigger in workflow_orchestrator.py
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
