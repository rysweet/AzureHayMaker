"""Data types and models for sprint orchestration.

This module defines all data structures used in the orchestration system:
- SprintConfig: Sprint configuration and timing
- TeamConfig: Team configuration and workflow distribution
- WorkflowExecution: Workflow execution record
- SprintPhase: Sprint phase enumeration with percentage allocation
- PhaseResult: Phase execution result
- TeamResult: Team-level result
- MultiTeamResult: Multi-team aggregated result
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class SprintPhase(Enum):
    """Sprint phases with percentage allocations.

    Each phase has a fixed percentage of sprint time:
    - PLANNING: 10%
    - DEVELOPMENT: 70%
    - CODE_FREEZE: 15%
    - RETROSPECTIVE: 5%
    """
    PLANNING = "planning"
    DEVELOPMENT = "development"
    CODE_FREEZE = "code_freeze"
    RETROSPECTIVE = "retrospective"

    @property
    def percentage(self) -> float:
        """Get the percentage allocation for this phase.

        Returns:
            Percentage as decimal (0.0 to 1.0)
        """
        percentages = {
            SprintPhase.PLANNING: 0.10,
            SprintPhase.DEVELOPMENT: 0.70,
            SprintPhase.CODE_FREEZE: 0.15,
            SprintPhase.RETROSPECTIVE: 0.05,
        }
        return percentages[self]


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class SprintConfig:
    """Configuration for a sprint.

    Args:
        sprint_id: Unique sprint identifier
        duration_days: Sprint duration in work days
        start_date: Sprint start date and time
        work_hours_start: Work day start hour (default: 9 AM)
        work_hours_end: Work day end hour (default: 6 PM)
        work_days: Work days as list of weekday numbers (default: Mon-Fri, 0-4)

    Raises:
        ValueError: If configuration is invalid
    """
    sprint_id: str
    duration_days: int
    start_date: datetime
    work_hours_start: int = 9
    work_hours_end: int = 18
    work_days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])

    def __post_init__(self):
        """Validate sprint configuration."""
        if self.duration_days <= 0:
            raise ValueError("duration_days must be > 0")

        if self.work_hours_start >= self.work_hours_end:
            raise ValueError("work_hours_start must be < work_hours_end")

    @property
    def end_date(self) -> datetime:
        """Calculate sprint end date.

        Returns:
            End date/time of sprint (end of work hours on last work day)
        """
        current = self.start_date
        work_days_counted = 0

        while work_days_counted < self.duration_days:
            if current.weekday() in self.work_days:
                work_days_counted += 1
                if work_days_counted == self.duration_days:
                    # Return end of work day
                    return current.replace(hour=self.work_hours_end, minute=0, second=0)
            current += timedelta(days=1)

        return current


@dataclass(frozen=True)
class TeamConfig:
    """Configuration for a team.

    Args:
        team_id: Unique team identifier
        team_size: Number of team members
        focus: Team focus area (e.g., "backend", "frontend")
        repo: Repository name
        velocity_points: Team velocity in story points
        workflows: List of workflow definitions (default: empty)
        github_org: GitHub organization name (default: None)
        github_base_branch: Base branch for PRs (default: "main")

    Raises:
        ValueError: If configuration is invalid
    """
    team_id: str
    team_size: int
    focus: str
    repo: str
    velocity_points: int
    workflows: list[dict[str, Any]] = field(default_factory=list)
    github_org: str | None = None
    github_base_branch: str = "main"

    def __post_init__(self):
        """Validate team configuration."""
        if self.team_size <= 0:
            raise ValueError("team_size must be > 0")

        if self.velocity_points <= 0:
            raise ValueError("velocity_points must be > 0")


@dataclass
class WorkflowExecution:
    """Record of a workflow execution.

    Args:
        workflow_id: Unique workflow identifier
        team_id: Team executing the workflow
        workflow_type: Type of workflow (e.g., "feature_development")
        scheduled_start: Scheduled start time
        actual_start: Actual start time
        actual_end: Actual end time (None if not completed)
        success: Whether execution succeeded
        telemetry: Workflow telemetry data
        error: Error message if failed (default: None)
    """
    workflow_id: str
    team_id: str
    workflow_type: str
    scheduled_start: datetime
    actual_start: datetime
    actual_end: datetime | None
    success: bool
    telemetry: dict[str, Any]
    error: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Calculate workflow duration in seconds.

        Returns:
            Duration in seconds, or None if not completed
        """
        if self.actual_end is None:
            return None
        return (self.actual_end - self.actual_start).total_seconds()


@dataclass
class PhaseResult:
    """Result of a sprint phase execution.

    Args:
        phase: Sprint phase that was executed
        workflows_executed: Total workflows executed
        workflows_succeeded: Number of successful workflows
        workflows_failed: Number of failed workflows
        telemetry: Aggregated phase telemetry
        duration_seconds: Phase duration in seconds (default: None)
    """
    phase: SprintPhase
    workflows_executed: int
    workflows_succeeded: int
    workflows_failed: int
    telemetry: dict[str, Any]
    duration_seconds: float | None = None

    @property
    def success_rate(self) -> float:
        """Calculate phase success rate.

        Returns:
            Success rate as decimal (0.0 to 1.0), 1.0 if no workflows
        """
        if self.workflows_executed == 0:
            return 1.0
        return self.workflows_succeeded / self.workflows_executed


@dataclass
class TeamResult:
    """Result of a team's sprint.

    Args:
        team_id: Team identifier
        sprint_id: Sprint identifier
        phase_results: Results from each phase
        total_workflows: Total workflows executed
        successful_workflows: Number of successful workflows
        failed_workflows: Number of failed workflows
        aggregated_telemetry: Aggregated telemetry across all phases
    """
    team_id: str
    sprint_id: str
    phase_results: list[PhaseResult]
    total_workflows: int
    successful_workflows: int
    failed_workflows: int
    aggregated_telemetry: dict[str, Any]

    @property
    def overall_success_rate(self) -> float:
        """Calculate overall team success rate.

        Returns:
            Success rate as decimal (0.0 to 1.0), 1.0 if no workflows
        """
        if self.total_workflows == 0:
            return 1.0
        return self.successful_workflows / self.total_workflows


@dataclass
class MultiTeamResult:
    """Result of a multi-team sprint.

    Args:
        sprint_id: Sprint identifier
        team_results: Dict mapping team_id to TeamResult
        total_workflows: Total workflows executed across all teams
        successful_workflows: Number of successful workflows
        failed_workflows: Number of failed workflows
        aggregated_telemetry: Aggregated telemetry across all teams
    """
    sprint_id: str
    team_results: dict[str, TeamResult]
    total_workflows: int
    successful_workflows: int
    failed_workflows: int
    aggregated_telemetry: dict[str, Any]

    @property
    def overall_success_rate(self) -> float:
        """Calculate overall multi-team success rate.

        Returns:
            Success rate as decimal (0.0 to 1.0), 1.0 if no workflows
        """
        if self.total_workflows == 0:
            return 1.0
        return self.successful_workflows / self.total_workflows
