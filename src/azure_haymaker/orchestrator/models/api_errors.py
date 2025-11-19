"""
Error classes for monitoring API.

This module defines domain-specific exceptions used throughout the monitoring API
to provide clear error handling and response generation. All errors inherit from
APIError which includes HTTP status code and machine-readable error codes.
"""


class APIError(Exception):
    """Base class for API errors with HTTP status code and error code."""

    def __init__(self, message: str, status_code: int = 500, code: str = "INTERNAL_ERROR"):
        """
        Initialize API error.

        Args:
            message: Human-readable error message describing the issue
            status_code: HTTP status code for the error response (default 500)
            code: Machine-readable error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class RunNotFoundError(APIError):
    """
    Raised when a requested run does not exist in storage.

    This error is raised by the service layer when attempting to retrieve
    run details or resources for a non-existent run ID.
    """

    def __init__(self, run_id: str):
        """
        Initialize RunNotFoundError.

        Args:
            run_id: The run ID that was not found in storage
        """
        message = f"Run with ID '{run_id}' not found"
        super().__init__(message, status_code=404, code="RUN_NOT_FOUND")
        self.run_id = run_id


class InvalidParameterError(APIError):
    """
    Raised when a request parameter fails validation.

    This error is raised by the service layer when validating input parameters
    such as run_id format, pagination values, or filter parameters.
    """

    def __init__(self, parameter: str, message: str):
        """
        Initialize InvalidParameterError.

        Args:
            parameter: The name of the parameter that is invalid
            message: Description of why the parameter is invalid
        """
        full_message = f"Invalid parameter '{parameter}': {message}"
        super().__init__(full_message, status_code=400, code="INVALID_PARAMETER")
        self.parameter = parameter


__all__ = [
    "APIError",
    "RunNotFoundError",
    "InvalidParameterError",
]
