"""Unit tests for SIEM Telemetry Export Pipeline.

This module contains comprehensive unit tests for the SIEM export pipeline
following TDD methodology. All tests are written BEFORE implementation.

Test Coverage:
- TelemetryEvent dataclass validation
- SentinelConnector connection/disconnection lifecycle
- SentinelConnector event sending with retry logic
- SentinelConnector batch operations
- SentinelConnector health checks
- TelemetryExporter lifecycle management
- TelemetryExporter event emission
- TelemetryExporter DLQ behavior
- Error handling (network, auth, rate limits)
- Retry logic with exponential backoff

Tests follow the testing pyramid: 60% unit, 30% integration, 10% E2E
"""

from dataclasses import asdict
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Import the modules under test (will fail initially - TDD red phase)
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
def sample_event():
    """Fixture: Sample telemetry event."""
    return TelemetryEvent(
        timestamp=datetime.now(UTC).isoformat(),
        event_type="worker.action.completed",
        source="knowledge_worker",
        severity="info",
        data={"action": "send_email", "status": "success", "duration_ms": 125},
        worker_id="kw-001",
        run_id=str(uuid4()),
    )


@pytest.fixture
def sentinel_config():
    """Fixture: Azure Sentinel configuration."""
    return {
        "dce_endpoint": "https://test-dce.monitor.azure.com",
        "dcr_id": "dcr-test123",
        "stream_name": "Custom-HayMakerTelemetry",
    }


@pytest.fixture
def mock_azure_monitor_client():
    """Fixture: Mock Azure Monitor Ingestion client."""
    client = MagicMock()
    client.upload = MagicMock()  # Synchronous method, not async
    client.close = MagicMock()  # Synchronous method, not async
    return client


@pytest.fixture
def sentinel_connector(sentinel_config):
    """Fixture: SentinelConnector instance."""
    return SentinelConnector(
        dce_endpoint=sentinel_config["dce_endpoint"],
        dcr_id=sentinel_config["dcr_id"],
        stream_name=sentinel_config["stream_name"],
    )


@pytest.fixture
def telemetry_exporter(sentinel_connector):
    """Fixture: TelemetryExporter instance."""
    return TelemetryExporter(connector=sentinel_connector)


# ==============================================================================
# TELEMETRY EVENT TESTS
# ==============================================================================


class TestTelemetryEvent:
    """Tests for TelemetryEvent dataclass."""

    def test_telemetry_event_creation(self):
        """Test TelemetryEvent dataclass can be created with required fields."""
        event = TelemetryEvent(
            timestamp="2024-12-01T10:00:00Z",
            event_type="worker.started",
            source="knowledge_worker",
            severity="info",
            data={"worker_id": "kw-001"},
            worker_id="kw-001",
            run_id="run-123",
        )

        assert event.timestamp == "2024-12-01T10:00:00Z"
        assert event.event_type == "worker.started"
        assert event.source == "knowledge_worker"
        assert event.severity == "info"
        assert event.worker_id == "kw-001"
        assert event.run_id == "run-123"

    def test_telemetry_event_with_nested_data(self):
        """Test TelemetryEvent handles nested data structures."""
        event = TelemetryEvent(
            timestamp="2024-12-01T10:00:00Z",
            event_type="worker.action.completed",
            source="knowledge_worker",
            severity="info",
            data={
                "action": "send_email",
                "metadata": {"to": "user@example.com", "subject": "Test"},
                "metrics": {"duration_ms": 125, "retry_count": 0},
            },
            worker_id="kw-001",
            run_id="run-123",
        )

        assert isinstance(event.data, dict)
        assert "metadata" in event.data
        assert event.data["metadata"]["to"] == "user@example.com"

    def test_telemetry_event_serialization(self, sample_event):
        """Test TelemetryEvent can be serialized to dict."""
        event_dict = asdict(sample_event)

        assert isinstance(event_dict, dict)
        assert "timestamp" in event_dict
        assert "event_type" in event_dict
        assert "data" in event_dict
        assert event_dict["worker_id"] == "kw-001"

    def test_telemetry_event_severity_levels(self):
        """Test TelemetryEvent supports different severity levels."""
        severities = ["debug", "info", "warning", "error", "critical"]

        for severity in severities:
            event = TelemetryEvent(
                timestamp="2024-12-01T10:00:00Z",
                event_type="test.event",
                source="test",
                severity=severity,
                data={},
                worker_id="kw-001",
                run_id="run-123",
            )
            assert event.severity == severity

    def test_telemetry_event_with_empty_data(self):
        """Test TelemetryEvent handles empty data dict."""
        event = TelemetryEvent(
            timestamp="2024-12-01T10:00:00Z",
            event_type="test.event",
            source="test",
            severity="info",
            data={},
            worker_id="kw-001",
            run_id="run-123",
        )

        assert event.data == {}


# ==============================================================================
# SENTINEL CONNECTOR TESTS - INITIALIZATION
# ==============================================================================


class TestSentinelConnectorInitialization:
    """Tests for SentinelConnector initialization."""

    def test_sentinel_connector_initialization(self, sentinel_config):
        """Test SentinelConnector initializes with required parameters."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )

        assert connector.dce_endpoint == sentinel_config["dce_endpoint"]
        assert connector.dcr_id == sentinel_config["dcr_id"]
        assert connector.stream_name == sentinel_config["stream_name"]

    def test_sentinel_connector_default_retry_config(self, sentinel_connector):
        """Test SentinelConnector uses default retry configuration."""
        assert sentinel_connector.max_retries == 3
        assert sentinel_connector.base_delay == 1.0
        assert sentinel_connector.max_delay == 60.0

    def test_sentinel_connector_custom_retry_config(self, sentinel_config):
        """Test SentinelConnector accepts custom retry configuration."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
        )

        assert connector.max_retries == 5
        assert connector.base_delay == 2.0
        assert connector.max_delay == 120.0


# ==============================================================================
# SENTINEL CONNECTOR TESTS - CONNECTION LIFECYCLE
# ==============================================================================


class TestSentinelConnectorLifecycle:
    """Tests for SentinelConnector connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_creates_client(self, sentinel_connector):
        """Test connect() creates Azure Monitor client."""
        with patch(
            "azure_haymaker.knowledge_worker.telemetry.exporter.LogsIngestionClient"
        ) as mock_client_class:
            mock_credential = MagicMock()
            with patch(
                "azure_haymaker.knowledge_worker.telemetry.exporter.DefaultAzureCredential",
                return_value=mock_credential,
            ):
                await sentinel_connector.connect()

                mock_client_class.assert_called_once_with(
                    endpoint=sentinel_connector.dce_endpoint, credential=mock_credential
                )
                assert sentinel_connector.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, sentinel_connector):
        """Test connect() is idempotent - multiple calls are safe."""
        with patch(
            "azure_haymaker.knowledge_worker.telemetry.exporter.LogsIngestionClient"
        ) as mock_client_class:
            mock_credential = MagicMock()
            with patch(
                "azure_haymaker.knowledge_worker.telemetry.exporter.DefaultAzureCredential",
                return_value=mock_credential,
            ):
                await sentinel_connector.connect()
                await sentinel_connector.connect()

                # Should only create client once
                assert mock_client_class.call_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self, sentinel_connector, mock_azure_monitor_client):
        """Test disconnect() closes Azure Monitor client."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        await sentinel_connector.disconnect()

        mock_azure_monitor_client.close.assert_called_once()
        assert sentinel_connector.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, sentinel_connector):
        """Test disconnect() handles being called when not connected."""
        # Should not raise an error
        await sentinel_connector.disconnect()
        assert sentinel_connector.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_handles_authentication_error(self, sentinel_connector):
        """Test connect() handles authentication errors."""
        with (
            patch(
                "azure_haymaker.knowledge_worker.telemetry.exporter.DefaultAzureCredential",
                side_effect=Exception("Authentication failed"),
            ),
            pytest.raises(Exception, match="Authentication failed"),
        ):
            await sentinel_connector.connect()


# ==============================================================================
# SENTINEL CONNECTOR TESTS - SEND EVENT
# ==============================================================================


class TestSentinelConnectorSendEvent:
    """Tests for SentinelConnector send_event method."""

    @pytest.mark.asyncio
    async def test_send_event_success(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_event successfully sends a single event."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        await sentinel_connector.send_event(sample_event)

        mock_azure_monitor_client.upload.assert_called_once()
        call_args = mock_azure_monitor_client.upload.call_args
        assert call_args.kwargs["rule_id"] == sentinel_connector.dcr_id
        assert call_args.kwargs["stream_name"] == sentinel_connector.stream_name

    @pytest.mark.asyncio
    async def test_send_event_requires_connection(self, sentinel_connector, sample_event):
        """Test send_event raises error when not connected."""
        with pytest.raises(RuntimeError, match="not connected"):
            await sentinel_connector.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_send_event_with_retry_on_transient_error(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_event retries on transient network errors."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        # Fail twice, then succeed
        mock_azure_monitor_client.upload.side_effect = [
            Exception("Network timeout"),
            Exception("Connection reset"),
            None,
        ]

        await sentinel_connector.send_event(sample_event)

        # Should have retried and eventually succeeded
        assert mock_azure_monitor_client.upload.call_count == 3

    @pytest.mark.asyncio
    async def test_send_event_exhausts_retries(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_event raises after exhausting retries."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True
        sentinel_connector.max_retries = 2

        # Always fail
        mock_azure_monitor_client.upload.side_effect = Exception("Persistent error")

        with pytest.raises(Exception, match="Persistent error"):
            await sentinel_connector.send_event(sample_event)

        # Should have tried: initial + 2 retries = 3 attempts
        assert mock_azure_monitor_client.upload.call_count == 3

    @pytest.mark.asyncio
    async def test_send_event_exponential_backoff(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_event uses exponential backoff between retries."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True
        sentinel_connector.base_delay = 0.1  # Fast for testing

        mock_azure_monitor_client.upload.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            None,
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await sentinel_connector.send_event(sample_event)

            # Should have slept with exponential backoff
            assert mock_sleep.call_count == 2
            # First retry: base_delay * 2^0 = 0.1
            # Second retry: base_delay * 2^1 = 0.2
            delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert delays[0] == 0.1
            assert delays[1] == 0.2

    @pytest.mark.asyncio
    async def test_send_event_max_delay_cap(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_event caps delay at max_delay."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True
        sentinel_connector.base_delay = 30.0
        sentinel_connector.max_delay = 60.0
        sentinel_connector.max_retries = 3

        mock_azure_monitor_client.upload.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3"),
            None,
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await sentinel_connector.send_event(sample_event)

            # All delays should be capped at max_delay
            delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert all(delay <= sentinel_connector.max_delay for delay in delays)

    @pytest.mark.asyncio
    async def test_send_event_handles_rate_limit_error(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_event handles rate limit errors with retry."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        # Simulate rate limit then success
        rate_limit_error = Exception("HTTP 429: Too Many Requests")
        mock_azure_monitor_client.upload.side_effect = [rate_limit_error, None]

        await sentinel_connector.send_event(sample_event)

        assert mock_azure_monitor_client.upload.call_count == 2


# ==============================================================================
# SENTINEL CONNECTOR TESTS - SEND BATCH
# ==============================================================================


class TestSentinelConnectorSendBatch:
    """Tests for SentinelConnector send_batch method."""

    @pytest.mark.asyncio
    async def test_send_batch_success(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_batch successfully sends multiple events."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        events = [sample_event, sample_event, sample_event]

        await sentinel_connector.send_batch(events)

        mock_azure_monitor_client.upload.assert_called_once()
        call_args = mock_azure_monitor_client.upload.call_args
        logs = call_args.kwargs["logs"]  # Correct parameter name
        assert len(logs) == 3

    @pytest.mark.asyncio
    async def test_send_batch_empty_list(self, sentinel_connector, mock_azure_monitor_client):
        """Test send_batch handles empty event list."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        await sentinel_connector.send_batch([])

        # Should not call upload for empty batch
        mock_azure_monitor_client.upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_batch_requires_connection(self, sentinel_connector, sample_event):
        """Test send_batch raises error when not connected."""
        with pytest.raises(RuntimeError, match="not connected"):
            await sentinel_connector.send_batch([sample_event])

    @pytest.mark.asyncio
    async def test_send_batch_with_retry(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_batch retries on failure."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        events = [sample_event, sample_event]

        # Fail once, then succeed
        mock_azure_monitor_client.upload.side_effect = [
            Exception("Network error"),
            None,
        ]

        await sentinel_connector.send_batch(events)

        assert mock_azure_monitor_client.upload.call_count == 2

    @pytest.mark.asyncio
    async def test_send_batch_partial_failure_handling(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test send_batch handles partial batch failures."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        events = [sample_event] * 10

        # Simulate partial failure response
        partial_error = Exception("Some events failed")
        mock_azure_monitor_client.upload.side_effect = partial_error

        with pytest.raises(Exception, match="Some events failed"):
            await sentinel_connector.send_batch(events)


# ==============================================================================
# SENTINEL CONNECTOR TESTS - HEALTH CHECK
# ==============================================================================


class TestSentinelConnectorHealthCheck:
    """Tests for SentinelConnector health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_when_connected(self, sentinel_connector, mock_azure_monitor_client):
        """Test health_check returns True when connected and healthy."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        # Mock a successful test upload
        mock_azure_monitor_client.upload.return_value = None

        is_healthy = await sentinel_connector.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_when_not_connected(self, sentinel_connector):
        """Test health_check returns False when not connected."""
        is_healthy = await sentinel_connector.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_catches_client_errors(
        self, sentinel_connector, mock_azure_monitor_client
    ):
        """Test health_check returns False on client errors."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        mock_azure_monitor_client.upload.side_effect = Exception("Service unavailable")

        is_healthy = await sentinel_connector.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_does_not_throw(self, sentinel_connector, mock_azure_monitor_client):
        """Test health_check never throws exceptions."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        mock_azure_monitor_client.upload.side_effect = Exception("Unexpected error")

        # Should not raise
        is_healthy = await sentinel_connector.health_check()
        assert is_healthy is False


# ==============================================================================
# TELEMETRY EXPORTER TESTS - INITIALIZATION
# ==============================================================================


class TestTelemetryExporterInitialization:
    """Tests for TelemetryExporter initialization."""

    def test_telemetry_exporter_initialization(self, sentinel_connector):
        """Test TelemetryExporter initializes with connector."""
        exporter = TelemetryExporter(connector=sentinel_connector)

        assert exporter.connector == sentinel_connector
        assert exporter.is_running is False

    def test_telemetry_exporter_default_dlq_size(self, telemetry_exporter):
        """Test TelemetryExporter uses default DLQ size."""
        assert telemetry_exporter.max_dlq_size == 1000

    def test_telemetry_exporter_custom_dlq_size(self, sentinel_connector):
        """Test TelemetryExporter accepts custom DLQ size."""
        exporter = TelemetryExporter(connector=sentinel_connector, max_dlq_size=500)

        assert exporter.max_dlq_size == 500


# ==============================================================================
# TELEMETRY EXPORTER TESTS - LIFECYCLE
# ==============================================================================


class TestTelemetryExporterLifecycle:
    """Tests for TelemetryExporter lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_connects_to_sentinel(self, telemetry_exporter):
        """Test start() connects the SentinelConnector."""
        with patch.object(telemetry_exporter.connector, "connect", new_callable=AsyncMock):
            await telemetry_exporter.start()

            telemetry_exporter.connector.connect.assert_called_once()
            assert telemetry_exporter.is_running is True

    @pytest.mark.asyncio
    async def test_start_idempotent(self, telemetry_exporter):
        """Test start() is idempotent - multiple calls are safe."""
        with patch.object(
            telemetry_exporter.connector, "connect", new_callable=AsyncMock
        ) as mock_connect:
            await telemetry_exporter.start()
            await telemetry_exporter.start()

            # Should only connect once
            assert mock_connect.call_count == 1

    @pytest.mark.asyncio
    async def test_stop_disconnects_from_sentinel(self, telemetry_exporter):
        """Test stop() disconnects the SentinelConnector."""
        telemetry_exporter._running = True

        with patch.object(telemetry_exporter.connector, "disconnect", new_callable=AsyncMock):
            await telemetry_exporter.stop()

            telemetry_exporter.connector.disconnect.assert_called_once()
            assert telemetry_exporter.is_running is False

    @pytest.mark.asyncio
    async def test_stop_flushes_pending_events(self, telemetry_exporter, sample_event):
        """Test stop() flushes any pending events before stopping."""
        telemetry_exporter._running = True
        telemetry_exporter._pending_events = [sample_event]

        with (
            patch.object(telemetry_exporter.connector, "send_batch", new_callable=AsyncMock),
            patch.object(telemetry_exporter.connector, "disconnect", new_callable=AsyncMock),
        ):
            await telemetry_exporter.stop()

            telemetry_exporter.connector.send_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, telemetry_exporter):
        """Test stop() handles being called when not running."""
        # Should not raise an error
        await telemetry_exporter.stop()
        assert telemetry_exporter.is_running is False


# ==============================================================================
# TELEMETRY EXPORTER TESTS - EMIT EVENT
# ==============================================================================


class TestTelemetryExporterEmitEvent:
    """Tests for TelemetryExporter emit_event method."""

    @pytest.mark.asyncio
    async def test_emit_event_converts_dict_to_telemetry_event(self, telemetry_exporter):
        """Test emit_event converts dict to TelemetryEvent."""
        telemetry_exporter._running = True

        event_dict = {
            "timestamp": "2024-12-01T10:00:00Z",
            "event_type": "test.event",
            "source": "test",
            "severity": "info",
            "data": {"key": "value"},
            "worker_id": "kw-001",
            "run_id": "run-123",
        }

        with patch.object(telemetry_exporter.connector, "send_event", new_callable=AsyncMock):
            await telemetry_exporter.emit_event(event_dict)

            telemetry_exporter.connector.send_event.assert_called_once()
            call_args = telemetry_exporter.connector.send_event.call_args
            event = call_args.args[0]
            assert isinstance(event, TelemetryEvent)
            assert event.event_type == "test.event"

    @pytest.mark.asyncio
    async def test_emit_event_sends_immediately(self, telemetry_exporter):
        """Test emit_event sends event immediately when running."""
        telemetry_exporter._running = True

        event_dict = {
            "timestamp": "2024-12-01T10:00:00Z",
            "event_type": "test.event",
            "source": "test",
            "severity": "info",
            "data": {},
            "worker_id": "kw-001",
            "run_id": "run-123",
        }

        with patch.object(
            telemetry_exporter.connector, "send_event", new_callable=AsyncMock
        ) as mock_send:
            await telemetry_exporter.emit_event(event_dict)

            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event_adds_to_dlq_on_failure(self, telemetry_exporter):
        """Test emit_event adds event to DLQ on send failure."""
        telemetry_exporter._running = True

        event_dict = {
            "timestamp": "2024-12-01T10:00:00Z",
            "event_type": "test.event",
            "source": "test",
            "severity": "info",
            "data": {},
            "worker_id": "kw-001",
            "run_id": "run-123",
        }

        with patch.object(
            telemetry_exporter.connector,
            "send_event",
            new_callable=AsyncMock,
            side_effect=Exception("Send failed"),
        ):
            await telemetry_exporter.emit_event(event_dict)

            assert telemetry_exporter.get_dlq_size() == 1

    @pytest.mark.asyncio
    async def test_emit_event_when_not_running(self, telemetry_exporter):
        """Test emit_event queues event when not running."""
        event_dict = {
            "timestamp": "2024-12-01T10:00:00Z",
            "event_type": "test.event",
            "source": "test",
            "severity": "info",
            "data": {},
            "worker_id": "kw-001",
            "run_id": "run-123",
        }

        await telemetry_exporter.emit_event(event_dict)

        # Should add to pending queue instead of sending
        assert len(telemetry_exporter._pending_events) == 1


# ==============================================================================
# TELEMETRY EXPORTER TESTS - DLQ BEHAVIOR
# ==============================================================================


class TestTelemetryExporterDLQ:
    """Tests for TelemetryExporter Dead Letter Queue behavior."""

    def test_get_dlq_size_initially_zero(self, telemetry_exporter):
        """Test get_dlq_size returns 0 initially."""
        assert telemetry_exporter.get_dlq_size() == 0

    @pytest.mark.asyncio
    async def test_dlq_accumulates_failed_events(self, telemetry_exporter):
        """Test DLQ accumulates events that fail to send."""
        telemetry_exporter._running = True

        event_dicts = [
            {
                "timestamp": "2024-12-01T10:00:00Z",
                "event_type": f"test.event.{i}",
                "source": "test",
                "severity": "info",
                "data": {},
                "worker_id": "kw-001",
                "run_id": "run-123",
            }
            for i in range(5)
        ]

        with patch.object(
            telemetry_exporter.connector,
            "send_event",
            new_callable=AsyncMock,
            side_effect=Exception("Send failed"),
        ):
            for event_dict in event_dicts:
                await telemetry_exporter.emit_event(event_dict)

            assert telemetry_exporter.get_dlq_size() == 5

    @pytest.mark.asyncio
    async def test_dlq_enforces_max_size(self, telemetry_exporter):
        """Test DLQ enforces maximum size limit."""
        telemetry_exporter._running = True
        telemetry_exporter.max_dlq_size = 3

        event_dicts = [
            {
                "timestamp": "2024-12-01T10:00:00Z",
                "event_type": f"test.event.{i}",
                "source": "test",
                "severity": "info",
                "data": {},
                "worker_id": "kw-001",
                "run_id": "run-123",
            }
            for i in range(5)
        ]

        with patch.object(
            telemetry_exporter.connector,
            "send_event",
            new_callable=AsyncMock,
            side_effect=Exception("Send failed"),
        ):
            for event_dict in event_dicts:
                await telemetry_exporter.emit_event(event_dict)

            # Should only keep most recent max_dlq_size events
            assert telemetry_exporter.get_dlq_size() == 3

    @pytest.mark.asyncio
    async def test_dlq_preserves_event_order(self, telemetry_exporter):
        """Test DLQ preserves event order (FIFO)."""
        telemetry_exporter._running = True

        event_dicts = [
            {
                "timestamp": "2024-12-01T10:00:00Z",
                "event_type": f"test.event.{i}",
                "source": "test",
                "severity": "info",
                "data": {"sequence": i},
                "worker_id": "kw-001",
                "run_id": "run-123",
            }
            for i in range(3)
        ]

        with patch.object(
            telemetry_exporter.connector,
            "send_event",
            new_callable=AsyncMock,
            side_effect=Exception("Send failed"),
        ):
            for event_dict in event_dicts:
                await telemetry_exporter.emit_event(event_dict)

            # Check order is preserved
            dlq_events = telemetry_exporter._dead_letter_queue
            assert dlq_events[0].data["sequence"] == 0
            assert dlq_events[1].data["sequence"] == 1
            assert dlq_events[2].data["sequence"] == 2


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================


class TestErrorHandling:
    """Tests for comprehensive error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handles_authentication_error(self, sentinel_connector):
        """Test graceful handling of Azure authentication errors."""
        with (
            patch(
                "azure_haymaker.knowledge_worker.telemetry.exporter.DefaultAzureCredential",
                side_effect=Exception("Authentication failed: Invalid credentials"),
            ),
            pytest.raises(Exception, match="Authentication failed"),
        ):
            await sentinel_connector.connect()

    @pytest.mark.asyncio
    async def test_handles_network_timeout(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test handling of network timeout errors."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        mock_azure_monitor_client.upload.side_effect = TimeoutError("Request timed out")

        with pytest.raises(TimeoutError):
            await sentinel_connector.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_handles_invalid_endpoint(self, sentinel_config):
        """Test handling of invalid DCE endpoint."""
        connector = SentinelConnector(
            dce_endpoint="https://invalid-endpoint",
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )

        with (
            patch(
                "azure_haymaker.knowledge_worker.telemetry.exporter.LogsIngestionClient",
                side_effect=ValueError("Invalid endpoint URL"),
            ),
            pytest.raises(ValueError, match="Invalid endpoint"),
        ):
            await connector.connect()

    @pytest.mark.asyncio
    async def test_handles_malformed_event_data(self, telemetry_exporter):
        """Test handling of malformed event data."""
        telemetry_exporter._running = True

        # Missing required fields
        malformed_event = {
            "timestamp": "2024-12-01T10:00:00Z",
            # Missing event_type, source, severity, etc.
        }

        with pytest.raises((KeyError, TypeError)):
            await telemetry_exporter.emit_event(malformed_event)

    @pytest.mark.asyncio
    async def test_handles_service_unavailable(
        self, sentinel_connector, sample_event, mock_azure_monitor_client
    ):
        """Test handling of Azure service unavailable errors."""
        sentinel_connector._client = mock_azure_monitor_client
        sentinel_connector._connected = True

        mock_azure_monitor_client.upload.side_effect = Exception("HTTP 503: Service Unavailable")

        with pytest.raises(Exception, match="Service Unavailable"):
            await sentinel_connector.send_event(sample_event)


# ==============================================================================
# INTEGRATION-STYLE TESTS (within unit test file)
# ==============================================================================


class TestEndToEndFlow:
    """Integration-style tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_workflow(self, sentinel_config):
        """Test complete exporter lifecycle from start to stop."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )
        exporter = TelemetryExporter(connector=connector)

        with (
            patch.object(connector, "connect", new_callable=AsyncMock),
            patch.object(connector, "send_event", new_callable=AsyncMock),
            patch.object(connector, "disconnect", new_callable=AsyncMock),
        ):
            # Start
            await exporter.start()
            assert exporter.is_running

            # Emit event
            event = {
                "timestamp": "2024-12-01T10:00:00Z",
                "event_type": "test.event",
                "source": "test",
                "severity": "info",
                "data": {},
                "worker_id": "kw-001",
                "run_id": "run-123",
            }
            await exporter.emit_event(event)

            # Stop
            await exporter.stop()
            assert not exporter.is_running

            connector.connect.assert_called_once()
            connector.send_event.assert_called_once()
            connector.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_processing_workflow(self, sentinel_config):
        """Test batch event processing workflow."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )

        events = [
            TelemetryEvent(
                timestamp="2024-12-01T10:00:00Z",
                event_type=f"test.event.{i}",
                source="test",
                severity="info",
                data={"index": i},
                worker_id="kw-001",
                run_id="run-123",
            )
            for i in range(10)
        ]

        with (
            patch.object(connector, "connect", new_callable=AsyncMock),
            patch.object(connector, "send_batch", new_callable=AsyncMock),
        ):
            await connector.connect()
            await connector.send_batch(events)

            connector.send_batch.assert_called_once()
            call_args = connector.send_batch.call_args
            sent_events = call_args.args[0]
            assert len(sent_events) == 10

    @pytest.mark.asyncio
    async def test_resilience_to_transient_failures(self, sentinel_config):
        """Test system resilience to transient failures."""
        connector = SentinelConnector(
            dce_endpoint=sentinel_config["dce_endpoint"],
            dcr_id=sentinel_config["dcr_id"],
            stream_name=sentinel_config["stream_name"],
        )
        exporter = TelemetryExporter(connector=connector)

        with (
            patch.object(connector, "connect", new_callable=AsyncMock),
            patch.object(connector, "_client") as mock_client,
        ):
            mock_client.upload = MagicMock(  # Synchronous method, not async
                side_effect=[
                    Exception("Transient error 1"),
                    Exception("Transient error 2"),
                    None,  # Success
                ]
            )
            connector._connected = True
            await exporter.start()

            event = {
                "timestamp": "2024-12-01T10:00:00Z",
                "event_type": "test.event",
                "source": "test",
                "severity": "info",
                "data": {},
                "worker_id": "kw-001",
                "run_id": "run-123",
            }

            # Should succeed after retries at connector level
            await exporter.emit_event(event)
            assert mock_client.upload.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
