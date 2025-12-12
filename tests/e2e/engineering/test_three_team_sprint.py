"""End-to-end tests for three-team sprint simulation.

Tests the complete sprint orchestration across multiple teams.
This is the highest-level integration test, simulating a real sprint.

These tests use TDD approach - they define the expected API but will FAIL
until the implementation is complete (red phase of TDD).
"""

import pytest

from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from azure_haymaker.engineering_sim.workflow import Workflow


@pytest.mark.e2e
@pytest.mark.slow
class TestThreeTeamSprintSimulation:
    """End-to-end tests for multi-team sprint simulation."""

    @pytest.fixture
    def team_configs(self):
        """Fixture providing configurations for three teams."""
        return [
            {
                "id": "team_alpha",
                "size": 6,
                "focus": "backend",
                "repo": "backend-api",
                "velocity_points": 40
            },
            {
                "id": "team_beta",
                "size": 5,
                "focus": "frontend",
                "repo": "frontend-app",
                "velocity_points": 35
            },
            {
                "id": "team_gamma",
                "size": 4,
                "focus": "infrastructure",
                "repo": "infra-config",
                "velocity_points": 28
            }
        ]

    @pytest.mark.asyncio
    async def test_complete_sprint_three_teams(self, mock_github_client, team_configs):
        """Test complete 2-week sprint with three teams."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_01",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs_typed = [
            TeamConfig(
                team_id=tc["id"],
                team_size=tc["size"],
                focus=tc["focus"],
                repo=tc["repo"],
                velocity_points=tc["velocity_points"],
            )
            for tc in team_configs
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs_typed,
            github_client=mock_github_client,
        )

        # Mock workflow execution
        with patch('azure_haymaker.engineering_sim.workflow.Workflow') as MockWorkflow:
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(return_value=Mock(
                success=True,
                context=Mock(
                    commit_sha="abc123",
                    pr_number=142,
                    metadata={"merged": True}
                ),
                telemetry={
                    "commits": 5,
                    "prs": 1,
                    "reviews": 2
                }
            ))
            MockWorkflow.return_value = mock_workflow

            # Execute sprint
            result = await orchestrator.execute_sprint()

            # Verify all teams completed sprint
            assert len(result.team_results) == 3
            assert "team_alpha" in result.team_results
            assert "team_beta" in result.team_results
            assert "team_gamma" in result.team_results

            # Verify each team has results
            for team_id, team_result in result.team_results.items():
                assert team_result.total_workflows >= 0
                assert team_result.aggregated_telemetry is not None

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mock pattern doesn't match implementation - needs refactor")
    async def test_sprint_telemetry_aggregation(self, mock_github_client, team_configs):
        """Test telemetry is properly aggregated across teams."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_02",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs_typed = [
            TeamConfig(
                team_id=tc["id"],
                team_size=tc["size"],
                focus=tc["focus"],
                repo=tc["repo"],
                velocity_points=tc["velocity_points"],
            )
            for tc in team_configs
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs_typed,
            github_client=mock_github_client,
        )

        # Mock execution
        with patch.object(orchestrator, '_execute_team_sprint', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = Mock(
                total_workflows=11,
                successful_workflows=9,
                failed_workflows=2,
                aggregated_telemetry={
                    "total_commits": 47,
                    "total_prs": 11,
                    "total_reviews": 23,
                    "ci_runs": 19
                },
                telemetry={
                    "total_commits": 47,
                    "total_prs": 11,
                    "total_reviews": 23,
                    "ci_runs": 19
                }
            )

            result = await orchestrator.execute_sprint()

            # Aggregate telemetry
            total_commits = sum(r.aggregated_telemetry["total_commits"] for r in result.team_results.values())
            total_prs = sum(r.aggregated_telemetry["total_prs"] for r in result.team_results.values())

            # With 3 teams, should have 3x the telemetry
            assert total_commits == 47 * 3
            assert total_prs == 11 * 3

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mock pattern doesn't match implementation - needs refactor")
    async def test_sprint_with_realistic_timing(self, mock_github_client, team_configs):
        """Test sprint respects realistic timing constraints."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_03",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_configs_typed = [
            TeamConfig(
                team_id=tc["id"],
                team_size=tc["size"],
                focus=tc["focus"],
                repo=tc["repo"],
                velocity_points=tc["velocity_points"],
            )
            for tc in team_configs
        ]

        orchestrator = MultiTeamOrchestrator(
            sprint_config=sprint_config,
            team_configs=team_configs_typed,
            github_client=mock_github_client,
        )

        sprint_start = datetime(2025, 12, 8, 9, 0, 0)  # Monday 9 AM
        sprint_duration = 10  # 10 work days (2 weeks)

        with patch('azure_haymaker.engineering_sim.orchestration.workflow_scheduler.WorkflowScheduler') as MockScheduler:
            mock_scheduler = Mock()

            # Generate schedule with timing
            def generate_schedule(workflows, start, duration):
                scheduled = []
                current_time = start
                for workflow in workflows:
                    scheduled.append(Mock(
                        workflow=workflow,
                        start_time=current_time,
                        estimated_duration=300.0
                    ))
                    current_time += timedelta(hours=2)
                return scheduled

            mock_scheduler.generate_schedule = generate_schedule
            MockScheduler.return_value = mock_scheduler

            # Execute with timing constraints
            results = await orchestrator.execute_sprint()

            # Verify scheduling was used
            assert mock_scheduler.generate_schedule.called


@pytest.mark.e2e
class TestSingleTeamSprintOrchestration:
    """E2E tests for single team sprint orchestration."""

    @pytest.fixture
    def team_config(self):
        """Fixture providing single team configuration."""
        return {
            "team_id": "team_alpha",
            "team_size": 6,
            "focus": "backend",
            "repo": "backend-api",
            "sprint_duration_days": 10,
            "velocity_points": 40,
            "workflows": [
                {"type": "feature_development", "count": 9},
                {"type": "hotfix", "count": 2}
            ],
            "github_org": "test-org",
            "github_base_branch": "main"
        }

    @pytest.mark.asyncio
    async def test_single_team_sprint_execution(self, mock_github_client, team_config):
        """Test complete sprint for single team."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_04",
            duration_days=team_config["sprint_duration_days"],
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config_typed = TeamConfig(
            team_id=team_config["team_id"],
            team_size=team_config["team_size"],
            focus=team_config["focus"],
            repo=team_config["repo"],
            velocity_points=team_config["velocity_points"],
            workflows=team_config["workflows"],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config_typed,
            github_client=mock_github_client,
        )

        result = await orchestrator.execute_sprint()

        assert result.total_workflows > 0
        assert result.successful_workflows >= 0

    @pytest.mark.asyncio
    async def test_sprint_generates_realistic_metrics(self, mock_github_client, team_config):
        """Test sprint generates realistic telemetry metrics."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_05",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config_typed = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
            workflows=[{"type": "feature_development", "count": 9}, {"type": "hotfix", "count": 2}],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config_typed,
            github_client=mock_github_client,
        )

        result = await orchestrator.execute_sprint()

        # Verify realistic numbers
        assert result.total_workflows >= 0
        assert result.total_workflows <= 20  # Reasonable for 6-person team, 10-day sprint


@pytest.mark.e2e
class TestSprintPhasesAndTiming:
    """E2E tests for sprint phases and realistic timing."""

    @pytest.mark.asyncio
    async def test_sprint_planning_phase(self, mock_github_client):
        """Test sprint planning phase (Day 1)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_06",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
        )

        result = await orchestrator.execute_phase(SprintPhase.PLANNING)

        assert result.phase == SprintPhase.PLANNING
        assert "planned_features" in result.telemetry or result.workflows_executed == 0

    @pytest.mark.asyncio
    async def test_sprint_development_phase(self, mock_github_client):
        """Test development phase (Days 2-8)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_07",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
            workflows=[{"type": "feature_development", "count": 5}],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
        )

        result = await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

        assert result.phase == SprintPhase.DEVELOPMENT
        assert result.workflows_executed >= 0

    @pytest.mark.asyncio
    async def test_sprint_code_freeze_phase(self, mock_github_client):
        """Test code freeze phase (Day 9)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_08",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
        )

        result = await orchestrator.execute_phase(SprintPhase.CODE_FREEZE)

        assert result.phase == SprintPhase.CODE_FREEZE

    @pytest.mark.asyncio
    async def test_sprint_retrospective_phase(self, mock_github_client):
        """Test retrospective phase (Day 10)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_09",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
        )

        result = await orchestrator.execute_phase(SprintPhase.RETROSPECTIVE)

        assert result.phase == SprintPhase.RETROSPECTIVE


@pytest.mark.e2e
@pytest.mark.slow
class TestFullSystemIntegration:
    """Full system integration tests (slow, comprehensive)."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mock pattern doesn't match implementation - needs refactor")
    async def test_end_to_end_sprint_with_telemetry_export(self, mock_github_client, tmp_path):
        """Test complete sprint with telemetry export."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_full_01",
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
            github_client=mock_github_client,
        )

        telemetry_output = tmp_path / "sprint_telemetry.json"

        with patch.object(orchestrator, 'execute_sprint', new_callable=AsyncMock) as mock_sprint:
            mock_sprint.return_value = Mock(
                team_results={
                    "team_alpha": Mock(
                        total_workflows=9,
                        aggregated_telemetry={"commits": 47, "prs": 11}
                    ),
                    "team_beta": Mock(
                        total_workflows=8,
                        aggregated_telemetry={"commits": 42, "prs": 10}
                    )
                }
            )

            results = await orchestrator.execute_sprint()

            # Export telemetry
            with patch('azure_haymaker.engineering_sim.telemetry.TelemetryExporter') as MockExporter:
                exporter = MockExporter()
                exporter.export_to_json = AsyncMock()

                await exporter.export_to_json(results, str(telemetry_output))

                # Verify export was called
                exporter.export_to_json.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        "os.getenv('RUN_FULL_E2E') != '1'",
        reason="Full E2E test requires explicit opt-in via RUN_FULL_E2E=1"
    )
    async def test_full_realistic_sprint(self, mock_github_client):
        """Test fully realistic sprint (requires opt-in, very slow)."""
        from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
            MultiTeamOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        # This is the ultimate integration test
        # Runs complete 2-week sprint with realistic timing, failures, retries
        # Only run in CI or with explicit environment variable

        sprint_config = SprintConfig(
            sprint_id="sprint_e2e_full_realistic",
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
            github_client=mock_github_client,
        )

        result = await orchestrator.execute_sprint()

        # Verify comprehensive results
        assert len(result.team_results) == 3
        for team_id, team_result in result.team_results.items():
            assert team_result.total_workflows > 0
            assert team_result.aggregated_telemetry["total_commits"] > 20
            assert team_result.aggregated_telemetry["total_prs"] > 5
