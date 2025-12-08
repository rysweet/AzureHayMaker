"""Unit tests for MergeBrick - PR merge simulation.

Following TDD - these tests WILL FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock

from azure_haymaker.engineering_sim.bricks.base import BrickContext, BrickResult
from azure_haymaker.engineering_sim.bricks.merge import MergeBrick


class TestMergeBrickValidation:
    """Test MergeBrick validation."""

    def test_validate_requires_pr_number_and_ci_success(self, mock_github_client):
        """Test validate() requires pr_number and successful CI."""
        brick = MergeBrick(github_client=mock_github_client)

        # Missing PR number
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )
        assert brick.validate(context) is False

        # Has PR but no CI status
        context = context.update(pr_number=142)
        assert brick.validate(context) is False

        # Has PR and successful CI
        context = context.update(metadata={"ci_status": "success"})
        assert brick.validate(context) is True


class TestMergeBrickExecution:
    """Test MergeBrick execute()."""

    @pytest.mark.asyncio
    async def test_execute_merges_pull_request(self, mock_github_client):
        """Test execute() merges PR."""
        mock_github_client.merge_pull_request = AsyncMock(return_value={
            "sha": "merge_sha_123",
            "merged": True,
            "message": "Pull request merged"
        })

        brick = MergeBrick(
            github_client=mock_github_client,
            merge_strategy="squash"
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            pr_number=142,
            metadata={"ci_status": "success"}
        )

        result = await brick.execute(context)

        assert result.success is True
        assert result.telemetry["brick_type"] == "merge"
        assert result.telemetry["pr_number"] == 142
        assert result.telemetry["merge_method"] == "squash"
        assert result.context.metadata["merged"] is True

    @pytest.mark.asyncio
    async def test_execute_with_different_strategies(self, mock_github_client):
        """Test execute() supports different merge strategies."""
        mock_github_client.merge_pull_request = AsyncMock(return_value={
            "sha": "merge_sha",
            "merged": True
        })

        for strategy in ["squash", "merge", "rebase"]:
            brick = MergeBrick(
                github_client=mock_github_client,
                merge_strategy=strategy
            )

            context = BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api",
                pr_number=142,
                metadata={"ci_status": "success"}
            )

            result = await brick.execute(context)

            assert result.success is True
            assert result.telemetry["merge_method"] == strategy
