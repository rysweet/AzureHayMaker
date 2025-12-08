"""Unit tests for CIPipelineBrick - CI/CD pipeline simulation.

Following TDD - these tests WILL FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock

from azure_haymaker.engineering_sim.bricks.base import BrickContext, BrickResult
from azure_haymaker.engineering_sim.bricks.ci_pipeline import CIPipelineBrick


class TestCIPipelineBrickValidation:
    """Test CIPipelineBrick validation."""

    def test_validate_requires_commit_sha(self, mock_github_client):
        """Test validate() requires commit_sha."""
        brick = CIPipelineBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )
        assert brick.validate(context) is False

    def test_validate_passes_with_commit_sha(self, mock_github_client):
        """Test validate() passes with commit_sha."""
        brick = CIPipelineBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            commit_sha="abc123"
        )
        assert brick.validate(context) is True


class TestCIPipelineBrickExecution:
    """Test CIPipelineBrick execute()."""

    @pytest.mark.asyncio
    async def test_execute_runs_ci_pipeline(self, mock_github_client):
        """Test execute() triggers CI pipeline."""
        mock_github_client.trigger_workflow = AsyncMock(return_value={
            "id": "run_123",
            "status": "completed",
            "conclusion": "success"
        })

        brick = CIPipelineBrick(
            github_client=mock_github_client,
            workflow_name="ci.yml"
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            commit_sha="abc123"
        )

        result = await brick.execute(context)

        assert result.success is True
        assert result.telemetry["brick_type"] == "ci_pipeline"
        assert result.telemetry["status"] in ["success", "failure"]
        assert result.context.metadata.get("ci_status") is not None

    @pytest.mark.asyncio
    async def test_execute_simulates_failure_probability(self, mock_github_client):
        """Test execute() respects failure_probability."""
        mock_github_client.trigger_workflow = AsyncMock(return_value={
            "id": "run_124",
            "status": "completed",
            "conclusion": "success"
        })

        brick = CIPipelineBrick(
            github_client=mock_github_client,
            failure_probability=0.0  # Never fail
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            commit_sha="abc123"
        )

        result = await brick.execute(context)

        # With 0.0 failure probability, should always succeed
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_includes_test_results(self, mock_github_client):
        """Test execute() includes test statistics."""
        mock_github_client.trigger_workflow = AsyncMock(return_value={
            "id": "run_125",
            "status": "completed",
            "conclusion": "success"
        })

        brick = CIPipelineBrick(
            github_client=mock_github_client,
            test_count_range=(50, 200)
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            commit_sha="abc123"
        )

        result = await brick.execute(context)

        assert result.telemetry["tests_total"] >= 50
        assert result.telemetry["tests_passed"] >= 0
        assert "duration_seconds" in result.telemetry
