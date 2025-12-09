"""
Unit tests for tenant-aware storage clients.

These tests follow TDD methodology - they will FAIL initially until
the tenant-aware storage clients are implemented.

Test Coverage:
- TenantAwareBlobClient path prefixing
- TenantAwareTableClient partition key generation
- TenantAwareCosmosClient tenant_id filtering
- Single-tenant mode (no prefixing)
"""

import pytest
from uuid import uuid4

# These imports will fail until implementation - that's expected for TDD!
try:
    from azure_haymaker.orchestrator.services.tenant_storage import (
        TenantAwareBlobClient,
        TenantAwareTableClient,
        TenantAwareCosmosClient,
    )
except ImportError:
    pytest.skip("Tenant-aware storage clients not yet implemented", allow_module_level=True)

from tests.fixtures.mock_clients import MockBlobClient, MockTableClient, MockCosmosClient
from tests.fixtures.tenant_configs import sample_tenant_context
from tests.fixtures.test_data import sample_blob_data, sample_table_entity, sample_cosmos_document


class TestTenantAwareBlobClient:
    """Test TenantAwareBlobClient for path prefixing."""

    @pytest.fixture
    def mock_blob_client(self):
        """Create mock blob client."""
        return MockBlobClient()

    @pytest.fixture
    def tenant_context(self):
        """Create tenant context."""
        return sample_tenant_context()

    @pytest.mark.asyncio
    async def test_upload_blob_with_tenant_prefix_adds_prefix_to_path(
        self, mock_blob_client, tenant_context
    ):
        """Test that blob upload includes tenant prefix in path."""
        # Arrange
        tenant_aware_client = TenantAwareBlobClient(
            blob_client=mock_blob_client, tenant_context=tenant_context
        )
        blob_name = "test-file.txt"
        data = b"test data"

        # Act
        await tenant_aware_client.upload_blob(blob_name, data)

        # Assert
        expected_path = f"{tenant_context['tenant_id']}/{blob_name}"
        assert expected_path in mock_blob_client.uploaded_blobs

    @pytest.mark.asyncio
    async def test_upload_blob_without_tenant_context_does_not_prefix(self, mock_blob_client):
        """Test that blob upload without tenant context doesn't add prefix (single-tenant mode)."""
        # Arrange
        tenant_aware_client = TenantAwareBlobClient(
            blob_client=mock_blob_client, tenant_context=None
        )
        blob_name = "test-file.txt"
        data = b"test data"

        # Act
        await tenant_aware_client.upload_blob(blob_name, data)

        # Assert
        assert blob_name in mock_blob_client.uploaded_blobs
        # Should not have any prefix
        assert "/" not in mock_blob_client.uploaded_blobs[0]

    @pytest.mark.asyncio
    async def test_download_blob_with_tenant_prefix_uses_correct_path(
        self, mock_blob_client, tenant_context
    ):
        """Test that blob download uses tenant-prefixed path."""
        # Arrange
        tenant_aware_client = TenantAwareBlobClient(
            blob_client=mock_blob_client, tenant_context=tenant_context
        )
        blob_name = "test-file.txt"
        data = b"test data"

        # Upload blob first
        prefixed_path = f"{tenant_context['tenant_id']}/{blob_name}"
        await mock_blob_client.upload_blob(prefixed_path, data)

        # Act
        downloaded = await tenant_aware_client.download_blob(blob_name)

        # Assert
        assert downloaded is not None
        assert prefixed_path in mock_blob_client.downloaded_blobs

    @pytest.mark.asyncio
    async def test_list_blobs_filters_by_tenant_prefix(self, mock_blob_client, tenant_context):
        """Test that list_blobs only returns blobs for current tenant."""
        # Arrange
        tenant_aware_client = TenantAwareBlobClient(
            blob_client=mock_blob_client, tenant_context=tenant_context
        )

        # Upload blobs for different tenants
        tenant_a_id = tenant_context["tenant_id"]
        tenant_b_id = str(uuid4())

        await mock_blob_client.upload_blob(f"{tenant_a_id}/file1.txt", b"data1")
        await mock_blob_client.upload_blob(f"{tenant_a_id}/file2.txt", b"data2")
        await mock_blob_client.upload_blob(f"{tenant_b_id}/file3.txt", b"data3")

        # Act
        blobs = await tenant_aware_client.list_blobs()

        # Assert
        assert len(blobs) == 2
        assert all(blob.startswith(tenant_a_id) for blob in blobs)


class TestTenantAwareTableClient:
    """Test TenantAwareTableClient for partition key generation."""

    @pytest.fixture
    def mock_table_client(self):
        """Create mock table client."""
        return MockTableClient()

    @pytest.fixture
    def tenant_context(self):
        """Create tenant context."""
        return sample_tenant_context()

    @pytest.mark.asyncio
    async def test_create_entity_generates_partition_key_with_tenant_id(
        self, mock_table_client, tenant_context
    ):
        """Test that partition key is generated as {tenant_id}#{run_id}."""
        # Arrange
        tenant_aware_client = TenantAwareTableClient(
            table_client=mock_table_client, tenant_context=tenant_context
        )
        run_id = str(uuid4())
        entity = {"run_id": run_id, "status": "completed", "data": "test"}

        # Act
        await tenant_aware_client.create_entity(entity)

        # Assert
        created_entity = mock_table_client.entities[0]
        expected_partition_key = f"{tenant_context['tenant_id']}#{run_id}"
        assert created_entity["PartitionKey"] == expected_partition_key

    @pytest.mark.asyncio
    async def test_create_entity_without_tenant_context_uses_simple_partition_key(
        self, mock_table_client
    ):
        """Test that entities without tenant context use simple partition key (single-tenant mode)."""
        # Arrange
        tenant_aware_client = TenantAwareTableClient(
            table_client=mock_table_client, tenant_context=None
        )
        run_id = str(uuid4())
        entity = {"run_id": run_id, "status": "completed"}

        # Act
        await tenant_aware_client.create_entity(entity)

        # Assert
        created_entity = mock_table_client.entities[0]
        assert created_entity["PartitionKey"] == run_id
        assert "#" not in created_entity["PartitionKey"]

    @pytest.mark.asyncio
    async def test_query_entities_filters_by_tenant_id(self, mock_table_client, tenant_context):
        """Test that query filters entities by tenant_id."""
        # Arrange
        tenant_aware_client = TenantAwareTableClient(
            table_client=mock_table_client, tenant_context=tenant_context
        )

        # Create entities for different tenants
        tenant_a_id = tenant_context["tenant_id"]
        tenant_b_id = str(uuid4())
        run_id = str(uuid4())

        await mock_table_client.create_entity(
            {"PartitionKey": f"{tenant_a_id}#{run_id}", "RowKey": "1", "data": "A"}
        )
        await mock_table_client.create_entity(
            {"PartitionKey": f"{tenant_b_id}#{run_id}", "RowKey": "2", "data": "B"}
        )

        # Act
        results = await tenant_aware_client.query_entities(f"run_id eq '{run_id}'")

        # Assert
        assert len(results) == 1
        assert results[0]["data"] == "A"


class TestTenantAwareCosmosClient:
    """Test TenantAwareCosmosClient for tenant_id filtering."""

    @pytest.fixture
    def mock_cosmos_client(self):
        """Create mock Cosmos client."""
        return MockCosmosClient()

    @pytest.fixture
    def tenant_context(self):
        """Create tenant context."""
        return sample_tenant_context()

    @pytest.mark.asyncio
    async def test_create_item_adds_tenant_id_field(self, mock_cosmos_client, tenant_context):
        """Test that documents created include tenant_id field."""
        # Arrange
        tenant_aware_client = TenantAwareCosmosClient(
            cosmos_client=mock_cosmos_client, tenant_context=tenant_context
        )
        document = {"type": "log", "data": "test", "timestamp": "2025-12-09T00:00:00Z"}

        # Act
        created_doc = await tenant_aware_client.create_item(document)

        # Assert
        assert created_doc["tenant_id"] == tenant_context["tenant_id"]

    @pytest.mark.asyncio
    async def test_create_item_without_tenant_context_does_not_add_tenant_id(
        self, mock_cosmos_client
    ):
        """Test that documents without tenant context don't have tenant_id (single-tenant mode)."""
        # Arrange
        tenant_aware_client = TenantAwareCosmosClient(
            cosmos_client=mock_cosmos_client, tenant_context=None
        )
        document = {"type": "log", "data": "test"}

        # Act
        created_doc = await tenant_aware_client.create_item(document)

        # Assert
        assert "tenant_id" not in created_doc

    @pytest.mark.asyncio
    async def test_query_items_filters_by_tenant_id(self, mock_cosmos_client, tenant_context):
        """Test that queries automatically filter by tenant_id."""
        # Arrange
        tenant_aware_client = TenantAwareCosmosClient(
            cosmos_client=mock_cosmos_client, tenant_context=tenant_context
        )

        # Create documents for different tenants
        tenant_a_id = tenant_context["tenant_id"]
        tenant_b_id = str(uuid4())

        await mock_cosmos_client.create_item({"tenant_id": tenant_a_id, "type": "log", "data": "A"})
        await mock_cosmos_client.create_item({"tenant_id": tenant_b_id, "type": "log", "data": "B"})

        # Act
        results = await tenant_aware_client.query_items("SELECT * FROM c WHERE c.type = 'log'")

        # Assert
        assert len(results) == 1
        assert results[0]["data"] == "A"

    @pytest.mark.asyncio
    async def test_cosmos_partition_key_equals_tenant_id(self, mock_cosmos_client, tenant_context):
        """Test that partition key is set to tenant_id."""
        # Arrange
        tenant_aware_client = TenantAwareCosmosClient(
            cosmos_client=mock_cosmos_client,
            tenant_context=tenant_context,
            partition_key_path="/tenant_id",
        )
        document = {"type": "log", "data": "test"}

        # Act
        created_doc = await tenant_aware_client.create_item(document)

        # Assert
        assert created_doc["tenant_id"] == tenant_context["tenant_id"]
        # In Cosmos DB, partition key must match the document's tenant_id field
        assert "tenant_id" in created_doc
