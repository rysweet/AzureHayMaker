"""Multi-team orchestrator for coordinating parallel team sprints.

This module implements the MultiTeamOrchestrator which:
- Coordinates 3-50 teams executing sprints in parallel
- Manages shared rate limit budget via RateLimitManager
- Isolates team failures (one team failure doesn't crash others)
- Aggregates telemetry across all teams
- Supports concurrency limiting
- Exports telemetry to JSON files
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
    RateLimitManager,
)
from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
    SprintOrchestrator,
)
from azure_haymaker.engineering_sim.orchestration.types import (
    MultiTeamResult,
    SprintConfig,
    TeamConfig,
    TeamResult,
)

logger = logging.getLogger(__name__)


class MultiTeamOrchestrator:
    """Orchestrates sprints for multiple teams in parallel.

    Coordinates concurrent team sprint execution with shared rate limiting
    and cross-team telemetry aggregation.

    Args:
        sprint_config: Sprint configuration (shared across teams)
        team_configs: List of team configurations
        rate_limit_manager: Optional shared rate limit manager
        max_concurrent_teams: Maximum concurrent teams (None = unlimited)
        github_client: Optional GitHub client for API interactions
    """

    def __init__(
        self,
        sprint_config: SprintConfig,
        team_configs: list[TeamConfig],
        rate_limit_manager: RateLimitManager | None = None,
        max_concurrent_teams: int | None = None,
        github_client: Any = None,
    ):
        self.sprint_config = sprint_config
        self.team_configs = team_configs
        self.rate_limit_manager = rate_limit_manager or RateLimitManager()
        self.max_concurrent_teams = max_concurrent_teams
        self.github_client = github_client

    async def execute_sprint(self) -> MultiTeamResult:
        """Execute sprints for all teams in parallel.

        Returns:
            MultiTeamResult with aggregated metrics from all teams
        """
        logger.info(
            f"Starting multi-team sprint {self.sprint_config.sprint_id} "
            f"with {len(self.team_configs)} teams"
        )

        # Create orchestrators for each team
        orchestrators = [
            SprintOrchestrator(
                sprint_config=self.sprint_config,
                team_config=team_config,
                github_client=self.github_client,
            )
            for team_config in self.team_configs
        ]

        # Execute teams in parallel with concurrency control
        team_results = await self._execute_teams_parallel(orchestrators)

        # Aggregate results across all teams
        result = self._aggregate_results(team_results)

        logger.info(
            f"Multi-team sprint {self.sprint_config.sprint_id} completed: "
            f"{result.successful_workflows}/{result.total_workflows} workflows succeeded "
            f"across {len(result.team_results)} teams"
        )

        return result

    async def _execute_teams_parallel(
        self, orchestrators: list[SprintOrchestrator]
    ) -> list[TeamResult]:
        """Execute team sprints in parallel with concurrency control.

        Args:
            orchestrators: List of SprintOrchestrator instances

        Returns:
            List of successful TeamResult objects
        """
        results: list[TeamResult] = []

        if self.max_concurrent_teams:
            # Use semaphore to limit concurrency
            semaphore = asyncio.Semaphore(self.max_concurrent_teams)

            async def execute_with_semaphore(
                orchestrator: SprintOrchestrator,
            ) -> TeamResult | None:
                async with semaphore:
                    return await self._execute_team_sprint(orchestrator.team_config)

            # Execute with concurrency limit
            tasks = [execute_with_semaphore(orch) for orch in orchestrators]
            team_results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # No concurrency limit - execute all in parallel
            tasks = [
                self._execute_team_sprint(orch.team_config) for orch in orchestrators
            ]
            team_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failures and exceptions
        for result in team_results:
            if isinstance(result, Exception):
                logger.error(f"Team sprint failed with exception: {result}")
                continue
            if result is not None:
                results.append(result)

        return results

    async def _execute_team_sprint(
        self, team_config: TeamConfig
    ) -> TeamResult | None:
        """Execute sprint for a single team with error isolation.

        Args:
            team_config: Team configuration

        Returns:
            TeamResult if successful, None if failed
        """
        try:
            logger.info(f"Starting sprint for team {team_config.team_id}")

            # Create orchestrator for this team
            orchestrator = SprintOrchestrator(
                sprint_config=self.sprint_config,
                team_config=team_config,
                github_client=self.github_client,
            )

            # Execute sprint
            result = await orchestrator.execute_sprint()

            logger.info(
                f"Team {team_config.team_id} completed: "
                f"{result.successful_workflows}/{result.total_workflows} workflows succeeded"
            )

            return result

        except Exception as e:
            logger.error(f"Team {team_config.team_id} sprint failed: {e}")
            return None

    def _aggregate_results(self, team_results: list[TeamResult]) -> MultiTeamResult:
        """Aggregate results from all teams.

        Args:
            team_results: List of TeamResult objects

        Returns:
            MultiTeamResult with aggregated metrics
        """
        # Build team results dict
        team_results_dict = {
            result.team_id: result for result in team_results if result is not None
        }

        # Aggregate totals
        total_workflows = sum(r.total_workflows for r in team_results)
        successful_workflows = sum(r.successful_workflows for r in team_results)
        failed_workflows = sum(r.failed_workflows for r in team_results)

        # Aggregate telemetry across all teams
        aggregated_telemetry: dict[str, Any] = {}

        for team_result in team_results:
            for key, value in team_result.aggregated_telemetry.items():
                if isinstance(value, (int, float)):
                    # Sum numeric values
                    aggregated_telemetry[key] = (
                        aggregated_telemetry.get(key, 0) + value
                    )
                elif isinstance(value, dict):
                    # Merge dict values
                    if key not in aggregated_telemetry:
                        aggregated_telemetry[key] = {}
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            aggregated_telemetry[key][sub_key] = (
                                aggregated_telemetry[key].get(sub_key, 0) + sub_value
                            )

        return MultiTeamResult(
            sprint_id=self.sprint_config.sprint_id,
            team_results=team_results_dict,
            total_workflows=total_workflows,
            successful_workflows=successful_workflows,
            failed_workflows=failed_workflows,
            aggregated_telemetry=aggregated_telemetry,
        )

    def export_telemetry(
        self, result: MultiTeamResult, output_file: Path | str
    ) -> None:
        """Export telemetry to JSON file.

        Args:
            result: MultiTeamResult to export
            output_file: Path to output JSON file
        """
        output_path = Path(output_file)

        # Prepare export data
        export_data = {
            "sprint_id": result.sprint_id,
            "total_teams": len(result.team_results),
            "total_workflows": result.total_workflows,
            "successful_workflows": result.successful_workflows,
            "failed_workflows": result.failed_workflows,
            "aggregated_telemetry": result.aggregated_telemetry,
            "teams": {},
        }

        # Add per-team details
        for team_id, team_result in result.team_results.items():
            export_data["teams"][team_id] = {
                "team_id": team_result.team_id,
                "sprint_id": team_result.sprint_id,
                "total_workflows": team_result.total_workflows,
                "successful_workflows": team_result.successful_workflows,
                "failed_workflows": team_result.failed_workflows,
                "telemetry": team_result.aggregated_telemetry,
                "phases": [
                    {
                        "phase": phase_result.phase.value,
                        "workflows_executed": phase_result.workflows_executed,
                        "workflows_succeeded": phase_result.workflows_succeeded,
                        "workflows_failed": phase_result.workflows_failed,
                        "telemetry": phase_result.telemetry,
                    }
                    for phase_result in team_result.phase_results
                ],
            }

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Telemetry exported to {output_path}")
