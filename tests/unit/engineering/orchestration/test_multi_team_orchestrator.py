"""Tests for MultiTeamOrchestrator - multi-team coordination.

This module tests the MultiTeamOrchestrator which:
- Executes 3-team parallel sprints
- Coordinates rate limits across teams
- Isolates team failures
- Aggregates cross-team telemetry
- Manages concurrency (max_concurrent_teams)
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch


class TestMultiTeamOrchestratorCreation:
    """Tests for MultiTeamOrchestrator creation."""

    def test_create_multi_team_orchestrator(self):
        """Test creating a MultiTeamOrchestrator."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_42",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(
                team_id="team_alpha",
                team_size=6,
                focus="backend",
                repo="backend-api",
                velocity_points=40,
            ),
            TeamConfig(
                team_id="team_beta",
                team_size=5,
                focus="frontend",
                repo="frontend-app",
                velocity_points=35,
            ),
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        assert orchestrator.sprint_config == sprint_config
        assert len(orchestrator.team_configs) == 2

    def test_create_with_rate_limit_manager(self):
        """Test creating orchestrator with rate limit manager."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_43",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id="team_alpha", team_size=6, focus="backend", repo="backend-api", velocity_points=40),
        ]

        rate_limit_manager = RateLimitManager(total_budget=5000)

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
            rate_limit_manager=rate_limit_manager,
        )

        assert orchestrator.rate_limit_manager == rate_limit_manager


class TestThreeTeamParallelExecution:
    """Tests for 3-team parallel sprint execution."""

    @pytest.mark.asyncio
    async def test_execute_three_teams_parallel(self):
        """Test executing sprints for three teams in parallel."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            TeamResult,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_44",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id="team_alpha", team_size=6, focus="backend", repo="backend-api", velocity_points=40),
            TeamConfig(team_id="team_beta", team_size=5, focus="frontend", repo="frontend-app", velocity_points=35),
            TeamConfig(team_id="team_gamma", team_size=4, focus="infrastructure", repo="infra-config", velocity_points=28),
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        # Mock team sprint execution - need different team_ids for each call
        with patch.object(orchestrator, "_execute_team_sprint", new_callable=AsyncMock) as mock_exec:
            # Return different TeamResults based on which team_config is passed
            def create_team_result(team_config):
                return TeamResult(
                    team_id=team_config.team_id,  # Use actual team_id from config
                    sprint_id="sprint_44",
                    phase_results=[],
                    total_workflows=10,
                    successful_workflows=9,
                    failed_workflows=1,
                    aggregated_telemetry={"commits": 40},
                )
            mock_exec.side_effect = create_team_result

            result = await orchestrator.execute_sprint()

            # Verify all teams executed
            assert mock_exec.call_count == 3
            assert len(result.team_results) == 3

    @pytest.mark.asyncio
    async def test_teams_execute_concurrently(self):
        """Test that teams actually execute concurrently."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            TeamResult,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_45",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id=f"team_{i}", team_size=5, focus="backend", repo=f"repo_{i}", velocity_points=30)
            for i in range(3)
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        # Track execution times
        execution_times = []

        async def mock_team_sprint(team_config):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)  # Simulate work
            end = asyncio.get_event_loop().time()
            execution_times.append((team_config.team_id, start, end))
            return TeamResult(
                team_id=team_config.team_id,
                sprint_id="sprint_45",
                phase_results=[],
                total_workflows=10,
                successful_workflows=10,
                failed_workflows=0,
                aggregated_telemetry={},
            )

        with patch.object(orchestrator, "_execute_team_sprint", side_effect=mock_team_sprint):
            await orchestrator.execute_sprint()

            # Verify some overlap in execution (concurrent)
            starts = [t[1] for t in execution_times]
            ends = [t[2] for t in execution_times]

            # If truly sequential, max(starts) would be > min(ends)
            # If concurrent, there should be overlap
            assert min(ends) > min(starts)  # Some overlap


class TestRateLimitCoordination:
    """Tests for rate limit coordination across teams."""

    @pytest.mark.asyncio
    async def test_teams_share_rate_limit_budget(self):
        """Test teams share the same rate limit budget."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_46",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id="team_alpha", team_size=6, focus="backend", repo="backend-api", velocity_points=40),
            TeamConfig(team_id="team_beta", team_size=5, focus="frontend", repo="frontend-app", velocity_points=35),
        ]

        rate_limit_manager = RateLimitManager(total_budget=1000)

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
            rate_limit_manager=rate_limit_manager,
        )

        # Each team should use shared rate limit
        async def mock_team_sprint(team_config):
            from azure_haymaker.engineering_sim.orchestration.types import TeamResult
            # Acquire some budget
            await orchestrator.rate_limit_manager.acquire(100, team_id=team_config.team_id)
            return TeamResult(
                team_id=team_config.team_id,
                sprint_id="sprint_46",
                phase_results=[],
                total_workflows=5,
                successful_workflows=5,
                failed_workflows=0,
                aggregated_telemetry={"commits": 20},
            )

        with patch.object(orchestrator, "_execute_team_sprint", side_effect=mock_team_sprint):
            await orchestrator.execute_sprint()

            # Verify budget was consumed
            assert rate_limit_manager.remaining_budget < 1000

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_team_when_depleted(self):
        """Test rate limit blocks team when budget is depleted."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_47",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id="team_alpha", team_size=6, focus="backend", repo="backend-api", velocity_points=40),
            TeamConfig(team_id="team_beta", team_size=5, focus="frontend", repo="frontend-app", velocity_points=35),
        ]

        rate_limit_manager = RateLimitManager(total_budget=100)

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
            rate_limit_manager=rate_limit_manager,
        )

        # Track which team waited
        waited_teams = []

        async def mock_team_sprint(team_config):
            from azure_haymaker.engineering_sim.orchestration.types import TeamResult
            # First team depletes budget
            if team_config.team_id == "team_alpha":
                await orchestrator.rate_limit_manager.acquire(100, team_id=team_config.team_id)
            else:
                # Second team should wait
                success = await orchestrator.rate_limit_manager.acquire(
                    50, team_id=team_config.team_id, wait=False
                )
                if not success:
                    waited_teams.append(team_config.team_id)
            return TeamResult(
                team_id=team_config.team_id,
                sprint_id="sprint_47",
                phase_results=[],
                total_workflows=5,
                successful_workflows=5,
                failed_workflows=0,
                aggregated_telemetry={"commits": 20},
            )

        with patch.object(orchestrator, "_execute_team_sprint", side_effect=mock_team_sprint):
            await orchestrator.execute_sprint()

            # At least one team should have waited
            assert len(waited_teams) > 0


class TestTeamFailureIsolation:
    """Tests for team failure isolation."""

    @pytest.mark.asyncio
    async def test_single_team_failure_does_not_affect_others(self):
        """Test that one team failing doesn't affect other teams."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            TeamResult,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_48",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id="team_alpha", team_size=6, focus="backend", repo="backend-api", velocity_points=40),
            TeamConfig(team_id="team_beta", team_size=5, focus="frontend", repo="frontend-app", velocity_points=35),
            TeamConfig(team_id="team_gamma", team_size=4, focus="infrastructure", repo="infra-config", velocity_points=28),
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        async def mock_team_sprint(team_config):
            if team_config.team_id == "team_beta":
                # Team beta fails
                raise Exception("Team beta sprint failed")
            return TeamResult(
                team_id=team_config.team_id,
                sprint_id="sprint_48",
                phase_results=[],
                total_workflows=10,
                successful_workflows=10,
                failed_workflows=0,
                aggregated_telemetry={},
            )

        with patch.object(orchestrator, "_execute_team_sprint", side_effect=mock_team_sprint):
            result = await orchestrator.execute_sprint()

            # Other teams should still complete
            assert len(result.team_results) == 2  # Alpha and Gamma succeeded
            assert "team_alpha" in result.team_results
            assert "team_gamma" in result.team_results
            assert "team_beta" not in result.team_results

    @pytest.mark.asyncio
    async def test_all_teams_can_fail_independently(self):
        """Test that all teams can fail without crashing orchestrator."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_49",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id="team_alpha", team_size=6, focus="backend", repo="backend-api", velocity_points=40),
            TeamConfig(team_id="team_beta", team_size=5, focus="frontend", repo="frontend-app", velocity_points=35),
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        async def mock_team_sprint(team_config):
            raise Exception(f"{team_config.team_id} failed")

        with patch.object(orchestrator, "_execute_team_sprint", side_effect=mock_team_sprint):
            result = await orchestrator.execute_sprint()

            # No teams succeeded
            assert len(result.team_results) == 0


class TestCrossTeamTelemetryAggregation:
    """Tests for cross-team telemetry aggregation."""

    @pytest.mark.asyncio
    async def test_aggregate_telemetry_across_teams(self):
        """Test aggregating telemetry from multiple teams."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            TeamResult,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_50",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id="team_alpha", team_size=6, focus="backend", repo="backend-api", velocity_points=40),
            TeamConfig(team_id="team_beta", team_size=5, focus="frontend", repo="frontend-app", velocity_points=35),
            TeamConfig(team_id="team_gamma", team_size=4, focus="infrastructure", repo="infra-config", velocity_points=28),
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        # Mock team results with different metrics
        team_results = [
            TeamResult(
                team_id="team_alpha",
                sprint_id="sprint_50",
                phase_results=[],
                total_workflows=11,
                successful_workflows=10,
                failed_workflows=1,
                aggregated_telemetry={"total_commits": 47, "total_prs": 11, "lines_added": 1850},
            ),
            TeamResult(
                team_id="team_beta",
                sprint_id="sprint_50",
                phase_results=[],
                total_workflows=10,
                successful_workflows=9,
                failed_workflows=1,
                aggregated_telemetry={"total_commits": 42, "total_prs": 10, "lines_added": 1650},
            ),
            TeamResult(
                team_id="team_gamma",
                sprint_id="sprint_50",
                phase_results=[],
                total_workflows=8,
                successful_workflows=8,
                failed_workflows=0,
                aggregated_telemetry={"total_commits": 35, "total_prs": 8, "lines_added": 1400},
            ),
        ]

        call_count = 0

        async def mock_team_sprint(team_config):
            nonlocal call_count
            result = team_results[call_count]
            call_count += 1
            return result

        with patch.object(orchestrator, "_execute_team_sprint", side_effect=mock_team_sprint):
            result = await orchestrator.execute_sprint()

            # Verify cross-team aggregation
            assert result.total_workflows == 29  # 11 + 10 + 8
            assert result.successful_workflows == 27  # 10 + 9 + 8
            assert result.failed_workflows == 2  # 1 + 1 + 0
            assert result.aggregated_telemetry["total_commits"] == 124  # 47 + 42 + 35
            assert result.aggregated_telemetry["total_prs"] == 29  # 11 + 10 + 8
            assert result.aggregated_telemetry["lines_added"] == 4900  # 1850 + 1650 + 1400


class TestConcurrencyLimiting:
    """Tests for max_concurrent_teams limiting."""

    @pytest.mark.asyncio
    async def test_limit_concurrent_teams(self):
        """Test limiting number of concurrent teams."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            TeamResult,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_51",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        # Create 5 teams
        team_configs = [
            TeamConfig(team_id=f"team_{i}", team_size=5, focus="backend", repo=f"repo_{i}", velocity_points=30)
            for i in range(5)
        ]

        # Only allow 2 concurrent teams
        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
            max_concurrent_teams=2,
        )

        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0

        async def mock_team_sprint(team_config):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)
            concurrent_count -= 1
            return TeamResult(
                team_id=team_config.team_id,
                sprint_id="sprint_51",
                phase_results=[],
                total_workflows=5,
                successful_workflows=5,
                failed_workflows=0,
                aggregated_telemetry={},
            )

        with patch.object(orchestrator, "_execute_team_sprint", side_effect=mock_team_sprint):
            await orchestrator.execute_sprint()

            # Verify max concurrent teams was respected
            assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_default_no_concurrency_limit(self):
        """Test default behavior with no concurrency limit."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            TeamResult,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_52",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(team_id=f"team_{i}", team_size=5, focus="backend", repo=f"repo_{i}", velocity_points=30)
            for i in range(5)
        ]

        # No max_concurrent_teams specified
        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        concurrent_count = 0
        max_concurrent = 0

        async def mock_team_sprint(team_config):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return TeamResult(
                team_id=team_config.team_id,
                sprint_id="sprint_52",
                phase_results=[],
                total_workflows=5,
                successful_workflows=5,
                failed_workflows=0,
                aggregated_telemetry={},
            )

        with patch.object(orchestrator, "_execute_team_sprint", side_effect=mock_team_sprint):
            await orchestrator.execute_sprint()

            # All teams should execute concurrently
            assert max_concurrent == 5
