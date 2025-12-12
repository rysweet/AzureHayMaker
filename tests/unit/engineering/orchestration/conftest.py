"""Fixtures for orchestration tests."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def sprint_config():
    """Fixture providing a standard SprintConfig."""
    from azure_haymaker.engineering_sim.orchestration.types import SprintConfig

    return SprintConfig(
        sprint_id="sprint_test",
        duration_days=10,
        start_date=datetime(2025, 12, 8, 9, 0, 0),  # Monday 9 AM
        work_hours_start=9,
        work_hours_end=18,
        work_days=[0, 1, 2, 3, 4],  # Mon-Fri
    )


@pytest.fixture
def team_config_alpha():
    """Fixture providing team_alpha configuration."""
    from azure_haymaker.engineering_sim.orchestration.types import TeamConfig

    return TeamConfig(
        team_id="team_alpha",
        team_size=6,
        focus="backend",
        repo="backend-api",
        velocity_points=40,
        github_org="test-org",
        github_base_branch="main",
        workflows=[
            {"type": "feature_development", "count": 9},
            {"type": "hotfix", "count": 2},
        ],
    )


@pytest.fixture
def team_config_beta():
    """Fixture providing team_beta configuration."""
    from azure_haymaker.engineering_sim.orchestration.types import TeamConfig

    return TeamConfig(
        team_id="team_beta",
        team_size=5,
        focus="frontend",
        repo="frontend-app",
        velocity_points=35,
        github_org="test-org",
        github_base_branch="main",
        workflows=[
            {"type": "feature_development", "count": 8},
            {"type": "hotfix", "count": 2},
        ],
    )


@pytest.fixture
def team_config_gamma():
    """Fixture providing team_gamma configuration."""
    from azure_haymaker.engineering_sim.orchestration.types import TeamConfig

    return TeamConfig(
        team_id="team_gamma",
        team_size=4,
        focus="infrastructure",
        repo="infra-config",
        velocity_points=28,
        github_org="test-org",
        github_base_branch="main",
        workflows=[
            {"type": "feature_development", "count": 7},
            {"type": "hotfix", "count": 1},
        ],
    )


@pytest.fixture
def three_team_configs(team_config_alpha, team_config_beta, team_config_gamma):
    """Fixture providing three team configurations."""
    return [team_config_alpha, team_config_beta, team_config_gamma]


@pytest.fixture
def mock_rate_limit_manager():
    """Fixture providing a mock RateLimitManager."""
    manager = Mock()
    manager.total_budget = 5000
    manager.remaining_budget = 5000
    manager.acquire = AsyncMock(return_value=True)
    manager.release = AsyncMock()
    manager.refresh = Mock()
    manager.get_stats = Mock(
        return_value={
            "total_budget": 5000,
            "remaining_budget": 5000,
            "total_requests": 0,
            "peak_usage": 0,
        }
    )
    return manager


@pytest.fixture
def mock_workflow_scheduler(sprint_config):
    """Fixture providing a mock WorkflowScheduler."""
    from azure_haymaker.engineering_sim.orchestration.workflow_scheduler import (
        WorkflowScheduler,
    )

    scheduler = Mock(spec=WorkflowScheduler)
    scheduler.sprint_config = sprint_config
    scheduler.is_work_hour = Mock(return_value=True)
    scheduler.is_work_day = Mock(return_value=True)
    scheduler.next_work_hour = Mock(return_value=datetime(2025, 12, 8, 9, 0, 0))
    scheduler.calculate_time_slots = Mock(return_value=[])
    scheduler.schedule_workflows = Mock(return_value=[])
    return scheduler


@pytest.fixture
def mock_telemetry_aggregator():
    """Fixture providing a mock TelemetryAggregator."""
    aggregator = Mock()
    aggregator.aggregate_workflow = Mock(
        return_value={
            "workflow": "test",
            "total_bricks": 0,
            "lines_added": 0,
            "commits": 0,
        }
    )
    aggregator.aggregate_phase = Mock(
        return_value={
            "phase": "development",
            "workflows_executed": 0,
            "total_commits": 0,
        }
    )
    aggregator.aggregate_team = Mock(
        return_value={
            "team_id": "test_team",
            "total_workflows": 0,
            "successful_workflows": 0,
        }
    )
    aggregator.aggregate_multi_team = Mock(
        return_value={
            "total_teams": 0,
            "total_workflows": 0,
            "successful_workflows": 0,
        }
    )
    return aggregator


@pytest.fixture
def sample_phase_result():
    """Fixture providing a sample PhaseResult."""
    from azure_haymaker.engineering_sim.orchestration.types import (
        PhaseResult,
        SprintPhase,
    )

    return PhaseResult(
        phase=SprintPhase.DEVELOPMENT,
        workflows_executed=10,
        workflows_succeeded=9,
        workflows_failed=1,
        telemetry={
            "total_commits": 42,
            "total_prs": 10,
            "total_reviews": 20,
        },
        duration_seconds=25200.0,
    )


@pytest.fixture
def sample_team_result(sample_phase_result):
    """Fixture providing a sample TeamResult."""
    from azure_haymaker.engineering_sim.orchestration.types import TeamResult

    return TeamResult(
        team_id="team_test",
        sprint_id="sprint_test",
        phase_results=[sample_phase_result],
        total_workflows=10,
        successful_workflows=9,
        failed_workflows=1,
        aggregated_telemetry={
            "total_commits": 42,
            "total_prs": 10,
        },
    )


@pytest.fixture
def sample_workflow_execution():
    """Fixture providing a sample WorkflowExecution."""
    from azure_haymaker.engineering_sim.orchestration.types import WorkflowExecution

    return WorkflowExecution(
        workflow_id="wf_test_001",
        team_id="team_test",
        workflow_type="feature_development",
        scheduled_start=datetime(2025, 12, 8, 10, 0, 0),
        actual_start=datetime(2025, 12, 8, 10, 5, 0),
        actual_end=datetime(2025, 12, 8, 10, 30, 0),
        success=True,
        telemetry={"commits": 3, "prs": 1},
    )


@pytest.fixture
def mock_sprint_orchestrator(sprint_config, team_config_alpha):
    """Fixture providing a mock SprintOrchestrator."""
    from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
        SprintOrchestrator,
    )

    orchestrator = Mock(spec=SprintOrchestrator)
    orchestrator.sprint_config = sprint_config
    orchestrator.team_config = team_config_alpha
    orchestrator.execute_sprint = AsyncMock()
    orchestrator.execute_phase = AsyncMock()
    orchestrator.build_workflows = Mock(return_value=[])
    return orchestrator


@pytest.fixture
def mock_multi_team_orchestrator(sprint_config, three_team_configs):
    """Fixture providing a mock MultiTeamOrchestrator."""
    from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
        MultiTeamOrchestrator,
    )

    orchestrator = Mock(spec=MultiTeamOrchestrator)
    orchestrator.sprint_config = sprint_config
    orchestrator.team_configs = three_team_configs
    orchestrator.execute_sprint = AsyncMock()
    return orchestrator
