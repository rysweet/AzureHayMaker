"""
Monitoring API for Azure HayMaker orchestration service.

Provides HTTP endpoints for querying execution status, runs, and resources.
Implements the 3 core endpoints from the API specification:
- GET /status - Get current orchestrator status
- GET /runs/{run_id} - Get detailed run information
- GET /runs/{run_id}/resources - Get resources created in a run

All endpoints use Table Storage + Blob Storage as backends with basic Azure AD authentication.

OpenAPI Spec: specs/api-design.md
Architecture: specs/architecture.md
"""

import json
import logging
import uuid

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


# ==============================================================================
# CUSTOM EXCEPTIONS
# ==============================================================================


class APIError(Exception):
    """Base class for API errors."""

    def __init__(self, message: str, status_code: int = 500, code: str = "INTERNAL_ERROR"):
        """
        Initialize API error.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            code: Machine-readable error code
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class RunNotFoundError(APIError):
    """Raised when a run is not found."""

    def __init__(self, run_id: str):
        """
        Initialize RunNotFoundError.

        Args:
            run_id: The run ID that was not found
        """
        message = f"Run with ID '{run_id}' not found"
        super().__init__(message, status_code=404, code="RUN_NOT_FOUND")
        self.run_id = run_id


class InvalidParameterError(APIError):
    """Raised when a request parameter is invalid."""

    def __init__(self, parameter: str, message: str):
        """
        Initialize InvalidParameterError.

        Args:
            parameter: The parameter that is invalid
            message: Description of why it's invalid
        """
        full_message = f"Invalid parameter '{parameter}': {message}"
        super().__init__(full_message, status_code=400, code="INVALID_PARAMETER")
        self.parameter = parameter


# ==============================================================================
# VALIDATION UTILITIES
# ==============================================================================


def validate_run_id(run_id: str) -> None:
    """
    Validate that run_id is a valid UUID.

    Args:
        run_id: The run ID to validate

    Raises:
        InvalidParameterError: If run_id is not a valid UUID
    """
    try:
        uuid.UUID(run_id)
    except ValueError as e:
        raise InvalidParameterError("run_id", f"Must be a valid UUID, got '{run_id}'") from e


def validate_pagination_params(page: str, page_size: str) -> tuple[int, int]:
    """
    Validate and parse pagination parameters.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (page, page_size) as integers

    Raises:
        InvalidParameterError: If parameters are invalid
    """
    try:
        page_int = int(page) if page else 1
        page_size_int = int(page_size) if page_size else 100
    except ValueError as e:
        raise InvalidParameterError("pagination", "page and page_size must be integers") from e

    if page_int < 1:
        raise InvalidParameterError("page", "page must be >= 1")

    if page_size_int < 1 or page_size_int > 500:
        raise InvalidParameterError("page_size", "page_size must be between 1 and 500")

    return page_int, page_size_int


# ==============================================================================
# ERROR RESPONSE UTILITIES
# ==============================================================================


def create_error_response(error: APIError, trace_id: str | None = None) -> func.HttpResponse:
    """
    Create standard error response.

    Args:
        error: The APIError to convert to response
        trace_id: Optional trace ID for correlation

    Returns:
        HttpResponse with error details
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())

    error_body = {
        "error": {
            "code": error.code,
            "message": error.message,
            "trace_id": trace_id,
        }
    }

    # Add parameter details if available
    if isinstance(error, InvalidParameterError):
        error_body["error"]["details"] = {
            "parameter": error.parameter,
        }

    if isinstance(error, RunNotFoundError):
        error_body["error"]["details"] = {
            "run_id": error.run_id,
        }

    return func.HttpResponse(
        body=json.dumps(error_body),
        status_code=error.status_code,
        mimetype="application/json",
        headers={
            "Content-Type": "application/json",
            "X-Trace-ID": trace_id,
        },
    )


# ==============================================================================
# STORAGE ACCESS UTILITIES
# ==============================================================================


async def read_blob_json(
    blob_client: BlobServiceClient, container: str, blob_name: str
) -> dict[str, object]:
    """
    Read and parse JSON from blob storage.

    Args:
        blob_client: Azure Blob Service client
        container: Container name
        blob_name: Blob name (path)

    Returns:
        Parsed JSON as dictionary

    Raises:
        ResourceNotFoundError: If blob doesn't exist
        Exception: For other storage errors
    """
    try:
        blob = blob_client.get_blob_client(container=container, blob=blob_name)
        download_stream = blob.download_blob()

        # Handle both sync and async download
        if hasattr(download_stream, "readall"):
            # Async case
            if callable(download_stream.readall):
                data_result = download_stream.readall()
                # Check if it's a coroutine
                if hasattr(data_result, "__await__"):
                    data = await data_result
                else:
                    data = data_result
            else:
                data = await download_stream.readall()
        else:
            # Fallback for sync API
            data = download_stream.readall()

        if isinstance(data, str):
            data = data.encode("utf-8")
        return json.loads(data.decode("utf-8"))
    except ResourceNotFoundError:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from blob {blob_name}: {e}")
        raise Exception(f"Corrupted data in storage: {blob_name}") from e
    except Exception as e:
        logger.error(f"Failed to read blob {blob_name}: {e}")
        raise


# ==============================================================================
# CORE ENDPOINT IMPLEMENTATIONS
# ==============================================================================


async def get_status(
    req: func.HttpRequest,
    blob_client: BlobServiceClient,
) -> func.HttpResponse:
    """
    GET /api/v1/status

    Returns current orchestrator status including active run information and health indicators.

    Args:
        req: Azure Functions HTTP request
        blob_client: Blob Storage client for reading status data

    Returns:
        HttpResponse with OrchestratorStatus JSON (200) or error response

    OpenAPI Contract:
        - Method: GET
        - Path: /api/v1/status
        - Auth: Azure AD token or API Key
        - Response 200: OrchestratorStatus schema
        - Response 500: InternalServerError schema
        - Response 503: ServiceUnavailable schema
    """
    trace_id = str(uuid.uuid4())

    try:
        # Read current status from blob storage
        # Path: execution-state/current_status.json
        status_data = await read_blob_json(
            blob_client, container="execution-state", blob_name="current_status.json"
        )

        # Build response with all required fields
        response_body = {
            "status": status_data.get("status", "idle"),
            "health": status_data.get("health", "healthy"),
        }

        # Optional fields that may be null
        response_body["current_run_id"] = status_data.get("current_run_id")
        response_body["started_at"] = status_data.get("started_at")
        response_body["scheduled_end_at"] = status_data.get("scheduled_end_at")
        response_body["phase"] = status_data.get("phase")
        response_body["scenarios_count"] = status_data.get("scenarios_count")
        response_body["scenarios_completed"] = status_data.get("scenarios_completed")
        response_body["scenarios_running"] = status_data.get("scenarios_running")
        response_body["scenarios_failed"] = status_data.get("scenarios_failed")
        response_body["next_scheduled_run"] = status_data.get("next_scheduled_run")

        return func.HttpResponse(
            body=json.dumps(response_body),
            status_code=200,
            mimetype="application/json",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "private, max-age=10",
                "X-Trace-ID": trace_id,
            },
        )

    except ResourceNotFoundError:
        # Status not yet created, return idle
        logger.info("Status file not found, returning idle state")
        response_body = {
            "status": "idle",
            "health": "healthy",
            "current_run_id": None,
            "started_at": None,
            "scheduled_end_at": None,
            "phase": None,
            "scenarios_count": None,
            "scenarios_completed": None,
            "scenarios_running": None,
            "scenarios_failed": None,
            "next_scheduled_run": None,
        }

        return func.HttpResponse(
            body=json.dumps(response_body),
            status_code=200,
            mimetype="application/json",
            headers={
                "Content-Type": "application/json",
                "X-Trace-ID": trace_id,
            },
        )

    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        api_error = APIError(
            "Failed to retrieve orchestrator status", status_code=500, code="STORAGE_ERROR"
        )
        return create_error_response(api_error, trace_id)


async def get_run_details(
    req: func.HttpRequest,
    blob_client: BlobServiceClient,
) -> func.HttpResponse:
    """
    GET /api/v1/runs/{run_id}

    Returns comprehensive details for a specific execution run including scenarios,
    resources, and cleanup verification results.

    Args:
        req: Azure Functions HTTP request containing run_id parameter
        blob_client: Blob Storage client for reading run data

    Returns:
        HttpResponse with RunDetails JSON (200) or error response

    Raises:
        InvalidParameterError: If run_id format is invalid
        RunNotFoundError: If run doesn't exist

    OpenAPI Contract:
        - Method: GET
        - Path: /api/v1/runs/{run_id}
        - Parameter: run_id (path, required, UUID format)
        - Auth: Azure AD token or API Key
        - Response 200: RunDetails schema
        - Response 404: NotFound error (RUN_NOT_FOUND code)
        - Response 500: InternalServerError schema
    """
    trace_id = str(uuid.uuid4())

    try:
        # Extract and validate run_id from path
        run_id = req.params.get("run_id")
        if not run_id:
            raise InvalidParameterError("run_id", "Required parameter missing from path")

        validate_run_id(run_id)

        # Read run details from blob storage
        # Path: execution-reports/{run_id}/report.json
        run_data = await read_blob_json(
            blob_client, container="execution-reports", blob_name=f"{run_id}/report.json"
        )

        # Build response matching RunDetails schema
        response_body = {
            "run_id": run_data["run_id"],
            "started_at": run_data["started_at"],
            "ended_at": run_data.get("ended_at"),
            "status": run_data["status"],
            "phase": run_data.get("phase"),
            "simulation_size": run_data.get("simulation_size"),
            "scenarios": run_data.get("scenarios", []),
            "total_resources": run_data.get("total_resources", 0),
            "total_service_principals": run_data.get("total_service_principals", 0),
            "cleanup_verification": run_data.get("cleanup_verification", {}),
            "errors": run_data.get("errors", []),
        }

        return func.HttpResponse(
            body=json.dumps(response_body),
            status_code=200,
            mimetype="application/json",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "private, max-age=30",
                "X-Trace-ID": trace_id,
            },
        )

    except InvalidParameterError as e:
        return create_error_response(e, trace_id)

    except ResourceNotFoundError:
        logger.info(f"Run not found: {run_id}")
        run_error = RunNotFoundError(run_id)
        return create_error_response(run_error, trace_id)

    except json.JSONDecodeError as e:
        logger.error(f"Corrupted run data for {run_id}: {e}")
        api_error = APIError(
            "Corrupted data in storage for run", status_code=500, code="STORAGE_ERROR"
        )
        return create_error_response(api_error, trace_id)

    except Exception as e:
        logger.error(f"Error getting run details for {run_id}: {e}", exc_info=True)
        api_error = APIError(
            "Failed to retrieve run details", status_code=500, code="STORAGE_ERROR"
        )
        return create_error_response(api_error, trace_id)


async def get_run_resources(
    req: func.HttpRequest,
    blob_client: BlobServiceClient,
) -> func.HttpResponse:
    """
    GET /api/v1/runs/{run_id}/resources

    Returns paginated list of Azure resources created in a run with lifecycle tracking.
    Supports filtering by scenario_name, resource_type, and status.

    Args:
        req: Azure Functions HTTP request with parameters:
            - run_id (path, required): UUID of the run
            - page (query, optional): Page number (default 1)
            - page_size (query, optional): Items per page (default 100, max 500)
            - scenario_name (query, optional): Filter by scenario
            - resource_type (query, optional): Filter by Azure resource type
            - status (query, optional): Filter by resource status

        blob_client: Blob Storage client for reading resource data

    Returns:
        HttpResponse with ResourcesListResponse JSON (200) or error response

    OpenAPI Contract:
        - Method: GET
        - Path: /api/v1/runs/{run_id}/resources
        - Parameters: run_id, page, page_size, scenario_name, resource_type, status
        - Auth: Azure AD token or API Key
        - Response 200: ResourcesListResponse schema
        - Response 400: BadRequest for invalid parameters
        - Response 404: NotFound error (RUN_NOT_FOUND code)
        - Response 500: InternalServerError schema
    """
    trace_id = str(uuid.uuid4())

    try:
        # Extract and validate run_id
        run_id = req.params.get("run_id")
        if not run_id:
            raise InvalidParameterError("run_id", "Required parameter missing from path")

        validate_run_id(run_id)

        # Extract and validate pagination parameters
        page_str = req.params.get("page", "1")
        page_size_str = req.params.get("page_size", "100")
        page, page_size = validate_pagination_params(page_str, page_size_str)

        # Extract optional filters
        scenario_filter = req.params.get("scenario_name")
        resource_type_filter = req.params.get("resource_type")
        status_filter = req.params.get("status")

        # Read resources list from blob storage
        # Path: execution-reports/{run_id}/resources.json
        resources_data = await read_blob_json(
            blob_client, container="execution-reports", blob_name=f"{run_id}/resources.json"
        )

        # Get all resources
        all_resources = resources_data.get("resources", [])

        # Apply filters
        filtered_resources = all_resources

        if scenario_filter:
            filtered_resources = [
                r for r in filtered_resources if r.get("scenario_name") == scenario_filter
            ]

        if resource_type_filter:
            filtered_resources = [
                r for r in filtered_resources if r.get("resource_type") == resource_type_filter
            ]

        if status_filter:
            valid_statuses = ["created", "exists", "deleted", "deletion_failed"]
            if status_filter not in valid_statuses:
                raise InvalidParameterError(
                    "status", f"Must be one of: {', '.join(valid_statuses)}"
                )
            filtered_resources = [r for r in filtered_resources if r.get("status") == status_filter]

        # Calculate pagination
        total_items = len(filtered_resources)
        total_pages = (total_items + page_size - 1) // page_size

        # Validate page number
        if page > total_pages and total_pages > 0:
            raise InvalidParameterError("page", f"Page {page} exceeds total pages {total_pages}")

        # Get items for current page
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_resources = filtered_resources[start_idx:end_idx]

        # Build response
        response_body = {
            "run_id": run_id,
            "resources": page_resources,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        }

        return func.HttpResponse(
            body=json.dumps(response_body),
            status_code=200,
            mimetype="application/json",
            headers={
                "Content-Type": "application/json",
                "X-Trace-ID": trace_id,
            },
        )

    except InvalidParameterError as e:
        return create_error_response(e, trace_id)

    except ResourceNotFoundError:
        logger.info(f"Resources not found for run: {run_id}")
        run_error = RunNotFoundError(run_id)
        return create_error_response(run_error, trace_id)

    except json.JSONDecodeError as e:
        logger.error(f"Corrupted resources data for {run_id}: {e}")
        api_error = APIError(
            "Corrupted data in storage for run", status_code=500, code="STORAGE_ERROR"
        )
        return create_error_response(api_error, trace_id)

    except Exception as e:
        logger.error(f"Error getting resources for {run_id}: {e}", exc_info=True)
        api_error = APIError("Failed to retrieve resources", status_code=500, code="STORAGE_ERROR")
        return create_error_response(api_error, trace_id)


# ==============================================================================
# MODULE EXPORTS
# ==============================================================================

__all__ = [
    "get_status",
    "get_run_details",
    "get_run_resources",
    "APIError",
    "RunNotFoundError",
    "InvalidParameterError",
    "validate_run_id",
    "validate_pagination_params",
    "create_error_response",
]
