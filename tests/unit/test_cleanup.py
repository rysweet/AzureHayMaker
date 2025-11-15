"""Tests for Cleanup Manager.

This module tests the cleanup verification, forced deletion of resources,
and service principal deletion after scenario execution.
"""

import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.models.resource import Resource
from azure_haymaker.models.service_principal import ServicePrincipalDetails
from azure_haymaker.orchestrator.cleanup import (
    CleanupReport,
    CleanupStatus,
    ResourceDeletion,
    force_delete_resources,
    query_managed_resources,
    verify_cleanup_complete,
)

# Mock azure.mgmt.resourcegraph module for testing
mock_resourcegraph = MagicMock()
sys.modules["azure.mgmt.resourcegraph"] = mock_resourcegraph
sys.modules["azure.mgmt.resourcegraph.models"] = mock_resourcegraph.models


class TestQueryManagedResources:
    """Test querying Azure Resource Graph for AzureHayMaker-managed resources."""

    @pytest.mark.asyncio
    async def test_query_managed_resources_success(self):
        """Test successful query of managed resources."""
        run_id = "test-run-123"
        subscription_id = "sub-12345"

        # Create mock resources
        mock_resources = [
            {
                "id": "/subscriptions/sub-12345/resourceGroups/haymaker-rg-1",
                "type": "Microsoft.Resources/resourceGroups",
                "name": "haymaker-rg-1",
                "tags": {"AzureHayMaker-managed": "true", "RunId": run_id},
            },
            {
                "id": "/subscriptions/sub-12345/resourceGroups/haymaker-rg-1/providers/Microsoft.Storage/storageAccounts/st1",
                "type": "Microsoft.Storage/storageAccounts",
                "name": "st1",
                "tags": {"AzureHayMaker-managed": "true", "RunId": run_id},
            },
        ]

        mock_resource_graph_client = MagicMock()
        mock_query_result = MagicMock()
        mock_query_result.data = mock_resources
        mock_query_result.total_records = 2
        mock_query_result.skip_token = None
        mock_resource_graph_client.resources.return_value = mock_query_result

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=mock_resource_graph_client
        ):
            result = await query_managed_resources(subscription_id, run_id)

        assert len(result) == 2
        assert result[0].resource_id == "/subscriptions/sub-12345/resourceGroups/haymaker-rg-1"
        assert result[0].resource_type == "Microsoft.Resources/resourceGroups"
        assert result[0].run_id == run_id
        assert result[1].resource_name == "st1"

    @pytest.mark.asyncio
    async def test_query_managed_resources_empty_result(self):
        """Test query returns empty list when no resources found."""
        run_id = "test-run-empty"
        subscription_id = "sub-12345"

        mock_resource_graph_client = MagicMock()
        mock_query_result = MagicMock()
        mock_query_result.data = []
        mock_query_result.total_records = 0
        mock_query_result.skip_token = None
        mock_resource_graph_client.resources.return_value = mock_query_result

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=mock_resource_graph_client
        ):
            result = await query_managed_resources(subscription_id, run_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_query_managed_resources_filters_by_run_id(self):
        """Test that query filters resources by run ID."""
        run_id = "test-run-123"
        subscription_id = "sub-12345"

        mock_resource_graph_client = MagicMock()
        mock_query_result = MagicMock()
        mock_query_result.data = []
        mock_query_result.skip_token = None
        mock_resource_graph_client.resources.return_value = mock_query_result

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=mock_resource_graph_client
        ):
            await query_managed_resources(subscription_id, run_id)

        # Verify the resources method was called
        assert mock_resource_graph_client.resources.called
        # Verify the call was made with proper arguments
        call_args = mock_resource_graph_client.resources.call_args
        if call_args and call_args[0]:
            query_request = call_args[0][0]
            query_string = query_request.query
            assert run_id in query_string
            assert "AzureHayMaker-managed" in query_string

    @pytest.mark.asyncio
    async def test_query_managed_resources_pagination(self):
        """Test query handles paginated results."""
        run_id = "test-run-paginated"
        subscription_id = "sub-12345"

        # Create mock resources across multiple pages
        page1_resources = [
            {
                "id": f"/subscriptions/sub/resource-{i}",
                "type": "type",
                "name": f"res-{i}",
                "tags": {},
            }
            for i in range(100)
        ]
        page2_resources = [
            {
                "id": f"/subscriptions/sub/resource-{i}",
                "type": "type",
                "name": f"res-{i}",
                "tags": {},
            }
            for i in range(100, 150)
        ]

        mock_resource_graph_client = MagicMock()
        mock_query_result1 = MagicMock()
        mock_query_result1.data = page1_resources
        mock_query_result1.total_records = 150
        mock_query_result1.skip_token = "token-page-2"

        mock_query_result2 = MagicMock()
        mock_query_result2.data = page2_resources
        mock_query_result2.total_records = 150
        mock_query_result2.skip_token = None

        # First call returns first page, then second page
        mock_resource_graph_client.resources.side_effect = [mock_query_result1, mock_query_result2]

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=mock_resource_graph_client
        ):
            result = await query_managed_resources(subscription_id, run_id)

        # Should have collected resources from both pages
        assert len(result) == 150

    @pytest.mark.asyncio
    async def test_query_managed_resources_api_error(self):
        """Test handling of Resource Graph API errors."""
        run_id = "test-run-error"
        subscription_id = "sub-12345"

        mock_resource_graph_client = MagicMock()
        mock_resource_graph_client.resources.side_effect = Exception("API error")

        with (
            patch(
                "azure.mgmt.resourcegraph.ResourceGraphClient",
                return_value=mock_resource_graph_client,
            ),
            pytest.raises(Exception, match="API error"),
        ):
            await query_managed_resources(subscription_id, run_id)


class TestVerifyCleanupComplete:
    """Test verification that cleanup is complete."""

    @pytest.mark.asyncio
    async def test_verify_cleanup_complete_all_deleted(self):
        """Test verification succeeds when all resources are deleted."""
        run_id = "test-run-clean"

        mock_resource_graph_client = MagicMock()
        mock_query_result = MagicMock()
        mock_query_result.data = []  # No resources found
        mock_query_result.total_records = 0
        mock_resource_graph_client.resources.return_value = mock_query_result

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=mock_resource_graph_client
        ):
            report = await verify_cleanup_complete(run_id)

        assert report.status == CleanupStatus.VERIFIED
        assert report.remaining_resources == []
        assert len(report.remaining_resources) == 0

    @pytest.mark.asyncio
    async def test_verify_cleanup_complete_resources_remain(self):
        """Test verification detects remaining resources."""
        run_id = "test-run-remaining"

        mock_resources = [
            {
                "id": "/subscriptions/sub/resourceGroups/haymaker-rg-1",
                "type": "Microsoft.Resources/resourceGroups",
                "name": "haymaker-rg-1",
                "tags": {"AzureHayMaker-managed": "true", "RunId": run_id},
            },
            {
                "id": "/subscriptions/sub/resourceGroups/haymaker-rg-1/providers/Microsoft.Storage/storageAccounts/st1",
                "type": "Microsoft.Storage/storageAccounts",
                "name": "st1",
                "tags": {"AzureHayMaker-managed": "true", "RunId": run_id},
            },
        ]

        mock_resource_graph_client = MagicMock()
        mock_query_result = MagicMock()
        mock_query_result.data = mock_resources
        mock_query_result.total_records = 2
        mock_resource_graph_client.resources.return_value = mock_query_result

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=mock_resource_graph_client
        ):
            report = await verify_cleanup_complete(run_id)

        assert report.status == CleanupStatus.VERIFICATION_FAILED
        assert len(report.remaining_resources) == 2
        assert report.remaining_resources[0].resource_id == mock_resources[0]["id"]

    @pytest.mark.asyncio
    async def test_verify_cleanup_complete_partial_deletion(self):
        """Test verification when some resources remain."""
        run_id = "test-run-partial"

        # Only one resource remains
        mock_resources = [
            {
                "id": "/subscriptions/sub/resourceGroups/haymaker-rg-1",
                "type": "Microsoft.Resources/resourceGroups",
                "name": "haymaker-rg-1",
                "tags": {"AzureHayMaker-managed": "true", "RunId": run_id},
            },
        ]

        mock_resource_graph_client = MagicMock()
        mock_query_result = MagicMock()
        mock_query_result.data = mock_resources
        mock_query_result.total_records = 1
        mock_resource_graph_client.resources.return_value = mock_query_result

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=mock_resource_graph_client
        ):
            report = await verify_cleanup_complete(run_id)

        assert report.status == CleanupStatus.VERIFICATION_FAILED
        assert len(report.remaining_resources) == 1

    @pytest.mark.asyncio
    async def test_verify_cleanup_complete_api_error(self):
        """Test verification handles API errors gracefully."""
        run_id = "test-run-verify-error"

        mock_resource_graph_client = MagicMock()
        mock_resource_graph_client.resources.side_effect = Exception("Query failed")

        with (
            patch(
                "azure.mgmt.resourcegraph.ResourceGraphClient",
                return_value=mock_resource_graph_client,
            ),
            pytest.raises(Exception, match="Query failed"),
        ):
            await verify_cleanup_complete(run_id)

    @pytest.mark.asyncio
    async def test_verify_cleanup_complete_includes_resource_details(self):
        """Test verification report includes all resource details."""
        run_id = "test-run-details"

        mock_resources = [
            {
                "id": "/subscriptions/sub-123/resourceGroups/rg-1",
                "type": "Microsoft.Resources/resourceGroups",
                "name": "rg-1",
                "tags": {
                    "AzureHayMaker-managed": "true",
                    "RunId": run_id,
                    "Scenario": "scenario-1",
                },
            },
        ]

        mock_resource_graph_client = MagicMock()
        mock_query_result = MagicMock()
        mock_query_result.data = mock_resources
        mock_query_result.total_records = 1
        mock_resource_graph_client.resources.return_value = mock_query_result

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=mock_resource_graph_client
        ):
            report = await verify_cleanup_complete(run_id)

        assert report.remaining_resources[0].resource_name == "rg-1"
        assert report.remaining_resources[0].resource_type == "Microsoft.Resources/resourceGroups"


class TestForceDeleteResources:
    """Test forced deletion of remaining resources."""

    @pytest.mark.asyncio
    async def test_force_delete_resources_success(self):
        """Test successful deletion of all resources."""
        resources = [
            Resource(
                resource_id="/subscriptions/sub-12345/resourceGroups/rg-1",
                resource_type="Microsoft.Resources/resourceGroups",
                resource_name="rg-1",
                scenario_name="scenario-1",
                run_id="run-123",
                created_at=datetime.now(UTC),
                tags={"AzureHayMaker-managed": "true"},
            ),
        ]

        mock_resource_client = MagicMock()
        mock_poller = MagicMock()
        mock_poller.result.return_value = None
        mock_resource_client.resources.begin_delete_by_id.return_value = mock_poller

        with (
            patch(
                "azure.mgmt.resource.ResourceManagementClient", return_value=mock_resource_client
            ),
            patch("azure_haymaker.orchestrator.cleanup.DefaultAzureCredential"),
        ):
            result = await force_delete_resources(resources, subscription_id="sub-12345")

        assert len(result.deletions) == 1
        assert result.deletions[0].status == "deleted"
        assert result.deletions[0].attempts == 1

    @pytest.mark.asyncio
    async def test_force_delete_resources_empty_list(self):
        """Test force delete with empty resource list."""
        result = await force_delete_resources([])

        assert len(result.deletions) == 0

    @pytest.mark.asyncio
    async def test_force_delete_resources_retry_on_dependency_error(self):
        """Test retry logic for resources with dependencies."""
        resources = [
            Resource(
                resource_id="/subscriptions/sub/resourceGroups/rg-1",
                resource_type="Microsoft.Resources/resourceGroups",
                resource_name="rg-1",
                scenario_name="scenario-1",
                run_id="run-123",
                created_at=datetime.now(UTC),
                tags={"AzureHayMaker-managed": "true"},
            ),
        ]

        mock_resource_client = MagicMock()
        mock_poller = MagicMock()

        # First call fails with dependency error, second succeeds
        error = Exception("Conflict: The resource group contains resources and cannot be deleted")
        mock_poller.result.side_effect = [error, None]
        mock_resource_client.resources.begin_delete_by_id.return_value = mock_poller

        with (
            patch(
                "azure.mgmt.resource.ResourceManagementClient", return_value=mock_resource_client
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await force_delete_resources(resources)

        assert len(result.deletions) == 1
        # Should have retried
        assert result.deletions[0].attempts >= 1

    @pytest.mark.asyncio
    async def test_force_delete_resources_max_retries(self):
        """Test max retry limit is respected."""
        resources = [
            Resource(
                resource_id="/subscriptions/sub/resourceGroups/rg-1",
                resource_type="Microsoft.Resources/resourceGroups",
                resource_name="rg-1",
                scenario_name="scenario-1",
                run_id="run-123",
                created_at=datetime.now(UTC),
                tags={"AzureHayMaker-managed": "true"},
            ),
        ]

        mock_resource_client = MagicMock()
        mock_poller = MagicMock()

        # All deletion attempts fail
        error = Exception("Conflict: The resource group contains resources and cannot be deleted")
        mock_poller.result.side_effect = [error] * 10
        mock_resource_client.resources.begin_delete_by_id.return_value = mock_poller

        with (
            patch(
                "azure.mgmt.resource.ResourceManagementClient", return_value=mock_resource_client
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await force_delete_resources(resources)

        assert len(result.deletions) == 1
        assert result.deletions[0].status == "failed"
        assert result.deletions[0].error is not None

    @pytest.mark.asyncio
    async def test_force_delete_resources_multiple_resources(self):
        """Test deletion of multiple resources."""
        resources = [
            Resource(
                resource_id=f"/subscriptions/sub-12345/resourceGroups/rg-{i}",
                resource_type="Microsoft.Resources/resourceGroups",
                resource_name=f"rg-{i}",
                scenario_name="scenario-1",
                run_id="run-123",
                created_at=datetime.now(UTC),
                tags={"AzureHayMaker-managed": "true"},
            )
            for i in range(3)
        ]

        mock_resource_client = MagicMock()
        mock_poller = MagicMock()
        mock_poller.result.return_value = None
        mock_resource_client.resources.begin_delete_by_id.return_value = mock_poller

        with (
            patch(
                "azure.mgmt.resource.ResourceManagementClient", return_value=mock_resource_client
            ),
            patch("azure_haymaker.orchestrator.cleanup.DefaultAzureCredential"),
        ):
            result = await force_delete_resources(resources, subscription_id="sub-12345")

        assert len(result.deletions) == 3
        assert all(d.status == "deleted" for d in result.deletions)

    @pytest.mark.asyncio
    async def test_force_delete_resources_not_found_treated_as_success(self):
        """Test that resource not found errors are treated as successful deletion."""
        resources = [
            Resource(
                resource_id="/subscriptions/sub-12345/resourceGroups/rg-1",
                resource_type="Microsoft.Resources/resourceGroups",
                resource_name="rg-1",
                scenario_name="scenario-1",
                run_id="run-123",
                created_at=datetime.now(UTC),
                tags={"AzureHayMaker-managed": "true"},
            ),
        ]

        mock_resource_client = MagicMock()
        mock_poller = MagicMock()
        # Resource not found error (already deleted)
        mock_poller.result.side_effect = ResourceNotFoundError("Resource not found")
        mock_resource_client.resources.begin_delete_by_id.return_value = mock_poller

        with (
            patch(
                "azure.mgmt.resource.ResourceManagementClient", return_value=mock_resource_client
            ),
            patch("azure_haymaker.orchestrator.cleanup.DefaultAzureCredential"),
        ):
            result = await force_delete_resources(resources, subscription_id="sub-12345")

        assert len(result.deletions) == 1
        # Should treat as success since resource is gone
        assert result.deletions[0].status == "deleted"

    @pytest.mark.asyncio
    async def test_force_delete_resources_deleted_at_updated(self):
        """Test that deleted_at timestamp is recorded."""
        before_delete = datetime.now(UTC)

        resources = [
            Resource(
                resource_id="/subscriptions/sub-12345/resourceGroups/rg-1",
                resource_type="Microsoft.Resources/resourceGroups",
                resource_name="rg-1",
                scenario_name="scenario-1",
                run_id="run-123",
                created_at=datetime.now(UTC),
                tags={"AzureHayMaker-managed": "true"},
            ),
        ]

        mock_resource_client = MagicMock()
        mock_poller = MagicMock()
        mock_poller.result.return_value = None
        mock_resource_client.resources.begin_delete_by_id.return_value = mock_poller

        with (
            patch(
                "azure.mgmt.resource.ResourceManagementClient", return_value=mock_resource_client
            ),
            patch("azure_haymaker.orchestrator.cleanup.DefaultAzureCredential"),
        ):
            result = await force_delete_resources(resources, subscription_id="sub-12345")

        after_delete = datetime.now(UTC)

        deletion = result.deletions[0]
        assert deletion.status == "deleted"
        # deleted_at timestamp should be set and within reasonable range
        assert before_delete <= deletion.deleted_at <= after_delete

    @pytest.mark.asyncio
    async def test_force_delete_service_principals(self):
        """Test deletion of associated service principals."""
        sp_details = [
            ServicePrincipalDetails(
                sp_name="AzureHayMaker-scenario-1-admin",
                client_id="client-123",
                principal_id="principal-123",
                secret_reference="secret-ref-1",
                created_at="2025-11-14T12:00:00Z",
            ),
        ]

        mock_resource_client = MagicMock()
        mock_poller = MagicMock()
        mock_poller.result.return_value = None
        mock_resource_client.resources.begin_delete_by_id.return_value = mock_poller

        mock_graph_client = MagicMock()
        mock_sp_list = MagicMock()
        mock_sp = MagicMock()
        mock_sp.id = "sp-obj-id"
        mock_sp_list.value = [mock_sp]
        mock_graph_client.service_principals.get.return_value = mock_sp_list
        mock_graph_client.service_principals.by_service_principal_id().delete.return_value = None

        mock_kv_client = AsyncMock()

        with (
            patch(
                "azure.mgmt.resource.ResourceManagementClient", return_value=mock_resource_client
            ),
            patch("msgraph.GraphServiceClient", return_value=mock_graph_client),
            patch("azure_haymaker.orchestrator.cleanup.DefaultAzureCredential"),
        ):
            result = await force_delete_resources(
                [], sp_details=sp_details, kv_client=mock_kv_client, subscription_id="sub-12345"
            )

        # Verify result is empty (no resources to delete)
        assert len(result.deletions) == 0
        # Verify SP deletion was attempted
        assert mock_graph_client.service_principals.by_service_principal_id().delete.called


class TestCleanupReport:
    """Test CleanupReport dataclass."""

    def test_cleanup_report_creation(self):
        """Test creating CleanupReport."""
        deletion = ResourceDeletion(
            resource_id="/subscriptions/sub/resourceGroups/rg-1",
            resource_type="Microsoft.Resources/resourceGroups",
            status="deleted",
            attempts=1,
            deleted_at=datetime.now(UTC),
        )

        report = CleanupReport(
            run_id="run-123",
            status=CleanupStatus.VERIFIED,
            total_resources_expected=1,
            total_resources_deleted=1,
            deletions=[deletion],
        )

        assert report.run_id == "run-123"
        assert report.status == CleanupStatus.VERIFIED
        assert len(report.deletions) == 1

    def test_cleanup_report_has_failures(self):
        """Test cleanup report failure detection."""
        deletions = [
            ResourceDeletion(
                resource_id="/subscriptions/sub/resourceGroups/rg-1",
                resource_type="Microsoft.Resources/resourceGroups",
                status="deleted",
                attempts=1,
                deleted_at=datetime.now(UTC),
            ),
            ResourceDeletion(
                resource_id="/subscriptions/sub/resourceGroups/rg-2",
                resource_type="Microsoft.Resources/resourceGroups",
                status="failed",
                attempts=3,
                error="Resource still has locks",
            ),
        ]

        report = CleanupReport(
            run_id="run-123",
            status=CleanupStatus.PARTIAL_FAILURE,
            total_resources_expected=2,
            total_resources_deleted=1,
            deletions=deletions,
        )

        assert report.has_failures() is True

    def test_cleanup_report_no_failures(self):
        """Test cleanup report success detection."""
        deletions = [
            ResourceDeletion(
                resource_id="/subscriptions/sub/resourceGroups/rg-1",
                resource_type="Microsoft.Resources/resourceGroups",
                status="deleted",
                attempts=1,
                deleted_at=datetime.now(UTC),
            ),
        ]

        report = CleanupReport(
            run_id="run-123",
            status=CleanupStatus.VERIFIED,
            total_resources_expected=1,
            total_resources_deleted=1,
            deletions=deletions,
        )

        assert report.has_failures() is False
