"""Telemetry aggregation across workflow/phase/team/multi-team levels.

This module provides 4-level telemetry aggregation:
- Level 1: Workflow-level (from individual bricks)
- Level 2: Phase-level (from multiple workflows)
- Level 3: Team-level (from multiple phases)
- Level 4: Multi-team level (from multiple teams)

All functions are pure (no side effects) and designed for easy testing.
"""

from typing import Any

from azure_haymaker.engineering_sim.bricks.base import BrickResult
from azure_haymaker.engineering_sim.orchestration.types import PhaseResult, SprintPhase


class TelemetryAggregator:
    """Aggregator for telemetry across multiple levels.

    This is a stateless aggregator that provides pure functions for
    rolling up telemetry from workflows -> phases -> teams -> multi-team.
    """

    def aggregate_workflow(self, workflow_result: BrickResult) -> dict[str, Any]:
        """Aggregate telemetry from a single workflow's brick results.

        Args:
            workflow_result: Result from workflow execution containing brick telemetry

        Returns:
            Aggregated workflow-level telemetry
        """
        telemetry = workflow_result.telemetry.copy()

        # Extract brick list if present
        bricks = telemetry.get("bricks", [])

        # Initialize counters
        aggregated = {
            "workflow": telemetry.get("workflow", "unknown"),
            "total_bricks": telemetry.get("bricks_executed", len(bricks)),
            "lines_added": 0,
            "lines_deleted": 0,
            "commits": 0,
            "prs": 0,
            "reviews": 0,
            "ci_runs": 0,
            "ci_failures": 0,
            "success": workflow_result.success,
        }

        # Add error if present
        if workflow_result.error:
            aggregated["error"] = workflow_result.error

        # Aggregate metrics from bricks
        for brick in bricks:
            if not isinstance(brick, dict):
                continue

            # Sum numeric fields
            aggregated["lines_added"] += brick.get("lines_added", 0)
            aggregated["lines_deleted"] += brick.get("lines_deleted", 0)

            # Count by brick type
            brick_name = brick.get("brick", "")
            if "Commit" in brick_name:
                aggregated["commits"] += 1
            elif "PullRequest" in brick_name:
                aggregated["prs"] += 1
            elif "Review" in brick_name:
                aggregated["reviews"] += 1
            elif "CIPipeline" in brick_name or "CI" in brick_name:
                aggregated["ci_runs"] += 1
                if brick.get("status") == "failed":
                    aggregated["ci_failures"] += 1

        return aggregated

    def aggregate_phase(
        self,
        phase: SprintPhase,
        workflow_telemetries: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aggregate telemetry from multiple workflows in a phase.

        Args:
            phase: Sprint phase being aggregated
            workflow_telemetries: List of workflow-level telemetry dicts
            metadata: Optional phase-specific metadata

        Returns:
            Aggregated phase-level telemetry
        """
        aggregated = {
            "phase": phase.value,
            "workflows_executed": len(workflow_telemetries),
            "workflows_succeeded": 0,
            "workflows_failed": 0,
            "total_commits": 0,
            "total_prs": 0,
            "total_reviews": 0,
            "total_lines_added": 0,
            "total_lines_deleted": 0,
        }

        # Add metadata if provided
        if metadata:
            aggregated.update(metadata)

        # Aggregate from workflows
        for workflow_telemetry in workflow_telemetries:
            # Count successes/failures
            if workflow_telemetry.get("success", True):
                aggregated["workflows_succeeded"] += 1
            else:
                aggregated["workflows_failed"] += 1

            # Sum metrics
            aggregated["total_commits"] += workflow_telemetry.get("commits", 0)
            aggregated["total_prs"] += workflow_telemetry.get("prs", 0)
            aggregated["total_reviews"] += workflow_telemetry.get("reviews", 0)
            aggregated["total_lines_added"] += workflow_telemetry.get("lines_added", 0)
            aggregated["total_lines_deleted"] += workflow_telemetry.get("lines_deleted", 0)

            # Phase-specific aggregations
            if phase == SprintPhase.CODE_FREEZE:
                if workflow_telemetry.get("merged"):
                    aggregated["prs_merged"] = aggregated.get("prs_merged", 0) + 1
                if workflow_telemetry.get("workflow") == "hotfix":
                    aggregated["hotfixes_allowed"] = aggregated.get("hotfixes_allowed", 0) + 1

        # Calculate success rate
        if aggregated["workflows_executed"] > 0:
            aggregated["success_rate"] = (
                aggregated["workflows_succeeded"] / aggregated["workflows_executed"]
            )
        else:
            aggregated["success_rate"] = 1.0

        return aggregated

    def aggregate_team(
        self,
        team_id: str,
        phase_results: list[PhaseResult],
    ) -> dict[str, Any]:
        """Aggregate telemetry from all phases for a single team.

        Args:
            team_id: Team identifier
            phase_results: Results from each sprint phase

        Returns:
            Aggregated team-level telemetry
        """
        aggregated = {
            "team_id": team_id,
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "total_duration_seconds": 0.0,
            "total_commits": 0,
            "total_prs": 0,
            "total_reviews": 0,
            "total_lines_added": 0,
            "total_lines_deleted": 0,
        }

        # Aggregate from phases
        for phase_result in phase_results:
            aggregated["total_workflows"] += phase_result.workflows_executed
            aggregated["successful_workflows"] += phase_result.workflows_succeeded
            aggregated["failed_workflows"] += phase_result.workflows_failed

            if phase_result.duration_seconds:
                aggregated["total_duration_seconds"] += phase_result.duration_seconds

            # Sum metrics from telemetry
            telemetry = phase_result.telemetry
            aggregated["total_commits"] += telemetry.get("total_commits", 0)
            aggregated["total_prs"] += telemetry.get("total_prs", 0)
            aggregated["total_reviews"] += telemetry.get("total_reviews", 0)
            aggregated["total_lines_added"] += telemetry.get("total_lines_added", 0)
            aggregated["total_lines_deleted"] += telemetry.get("total_lines_deleted", 0)

            # Phase-specific metrics
            if "prs_merged" in telemetry:
                aggregated["prs_merged"] = telemetry["prs_merged"]
            if "velocity_achieved" in telemetry:
                aggregated["velocity_achieved"] = telemetry["velocity_achieved"]

        # Calculate overall success rate
        if aggregated["total_workflows"] > 0:
            aggregated["overall_success_rate"] = (
                aggregated["successful_workflows"] / aggregated["total_workflows"]
            )
        else:
            aggregated["overall_success_rate"] = 1.0

        return aggregated

    def aggregate_multi_team(
        self,
        team_telemetries: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate telemetry across multiple teams.

        Args:
            team_telemetries: Dict mapping team_id to team telemetry

        Returns:
            Aggregated multi-team telemetry
        """
        aggregated = {
            "total_teams": len(team_telemetries),
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "total_commits": 0,
            "total_prs": 0,
            "total_reviews": 0,
            "total_lines_added": 0,
            "total_lines_deleted": 0,
            "teams": {},
        }

        # Aggregate from teams
        for team_id, team_telemetry in team_telemetries.items():
            # Preserve per-team breakdown
            aggregated["teams"][team_id] = team_telemetry

            # Sum metrics
            aggregated["total_workflows"] += team_telemetry.get("total_workflows", 0)
            aggregated["successful_workflows"] += team_telemetry.get("successful_workflows", 0)
            aggregated["failed_workflows"] += team_telemetry.get("failed_workflows", 0)
            aggregated["total_commits"] += team_telemetry.get("total_commits", 0)
            aggregated["total_prs"] += team_telemetry.get("total_prs", 0)
            aggregated["total_reviews"] += team_telemetry.get("total_reviews", 0)
            aggregated["total_lines_added"] += team_telemetry.get("total_lines_added", 0)
            aggregated["total_lines_deleted"] += team_telemetry.get("total_lines_deleted", 0)

        # Calculate overall success rate
        if aggregated["total_workflows"] > 0:
            aggregated["overall_success_rate"] = (
                aggregated["successful_workflows"] / aggregated["total_workflows"]
            )
        else:
            aggregated["overall_success_rate"] = 1.0

        return aggregated
