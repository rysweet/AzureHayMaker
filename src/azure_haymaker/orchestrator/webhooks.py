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

import ipaddress
import logging
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class WebhookValidationError(Exception):
    """Raised when webhook URL validation fails."""

    pass

# Default timeout for webhook requests (5 seconds)
WEBHOOK_TIMEOUT = 5.0

# Private IP ranges that may indicate SSRF attempts
_PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private IP address.

    Args:
        hostname: The hostname or IP address to check.

    Returns:
        True if the hostname is or resolves to a private IP, False otherwise.
    """
    try:
        ip = ipaddress.ip_address(hostname)
        return any(ip in network for network in _PRIVATE_IP_RANGES)
    except ValueError:
        # Not a valid IP address - it's a hostname, allow it
        # (DNS resolution would require network access which we avoid here)
        return False


def validate_webhook_url(url: str, block_private_ips: bool = True) -> str:
    """Validate webhook URL for security (SSRF mitigation).

    This function validates that the webhook URL uses an allowed scheme
    and optionally blocks URLs pointing to private IP ranges.

    Security Note:
        This validation provides defense-in-depth against SSRF attacks.
        For production use, consider additional measures such as:
        - Using an allowlist of permitted webhook domains
        - Running webhook requests through a proxy
        - Network-level controls to prevent internal access

    Args:
        url: The webhook URL to validate.
        block_private_ips: If True, reject URLs with private IP addresses.
            Defaults to True for security.

    Returns:
        The validated URL (unchanged).

    Raises:
        WebhookValidationError: If the URL fails validation.

    Example:
        >>> validate_webhook_url("https://example.com/webhook")
        'https://example.com/webhook'
        >>> validate_webhook_url("http://192.168.1.1/hook")  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        WebhookValidationError: ...
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise WebhookValidationError(f"Invalid URL format: {e}") from e

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise WebhookValidationError(
            f"Invalid URL scheme '{parsed.scheme}': only http and https are allowed"
        )

    # Check hostname exists
    if not parsed.hostname:
        raise WebhookValidationError("URL must include a hostname")

    # Check for private IPs if enabled
    if block_private_ips and _is_private_ip(parsed.hostname):
        raise WebhookValidationError(
            f"Private IP addresses are not allowed: {parsed.hostname}"
        )

    return url


def get_webhook_url() -> str | None:
    """Get webhook URL from environment variable."""
    return os.getenv("HAYMAKER_WEBHOOK_URL")


async def send_webhook(
    url: str | None,
    event_type: str,
    data: dict[str, Any],
    validate_url: bool = True,
) -> bool:
    """Fire-and-forget webhook notification.

    Sends a POST request to the configured webhook URL with event data.
    This is designed to be non-blocking - failures are logged but do not
    raise exceptions or block the calling code.

    Args:
        url: Webhook URL to POST to. If None or empty, returns True immediately.
        event_type: Type of event (e.g., "execution.started", "execution.completed")
        data: Event-specific data to include in the payload
        validate_url: If True, validate URL for SSRF protection. Defaults to True.

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

    # Validate URL for security (SSRF mitigation)
    if validate_url:
        try:
            validate_webhook_url(url)
        except WebhookValidationError as e:
            logger.error(f"Webhook URL validation failed ({type(e).__name__}): {e}")
            return False

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
        logger.error(f"Webhook timeout ({type(httpx.TimeoutException).__name__}) for {event_type}")
        return False
    except Exception as e:
        logger.error(f"Webhook error ({type(e).__name__}): {e}")
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
