"""
Security tests for tenant isolation.

These tests verify that tenant data is completely isolated and
cannot be accessed across tenant boundaries.

Test Coverage:
- Storage isolation (Blob, Table, Cosmos)
- Credential isolation
- Cross-tenant query prevention
- SQL/NoSQL injection prevention
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
    from azure_haymaker.orchestrator.tenant_auth import TenantCredentialManager
except ImportError:
    pytest.skip("Tenant isolation components not yet implemented", allow_module_level=True)

from tests.fixtures.mock_clients import (
    MockBlobClient,
    MockTableClient,
    MockCosmosClient,
    MockKeyVaultClient,
)
from tests.fixtures.tenant_configs import sample_tenant_context


@pytest.mark.security
class TestStorageIsolation:
    """Test that storage is properly isolated between tenants."""

    @pytest.fixture
    def tenant_a_context(self):
        """Create context for Tenant A."""
        return {
            "tenant_id": str(uuid4()),
            "tenant_name": "tenant-a",
            "subscription_id": str(uuid4()),
            "region": "eastus",
        }

    @pytest.fixture
    def tenant_b_context(self):
        """Create context for Tenant B."""
        return {
            "tenant_id": str(uuid4()),
            "tenant_name": "tenant-b",
            "subscription_id": str(uuid4()),
            "region": "westus",
        }

    @pytest.mark.asyncio
    async def test_blob_storage_query_for_tenant_a_returns_only_tenant_a_records(
        self, tenant_a_context, tenant_b_context
    ):
        """Test that Tenant A queries only return Tenant A blobs."""
        # Arrange
        mock_blob_client = MockBlobClient()
        tenant_a_client = TenantAwareBlobClient(mock_blob_client, tenant_a_context)
        tenant_b_client = TenantAwareBlobClient(mock_blob_client, tenant_b_context)

        # Upload blobs for both tenants
        await tenant_a_client.upload_blob("file1.txt", b"Tenant A data 1")
        await tenant_a_client.upload_blob("file2.txt", b"Tenant A data 2")
        await tenant_b_client.upload_blob("file1.txt", b"Tenant B data 1")

        # Act - Query Tenant A blobs
        tenant_a_blobs = await tenant_a_client.list_blobs()

        # Assert - Should only return Tenant A blobs
        assert len(tenant_a_blobs) == 2
        assert all(tenant_a_context["tenant_id"] in blob for blob in tenant_a_blobs)
        assert not any(tenant_b_context["tenant_id"] in blob for blob in tenant_a_blobs)

    @pytest.mark.asyncio
    async def test_blob_storage_query_for_tenant_b_returns_only_tenant_b_records(
        self, tenant_a_context, tenant_b_context
    ):
        """Test that Tenant B queries only return Tenant B blobs."""
        # Arrange
        mock_blob_client = MockBlobClient()
        tenant_a_client = TenantAwareBlobClient(mock_blob_client, tenant_a_context)
        tenant_b_client = TenantAwareBlobClient(mock_blob_client, tenant_b_context)

        # Upload blobs for both tenants
        await tenant_a_client.upload_blob("file1.txt", b"Tenant A data 1")
        await tenant_b_client.upload_blob("file1.txt", b"Tenant B data 1")
        await tenant_b_client.upload_blob("file2.txt", b"Tenant B data 2")

        # Act - Query Tenant B blobs
        tenant_b_blobs = await tenant_b_client.list_blobs()

        # Assert - Should only return Tenant B blobs
        assert len(tenant_b_blobs) == 2
        assert all(tenant_b_context["tenant_id"] in blob for blob in tenant_b_blobs)
        assert not any(tenant_a_context["tenant_id"] in blob for blob in tenant_b_blobs)

    @pytest.mark.asyncio
    async def test_cross_tenant_blob_query_returns_zero_records(
        self, tenant_a_context, tenant_b_context
    ):
        """Test that attempting to query Tenant B data with Tenant A context returns nothing."""
        # Arrange
        mock_blob_client = MockBlobClient()
        tenant_a_client = TenantAwareBlobClient(mock_blob_client, tenant_a_context)

        # Upload blobs for Tenant B only
        tenant_b_prefix = tenant_b_context["tenant_id"]
        await mock_blob_client.upload_blob(f"{tenant_b_prefix}/secret.txt", b"B secret data")

        # Act - Try to list blobs with Tenant A context
        tenant_a_blobs = await tenant_a_client.list_blobs()

        # Assert - Should return zero blobs (cannot access Tenant B data)
        assert len(tenant_a_blobs) == 0

    @pytest.mark.asyncio
    async def test_table_storage_partition_key_isolation_tenant_a(
        self, tenant_a_context, tenant_b_context
    ):
        """Test that Table Storage partition keys isolate Tenant A data."""
        # Arrange
        mock_table_client = MockTableClient()
        tenant_a_client = TenantAwareTableClient(mock_table_client, tenant_a_context)
        tenant_b_client = TenantAwareTableClient(mock_table_client, tenant_b_context)

        run_id = str(uuid4())

        # Create entities for both tenants
        await tenant_a_client.create_entity({"run_id": run_id, "data": "Tenant A"})
        await tenant_b_client.create_entity({"run_id": run_id, "data": "Tenant B"})

        # Act - Query with Tenant A context
        results = await tenant_a_client.query_entities(f"run_id eq '{run_id}'")

        # Assert - Should only return Tenant A entity
        assert len(results) == 1
        assert results[0]["data"] == "Tenant A"

    @pytest.mark.asyncio
    async def test_cosmos_db_partition_key_isolation_tenant_a(
        self, tenant_a_context, tenant_b_context
    ):
        """Test that Cosmos DB partition keys isolate Tenant A data."""
        # Arrange
        mock_cosmos_client = MockCosmosClient()
        tenant_a_client = TenantAwareCosmosClient(mock_cosmos_client, tenant_a_context)
        tenant_b_client = TenantAwareCosmosClient(mock_cosmos_client, tenant_b_context)

        # Create documents for both tenants
        await tenant_a_client.create_item({"type": "log", "data": "Tenant A log"})
        await tenant_b_client.create_item({"type": "log", "data": "Tenant B log"})

        # Act - Query with Tenant A context
        results = await tenant_a_client.query_items("SELECT * FROM c WHERE c.type = 'log'")

        # Assert - Should only return Tenant A document
        assert len(results) == 1
        assert results[0]["data"] == "Tenant A log"


@pytest.mark.security
class TestCredentialIsolation:
    """Test that credentials are isolated between tenants."""

    @pytest.fixture
    def mock_kv_client(self):
        """Create mock Key Vault client."""
        return MockKeyVaultClient()

    @pytest.mark.asyncio
    async def test_tenant_a_credentials_cannot_access_tenant_b_resources(self, mock_kv_client):
        """Test that Tenant A credentials cannot retrieve Tenant B credentials."""
        # Arrange
        tenant_a_name = "tenant-a"
        tenant_b_name = "tenant-b"

        # Store credentials for both tenants
        mock_kv_client.set_secret(f"{tenant_a_name}-client-id", str(uuid4()))
        mock_kv_client.set_secret(f"{tenant_a_name}-client-secret", "secret-a")
        mock_kv_client.set_secret(f"{tenant_a_name}-tenant-id", str(uuid4()))
        mock_kv_client.set_secret(f"{tenant_a_name}-subscription-id", str(uuid4()))
        mock_kv_client.set_secret(f"{tenant_b_name}-client-id", str(uuid4()))
        mock_kv_client.set_secret(f"{tenant_b_name}-client-secret", "secret-b")
        mock_kv_client.set_secret(f"{tenant_b_name}-tenant-id", str(uuid4()))
        mock_kv_client.set_secret(f"{tenant_b_name}-subscription-id", str(uuid4()))

        credential_manager = TenantCredentialManager(mock_kv_client)

        # Act - Retrieve Tenant A credentials
        tenant_a_creds = await credential_manager.get_tenant_credential(tenant_a_name)

        # Assert - Should only have access to Tenant A credentials
        assert tenant_a_creds.client_secret.get_secret_value() == "secret-a"
        assert tenant_a_creds.client_secret.get_secret_value() != "secret-b"

    @pytest.mark.asyncio
    async def test_keyvault_secrets_scoped_to_correct_tenant(self, mock_kv_client):
        """Test that Key Vault secrets are scoped to tenant names."""
        # Arrange
        tenant_name = "tenant-secure"
        mock_kv_client.set_secret(f"{tenant_name}-client-id", "correct-client-id")
        mock_kv_client.set_secret(f"{tenant_name}-client-secret", "correct-secret")
        mock_kv_client.set_secret(f"{tenant_name}-tenant-id", str(uuid4()))
        mock_kv_client.set_secret(f"{tenant_name}-subscription-id", str(uuid4()))

        credential_manager = TenantCredentialManager(mock_kv_client)

        # Act
        creds = await credential_manager.get_tenant_credential(tenant_name)

        # Assert - Verify correct scoping
        assert f"{tenant_name}-client-id" in mock_kv_client.get_secret_calls


@pytest.mark.security
class TestInjectionPrevention:
    """Test that SQL/NoSQL injection attempts are prevented."""

    @pytest.mark.asyncio
    async def test_invalid_tenant_id_format_is_rejected(self):
        """Test that invalid tenant_id format (injection attempt) is rejected."""
        # Arrange
        invalid_tenant_id = "'; DROP TABLE tenants; --"
        tenant_context = {
            "tenant_id": invalid_tenant_id,
            "tenant_name": "hacker",
            "subscription_id": str(uuid4()),
            "region": "eastus",
        }

        mock_blob_client = MockBlobClient()

        # Act & Assert - Should raise validation error or sanitize input
        with pytest.raises((ValueError, TypeError)):
            tenant_aware_client = TenantAwareBlobClient(mock_blob_client, tenant_context)
            await tenant_aware_client.list_blobs()

    @pytest.mark.asyncio
    async def test_odata_injection_attempt_is_sanitized(self):
        """Test that OData filter injection attempts are sanitized."""
        # Arrange
        mock_table_client = MockTableClient()
        tenant_context = sample_tenant_context()
        tenant_aware_client = TenantAwareTableClient(mock_table_client, tenant_context)

        # Malicious query with OData injection
        malicious_query = "run_id eq 'test' or PartitionKey ne ''"

        # Act
        results = await tenant_aware_client.query_entities(malicious_query)

        # Assert - Should only return results for current tenant
        # Injection should be sanitized and not return all data
        for result in results:
            assert tenant_context["tenant_id"] in result.get("PartitionKey", "")

    @pytest.mark.asyncio
    async def test_query_filter_bypass_with_or_operator_prevented(self):
        """Test that OR operator cannot bypass tenant isolation."""
        # Arrange
        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4())

        tenant_a_context = {
            "tenant_id": tenant_a_id,
            "tenant_name": "tenant-a",
            "subscription_id": str(uuid4()),
            "region": "eastus",
        }

        mock_cosmos_client = MockCosmosClient()
        tenant_a_client = TenantAwareCosmosClient(mock_cosmos_client, tenant_a_context)

        # Create data for both tenants
        await mock_cosmos_client.create_item({"tenant_id": tenant_a_id, "data": "A"})
        await mock_cosmos_client.create_item({"tenant_id": tenant_b_id, "data": "B"})

        # Act - Attempt to bypass filter with OR
        malicious_query = f"SELECT * FROM c WHERE c.tenant_id = '{tenant_b_id}'"
        results = await tenant_a_client.query_items(malicious_query)

        # Assert - Should still only return Tenant A data
        assert len(results) == 1
        assert results[0]["data"] == "A"

    @pytest.mark.asyncio
    async def test_not_operator_cannot_bypass_tenant_filter(self):
        """Test that NOT operator cannot bypass tenant isolation."""
        # Arrange
        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4())

        tenant_a_context = {
            "tenant_id": tenant_a_id,
            "tenant_name": "tenant-a",
            "subscription_id": str(uuid4()),
            "region": "eastus",
        }

        mock_table_client = MockTableClient()
        tenant_a_client = TenantAwareTableClient(mock_table_client, tenant_a_context)

        run_id = str(uuid4())

        # Create entities
        await mock_table_client.create_entity(
            {"PartitionKey": f"{tenant_a_id}#{run_id}", "RowKey": "1", "data": "A"}
        )
        await mock_table_client.create_entity(
            {"PartitionKey": f"{tenant_b_id}#{run_id}", "RowKey": "2", "data": "B"}
        )

        # Act - Attempt bypass with NOT operator
        malicious_query = f"PartitionKey ne '{tenant_a_id}#{run_id}'"
        results = await tenant_a_client.query_entities(malicious_query)

        # Assert - Should return empty or only Tenant A data, never Tenant B
        for result in results:
            assert tenant_b_id not in result.get("PartitionKey", "")
