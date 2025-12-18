"""Integration tests for SIEM Telemetry Export Pipeline.

This module contains integration tests that verify the complete SIEM export
pipeline works end-to-end with Azure Sentinel. Tests use mocked Azure services
but test the full integration flow.

Test Coverage:
- Complete exporter lifecycle with real-world scenarios
- Multi-worker telemetry collection and export
- Error recovery and retry scenarios
- DLQ overflow and management
- Concurrent event emission
- Batch processing at scale
- Health monitoring and alerting
- Configuration validation

These tests represent 30% of the testing pyramid.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Import the modules under test
try:
    from azure_haymaker.knowledge_worker.telemetry.exporter import (
        SentinelConnector,
        TelemetryEvent,
        TelemetryExporter,
    )

    EXPORTER_AVAILABLE = True
except ImportError:
    EXPORTER_AVAILABLE = False
    TelemetryEvent = None
    SentinelConnector = None
    TelemetryExporter = None


pytestmark = pytest.mark.skipif(not EXPORTER_AVAILABLE, reason="SIEM exporter module not available")


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def sentinel_config():
    """Fixture: Azure Sentinel configuration."""
    return {
        "dce_endpoint": "https://test-dce.monitor.azure.com",
        "dcr_id": "dcr-haymaker-telemetry",
        "stream_name": "Custom-HayMakerTelemetry",
    }


@pytest.fixture
def mock_azure_services():
    """Fixture: Mock all Azure SDK services."""
    with (
        patch(
            "azure_haymaker.knowledge_worker.telemetry.exporter.DefaultAzureCredential"
        ) as mock_cred,
        patch(
            "azure_haymaker.knowledge_worker.telemetry.exporter.LogsIngestionClient"
        ) as mock_client_class,
    ):
        mock_credential = MagicMock()
        mock_cred.return_value = mock_credential

        mock_client = MagicMock()
        mock_client.upload = MagicMock()  # Synchronous method, not async
        mock_client.close = MagicMock()  # Synchronous method, not async
        mock_client_class.return_value = mock_client

        yield {
            "credential": mock_credential,
            "client_class": mock_client_class,
            "client": mock_client,
        }


@pytest.fixture
async def running_exporter(sentinel_config, mock_azure_services):
    """Fixture: Running TelemetryExporter instance."""
    connector = SentinelConnector(
        dce_endpoint=sentinel_config["dce_endpoint"],
        dcr_id=sentinel_config["dcr_id"],
        stream_name=sentinel_config["stream_name"],
    )
    exporter = TelemetryExporter(connector=connector)

    await exporter.start()
    yield exporter
    await exporter.stop()


def create_worker_event(worker_id: str, run_id: str, event_type: str) -> dict:
    """Helper: Create a worker telemetry event."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "source": "knowledge_worker",
        "severity": "info",
        "data": {
            "worker_id": worker_id,
            "action": event_type.split(".")[-1],
            "duration_ms": 125,
        },
        "worker_id": worker_id,
        "run_id": run_id,
    }


# ==============================================================================
# LIFECYCLE INTEGRATION TESTS
# ==============================================================================


class TestExporterLifecycleIntegration:
    """Integration tests for exporter lifecycle."""

    @pytest.mark.asyncio
    async def test_exporter_starts_and_stops_cleanly(self, sentinel_config, mock_azure_services):
        """Test exporter can start and stop without errors."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )
        exporter = TelemetryExporter(connector=connector)

        # Start
        await exporter.start()
        assert exporter.is_running
        assert exporter.connector.is_connected

        # Stop
        await exporter.stop()
        assert not exporter.is_running
        assert not exporter.connector.is_connected

    @pytest.mark.asyncio
    async def test_exporter_survives_connector_failures_on_start(
        self, sentinel_config, mock_azure_services
    ):
        """Test exporter handles connector failures during startup."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )
        exporter = TelemetryExporter(connector=connector)

        # Simulate connection failure
        mock_azure_services["client_class"].side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await exporter.start()

        assert not exporter.is_running

    @pytest.mark.asyncio
    async def test_exporter_flushes_events_on_stop(self, sentinel_config, mock_azure_services):
        """Test exporter flushes pending events when stopping."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )
        exporter = TelemetryExporter(connector=connector)

        await exporter.start()

        # Queue some events
        run_id = str(uuid4())
        for i in range(5):
            event = create_worker_event(f"kw-{i:03d}", run_id, "worker.action.completed")
            await exporter.emit_event(event)

        # Stop should flush
        await exporter.stop()

        # Verify events were sent
        assert mock_azure_services["client"].upload.call_count >= 5


# ==============================================================================
# MULTI-WORKER TELEMETRY TESTS
# ==============================================================================


class TestMultiWorkerTelemetry:
    """Integration tests for multi-worker telemetry scenarios."""

    @pytest.mark.asyncio
    async def test_collects_telemetry_from_multiple_workers(
        self, running_exporter, mock_azure_services
    ):
        """Test collecting and exporting telemetry from multiple workers."""
        run_id = str(uuid4())
        worker_count = 10

        # Simulate multiple workers emitting events
        for worker_idx in range(worker_count):
            worker_id = f"kw-{worker_idx:03d}"

            # Each worker emits multiple events
            for event_type in ["worker.started", "worker.action.completed", "worker.stopped"]:
                event = create_worker_event(worker_id, run_id, event_type)
                await running_exporter.emit_event(event)

        # Verify all events were sent
        total_events = worker_count * 3
        assert mock_azure_services["client"].upload.call_count >= total_events

    @pytest.mark.asyncio
    async def test_handles_concurrent_event_emission(self, running_exporter, mock_azure_services):
        """Test handling concurrent event emission from multiple workers."""
        run_id = str(uuid4())
        worker_count = 20

        async def emit_worker_events(worker_idx: int):
            """Emit events for a single worker."""
            worker_id = f"kw-{worker_idx:03d}"
            for _ in range(5):
                event = create_worker_event(worker_id, run_id, "worker.action.completed")
                await running_exporter.emit_event(event)

        # Emit events concurrently
        tasks = [emit_worker_events(i) for i in range(worker_count)]
        await asyncio.gather(*tasks)

        # Verify all events were sent
        total_events = worker_count * 5
        assert mock_azure_services["client"].upload.call_count >= total_events

    @pytest.mark.asyncio
    async def test_aggregates_telemetry_by_run_id(self, running_exporter, mock_azure_services):
        """Test telemetry can be aggregated by run_id."""
        run_id_1 = str(uuid4())
        run_id_2 = str(uuid4())

        # Run 1: 5 workers
        for i in range(5):
            event = create_worker_event(f"kw-{i:03d}", run_id_1, "worker.action.completed")
            await running_exporter.emit_event(event)

        # Run 2: 3 workers
        for i in range(3):
            event = create_worker_event(f"kw-{i:03d}", run_id_2, "worker.action.completed")
            await running_exporter.emit_event(event)

        # Verify events from both runs were sent
        assert mock_azure_services["client"].upload.call_count >= 8

        # Verify events contain correct run_ids
        all_calls = mock_azure_services["client"].upload.call_args_list
        sent_logs = []
        for call in all_calls:
            if "logs" in call.kwargs:  # Correct parameter name
                sent_logs.extend(call.kwargs["logs"])

        # Check run_ids are present in logs
        run_ids_found = {log.get("run_id") for log in sent_logs if isinstance(log, dict)}
        assert run_id_1 in run_ids_found or run_id_2 in run_ids_found


# ==============================================================================
# ERROR RECOVERY INTEGRATION TESTS
# ==============================================================================


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_recovers_from_transient_network_errors(
        self, sentinel_config, mock_azure_services
    ):
        """Test recovery from transient network errors with retry."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
            max_retries=3,
            base_delay=0.01,  # Fast for testing
        )
        exporter = TelemetryExporter(connector=connector)

        await exporter.start()

        # Simulate transient failures then success
        mock_azure_services["client"].upload.side_effect = [
            Exception("Connection timeout"),
            Exception("Connection reset"),
            None,  # Success
        ]

        run_id = str(uuid4())
        event = create_worker_event("kw-001", run_id, "worker.action.completed")

        # Should succeed after retries
        await exporter.emit_event(event)

        # Verify retries happened
        assert mock_azure_services["client"].upload.call_count == 3

        await exporter.stop()

    @pytest.mark.asyncio
    async def test_uses_dlq_after_exhausting_retries(self, sentinel_config, mock_azure_services):
        """Test events go to DLQ after exhausting retries."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
            max_retries=2,
            base_delay=0.01,
        )
        exporter = TelemetryExporter(connector=connector)

        await exporter.start()

        # Simulate persistent failure
        mock_azure_services["client"].upload.side_effect = Exception("Persistent error")

        run_id = str(uuid4())
        for i in range(5):
            event = create_worker_event(f"kw-{i:03d}", run_id, "worker.action.completed")
            await exporter.emit_event(event)

        # All events should be in DLQ
        assert exporter.get_dlq_size() == 5

        await exporter.stop()

    @pytest.mark.asyncio
    async def test_handles_rate_limiting_gracefully(self, sentinel_config, mock_azure_services):
        """Test graceful handling of Azure rate limiting."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
            max_retries=3,
            base_delay=0.01,
        )
        exporter = TelemetryExporter(connector=connector)

        await exporter.start()

        # Simulate rate limit then success
        mock_azure_services["client"].upload.side_effect = [
            Exception("HTTP 429: Too Many Requests"),
            None,  # Success after backoff
        ]

        run_id = str(uuid4())
        event = create_worker_event("kw-001", run_id, "worker.action.completed")

        await exporter.emit_event(event)

        # Should have retried and succeeded
        assert mock_azure_services["client"].upload.call_count == 2

        await exporter.stop()

    @pytest.mark.asyncio
    async def test_continues_operation_after_partial_failures(
        self, sentinel_config, mock_azure_services
    ):
        """Test exporter continues operating after partial failures."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
            max_retries=1,
            base_delay=0.01,
        )
        exporter = TelemetryExporter(connector=connector)

        await exporter.start()

        run_id = str(uuid4())

        # First event fails
        mock_azure_services["client"].upload.side_effect = Exception("Error")
        event1 = create_worker_event("kw-001", run_id, "worker.action.completed")
        await exporter.emit_event(event1)

        # Second event succeeds
        mock_azure_services["client"].upload.side_effect = None
        event2 = create_worker_event("kw-002", run_id, "worker.action.completed")
        await exporter.emit_event(event2)

        # Should have 1 in DLQ and 1 succeeded
        assert exporter.get_dlq_size() == 1

        await exporter.stop()


# ==============================================================================
# BATCH PROCESSING INTEGRATION TESTS
# ==============================================================================


class TestBatchProcessingIntegration:
    """Integration tests for batch processing scenarios."""

    @pytest.mark.asyncio
    async def test_processes_large_event_batches(self, sentinel_config, mock_azure_services):
        """Test processing large batches of events efficiently."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )

        await connector.connect()

        # Create large batch
        run_id = str(uuid4())
        events = [
            TelemetryEvent(
                timestamp=datetime.now(UTC).isoformat(),
                event_type="worker.action.completed",
                source="knowledge_worker",
                severity="info",
                data={"index": i},
                worker_id=f"kw-{i:03d}",
                run_id=run_id,
            )
            for i in range(100)
        ]

        # Send batch
        await connector.send_batch(events)

        # Verify batch was sent
        mock_azure_services["client"].upload.assert_called_once()
        call_kwargs = mock_azure_services["client"].upload.call_args.kwargs
        assert len(call_kwargs["logs"]) == 100  # Correct parameter name

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_handles_empty_batch_gracefully(self, sentinel_config, mock_azure_services):
        """Test handling of empty batch doesn't cause errors."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )

        await connector.connect()

        # Send empty batch
        await connector.send_batch([])

        # Should not call upload
        mock_azure_services["client"].upload.assert_not_called()

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_retries_failed_batches(self, sentinel_config, mock_azure_services):
        """Test batch sends are retried on failure."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
            max_retries=2,
            base_delay=0.01,
        )

        await connector.connect()

        # Simulate failure then success
        mock_azure_services["client"].upload.side_effect = [
            Exception("Batch upload failed"),
            None,  # Success
        ]

        run_id = str(uuid4())
        events = [
            TelemetryEvent(
                timestamp=datetime.now(UTC).isoformat(),
                event_type="test.event",
                source="test",
                severity="info",
                data={},
                worker_id="kw-001",
                run_id=run_id,
            )
            for _ in range(10)
        ]

        await connector.send_batch(events)

        # Should have retried
        assert mock_azure_services["client"].upload.call_count == 2

        await connector.disconnect()


# ==============================================================================
# DLQ MANAGEMENT INTEGRATION TESTS
# ==============================================================================


class TestDLQManagementIntegration:
    """Integration tests for DLQ management."""

    @pytest.mark.asyncio
    async def test_dlq_overflow_handling(self, sentinel_config, mock_azure_services):
        """Test DLQ handles overflow by dropping oldest events."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
            max_retries=1,
            base_delay=0.01,
        )
        exporter = TelemetryExporter(connector=connector, max_dlq_size=10)

        await exporter.start()

        # Simulate all events failing
        mock_azure_services["client"].upload.side_effect = Exception("All fail")

        run_id = str(uuid4())
        for i in range(20):
            event = create_worker_event(f"kw-{i:03d}", run_id, "worker.action.completed")
            await exporter.emit_event(event)

        # DLQ should be capped at max_dlq_size
        assert exporter.get_dlq_size() == 10

        await exporter.stop()

    @pytest.mark.asyncio
    async def test_dlq_events_can_be_retrieved(self, sentinel_config, mock_azure_services):
        """Test failed events in DLQ can be retrieved for inspection."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
            max_retries=1,
            base_delay=0.01,
        )
        exporter = TelemetryExporter(connector=connector)

        await exporter.start()

        # Fail some events
        mock_azure_services["client"].upload.side_effect = Exception("Fail")

        run_id = str(uuid4())
        for i in range(3):
            event = create_worker_event(f"kw-{i:03d}", run_id, "worker.action.completed")
            await exporter.emit_event(event)

        # Retrieve DLQ contents
        dlq_events = exporter.get_dead_letter_queue()

        assert len(dlq_events) == 3
        assert all(isinstance(e, TelemetryEvent) for e in dlq_events)

        await exporter.stop()


# ==============================================================================
# HEALTH MONITORING INTEGRATION TESTS
# ==============================================================================


class TestHealthMonitoringIntegration:
    """Integration tests for health monitoring."""

    @pytest.mark.asyncio
    async def test_health_check_reflects_connection_state(
        self, sentinel_config, mock_azure_services
    ):
        """Test health check accurately reflects connection state."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )

        # Before connection
        is_healthy = await connector.health_check()
        assert is_healthy is False

        # After connection
        await connector.connect()
        is_healthy = await connector.health_check()
        assert is_healthy is True

        # After disconnection
        await connector.disconnect()
        is_healthy = await connector.health_check()
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_detects_service_degradation(
        self, sentinel_config, mock_azure_services
    ):
        """Test health check detects when Azure service is degraded."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )

        await connector.connect()

        # Simulate service degradation
        mock_azure_services["client"].upload.side_effect = Exception("Service degraded")

        is_healthy = await connector.health_check()
        assert is_healthy is False

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_periodic_health_checks_during_operation(
        self, running_exporter, mock_azure_services
    ):
        """Test periodic health checks can be performed during operation."""
        # Perform multiple health checks while emitting events
        run_id = str(uuid4())

        for i in range(5):
            # Emit event
            event = create_worker_event(f"kw-{i:03d}", run_id, "worker.action.completed")
            await running_exporter.emit_event(event)

            # Check health
            is_healthy = await running_exporter.connector.health_check()
            assert is_healthy is True


# ==============================================================================
# CONFIGURATION VALIDATION TESTS
# ==============================================================================


class TestConfigurationValidation:
    """Integration tests for configuration validation."""

    def test_rejects_invalid_dce_endpoint(self):
        """Test connector rejects invalid DCE endpoint format."""
        with pytest.raises((ValueError, Exception)):
            SentinelConnector(
                dce_endpoint="not-a-valid-url",
                dcr_id="dcr-123",
                stream_name="Custom-Stream",
            )

    def test_rejects_empty_dcr_id(self):
        """Test connector rejects empty DCR ID."""
        with pytest.raises((ValueError, Exception)):
            SentinelConnector(
                dce_endpoint="https://test-dce.monitor.azure.com",
                dcr_id="",
                stream_name="Custom-Stream",
            )

    def test_rejects_empty_stream_name(self):
        """Test connector rejects empty stream name."""
        with pytest.raises((ValueError, Exception)):
            SentinelConnector(
                dce_endpoint="https://test-dce.monitor.azure.com",
                dcr_id="dcr-123",
                stream_name="",
            )

    def test_validates_retry_configuration(self, sentinel_config):
        """Test connector validates retry configuration parameters."""
        # Negative max_retries
        with pytest.raises((ValueError, Exception)):
            SentinelConnector(
                dce_endpoint=sentinel_config["dce_endpoint"],
                dcr_id=sentinel_config["dcr_id"],
                stream_name=sentinel_config["stream_name"],
                max_retries=-1,
            )

        # Negative delays
        with pytest.raises((ValueError, Exception)):
            SentinelConnector(
                dce_endpoint=sentinel_config["dce_endpoint"],
                dcr_id=sentinel_config["dcr_id"],
                stream_name=sentinel_config["stream_name"],
                base_delay=-1.0,
            )


# ==============================================================================
# REAL-WORLD SCENARIO TESTS
# ==============================================================================


class TestRealWorldScenarios:
    """Integration tests for real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_typical_knowledge_worker_run(self, running_exporter, mock_azure_services):
        """Test typical knowledge worker run with realistic event sequence."""
        run_id = str(uuid4())
        worker_id = "kw-001"

        # Simulate realistic event sequence
        event_sequence = [
            ("worker.started", "info"),
            ("worker.identity.created", "info"),
            ("worker.m365.logged_in", "info"),
            ("worker.action.send_email", "info"),
            ("worker.action.create_meeting", "info"),
            ("worker.action.send_teams_message", "info"),
            ("worker.action.completed", "info"),
            ("worker.m365.logged_out", "info"),
            ("worker.stopped", "info"),
        ]

        for event_type, severity in event_sequence:
            event = {
                "timestamp": datetime.now(UTC).isoformat(),
                "event_type": event_type,
                "source": "knowledge_worker",
                "severity": severity,
                "data": {"worker_id": worker_id, "action": event_type},
                "worker_id": worker_id,
                "run_id": run_id,
            }
            await running_exporter.emit_event(event)

        # Verify all events were sent
        assert mock_azure_services["client"].upload.call_count == len(event_sequence)

    @pytest.mark.asyncio
    async def test_error_event_escalation(self, running_exporter, mock_azure_services):
        """Test error events with increasing severity are handled correctly."""
        run_id = str(uuid4())
        worker_id = "kw-001"

        error_events = [
            ("worker.warning.retry_needed", "warning"),
            ("worker.error.auth_failed", "error"),
            ("worker.critical.operation_failed", "critical"),
        ]

        for event_type, severity in error_events:
            event = {
                "timestamp": datetime.now(UTC).isoformat(),
                "event_type": event_type,
                "source": "knowledge_worker",
                "severity": severity,
                "data": {
                    "worker_id": worker_id,
                    "error": "Simulated error",
                    "context": {"attempt": 1},
                },
                "worker_id": worker_id,
                "run_id": run_id,
            }
            await running_exporter.emit_event(event)

        # All error events should be sent immediately
        assert mock_azure_services["client"].upload.call_count == len(error_events)

    @pytest.mark.asyncio
    async def test_long_running_export_session(self, sentinel_config, mock_azure_services):
        """Test exporter handles long-running session with many events."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )
        exporter = TelemetryExporter(connector=connector)

        await exporter.start()

        # Simulate long-running session
        run_id = str(uuid4())
        worker_count = 50
        events_per_worker = 10

        for worker_idx in range(worker_count):
            worker_id = f"kw-{worker_idx:03d}"
            for event_idx in range(events_per_worker):
                event = create_worker_event(worker_id, run_id, f"worker.action.{event_idx}")
                await exporter.emit_event(event)

        # Verify all events were processed
        total_events = worker_count * events_per_worker
        assert mock_azure_services["client"].upload.call_count >= total_events

        await exporter.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
