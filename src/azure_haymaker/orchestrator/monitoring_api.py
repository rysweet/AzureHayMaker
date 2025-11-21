"""
Monitoring API for Azure HayMaker orchestration service.

This module provides HTTP endpoints for querying execution status, runs, and resources.
It implements a clean 3-layer architecture:
- Controller: HTTP/Azure Functions handling
- Service: Business logic and validation
- Repository: Data access to Azure Blob Storage

The module exports adapter functions that maintain backward compatibility with
existing Azure Functions code while delegating to the new layered architecture.

Endpoints:
- GET /status - Get current orchestrator status
- GET /runs/{run_id} - Get detailed run information
- GET /runs/{run_id}/resources - Get resources created in a run

OpenAPI Spec: specs/api-design.md
Architecture: specs/architecture.md
"""

import azure.functions as func
from azure.storage.blob import BlobServiceClient

from .api.monitoring_controller import MonitoringController
from .models.api_errors import APIError, InvalidParameterError, RunNotFoundError
from .repositories.monitoring_repository import MonitoringRepository
from .services.monitoring_service import MonitoringService


def _get_controller(blob_client: BlobServiceClient) -> MonitoringController:
    """
    Get or create controller instance.

    This function creates a new controller instance for each blob_client.
    This ensures tests with different mock clients work correctly.

    Args:
        blob_client: Azure Blob Service client

    Returns:
        MonitoringController instance with fully initialized dependencies
    """
    # Initialize layers with dependency injection
    # Always create a new instance to support testing with different mock clients
    repository = MonitoringRepository(blob_client)
    service = MonitoringService(repository)
    controller = MonitoringController(service)
    return controller


# ==============================================================================
# ADAPTER FUNCTIONS FOR AZURE FUNCTIONS
#
# These functions maintain backward compatibility with existing Azure Functions
# code while delegating to the new 3-layer architecture.
# ==============================================================================


async def get_status(
    req: func.HttpRequest,
    blob_client: BlobServiceClient,
) -> func.HttpResponse:
    """
    GET /api/v1/status

    Returns current orchestrator status including active run information and health indicators.

    This function is an adapter for Azure Functions that delegates to the controller layer.
    Function signature and behavior are maintained for backward compatibility.

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
    controller = _get_controller(blob_client)
    return await controller.get_status(req)


async def get_run_details(
    req: func.HttpRequest,
    blob_client: BlobServiceClient,
) -> func.HttpResponse:
    """
    GET /api/v1/runs/{run_id}

    Returns comprehensive details for a specific execution run including scenarios,
    resources, and cleanup verification results.

    This function is an adapter for Azure Functions that delegates to the controller layer.
    Function signature and behavior are maintained for backward compatibility.

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
    controller = _get_controller(blob_client)
    return await controller.get_run_details(req)


async def get_run_resources(
    req: func.HttpRequest,
    blob_client: BlobServiceClient,
) -> func.HttpResponse:
    """
    GET /api/v1/runs/{run_id}/resources

    Returns paginated list of Azure resources created in a run with lifecycle tracking.
    Supports filtering by scenario_name, resource_type, and status.

    This function is an adapter for Azure Functions that delegates to the controller layer.
    Function signature and behavior are maintained for backward compatibility.

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
    controller = _get_controller(blob_client)
    return await controller.get_run_resources(req)


# ==============================================================================
# MODULE EXPORTS
# ==============================================================================

__all__ = [
    # Adapter functions (for Azure Functions)
    "get_status",
    "get_run_details",
    "get_run_resources",
    # Layer classes (for testing and direct use)
    "MonitoringController",
    "MonitoringService",
    "MonitoringRepository",
    # Error classes (for error handling)
    "APIError",
    "RunNotFoundError",
    "InvalidParameterError",
]
