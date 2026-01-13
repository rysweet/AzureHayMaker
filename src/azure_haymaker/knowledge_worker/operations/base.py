"""Base class for M365 operations.

Provides common functionality for all M365 operations including
recipient validation, rate limiting, and logging.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Protocol

from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity
from azure_haymaker.knowledge_worker.operations.validators import (
    CommunicationValidator,
)

logger = logging.getLogger(__name__)


class M365Client(Protocol):
    """Protocol for M365 client implementations.

    Defines the interface that M365 clients must implement
    to be used with M365 operations.
    """

    @property
    def graph(self) -> Any:
        """Access to Microsoft Graph client."""
        ...


class M365OperationBase(ABC):
    """Abstract base class for M365 operations.

    All M365 operations must:
    1. Validate recipients are internal-only
    2. Rate limit API calls
    3. Log operations for telemetry
    4. Handle Graph API errors gracefully

    This base class provides common functionality for:
    - Recipient validation via CommunicationValidator
    - Operation counting and rate limiting
    - Logging with worker context

    Attributes:
        worker: Identity of the worker performing operations
        client: M365 client for Graph API calls
        validator: Communication validator for recipient checks
        _operation_count: Running count of operations performed
        _last_rate_limit_time: Timestamp of last rate limit pause
    """

    # Rate limiting configuration
    RATE_LIMIT_OPERATIONS = 100  # Pause after this many operations
    RATE_LIMIT_PAUSE_SECONDS = 1.0  # Seconds to pause

    def __init__(
        self,
        worker_identity: WorkerIdentity,
        m365_client: M365Client,
        validator: CommunicationValidator,
    ):
        """Initialize M365OperationBase.

        Args:
            worker_identity: Identity of the worker performing operations
            m365_client: M365 client for Graph API calls
            validator: Communication validator for recipient checks
        """
        self.worker = worker_identity
        self.client = m365_client
        self.validator = validator
        self._operation_count = 0
        self._last_rate_limit_time: datetime | None = None

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the M365 operation.

        Subclasses must implement this method to perform
        specific M365 operations.

        Args:
            **kwargs: Operation-specific parameters

        Returns:
            Operation-specific result
        """
        ...

    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient is in allowed list.

        Logs a warning if the recipient is external.

        Args:
            recipient: Email address or UPN to validate

        Returns:
            True if recipient is internal, False otherwise
        """
        is_valid = self.validator.is_internal(recipient)
        if not is_valid:
            logger.warning(
                f"Blocked external recipient: {recipient} (worker: {self.worker.worker_id})"
            )
        return is_valid

    def validate_recipients(self, recipients: list[str]) -> list[str]:
        """Filter recipients to only allowed internal addresses.

        Returns only the recipients that pass validation.
        Logs warnings for any filtered recipients.

        Args:
            recipients: List of email addresses or UPNs

        Returns:
            List of valid internal recipients
        """
        valid = self.validator.filter_recipients(recipients)

        if len(valid) < len(recipients):
            blocked_count = len(recipients) - len(valid)
            logger.warning(
                f"Filtered {blocked_count} external recipients (worker: {self.worker.worker_id})"
            )

        return valid

    async def _rate_limit(self) -> None:
        """Apply rate limiting between operations.

        Pauses execution periodically to avoid hitting
        Graph API rate limits.
        """
        self._operation_count += 1

        if self._operation_count % self.RATE_LIMIT_OPERATIONS == 0:
            logger.debug(
                f"Rate limiting: pausing for {self.RATE_LIMIT_PAUSE_SECONDS}s "
                f"after {self._operation_count} operations "
                f"(worker: {self.worker.worker_id})"
            )
            self._last_rate_limit_time = datetime.utcnow()
            await asyncio.sleep(self.RATE_LIMIT_PAUSE_SECONDS)

    def _log_operation(
        self,
        operation_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an operation with worker context.

        Args:
            operation_name: Name of the operation being performed
            details: Optional additional details to log
        """
        log_data = {
            "worker_id": self.worker.worker_id,
            "operation": operation_name,
            "operation_count": self._operation_count,
        }
        if details:
            log_data.update(details)

        logger.info(f"M365 operation: {log_data}")

    def _log_error(
        self,
        operation_name: str,
        error: Exception,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an operation error with worker context.

        Args:
            operation_name: Name of the operation that failed
            error: The exception that was raised
            details: Optional additional details to log
        """
        log_data = {
            "worker_id": self.worker.worker_id,
            "operation": operation_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        if details:
            log_data.update(details)

        logger.error(f"M365 operation failed: {log_data}")

    def get_operation_stats(self) -> dict[str, Any]:
        """Get statistics about operations performed.

        Returns:
            Dictionary with operation count and rate limit info
        """
        return {
            "worker_id": self.worker.worker_id,
            "operation_count": self._operation_count,
            "last_rate_limit": (
                self._last_rate_limit_time.isoformat() if self._last_rate_limit_time else None
            ),
        }

    async def __aenter__(self) -> "M365OperationBase":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        # Log any errors that occurred
        if exc_val is not None and isinstance(exc_val, Exception):
            self._log_error("context_exit", exc_val)
