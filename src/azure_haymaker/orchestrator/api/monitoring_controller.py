"""
Controller layer for monitoring API.

This controller handles HTTP/Azure Functions concerns for the monitoring API.
It extracts parameters from requests, calls the service layer, and converts
results into HTTP responses with proper headers and error handling.

Responsibilities:
- Extract parameters from HTTP requests
- Convert service calls to HTTP responses
- Handle errors and create error responses
- Set HTTP headers (Content-Type, Cache-Control, X-Trace-ID)
"""

import json
import logging
import uuid
from typing import Any

import azure.functions as func

from ..models.api_errors import APIError, InvalidParameterError
from ..services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)


class MonitoringController:
    """
    Controller for monitoring API HTTP endpoints.

    This class is a thin adapter between Azure Functions HTTP layer and
    the service layer business logic. It handles HTTP concerns only.
    """

    def __init__(self, service: MonitoringService):
        """
        Initialize controller with service.

        Args:
            service: Business logic service for monitoring operations
        """
        self.service = service

    async def get_status(self, req: func.HttpRequest) -> func.HttpResponse:
        """
        GET /api/v1/status

        Returns current orchestrator status including active run information
        and health indicators.

        Args:
            req: Azure Functions HTTP request

        Returns:
            HttpResponse with OrchestratorStatus JSON (200) or error response (500)
        """
        trace_id = str(uuid.uuid4())

        try:
            response_body = await self.service.get_status()

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

        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            api_error = APIError(
                "Failed to retrieve orchestrator status", status_code=500, code="STORAGE_ERROR"
            )
            return self._create_error_response(api_error, trace_id)

    async def get_run_details(self, req: func.HttpRequest) -> func.HttpResponse:
        """
        GET /api/v1/runs/{run_id}

        Returns comprehensive details for a specific execution run.

        Args:
            req: Azure Functions HTTP request containing run_id parameter

        Returns:
            HttpResponse with RunDetails JSON (200), error response (400/404/500)
        """
        trace_id = str(uuid.uuid4())
        run_id = req.params.get("run_id")

        try:
            if not run_id:
                raise InvalidParameterError("run_id", "Required parameter missing from path")

            response_body = await self.service.get_run_details(run_id)

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

        except (InvalidParameterError, APIError) as e:
            return self._create_error_response(e, trace_id)

        except Exception as e:
            logger.error(f"Error getting run details: {e}", exc_info=True)
            api_error = APIError(
                "Failed to retrieve run details", status_code=500, code="STORAGE_ERROR"
            )
            return self._create_error_response(api_error, trace_id)

    async def get_run_resources(self, req: func.HttpRequest) -> func.HttpResponse:
        """
        GET /api/v1/runs/{run_id}/resources

        Returns paginated list of Azure resources created in a run with
        lifecycle tracking. Supports filtering by scenario_name, resource_type,
        and status.

        Args:
            req: Azure Functions HTTP request with parameters:
                - run_id (path): UUID of the run
                - page (query): Page number (default 1)
                - page_size (query): Items per page (default 100, max 500)
                - scenario_name (query): Filter by scenario
                - resource_type (query): Filter by Azure resource type
                - status (query): Filter by resource status

        Returns:
            HttpResponse with ResourcesListResponse JSON (200), error response (400/404/500)
        """
        trace_id = str(uuid.uuid4())

        try:
            # Extract run_id
            run_id = req.params.get("run_id")
            if not run_id:
                raise InvalidParameterError("run_id", "Required parameter missing from path")

            # Parse pagination parameters
            page = self._parse_int_param(req.params.get("page", "1"), "page", default=1)
            page_size = self._parse_int_param(
                req.params.get("page_size", "100"), "page_size", default=100
            )

            # Extract optional filters
            scenario_name = req.params.get("scenario_name")
            resource_type = req.params.get("resource_type")
            status = req.params.get("status")

            # Call service
            response_body = await self.service.get_run_resources(
                run_id=run_id,
                page=page,
                page_size=page_size,
                scenario_name=scenario_name,
                resource_type=resource_type,
                status=status,
            )

            return func.HttpResponse(
                body=json.dumps(response_body),
                status_code=200,
                mimetype="application/json",
                headers={
                    "Content-Type": "application/json",
                    "X-Trace-ID": trace_id,
                },
            )

        except (InvalidParameterError, APIError) as e:
            return self._create_error_response(e, trace_id)

        except Exception as e:
            logger.error(f"Error getting resources: {e}", exc_info=True)
            api_error = APIError(
                "Failed to retrieve resources", status_code=500, code="STORAGE_ERROR"
            )
            return self._create_error_response(api_error, trace_id)

    def _parse_int_param(self, value: str, name: str, default: int) -> int:
        """
        Parse integer parameter with default.

        Args:
            value: String value to parse
            name: Parameter name (for error messages)
            default: Default value if empty

        Returns:
            Parsed integer value

        Raises:
            InvalidParameterError: If value is not a valid integer
        """
        if not value:
            return default

        try:
            return int(value)
        except ValueError as e:
            raise InvalidParameterError(name, f"Must be an integer, got '{value}'") from e

    def _create_error_response(self, error: APIError, trace_id: str) -> func.HttpResponse:
        """
        Create standard error response.

        Args:
            error: The APIError to convert to response
            trace_id: Trace ID for correlation

        Returns:
            HttpResponse with error details and appropriate status code
        """
        error_body: dict[str, Any] = {
            "error": {
                "code": error.code,
                "message": error.message,
                "trace_id": trace_id,
            }
        }

        # Add parameter details if available
        if hasattr(error, "parameter"):
            error_body["error"]["details"] = {"parameter": error.parameter}

        if hasattr(error, "run_id"):
            error_body["error"]["details"] = {"run_id": error.run_id}

        return func.HttpResponse(
            body=json.dumps(error_body),
            status_code=error.status_code,
            mimetype="application/json",
            headers={
                "Content-Type": "application/json",
                "X-Trace-ID": trace_id,
            },
        )


__all__ = ["MonitoringController"]
