"""Repository for tracking scenario execution failures and metrics.

Provides data access for recording execution outcomes and querying failure
metrics. Uses Azure Table Storage for persistence (ScenarioMetrics table).

Philosophy:
- Single responsibility: Only handles failure/metrics tracking
- Simple interface for recording and querying
- Supports time-windowed metrics queries

Public API (the "studs"):
    FailureTrackingRepository: Main repository class
    ScenarioExecutionRecord: Data model for execution records
    ScenarioMetrics: Aggregated metrics data model
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableClient


@dataclass
class ScenarioExecutionRecord:
    """Record of a single scenario execution.

    Attributes:
        scenario_name: Name of the executed scenario
        success: Whether execution succeeded
        duration_seconds: Execution duration in seconds
        error_type: Type of error if failed (e.g., 'TimeoutError')
        error_message: Error message if failed
        timestamp: When execution occurred
        run_id: Optional run identifier for correlation
    """

    scenario_name: str
    success: bool
    duration_seconds: float
    error_type: str | None = None
    error_message: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    run_id: str | None = None


@dataclass
class ScenarioMetrics:
    """Aggregated metrics for a scenario within a time window.

    Attributes:
        scenario_name: Name of the scenario
        total_executions: Total number of executions
        successful_executions: Number of successful executions
        failed_executions: Number of failed executions
        failure_rate: Ratio of failed to total (0.0 to 1.0)
        avg_duration_seconds: Average execution duration
        last_execution_at: Timestamp of most recent execution
        last_failure_at: Timestamp of most recent failure (if any)
        window_hours: Time window for these metrics
        error_types: Count of each error type encountered
    """

    scenario_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    failure_rate: float
    avg_duration_seconds: float
    last_execution_at: datetime | None
    last_failure_at: datetime | None
    window_hours: int
    error_types: dict[str, int] = field(default_factory=dict)


# Table Storage constants
METRICS_TABLE_NAME = "ScenarioMetrics"
PARTITION_KEY = "metrics"


class FailureTrackingRepository:
    """Repository for tracking and querying scenario execution metrics.

    Uses Azure Table Storage to persist execution records and provides
    methods for querying failure metrics within time windows.

    Example:
        >>> repo = FailureTrackingRepository(table_client)
        >>> await repo.record_execution("scenario1", success=True, duration=5.2)
        >>> metrics = await repo.get_metrics("scenario1", window_hours=24)
        >>> print(f"Failure rate: {metrics.failure_rate}")
    """

    def __init__(self, table_client: TableClient) -> None:
        """Initialize repository with Azure Table Storage client.

        Args:
            table_client: Azure Table Storage client for ScenarioMetrics table
        """
        self._client = table_client

    async def record_execution(
        self,
        scenario_name: str,
        success: bool,
        duration_seconds: float,
        error_type: str | None = None,
        error_message: str | None = None,
        run_id: str | None = None,
    ) -> ScenarioExecutionRecord:
        """Record a scenario execution outcome.

        Args:
            scenario_name: Name of the executed scenario
            success: Whether execution succeeded
            duration_seconds: Execution duration in seconds
            error_type: Type of error if failed
            error_message: Error message if failed
            run_id: Optional run identifier for correlation

        Returns:
            The recorded execution record
        """
        timestamp = datetime.now(UTC)
        record = ScenarioExecutionRecord(
            scenario_name=scenario_name,
            success=success,
            duration_seconds=duration_seconds,
            error_type=error_type,
            error_message=error_message,
            timestamp=timestamp,
            run_id=run_id,
        )

        # Create entity for Table Storage
        # Use timestamp as part of RowKey for time-range queries
        row_key = f"{scenario_name}_{timestamp.isoformat().replace(':', '-').replace('.', '-')}"

        entity = {
            "PartitionKey": PARTITION_KEY,
            "RowKey": row_key,
            "ScenarioName": scenario_name,
            "Success": success,
            "DurationSeconds": duration_seconds,
            "ErrorType": error_type or "",
            "ErrorMessage": (error_message or "")[:1000],  # Truncate long messages
            "Timestamp": timestamp.isoformat(),
            "RunId": run_id or "",
        }

        self._client.create_entity(entity=entity)
        return record

    async def get_metrics(
        self,
        scenario_name: str,
        window_hours: int = 24,
    ) -> ScenarioMetrics:
        """Get aggregated metrics for a scenario within a time window.

        Args:
            scenario_name: Name of the scenario to query
            window_hours: Number of hours to look back (default 24)

        Returns:
            Aggregated metrics for the scenario
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=window_hours)
        cutoff_str = cutoff_time.isoformat()

        # Query for records in the time window
        filter_str = (
            f"PartitionKey eq '{PARTITION_KEY}' and "
            f"ScenarioName eq '{scenario_name}' and "
            f"Timestamp ge '{cutoff_str}'"
        )

        records: list[dict[str, Any]] = []
        try:
            for entity in self._client.query_entities(query_filter=filter_str):
                records.append(dict(entity))
        except ResourceNotFoundError:
            pass  # Table or entities don't exist yet

        # Calculate metrics
        total = len(records)
        successful = sum(1 for r in records if r.get("Success", False))
        failed = total - successful

        durations = [r.get("DurationSeconds", 0) for r in records if r.get("DurationSeconds")]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Find last execution and failure times
        last_execution: datetime | None = None
        last_failure: datetime | None = None
        error_types: dict[str, int] = {}

        for r in records:
            ts_str = r.get("Timestamp", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if last_execution is None or ts > last_execution:
                    last_execution = ts
                if not r.get("Success", False):
                    if last_failure is None or ts > last_failure:
                        last_failure = ts
                    error_type = r.get("ErrorType", "Unknown")
                    if error_type:
                        error_types[error_type] = error_types.get(error_type, 0) + 1

        failure_rate = failed / total if total > 0 else 0.0

        return ScenarioMetrics(
            scenario_name=scenario_name,
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            failure_rate=failure_rate,
            avg_duration_seconds=avg_duration,
            last_execution_at=last_execution,
            last_failure_at=last_failure,
            window_hours=window_hours,
            error_types=error_types,
        )

    async def get_scenarios_exceeding_threshold(
        self,
        threshold: float = 0.5,
        window_hours: int = 24,
    ) -> list[ScenarioMetrics]:
        """Get all scenarios with failure rate exceeding threshold.

        Args:
            threshold: Failure rate threshold (0.0 to 1.0, default 0.5)
            window_hours: Time window for metrics (default 24 hours)

        Returns:
            List of ScenarioMetrics for scenarios exceeding threshold
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=window_hours)
        cutoff_str = cutoff_time.isoformat()

        # Query all records in time window
        filter_str = f"PartitionKey eq '{PARTITION_KEY}' and Timestamp ge '{cutoff_str}'"

        records: list[dict[str, Any]] = []
        try:
            for entity in self._client.query_entities(query_filter=filter_str):
                records.append(dict(entity))
        except ResourceNotFoundError:
            return []

        # Group by scenario
        scenarios: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            name = r.get("ScenarioName", "unknown")
            if name not in scenarios:
                scenarios[name] = []
            scenarios[name].append(r)

        # Calculate metrics per scenario and filter
        exceeding: list[ScenarioMetrics] = []
        for scenario_name, scenario_records in scenarios.items():
            total = len(scenario_records)
            if total == 0:
                continue

            failed = sum(1 for r in scenario_records if not r.get("Success", False))
            failure_rate = failed / total

            if failure_rate >= threshold:
                # Get full metrics for this scenario
                metrics = await self.get_metrics(scenario_name, window_hours)
                exceeding.append(metrics)

        # Sort by failure rate descending
        exceeding.sort(key=lambda m: m.failure_rate, reverse=True)
        return exceeding

    async def get_all_scenario_names(self) -> list[str]:
        """Get list of all unique scenario names in the metrics table.

        Returns:
            List of unique scenario names
        """
        filter_str = f"PartitionKey eq '{PARTITION_KEY}'"

        scenarios: set[str] = set()
        try:
            for entity in self._client.query_entities(
                query_filter=filter_str,
                select=["ScenarioName"],
            ):
                name = entity.get("ScenarioName")
                if name:
                    scenarios.add(name)
        except ResourceNotFoundError:
            pass

        return sorted(scenarios)

    async def delete_old_records(
        self,
        retention_days: int = 30,
    ) -> int:
        """Delete execution records older than retention period.

        Args:
            retention_days: Number of days to retain records (default 30)

        Returns:
            Number of records deleted
        """
        cutoff_time = datetime.now(UTC) - timedelta(days=retention_days)
        cutoff_str = cutoff_time.isoformat()

        # Query for old records
        filter_str = f"PartitionKey eq '{PARTITION_KEY}' and Timestamp lt '{cutoff_str}'"

        deleted_count = 0
        try:
            for entity in self._client.query_entities(query_filter=filter_str):
                self._client.delete_entity(
                    partition_key=entity["PartitionKey"],
                    row_key=entity["RowKey"],
                )
                deleted_count += 1
        except ResourceNotFoundError:
            pass

        return deleted_count


__all__ = [
    "FailureTrackingRepository",
    "ScenarioExecutionRecord",
    "ScenarioMetrics",
    "METRICS_TABLE_NAME",
]
