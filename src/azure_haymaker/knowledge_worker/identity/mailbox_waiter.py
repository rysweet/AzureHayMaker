"""Mailbox provisioning waiter for Knowledge Worker deployments.

Handles the asynchronous delay between E5 license assignment and
Exchange Online mailbox provisioning.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MailboxStatus(str, Enum):
    """Status of mailbox provisioning check."""
    READY = "ready"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class MailboxWaitResult:
    """Result of waiting for mailbox provisioning."""
    status: MailboxStatus
    elapsed_seconds: float
    attempts: int
    error_message: str | None = None


class MailboxReadinessChecker:
    """Check if a user's mailbox is ready for REST API operations."""

    def __init__(self, graph_client: Any):
        self.graph_client = graph_client

    async def is_ready(self, user_id: str) -> tuple[bool, str | None]:
        """Check if mailbox is accessible."""
        try:
            await self.graph_client.users.by_user_id(user_id).mailbox_settings.get()
            return (True, None)
        except Exception as e:
            error_str = str(e)
            if "MailboxNotEnabledForRESTAPI" in error_str:
                return (False, "MailboxNotEnabledForRESTAPI")
            elif "ResourceNotFound" in error_str:
                return (False, "ResourceNotFound")
            elif "ErrorAccessDenied" in error_str:
                return (False, "ErrorAccessDenied")
            else:
                return (False, "UnknownError")


class MailboxProvisioningWaiter:
    """Wait for mailbox provisioning with exponential backoff."""

    INITIAL_DELAY = 10
    MAX_RETRY_DELAY = 120
    BACKOFF_MULTIPLIER = 1.5
    DEFAULT_TIMEOUT = 900

    def __init__(self, graph_client: Any):
        self.checker = MailboxReadinessChecker(graph_client)

    async def wait_for_mailbox(
        self,
        user_id: str,
        timeout_seconds: int | None = None,
    ) -> MailboxWaitResult:
        """Wait for mailbox to be ready."""
        timeout = timeout_seconds or self.DEFAULT_TIMEOUT
        start_time = asyncio.get_event_loop().time()
        attempts = 0
        delay = self.INITIAL_DELAY

        logger.info(f"Waiting for mailbox: {user_id} (timeout: {timeout}s)")

        await asyncio.sleep(self.INITIAL_DELAY)

        while True:
            attempts += 1
            elapsed = asyncio.get_event_loop().time() - start_time

            if elapsed >= timeout:
                logger.warning(f"Mailbox timeout after {elapsed:.1f}s: {user_id}")
                return MailboxWaitResult(
                    status=MailboxStatus.TIMEOUT,
                    elapsed_seconds=elapsed,
                    attempts=attempts,
                    error_message=f"Timeout after {timeout}s",
                )

            is_ready, error_code = await self.checker.is_ready(user_id)

            if is_ready:
                logger.info(f"Mailbox ready after {elapsed:.1f}s: {user_id}")
                return MailboxWaitResult(
                    status=MailboxStatus.READY,
                    elapsed_seconds=elapsed,
                    attempts=attempts,
                )

            if error_code == "ResourceNotFound":
                return MailboxWaitResult(
                    status=MailboxStatus.NOT_FOUND,
                    elapsed_seconds=elapsed,
                    attempts=attempts,
                    error_message="User not found",
                )

            await asyncio.sleep(delay)
            delay = min(delay * self.BACKOFF_MULTIPLIER, self.MAX_RETRY_DELAY)


__all__ = [
    "MailboxStatus",
    "MailboxWaitResult",
    "MailboxReadinessChecker",
    "MailboxProvisioningWaiter",
]
