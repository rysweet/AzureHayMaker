"""Resource Graph querying for Azure HayMaker cleanup operations.

This module handles querying Azure Resource Graph to find and verify
AzureHayMaker-managed resources during cleanup operations.

Philosophy:
- Single responsibility: Resource Graph queries only
- Standard library where possible
- Self-contained and regeneratable

Public API (the "studs"):
    CleanupStatus: Enum for cleanup operation status
    CleanupReport: Report from cleanup operations
    query_managed_resources: Query resources for a specific run
    verify_cleanup_complete: Verify all resources deleted
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
)
from pydantic import BaseModel, Field

from azure_haymaker.exceptions import (
    CleanupError,
    CredentialError,
)
from azure_haymaker.models.resource import Resource, ResourceStatus
from azure_haymaker.utils.credentials import get_credential

# Lazy imports for optional dependencies and circular import prevention
if TYPE_CHECKING:
    from azure_haymaker.orchestrator.cleanup.resource_deletion import ResourceDeletion

logger = logging.getLogger(__name__)


class CleanupStatus(str, Enum):
    """Status of cleanup operation."""

    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"
    PARTIAL_FAILURE = "partial_failure"
    FORCE_DELETION_COMPLETE = "force_deletion_complete"


class CleanupReport(BaseModel):
    """Report from cleanup operations."""

    run_id: str = Field(..., description="Execution run ID")
    status: CleanupStatus = Field(..., description="Overall cleanup status")
    total_resources_expected: int = Field(default=0, description="Expected resource count")
    total_resources_deleted: int = Field(default=0, description="Successfully deleted count")
    deletions: list["ResourceDeletion"] = Field(  # Forward reference for circular import
        default_factory=list, description="Deletion records"
    )
    remaining_resources: list[Resource] = Field(
        default_factory=list, description="Resources not deleted"
    )
    service_principals_deleted: list[str] = Field(
        default_factory=list, description="Deleted SP names"
    )

    def has_failures(self) -> bool:
        """Check if cleanup report contains any failures."""
        return (
            any(d.status == "failed" for d in self.deletions) or len(self.remaining_resources) > 0
        )


# Rebuild model after all definitions are complete to resolve forward references
# This is safe because we use TYPE_CHECKING to prevent circular imports
def _rebuild_models():
    """Rebuild Pydantic models to resolve forward references."""
    try:
        from azure_haymaker.orchestrator.cleanup.resource_deletion import ResourceDeletion  # noqa: F401
        CleanupReport.model_rebuild()
    except ImportError:
        pass  # ResourceDeletion not yet available, will rebuild later


# Call rebuild function at module load time
_rebuild_models()


def _query_azure_resources(
    run_id: str,
    subscription_ids: list[str] | None = None,
    use_pagination: bool = False,
) -> list[Resource]:
    """Internal helper to query Azure Resource Graph for managed resources.

    Consolidates the common query logic used by query_managed_resources
    and verify_cleanup_complete.

    Args:
        run_id: Execution run ID to filter resources
        subscription_ids: List of subscription IDs to query (empty list for all)
        use_pagination: Whether to handle paginated results

    Returns:
        List of Resource objects matching the query
    """
    # Lazy import to avoid dependency requirement if module is only used with mocks
    from azure.mgmt.resourcegraph import ResourceGraphClient
    from azure.mgmt.resourcegraph.models import QueryRequest

    credentials = get_credential()
    resource_graph_client = ResourceGraphClient(credentials)

    # Build KQL query for managed resources
    query = (
        f"Resources "
        f"| where tags['AzureHayMaker-managed'] == 'true' "
        f"| where tags['RunId'] == '{run_id}' "
        f"| project id, type, name, tags"
    )

    resources: list[Resource] = []
    skip_token = None

    while True:
        query_request = QueryRequest(
            subscriptions=subscription_ids or [],
            query=query,
            skip_token=skip_token,
        )
        result = resource_graph_client.resources(query_request)

        # Convert to Resource objects
        if result.data and hasattr(result.data, "__iter__"):
            for item in result.data:  # pyright: ignore[reportGeneralTypeIssues]
                resource = Resource(
                    resource_id=item.get("id"),
                    resource_type=item.get("type"),
                    resource_name=item.get("name"),
                    scenario_name=item.get("tags", {}).get("Scenario", "unknown"),
                    run_id=run_id,
                    created_at=datetime.now(UTC),
                    tags=item.get("tags", {}),
                    status=ResourceStatus.EXISTS,
                )
                resources.append(resource)

        # Check if there are more results (only when pagination is enabled)
        if use_pagination and result.skip_token:
            skip_token = result.skip_token
        else:
            break

    return resources


async def query_managed_resources(subscription_id: str, run_id: str) -> list[Resource]:
    """Query Azure Resource Graph for AzureHayMaker-managed resources.

    Searches for all resources tagged with AzureHayMaker-managed matching
    the specified run ID. Handles pagination for large result sets.

    Args:
        subscription_id: Azure subscription ID to query
        run_id: Execution run ID to filter resources

    Returns:
        List of Resource objects matching the query

    Raises:
        CredentialError: If authentication fails
        CleanupError: If Resource Graph API call fails
    """
    try:
        resources = _query_azure_resources(
            run_id=run_id,
            subscription_ids=[subscription_id],
            use_pagination=True,
        )
        logger.info(f"Found {len(resources)} managed resources for run {run_id}")
        return resources
    except ClientAuthenticationError as e:
        logger.error(f"Authentication failed querying managed resources: {e}")
        raise CredentialError(
            f"Authentication failed querying managed resources: {e}",
            details={"run_id": run_id, "subscription_id": subscription_id},
        ) from e
    except HttpResponseError as e:
        logger.error(f"HTTP error querying managed resources: {e}")
        raise CleanupError(
            f"Failed to query managed resources: {e}",
            run_id=run_id,
        ) from e


async def verify_cleanup_complete(run_id: str) -> CleanupReport:
    """Verify that cleanup is complete by querying for remaining resources.

    Queries Azure Resource Graph for any resources still tagged as
    AzureHayMaker-managed for the given run ID. If resources remain,
    they will be included in the report for forced deletion.

    Args:
        run_id: Execution run ID to verify

    Returns:
        CleanupReport with verification results

    Raises:
        CredentialError: If authentication fails
        CleanupError: If Resource Graph query fails
    """
    try:
        # Query for remaining resources across all subscriptions (empty list)
        remaining_resources = _query_azure_resources(
            run_id=run_id,
            subscription_ids=[],  # Search all subscriptions
            use_pagination=False,
        )

        if not remaining_resources:
            status = CleanupStatus.VERIFIED
            logger.info(f"Cleanup verified for run {run_id}: all resources deleted")
        else:
            status = CleanupStatus.VERIFICATION_FAILED
            logger.warning(
                f"Cleanup verification failed for run {run_id}: "
                f"{len(remaining_resources)} resources remain"
            )

        return CleanupReport(
            run_id=run_id,
            status=status,
            remaining_resources=remaining_resources,
            total_resources_expected=len(remaining_resources),
            total_resources_deleted=0,
        )

    except ClientAuthenticationError as e:
        logger.error(f"Authentication failed verifying cleanup for run {run_id}: {e}")
        raise CredentialError(
            f"Authentication failed verifying cleanup: {e}",
            details={"run_id": run_id},
        ) from e
    except HttpResponseError as e:
        logger.error(f"HTTP error verifying cleanup for run {run_id}: {e}")
        raise CleanupError(
            f"Failed to verify cleanup: {e}",
            run_id=run_id,
        ) from e


__all__ = [
    "CleanupStatus",
    "CleanupReport",
    "query_managed_resources",
    "verify_cleanup_complete",
]
