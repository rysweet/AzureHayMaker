"""Unit tests for ReviewBrick - Code review simulation.

Following TDD - these tests WILL FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock

from azure_haymaker.engineering_sim.bricks.base import BrickContext, BrickResult
from azure_haymaker.engineering_sim.bricks.review import ReviewBrick


class TestReviewBrickValidation:
    """Test ReviewBrick validation."""

    def test_validate_requires_pr_number(self, mock_github_client):
        """Test validate() requires pr_number in context."""
        brick = ReviewBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )
        assert brick.validate(context) is False

    def test_validate_passes_with_pr_number(self, mock_github_client):
        """Test validate() passes with pr_number set."""
        brick = ReviewBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            pr_number=142
        )
        assert brick.validate(context) is True


class TestReviewBrickExecution:
    """Test ReviewBrick execute()."""

    @pytest.mark.asyncio
    async def test_execute_creates_review(self, mock_github_client):
        """Test execute() creates code review."""
        mock_github_client.create_review = AsyncMock(return_value={
            "id": 1,
            "user": {"login": "tech-lead"},
            "state": "APPROVED",
            "body": "LGTM!",
            "submitted_at": "2025-12-08T11:00:00Z"
        })

        brick = ReviewBrick(
            github_client=mock_github_client,
            reviewer_name="tech-lead",
            review_type="APPROVE"
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            pr_number=142
        )

        result = await brick.execute(context)

        assert result.success is True
        assert result.telemetry["brick_type"] == "review"
        assert result.telemetry["review_id"] == 1
        assert result.telemetry["state"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_execute_with_line_comments(self, mock_github_client):
        """Test execute() with line-specific comments."""
        mock_github_client.create_review = AsyncMock(return_value={
            "id": 2,
            "user": {"login": "reviewer"},
            "state": "COMMENT",
            "submitted_at": "2025-12-08T11:00:00Z"
        })

        brick = ReviewBrick(
            github_client=mock_github_client,
            review_type="COMMENT",
            line_comments=[
                {"path": "src/auth.py", "line": 42, "body": "Consider using constant"}
            ]
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            pr_number=142
        )

        result = await brick.execute(context)

        assert result.success is True
        assert result.telemetry["line_comments_count"] >= 1

    @pytest.mark.asyncio
    async def test_execute_request_changes(self, mock_github_client):
        """Test execute() with REQUEST_CHANGES review type."""
        mock_github_client.create_review = AsyncMock(return_value={
            "id": 3,
            "user": {"login": "reviewer"},
            "state": "CHANGES_REQUESTED",
            "body": "Please address these issues",
            "submitted_at": "2025-12-08T11:00:00Z"
        })

        brick = ReviewBrick(
            github_client=mock_github_client,
            review_type="REQUEST_CHANGES",
            comments=["Fix the bug in line 42", "Add error handling"]
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            pr_number=142
        )

        result = await brick.execute(context)

        assert result.success is True
        assert result.telemetry["state"] == "CHANGES_REQUESTED"
