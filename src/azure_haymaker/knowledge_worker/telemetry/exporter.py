"""SIEM Telemetry Export Pipeline for Azure Sentinel.

Ruthlessly simple pipeline for exporting telemetry to Azure Sentinel via
Azure Monitor Ingestion API with retry logic, DLQ, and health monitoring.

Architecture:
- TelemetryEvent: Event dataclass
- SentinelConnector: Sentinel client with exponential backoff retry
- TelemetryExporter: Orchestrator with DLQ

Zero external dependencies beyond Azure SDK.
"""

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import Any, cast

from azure.identity import DefaultAzureCredential
from azure.monitor.ingestion import LogsIngestionClient

logger = logging.getLogger(__name__)


@dataclass
class TelemetryEvent:
    """Telemetry event container.

    Attributes:
        timestamp: ISO 8601 timestamp
        event_type: Event type (e.g., "worker.action.completed")
        source: Event source (e.g., "knowledge_worker")
        severity: Event severity (debug, info, warning, error, critical)
        data: Event payload (arbitrary dict)
        worker_id: Worker identifier
        run_id: Run identifier
    """

    timestamp: str
    event_type: str
    source: str
    severity: str
    data: dict[str, Any]
    worker_id: str
    run_id: str


class SentinelConnector:
    """Azure Sentinel connector with retry logic.

    Manages connection to Azure Sentinel via Azure Monitor Ingestion API.
    Implements exponential backoff retry for transient failures.
    """

    def __init__(
        self,
        dce_endpoint: str,
        dcr_id: str,
        stream_name: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        """Initialize Sentinel connector.

        Args:
            dce_endpoint: Data Collection Endpoint URL
            dcr_id: Data Collection Rule ID
            stream_name: Stream name for logs
            max_retries: Maximum retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay cap (seconds)

        Raises:
            ValueError: If parameters are invalid
        """
        if not dce_endpoint or not dce_endpoint.startswith("https://"):
            raise ValueError("dce_endpoint must be a valid HTTPS URL")
        if not dcr_id or not stream_name:
            raise ValueError("dcr_id and stream_name cannot be empty")
        if max_retries < 0 or base_delay < 0:
            raise ValueError("max_retries and base_delay cannot be negative")

        self.dce_endpoint = dce_endpoint
        self.dcr_id = dcr_id
        self.stream_name = stream_name
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        self._client: LogsIngestionClient | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connector is connected."""
        return self._connected

    async def connect(self) -> None:
        """Connect to Azure Sentinel.

        Creates Azure Monitor Ingestion client with managed identity.

        Raises:
            Exception: If authentication or connection fails
        """
        if self._connected:
            return

        logger.debug("Connecting to Azure Sentinel at %s", self.dce_endpoint)
        credential = DefaultAzureCredential()
        self._client = LogsIngestionClient(endpoint=self.dce_endpoint, credential=credential)
        self._connected = True
        logger.info("Connected to Azure Sentinel")

    async def disconnect(self) -> None:
        """Disconnect from Azure Sentinel."""
        if not self._connected:
            return

        logger.debug("Disconnecting from Azure Sentinel")
        if self._client:
            self._client.close()
        self._client = None
        self._connected = False
        logger.info("Disconnected from Azure Sentinel")

    async def send_event(self, event: TelemetryEvent) -> None:
        """Send single event with exponential backoff retry.

        Args:
            event: Telemetry event to send

        Raises:
            RuntimeError: If not connected
            Exception: If send fails after retries
        """
        if not self._connected or self._client is None:
            raise RuntimeError("Connector not connected")

        event_dict = asdict(event)
        attempt = 0

        while attempt <= self.max_retries:
            try:
                self._client.upload(
                    rule_id=self.dcr_id, stream_name=self.stream_name, logs=[event_dict]
                )
                logger.debug("Event sent: %s", event.event_type)
                return
            except Exception as e:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error("Event send failed after %d attempts: %s", attempt, e)
                    raise

                delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                logger.debug("Retry %d/%d after %.1fs: %s", attempt, self.max_retries, delay, e)
                await asyncio.sleep(delay)

    async def send_batch(self, events: list[TelemetryEvent]) -> None:
        """Send batch of events with retry.

        Args:
            events: List of events

        Raises:
            RuntimeError: If not connected
            Exception: If send fails after retries
        """
        if not events:
            return

        if not self._connected or self._client is None:
            raise RuntimeError("Connector not connected")

        event_dicts = [asdict(event) for event in events]
        attempt = 0

        while attempt <= self.max_retries:
            try:
                # Cast to List[Any] to satisfy Azure SDK type requirements
                self._client.upload(
                    rule_id=self.dcr_id,
                    stream_name=self.stream_name,
                    logs=cast(list[Any], event_dicts),
                )
                logger.debug("Batch sent: %d events", len(events))
                return
            except Exception as e:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error("Batch send failed after %d attempts: %s", attempt, e)
                    raise

                delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                logger.debug("Retry %d/%d after %.1fs: %s", attempt, self.max_retries, delay, e)
                await asyncio.sleep(delay)

    async def health_check(self) -> bool:
        """Check connector health via test upload.

        Returns:
            True if healthy, False otherwise
        """
        if not self._connected or self._client is None:
            return False

        try:
            test_event = TelemetryEvent(
                timestamp="2024-01-01T00:00:00Z",
                event_type="health.check",
                source="exporter",
                severity="debug",
                data={},
                worker_id="health-check",
                run_id="health-check",
            )
            self._client.upload(
                rule_id=self.dcr_id,
                stream_name=self.stream_name,
                logs=[asdict(test_event)],
            )
            return True
        except Exception as e:
            logger.debug("Health check failed: %s", e)
            return False


class TelemetryExporter:
    """Telemetry exporter with DLQ support."""

    def __init__(self, connector: SentinelConnector, max_dlq_size: int = 1000):
        """Initialize exporter.

        Args:
            connector: Sentinel connector
            max_dlq_size: Max DLQ size
        """
        self.connector = connector
        self.max_dlq_size = max_dlq_size
        self._running = False
        self._pending_events: list[TelemetryEvent] = []
        self._dead_letter_queue: list[TelemetryEvent] = []

    @property
    def is_running(self) -> bool:
        """Check if exporter is running."""
        return self._running

    async def start(self) -> None:
        """Start exporter and connect to Sentinel."""
        if self._running:
            return

        logger.debug("Starting telemetry exporter")
        await self.connector.connect()
        self._running = True
        logger.info("Telemetry exporter started")

    async def stop(self) -> None:
        """Stop exporter, flush pending events, disconnect."""
        if not self._running:
            return

        logger.debug("Stopping telemetry exporter")

        if self._pending_events:
            try:
                await self.connector.send_batch(self._pending_events)
                self._pending_events.clear()
            except Exception as e:
                logger.error("Failed to flush pending events: %s", e)

        await self.connector.disconnect()
        self._running = False
        logger.info("Telemetry exporter stopped")

    async def emit_event(self, event: dict) -> None:
        """Emit event. Queue if not running, send immediately otherwise.

        Args:
            event: Event dict with required fields

        Raises:
            KeyError: If missing required fields
        """
        telemetry_event = TelemetryEvent(
            timestamp=event["timestamp"],
            event_type=event["event_type"],
            source=event["source"],
            severity=event["severity"],
            data=event["data"],
            worker_id=event["worker_id"],
            run_id=event["run_id"],
        )

        if not self._running:
            self._pending_events.append(telemetry_event)
            return

        try:
            await self.connector.send_event(telemetry_event)
        except Exception as e:
            logger.error("Failed to send event, adding to DLQ: %s", e)
            self._add_to_dlq(telemetry_event)

    def _add_to_dlq(self, event: TelemetryEvent) -> None:
        """Add event to DLQ, enforce max size."""
        self._dead_letter_queue.append(event)
        if len(self._dead_letter_queue) > self.max_dlq_size:
            self._dead_letter_queue = self._dead_letter_queue[-self.max_dlq_size :]

    def get_dlq_size(self) -> int:
        """Get DLQ size."""
        return len(self._dead_letter_queue)

    def get_dead_letter_queue(self) -> list[TelemetryEvent]:
        """Get DLQ contents."""
        return self._dead_letter_queue
