"""Tests for telemetry aggregation across workflow/phase/team/multi-team levels.

This module tests the TelemetryAggregator which provides 3-level aggregation:
- Level 1: Workflow-level telemetry (from individual bricks)
- Level 2: Phase-level aggregation (from multiple workflows)
- Level 3: Team-level aggregation (from multiple phases)
- Level 4: Multi-team aggregation (from multiple teams)
"""

import pytest
from datetime import datetime


class TestWorkflowLevelAggregation:
    """Tests for workflow-level telemetry aggregation (Level 1)."""

    def test_aggregate_single_workflow(self):
        """Test aggregating telemetry from a single workflow."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.bricks.base import BrickResult, BrickContext

        # Mock workflow results with brick telemetry
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
        )

        workflow_result = BrickResult(
            success=True,
            context=context,
            telemetry={
                "workflow": "feature_development",
                "bricks": [
                    {"brick": "CommitBrick", "lines_added": 120, "lines_deleted": 30},
                    {"brick": "CommitBrick", "lines_added": 80, "lines_deleted": 20},
                    {"brick": "PullRequestBrick", "pr_number": 142},
                    {"brick": "ReviewBrick", "review_state": "APPROVED"},
                ],
                "bricks_executed": 4,
            },
            duration_seconds=300.0,
        )

        aggregator = TelemetryAggregator()
        aggregated = aggregator.aggregate_workflow(workflow_result)

        # Verify aggregation
        assert aggregated["workflow"] == "feature_development"
        assert aggregated["total_bricks"] == 4
        assert aggregated["lines_added"] == 200  # 120 + 80
        assert aggregated["lines_deleted"] == 50  # 30 + 20
        assert aggregated["commits"] == 2
        assert aggregated["prs"] == 1
        assert aggregated["reviews"] == 1

    def test_aggregate_workflow_with_failures(self):
        """Test aggregating workflow with some brick failures."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.bricks.base import BrickResult, BrickContext

        context = BrickContext(
            team_id="team_beta",
            sprint_id="sprint_42",
            repo_name="frontend-app",
        )

        workflow_result = BrickResult(
            success=False,
            context=context,
            telemetry={
                "workflow": "hotfix",
                "bricks": [
                    {"brick": "CommitBrick", "lines_added": 50, "lines_deleted": 10},
                    {"brick": "PullRequestBrick", "pr_number": 143},
                    {"brick": "CIPipelineBrick", "status": "failed", "error": "Tests failed"},
                ],
                "bricks_executed": 3,
            },
            error="CI pipeline failed",
            duration_seconds=450.0,
        )

        aggregator = TelemetryAggregator()
        aggregated = aggregator.aggregate_workflow(workflow_result)

        assert aggregated["workflow"] == "hotfix"
        assert aggregated["success"] is False
        assert aggregated["error"] == "CI pipeline failed"
        assert aggregated["commits"] == 1
        assert aggregated["ci_runs"] == 1
        assert aggregated["ci_failures"] == 1

    def test_aggregate_empty_workflow(self):
        """Test aggregating workflow with no bricks."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.bricks.base import BrickResult, BrickContext

        context = BrickContext(
            team_id="team_gamma",
            sprint_id="sprint_42",
            repo_name="infra-config",
        )

        workflow_result = BrickResult(
            success=True,
            context=context,
            telemetry={"workflow": "empty", "bricks_executed": 0},
            duration_seconds=0.0,
        )

        aggregator = TelemetryAggregator()
        aggregated = aggregator.aggregate_workflow(workflow_result)

        assert aggregated["total_bricks"] == 0
        assert aggregated["lines_added"] == 0
        assert aggregated["commits"] == 0


class TestPhaseLevelAggregation:
    """Tests for phase-level telemetry aggregation (Level 2)."""

    def test_aggregate_single_phase(self):
        """Test aggregating telemetry from a single sprint phase."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        workflow_telemetries = [
            {
                "workflow": "feature_development",
                "lines_added": 200,
                "lines_deleted": 50,
                "commits": 2,
                "prs": 1,
                "reviews": 1,
                "success": True,
            },
            {
                "workflow": "feature_development",
                "lines_added": 150,
                "lines_deleted": 30,
                "commits": 2,
                "prs": 1,
                "reviews": 1,
                "success": True,
            },
            {
                "workflow": "hotfix",
                "lines_added": 50,
                "lines_deleted": 10,
                "commits": 1,
                "prs": 1,
                "reviews": 1,
                "success": True,
            },
        ]

        aggregator = TelemetryAggregator()
        phase_telemetry = aggregator.aggregate_phase(
            SprintPhase.DEVELOPMENT, workflow_telemetries
        )

        assert phase_telemetry["phase"] == "development"
        assert phase_telemetry["workflows_executed"] == 3
        assert phase_telemetry["total_commits"] == 5  # 2 + 2 + 1
        assert phase_telemetry["total_prs"] == 3  # 1 + 1 + 1
        assert phase_telemetry["total_reviews"] == 3
        assert phase_telemetry["total_lines_added"] == 400  # 200 + 150 + 50
        assert phase_telemetry["total_lines_deleted"] == 90  # 50 + 30 + 10

    def test_aggregate_phase_with_failures(self):
        """Test aggregating phase with some workflow failures."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        workflow_telemetries = [
            {
                "workflow": "feature_development",
                "commits": 2,
                "prs": 1,
                "success": True,
            },
            {
                "workflow": "feature_development",
                "commits": 2,
                "prs": 1,
                "success": False,
                "error": "CI failed",
            },
            {
                "workflow": "hotfix",
                "commits": 1,
                "prs": 1,
                "success": True,
            },
        ]

        aggregator = TelemetryAggregator()
        phase_telemetry = aggregator.aggregate_phase(
            SprintPhase.DEVELOPMENT, workflow_telemetries
        )

        assert phase_telemetry["workflows_executed"] == 3
        assert phase_telemetry["workflows_succeeded"] == 2
        assert phase_telemetry["workflows_failed"] == 1
        assert phase_telemetry["success_rate"] == pytest.approx(0.667, rel=0.01)

    def test_aggregate_planning_phase(self):
        """Test aggregating planning phase (no workflow executions)."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        # Planning phase has no workflow executions, only metadata
        workflow_telemetries = []

        aggregator = TelemetryAggregator()
        phase_telemetry = aggregator.aggregate_phase(
            SprintPhase.PLANNING,
            workflow_telemetries,
            metadata={"planned_features": 9, "story_points": 40},
        )

        assert phase_telemetry["phase"] == "planning"
        assert phase_telemetry["workflows_executed"] == 0
        assert phase_telemetry["planned_features"] == 9
        assert phase_telemetry["story_points"] == 40

    def test_aggregate_code_freeze_phase(self):
        """Test aggregating code freeze phase (merges only)."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        workflow_telemetries = [
            {"workflow": "merge_pr", "pr_number": 142, "merged": True, "success": True},
            {"workflow": "merge_pr", "pr_number": 143, "merged": True, "success": True},
            {"workflow": "hotfix", "commits": 1, "prs": 1, "success": True},
        ]

        aggregator = TelemetryAggregator()
        phase_telemetry = aggregator.aggregate_phase(
            SprintPhase.CODE_FREEZE, workflow_telemetries
        )

        assert phase_telemetry["phase"] == "code_freeze"
        assert phase_telemetry["workflows_executed"] == 3
        assert phase_telemetry["prs_merged"] == 2
        assert phase_telemetry["hotfixes_allowed"] == 1


class TestTeamLevelAggregation:
    """Tests for team-level telemetry aggregation (Level 3)."""

    def test_aggregate_single_team(self):
        """Test aggregating telemetry from all phases for a single team."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            PhaseResult,
            SprintPhase,
        )

        phase_results = [
            PhaseResult(
                phase=SprintPhase.PLANNING,
                workflows_executed=0,
                workflows_succeeded=0,
                workflows_failed=0,
                telemetry={"planned_features": 9},
                duration_seconds=3600.0,
            ),
            PhaseResult(
                phase=SprintPhase.DEVELOPMENT,
                workflows_executed=11,
                workflows_succeeded=10,
                workflows_failed=1,
                telemetry={
                    "total_commits": 47,
                    "total_prs": 11,
                    "total_reviews": 23,
                    "total_lines_added": 1850,
                    "total_lines_deleted": 420,
                },
                duration_seconds=25200.0,
            ),
            PhaseResult(
                phase=SprintPhase.CODE_FREEZE,
                workflows_executed=9,
                workflows_succeeded=9,
                workflows_failed=0,
                telemetry={"prs_merged": 9},
                duration_seconds=5400.0,
            ),
            PhaseResult(
                phase=SprintPhase.RETROSPECTIVE,
                workflows_executed=0,
                workflows_succeeded=0,
                workflows_failed=0,
                telemetry={"velocity_achieved": 38},
                duration_seconds=1800.0,
            ),
        ]

        aggregator = TelemetryAggregator()
        team_telemetry = aggregator.aggregate_team("team_alpha", phase_results)

        assert team_telemetry["team_id"] == "team_alpha"
        assert team_telemetry["total_workflows"] == 20  # 0 + 11 + 9 + 0
        assert team_telemetry["successful_workflows"] == 19  # 0 + 10 + 9 + 0
        assert team_telemetry["failed_workflows"] == 1
        assert team_telemetry["total_commits"] == 47
        assert team_telemetry["total_prs"] == 11
        assert team_telemetry["prs_merged"] == 9
        assert team_telemetry["total_duration_seconds"] == 36000.0  # Sum of all phases

    def test_aggregate_team_success_rate(self):
        """Test team-level success rate calculation."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import (
            PhaseResult,
            SprintPhase,
        )

        phase_results = [
            PhaseResult(
                phase=SprintPhase.DEVELOPMENT,
                workflows_executed=10,
                workflows_succeeded=8,
                workflows_failed=2,
                telemetry={},
            ),
            PhaseResult(
                phase=SprintPhase.CODE_FREEZE,
                workflows_executed=8,
                workflows_succeeded=7,
                workflows_failed=1,
                telemetry={},
            ),
        ]

        aggregator = TelemetryAggregator()
        team_telemetry = aggregator.aggregate_team("team_beta", phase_results)

        assert team_telemetry["total_workflows"] == 18
        assert team_telemetry["successful_workflows"] == 15
        assert team_telemetry["failed_workflows"] == 3
        assert team_telemetry["overall_success_rate"] == pytest.approx(0.833, rel=0.01)


class TestMultiTeamAggregation:
    """Tests for multi-team telemetry aggregation (Level 4)."""

    def test_aggregate_three_teams(self):
        """Test aggregating telemetry across three teams."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )

        team_telemetries = {
            "team_alpha": {
                "team_id": "team_alpha",
                "total_workflows": 20,
                "successful_workflows": 19,
                "failed_workflows": 1,
                "total_commits": 47,
                "total_prs": 11,
                "total_lines_added": 1850,
                "total_lines_deleted": 420,
            },
            "team_beta": {
                "team_id": "team_beta",
                "total_workflows": 18,
                "successful_workflows": 17,
                "failed_workflows": 1,
                "total_commits": 42,
                "total_prs": 10,
                "total_lines_added": 1650,
                "total_lines_deleted": 380,
            },
            "team_gamma": {
                "team_id": "team_gamma",
                "total_workflows": 15,
                "successful_workflows": 15,
                "failed_workflows": 0,
                "total_commits": 35,
                "total_prs": 8,
                "total_lines_added": 1400,
                "total_lines_deleted": 320,
            },
        }

        aggregator = TelemetryAggregator()
        multi_team_telemetry = aggregator.aggregate_multi_team(team_telemetries)

        assert multi_team_telemetry["total_teams"] == 3
        assert multi_team_telemetry["total_workflows"] == 53  # 20 + 18 + 15
        assert multi_team_telemetry["successful_workflows"] == 51  # 19 + 17 + 15
        assert multi_team_telemetry["failed_workflows"] == 2  # 1 + 1 + 0
        assert multi_team_telemetry["total_commits"] == 124  # 47 + 42 + 35
        assert multi_team_telemetry["total_prs"] == 29  # 11 + 10 + 8
        assert multi_team_telemetry["total_lines_added"] == 4900  # Sum
        assert multi_team_telemetry["total_lines_deleted"] == 1120  # Sum

    def test_aggregate_multi_team_success_rate(self):
        """Test multi-team overall success rate."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )

        team_telemetries = {
            "team_alpha": {
                "team_id": "team_alpha",
                "total_workflows": 20,
                "successful_workflows": 18,
                "failed_workflows": 2,
            },
            "team_beta": {
                "team_id": "team_beta",
                "total_workflows": 15,
                "successful_workflows": 14,
                "failed_workflows": 1,
            },
        }

        aggregator = TelemetryAggregator()
        multi_team_telemetry = aggregator.aggregate_multi_team(team_telemetries)

        assert multi_team_telemetry["total_workflows"] == 35
        assert multi_team_telemetry["successful_workflows"] == 32
        assert multi_team_telemetry["overall_success_rate"] == pytest.approx(
            0.914, rel=0.01
        )  # 32/35

    def test_aggregate_multi_team_per_team_metrics(self):
        """Test multi-team aggregation preserves per-team breakdowns."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )

        team_telemetries = {
            "team_alpha": {
                "team_id": "team_alpha",
                "total_workflows": 20,
                "successful_workflows": 19,
                "total_commits": 47,
            },
            "team_beta": {
                "team_id": "team_beta",
                "total_workflows": 18,
                "successful_workflows": 17,
                "total_commits": 42,
            },
        }

        aggregator = TelemetryAggregator()
        multi_team_telemetry = aggregator.aggregate_multi_team(team_telemetries)

        # Verify per-team breakdown is preserved
        assert "teams" in multi_team_telemetry
        assert len(multi_team_telemetry["teams"]) == 2
        assert multi_team_telemetry["teams"]["team_alpha"]["total_commits"] == 47
        assert multi_team_telemetry["teams"]["team_beta"]["total_commits"] == 42


class TestTelemetryAggregatorEdgeCases:
    """Tests for TelemetryAggregator edge cases."""

    def test_aggregate_with_missing_fields(self):
        """Test aggregation handles missing telemetry fields gracefully."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        # Some workflows have incomplete telemetry
        workflow_telemetries = [
            {"workflow": "feature_development", "commits": 2, "prs": 1},
            {"workflow": "hotfix", "commits": 1},  # Missing 'prs'
            {"workflow": "feature_development"},  # Missing both
        ]

        aggregator = TelemetryAggregator()
        phase_telemetry = aggregator.aggregate_phase(
            SprintPhase.DEVELOPMENT, workflow_telemetries
        )

        # Should use 0 for missing fields
        assert phase_telemetry["total_commits"] == 3  # 2 + 1 + 0
        assert phase_telemetry["total_prs"] == 1  # 1 + 0 + 0

    def test_aggregate_numeric_overflow(self):
        """Test aggregation handles large numbers correctly."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        # Simulate many workflows with large numbers
        workflow_telemetries = [
            {"workflow": f"workflow_{i}", "lines_added": 10000, "commits": 100}
            for i in range(100)
        ]

        aggregator = TelemetryAggregator()
        phase_telemetry = aggregator.aggregate_phase(
            SprintPhase.DEVELOPMENT, workflow_telemetries
        )

        assert phase_telemetry["total_lines_added"] == 1000000  # 10000 * 100
        assert phase_telemetry["total_commits"] == 10000  # 100 * 100

    def test_aggregate_with_zero_workflows(self):
        """Test aggregation with zero workflows executed."""
        from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
            TelemetryAggregator,
        )
        from azure_haymaker.engineering_sim.orchestration.types import SprintPhase

        workflow_telemetries = []

        aggregator = TelemetryAggregator()
        phase_telemetry = aggregator.aggregate_phase(
            SprintPhase.RETROSPECTIVE, workflow_telemetries
        )

        assert phase_telemetry["workflows_executed"] == 0
        assert phase_telemetry["total_commits"] == 0
        assert phase_telemetry["success_rate"] == 1.0  # 100% when no workflows
