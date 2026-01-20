"""Core tracing initialization and tracer management.

Provides OpenTelemetry initialization with optional Azure Application Insights export.
Tracing is backward-compatible: if APPLICATIONINSIGHTS_CONNECTION_STRING is not set,
tracing still works locally with console output or no-op behavior.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer

logger = logging.getLogger(__name__)

# Module-level state for tracer provider
_tracer_provider: TracerProvider | None = None
_initialized: bool = False


def init_tracing(
    service_name: str,
    connection_string: str | None = None,
    enable_console_export: bool = False,
) -> TracerProvider:
    """Initialize OpenTelemetry tracing with optional Application Insights export.

    Sets up the global tracer provider with appropriate exporters based on
    configuration. If a connection string is provided (or found in environment),
    spans are exported to Azure Application Insights. Otherwise, tracing works
    locally with optional console output.

    Args:
        service_name: Name of the service for resource identification.
        connection_string: Optional Azure Application Insights connection string.
            If not provided, reads from APPLICATIONINSIGHTS_CONNECTION_STRING env var.
        enable_console_export: If True, also exports spans to console (for debugging).

    Returns:
        Configured TracerProvider instance.

    Example:
        >>> provider = init_tracing("haymaker-orchestrator")
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("my-operation"):
        ...     pass
    """
    global _tracer_provider, _initialized

    if _initialized:
        logger.debug("Tracing already initialized, returning existing provider")
        return _tracer_provider  # type: ignore[return-value]

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "azure-haymaker",
            "deployment.environment": os.environ.get("ENVIRONMENT", "development"),
        }
    )

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Determine connection string
    conn_string = connection_string or os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")

    # Add Azure Monitor exporter if connection string is available
    if conn_string:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            azure_exporter = AzureMonitorTraceExporter(connection_string=conn_string)
            _tracer_provider.add_span_processor(BatchSpanProcessor(azure_exporter))
            logger.info(
                f"Tracing initialized with Azure Application Insights export for {service_name}"
            )
        except ImportError:
            logger.warning(
                "azure-monitor-opentelemetry-exporter not installed, Azure export disabled"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Azure Monitor exporter: {e}")

    # Add console exporter if requested (useful for local debugging)
    if enable_console_export:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console span export enabled")

    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    _initialized = True

    logger.info(f"OpenTelemetry tracing initialized for service: {service_name}")
    return _tracer_provider


def get_tracer(name: str) -> Tracer:
    """Get a named tracer instance.

    Returns a tracer that can be used to create spans. If tracing has not been
    initialized, returns a no-op tracer from the default provider.

    Args:
        name: Name for the tracer, typically __name__ of the calling module.

    Returns:
        Tracer instance for creating spans.

    Example:
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("operation") as span:
        ...     span.set_attribute("key", "value")
    """
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Shutdown tracing and flush any pending spans.

    Should be called during application shutdown to ensure all spans
    are exported before the process exits.
    """
    global _tracer_provider, _initialized

    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        logger.info("Tracing shut down")

    _initialized = False
    _tracer_provider = None


def is_tracing_enabled() -> bool:
    """Check if tracing has been initialized.

    Returns:
        True if init_tracing has been called, False otherwise.
    """
    return _initialized


__all__ = [
    "get_tracer",
    "init_tracing",
    "is_tracing_enabled",
    "shutdown_tracing",
]
