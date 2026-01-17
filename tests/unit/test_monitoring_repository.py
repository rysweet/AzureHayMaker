"""Unit tests for monitoring_repository module.

Tests for the data access layer of the monitoring API, including blob storage
operations for reading status, run reports, and resource lists.

This module tests:
- MonitoringRepository initialization
- get_status method
- get_run_report method
- get_run_resources method
- _read_blob_json helper
- Error handling
"""

import json
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.orchestrator.repositories.monitoring_repository import (
    MonitoringRepository,
)


def create_mock_blob_service_client() -> MagicMock:
    """Create a mock BlobServiceClient."""
    return MagicMock()


class TestMonitoringRepositoryInit:
    """Tests for MonitoringRepository initialization."""

    def test_init_with_blob_client(self) -> None:
        """Test successful initialization with blob client."""
        mock_client = create_mock_blob_service_client()
        repo = MonitoringRepository(blob_client=mock_client)

        assert repo.blob_client == mock_client


class TestMonitoringRepositoryGetStatus:
    """Tests for the get_status method."""

    @pytest.mark.asyncio
    async def test_get_status_returns_data(self) -> None:
        """Test that get_status returns parsed JSON data."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = json.dumps(
            {
                "status": "running",
                "health": "healthy",
                "current_run_id": "run-123",
            }
        ).encode("utf-8")
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo.get_status()

        assert result is not None
        assert result["status"] == "running"
        assert result["health"] == "healthy"
        mock_client.get_blob_client.assert_called_once_with(
            container="execution-state", blob="current_status.json"
        )

    @pytest.mark.asyncio
    async def test_get_status_returns_none_when_not_found(self) -> None:
        """Test that get_status returns None when status file doesn't exist."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_blob.download_blob.side_effect = ResourceNotFoundError("Not found")
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo.get_status()

        assert result is None


class TestMonitoringRepositoryGetRunReport:
    """Tests for the get_run_report method."""

    @pytest.mark.asyncio
    async def test_get_run_report_returns_data(self) -> None:
        """Test that get_run_report returns parsed JSON data."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = json.dumps(
            {
                "run_id": "run-123",
                "status": "completed",
                "scenarios": [],
            }
        ).encode("utf-8")
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo.get_run_report("run-123")

        assert result["run_id"] == "run-123"
        assert result["status"] == "completed"
        mock_client.get_blob_client.assert_called_once_with(
            container="execution-reports", blob="run-123/report.json"
        )

    @pytest.mark.asyncio
    async def test_get_run_report_raises_not_found(self) -> None:
        """Test that get_run_report raises ResourceNotFoundError when not found."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_blob.download_blob.side_effect = ResourceNotFoundError("Not found")
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)

        with pytest.raises(ResourceNotFoundError):
            await repo.get_run_report("nonexistent-run")


class TestMonitoringRepositoryGetRunResources:
    """Tests for the get_run_resources method."""

    @pytest.mark.asyncio
    async def test_get_run_resources_returns_data(self) -> None:
        """Test that get_run_resources returns parsed JSON data."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = json.dumps(
            {
                "resources": [
                    {"resource_id": "res-1", "status": "created"},
                    {"resource_id": "res-2", "status": "deleted"},
                ]
            }
        ).encode("utf-8")
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo.get_run_resources("run-123")

        assert len(result["resources"]) == 2
        mock_client.get_blob_client.assert_called_once_with(
            container="execution-reports", blob="run-123/resources.json"
        )

    @pytest.mark.asyncio
    async def test_get_run_resources_raises_not_found(self) -> None:
        """Test that get_run_resources raises ResourceNotFoundError when not found."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_blob.download_blob.side_effect = ResourceNotFoundError("Not found")
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)

        with pytest.raises(ResourceNotFoundError):
            await repo.get_run_resources("nonexistent-run")


class TestMonitoringRepositoryReadBlobJson:
    """Tests for the _read_blob_json helper method."""

    @pytest.mark.asyncio
    async def test_read_blob_json_with_bytes(self) -> None:
        """Test reading JSON from bytes response."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = b'{"key": "value"}'
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo._read_blob_json("test-container", "test-blob.json")

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_read_blob_json_with_string(self) -> None:
        """Test reading JSON from string response."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = '{"key": "value"}'
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo._read_blob_json("test-container", "test-blob.json")

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_read_blob_json_with_async_readall(self) -> None:
        """Test reading JSON when readall returns a coroutine."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()

        # Simulate async readall
        async def async_readall() -> bytes:
            return b'{"async": true}'

        mock_download.readall.return_value = async_readall()
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo._read_blob_json("test-container", "test-blob.json")

        assert result == {"async": True}

    @pytest.mark.asyncio
    async def test_read_blob_json_handles_invalid_json(self) -> None:
        """Test that invalid JSON raises an exception."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = b"not valid json"
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)

        with pytest.raises(Exception, match="Corrupted data in storage"):
            await repo._read_blob_json("test-container", "test-blob.json")

    @pytest.mark.asyncio
    async def test_read_blob_json_reraises_not_found(self) -> None:
        """Test that ResourceNotFoundError is re-raised."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_blob.download_blob.side_effect = ResourceNotFoundError("Not found")
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)

        with pytest.raises(ResourceNotFoundError):
            await repo._read_blob_json("test-container", "nonexistent.json")


class TestMonitoringRepositoryEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_handles_utf8_encoding(self) -> None:
        """Test that UTF-8 encoded content is handled correctly."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()
        # Include unicode characters
        mock_download.readall.return_value = '{"message": "Hello 世界"}'.encode()
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo._read_blob_json("test-container", "test-blob.json")

        assert result["message"] == "Hello 世界"

    @pytest.mark.asyncio
    async def test_handles_large_json(self) -> None:
        """Test that large JSON responses are handled correctly."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()

        # Generate large JSON
        large_data = {"resources": [{"id": f"res-{i}", "data": "x" * 100} for i in range(1000)]}
        mock_download.readall.return_value = json.dumps(large_data).encode("utf-8")
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo._read_blob_json("test-container", "large.json")

        assert len(result["resources"]) == 1000

    @pytest.mark.asyncio
    async def test_handles_empty_json_object(self) -> None:
        """Test that empty JSON object is handled correctly."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = b"{}"
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo._read_blob_json("test-container", "empty.json")

        assert result == {}

    @pytest.mark.asyncio
    async def test_handles_nested_json(self) -> None:
        """Test that deeply nested JSON is handled correctly."""
        mock_client = create_mock_blob_service_client()
        mock_blob = MagicMock()
        mock_download = MagicMock()

        nested_data = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}
        mock_download.readall.return_value = json.dumps(nested_data).encode("utf-8")
        mock_blob.download_blob.return_value = mock_download
        mock_client.get_blob_client.return_value = mock_blob

        repo = MonitoringRepository(blob_client=mock_client)
        result = await repo._read_blob_json("test-container", "nested.json")

        assert result["level1"]["level2"]["level3"]["level4"]["value"] == "deep"


class TestMonitoringRepositoryModule:
    """Tests for module-level exports."""

    def test_all_exports(self) -> None:
        """Test that __all__ exports the correct classes."""
        from azure_haymaker.orchestrator.repositories import monitoring_repository

        assert "MonitoringRepository" in monitoring_repository.__all__
