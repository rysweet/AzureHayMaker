"""Integration tests for sprint orchestration.

These tests verify the integration between:
- SprintOrchestrator and WorkflowScheduler
- SprintOrchestrator and RateLimitManager
- SprintOrchestrator and TelemetryAggregator
- SprintOrchestrator and Workflow/Bricks
- MultiTeamOrchestrator and SprintOrchestrator
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.integration
class TestSprintOrchestratorIntegration:
    """Integration tests for SprintOrchestrator with real components."""

    @pytest.mark.asyncio
    async def test_orchestrator_with_real_scheduler(self, mock_github_client):
        """Test SprintOrchestrator integrates with real WorkflowScheduler."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_int_01",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=4,
            focus="backend",
            repo="backend-api",
            velocity_points=25,
            workflows=[
                {"type": "feature_development", "count": 3},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
        )

        # Mock workflow execution but use real scheduler
        with patch.object(orchestrator, "_execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = Mock(
                success=True,
                telemetry={"commits": 2, "prs": 1},
            )

            result = await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

            # Verify scheduler was used (workflows were scheduled)
            assert result.workflows_executed > 0

    @pytest.mark.asyncio
    async def test_orchestrator_with_real_rate_limit_manager(self, mock_github_client):
        """Test SprintOrchestrator integrates with real RateLimitManager."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )
        from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
            RateLimitManager,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_int_02",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_beta",
            team_size=4,
            focus="frontend",
            repo="frontend-app",
            velocity_points=25,
            workflows=[
                {"type": "feature_development", "count": 2},
            ],
        )

        rate_limit_manager = RateLimitManager(total_budget=1000)

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
            rate_limit_manager=rate_limit_manager,
        )

        # Mock workflow execution
        async def mock_workflow_exec(workflow):
            # Acquire rate limit
            await rate_limit_manager.acquire(50, team_id=team_config.team_id)
            return Mock(success=True, telemetry={"commits": 2})

        with patch.object(orchestrator, "_execute_workflow", side_effect=mock_workflow_exec):
            result = await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

            # Verify rate limit was consumed
            assert rate_limit_manager.remaining_budget < 1000

    @pytest.mark.asyncio
    async def test_orchestrator_with_real_telemetry_aggregator(self, mock_github_client):
        """Test SprintOrchestrator integrates with real TelemetryAggregator."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_int_03",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_gamma",
            team_size=4,
            focus="infrastructure",
            repo="infra-config",
            velocity_points=20,
            workflows=[
                {"type": "feature_development", "count": 2},
            ],
        )

        telemetry_aggregator = TelemetryAggregator()

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
            telemetry_aggregator=telemetry_aggregator,
        )

        # Mock workflow execution with telemetry
        with patch.object(orchestrator, "_execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = Mock(
                success=True,
                telemetry={"commits": 3, "prs": 1, "lines_added": 150},
            )

            result = await orchestrator.execute_sprint()

            # Verify telemetry was aggregated
            assert result.aggregated_telemetry is not None
            assert "total_commits" in result.aggregated_telemetry


@pytest.mark.integration
class TestMultiTeamOrchestratorIntegration:
    """Integration tests for MultiTeamOrchestrator."""

    @pytest.mark.asyncio
    async def test_multi_team_with_real_rate_limit_coordination(self, mock_github_client):
        """Test MultiTeamOrchestrator coordinates rate limits across teams."""
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
            sprint_id="sprint_int_04",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(
                team_id="team_alpha",
                team_size=4,
                focus="backend",
                repo="backend-api",
                velocity_points=20,
                workflows=[{"type": "feature_development", "count": 2}],
            ),
            TeamConfig(
                team_id="team_beta",
                team_size=4,
                focus="frontend",
                repo="frontend-app",
                velocity_points=20,
                workflows=[{"type": "feature_development", "count": 2}],
            ),
        ]

        rate_limit_manager = RateLimitManager(total_budget=500)

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
            rate_limit_manager=rate_limit_manager,
        )

        # Mock team sprint execution
        with patch.object(orchestrator, "_execute_team_sprint", new_callable=AsyncMock) as mock_team:
            from azure_haymaker.engineering_sim.orchestration.types import TeamResult

            async def execute_team_sprint(team_config):
                # Each team uses some rate limit
                await rate_limit_manager.acquire(100, team_id=team_config.team_id)
                return TeamResult(
                    team_id=team_config.team_id,
                    sprint_id="sprint_int_04",
                    phase_results=[],
                    total_workflows=2,
                    successful_workflows=2,
                    failed_workflows=0,
                    aggregated_telemetry={},
                )

            mock_team.side_effect = execute_team_sprint

            result = await orchestrator.execute_sprint()

            # Verify both teams used shared rate limit
            assert rate_limit_manager.remaining_budget < 500
            stats = rate_limit_manager.get_stats()
            assert stats["team_alpha"]["total_acquired"] > 0
            assert stats["team_beta"]["total_acquired"] > 0

    @pytest.mark.asyncio
    async def test_multi_team_telemetry_aggregation_end_to_end(self, mock_github_client):
        """Test end-to-end telemetry aggregation across multiple teams."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            TeamResult,
            PhaseResult,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_int_05",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(
                team_id=f"team_{i}",
                team_size=4,
                focus="backend",
                repo=f"repo_{i}",
                velocity_points=20,
                workflows=[{"type": "feature_development", "count": 2}],
            )
            for i in range(3)
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        # Mock team results with real telemetry structure
        with patch.object(orchestrator, "_execute_team_sprint", new_callable=AsyncMock) as mock_team:
            call_count = 0

            async def execute_team_sprint(team_config):
                nonlocal call_count
                commits = 10 + call_count * 5  # Different per team
                call_count += 1

                return TeamResult(
                    team_id=team_config.team_id,
                    sprint_id="sprint_int_05",
                    phase_results=[
                        PhaseResult(
                            phase=SprintPhase.DEVELOPMENT,
                            workflows_executed=2,
                            workflows_succeeded=2,
                            workflows_failed=0,
                            telemetry={"total_commits": commits, "total_prs": 2},
                        ),
                    ],
                    total_workflows=2,
                    successful_workflows=2,
                    failed_workflows=0,
                    aggregated_telemetry={"total_commits": commits, "total_prs": 2},
                )

            mock_team.side_effect = execute_team_sprint

            result = await orchestrator.execute_sprint()

            # Verify cross-team aggregation
            assert result.total_workflows == 6  # 3 teams * 2 workflows
            assert result.aggregated_telemetry["total_commits"] == 45  # 10 + 15 + 20
            assert result.aggregated_telemetry["total_prs"] == 6  # 3 teams * 2 PRs


@pytest.mark.integration
class TestWorkflowBrickIntegration:
    """Integration tests for Workflow and Brick execution within orchestration."""

    @pytest.mark.asyncio
    async def test_complete_workflow_execution_in_sprint(self, mock_github_client):
        """Test executing a complete workflow with real bricks in a sprint."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )
        from azure_haymaker.engineering_sim.workflow import Workflow
        from azure_haymaker.engineering_sim.bricks.base import BrickContext

        sprint_config = SprintConfig(
            sprint_id="sprint_int_06",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=4,
            focus="backend",
            repo="backend-api",
            velocity_points=20,
            workflows=[{"type": "feature_development", "count": 1}],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
        )

        # Create a real workflow with mocked bricks
        workflow = Workflow("feature_development")

        # Mock brick execution
        mock_brick = Mock()
        mock_brick.name = "CommitBrick"
        mock_brick.validate = Mock(return_value=True)
        mock_brick.execute = AsyncMock(
            return_value=Mock(
                success=True,
                context=BrickContext(
                    team_id="team_alpha",
                    sprint_id="sprint_int_06",
                    repo_name="backend-api",
                    commit_sha="abc123",
                ),
                telemetry={"brick": "CommitBrick", "lines_added": 100},
                duration_seconds=60.0,
            )
        )

        workflow.add_brick(mock_brick)

        # Execute workflow through orchestrator
        with patch.object(orchestrator, "build_workflows", return_value=[workflow]):
            result = await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

            # Verify workflow executed with bricks
            assert result.workflows_executed == 1
            assert result.workflows_succeeded == 1
            mock_brick.execute.assert_called_once()


@pytest.mark.integration
@pytest.mark.slow
class TestFullSprintIntegration:
    """Full integration tests for complete sprint execution."""

    @pytest.mark.asyncio
    async def test_complete_single_team_sprint(self, mock_github_client):
        """Test complete single team sprint with all components."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_int_full_01",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=4,
            focus="backend",
            repo="backend-api",
            velocity_points=20,
            workflows=[
                {"type": "feature_development", "count": 3},
                {"type": "hotfix", "count": 1},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
        )

        # Mock workflow execution
        with patch.object(orchestrator, "_execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = Mock(
                success=True,
                telemetry={"commits": 2, "prs": 1, "reviews": 2},
            )

            result = await orchestrator.execute_sprint()

            # Verify complete sprint execution
            assert result.team_id == "team_alpha"
            assert result.sprint_id == "sprint_int_full_01"
            assert result.total_workflows > 0
            assert len(result.phase_results) == 4  # All 4 phases

    @pytest.mark.asyncio
    async def test_complete_multi_team_sprint(self, mock_github_client):
        """Test complete multi-team sprint with all components."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_int_full_02",
            duration_days=5,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs = [
            TeamConfig(
                team_id="team_alpha",
                team_size=4,
                focus="backend",
                repo="backend-api",
                velocity_points=20,
                workflows=[{"type": "feature_development", "count": 2}],
            ),
            TeamConfig(
                team_id="team_beta",
                team_size=4,
                focus="frontend",
                repo="frontend-app",
                velocity_points=20,
                workflows=[{"type": "feature_development", "count": 2}],
            ),
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs,
        )

        # Mock team execution
        with patch.object(orchestrator, "_execute_team_sprint", new_callable=AsyncMock) as mock_team:
            from azure_haymaker.engineering_sim.orchestration.types import TeamResult

            async def execute_team(team_config):
                return TeamResult(
                    team_id=team_config.team_id,
                    sprint_id="sprint_int_full_02",
                    phase_results=[],
                    total_workflows=2,
                    successful_workflows=2,
                    failed_workflows=0,
                    aggregated_telemetry={"commits": 8, "prs": 2},
                )

            mock_team.side_effect = execute_team

            result = await orchestrator.execute_sprint()

            # Verify multi-team execution
            assert len(result.team_results) == 2
            assert result.total_workflows == 4  # 2 teams * 2 workflows
            assert result.aggregated_telemetry["commits"] == 16  # 2 teams * 8 commits
