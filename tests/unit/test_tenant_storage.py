"""Unit tests for TenantStorageManager (Phase 4 cross-tenant storage).

Tests cover:
- Tenant path generation: {tenant_id}/{execution_id}/{artifact}
- Backward compatibility without tenant_id: {execution_id}/{artifact}
- Upload/download operations (mocked)
- List and cleanup operations

Testing Strategy:
- 60% unit tests (fast, mocked Azure SDK)
- Focus on path generation logic (deterministic)
- Mock BlobServiceClient for async operations
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from azure_haymaker.storage.tenant_storage import (
    TenantStorageConfig,
    TenantStorageManager,
    get_tenant_blob_path,
)


# =============================================================================
# get_tenant_blob_path Tests
# =============================================================================


class TestGetTenantBlobPath:
    """Tests for get_tenant_blob_path function."""

    def test_path_with_tenant_id(self):
        """Test path generation with tenant_id prefix."""
        path = get_tenant_blob_path(
            execution_id="exec-123",
            artifact_name="results.json",
            tenant_id="tenant-abc",
        )
        assert path == "tenant-abc/exec-123/results.json"

    def test_path_without_tenant_id(self):
        """Test backward compatible path without tenant_id."""
        path = get_tenant_blob_path(
            execution_id="exec-123",
            artifact_name="results.json",
            tenant_id=None,
        )
        assert path == "exec-123/results.json"

    def test_path_with_empty_tenant_id(self):
        """Test path with empty string tenant_id (treated as no tenant)."""
        path = get_tenant_blob_path(
            execution_id="exec-123",
            artifact_name="results.json",
            tenant_id="",
        )
        # Empty string is falsy, should behave like None
        assert path == "exec-123/results.json"

    def test_path_with_complex_artifact_name(self):
        """Test path with nested artifact name."""
        path = get_tenant_blob_path(
            execution_id="exec-123",
            artifact_name="logs/scenario-01/output.txt",
            tenant_id="tenant-abc",
        )
        assert path == "tenant-abc/exec-123/logs/scenario-01/output.txt"

    def test_path_with_special_characters_in_tenant(self):
        """Test path with special characters in tenant ID."""
        path = get_tenant_blob_path(
            execution_id="exec-123",
            artifact_name="report.json",
            tenant_id="00000000-0000-0000-0000-000000000001",
        )
        assert path == "00000000-0000-0000-0000-000000000001/exec-123/report.json"


# =============================================================================
# TenantStorageConfig Tests
# =============================================================================


class TestTenantStorageConfig:
    """Tests for TenantStorageConfig dataclass."""

    def test_default_config(self):
        """Test default container names."""
        config = TenantStorageConfig()
        assert config.container_logs == "execution-logs"
        assert config.container_state == "execution-state"
        assert config.container_reports == "execution-reports"
        assert config.container_scenarios == "scenarios"

    def test_custom_config(self):
        """Test custom container names."""
        config = TenantStorageConfig(
            container_logs="custom-logs",
            container_state="custom-state",
            container_reports="custom-reports",
            container_scenarios="custom-scenarios",
        )
        assert config.container_logs == "custom-logs"
        assert config.container_state == "custom-state"


# =============================================================================
# TenantStorageManager Tests
# =============================================================================


@pytest.fixture
def mock_blob_service_client():
    """Create a mock BlobServiceClient."""
    client = MagicMock()
    container_client = MagicMock()
    blob_client = MagicMock()

    # Setup async mock for upload_blob
    blob_client.upload_blob = AsyncMock()
    blob_client.download_blob = AsyncMock()
    blob_client.delete_blob = AsyncMock()
    blob_client.url = "https://storage.blob.core.windows.net/container/path"

    # Setup download mock to return data
    download_mock = AsyncMock()
    download_mock.readall = AsyncMock(return_value=b'{"status": "success"}')
    blob_client.download_blob.return_value = download_mock

    container_client.get_blob_client.return_value = blob_client

    # Setup list_blobs as an async generator
    async def async_list_blobs(name_starts_with=None):
        # Create mock blobs with name as a regular attribute, not the mock's display name
        prefix = name_starts_with or ""
        blob1 = MagicMock()
        blob1.name = f"{prefix}report.json"
        blob2 = MagicMock()
        blob2.name = f"{prefix}logs.txt"
        blob3 = MagicMock()
        blob3.name = f"{prefix}metrics.json"
        blobs = [blob1, blob2, blob3]
        for blob in blobs:
            yield blob

    container_client.list_blobs = MagicMock(side_effect=async_list_blobs)

    client.get_container_client.return_value = container_client

    return client


@pytest.fixture
def storage_manager(mock_blob_service_client):
    """Create TenantStorageManager with mocked client."""
    return TenantStorageManager(mock_blob_service_client)


class TestTenantStorageManager:
    """Tests for TenantStorageManager class."""

    def test_init_with_default_config(self, mock_blob_service_client):
        """Test initialization with default config."""
        manager = TenantStorageManager(mock_blob_service_client)
        assert manager._config.container_reports == "execution-reports"

    def test_init_with_custom_config(self, mock_blob_service_client):
        """Test initialization with custom config."""
        config = TenantStorageConfig(container_reports="my-reports")
        manager = TenantStorageManager(mock_blob_service_client, config=config)
        assert manager._config.container_reports == "my-reports"

    def test_get_tenant_container_client(self, storage_manager, mock_blob_service_client):
        """Test getting container client."""
        container = storage_manager.get_tenant_container_client("test-container")
        mock_blob_service_client.get_container_client.assert_called_with("test-container")
        assert container is not None

    @pytest.mark.asyncio
    async def test_upload_tenant_data_with_tenant(self, storage_manager, mock_blob_service_client):
        """Test upload with tenant_id prefix."""
        url = await storage_manager.upload_tenant_data(
            tenant_id="tenant-abc",
            execution_id="exec-123",
            artifact_name="results.json",
            data=b'{"status": "success"}',
            content_type="application/json",
        )

        # Verify correct path was used
        container_client = mock_blob_service_client.get_container_client.return_value
        blob_client = container_client.get_blob_client
        blob_client.assert_called_with("tenant-abc/exec-123/results.json")

        # Verify upload was called
        actual_blob_client = blob_client.return_value
        actual_blob_client.upload_blob.assert_called_once()
        assert url is not None

    @pytest.mark.asyncio
    async def test_upload_tenant_data_without_tenant(
        self, storage_manager, mock_blob_service_client
    ):
        """Test upload without tenant_id (backward compatibility)."""
        await storage_manager.upload_tenant_data(
            execution_id="exec-123",
            artifact_name="results.json",
            data=b'{"status": "success"}',
        )

        # Verify correct path was used (no tenant prefix)
        container_client = mock_blob_service_client.get_container_client.return_value
        blob_client = container_client.get_blob_client
        blob_client.assert_called_with("exec-123/results.json")

    @pytest.mark.asyncio
    async def test_upload_tenant_data_string(self, storage_manager, mock_blob_service_client):
        """Test upload with string data (auto-encodes to UTF-8)."""
        await storage_manager.upload_tenant_data(
            execution_id="exec-123",
            artifact_name="results.json",
            data='{"status": "success"}',  # String, not bytes
        )

        actual_blob_client = (
            mock_blob_service_client.get_container_client.return_value.get_blob_client.return_value
        )
        actual_blob_client.upload_blob.assert_called_once()
        # Verify data was converted to bytes
        call_args = actual_blob_client.upload_blob.call_args
        assert isinstance(call_args[0][0], bytes)

    @pytest.mark.asyncio
    async def test_upload_tenant_data_custom_container(
        self, storage_manager, mock_blob_service_client
    ):
        """Test upload to custom container."""
        await storage_manager.upload_tenant_data(
            execution_id="exec-123",
            artifact_name="log.txt",
            data=b"log content",
            container_name="custom-container",
        )

        mock_blob_service_client.get_container_client.assert_called_with("custom-container")

    @pytest.mark.asyncio
    async def test_download_tenant_data_with_tenant(
        self, storage_manager, mock_blob_service_client
    ):
        """Test download with tenant_id prefix."""
        data = await storage_manager.download_tenant_data(
            tenant_id="tenant-abc",
            execution_id="exec-123",
            artifact_name="results.json",
        )

        # Verify correct path was used
        container_client = mock_blob_service_client.get_container_client.return_value
        blob_client = container_client.get_blob_client
        blob_client.assert_called_with("tenant-abc/exec-123/results.json")

        assert data == b'{"status": "success"}'

    @pytest.mark.asyncio
    async def test_download_tenant_data_without_tenant(
        self, storage_manager, mock_blob_service_client
    ):
        """Test download without tenant_id (backward compatibility)."""
        await storage_manager.download_tenant_data(
            execution_id="exec-123",
            artifact_name="results.json",
        )

        container_client = mock_blob_service_client.get_container_client.return_value
        blob_client = container_client.get_blob_client
        blob_client.assert_called_with("exec-123/results.json")

    @pytest.mark.asyncio
    async def test_delete_tenant_data(self, storage_manager, mock_blob_service_client):
        """Test delete operation."""
        await storage_manager.delete_tenant_data(
            tenant_id="tenant-abc",
            execution_id="exec-123",
            artifact_name="old-results.json",
        )

        container_client = mock_blob_service_client.get_container_client.return_value
        blob_client = container_client.get_blob_client
        blob_client.assert_called_with("tenant-abc/exec-123/old-results.json")

        actual_blob_client = blob_client.return_value
        actual_blob_client.delete_blob.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tenant_artifacts(self, mock_blob_service_client):
        """Test listing artifacts for a tenant execution."""
        # Create fresh manager for this test to properly mock list_blobs
        container_client = mock_blob_service_client.get_container_client.return_value

        # Create proper async iterator class for list_blobs
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        def mock_list_blobs(name_starts_with=None):
            prefix = name_starts_with or ""
            # Create mock blobs with name as a regular attribute, not the mock's display name
            blob1 = MagicMock()
            blob1.name = f"{prefix}report.json"
            blob2 = MagicMock()
            blob2.name = f"{prefix}logs.txt"
            return MockAsyncIterator([blob1, blob2])

        container_client.list_blobs = mock_list_blobs

        manager = TenantStorageManager(mock_blob_service_client)
        artifacts = await manager.list_tenant_artifacts(
            tenant_id="tenant-abc",
            execution_id="exec-123",
        )

        assert len(artifacts) == 2
        assert "report.json" in artifacts
        assert "logs.txt" in artifacts

    @pytest.mark.asyncio
    async def test_cleanup_tenant_execution(self, storage_manager, mock_blob_service_client):
        """Test cleanup deletes all artifacts."""
        container_client = mock_blob_service_client.get_container_client.return_value

        # Create proper async iterator for list_blobs
        async def mock_list_blobs(name_starts_with=None):
            prefix = name_starts_with or ""
            # Create mock blobs with name as a regular attribute
            blob1 = MagicMock()
            blob1.name = f"{prefix}report.json"
            blob2 = MagicMock()
            blob2.name = f"{prefix}logs.txt"
            blobs = [blob1, blob2]
            for blob in blobs:
                yield blob

        container_client.list_blobs = mock_list_blobs

        deleted_count = await storage_manager.cleanup_tenant_execution(
            tenant_id="tenant-abc",
            execution_id="exec-123",
        )

        assert deleted_count == 2


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestStorageErrorHandling:
    """Tests for error handling in storage operations."""

    @pytest.mark.asyncio
    async def test_upload_error_propagates(self, mock_blob_service_client):
        """Test that upload errors are propagated."""
        container_client = mock_blob_service_client.get_container_client.return_value
        blob_client = container_client.get_blob_client.return_value
        blob_client.upload_blob = AsyncMock(side_effect=Exception("Upload failed"))

        manager = TenantStorageManager(mock_blob_service_client)

        with pytest.raises(Exception, match="Upload failed"):
            await manager.upload_tenant_data(
                execution_id="exec-123",
                artifact_name="results.json",
                data=b"test",
            )

    @pytest.mark.asyncio
    async def test_download_error_propagates(self, mock_blob_service_client):
        """Test that download errors are propagated."""
        container_client = mock_blob_service_client.get_container_client.return_value
        blob_client = container_client.get_blob_client.return_value
        blob_client.download_blob = AsyncMock(side_effect=Exception("Blob not found"))

        manager = TenantStorageManager(mock_blob_service_client)

        with pytest.raises(Exception, match="Blob not found"):
            await manager.download_tenant_data(
                execution_id="exec-123",
                artifact_name="results.json",
            )

    @pytest.mark.asyncio
    async def test_cleanup_continues_on_individual_delete_error(self, mock_blob_service_client):
        """Test that cleanup continues even if individual deletes fail."""
        container_client = mock_blob_service_client.get_container_client.return_value
        blob_client = container_client.get_blob_client.return_value

        # First delete succeeds, second fails
        delete_call_count = 0

        async def flaky_delete():
            nonlocal delete_call_count
            delete_call_count += 1
            if delete_call_count == 2:
                raise Exception("Delete failed")

        blob_client.delete_blob = AsyncMock(side_effect=flaky_delete)

        # Create proper async iterator for list_blobs
        async def mock_list_blobs(name_starts_with=None):
            prefix = name_starts_with or ""
            # Create mock blobs with name as a regular attribute
            blob1 = MagicMock()
            blob1.name = f"{prefix}file1.json"
            blob2 = MagicMock()
            blob2.name = f"{prefix}file2.json"  # This delete will fail
            blob3 = MagicMock()
            blob3.name = f"{prefix}file3.json"
            blobs = [blob1, blob2, blob3]
            for blob in blobs:
                yield blob

        container_client.list_blobs = mock_list_blobs

        manager = TenantStorageManager(mock_blob_service_client)

        # Should not raise, should continue and return partial count
        deleted_count = await manager.cleanup_tenant_execution(
            tenant_id="tenant-abc",
            execution_id="exec-123",
        )

        # 2 out of 3 should have succeeded
        assert deleted_count == 2
