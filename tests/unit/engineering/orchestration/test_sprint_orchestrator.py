"""Tests for SprintOrchestrator - single team sprint execution.

This module tests the SprintOrchestrator which:
- Executes complete sprint (4 phases)
- Distributes phases by percentage (10%/70%/15%/5%)
- Handles individual workflow failures gracefully
- Aggregates telemetry per phase
- Integrates with WorkflowScheduler
- Integrates with existing Workflow/bricks
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock


class TestSprintOrchestratorCreation:
    """Tests for SprintOrchestrator creation and configuration."""

    def test_create_sprint_orchestrator(self):
        """Test creating a SprintOrchestrator."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
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
        )

        assert orchestrator.sprint_config == sprint_config
        assert orchestrator.team_config == team_config

    def test_create_with_github_client(self):
        """Test creating orchestrator with GitHub client."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_43",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_beta",
            team_size=5,
            focus="frontend",
            repo="frontend-app",
            velocity_points=35,
        )

        mock_github_client = Mock()

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
            github_client=mock_github_client,
        )

        assert orchestrator.github_client == mock_github_client


class TestSprintPhaseExecution:
    """Tests for executing individual sprint phases."""

    @pytest.mark.asyncio
    async def test_execute_planning_phase(self):
        """Test executing planning phase (10% of sprint)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_44",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
            workflows=[
                {"type": "feature_development", "count": 9},
                {"type": "hotfix", "count": 2},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        result = await orchestrator.execute_phase(SprintPhase.PLANNING)

        assert result.phase == SprintPhase.PLANNING
        # Planning phase has no workflows, just metadata
        assert result.workflows_executed == 0
        assert "planned_features" in result.telemetry
        assert result.telemetry["planned_features"] == 9

    @pytest.mark.asyncio
    async def test_execute_development_phase(self):
        """Test executing development phase (70% of sprint)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_45",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_beta",
            team_size=5,
            focus="frontend",
            repo="frontend-app",
            velocity_points=35,
            workflows=[
                {"type": "feature_development", "count": 8},
                {"type": "hotfix", "count": 2},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        # Mock workflow execution
        with patch.object(orchestrator, "_execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = Mock(
                success=True,
                telemetry={"commits": 3, "prs": 1},
            )

            result = await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

            assert result.phase == SprintPhase.DEVELOPMENT
            # Development should execute all workflows (8 features + 2 hotfixes)
            assert result.workflows_executed == 10
            assert result.workflows_succeeded >= 0

    @pytest.mark.asyncio
    async def test_execute_code_freeze_phase(self):
        """Test executing code freeze phase (15% of sprint)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_46",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_gamma",
            team_size=4,
            focus="infrastructure",
            repo="infra-config",
            velocity_points=28,
            workflows=[
                {"type": "feature_development", "count": 7},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        # Mock merge operations
        with patch.object(orchestrator, "_merge_pending_prs", new_callable=AsyncMock) as mock_merge:
            mock_merge.return_value = {"prs_merged": 7}

            result = await orchestrator.execute_phase(SprintPhase.CODE_FREEZE)

            assert result.phase == SprintPhase.CODE_FREEZE
            assert result.telemetry["prs_merged"] == 7

    @pytest.mark.asyncio
    async def test_execute_retrospective_phase(self):
        """Test executing retrospective phase (5% of sprint)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_47",
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
        )

        # Retrospective analyzes previous phase results
        phase_results = []

        result = await orchestrator.execute_phase(
            SprintPhase.RETROSPECTIVE,
            previous_results=phase_results,
        )

        assert result.phase == SprintPhase.RETROSPECTIVE
        assert "velocity_achieved" in result.telemetry


class TestCompleteSprint:
    """Tests for executing a complete sprint (all 4 phases)."""

    @pytest.mark.asyncio
    async def test_execute_complete_sprint(self):
        """Test executing complete sprint with all phases."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_48",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
            workflows=[
                {"type": "feature_development", "count": 9},
                {"type": "hotfix", "count": 2},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        # Mock phase execution
        with patch.object(orchestrator, "execute_phase", new_callable=AsyncMock) as mock_phase:
            from azure_haymaker.engineering_sim.orchestration.types import PhaseResult

            # Mock results for each phase
            mock_phase.side_effect = [
                PhaseResult(
                    phase=SprintPhase.PLANNING,
                    workflows_executed=0,
                    workflows_succeeded=0,
                    workflows_failed=0,
                    telemetry={"planned_features": 9},
                ),
                PhaseResult(
                    phase=SprintPhase.DEVELOPMENT,
                    workflows_executed=11,
                    workflows_succeeded=10,
                    workflows_failed=1,
                    telemetry={"total_commits": 47, "total_prs": 11},
                ),
                PhaseResult(
                    phase=SprintPhase.CODE_FREEZE,
                    workflows_executed=9,
                    workflows_succeeded=9,
                    workflows_failed=0,
                    telemetry={"prs_merged": 9},
                ),
                PhaseResult(
                    phase=SprintPhase.RETROSPECTIVE,
                    workflows_executed=0,
                    workflows_succeeded=0,
                    workflows_failed=0,
                    telemetry={"velocity_achieved": 38},
                ),
            ]

            result = await orchestrator.execute_sprint()

            # Verify all phases were executed
            assert mock_phase.call_count == 4
            assert result.team_id == "team_alpha"
            assert result.total_workflows == 20  # 0 + 11 + 9 + 0

    @pytest.mark.asyncio
    async def test_sprint_phase_distribution(self):
        """Test sprint phases are distributed correctly (10%/70%/15%/5%)."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
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

        team_config = TeamConfig(
            team_id="team_beta",
            team_size=5,
            focus="frontend",
            repo="frontend-app",
            velocity_points=35,
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        phase_durations = orchestrator.calculate_phase_durations()

        # 10 days = 90 work hours (9 hours/day * 10 days)
        total_hours = 90

        # Planning: 10%
        assert phase_durations["planning"] == pytest.approx(total_hours * 0.10, rel=0.01)

        # Development: 70%
        assert phase_durations["development"] == pytest.approx(total_hours * 0.70, rel=0.01)

        # Code Freeze: 15%
        assert phase_durations["code_freeze"] == pytest.approx(total_hours * 0.15, rel=0.01)

        # Retrospective: 5%
        assert phase_durations["retrospective"] == pytest.approx(total_hours * 0.05, rel=0.01)


class TestWorkflowFailureHandling:
    """Tests for handling individual workflow failures."""

    @pytest.mark.asyncio
    async def test_single_workflow_failure_does_not_crash_sprint(self):
        """Test that a single workflow failure doesn't crash the sprint."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_50",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_gamma",
            team_size=4,
            focus="infrastructure",
            repo="infra-config",
            velocity_points=28,
            workflows=[
                {"type": "feature_development", "count": 5},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        # Mock workflow execution with one failure
        call_count = 0

        async def mock_execute_workflow(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                # Third workflow fails
                return Mock(success=False, error="CI pipeline failed", telemetry={})
            return Mock(success=True, telemetry={"commits": 3, "prs": 1})

        with patch.object(orchestrator, "_execute_workflow", side_effect=mock_execute_workflow):
            result = await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

            # Verify phase completed despite failure
            assert result.workflows_executed == 5
            assert result.workflows_succeeded == 4
            assert result.workflows_failed == 1

    @pytest.mark.asyncio
    async def test_multiple_workflow_failures(self):
        """Test handling multiple workflow failures."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_51",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
            workflows=[
                {"type": "feature_development", "count": 10},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        # Mock with 30% failure rate
        call_count = 0

        async def mock_execute_workflow(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Every 3rd workflow fails
            if call_count % 3 == 0:
                return Mock(success=False, error="Random failure", telemetry={})
            return Mock(success=True, telemetry={"commits": 2, "prs": 1})

        with patch.object(orchestrator, "_execute_workflow", side_effect=mock_execute_workflow):
            result = await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

            # ~70% success rate
            assert result.workflows_failed > 0
            assert result.success_rate < 1.0
            assert result.success_rate >= 0.6


class TestTelemetryAggregation:
    """Tests for telemetry aggregation per phase."""

    @pytest.mark.asyncio
    async def test_aggregate_phase_telemetry(self):
        """Test aggregating telemetry from multiple workflows."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_52",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_beta",
            team_size=5,
            focus="frontend",
            repo="frontend-app",
            velocity_points=35,
            workflows=[
                {"type": "feature_development", "count": 3},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        # Mock workflow execution with varying telemetry
        workflow_results = [
            Mock(
                success=True,
                telemetry={
                    "commits": 3,
                    "prs": 1,
                    "lines_added": 200,
                    "lines_deleted": 50,
                },
            ),
            Mock(
                success=True,
                telemetry={
                    "commits": 2,
                    "prs": 1,
                    "lines_added": 150,
                    "lines_deleted": 30,
                },
            ),
            Mock(
                success=True,
                telemetry={
                    "commits": 4,
                    "prs": 1,
                    "lines_added": 180,
                    "lines_deleted": 40,
                },
            ),
        ]

        call_count = 0

        async def mock_execute_workflow(*args, **kwargs):
            nonlocal call_count
            result = workflow_results[call_count]
            call_count += 1
            return result

        with patch.object(orchestrator, "_execute_workflow", side_effect=mock_execute_workflow):
            result = await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

            # Verify aggregation
            assert result.telemetry["total_commits"] == 9  # 3 + 2 + 4
            assert result.telemetry["total_prs"] == 3  # 1 + 1 + 1
            assert result.telemetry["total_lines_added"] == 530  # 200 + 150 + 180
            assert result.telemetry["total_lines_deleted"] == 120  # 50 + 30 + 40


class TestWorkflowSchedulerIntegration:
    """Tests for integration with WorkflowScheduler."""

    @pytest.mark.asyncio
    async def test_uses_workflow_scheduler(self):
        """Test orchestrator uses WorkflowScheduler for timing."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
            SprintPhase,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_53",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_gamma",
            team_size=4,
            focus="infrastructure",
            repo="infra-config",
            velocity_points=28,
            workflows=[
                {"type": "feature_development", "count": 5},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        # Verify scheduler is created
        assert orchestrator.scheduler is not None

        # Mock workflow execution
        with patch.object(orchestrator, "_execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = Mock(success=True, telemetry={})

            with patch.object(orchestrator.scheduler, "schedule_workflows") as mock_schedule:
                mock_schedule.return_value = [
                    Mock(workflow=Mock(), scheduled_time=datetime(2025, 12, 8, 10, 0, 0))
                    for _ in range(5)
                ]

                await orchestrator.execute_phase(SprintPhase.DEVELOPMENT)

                # Verify scheduler was used
                mock_schedule.assert_called_once()


class TestWorkflowBrickIntegration:
    """Tests for integration with existing Workflow and bricks."""

    @pytest.mark.asyncio
    async def test_builds_workflows_from_config(self):
        """Test building Workflow objects from team config."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )

        sprint_config = SprintConfig(
            sprint_id="sprint_54",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
            workflows=[
                {"type": "feature_development", "count": 3},
                {"type": "hotfix", "count": 1},
            ],
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        workflows = orchestrator.build_workflows()

        # Verify workflows were built
        assert len(workflows) == 4  # 3 features + 1 hotfix
        assert all(hasattr(w, "execute") for w in workflows)
        assert all(hasattr(w, "bricks") for w in workflows)

    @pytest.mark.asyncio
    async def test_executes_workflow_with_bricks(self):
        """Test executing a Workflow with bricks."""
        from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
            SprintOrchestrator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            SprintConfig,
            TeamConfig,
        )
        from azure_haymaker.engineering_sim.workflow import Workflow
        from azure_haymaker.engineering_sim.bricks.base import BrickContext, BrickResult

        sprint_config = SprintConfig(
            sprint_id="sprint_55",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        team_config = TeamConfig(
            team_id="team_beta",
            team_size=5,
            focus="frontend",
            repo="frontend-app",
            velocity_points=35,
        )

        orchestrator = SprintOrchestrator(
            sprint_config=sprint_config,
            team_config=team_config,
        )

        # Create mock workflow with bricks
        mock_workflow = Mock(spec=Workflow)
        mock_workflow.name = "feature_development"
        mock_workflow.execute = AsyncMock(
            return_value=BrickResult(
                success=True,
                context=BrickContext(
                    team_id="team_beta",
                    sprint_id="sprint_55",
                    repo_name="frontend-app",
                ),
                telemetry={"commits": 3, "prs": 1},
            )
        )

        result = await orchestrator._execute_workflow(mock_workflow)

        # Verify workflow was executed
        mock_workflow.execute.assert_called_once()
        assert result.success is True
        assert result.telemetry["commits"] == 3
