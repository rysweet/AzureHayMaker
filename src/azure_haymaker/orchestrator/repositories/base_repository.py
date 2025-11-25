"""Base repository interface for Azure resource operations.

This module defines the abstract interface that all resource repositories
must implement. The repository pattern provides a clean abstraction over
Azure SDK calls, enabling:
- Testability through dependency injection
- Consistent error handling across resources
- Clear separation between business logic and data access
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Abstract base interface for Azure resource repositories.

    All repository implementations must inherit from this interface
    and implement the core CRUD operations. The generic type T represents
    the resource type being managed (e.g., ContainerApp, StorageAccount).

    This interface follows the repository pattern to abstract Azure SDK
    operations behind a clean, testable interface.
    """

    @abstractmethod
    async def get(self, resource_id: str) -> T | None:
        """Retrieve a resource by its identifier.

        Args:
            resource_id: Unique identifier for the resource (name or full ID)

        Returns:
            The resource if found, None otherwise

        Raises:
            RepositoryError: If the operation fails (other than not found)
        """
        ...

    @abstractmethod
    async def create(self, resource: T) -> T:
        """Create a new resource.

        Args:
            resource: Resource configuration to create

        Returns:
            The created resource with updated fields (e.g., generated ID)

        Raises:
            RepositoryError: If creation fails
            ValueError: If resource configuration is invalid
        """
        ...

    @abstractmethod
    async def delete(self, resource_id: str) -> bool:
        """Delete a resource by its identifier.

        Args:
            resource_id: Unique identifier for the resource to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            RepositoryError: If deletion fails (other than not found)
        """
        ...

    @abstractmethod
    async def exists(self, resource_id: str) -> bool:
        """Check if a resource exists.

        Args:
            resource_id: Unique identifier for the resource

        Returns:
            True if the resource exists, False otherwise

        Raises:
            RepositoryError: If the check fails
        """
        ...


class RepositoryError(Exception):
    """Base exception for repository operations.

    Raised when Azure SDK operations fail in a way that cannot be
    handled by returning None or False.
    """

    def __init__(self, message: str, operation: str | None = None, resource_id: str | None = None):
        """Initialize RepositoryError with context.

        Args:
            message: Error description
            operation: Operation that failed (get, create, delete, etc.)
            resource_id: Resource identifier involved in the operation
        """
        self.operation = operation
        self.resource_id = resource_id
        super().__init__(message)


__all__ = ["IRepository", "RepositoryError"]
