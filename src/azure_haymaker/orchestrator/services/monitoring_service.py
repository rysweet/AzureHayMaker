"""
Business logic layer for monitoring API.

This service layer contains all business logic, validation, and data transformation
for the monitoring API. It is independent of HTTP concerns and delegates data access
to the repository layer.

Responsibilities:
- Validate input parameters (run_id format, pagination)
- Transform repository data into response structures
- Apply business rules (filtering, pagination logic)
- Raise domain-specific errors
"""

import uuid
from typing import Any

from azure.core.exceptions import ResourceNotFoundError

from ..models.api_errors import InvalidParameterError, RunNotFoundError
from ..repositories.monitoring_repository import MonitoringRepository


class MonitoringService:
    """
    Service layer for monitoring business logic.

    This class handles validation, filtering, and data transformation for
    monitoring operations. It depends only on the repository layer and is
    independent of HTTP/Azure Functions concerns.
    """

    def __init__(self, repository: MonitoringRepository):
        """
        Initialize service with repository.

        Args:
            repository: Data access repository for blob storage operations
        """
        self.repository = repository

    async def get_status(self) -> dict[str, Any]:
        """
        Get current orchestrator status.

        Returns idle state when no status file exists, otherwise returns
        the current status with all required fields populated.

        Returns:
            Status dictionary with fields:
                - status: Current orchestrator state (idle, running, etc.)
                - health: Health indicator (healthy, degraded, etc.)
                - current_run_id: UUID of current run (None if idle)
                - started_at: ISO timestamp of run start
                - scheduled_end_at: ISO timestamp of scheduled end
                - phase: Current execution phase
                - scenarios_count: Total scenarios in run
                - scenarios_completed: Number of completed scenarios
                - scenarios_running: Number of running scenarios
                - scenarios_failed: Number of failed scenarios
                - next_scheduled_run: ISO timestamp of next scheduled run

        Raises:
            Exception: For storage errors (propagated from repository)
        """
        status_data = await self.repository.get_status()

        if status_data is None:
            # Return idle state when no status file exists
            return {
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

        # Build response with all required fields from storage data
        return {
            "status": status_data.get("status", "idle"),
            "health": status_data.get("health", "healthy"),
            "current_run_id": status_data.get("current_run_id"),
            "started_at": status_data.get("started_at"),
            "scheduled_end_at": status_data.get("scheduled_end_at"),
            "phase": status_data.get("phase"),
            "scenarios_count": status_data.get("scenarios_count"),
            "scenarios_completed": status_data.get("scenarios_completed"),
            "scenarios_running": status_data.get("scenarios_running"),
            "scenarios_failed": status_data.get("scenarios_failed"),
            "next_scheduled_run": status_data.get("next_scheduled_run"),
        }

    async def get_run_details(self, run_id: str) -> dict[str, Any]:
        """
        Get detailed information for a specific run.

        Validates run_id format and retrieves comprehensive run information
        including scenarios, resource counts, and cleanup verification.

        Args:
            run_id: Run UUID (must be valid UUID format)

        Returns:
            Run details dictionary with fields:
                - run_id: The run UUID
                - started_at: ISO timestamp of run start
                - ended_at: ISO timestamp of run end (None if running)
                - status: Run status (running, completed, failed, etc.)
                - phase: Current or final execution phase
                - simulation_size: Size of simulation (small, medium, large)
                - scenarios: List of scenario execution details
                - total_resources: Total number of resources created
                - total_service_principals: Total number of service principals
                - cleanup_verification: Cleanup verification results
                - errors: List of errors encountered during execution

        Raises:
            InvalidParameterError: If run_id format is invalid
            RunNotFoundError: If run doesn't exist in storage
            Exception: For storage errors (propagated from repository)
        """
        # Validate run_id format
        self._validate_run_id(run_id)

        # Fetch from repository
        try:
            run_data = await self.repository.get_run_report(run_id)
        except ResourceNotFoundError:
            raise RunNotFoundError(run_id)

        # Build response matching RunDetails schema
        return {
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

    async def get_run_resources(
        self,
        run_id: str,
        page: int = 1,
        page_size: int = 100,
        scenario_name: str | None = None,
        resource_type: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        Get paginated resources for a run with optional filtering.

        Validates all parameters, applies filters, and returns paginated results
        with metadata.

        Args:
            run_id: Run UUID (must be valid UUID format)
            page: Page number, 1-indexed (default 1)
            page_size: Items per page, must be 1-500 (default 100)
            scenario_name: Optional filter for scenario name
            resource_type: Optional filter for Azure resource type
            status: Optional filter for resource status (created, exists, deleted, deletion_failed)

        Returns:
            Resources list response with fields:
                - run_id: The run UUID
                - resources: List of resources for current page
                - pagination: Pagination metadata with page, page_size, total_items,
                  total_pages, has_next, has_previous

        Raises:
            InvalidParameterError: If any parameter is invalid
            RunNotFoundError: If run doesn't exist in storage
            Exception: For storage errors (propagated from repository)
        """
        # Validate parameters
        self._validate_run_id(run_id)
        self._validate_pagination(page, page_size)
        if status:
            self._validate_resource_status(status)

        # Fetch from repository
        try:
            resources_data = await self.repository.get_run_resources(run_id)
        except ResourceNotFoundError:
            raise RunNotFoundError(run_id)

        # Get all resources
        all_resources = resources_data.get("resources", [])

        # Apply filters
        filtered_resources = self._apply_resource_filters(
            all_resources, scenario_name, resource_type, status
        )

        # Calculate pagination
        total_items = len(filtered_resources)
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

        # Validate page number
        if page > total_pages and total_pages > 0:
            raise InvalidParameterError("page", f"Page {page} exceeds total pages {total_pages}")

        # Get items for current page
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_resources = filtered_resources[start_idx:end_idx]

        # Build response
        return {
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

    def _validate_run_id(self, run_id: str) -> None:
        """
        Validate that run_id is a valid UUID.

        Args:
            run_id: The run ID to validate

        Raises:
            InvalidParameterError: If run_id is not a valid UUID format
        """
        try:
            uuid.UUID(run_id)
        except ValueError as e:
            raise InvalidParameterError(
                "run_id", f"Must be a valid UUID, got '{run_id}'"
            ) from e

    def _validate_pagination(self, page: int, page_size: int) -> None:
        """
        Validate pagination parameters.

        Args:
            page: Page number (must be >= 1)
            page_size: Number of items per page (must be 1-500)

        Raises:
            InvalidParameterError: If parameters are invalid
        """
        if page < 1:
            raise InvalidParameterError("page", "page must be >= 1")

        if page_size < 1 or page_size > 500:
            raise InvalidParameterError("page_size", "page_size must be between 1 and 500")

    def _validate_resource_status(self, status: str) -> None:
        """
        Validate resource status filter value.

        Args:
            status: Status filter value to validate

        Raises:
            InvalidParameterError: If status is not a valid value
        """
        valid_statuses = ["created", "exists", "deleted", "deletion_failed"]
        if status not in valid_statuses:
            raise InvalidParameterError(
                "status", f"Must be one of: {', '.join(valid_statuses)}"
            )

    def _apply_resource_filters(
        self,
        resources: list[dict[str, Any]],
        scenario_name: str | None,
        resource_type: str | None,
        status: str | None,
    ) -> list[dict[str, Any]]:
        """
        Apply filters to resources list.

        Filters are applied in sequence. Each filter narrows down the results.

        Args:
            resources: List of all resources
            scenario_name: Optional scenario filter
            resource_type: Optional resource type filter
            status: Optional status filter

        Returns:
            Filtered resources list
        """
        filtered = resources

        if scenario_name:
            filtered = [r for r in filtered if r.get("scenario_name") == scenario_name]

        if resource_type:
            filtered = [r for r in filtered if r.get("resource_type") == resource_type]

        if status:
            filtered = [r for r in filtered if r.get("status") == status]

        return filtered


__all__ = ["MonitoringService"]
