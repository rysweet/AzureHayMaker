"""Exceptions for workflow bricks module.

Provides specific exception types for brick validation, execution,
and timeout errors.
"""


class BrickError(Exception):
    """Base exception for all brick-related errors."""

    pass


class BrickValidationError(BrickError):
    """Raised when brick validation fails.

    This exception indicates that preconditions for brick execution
    were not met, such as missing required parameters or invalid context.
    """

    pass


class BrickExecutionError(BrickError):
    """Raised when brick execution fails.

    This exception indicates that the brick's main action failed,
    such as an API call failure or unexpected response.
    """

    pass


class BrickTimeoutError(BrickError):
    """Raised when brick execution times out.

    This exception indicates that a brick operation took longer
    than the allowed timeout period.
    """

    pass


__all__ = [
    "BrickError",
    "BrickValidationError",
    "BrickExecutionError",
    "BrickTimeoutError",
]
