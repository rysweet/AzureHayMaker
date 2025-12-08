"""Sprint orchestrator for single-team sprint execution.

This module implements the SprintOrchestrator which:
- Executes complete 4-phase sprints for a single team
- Distributes workflows across phases (10%/70%/15%/5%)
- Uses WorkflowScheduler for realistic timing
- Uses TelemetryAggregator for metrics collection
- Handles workflow failures gracefully
- Integrates with Part 3 Workflow and bricks
"""

import logging
from datetime import datetime
from typing import Any

from azure_haymaker.engineering_sim.bricks.base import BrickContext, BrickResult
from azure_haymaker.engineering_sim.orchestration.telemetry_aggregator import (
    TelemetryAggregator,
)
from azure_haymaker.engineering_sim.orchestration.types import (
    PhaseResult,
    SprintConfig,
    SprintPhase,
    TeamConfig,
    TeamResult,
)
from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
    WorkflowScheduler,
)
from azure_haymaker.engineering_sim.workflow import Workflow

logger = logging.getLogger(__name__)


class SprintOrchestrator:
    """Orchestrates a complete sprint for a single team.

    Executes all 4 sprint phases (Planning, Development, Code Freeze, Retrospective)
    with proper workflow distribution and telemetry aggregation.

    Args:
        sprint_config: Sprint configuration
        team_config: Team configuration
        github_client: Optional GitHub client for API interactions
    """

    def __init__(
        self,
        sprint_config: SprintConfig,
        team_config: TeamConfig,
        github_client: Any = None,
    ):
        self.sprint_config = sprint_config
        self.team_config = team_config
        self.github_client = github_client

        # Initialize scheduler and aggregator
        self.scheduler = WorkflowScheduler(sprint_config)
        self.aggregator = TelemetryAggregator()

        # Phase results tracking
        self._phase_results: list[PhaseResult] = []

    def calculate_phase_durations(self) -> dict[str, float]:
        """Calculate duration in hours for each sprint phase.

        Returns:
            Dict mapping phase name to hours allocated
        """
        # Calculate total work hours in sprint
        work_hours_per_day = (
            self.sprint_config.work_hours_end - self.sprint_config.work_hours_start
        )
        total_hours = work_hours_per_day * self.sprint_config.duration_days

        return {
            "planning": total_hours * SprintPhase.PLANNING.percentage,
            "development": total_hours * SprintPhase.DEVELOPMENT.percentage,
            "code_freeze": total_hours * SprintPhase.CODE_FREEZE.percentage,
            "retrospective": total_hours * SprintPhase.RETROSPECTIVE.percentage,
        }

    def build_workflows(self) -> list[Workflow]:
        """Build Workflow objects from team configuration.

        Returns:
            List of Workflow objects ready for execution
        """
        workflows = []

        if not self.team_config.workflows:
            return workflows

        for workflow_spec in self.team_config.workflows:
            workflow_type = workflow_spec["type"]
            count = workflow_spec["count"]

            for i in range(count):
                workflow = Workflow(
                    name=f"{workflow_type}_{i+1}",
                    stop_on_failure=True,
                )
                workflows.append(workflow)

        return workflows

    async def execute_sprint(self) -> TeamResult:
        """Execute complete sprint with all 4 phases.

        Returns:
            TeamResult with aggregated metrics from all phases
        """
        logger.info(
            f"Starting sprint {self.sprint_config.sprint_id} "
            f"for team {self.team_config.team_id}"
        )

        self._phase_results = []

        # Execute each phase sequentially
        for phase in SprintPhase:
            logger.info(f"Executing phase: {phase.value}")

            # Pass previous results to phases that need them
            if phase == SprintPhase.RETROSPECTIVE:
                result = await self.execute_phase(
                    phase, previous_results=self._phase_results
                )
            else:
                result = await self.execute_phase(phase)

            self._phase_results.append(result)

        # Aggregate results across all phases
        total_workflows = sum(r.workflows_executed for r in self._phase_results)
        successful_workflows = sum(r.workflows_succeeded for r in self._phase_results)
        failed_workflows = sum(r.workflows_failed for r in self._phase_results)

        # Merge telemetry from all phases
        aggregated_telemetry = {}
        for phase_result in self._phase_results:
            aggregated_telemetry[phase_result.phase.value] = phase_result.telemetry

        logger.info(
            f"Sprint {self.sprint_config.sprint_id} completed: "
            f"{successful_workflows}/{total_workflows} workflows succeeded"
        )

        return TeamResult(
            team_id=self.team_config.team_id,
            sprint_id=self.sprint_config.sprint_id,
            phase_results=self._phase_results,
            total_workflows=total_workflows,
            successful_workflows=successful_workflows,
            failed_workflows=failed_workflows,
            aggregated_telemetry=aggregated_telemetry,
        )

    async def execute_phase(
        self,
        phase: SprintPhase,
        previous_results: list[PhaseResult] | None = None,
    ) -> PhaseResult:
        """Execute a single sprint phase.

        Args:
            phase: Sprint phase to execute
            previous_results: Results from previous phases (for retrospective)

        Returns:
            PhaseResult with phase-specific metrics
        """
        logger.info(f"Executing {phase.value} phase")

        if phase == SprintPhase.PLANNING:
            return await self._execute_planning_phase()
        elif phase == SprintPhase.DEVELOPMENT:
            return await self._execute_development_phase()
        elif phase == SprintPhase.CODE_FREEZE:
            return await self._execute_code_freeze_phase()
        elif phase == SprintPhase.RETROSPECTIVE:
            return await self._execute_retrospective_phase(previous_results or [])
        else:
            raise ValueError(f"Unknown phase: {phase}")

    async def _execute_planning_phase(self) -> PhaseResult:
        """Execute planning phase.

        Planning phase has no workflows, just planning metadata.
        """
        # Count planned features from team config
        planned_features = 0
        if self.team_config.workflows:
            for workflow_spec in self.team_config.workflows:
                if workflow_spec["type"] == "feature_development":
                    planned_features += workflow_spec["count"]

        return PhaseResult(
            phase=SprintPhase.PLANNING,
            workflows_executed=0,
            workflows_succeeded=0,
            workflows_failed=0,
            telemetry={
                "planned_features": planned_features,
                "team_size": self.team_config.team_size,
                "velocity_points": self.team_config.velocity_points,
            },
        )

    async def _execute_development_phase(self) -> PhaseResult:
        """Execute development phase.

        Development phase executes all configured workflows.
        """
        workflows = self.build_workflows()

        if not workflows:
            return PhaseResult(
                phase=SprintPhase.DEVELOPMENT,
                workflows_executed=0,
                workflows_succeeded=0,
                workflows_failed=0,
                telemetry={},
            )

        # Get time slots for development phase
        time_slots = self.scheduler.calculate_phase_time_slots(SprintPhase.DEVELOPMENT)

        # Schedule workflows
        scheduled = self.scheduler.schedule_workflows(
            workflows=workflows,
            time_slots=time_slots,
        )

        # Execute workflows
        results = await self._execute_workflows(scheduled)

        # Aggregate telemetry from results
        workflow_telemetries = [r.get("telemetry", {}) for r in results]
        phase_telemetry = self.aggregator.aggregate_phase(
            phase=SprintPhase.DEVELOPMENT,
            workflow_telemetries=workflow_telemetries,
        )

        return PhaseResult(
            phase=SprintPhase.DEVELOPMENT,
            workflows_executed=len(results),
            workflows_succeeded=sum(1 for r in results if r.get("success", False)),
            workflows_failed=sum(1 for r in results if not r.get("success", True)),
            telemetry=phase_telemetry,
        )

    async def _execute_code_freeze_phase(self) -> PhaseResult:
        """Execute code freeze phase.

        Code freeze merges pending PRs and runs final validations.
        """
        # Merge pending PRs
        merge_result = await self._merge_pending_prs()

        return PhaseResult(
            phase=SprintPhase.CODE_FREEZE,
            workflows_executed=0,
            workflows_succeeded=0,
            workflows_failed=0,
            telemetry=merge_result,
        )

    async def _execute_retrospective_phase(
        self, previous_results: list[PhaseResult]
    ) -> PhaseResult:
        """Execute retrospective phase.

        Retrospective analyzes sprint performance.

        Args:
            previous_results: Results from previous phases
        """
        # Calculate velocity achieved
        velocity_achieved = 0
        for result in previous_results:
            if result.phase == SprintPhase.DEVELOPMENT:
                velocity_achieved = result.workflows_succeeded

        return PhaseResult(
            phase=SprintPhase.RETROSPECTIVE,
            workflows_executed=0,
            workflows_succeeded=0,
            workflows_failed=0,
            telemetry={
                "velocity_achieved": velocity_achieved,
                "velocity_planned": self.team_config.velocity_points,
            },
        )

    async def _execute_workflows(
        self, scheduled_workflows: list[Any]
    ) -> list[dict[str, Any]]:
        """Execute scheduled workflows.

        Args:
            scheduled_workflows: List of ScheduledWorkflow objects

        Returns:
            List of workflow result dicts
        """
        results = []

        for scheduled in scheduled_workflows:
            workflow = scheduled.workflow

            try:
                result = await self._execute_workflow(workflow)
                results.append(
                    {
                        "workflow_name": workflow.name,
                        "success": result.success,
                        "telemetry": result.telemetry,
                        "error": result.error,
                    }
                )
            except Exception as e:
                logger.error(f"Workflow {workflow.name} failed: {e}")
                results.append(
                    {
                        "workflow_name": workflow.name,
                        "success": False,
                        "telemetry": {},
                        "error": str(e),
                    }
                )

        return results

    async def _execute_workflow(self, workflow: Workflow) -> BrickResult:
        """Execute a single workflow with bricks.

        Args:
            workflow: Workflow to execute

        Returns:
            BrickResult from workflow execution
        """
        # Create context for this workflow
        context = BrickContext(
            team_id=self.team_config.team_id,
            sprint_id=self.sprint_config.sprint_id,
            repo_name=self.team_config.repo,
            branch_name=f"feature/{workflow.name}",
        )

        # Execute workflow - always call execute
        # The workflow itself will handle empty brick lists
        result = await workflow.execute(context)
        return result

    async def _merge_pending_prs(self) -> dict[str, Any]:
        """Merge pending pull requests during code freeze.

        Returns:
            Dict with merge statistics
        """
        # Count PRs from development phase
        prs_merged = 0

        for phase_result in self._phase_results:
            if phase_result.phase == SprintPhase.DEVELOPMENT:
                # Estimate PRs from workflows
                prs_merged = phase_result.workflows_succeeded

        return {"prs_merged": prs_merged}
