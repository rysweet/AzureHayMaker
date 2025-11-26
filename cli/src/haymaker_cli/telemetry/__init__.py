"""Telemetry module for Azure HayMaker CLI.

Provides telemetry collection, storage, and management capabilities.
"""

from .models import (
    AgentRecord,
    CollectionResult,
    ExecutionRecord,
    ResourceRecord,
)
from .config import TelemetryConfig

__all__ = [
    "AgentRecord",
    "CollectionResult",
    "ExecutionRecord",
    "ResourceRecord",
    "TelemetryConfig",
]
