"""Fire-and-forget webhook notifications for execution events.

This module provides simple, non-blocking webhook notifications for
orchestration lifecycle events. Failures are logged but do not block
the main execution flow.

Configuration:
    HAYMAKER_WEBHOOK_URL: Optional URL to receive webhook notifications.
    If not set, webhooks are silently skipped.

Event Types:
    - execution.started: Fired when an orchestration run begins
    - execution.completed: Fired when an orchestration run succeeds
    - execution.failed: Fired when an orchestration run fails
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default timeout for webhook requests (5 seconds)
WEBHOOK_TIMEOUT = 5.0


def get_webhook_url() -> str | None:
    """Get webhook URL from environment variable."""
    return os.getenv("HAYMAKER_WEBHOOK_URL")


async def send_webhook(url: str | None, event_type: str, data: dict[str, Any]) -> bool:
    """Fire-and-forget webhook notification.

    Sends a POST request to the configured webhook URL with event data.
    This is designed to be non-blocking - failures are logged but do not
    raise exceptions or block the calling code.

    Args:
        url: Webhook URL to POST to. If None or empty, returns True immediately.
        event_type: Type of event (e.g., "execution.started", "execution.completed")
        data: Event-specific data to include in the payload

    Returns:
        True if successful or no webhook configured, False if the request failed.

    Example:
        >>> await send_webhook(
        ...     url="https://example.com/webhook",
        ...     event_type="execution.started",
        ...     data={"run_id": "abc-123", "scenarios": ["scenario1", "scenario2"]}
        ... )
        True
    """
    if not url:
        return True  # No webhook configured - silently skip

    payload = {
        "event": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        **data,
    }

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            if response.is_success:
                logger.info(f"Webhook sent: {event_type}")
                return True
            logger.warning(f"Webhook failed: {response.status_code}")
            return False
    except httpx.TimeoutException:
        logger.error(f"Webhook timeout for {event_type}")
        return False
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return False


async def notify_execution_started(
    run_id: str,
    scenarios: list[str],
    started_at: str | None = None,
) -> bool:
    """Send execution.started webhook notification.

    Args:
        run_id: Unique identifier for the execution run
        scenarios: List of scenario names being executed
        started_at: ISO format timestamp (defaults to current time)

    Returns:
        True if successful or no webhook configured, False on failure.
    """
    url = get_webhook_url()
    return await send_webhook(
        url=url,
        event_type="execution.started",
        data={
            "run_id": run_id,
            "scenarios": scenarios,
            "started_at": started_at or datetime.now(UTC).isoformat(),
        },
    )


async def notify_execution_completed(
    run_id: str,
    duration_hours: float,
    scenarios_count: int,
) -> bool:
    """Send execution.completed webhook notification.

    Args:
        run_id: Unique identifier for the execution run
        duration_hours: Total execution duration in hours
        scenarios_count: Number of scenarios that were executed

    Returns:
        True if successful or no webhook configured, False on failure.
    """
    url = get_webhook_url()
    return await send_webhook(
        url=url,
        event_type="execution.completed",
        data={
            "run_id": run_id,
            "duration_hours": duration_hours,
            "scenarios_count": scenarios_count,
        },
    )


async def notify_execution_failed(
    run_id: str,
    error: str,
    failed_at: str | None = None,
) -> bool:
    """Send execution.failed webhook notification.

    Args:
        run_id: Unique identifier for the execution run
        error: Error message or description
        failed_at: ISO format timestamp (defaults to current time)

    Returns:
        True if successful or no webhook configured, False on failure.
    """
    url = get_webhook_url()
    return await send_webhook(
        url=url,
        event_type="execution.failed",
        data={
            "run_id": run_id,
            "error": error,
            "failed_at": failed_at or datetime.now(UTC).isoformat(),
        },
    )
