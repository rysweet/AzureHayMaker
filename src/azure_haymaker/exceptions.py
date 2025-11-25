"""Custom exceptions for Azure HayMaker.

This module provides a hierarchy of specific exception classes to replace bare
`except Exception` clauses, improving debuggability and error handling precision.

Exception Hierarchy:
    HayMakerError (base)
    ├── ResourceError
    │   ├── ResourceNotFoundError
    │   ├── ResourceCreationError
    │   └── ResourceDeletionError
    ├── AuthenticationError
    │   ├── CredentialError
    │   └── TokenError
    ├── ConfigurationError
    ├── ValidationError
    ├── ServicePrincipalError
    │   ├── SPCreationError
    │   └── SPDeletionError
    ├── ContainerError
    │   ├── ContainerDeploymentError
    │   └── ContainerMonitorError
    ├── GraphAPIError
    ├── KeyVaultError
    └── OrchestrationError
"""

from typing import Any


class HayMakerError(Exception):
    """Base exception for all Azure HayMaker errors.

    All custom exceptions should inherit from this class to enable
    catching all HayMaker-specific errors with a single except clause.

    Attributes:
        message: Human-readable error description
        details: Optional dictionary with additional error context
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# =============================================================================
# Resource Errors
# =============================================================================


class ResourceError(HayMakerError):
    """Base exception for Azure resource operations.

    Raised when operations on Azure resources fail.
    """

    def __init__(
        self,
        message: str,
        resource_id: str | None = None,
        resource_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if resource_id:
            details["resource_id"] = resource_id
        if resource_type:
            details["resource_type"] = resource_type
        super().__init__(message, details)
        self.resource_id = resource_id
        self.resource_type = resource_type


class ResourceNotFoundError(ResourceError):
    """Raised when an expected Azure resource does not exist.

    This is distinct from azure.core.exceptions.ResourceNotFoundError
    to provide HayMaker-specific context.
    """

    pass


class ResourceCreationError(ResourceError):
    """Raised when creating an Azure resource fails."""

    pass


class ResourceDeletionError(ResourceError):
    """Raised when deleting an Azure resource fails."""

    pass


# =============================================================================
# Authentication Errors
# =============================================================================


class AuthenticationError(HayMakerError):
    """Base exception for authentication and authorization failures."""

    pass


class CredentialError(AuthenticationError):
    """Raised when Azure credentials are invalid or unavailable."""

    pass


class TokenError(AuthenticationError):
    """Raised when token acquisition or refresh fails."""

    pass


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(HayMakerError):
    """Raised when configuration is invalid or missing.

    Examples:
        - Missing required environment variables
        - Invalid configuration file format
        - Incompatible configuration values
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details)
        self.config_key = config_key


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(HayMakerError):
    """Raised when input validation fails.

    Examples:
        - Invalid scenario parameters
        - Failed environment validation checks
        - Schema validation failures
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(message, details)
        self.field = field
        self.value = value


# =============================================================================
# Service Principal Errors
# =============================================================================


class ServicePrincipalError(HayMakerError):
    """Base exception for service principal operations.

    Raised when operations on Entra ID service principals fail.
    """

    def __init__(
        self,
        message: str,
        sp_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if sp_name:
            details["sp_name"] = sp_name
        super().__init__(message, details)
        self.sp_name = sp_name


class SPCreationError(ServicePrincipalError):
    """Raised when creating a service principal fails."""

    pass


class SPDeletionError(ServicePrincipalError):
    """Raised when deleting a service principal fails."""

    pass


# =============================================================================
# Container Errors
# =============================================================================


class ContainerError(HayMakerError):
    """Base exception for Container App operations."""

    def __init__(
        self,
        message: str,
        container_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if container_name:
            details["container_name"] = container_name
        super().__init__(message, details)
        self.container_name = container_name


class ContainerDeploymentError(ContainerError):
    """Raised when deploying a Container App fails."""

    pass


class ContainerMonitorError(ContainerError):
    """Raised when monitoring a Container App fails."""

    pass


# =============================================================================
# External Service Errors
# =============================================================================


class GraphAPIError(HayMakerError):
    """Raised when Microsoft Graph API calls fail.

    Wraps errors from the Microsoft Graph SDK with additional context.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if status_code:
            details["status_code"] = status_code
        if error_code:
            details["error_code"] = error_code
        super().__init__(message, details)
        self.status_code = status_code
        self.error_code = error_code


class KeyVaultError(HayMakerError):
    """Raised when Azure Key Vault operations fail.

    Examples:
        - Secret retrieval failures
        - Secret storage failures
        - Access policy issues
    """

    def __init__(
        self,
        message: str,
        secret_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if secret_name:
            details["secret_name"] = secret_name
        super().__init__(message, details)
        self.secret_name = secret_name


# =============================================================================
# Orchestration Errors
# =============================================================================


class OrchestrationError(HayMakerError):
    """Raised when orchestration workflow execution fails.

    Examples:
        - Activity function failures
        - Workflow state corruption
        - Timer trigger failures
    """

    def __init__(
        self,
        message: str,
        run_id: str | None = None,
        phase: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if run_id:
            details["run_id"] = run_id
        if phase:
            details["phase"] = phase
        super().__init__(message, details)
        self.run_id = run_id
        self.phase = phase


# =============================================================================
# Cleanup Errors
# =============================================================================


class CleanupError(HayMakerError):
    """Raised when cleanup operations fail.

    Examples:
        - Resource deletion failures during cleanup
        - Cleanup verification failures
        - Forced cleanup failures
    """

    def __init__(
        self,
        message: str,
        run_id: str | None = None,
        remaining_count: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if run_id:
            details["run_id"] = run_id
        if remaining_count is not None:
            details["remaining_count"] = remaining_count
        super().__init__(message, details)
        self.run_id = run_id
        self.remaining_count = remaining_count


__all__ = [
    "HayMakerError",
    # Resource errors
    "ResourceError",
    "ResourceNotFoundError",
    "ResourceCreationError",
    "ResourceDeletionError",
    # Authentication errors
    "AuthenticationError",
    "CredentialError",
    "TokenError",
    # Configuration errors
    "ConfigurationError",
    # Validation errors
    "ValidationError",
    # Service principal errors
    "ServicePrincipalError",
    "SPCreationError",
    "SPDeletionError",
    # Container errors
    "ContainerError",
    "ContainerDeploymentError",
    "ContainerMonitorError",
    # External service errors
    "GraphAPIError",
    "KeyVaultError",
    # Orchestration errors
    "OrchestrationError",
    "CleanupError",
]
