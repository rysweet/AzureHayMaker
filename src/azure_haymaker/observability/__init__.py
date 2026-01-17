"""Observability module for Azure HayMaker.

Provides metrics and monitoring capabilities for orchestrator execution.

Public API:
    get_metrics_client: Get singleton metrics client instance
"""

from azure_haymaker.observability.metrics import get_metrics_client

__all__ = ["get_metrics_client"]
