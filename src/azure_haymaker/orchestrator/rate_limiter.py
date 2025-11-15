"""Rate limiter for on-demand execution requests using token bucket algorithm.

This module implements rate limiting using Azure Table Storage for persistence.
Supports multiple limit types: global, per-scenario, and per-user.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableClient, UpdateMode
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    limit: int = Field(..., description="Max requests per window", gt=0)
    window_seconds: int = Field(..., description="Time window in seconds", gt=0)


class RateLimitResult(BaseModel):
    """Result of rate limit check."""

    allowed: bool = Field(..., description="Whether request is allowed")
    retry_after: int = Field(..., description="Seconds to wait before retry", ge=0)
    current_count: int = Field(..., description="Current request count in window")
    limit: int = Field(..., description="Rate limit threshold")
    window_reset_at: datetime = Field(..., description="When window resets")


# Default rate limits
DEFAULT_RATE_LIMITS = {
    "global": RateLimitConfig(limit=100, window_seconds=3600),  # 100/hour globally
    "scenario": RateLimitConfig(limit=10, window_seconds=3600),  # 10/hour per scenario
    "user": RateLimitConfig(limit=20, window_seconds=3600),  # 20/hour per user
}


class RateLimiter:
    """Token bucket rate limiter using Azure Table Storage.

    Implements sliding window rate limiting with persistence in Table Storage.
    Each limit type (global, scenario, user) has its own partition.

    Example:
        >>> table_client = TableClient.from_connection_string(conn_str, "RateLimits")
        >>> limiter = RateLimiter(table_client)
        >>> result = await limiter.check_rate_limit("global", "default", 100, 3600)
        >>> if not result.allowed:
        ...     print(f"Rate limit exceeded. Retry after {result.retry_after}s")
    """

    def __init__(self, table_client: TableClient):
        """Initialize rate limiter.

        Args:
            table_client: Azure Table Storage client for rate limit storage
        """
        self.table = table_client

    async def check_rate_limit(
        self,
        limit_type: Literal["global", "scenario", "user"],
        identifier: str,
        limit: int,
        window_seconds: int = 3600,
    ) -> RateLimitResult:
        """Check if rate limit is exceeded.

        Uses token bucket algorithm with sliding window. State is stored in
        Table Storage for persistence across function invocations.

        Args:
            limit_type: Type of limit (global, scenario, user)
            identifier: Unique identifier (e.g., "default", scenario_name, user_id)
            limit: Max requests per window
            window_seconds: Time window in seconds

        Returns:
            RateLimitResult with decision and metadata

        Example:
            >>> result = await limiter.check_rate_limit("scenario", "compute-01", 10, 3600)
            >>> if result.allowed:
            ...     # Process request
            ...     pass
        """
        now = datetime.now(UTC)
        partition_key = limit_type
        row_key = identifier

        try:
            # Get existing rate limit record
            entity = await self.table.get_entity(
                partition_key=partition_key,
                row_key=row_key,
            )

            count = entity.get("Count", 0)
            window_start = entity.get("WindowStart")

            # Parse datetime if string
            if isinstance(window_start, str):
                window_start = datetime.fromisoformat(window_start.replace("Z", "+00:00"))

        except ResourceNotFoundError:
            # No record exists, create new window
            count = 0
            window_start = now

        # Check if window has expired
        window_end = window_start + timedelta(seconds=window_seconds)
        window_expired = now >= window_end

        if window_expired:
            # Reset window
            count = 0
            window_start = now
            window_end = window_start + timedelta(seconds=window_seconds)

        # Check if request allowed
        allowed = count < limit

        if allowed:
            # Increment counter
            new_count = count + 1

            # Update or create entity
            entity_data = {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Count": new_count,
                "WindowStart": window_start.isoformat(),
                "LastRequest": now.isoformat(),
                "Limit": limit,
            }

            try:
                await self.table.upsert_entity(
                    entity=entity_data,
                    mode=UpdateMode.REPLACE,
                )
            except Exception as e:
                logger.error(f"Failed to update rate limit record: {e}")
                # Continue anyway - better to allow request than fail

            retry_after = 0
            current_count = new_count
        else:
            # Calculate retry_after
            retry_after = int((window_end - now).total_seconds())
            current_count = count

        return RateLimitResult(
            allowed=allowed,
            retry_after=retry_after,
            current_count=current_count,
            limit=limit,
            window_reset_at=window_end,
        )

    async def check_multiple_limits(
        self,
        checks: list[tuple[Literal["global", "scenario", "user"], str]],
    ) -> RateLimitResult:
        """Check multiple rate limits at once.

        Returns first exceeded limit, or allowed if all pass.

        Args:
            checks: List of (limit_type, identifier) tuples to check

        Returns:
            RateLimitResult (first failure or success if all pass)

        Example:
            >>> checks = [
            ...     ("global", "default"),
            ...     ("scenario", "compute-01"),
            ...     ("user", "user@example.com"),
            ... ]
            >>> result = await limiter.check_multiple_limits(checks)
        """
        for limit_type, identifier in checks:
            config = DEFAULT_RATE_LIMITS.get(limit_type)
            if not config:
                logger.warning(f"Unknown limit type: {limit_type}")
                continue

            result = await self.check_rate_limit(
                limit_type=limit_type,
                identifier=identifier,
                limit=config.limit,
                window_seconds=config.window_seconds,
            )

            if not result.allowed:
                return result

        # All checks passed - return success from last check
        return result

    async def reset_limit(
        self,
        limit_type: Literal["global", "scenario", "user"],
        identifier: str,
    ) -> None:
        """Reset rate limit for testing or admin purposes.

        Args:
            limit_type: Type of limit to reset
            identifier: Identifier to reset

        Example:
            >>> await limiter.reset_limit("user", "user@example.com")
        """
        partition_key = limit_type
        row_key = identifier

        try:
            await self.table.delete_entity(
                partition_key=partition_key,
                row_key=row_key,
            )
            logger.info(f"Reset rate limit: {limit_type}/{identifier}")
        except ResourceNotFoundError:
            # Already deleted, that's fine
            pass
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            raise

    async def get_current_usage(
        self,
        limit_type: Literal["global", "scenario", "user"],
        identifier: str,
    ) -> dict[str, int]:
        """Get current rate limit usage without incrementing.

        Args:
            limit_type: Type of limit to check
            identifier: Identifier to check

        Returns:
            Dictionary with current_count, limit, and seconds_until_reset

        Example:
            >>> usage = await limiter.get_current_usage("global", "default")
            >>> print(f"Used {usage['current_count']}/{usage['limit']}")
        """
        partition_key = limit_type
        row_key = identifier

        try:
            entity = await self.table.get_entity(
                partition_key=partition_key,
                row_key=row_key,
            )

            count = entity.get("Count", 0)
            window_start = entity.get("WindowStart")
            limit = entity.get("Limit", DEFAULT_RATE_LIMITS[limit_type].limit)

            if isinstance(window_start, str):
                window_start = datetime.fromisoformat(window_start.replace("Z", "+00:00"))

            config = DEFAULT_RATE_LIMITS[limit_type]
            window_end = window_start + timedelta(seconds=config.window_seconds)
            now = datetime.now(UTC)

            seconds_until_reset = max(0, int((window_end - now).total_seconds()))

            return {
                "current_count": count,
                "limit": limit,
                "seconds_until_reset": seconds_until_reset,
            }

        except ResourceNotFoundError:
            config = DEFAULT_RATE_LIMITS[limit_type]
            return {
                "current_count": 0,
                "limit": config.limit,
                "seconds_until_reset": 0,
            }
