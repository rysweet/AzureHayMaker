"""Rate limit manager for shared API budget across teams.

This module provides async coordination for GitHub API rate limiting:
- Shared budget pool across multiple teams
- Acquire/release cycle for token management
- Blocking when budget is depleted
- Periodic refresh of rate limits
- Per-team statistics tracking
- Async coordination with asyncio.Condition
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class RateLimitManager:
    """Manages shared API rate limit budget across teams.

    This manager coordinates API rate limit usage across multiple concurrent
    teams, ensuring they don't exceed the shared GitHub API budget.

    Args:
        total_budget: Total API calls allowed (default: 5000, GitHub's limit)
        refresh_interval_seconds: How often budget refreshes (default: 3600, 1 hour)
    """

    def __init__(
        self,
        total_budget: int = 5000,
        refresh_interval_seconds: int = 3600,
    ):
        self.total_budget = total_budget
        self.remaining_budget = total_budget
        self.refresh_interval_seconds = refresh_interval_seconds

        # Async coordination
        self._condition = asyncio.Condition()
        self._lock = asyncio.Lock()

        # Statistics tracking
        self._stats: dict[str, Any] = {
            "total_requests": 0,
            "total_tokens_acquired": 0,
            "peak_usage": 0,
            "last_refresh": datetime.now(),
        }
        self._team_stats: dict[str, dict[str, Any]] = {}

    async def acquire(
        self,
        tokens: int,
        team_id: str,
        wait: bool = True,
    ) -> bool:
        """Acquire tokens from the rate limit budget.

        Args:
            tokens: Number of tokens to acquire
            team_id: Team identifier for tracking
            wait: Whether to wait for budget if insufficient (default: True)

        Returns:
            True if tokens acquired, False if insufficient and wait=False

        Raises:
            ValueError: If tokens < 0
        """
        if tokens < 0:
            raise ValueError("tokens must be >= 0")

        if tokens == 0:
            return True

        # Simple approach: check budget and wait/fail accordingly
        while True:
            async with self._lock:
                # Check if sufficient budget
                if self.remaining_budget >= tokens:
                    # Acquire tokens
                    self.remaining_budget -= tokens

                    # Update statistics
                    self._stats["total_requests"] += 1
                    self._stats["total_tokens_acquired"] += tokens
                    current_usage = self.total_budget - self.remaining_budget
                    self._stats["peak_usage"] = max(self._stats["peak_usage"], current_usage)

                    # Update per-team statistics
                    if team_id not in self._team_stats:
                        self._team_stats[team_id] = {
                            "total_acquired": 0,
                            "total_released": 0,
                            "requests": 0,
                        }

                    self._team_stats[team_id]["total_acquired"] += tokens
                    self._team_stats[team_id]["requests"] += 1

                    logger.debug(
                        f"Team {team_id} acquired {tokens} tokens, "
                        f"remaining: {self.remaining_budget}/{self.total_budget}"
                    )

                    return True

                # Insufficient budget
                if not wait:
                    return False

            # Wait for refresh
            await self._wait_for_refresh()
            # After waiting, loop back to try again

    async def release(self, tokens: int, team_id: str) -> None:
        """Release tokens back to the budget pool.

        Args:
            tokens: Number of tokens to release
            team_id: Team identifier for tracking
        """
        if tokens <= 0:
            return

        async with self._lock:
            # Don't exceed total budget
            self.remaining_budget = min(
                self.remaining_budget + tokens,
                self.total_budget
            )

            # Update per-team statistics
            if team_id in self._team_stats:
                self._team_stats[team_id]["total_released"] += tokens

            logger.debug(
                f"Team {team_id} released {tokens} tokens, "
                f"remaining: {self.remaining_budget}/{self.total_budget}"
            )

        # Notify waiting tasks (outside lock to avoid deadlock)
        async with self._condition:
            self._condition.notify_all()

    def refresh(self) -> None:
        """Manually refresh the rate limit budget to full.

        This is typically called after a refresh interval or when
        querying the GitHub API shows the budget has reset.
        """
        asyncio.create_task(self._refresh_internal())

    async def _refresh_internal(self) -> None:
        """Internal async refresh implementation."""
        async with self._lock:
            self.remaining_budget = self.total_budget
            self._stats["last_refresh"] = datetime.now()

            logger.info(f"Rate limit refreshed to {self.total_budget}")

        # Notify all waiting tasks (outside lock)
        async with self._condition:
            self._condition.notify_all()

    async def _wait_for_refresh(self, timeout: float = 60.0) -> None:
        """Wait for rate limit to be refreshed.

        This is called internally when budget is depleted.

        Args:
            timeout: Maximum time to wait in seconds (default: 60)
        """
        async with self._condition:
            try:
                await asyncio.wait_for(self._condition.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                # Timeout waiting for refresh - check if we should auto-refresh
                await self._maybe_refresh_rate_limit()

    def get_stats(self) -> dict[str, Any]:
        """Get current rate limit statistics.

        Returns:
            Dict with overall and per-team statistics
        """
        stats = {
            "total_budget": self.total_budget,
            "remaining_budget": self.remaining_budget,
            "current_usage": self.total_budget - self.remaining_budget,
            "total_requests": self._stats["total_requests"],
            "total_tokens_acquired": self._stats["total_tokens_acquired"],
            "peak_usage": self._stats["peak_usage"],
            "last_refresh": self._stats["last_refresh"],
        }

        # Add per-team breakdown
        for team_id, team_stat in self._team_stats.items():
            stats[team_id] = team_stat.copy()

        return stats

    async def _maybe_refresh_rate_limit(self) -> None:
        """Check if rate limit should be refreshed.

        This would typically query the GitHub API to check if the
        rate limit has reset. For simulation purposes, we track
        time-based refresh.
        """
        now = datetime.now()
        last_refresh = self._stats["last_refresh"]

        if (now - last_refresh).total_seconds() >= self.refresh_interval_seconds:
            await self._refresh_internal()

    def _is_over_budget(self) -> bool:
        """Check if budget is depleted.

        Returns:
            True if no budget remaining
        """
        return self.remaining_budget <= 0
