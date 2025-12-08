"""Unit tests for PullRequestBrick.

Tests cover:
- PR creation with title and body
- Auto-generation of title/body from context
- Labels, assignees, and reviewers
- Draft PR support
- Base and head branch handling
- Telemetry data capture
- Error handling
- Validation requirements

Following TDD - these tests WILL FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock

from azure_haymaker.engineering_sim.bricks.base import (
    BrickContext,
    BrickResult,
    BrickExecutionError,
)
from azure_haymaker.engineering_sim.bricks.pull_request import PullRequestBrick


class TestPullRequestBrickInitialization:
    """Test PullRequestBrick initialization."""

    def test_pr_brick_minimal_initialization(self, mock_github_client):
        """Test PullRequestBrick with minimal parameters."""
        brick = PullRequestBrick(github_client=mock_github_client)

        assert brick.github_client == mock_github_client
        assert brick.title is None
        assert brick.body is None
        assert brick.head_branch is None
        assert brick.base_branch == "main"
        assert brick.labels == []
        assert brick.assignees == []
        assert brick.reviewers == []
        assert brick.draft is False

    def test_pr_brick_full_initialization(self, mock_github_client):
        """Test PullRequestBrick with all parameters."""
        brick = PullRequestBrick(
            github_client=mock_github_client,
            title="Add OAuth2 authentication",
            body="Implements OAuth2 flow",
            head_branch="feature/oauth2",
            base_branch="develop",
            labels=["enhancement", "security"],
            assignees=["developer-1"],
            reviewers=["tech-lead"],
            draft=True
        )

        assert brick.title == "Add OAuth2 authentication"
        assert brick.body == "Implements OAuth2 flow"
        assert brick.head_branch == "feature/oauth2"
        assert brick.base_branch == "develop"
        assert brick.labels == ["enhancement", "security"]
        assert brick.assignees == ["developer-1"]
        assert brick.reviewers == ["tech-lead"]
        assert brick.draft is True


class TestPullRequestBrickValidation:
    """Test PullRequestBrick validation logic."""

    def test_validate_requires_branch_name(self, mock_github_client):
        """Test validate() requires branch_name in context."""
        brick = PullRequestBrick(github_client=mock_github_client)

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )
        assert brick.validate(context) is False

    def test_validate_requires_commit_sha(self, mock_github_client):
        """Test validate() requires commit_sha in context."""
        brick = PullRequestBrick(github_client=mock_github_client)

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
            # Missing commit_sha
        )
        assert brick.validate(context) is False

    def test_validate_passes_with_branch_and_commit(self, mock_github_client):
        """Test validate() passes with branch_name and commit_sha."""
        brick = PullRequestBrick(github_client=mock_github_client)

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test",
            commit_sha="abc123"
        )
        assert brick.validate(context) is True


class TestPullRequestBrickExecution:
    """Test PullRequestBrick execute() method."""

    @pytest.mark.asyncio
    async def test_execute_creates_pull_request(self, mock_github_client):
        """Test execute() creates a pull request via GitHub API."""
        mock_github_client.create_pull_request = AsyncMock(return_value={
            "number": 142,
            "title": "Add OAuth2 authentication",
            "body": "Implements OAuth2 flow",
            "state": "open",
            "head": {"ref": "feature/oauth2"},
            "base": {"ref": "main"},
            "labels": [{"name": "enhancement"}],
            "assignees": [],
            "requested_reviewers": [{"login": "tech-lead"}],
            "draft": False,
            "created_at": "2025-12-08T10:00:00Z"
        })

        brick = PullRequestBrick(
            github_client=mock_github_client,
            title="Add OAuth2 authentication",
            body="Implements OAuth2 flow"
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/oauth2",
            commit_sha="abc123"
        )

        result = await brick.execute(context)

        assert result.success is True
        assert result.context.pr_number == 142
        mock_github_client.create_pull_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_auto_generates_title(self, mock_github_client):
        """Test execute() auto-generates title from branch name."""
        mock_github_client.create_pull_request = AsyncMock(return_value={
            "number": 143,
            "title": "Feature: OAuth2",
            "body": "",
            "state": "open",
            "head": {"ref": "feature/oauth2"},
            "base": {"ref": "main"},
            "created_at": "2025-12-08T10:00:00Z"
        })

        brick = PullRequestBrick(
            github_client=mock_github_client,
            title=None  # Should auto-generate
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/oauth2",
            commit_sha="abc123"
        )

        result = await brick.execute(context)

        assert result.success is True
        assert len(result.telemetry["title"]) > 0

    @pytest.mark.asyncio
    async def test_execute_generates_telemetry(self, mock_github_client):
        """Test execute() generates comprehensive telemetry."""
        mock_github_client.create_pull_request = AsyncMock(return_value={
            "number": 144,
            "title": "Add feature X",
            "body": "Description",
            "state": "open",
            "head": {"ref": "feature/x"},
            "base": {"ref": "main"},
            "labels": [{"name": "enhancement"}],
            "assignees": [{"login": "dev1"}],
            "requested_reviewers": [{"login": "reviewer1"}],
            "draft": False,
            "created_at": "2025-12-08T10:00:00Z"
        })

        brick = PullRequestBrick(
            github_client=mock_github_client,
            title="Add feature X",
            labels=["enhancement"],
            assignees=["dev1"],
            reviewers=["reviewer1"]
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/x",
            commit_sha="abc123"
        )

        result = await brick.execute(context)

        assert result.telemetry["brick_type"] == "pull_request"
        assert result.telemetry["pr_number"] == 144
        assert result.telemetry["title"] == "Add feature X"
        assert result.telemetry["state"] == "open"
        assert result.telemetry["head_branch"] == "feature/x"
        assert result.telemetry["base_branch"] == "main"
        assert "labels" in result.telemetry
        assert "created_at" in result.telemetry

    @pytest.mark.asyncio
    async def test_execute_creates_draft_pr(self, mock_github_client):
        """Test execute() creates draft pull request."""
        mock_github_client.create_pull_request = AsyncMock(return_value={
            "number": 145,
            "title": "WIP: Feature X",
            "state": "open",
            "draft": True,
            "created_at": "2025-12-08T10:00:00Z"
        })

        brick = PullRequestBrick(
            github_client=mock_github_client,
            title="WIP: Feature X",
            draft=True
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/x",
            commit_sha="abc123"
        )

        result = await brick.execute(context)

        assert result.success is True
        assert result.telemetry["draft"] is True

    @pytest.mark.asyncio
    async def test_execute_with_custom_base_branch(self, mock_github_client):
        """Test execute() with custom base branch."""
        mock_github_client.create_pull_request = AsyncMock(return_value={
            "number": 146,
            "title": "Feature",
            "base": {"ref": "develop"},
            "head": {"ref": "feature/x"},
            "created_at": "2025-12-08T10:00:00Z"
        })

        brick = PullRequestBrick(
            github_client=mock_github_client,
            base_branch="develop"
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/x",
            commit_sha="abc123"
        )

        result = await brick.execute(context)

        assert result.telemetry["base_branch"] == "develop"


class TestPullRequestBrickErrorHandling:
    """Test PullRequestBrick error handling."""

    @pytest.mark.asyncio
    async def test_execute_handles_pr_already_exists(self, mock_github_client):
        """Test execute() handles PR already exists error."""
        mock_github_client.create_pull_request = AsyncMock(
            side_effect=BrickExecutionError("Pull request already exists")
        )

        brick = PullRequestBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test",
            commit_sha="abc123"
        )

        with pytest.raises(BrickExecutionError):
            await brick.execute(context)

    @pytest.mark.asyncio
    async def test_execute_handles_invalid_branch(self, mock_github_client):
        """Test execute() handles invalid branch reference."""
        mock_github_client.create_pull_request = AsyncMock(
            side_effect=BrickExecutionError("Branch not found")
        )

        brick = PullRequestBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/nonexistent",
            commit_sha="abc123"
        )

        with pytest.raises(BrickExecutionError):
            await brick.execute(context)
