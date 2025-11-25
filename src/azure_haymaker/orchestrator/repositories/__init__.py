"""
Repositories package for Azure HayMaker orchestrator.

Contains data access layer implementations for Azure resources,
providing clean abstractions over Azure SDK operations.

Repository Pattern Benefits:
- Testability: Repositories can be mocked for unit testing
- Separation of concerns: Business logic separated from data access
- Consistent error handling: All Azure errors wrapped in RepositoryError
- Dependency injection: Repositories can be injected into services
"""

from .base_repository import IRepository, RepositoryError
from .container_repository import ContainerAppRepository, ContainerAppResource
from .monitoring_repository import MonitoringRepository

__all__ = [
    # Base interface
    "IRepository",
    "RepositoryError",
    # Container operations
    "ContainerAppRepository",
    "ContainerAppResource",
    # Monitoring operations
    "MonitoringRepository",
]
