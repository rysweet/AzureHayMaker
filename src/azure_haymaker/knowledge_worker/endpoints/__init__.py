"""Endpoint management for Knowledge Worker Activity Framework.

Provides endpoint provisioning and management for worker activity
execution, including Windows 365 Cloud PCs and CLI containers.
"""

from azure_haymaker.knowledge_worker.endpoints.cloud_pc import Windows365CloudPCManager
from azure_haymaker.knowledge_worker.endpoints.cli_container import (
    M365CLIContainerManager,
)
from azure_haymaker.knowledge_worker.endpoints.manager import EndpointManager

__all__ = [
    "EndpointManager",
    "M365CLIContainerManager",
    "Windows365CloudPCManager",
]
