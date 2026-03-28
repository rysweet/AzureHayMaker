"""Resource deletion with retry logic for Azure HayMaker cleanup.

This module handles deletion of Azure resources with intelligent retry
logic for dependency handling and idempotent behavior.

Philosophy:
- Single responsibility: Resource deletion only
- Retry with exponential backoff for dependencies
- Self-contained and regeneratable

Public API (the "studs"):
    ResourceDeletion: Record of a resource deletion attempt
    force_delete_resources: Delete resources with retry logic
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.keyvault.secrets import SecretClient
from azure.mgmt.resource import ResourceManagementClient
from pydantic import BaseModel, Field

from azure_haymaker.models.resource import Resource
from azure_haymaker.models.service_principal import ServicePrincipalDetails
from azure_haymaker.utils.credentials import get_credential

# Import at runtime to avoid circular dependency
if TYPE_CHECKING:
    from azure_haymaker.orchestrator.cleanup.resource_graph import CleanupReport, CleanupStatus

logger = logging.getLogger(__name__)


class ResourceDeletion(BaseModel):
    """Record of a resource deletion attempt."""

    resource_id: str = Field(..., description="Full Azure resource ID")
    resource_type: str = Field(..., description="Azure resource type")
    status: str = Field(..., description="Deletion status (deleted/failed)")
    attempts: int = Field(default=1, description="Number of deletion attempts", ge=1)
    error: str | None = Field(default=None, description="Error message if failed")
    deleted_at: datetime | None = Field(default=None, description="Deletion completion time")


async def force_delete_resources(
    resources: list[Resource],
    sp_details: list[ServicePrincipalDetails] | None = None,
    kv_client: SecretClient | None = None,
    subscription_id: str | None = None,
) -> "CleanupReport":
    """Force delete remaining resources with retry logic for dependencies.

    Attempts to delete each resource, retrying up to 5 times for resources
    with dependencies. Resources not found are treated as successfully deleted.
    Also deletes associated service principals if provided.

    Args:
        resources: List of Resource objects to delete
        sp_details: Optional list of service principals to delete
        kv_client: Optional Key Vault client for deleting secrets
        subscription_id: Optional subscription ID (extracted from first resource if not provided)

    Returns:
        CleanupReport with deletion status for each resource

    Raises:
        Exception: If resource management fails
    """
    # Import at runtime to avoid circular dependency
    from azure_haymaker.orchestrator.cleanup.resource_graph import CleanupReport, CleanupStatus
    from azure_haymaker.orchestrator.cleanup.sp_cleanup import delete_service_principals

    # Delete service principals first if provided (independent of resources)
    deleted_sps = []
    if sp_details and kv_client:
        deleted_sps = await delete_service_principals(sp_details, kv_client)

    # Early return if no resources to delete
    if not resources:
        return CleanupReport(
            run_id="",
            status=CleanupStatus.VERIFIED,
            total_resources_expected=0,
            total_resources_deleted=0,
            service_principals_deleted=deleted_sps,
        )

    # Extract subscription ID from first resource if not provided
    if not subscription_id:
        # Extract from resource ID: /subscriptions/{subscriptionId}/...
        parts = resources[0].resource_id.split("/")
        if "subscriptions" in parts:
            idx = parts.index("subscriptions")
            subscription_id = parts[idx + 1] if idx + 1 < len(parts) else ""

    credentials = get_credential()
    resource_client = ResourceManagementClient(credentials, subscription_id or "")

    deletions = []
    run_id = resources[0].run_id if resources else ""

    # Delete resources with retry logic
    for resource in resources:
        deletion_record = await _delete_resource_with_retry(resource, resource_client)
        deletions.append(deletion_record)

    # Count successful deletions
    successful_deletions = sum(1 for d in deletions if d.status == "deleted")

    # Determine overall status
    if successful_deletions == len(resources):
        status = CleanupStatus.VERIFIED
    elif successful_deletions > 0:
        status = CleanupStatus.PARTIAL_FAILURE
    else:
        status = CleanupStatus.FORCE_DELETION_COMPLETE

    report = CleanupReport(
        run_id=run_id,
        status=status,
        total_resources_expected=len(resources),
        total_resources_deleted=successful_deletions,
        deletions=deletions,
        service_principals_deleted=deleted_sps,
    )

    logger.info(
        f"Force delete completed for run {run_id}: "
        f"{successful_deletions}/{len(resources)} resources deleted"
    )

    return report


async def _delete_resource_with_retry(
    resource: Resource,
    resource_client: ResourceManagementClient,
    max_retries: int = 5,
) -> ResourceDeletion:
    """Delete a single resource with retry logic for dependency errors.

    Attempts deletion up to max_retries times with exponential backoff.
    Resources not found are treated as successfully deleted.

    Args:
        resource: Resource to delete
        resource_client: Azure ResourceManagementClient
        max_retries: Maximum number of deletion attempts

    Returns:
        ResourceDeletion record with status
    """
    attempts = 0
    last_error = None

    for attempt in range(max_retries):
        attempts = attempt + 1
        try:
            logger.info(
                f"Attempting to delete resource {resource.resource_id} (attempt {attempts})"
            )

            # Use generic resource deletion API
            # Note: begin_delete_by_id exists but has typing issues in Azure SDK
            try:
                poller = resource_client.resources.begin_delete_by_id(  # type: ignore[attr-defined]  # Method exists but typing is incomplete
                    resource_id=resource.resource_id,
                    api_version="2023-07-01",
                )
            except (AttributeError, TypeError) as e:
                # Fallback: If begin_delete_by_id doesn't exist or has issues
                logger.error(f"Cannot delete resource {resource.resource_id}: {e}")
                raise ValueError(
                    f"Resource deletion not supported for {resource.resource_id}"
                ) from e

            # Wait for deletion to complete
            poller.result(timeout=300)

            logger.info(f"Successfully deleted resource {resource.resource_id}")
            return ResourceDeletion(
                resource_id=resource.resource_id,
                resource_type=resource.resource_type,
                status="deleted",
                attempts=attempts,
                deleted_at=datetime.now(UTC),
            )

        except ResourceNotFoundError:
            # Resource already deleted - treat as success
            logger.info(f"Resource {resource.resource_id} not found (already deleted)")
            return ResourceDeletion(
                resource_id=resource.resource_id,
                resource_type=resource.resource_type,
                status="deleted",
                attempts=attempts,
                deleted_at=datetime.now(UTC),
            )

        except ClientAuthenticationError as e:
            last_error = str(e)
            logger.error(f"Authentication failed deleting resource {resource.resource_id}: {e}")
            break  # Auth errors are not retryable
        except HttpResponseError as e:
            last_error = str(e)
            logger.warning(
                f"Deletion attempt {attempts}/{max_retries} failed for {resource.resource_id}: {e}"
            )

            # Check if error suggests dependency issue (retryable)
            error_msg = str(e).lower()
            if (
                "conflict" in error_msg
                or "contains" in error_msg
                or "dependency" in error_msg
                or "locked" in error_msg
            ):
                # Wait before retry with exponential backoff
                if attempt < max_retries - 1:
                    wait_seconds = min(2**attempt, 60)
                    logger.info(f"Waiting {wait_seconds}s before retry...")
                    await asyncio.sleep(wait_seconds)
            else:
                # Non-retryable HTTP error
                logger.error(f"Non-retryable error for resource {resource.resource_id}: {e}")
                break

    # All retries exhausted
    logger.error(
        f"Failed to delete resource {resource.resource_id} after {max_retries} attempts: {last_error}"
    )
    return ResourceDeletion(
        resource_id=resource.resource_id,
        resource_type=resource.resource_type,
        status="failed",
        attempts=attempts,
        error=last_error,
    )


__all__ = [
    "ResourceDeletion",
    "force_delete_resources",
]
