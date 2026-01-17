"""Application Insights custom metrics for Azure HayMaker.

This module provides metrics emission for operational visibility and monitoring.

Philosophy:
- Single responsibility: Metrics emission only
- Zero external dependencies beyond Azure Monitor SDK
- Graceful degradation if App Insights unavailable
- Minimal performance overhead

Public API:
    get_metrics_client: Get singleton metrics client instance
    MetricsClient: Main metrics client class
"""

import logging
import os
from typing import Optional

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.metrics import get_meter_provider

logger = logging.getLogger(__name__)


class MetricsClient:
    """Client for emitting custom metrics to Application Insights.

    Implements singleton pattern for efficient resource usage.
    Gracefully handles missing configuration by becoming a no-op client.
    """

    _instance: Optional["MetricsClient"] = None

    def __new__(cls) -> "MetricsClient":
        """Ensure single instance (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize metrics client with Azure Monitor configuration."""
        if self._initialized:
            return

        self._connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        self.is_enabled = bool(self._connection_string)

        if not self.is_enabled:
            logger.warning(
                "Application Insights connection string not set. Metrics will be disabled."
            )
            self._initialized = True
            return

        try:
            # Configure Azure Monitor with OpenTelemetry
            configure_azure_monitor(connection_string=self._connection_string)

            # Get meter provider and create meter
            meter_provider = get_meter_provider()
            self._meter = meter_provider.get_meter("azure_haymaker.observability")

            # Create metric instruments
            self._execution_duration_histogram = self._meter.create_histogram(
                name="haymaker.execution.duration_seconds",
                description="Total duration of orchestrator execution",
                unit="seconds",
            )

            self._scenarios_executed_counter = self._meter.create_counter(
                name="haymaker.scenarios.executed_count",
                description="Number of automation scenarios executed",
                unit="count",
            )

            self._cleanup_success_gauge = self._meter.create_up_down_counter(
                name="haymaker.cleanup.success",
                description="Cleanup success indicator (0=failure, 1=success)",
                unit="boolean",
            )

            self._resources_created_counter = self._meter.create_counter(
                name="haymaker.resources.created_count",
                description="Number of Azure resources created",
                unit="count",
            )

            logger.info("Metrics client initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize metrics client: {e}. Metrics disabled.")
            self.is_enabled = False

        self._initialized = True

    def record_execution_duration(self, run_id: str, duration_seconds: float, status: str) -> None:
        """Record orchestrator execution duration.

        Args:
            run_id: Unique identifier for the orchestration run
            duration_seconds: Total execution time in seconds
            status: Execution status ('success', 'failure', 'timeout')

        Raises:
            ValueError: If run_id is empty, duration is negative, or status is invalid
        """
        if not run_id:
            raise ValueError("run_id cannot be empty")

        if duration_seconds < 0:
            raise ValueError("duration cannot be negative")

        valid_statuses = {"success", "failure", "timeout"}
        if status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got '{status}' (invalid)")

        if not self.is_enabled:
            return

        try:
            self._execution_duration_histogram.record(
                duration_seconds, attributes={"run_id": run_id, "status": status}
            )
        except Exception as e:
            logger.warning(f"Failed to record execution duration metric: {e}")

    def increment_scenarios_executed(self, run_id: str, scenario_type: str, count: int = 1) -> None:
        """Increment scenarios executed counter.

        Args:
            run_id: Unique identifier for the orchestration run
            scenario_type: Type of scenario executed
            count: Number of scenarios to add (default: 1)

        Raises:
            ValueError: If run_id is empty
        """
        if not run_id:
            raise ValueError("run_id cannot be empty")

        if not self.is_enabled:
            return

        try:
            self._scenarios_executed_counter.add(
                count, attributes={"run_id": run_id, "scenario_type": scenario_type}
            )
        except Exception as e:
            logger.warning(f"Failed to increment scenarios executed metric: {e}")

    def record_cleanup_success(self, run_id: str, success: bool, cleanup_phase: str) -> None:
        """Record cleanup success indicator.

        Args:
            run_id: Unique identifier for the orchestration run
            success: True if cleanup succeeded, False otherwise
            cleanup_phase: Phase of cleanup ('resources', 'storage', 'network')

        Raises:
            ValueError: If run_id is empty
        """
        if not run_id:
            raise ValueError("run_id cannot be empty")

        if not self.is_enabled:
            return

        try:
            value = 1 if success else 0
            self._cleanup_success_gauge.set(
                value, attributes={"run_id": run_id, "cleanup_phase": cleanup_phase}
            )
        except Exception as e:
            logger.warning(f"Failed to record cleanup success metric: {e}")

    def increment_resources_created(self, run_id: str, resource_type: str, count: int = 1) -> None:
        """Increment resources created counter.

        Args:
            run_id: Unique identifier for the orchestration run
            resource_type: Type of Azure resource ('vm', 'storage', 'network', etc.)
            count: Number of resources to add (default: 1)

        Raises:
            ValueError: If run_id is empty or count is negative
        """
        if not run_id:
            raise ValueError("run_id cannot be empty")

        if count < 0:
            raise ValueError("count cannot be negative")

        if not self.is_enabled:
            return

        try:
            self._resources_created_counter.add(
                count, attributes={"run_id": run_id, "resource_type": resource_type}
            )
        except Exception as e:
            logger.warning(f"Failed to increment resources created metric: {e}")


# Singleton accessor
_metrics_client_instance: MetricsClient | None = None


def get_metrics_client() -> MetricsClient:
    """Get singleton metrics client instance.

    Returns:
        MetricsClient: Singleton instance of metrics client
    """
    global _metrics_client_instance
    if _metrics_client_instance is None:
        _metrics_client_instance = MetricsClient()
    return _metrics_client_instance


__all__ = ["get_metrics_client", "MetricsClient"]
