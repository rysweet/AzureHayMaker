"""Unit tests for Computer Use Telemetry Collector.

This module tests the telemetry collection system for Computer Use Knowledge Worker
Agents, including operation logging, metrics aggregation, and export.

Tests cover:
- Operation logging (workflow execution, browser events)
- Metrics aggregation and summaries
- Log retrieval and filtering
- Export to Azure Storage
- Performance metrics tracking
- Error tracking and reporting

Uses pytest with mocks for storage and time operations.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import the module under test
# Note: These imports will fail until ComputerUseTelemetryCollector is implemented
try:
    from azure_haymaker.knowledge_worker.computer_use.telemetry import (
        ComputerUseTelemetryCollector,
        OperationLog,
        TelemetryMetrics,
    )
    from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    ComputerUseTelemetryCollector = None
    OperationLog = None
    TelemetryMetrics = None
    WorkerIdentity = None


pytestmark = pytest.mark.skipif(
    not TELEMETRY_AVAILABLE, reason="ComputerUseTelemetryCollector not yet implemented"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def worker_identity():
    """Fixture: Worker identity."""
    return WorkerIdentity(
        worker_id="kw-test-001",
        display_name="Test Worker",
        user_principal_name="test.worker@tenant.onmicrosoft.com",
        entra_object_id="user-obj-123",
        department="engineering",
        persona="engineering",
        endpoint_type="cloud_pc",
        endpoint_id="cloudpc-abc123",
        team_ids=["team-001"],
    )


@pytest.fixture
def telemetry_collector(worker_identity):
    """Fixture: ComputerUseTelemetryCollector instance."""
    return ComputerUseTelemetryCollector(worker_identity=worker_identity)


@pytest.fixture
def sample_operations():
    """Fixture: Sample operation logs."""
    now = datetime.now(UTC)
    return [
        {
            "operation": "email_workflow",
            "status": "success",
            "duration_ms": 1500,
            "timestamp": now - timedelta(minutes=10),
            "metadata": {"to": "recipient@tenant.com", "subject": "Test Email"},
        },
        {
            "operation": "teams_workflow",
            "status": "success",
            "duration_ms": 800,
            "timestamp": now - timedelta(minutes=5),
            "metadata": {"channel": "General", "message": "Hello team!"},
        },
        {
            "operation": "email_workflow",
            "status": "error",
            "duration_ms": 500,
            "timestamp": now - timedelta(minutes=2),
            "metadata": {"error": "Browser timeout"},
        },
    ]


# ==============================================================================
# LOGGING TESTS
# ==============================================================================


class TestOperationLogging:
    """Tests for operation logging."""

    def test_log_operation_success(self, telemetry_collector, worker_identity):
        """Test logging successful operation."""
        # Arrange
        operation = "email_workflow"
        status = "success"
        duration_ms = 1200
        metadata = {"to": "recipient@tenant.com", "subject": "Test"}

        # Act
        telemetry_collector.log_operation(
            operation=operation,
            status=status,
            duration_ms=duration_ms,
            metadata=metadata,
        )

        # Assert
        logs = telemetry_collector.get_logs()
        assert len(logs) == 1
        assert logs[0].operation == operation
        assert logs[0].status == status
        assert logs[0].duration_ms == duration_ms
        assert logs[0].worker_id == worker_identity.worker_id

    def test_log_operation_failure(self, telemetry_collector):
        """Test logging failed operation with error details."""
        # Arrange
        operation = "teams_workflow"
        status = "error"
        metadata = {"error": "Connection timeout", "retry_count": 3}

        # Act
        telemetry_collector.log_operation(
            operation=operation, status=status, duration_ms=500, metadata=metadata
        )

        # Assert
        logs = telemetry_collector.get_logs()
        assert len(logs) == 1
        assert logs[0].status == "error"
        assert logs[0].metadata["error"] == "Connection timeout"
        assert logs[0].metadata["retry_count"] == 3

    def test_log_multiple_operations(self, telemetry_collector, sample_operations):
        """Test logging multiple operations."""
        # Act
        for op in sample_operations:
            telemetry_collector.log_operation(**op)

        # Assert
        logs = telemetry_collector.get_logs()
        assert len(logs) == len(sample_operations)

    def test_log_operation_with_missing_fields(self, telemetry_collector):
        """Test log_operation validates required fields."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            telemetry_collector.log_operation(
                operation="",  # Missing operation name
                status="success",
                duration_ms=100,
            )
        assert "operation" in str(exc_info.value).lower()


# ==============================================================================
# RETRIEVAL TESTS
# ==============================================================================


class TestLogRetrieval:
    """Tests for log retrieval and filtering."""

    def test_get_logs_all(self, telemetry_collector, sample_operations):
        """Test get_logs returns all logs."""
        # Arrange
        for op in sample_operations:
            telemetry_collector.log_operation(**op)

        # Act
        logs = telemetry_collector.get_logs()

        # Assert
        assert len(logs) == len(sample_operations)

    def test_get_logs_since_timestamp(self, telemetry_collector, sample_operations):
        """Test get_logs with time filter."""
        # Arrange
        for op in sample_operations:
            telemetry_collector.log_operation(**op)

        cutoff = datetime.now(UTC) - timedelta(minutes=6)

        # Act
        logs = telemetry_collector.get_logs(since=cutoff)

        # Assert - should only get recent logs
        assert len(logs) == 2  # Last 2 operations within 6 minutes
        assert all(log.timestamp >= cutoff for log in logs)

    def test_get_logs_by_status(self, telemetry_collector, sample_operations):
        """Test get_logs filtered by status."""
        # Arrange
        for op in sample_operations:
            telemetry_collector.log_operation(**op)

        # Act
        success_logs = telemetry_collector.get_logs(status="success")
        error_logs = telemetry_collector.get_logs(status="error")

        # Assert
        assert len(success_logs) == 2
        assert len(error_logs) == 1
        assert all(log.status == "success" for log in success_logs)
        assert all(log.status == "error" for log in error_logs)


# ==============================================================================
# METRICS TESTS
# ==============================================================================


class TestMetricsAggregation:
    """Tests for metrics aggregation and summaries."""

    def test_get_metrics_summary(self, telemetry_collector, sample_operations):
        """Test get_metrics_summary aggregates operation metrics."""
        # Arrange
        for op in sample_operations:
            telemetry_collector.log_operation(**op)

        # Act
        metrics = telemetry_collector.get_metrics_summary()

        # Assert
        assert isinstance(metrics, TelemetryMetrics)
        assert metrics.total_operations == 3
        assert metrics.successful_operations == 2
        assert metrics.failed_operations == 1
        assert metrics.average_duration_ms > 0
        assert metrics.success_rate == pytest.approx(0.6667, rel=0.01)

    def test_get_metrics_by_operation_type(self, telemetry_collector, sample_operations):
        """Test metrics grouped by operation type."""
        # Arrange
        for op in sample_operations:
            telemetry_collector.log_operation(**op)

        # Act
        metrics_by_type = telemetry_collector.get_metrics_by_operation()

        # Assert
        assert "email_workflow" in metrics_by_type
        assert "teams_workflow" in metrics_by_type
        assert metrics_by_type["email_workflow"]["count"] == 2
        assert metrics_by_type["teams_workflow"]["count"] == 1
        assert metrics_by_type["email_workflow"]["success_rate"] == 0.5


# ==============================================================================
# EXPORT TESTS
# ==============================================================================


class TestTelemetryExport:
    """Tests for telemetry export functionality."""

    @pytest.mark.asyncio
    async def test_export_logs_to_storage(
        self, telemetry_collector, sample_operations
    ):
        """Test export_logs writes to Azure Storage."""
        # Arrange
        for op in sample_operations:
            telemetry_collector.log_operation(**op)

        with patch(
            "azure.storage.blob.BlobServiceClient"
        ) as mock_blob_class:
            # Mock the BlobServiceClient instance
            mock_service_client = MagicMock()
            mock_blob_class.return_value = mock_service_client

            # Mock the blob client returned by get_blob_client
            mock_blob_client = MagicMock()
            mock_service_client.get_blob_client.return_value = mock_blob_client
            mock_blob_client.upload_blob = MagicMock()  # Not async

            # Act
            result = await telemetry_collector.export_logs(
                destination="azure://storageaccount/container/logs.json"
            )

            # Assert
            assert result["success"] is True
            assert result["log_count"] == 3
            mock_blob_client.upload_blob.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_logs_handles_storage_error(
        self, telemetry_collector, sample_operations
    ):
        """Test export_logs handles storage errors."""
        # Arrange
        for op in sample_operations:
            telemetry_collector.log_operation(**op)

        with patch(
            "azure.storage.blob.BlobServiceClient"
        ) as mock_blob_class:
            # Mock BlobServiceClient constructor to raise exception
            mock_blob_class.side_effect = Exception("Storage unavailable")

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await telemetry_collector.export_logs(
                    destination="azure://storageaccount/container/logs.json"
                )
            assert "unavailable" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
