"""Tests for orchestration data types and models.

This module tests the data models used in sprint orchestration:
- SprintConfig: Sprint configuration
- TeamConfig: Team configuration
- WorkflowExecution: Workflow execution record
- SprintPhase: Sprint phase enumeration
- PhaseResult: Phase execution result
- TeamResult: Team-level result
- MultiTeamResult: Multi-team aggregated result
"""

import pytest
from datetime import datetime, timedelta
from dataclasses import FrozenInstanceError


class TestSprintConfig:
    """Tests for SprintConfig data model."""

    def test_sprint_config_creation(self):
        """Test creating a valid SprintConfig."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        config = SprintConfig(
            sprint_id="sprint_42",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
            work_hours_start=9,
            work_hours_end=18,
            work_days=[0, 1, 2, 3, 4],  # Mon-Fri
        )

        assert config.sprint_id == "sprint_42"
        assert config.duration_days == 10
        assert config.work_hours_start == 9
        assert config.work_hours_end == 18
        assert config.work_days == [0, 1, 2, 3, 4]

    def test_sprint_config_defaults(self):
        """Test SprintConfig with default values."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        config = SprintConfig(
            sprint_id="sprint_43",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        # Verify defaults
        assert config.work_hours_start == 9  # Default 9 AM
        assert config.work_hours_end == 18  # Default 6 PM
        assert config.work_days == [0, 1, 2, 3, 4]  # Default Mon-Fri

    def test_sprint_config_invalid_work_hours(self):
        """Test SprintConfig validation rejects invalid work hours."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        with pytest.raises(ValueError, match="work_hours_start must be < work_hours_end"):
            SprintConfig(
                sprint_id="sprint_44",
                duration_days=10,
                start_date=datetime(2025, 12, 8, 9, 0, 0),
                work_hours_start=18,
                work_hours_end=9,
            )

    def test_sprint_config_invalid_duration(self):
        """Test SprintConfig validation rejects invalid duration."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        with pytest.raises(ValueError, match="duration_days must be > 0"):
            SprintConfig(
                sprint_id="sprint_45",
                duration_days=0,
                start_date=datetime(2025, 12, 8, 9, 0, 0),
            )

    def test_sprint_config_immutable(self):
        """Test SprintConfig is immutable (frozen dataclass)."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        config = SprintConfig(
            sprint_id="sprint_46",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),
        )

        with pytest.raises((FrozenInstanceError, AttributeError)):
            config.sprint_id = "sprint_47"

    def test_sprint_config_end_date_calculation(self):
        """Test SprintConfig calculates end_date correctly."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

        config = SprintConfig(
            sprint_id="sprint_48",
            duration_days=10,
            start_date=datetime(2025, 12, 8, 9, 0, 0),  # Monday
        )

        # 10 work days from Monday 12/8 should be Friday 12/19
        expected_end = datetime(2025, 12, 19, 18, 0, 0)
        assert config.end_date == expected_end


class TestTeamConfig:
    """Tests for TeamConfig data model."""

    def test_team_config_creation(self):
        """Test creating a valid TeamConfig."""
        from azure_haymaker.engineering_sim.orchestration.types import TeamConfig

        config = TeamConfig(
            team_id="team_alpha",
            team_size=6,
            focus="backend",
            repo="backend-api",
            velocity_points=40,
            github_org="test-org",
            github_base_branch="main",
        )

        assert config.team_id == "team_alpha"
        assert config.team_size == 6
        assert config.focus == "backend"
        assert config.velocity_points == 40

    def test_team_config_workflow_distribution(self):
        """Test TeamConfig workflow distribution."""
        from azure_haymaker.engineering_sim.orchestration.types import TeamConfig

        config = TeamConfig(
            team_id="team_beta",
            team_size=5,
            focus="frontend",
            repo="frontend-app",
            velocity_points=35,
            workflows=[
                {"type": "feature_development", "count": 9},
                {"type": "hotfix", "count": 2},
            ],
        )

        assert len(config.workflows) == 2
        assert config.workflows[0]["type"] == "feature_development"
        assert config.workflows[0]["count"] == 9

    def test_team_config_invalid_team_size(self):
        """Test TeamConfig validation rejects invalid team size."""
        from azure_haymaker.engineering_sim.orchestration.types import TeamConfig

        with pytest.raises(ValueError, match="team_size must be > 0"):
            TeamConfig(
                team_id="team_gamma",
                team_size=0,
                focus="infrastructure",
                repo="infra-config",
                velocity_points=28,
            )

    def test_team_config_invalid_velocity(self):
        """Test TeamConfig validation rejects invalid velocity."""
        from azure_haymaker.engineering_sim.orchestration.types import TeamConfig

        with pytest.raises(ValueError, match="velocity_points must be > 0"):
            TeamConfig(
                team_id="team_delta",
                team_size=4,
                focus="data",
                repo="data-pipeline",
                velocity_points=-5,
            )


class TestWorkflowExecution:
    """Tests for WorkflowExecution data model."""

    def test_workflow_execution_creation(self):
        """Test creating a WorkflowExecution record."""
        from azure_haymaker.engineering_sim.orchestration.types import WorkflowExecution

        execution = WorkflowExecution(
            workflow_id="wf_001",
            team_id="team_alpha",
            workflow_type="feature_development",
            scheduled_start=datetime(2025, 12, 8, 10, 0, 0),
            actual_start=datetime(2025, 12, 8, 10, 5, 0),
            actual_end=datetime(2025, 12, 8, 10, 30, 0),
            success=True,
            telemetry={"commits": 3, "prs": 1},
        )

        assert execution.workflow_id == "wf_001"
        assert execution.team_id == "team_alpha"
        assert execution.success is True
        assert execution.telemetry["commits"] == 3

    def test_workflow_execution_duration_calculation(self):
        """Test WorkflowExecution calculates duration correctly."""
        from azure_haymaker.engineering_sim.orchestration.types import WorkflowExecution

        execution = WorkflowExecution(
            workflow_id="wf_002",
            team_id="team_beta",
            workflow_type="hotfix",
            scheduled_start=datetime(2025, 12, 8, 14, 0, 0),
            actual_start=datetime(2025, 12, 8, 14, 0, 0),
            actual_end=datetime(2025, 12, 8, 14, 25, 0),
            success=True,
            telemetry={},
        )

        # Duration should be 25 minutes = 1500 seconds
        assert execution.duration_seconds == 1500.0

    def test_workflow_execution_incomplete(self):
        """Test WorkflowExecution with no end time."""
        from azure_haymaker.engineering_sim.orchestration.types import WorkflowExecution

        execution = WorkflowExecution(
            workflow_id="wf_003",
            team_id="team_gamma",
            workflow_type="feature_development",
            scheduled_start=datetime(2025, 12, 8, 11, 0, 0),
            actual_start=datetime(2025, 12, 8, 11, 0, 0),
            actual_end=None,
            success=False,
            telemetry={},
        )

        # Duration should be None for incomplete execution
        assert execution.duration_seconds is None

    def test_workflow_execution_with_error(self):
        """Test WorkflowExecution with error message."""
        from azure_haymaker.engineering_sim.orchestration.types import WorkflowExecution

        execution = WorkflowExecution(
            workflow_id="wf_004",
            team_id="team_alpha",
            workflow_type="feature_development",
            scheduled_start=datetime(2025, 12, 8, 15, 0, 0),
            actual_start=datetime(2025, 12, 8, 15, 0, 0),
            actual_end=datetime(2025, 12, 8, 15, 10, 0),
            success=False,
            telemetry={},
            error="Rate limit exceeded",
        )

        assert execution.success is False
        assert execution.error == "Rate limit exceeded"


class TestSprintPhase:
    """Tests for SprintPhase enumeration."""

    def test_sprint_phase_values(self):
        """Test SprintPhase enum has expected values."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        assert SprintPhase.PLANNING.value == "planning"
        assert SprintPhase.DEVELOPMENT.value == "development"
        assert SprintPhase.CODE_FREEZE.value == "code_freeze"
        assert SprintPhase.RETROSPECTIVE.value == "retrospective"

    def test_sprint_phase_iteration(self):
        """Test iterating over SprintPhase values."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        phases = list(SprintPhase)
        assert len(phases) == 4
        assert SprintPhase.PLANNING in phases
        assert SprintPhase.DEVELOPMENT in phases

    def test_sprint_phase_percentage_allocation(self):
        """Test SprintPhase has percentage allocation method."""
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        # Planning: 10%, Development: 70%, Code Freeze: 15%, Retrospective: 5%
        assert SprintPhase.PLANNING.percentage == 0.10
        assert SprintPhase.DEVELOPMENT.percentage == 0.70
        assert SprintPhase.CODE_FREEZE.percentage == 0.15
        assert SprintPhase.RETROSPECTIVE.percentage == 0.05


class TestPhaseResult:
    """Tests for PhaseResult data model."""

    def test_phase_result_creation(self):
        """Test creating a PhaseResult."""
        from azure_haymaker.engineering_sim.orchestration.types import (
            PhaseResult,
            SprintPhase,
        )

        result = PhaseResult(
            phase=SprintPhase.DEVELOPMENT,
            workflows_executed=11,
            workflows_succeeded=10,
            workflows_failed=1,
            telemetry={
                "total_commits": 47,
                "total_prs": 11,
                "total_reviews": 23,
            },
            duration_seconds=25200.0,  # 7 hours
        )

        assert result.phase == SprintPhase.DEVELOPMENT
        assert result.workflows_executed == 11
        assert result.workflows_succeeded == 10
        assert result.workflows_failed == 1

    def test_phase_result_success_rate(self):
        """Test PhaseResult calculates success rate."""
        from azure_haymaker.engineering_sim.orchestration.types import (
            PhaseResult,
            SprintPhase,
        )

        result = PhaseResult(
            phase=SprintPhase.DEVELOPMENT,
            workflows_executed=10,
            workflows_succeeded=8,
            workflows_failed=2,
            telemetry={},
        )

        assert result.success_rate == 0.8  # 8/10 = 80%

    def test_phase_result_zero_workflows(self):
        """Test PhaseResult with zero workflows executed."""
        from azure_haymaker.engineering_sim.orchestration.types import (
            PhaseResult,
            SprintPhase,
        )

        result = PhaseResult(
            phase=SprintPhase.PLANNING,
            workflows_executed=0,
            workflows_succeeded=0,
            workflows_failed=0,
            telemetry={},
        )

        # Success rate should be 1.0 (100%) when no workflows executed
        assert result.success_rate == 1.0


class TestTeamResult:
    """Tests for TeamResult data model."""

    def test_team_result_creation(self):
        """Test creating a TeamResult."""
        from azure_haymaker.engineering_sim.orchestration.types import (
            TeamResult,
            PhaseResult,
            SprintPhase,
        )

        phase_results = [
            PhaseResult(
                phase=SprintPhase.PLANNING,
                workflows_executed=0,
                workflows_succeeded=0,
                workflows_failed=0,
                telemetry={},
            ),
            PhaseResult(
                phase=SprintPhase.DEVELOPMENT,
                workflows_executed=11,
                workflows_succeeded=10,
                workflows_failed=1,
                telemetry={"commits": 47},
            ),
        ]

        result = TeamResult(
            team_id="team_alpha",
            sprint_id="sprint_42",
            phase_results=phase_results,
            total_workflows=11,
            successful_workflows=10,
            failed_workflows=1,
            aggregated_telemetry={"total_commits": 47},
        )

        assert result.team_id == "team_alpha"
        assert result.total_workflows == 11
        assert result.successful_workflows == 10

    def test_team_result_overall_success_rate(self):
        """Test TeamResult calculates overall success rate."""
        from azure_haymaker.engineering_sim.orchestration.types import TeamResult

        result = TeamResult(
            team_id="team_beta",
            sprint_id="sprint_42",
            phase_results=[],
            total_workflows=20,
            successful_workflows=18,
            failed_workflows=2,
            aggregated_telemetry={},
        )

        assert result.overall_success_rate == 0.9  # 18/20 = 90%


class TestMultiTeamResult:
    """Tests for MultiTeamResult data model."""

    def test_multi_team_result_creation(self):
        """Test creating a MultiTeamResult."""
        from azure_haymaker.engineering_sim.orchestration.types import (
            MultiTeamResult,
            TeamResult,
        )

        team_results = {
            "team_alpha": TeamResult(
                team_id="team_alpha",
                sprint_id="sprint_42",
                phase_results=[],
                total_workflows=11,
                successful_workflows=10,
                failed_workflows=1,
                aggregated_telemetry={"commits": 47},
            ),
            "team_beta": TeamResult(
                team_id="team_beta",
                sprint_id="sprint_42",
                phase_results=[],
                total_workflows=10,
                successful_workflows=9,
                failed_workflows=1,
                aggregated_telemetry={"commits": 42},
            ),
        }

        result = MultiTeamResult(
            sprint_id="sprint_42",
            team_results=team_results,
            total_workflows=21,
            successful_workflows=19,
            failed_workflows=2,
            aggregated_telemetry={"total_commits": 89},
        )

        assert result.sprint_id == "sprint_42"
        assert len(result.team_results) == 2
        assert result.total_workflows == 21

    def test_multi_team_result_cross_team_aggregation(self):
        """Test MultiTeamResult aggregates across teams."""
        from azure_haymaker.engineering_sim.orchestration.types import (
            MultiTeamResult,
            TeamResult,
        )

        team_results = {
            "team_alpha": TeamResult(
                team_id="team_alpha",
                sprint_id="sprint_42",
                phase_results=[],
                total_workflows=11,
                successful_workflows=10,
                failed_workflows=1,
                aggregated_telemetry={"commits": 47, "prs": 11},
            ),
            "team_beta": TeamResult(
                team_id="team_beta",
                sprint_id="sprint_42",
                phase_results=[],
                total_workflows=10,
                successful_workflows=9,
                failed_workflows=1,
                aggregated_telemetry={"commits": 42, "prs": 10},
            ),
            "team_gamma": TeamResult(
                team_id="team_gamma",
                sprint_id="sprint_42",
                phase_results=[],
                total_workflows=8,
                successful_workflows=8,
                failed_workflows=0,
                aggregated_telemetry={"commits": 35, "prs": 8},
            ),
        }

        result = MultiTeamResult(
            sprint_id="sprint_42",
            team_results=team_results,
            total_workflows=29,
            successful_workflows=27,
            failed_workflows=2,
            aggregated_telemetry={
                "total_commits": 124,  # 47 + 42 + 35
                "total_prs": 29,  # 11 + 10 + 8
            },
        )

        assert result.aggregated_telemetry["total_commits"] == 124
        assert result.aggregated_telemetry["total_prs"] == 29
        assert result.overall_success_rate == pytest.approx(0.931, rel=0.01)  # 27/29
