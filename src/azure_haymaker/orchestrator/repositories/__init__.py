"""
Repositories package for Azure HayMaker orchestrator.

Contains data access layer implementations for Azure resources,
providing clean abstractions over Azure SDK operations.

IRepository Pattern (ContainerAppRepository):
- Testability: Repositories can be mocked for unit testing
- Separation of concerns: Business logic separated from data access
- Consistent error handling: Azure errors wrapped in RepositoryError
- Dependency injection: Repositories can be injected into services

Note: MonitoringRepository is a legacy data access class that does not
implement IRepository. It will be migrated in a future refactoring.
"""

from .base_repository import IRepository, RepositoryError
from .container_repository import ContainerAppRepository, ContainerAppResource
from .monitoring_repository import MonitoringRepository

__all__ = [
    # Base interface (for IRepository implementations)
    "IRepository",
    "RepositoryError",
    # Container operations (implements IRepository)
    "ContainerAppRepository",
    "ContainerAppResource",
    # Monitoring operations (legacy, does not implement IRepository)
    "MonitoringRepository",
]
