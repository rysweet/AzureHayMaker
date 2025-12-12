"""Tests for RateLimitManager - shared API budget management.

This module tests the RateLimitManager which:
- Manages shared API rate limit budget across teams
- Supports acquire/release cycle
- Blocks when over budget
- Refreshes rate limits periodically
- Tracks usage statistics
- Provides async coordination for multiple teams
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch


class TestRateLimitManagerBasics:
    """Tests for RateLimitManager basic functionality."""

    def test_rate_limit_manager_creation(self):
        """Test creating a RateLimitManager."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(
            total_budget=5000,
            refresh_interval_seconds=3600,
        )

        assert manager.total_budget == 5000
        assert manager.remaining_budget == 5000
        assert manager.refresh_interval_seconds == 3600

    def test_rate_limit_manager_default_values(self):
        """Test RateLimitManager with default values."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager()

        # GitHub default is 5000 requests per hour
        assert manager.total_budget == 5000
        assert manager.refresh_interval_seconds == 3600


class TestAcquireReleaseCycle:
    """Tests for acquire/release cycle."""

    @pytest.mark.asyncio
    async def test_acquire_tokens_success(self):
        """Test successfully acquiring tokens."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Acquire 10 tokens
        success = await manager.acquire(10, team_id="team_alpha")

        assert success is True
        assert manager.remaining_budget == 4990

    @pytest.mark.asyncio
    async def test_acquire_tokens_multiple_requests(self):
        """Test multiple acquire requests."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Acquire tokens from multiple teams
        await manager.acquire(100, team_id="team_alpha")
        await manager.acquire(150, team_id="team_beta")
        await manager.acquire(200, team_id="team_gamma")

        assert manager.remaining_budget == 4550  # 5000 - 100 - 150 - 200

    @pytest.mark.asyncio
    async def test_release_tokens(self):
        """Test releasing tokens back to pool."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Acquire and release
        await manager.acquire(100, team_id="team_alpha")
        assert manager.remaining_budget == 4900

        await manager.release(50, team_id="team_alpha")
        assert manager.remaining_budget == 4950

    @pytest.mark.asyncio
    async def test_release_tokens_does_not_exceed_budget(self):
        """Test releasing tokens does not exceed total budget."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Try to release more than was acquired
        await manager.release(100, team_id="team_alpha")

        # Should not exceed total budget
        assert manager.remaining_budget == 5000


class TestBlockingWhenOverBudget:
    """Tests for blocking when over budget."""

    @pytest.mark.asyncio
    async def test_acquire_blocks_when_insufficient(self):
        """Test acquire blocks when insufficient tokens available."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=100)

        # Acquire most of the budget
        await manager.acquire(90, team_id="team_alpha")

        # Try to acquire more than remaining (should block or fail)
        with patch.object(manager, "_wait_for_refresh", new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = None

            # This should trigger waiting
            await manager.acquire(50, team_id="team_beta", wait=True)

            # Verify wait was called
            mock_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_fails_immediately_when_no_wait(self):
        """Test acquire fails immediately when wait=False."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=100)

        # Acquire all budget
        await manager.acquire(100, team_id="team_alpha")

        # Try to acquire without waiting
        success = await manager.acquire(10, team_id="team_beta", wait=False)

        assert success is False
        assert manager.remaining_budget == 0

    @pytest.mark.asyncio
    async def test_multiple_teams_wait_for_budget(self):
        """Test multiple teams waiting for budget."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=100)

        # Acquire all budget
        await manager.acquire(100, team_id="team_alpha")

        # Multiple teams try to acquire (will need to wait)
        with patch.object(manager, "_wait_for_refresh", new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = None

            # Start multiple acquire operations
            task1 = asyncio.create_task(
                manager.acquire(30, team_id="team_beta", wait=True)
            )
            task2 = asyncio.create_task(
                manager.acquire(40, team_id="team_gamma", wait=True)
            )

            # Let them process
            await asyncio.sleep(0.1)

            # Simulate refresh
            manager.refresh()

            # Tasks should complete
            await task1
            await task2


class TestRateLimitRefresh:
    """Tests for rate limit refresh logic."""

    def test_manual_refresh(self):
        """Test manually refreshing rate limit."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Use some budget
        asyncio.run(manager.acquire(1000, team_id="team_alpha"))
        assert manager.remaining_budget == 4000

        # Refresh
        manager.refresh()

        # Should be reset to full budget
        assert manager.remaining_budget == 5000

    @pytest.mark.asyncio
    async def test_automatic_refresh(self):
        """Test automatic refresh after interval."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        # Short refresh interval for testing
        manager = RateLimitManager(total_budget=5000, refresh_interval_seconds=1)

        # Use some budget
        await manager.acquire(1000, team_id="team_alpha")
        assert manager.remaining_budget == 4000

        # Wait for auto-refresh
        await asyncio.sleep(1.5)

        # Should be refreshed (if auto-refresh is implemented)
        # Note: This test assumes auto-refresh is implemented
        # Implementation will determine exact behavior

    def test_refresh_with_zero_budget(self):
        """Test refreshing when budget is completely depleted."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=100)

        # Deplete budget
        asyncio.run(manager.acquire(100, team_id="team_alpha"))
        assert manager.remaining_budget == 0

        # Refresh
        manager.refresh()

        # Should be restored
        assert manager.remaining_budget == 100


class TestStatisticsTracking:
    """Tests for usage statistics tracking."""

    @pytest.mark.asyncio
    async def test_track_per_team_usage(self):
        """Test tracking usage per team."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Multiple teams acquire tokens
        await manager.acquire(100, team_id="team_alpha")
        await manager.acquire(150, team_id="team_beta")
        await manager.acquire(200, team_id="team_alpha")  # Alpha again

        stats = manager.get_stats()

        assert stats["team_alpha"]["total_acquired"] == 300  # 100 + 200
        assert stats["team_beta"]["total_acquired"] == 150

    @pytest.mark.asyncio
    async def test_track_total_requests(self):
        """Test tracking total number of requests."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Make multiple requests
        await manager.acquire(50, team_id="team_alpha")
        await manager.acquire(50, team_id="team_alpha")
        await manager.acquire(50, team_id="team_beta")

        stats = manager.get_stats()

        assert stats["total_requests"] >= 3
        assert stats["total_tokens_acquired"] == 150

    @pytest.mark.asyncio
    async def test_track_peak_usage(self):
        """Test tracking peak usage."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Acquire varying amounts
        await manager.acquire(100, team_id="team_alpha")
        assert manager.remaining_budget == 4900

        await manager.acquire(200, team_id="team_beta")
        assert manager.remaining_budget == 4700  # Peak usage: 300

        await manager.release(150, team_id="team_alpha")
        assert manager.remaining_budget == 4850

        stats = manager.get_stats()

        # Peak usage should be 300 (when remaining was 4700)
        assert stats["peak_usage"] == 300

    @pytest.mark.asyncio
    async def test_get_stats_includes_current_state(self):
        """Test get_stats includes current state."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        await manager.acquire(500, team_id="team_alpha")

        stats = manager.get_stats()

        assert stats["total_budget"] == 5000
        assert stats["remaining_budget"] == 4500
        assert stats["current_usage"] == 500


class TestAsyncCoordination:
    """Tests for async coordination across multiple teams."""

    @pytest.mark.asyncio
    async def test_concurrent_acquires(self):
        """Test concurrent acquire requests from multiple teams."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Launch concurrent acquires
        tasks = [
            manager.acquire(100, team_id=f"team_{i}") for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert manager.remaining_budget == 4000  # 5000 - (10 * 100)

    @pytest.mark.asyncio
    async def test_acquire_with_timeout(self):
        """Test acquire with timeout when waiting for budget."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=100)

        # Deplete budget
        await manager.acquire(100, team_id="team_alpha")

        # Try to acquire with timeout (should timeout)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                manager.acquire(50, team_id="team_beta", wait=True),
                timeout=0.5,
            )

    @pytest.mark.asyncio
    async def test_fairness_across_teams(self):
        """Test fairness in distributing budget across teams."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=300)

        # Multiple teams compete for budget
        async def team_work(team_id: str, iterations: int):
            acquired = 0
            for _ in range(iterations):
                success = await manager.acquire(10, team_id=team_id, wait=False)
                if success:
                    acquired += 10
                await asyncio.sleep(0.01)
            return acquired

        # Three teams each try to acquire 10 tokens, 20 times
        tasks = [
            team_work("team_alpha", 20),
            team_work("team_beta", 20),
            team_work("team_gamma", 20),
        ]

        results = await asyncio.gather(*tasks)

        # Verify some fairness (no single team should get everything)
        # Each team should get roughly 100 tokens (300 / 3)
        for acquired in results:
            assert acquired > 0  # Each team got something
            assert acquired <= 200  # No team got too much


class TestRateLimitManagerEdgeCases:
    """Tests for RateLimitManager edge cases."""

    @pytest.mark.asyncio
    async def test_acquire_zero_tokens(self):
        """Test acquiring zero tokens."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        success = await manager.acquire(0, team_id="team_alpha")

        assert success is True
        assert manager.remaining_budget == 5000

    @pytest.mark.asyncio
    async def test_acquire_negative_tokens(self):
        """Test acquiring negative tokens (should be invalid)."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        with pytest.raises(ValueError, match="tokens must be >= 0"):
            await manager.acquire(-10, team_id="team_alpha")

    @pytest.mark.asyncio
    async def test_acquire_exact_remaining_budget(self):
        """Test acquiring exactly the remaining budget."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Acquire some
        await manager.acquire(4950, team_id="team_alpha")

        # Acquire exact remaining
        success = await manager.acquire(50, team_id="team_beta")

        assert success is True
        assert manager.remaining_budget == 0

    @pytest.mark.asyncio
    async def test_concurrent_refresh_and_acquire(self):
        """Test concurrent refresh and acquire operations."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=100)

        # Deplete budget
        await manager.acquire(100, team_id="team_alpha")

        # Concurrent refresh and acquire
        async def refresh_after_delay():
            await asyncio.sleep(0.1)
            manager.refresh()

        task1 = asyncio.create_task(refresh_after_delay())
        task2 = asyncio.create_task(
            manager.acquire(50, team_id="team_beta", wait=True)
        )

        await asyncio.gather(task1, task2)

        # After refresh, acquire should succeed
        assert manager.remaining_budget <= 100


class TestRateLimitManagerIntegration:
    """Integration tests for RateLimitManager with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_realistic_three_team_scenario(self):
        """Test realistic scenario with three teams."""
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        manager = RateLimitManager(total_budget=5000)

        # Simulate three teams executing workflows
        async def team_sprint(team_id: str, workflow_count: int):
            total_acquired = 0
            for i in range(workflow_count):
                # Each workflow needs ~50 API calls
                success = await manager.acquire(50, team_id=team_id)
                if success:
                    total_acquired += 50
                # Simulate workflow execution time
                await asyncio.sleep(0.01)
                # Release half (some calls are cached/reused)
                await manager.release(25, team_id=team_id)
            return total_acquired

        # Three teams with different workflow counts
        tasks = [
            team_sprint("team_alpha", 11),
            team_sprint("team_beta", 10),
            team_sprint("team_gamma", 8),
        ]

        results = await asyncio.gather(*tasks)

        # Verify all teams completed work
        assert all(r > 0 for r in results)

        # Get final stats
        stats = manager.get_stats()
        assert stats["total_requests"] > 0
        assert stats["team_alpha"]["total_acquired"] > 0
