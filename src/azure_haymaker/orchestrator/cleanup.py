"""Cleanup module for Azure HayMaker orchestrator.

This module handles cleanup verification, forced deletion of resources,
and service principal deletion after scenario execution. It queries Azure
Resource Graph for AzureHayMaker-managed resources, verifies cleanup completion,
and performs forced deletion with retry logic for dependencies.
"""

import asyncio
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.resource import ResourceManagementClient
from msgraph import GraphServiceClient
from pydantic import BaseModel, Field

from azure_haymaker.models.resource import Resource, ResourceStatus
from azure_haymaker.models.service_principal import ServicePrincipalDetails

# Lazy imports for optional dependencies used during actual Azure operations
if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CleanupStatus(str, Enum):
    """Status of cleanup operation."""

    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"
    PARTIAL_FAILURE = "partial_failure"
    FORCE_DELETION_COMPLETE = "force_deletion_complete"


class ResourceDeletion(BaseModel):
    """Record of a resource deletion attempt."""

    resource_id: str = Field(..., description="Full Azure resource ID")
    resource_type: str = Field(..., description="Azure resource type")
    status: str = Field(..., description="Deletion status (deleted/failed)")
    attempts: int = Field(default=1, description="Number of deletion attempts", ge=1)
    error: str | None = Field(default=None, description="Error message if failed")
    deleted_at: datetime | None = Field(default=None, description="Deletion completion time")


class CleanupReport(BaseModel):
    """Report from cleanup operations."""

    run_id: str = Field(..., description="Execution run ID")
    status: CleanupStatus = Field(..., description="Overall cleanup status")
    total_resources_expected: int = Field(default=0, description="Expected resource count")
    total_resources_deleted: int = Field(default=0, description="Successfully deleted count")
    deletions: list[ResourceDeletion] = Field(default_factory=list, description="Deletion records")
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
        Exception: If Resource Graph API call fails
    """
    # Lazy import to avoid dependency requirement if module is only used with mocks
    from azure.mgmt.resourcegraph import ResourceGraphClient
    from azure.mgmt.resourcegraph.models import QueryRequest

    credentials = DefaultAzureCredential()
    resource_graph_client = ResourceGraphClient(credentials)

    resources = []
    skip_token = None

    # Build KQL query for managed resources
    query = (
        f"Resources "
        f"| where tags['AzureHayMaker-managed'] == 'true' "
        f"| where tags['RunId'] == '{run_id}' "
        f"| project id, type, name, tags"
    )

    while True:
        try:
            query_request = QueryRequest(
                subscriptions=[subscription_id],
                query=query,
                skip_token=skip_token,
            )
            result = resource_graph_client.resources(query_request)

            # Convert to Resource objects
            for item in result.data:
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

            # Check if there are more results
            if result.skip_token:
                skip_token = result.skip_token
            else:
                break

        except Exception as e:
            logger.error(f"Failed to query managed resources: {e}")
            raise

    logger.info(f"Found {len(resources)} managed resources for run {run_id}")
    return resources


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
        Exception: If Resource Graph query fails
    """
    try:
        # Lazy import to avoid dependency requirement if module is only used with mocks
        from azure.mgmt.resourcegraph import ResourceGraphClient
        from azure.mgmt.resourcegraph.models import QueryRequest

        # Get subscription ID from environment or default
        credentials = DefaultAzureCredential()
        resource_graph_client = ResourceGraphClient(credentials)

        # Query for remaining resources - use subscription wildcard
        query = (
            f"Resources "
            f"| where tags['AzureHayMaker-managed'] == 'true' "
            f"| where tags['RunId'] == '{run_id}' "
            f"| project id, type, name, tags"
        )

        query_request = QueryRequest(
            subscriptions=[],  # Will search all subscriptions
            query=query,
        )

        result = resource_graph_client.resources(query_request)

        remaining_resources = []
        for item in result.data:
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
            remaining_resources.append(resource)

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

    except Exception as e:
        logger.error(f"Failed to verify cleanup for run {run_id}: {e}")
        raise


async def force_delete_resources(
    resources: list[Resource],
    sp_details: list[ServicePrincipalDetails] | None = None,
    kv_client: SecretClient | None = None,
    subscription_id: str | None = None,
) -> CleanupReport:
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
    if not resources:
        return CleanupReport(
            run_id="",
            status=CleanupStatus.VERIFIED,
            total_resources_expected=0,
            total_resources_deleted=0,
        )

    # Extract subscription ID from first resource if not provided
    if not subscription_id:
        # Extract from resource ID: /subscriptions/{subscriptionId}/...
        parts = resources[0].resource_id.split("/")
        if "subscriptions" in parts:
            idx = parts.index("subscriptions")
            subscription_id = parts[idx + 1] if idx + 1 < len(parts) else ""

    credentials = DefaultAzureCredential()
    resource_client = ResourceManagementClient(credentials, subscription_id or "")

    deletions = []
    run_id = resources[0].run_id if resources else ""

    # Delete resources with retry logic
    for resource in resources:
        deletion_record = await _delete_resource_with_retry(resource, resource_client)
        deletions.append(deletion_record)

    # Delete service principals if provided
    deleted_sps = []
    if sp_details and kv_client:
        deleted_sps = await _delete_service_principals(sp_details, kv_client)

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

            # Start async deletion
            poller = resource_client.resources.begin_delete_by_id(
                resource_id=resource.resource_id,
                api_version="2021-04-01",
            )

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

        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"Deletion attempt {attempts}/{max_retries} failed for {resource.resource_id}: {e}"
            )

            # Check if error suggests dependency issue
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
                # Non-retryable error
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


async def _delete_service_principals(
    sp_details: list[ServicePrincipalDetails],
    kv_client: SecretClient,
) -> list[str]:
    """Delete service principals and their Key Vault secrets.

    Args:
        sp_details: List of service principal details to delete
        kv_client: Key Vault client for deleting secrets

    Returns:
        List of deleted service principal names
    """
    credentials = DefaultAzureCredential()
    graph_client = GraphServiceClient(credentials)

    deleted_sps = []

    for sp in sp_details:
        try:
            # Find SP by display name
            filter_query = f"displayName eq '{sp.sp_name}'"
            sp_list = await asyncio.to_thread(
                graph_client.service_principals.get,
                filter=filter_query,
            )

            if sp_list and sp_list.value:
                sp_obj = sp_list.value[0]
                # Delete the SP
                await asyncio.to_thread(
                    graph_client.service_principals.by_service_principal_id(sp_obj.id).delete
                )
                logger.info(f"Deleted service principal {sp.sp_name}")
                deleted_sps.append(sp.sp_name)

            # Delete Key Vault secret
            try:
                kv_client.begin_delete_secret(sp.secret_reference)
                logger.info(f"Deleted Key Vault secret {sp.secret_reference}")
            except ResourceNotFoundError:
                logger.warning(f"Key Vault secret {sp.secret_reference} not found")

        except Exception as e:
            logger.error(f"Failed to delete service principal {sp.sp_name}: {e}")

    return deleted_sps


__all__ = [
    "CleanupStatus",
    "ResourceDeletion",
    "CleanupReport",
    "query_managed_resources",
    "verify_cleanup_complete",
    "force_delete_resources",
]
