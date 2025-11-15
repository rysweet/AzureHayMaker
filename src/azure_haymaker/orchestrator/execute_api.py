"""HTTP API for on-demand scenario execution.

This module provides HTTP endpoints for:
- POST /api/v1/execute - Submit execution request
- GET /api/v1/executions/{execution_id} - Query execution status
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import azure.functions as func
from azure.data.tables import TableClient
from azure.identity import DefaultAzureCredential
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

logger = logging.getLogger(__name__)

# Azure Functions app instance
app = func.FunctionApp()


def get_scenario_path(scenario_name: str) -> Path | None:
    """Get path to scenario document.

    Args:
        scenario_name: Scenario name to look up

    Returns:
        Path to scenario document or None if not found

    Example:
        >>> path = get_scenario_path("compute-01-linux-vm-web-server")
        >>> if path and path.exists():
        ...     print("Scenario exists")
    """
    # Search in docs/scenarios directory
    project_root = Path(__file__).parent.parent.parent.parent
    scenarios_dir = project_root / "docs" / "scenarios"

    if not scenarios_dir.exists():
        logger.warning(f"Scenarios directory not found: {scenarios_dir}")
        return None

    # Search for scenario file
    for scenario_file in scenarios_dir.glob("**/*.md"):
        if scenario_name in scenario_file.stem:
            return scenario_file

    return None


def validate_scenarios(scenarios: list[str]) -> tuple[bool, str | None]:
    """Validate that all scenarios exist.

    Args:
        scenarios: List of scenario names to validate

    Returns:
        Tuple of (valid: bool, error_message: str | None)

    Example:
        >>> valid, error = validate_scenarios(["compute-01", "invalid-scenario"])
        >>> if not valid:
        ...     print(error)
    """
    missing_scenarios = []

    for scenario_name in scenarios:
        path = get_scenario_path(scenario_name)
        if not path or not path.exists():
            missing_scenarios.append(scenario_name)

    if missing_scenarios:
        error_msg = f"Scenarios not found: {', '.join(missing_scenarios)}"
        return False, error_msg

    return True, None


@app.route(route="execute", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def execute_scenario(req: func.HttpRequest) -> func.HttpResponse:
    """Execute scenarios on-demand via HTTP POST.

    Request:
        POST /api/v1/execute
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

        # Check global and per-scenario limits
        rate_limit_checks = [("global", "default")]
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

        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name="execution-requests")
            async with sender:
                message_body = {
                    "execution_id": execution_id,
                    "scenarios": execution_request.scenarios,
                    "duration_hours": execution_request.duration_hours,
                    "tags": execution_request.tags,
                    "requested_at": datetime.now(UTC).isoformat(),
                }

                message = ServiceBusMessage(json.dumps(message_body))
                await sender.send_messages(message)

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


@app.route(
    route="executions/{execution_id}", methods=["GET"], auth_level=func.AuthLevel.FUNCTION
)
async def get_execution_status(req: func.HttpRequest) -> func.HttpResponse:
    """Get execution status via HTTP GET.

    Request:
        GET /api/v1/executions/{execution_id}

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
            logger.error(f"Execution not found: {execution_id}", exc_info=True)
            return func.HttpResponse(
                body=json.dumps(
                    {
                        "error": {
                            "code": "EXECUTION_NOT_FOUND",
                            "message": f"Execution not found: {execution_id}",
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
