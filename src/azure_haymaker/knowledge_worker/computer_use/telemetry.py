"""Telemetry Collection Module for Computer Use Knowledge Worker Agents.

Provides operation logging, metrics aggregation, and export capabilities
for Computer Use agent telemetry.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from azure_haymaker.knowledge_worker.computer_use.security_utils import (
    sanitize_dict,
    sanitize_error,
)
from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

logger = logging.getLogger(__name__)


@dataclass
class OperationLog:
    """Log entry for a single operation.

    Attributes:
        operation: Operation name (e.g., "email_workflow")
        status: Operation status ("success" or "error")
        duration_ms: Duration in milliseconds
        timestamp: When operation occurred
        worker_id: Worker that performed operation
        metadata: Additional operation-specific data
    """

    operation: str
    status: str
    duration_ms: int
    timestamp: datetime
    worker_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation": self.operation,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "worker_id": self.worker_id,
            "metadata": self.metadata,
        }


@dataclass
class TelemetryMetrics:
    """Aggregated telemetry metrics.

    Attributes:
        total_operations: Total number of operations
        successful_operations: Number of successful operations
        failed_operations: Number of failed operations
        average_duration_ms: Average operation duration
        success_rate: Ratio of successful to total operations
    """

    total_operations: int
    successful_operations: int
    failed_operations: int
    average_duration_ms: float
    success_rate: float


class ComputerUseTelemetryCollector:
    """Collects and manages telemetry for Computer Use agents.

    Logs all workflow operations, aggregates metrics, and provides
    export capabilities to Azure Storage or local files.

    Example:
        >>> identity = WorkerIdentity(worker_id="kw-test-001", ...)
        >>> collector = ComputerUseTelemetryCollector(worker_identity=identity)
        >>> collector.log_operation(
        ...     operation="email_workflow",
        ...     status="success",
        ...     duration_ms=1500,
        ...     metadata={"to": "recipient@tenant.com"}
        ... )
        >>> logs = collector.get_logs()
        >>> metrics = collector.get_metrics_summary()

    Attributes:
        worker_identity: Worker identity for this collector
        logs: List of operation logs
    """

    def __init__(
        self,
        worker_identity: WorkerIdentity,
        log_dir: Path | None = None,
    ):
        """Initialize telemetry collector.

        Args:
            worker_identity: Worker identity
            log_dir: Optional directory for log files
        """
        self.worker_identity = worker_identity
        self.log_dir = log_dir or Path.home() / ".azure_haymaker" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logs: list[OperationLog] = []

        logger.info(
            f"ComputerUseTelemetryCollector initialized for {worker_identity.worker_id}"
        )

    def log_operation(
        self,
        operation: str,
        status: str,
        duration_ms: int,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Log an operation execution.

        Args:
            operation: Operation name
            status: Operation status ("success" or "error")
            duration_ms: Operation duration in milliseconds
            metadata: Optional additional metadata
            timestamp: Optional timestamp (defaults to now)

        Raises:
            ValueError: If operation name is empty
        """
        if not operation or not operation.strip():
            raise ValueError("Operation name cannot be empty")

        # Sanitize metadata to remove sensitive data
        safe_metadata = sanitize_dict(metadata) if metadata else {}

        log_entry = OperationLog(
            operation=operation,
            status=status,
            duration_ms=duration_ms,
            timestamp=timestamp or datetime.now(UTC),
            worker_id=self.worker_identity.worker_id,
            metadata=safe_metadata,  # Use sanitized metadata
        )

        self.logs.append(log_entry)

        logger.debug(
            f"Logged operation: {operation} ({status}, {duration_ms}ms)"
        )

        # Persist to disk
        self._persist_log(log_entry)

    def get_logs(
        self,
        since: datetime | None = None,
        status: str | None = None,
    ) -> list[OperationLog]:
        """Retrieve operation logs with optional filters.

        Args:
            since: Optional timestamp to filter logs after
            status: Optional status to filter by ("success" or "error")

        Returns:
            List of matching operation logs
        """
        filtered_logs = self.logs

        # Filter by timestamp
        if since:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= since]

        # Filter by status
        if status:
            filtered_logs = [log for log in filtered_logs if log.status == status]

        return filtered_logs

    def get_metrics_summary(self) -> TelemetryMetrics:
        """Calculate aggregated metrics from logs.

        Returns:
            TelemetryMetrics with aggregated statistics
        """
        if not self.logs:
            return TelemetryMetrics(
                total_operations=0,
                successful_operations=0,
                failed_operations=0,
                average_duration_ms=0.0,
                success_rate=0.0,
            )

        total = len(self.logs)
        successful = sum(1 for log in self.logs if log.status == "success")
        failed = sum(1 for log in self.logs if log.status == "error")
        avg_duration = sum(log.duration_ms for log in self.logs) / total
        success_rate = successful / total if total > 0 else 0.0

        return TelemetryMetrics(
            total_operations=total,
            successful_operations=successful,
            failed_operations=failed,
            average_duration_ms=avg_duration,
            success_rate=success_rate,
        )

    def get_metrics_by_operation(self) -> dict[str, dict[str, Any]]:
        """Calculate metrics grouped by operation type.

        Returns:
            Dict mapping operation name to metrics:
                - count: Number of operations
                - success_rate: Success rate for this operation
                - avg_duration_ms: Average duration
        """
        metrics_by_op: dict[str, dict[str, Any]] = {}

        for log in self.logs:
            op_name = log.operation

            if op_name not in metrics_by_op:
                metrics_by_op[op_name] = {
                    "count": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_duration_ms": 0,
                }

            metrics_by_op[op_name]["count"] += 1
            metrics_by_op[op_name]["total_duration_ms"] += log.duration_ms

            if log.status == "success":
                metrics_by_op[op_name]["successes"] += 1
            else:
                metrics_by_op[op_name]["failures"] += 1

        # Calculate derived metrics
        for _op_name, metrics in metrics_by_op.items():
            count = metrics["count"]
            metrics["success_rate"] = metrics["successes"] / count if count > 0 else 0.0
            metrics["avg_duration_ms"] = metrics["total_duration_ms"] / count if count > 0 else 0.0

            # Remove intermediate values
            del metrics["total_duration_ms"]

        return metrics_by_op

    async def export_logs(
        self,
        destination: str,
    ) -> dict[str, Any]:
        """Export logs to storage.

        Supports Azure Storage Blob URLs (azure://) and local file paths.

        Args:
            destination: Destination URL or path
                - Azure: "azure://storageaccount/container/logs.json"
                - Local: "/path/to/logs.json"

        Returns:
            Dict with export result:
                - success: Whether export succeeded
                - log_count: Number of logs exported
                - destination: Export destination

        Raises:
            Exception: If export fails
        """
        logger.info(f"Exporting {len(self.logs)} logs to {destination}")

        # Convert logs to JSON
        logs_data = [log.to_dict() for log in self.logs]
        logs_json = json.dumps(logs_data, indent=2)

        try:
            if destination.startswith("azure://"):
                # Azure Storage export
                await self._export_to_azure_storage(destination, logs_json)
            else:
                # Local file export
                Path(destination).write_text(logs_json)

            logger.info(f"Successfully exported {len(self.logs)} logs")

            return {
                "success": True,
                "log_count": len(self.logs),
                "destination": destination,
            }

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.error(f"Failed to export logs: {sanitized_error}")
            raise

    async def _export_to_azure_storage(self, url: str, content: str) -> None:
        """Export logs to Azure Storage Blob.

        Args:
            url: Azure Storage URL (azure://account/container/blob)
            content: JSON content to upload

        Raises:
            Exception: If upload fails
        """
        # Import Azure Storage SDK at runtime to avoid requiring it for local exports
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as e:
            raise ImportError(
                "azure-storage-blob is required for Azure Storage exports. "
                "Install with: pip install azure-storage-blob"
            ) from e

        # Parse Azure URL
        # Format: azure://storageaccount/container/blobname
        parts = url.replace("azure://", "").split("/", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid Azure Storage URL: {url}")

        storage_account, container, blob_name = parts

        # Create blob client using account name (requires environment credentials)
        blob_url = f"https://{storage_account}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(account_url=blob_url)

        # Upload blob
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )
        blob_client.upload_blob(content, overwrite=True)

        logger.info(f"Uploaded logs to Azure Storage: {container}/{blob_name}")

    def _persist_log(self, log: OperationLog) -> None:
        """Persist log entry to disk.

        Args:
            log: Log entry to persist
        """
        try:
            # Create log file path
            log_file = (
                self.log_dir
                / f"{self.worker_identity.worker_id}_{datetime.now(UTC).strftime('%Y%m%d')}.jsonl"
            )

            # Append log entry as JSON line
            with log_file.open("a") as f:
                f.write(json.dumps(log.to_dict()) + "\n")

        except Exception as e:
            sanitized_error = sanitize_error(str(e))
            logger.warning(f"Failed to persist log to disk: {sanitized_error}")
