"""Unit tests for resources_api module.

Tests for API endpoints that manage resource queries and tracking.
Following the testing pyramid: 60% unit tests, 30% integration tests, 10% E2E tests.

This module tests:
- ResourceInfo model validation
- query_resources_from_table function
- list_resources endpoint
- get_resource endpoint
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from azure_haymaker.orchestrator.resources_api import (
    ResourceInfo,
    query_resources_from_table,
)


class TestResourceInfoModel:
    """Tests for ResourceInfo Pydantic model."""

    def test_resource_info_required_fields(self) -> None:
        """Test ResourceInfo with required fields only."""
        now = datetime.now(UTC)
        resource = ResourceInfo(
            id="res-123",
            name="test-vm",
            type="Microsoft.Compute/virtualMachines",
            scenario="compute-01",
            execution_id="exec-456",
            created_at=now,
        )
        assert resource.id == "res-123"
        assert resource.name == "test-vm"
        assert resource.type == "Microsoft.Compute/virtualMachines"
        assert resource.scenario == "compute-01"
        assert resource.execution_id == "exec-456"
        assert resource.created_at == now
        assert resource.deleted_at is None
        assert resource.status == "created"  # Default value
        assert resource.tags == {}  # Default value

    def test_resource_info_all_fields(self) -> None:
        """Test ResourceInfo with all fields populated."""
        created = datetime.now(UTC)
        deleted = datetime.now(UTC)
        resource = ResourceInfo(
            id="res-789",
            name="test-storage",
            type="Microsoft.Storage/storageAccounts",
            scenario="storage-02",
            execution_id="exec-012",
            created_at=created,
            deleted_at=deleted,
            status="deleted",
            tags={"environment": "test", "owner": "test-user"},
        )
        assert resource.deleted_at == deleted
        assert resource.status == "deleted"
        assert resource.tags == {"environment": "test", "owner": "test-user"}

    def test_resource_info_status_values(self) -> None:
        """Test ResourceInfo with different status values."""
        now = datetime.now(UTC)
        for status in ["created", "exists", "deleted", "deletion_failed"]:
            resource = ResourceInfo(
                id="res-123",
                name="test",
                type="Microsoft.Test/test",
                scenario="test",
                execution_id="exec-123",
                created_at=now,
                status=status,
            )
            assert resource.status == status


class TestQueryResourcesFromTable:
    """Tests for query_resources_from_table function."""

    @pytest.mark.asyncio
    async def test_query_resources_basic(self) -> None:
        """Test basic resource query with tenant_id."""
        mock_table_client = MagicMock()
        mock_entity = {
            "resource_id": "res-123",
            "resource_name": "test-vm",
            "resource_type": "Microsoft.Compute/virtualMachines",
            "scenario": "compute-01",
            "execution_id": "exec-456",
            "created_at": datetime.now(UTC),
            "deleted_at": None,
            "status": "created",
        }
        mock_table_client.query_entities.return_value = [mock_entity]

        resources = await query_resources_from_table(mock_table_client, tenant_id="tenant-123")

        assert len(resources) == 1
        assert resources[0].id == "res-123"
        assert resources[0].name == "test-vm"
        mock_table_client.query_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_resources_with_execution_filter(self) -> None:
        """Test resource query with execution_id filter."""
        mock_table_client = MagicMock()
        mock_table_client.query_entities.return_value = []

        await query_resources_from_table(
            mock_table_client, tenant_id="tenant-123", execution_id="exec-456"
        )

        call_kwargs = mock_table_client.query_entities.call_args[1]
        assert "execution_id eq 'exec-456'" in call_kwargs["query_filter"]

    @pytest.mark.asyncio
    async def test_query_resources_with_scenario_filter(self) -> None:
        """Test resource query with scenario filter."""
        mock_table_client = MagicMock()
        mock_table_client.query_entities.return_value = []

        await query_resources_from_table(
            mock_table_client, tenant_id="tenant-123", scenario="compute-01"
        )

        call_kwargs = mock_table_client.query_entities.call_args[1]
        assert "scenario eq 'compute-01'" in call_kwargs["query_filter"]

    @pytest.mark.asyncio
    async def test_query_resources_with_status_filter(self) -> None:
        """Test resource query with status filter."""
        mock_table_client = MagicMock()
        mock_table_client.query_entities.return_value = []

        await query_resources_from_table(
            mock_table_client, tenant_id="tenant-123", status="deleted"
        )

        call_kwargs = mock_table_client.query_entities.call_args[1]
        assert "status eq 'deleted'" in call_kwargs["query_filter"]

    @pytest.mark.asyncio
    async def test_query_resources_with_multiple_filters(self) -> None:
        """Test resource query with multiple filters combined."""
        mock_table_client = MagicMock()
        mock_table_client.query_entities.return_value = []

        await query_resources_from_table(
            mock_table_client,
            tenant_id="tenant-123",
            execution_id="exec-456",
            scenario="compute-01",
            status="created",
        )

        call_kwargs = mock_table_client.query_entities.call_args[1]
        query_filter = call_kwargs["query_filter"]
        assert "PartitionKey eq 'tenant-123'" in query_filter
        assert "execution_id eq 'exec-456'" in query_filter
        assert "scenario eq 'compute-01'" in query_filter
        assert "status eq 'created'" in query_filter

    @pytest.mark.asyncio
    async def test_query_resources_respects_limit(self) -> None:
        """Test that query respects the limit parameter."""
        mock_table_client = MagicMock()
        mock_entities = [
            {
                "resource_id": f"res-{i}",
                "resource_name": f"resource-{i}",
                "resource_type": "Microsoft.Test/test",
                "scenario": "test",
                "execution_id": "exec-123",
                "created_at": datetime.now(UTC),
                "status": "created",
            }
            for i in range(10)
        ]
        mock_table_client.query_entities.return_value = mock_entities

        resources = await query_resources_from_table(
            mock_table_client, tenant_id="tenant-123", limit=5
        )

        assert len(resources) == 5

    @pytest.mark.asyncio
    async def test_query_resources_parses_tags(self) -> None:
        """Test that tags are properly parsed from tag_ prefixed fields."""
        mock_table_client = MagicMock()
        mock_entity = {
            "resource_id": "res-123",
            "resource_name": "test",
            "resource_type": "Microsoft.Test/test",
            "scenario": "test",
            "execution_id": "exec-123",
            "created_at": datetime.now(UTC),
            "status": "created",
            "tag_environment": "test",
            "tag_owner": "test-user",
            "tag_cost_center": "123",
        }
        mock_table_client.query_entities.return_value = [mock_entity]

        resources = await query_resources_from_table(mock_table_client, tenant_id="tenant-123")

        assert resources[0].tags == {
            "environment": "test",
            "owner": "test-user",
            "cost_center": "123",
        }

    @pytest.mark.asyncio
    async def test_query_resources_uses_rowkey_fallback(self) -> None:
        """Test that resource_id falls back to RowKey if not present."""
        mock_table_client = MagicMock()
        mock_entity = {
            "RowKey": "fallback-resource-id",
            "resource_name": "test",
            "resource_type": "Microsoft.Test/test",
            "scenario": "test",
            "execution_id": "exec-123",
            "created_at": datetime.now(UTC),
            "status": "created",
        }
        mock_table_client.query_entities.return_value = [mock_entity]

        resources = await query_resources_from_table(mock_table_client, tenant_id="tenant-123")

        assert resources[0].id == "fallback-resource-id"

    @pytest.mark.asyncio
    async def test_query_resources_handles_query_error(self) -> None:
        """Test that query errors are propagated."""
        mock_table_client = MagicMock()
        mock_table_client.query_entities.side_effect = Exception("Table Storage error")

        with pytest.raises(Exception, match="Table Storage error"):
            await query_resources_from_table(mock_table_client, tenant_id="tenant-123")

    @pytest.mark.asyncio
    async def test_query_resources_skips_malformed_entities(self) -> None:
        """Test that malformed entities are skipped with a warning."""
        mock_table_client = MagicMock()
        mock_entity_good = {
            "resource_id": "res-good",
            "resource_name": "good-resource",
            "resource_type": "Microsoft.Test/test",
            "scenario": "test",
            "execution_id": "exec-123",
            "created_at": datetime.now(UTC),
            "status": "created",
        }
        mock_entity_bad = {
            "resource_id": "res-bad",
            # Missing required fields
        }
        mock_table_client.query_entities.return_value = [mock_entity_good, mock_entity_bad]

        resources = await query_resources_from_table(mock_table_client, tenant_id="tenant-123")

        # Should return at least the good entity
        assert len(resources) >= 1
        assert resources[0].id == "res-good"


class TestListResourcesEndpoint:
    """Tests for list_resources HTTP endpoint."""

    @pytest.mark.asyncio
    async def test_list_resources_missing_table_config(self) -> None:
        """Test list_resources returns error when TABLE_STORAGE_ACCOUNT_NAME is missing."""
        from azure_haymaker.orchestrator.resources_api import list_resources

        mock_request = MagicMock()
        mock_request.params = {}

        with patch.dict("os.environ", {}, clear=True):
            response = await list_resources(mock_request)

        assert response.status_code == 500
        assert b"not configured" in response.get_body()

    @pytest.mark.asyncio
    async def test_list_resources_missing_tenant_id(self) -> None:
        """Test list_resources returns error when tenant_id is missing."""
        from azure_haymaker.orchestrator.resources_api import list_resources

        mock_request = MagicMock()
        mock_request.params = {}

        with patch.dict(
            "os.environ",
            {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount"},
            clear=True,
        ):
            response = await list_resources(mock_request)

        assert response.status_code == 400
        assert b"tenant_id required" in response.get_body()

    @pytest.mark.asyncio
    async def test_list_resources_invalid_limit_parameter(self) -> None:
        """Test list_resources handles invalid limit parameter."""
        from azure_haymaker.orchestrator.resources_api import list_resources

        mock_request = MagicMock()
        mock_request.params = {"limit": "invalid", "tenant_id": "tenant-123"}

        with patch.dict("os.environ", {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount"}):
            response = await list_resources(mock_request)

        assert response.status_code == 400


class TestGetResourceEndpoint:
    """Tests for get_resource HTTP endpoint."""

    @pytest.mark.asyncio
    async def test_get_resource_missing_resource_id(self) -> None:
        """Test get_resource returns error when resource_id is missing."""
        from azure_haymaker.orchestrator.resources_api import get_resource

        mock_request = MagicMock()
        mock_request.route_params = {}
        mock_request.params = {}

        response = await get_resource(mock_request)

        assert response.status_code == 400
        assert b"resource_id is required" in response.get_body()

    @pytest.mark.asyncio
    async def test_get_resource_missing_table_config(self) -> None:
        """Test get_resource returns error when TABLE_STORAGE_ACCOUNT_NAME is missing."""
        from azure_haymaker.orchestrator.resources_api import get_resource

        mock_request = MagicMock()
        mock_request.route_params = {"resource_id": "res-123"}
        mock_request.params = {}

        with patch.dict("os.environ", {}, clear=True):
            response = await get_resource(mock_request)

        assert response.status_code == 500
        assert b"not configured" in response.get_body()

    @pytest.mark.asyncio
    async def test_get_resource_missing_tenant_id(self) -> None:
        """Test get_resource returns error when tenant_id is missing."""
        from azure_haymaker.orchestrator.resources_api import get_resource

        mock_request = MagicMock()
        mock_request.route_params = {"resource_id": "res-123"}
        mock_request.params = {}

        with patch.dict(
            "os.environ",
            {"TABLE_STORAGE_ACCOUNT_NAME": "testaccount"},
            clear=True,
        ):
            response = await get_resource(mock_request)

        assert response.status_code == 400
        assert b"tenant_id required" in response.get_body()
