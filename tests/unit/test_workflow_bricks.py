"""Tests for Workflow Bricks - Software Engineering Team Simulation.

Following TDD approach: These tests define the expected behavior
of the workflow bricks module before implementation.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# These imports will fail until implementation exists
from azure_haymaker.workflow_bricks import (
    BrickContext,
    BrickResult,
    BrickStatus,
    CIPipelineBrick,
    CodeReviewBrick,
    CommitBrick,
    GitHubClient,
    MergeBrick,
    PullRequestBrick,
    Workflow,
)
from azure_haymaker.workflow_bricks.exceptions import (
    BrickValidationError,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_github_client() -> MagicMock:
    """Create a mock GitHub client for testing."""
    client = MagicMock(spec=GitHubClient)
    client.create_commit = AsyncMock(return_value={"sha": "abc123def456"})
    client.create_pull_request = AsyncMock(
        return_value={"number": 42, "html_url": "https://github.com/owner/repo/pull/42"}
    )
    client.create_review = AsyncMock(return_value={"id": 123})
    client.trigger_workflow = AsyncMock(return_value={"id": 456, "status": "queued"})
    client.get_workflow_runs = AsyncMock(
        return_value={
            "workflow_runs": [{"id": 456, "status": "completed", "conclusion": "success"}]
        }
    )
    client.merge_pull_request = AsyncMock(return_value={"sha": "merged123"})
    client.delete_branch = AsyncMock(return_value=True)
    client.get_pull_request = AsyncMock(return_value={"head": {"ref": "feat/test-feature"}})
    return client


@pytest.fixture
def brick_context(mock_github_client: MagicMock) -> BrickContext:
    """Create a standard BrickContext for testing."""
    return BrickContext(
        tenant_id="test-tenant-001",
        team_id="engineering-team-alpha",
        repo_owner="test-org",
        repo_name="test-repo",
        branch_name="feat/test-feature",
        actor="alice@example.com",
        github_token="ghp_test_token",
        dry_run=False,
        metadata={},
        github_client=mock_github_client,
    )


@pytest.fixture
def dry_run_context(brick_context: BrickContext) -> BrickContext:
    """Create a dry-run context for simulation testing."""
    return BrickContext(
        tenant_id=brick_context.tenant_id,
        team_id=brick_context.team_id,
        repo_owner=brick_context.repo_owner,
        repo_name=brick_context.repo_name,
        branch_name=brick_context.branch_name,
        actor=brick_context.actor,
        github_token=brick_context.github_token,
        dry_run=True,
        metadata={},
        github_client=brick_context.github_client,
    )


# =============================================================================
# UNIT TESTS: BrickContext and BrickResult (60%)
# =============================================================================


class TestBrickContext:
    """Unit tests for BrickContext model."""

    def test_create_context_with_required_fields(self) -> None:
        """BrickContext should accept all required fields."""
        context = BrickContext(
            tenant_id="tenant-1",
            team_id="team-1",
            repo_owner="owner",
            repo_name="repo",
            branch_name="main",
            actor="user@example.com",
            github_token="token123",
        )

        assert context.tenant_id == "tenant-1"
        assert context.team_id == "team-1"
        assert context.repo_owner == "owner"
        assert context.repo_name == "repo"
        assert context.branch_name == "main"
        assert context.actor == "user@example.com"
        assert context.github_token == "token123"
        assert context.dry_run is False  # default
        assert context.metadata == {}  # default

    def test_context_dry_run_mode(self) -> None:
        """BrickContext should support dry_run mode."""
        context = BrickContext(
            tenant_id="tenant-1",
            team_id="team-1",
            repo_owner="owner",
            repo_name="repo",
            branch_name="main",
            actor="user@example.com",
            github_token="token123",
            dry_run=True,
        )

        assert context.dry_run is True

    def test_context_metadata_storage(self) -> None:
        """BrickContext should store and pass metadata between bricks."""
        context = BrickContext(
            tenant_id="tenant-1",
            team_id="team-1",
            repo_owner="owner",
            repo_name="repo",
            branch_name="main",
            actor="user@example.com",
            github_token="token123",
            metadata={"pr_number": 42, "commit_sha": "abc123"},
        )

        assert context.metadata["pr_number"] == 42
        assert context.metadata["commit_sha"] == "abc123"


class TestBrickResult:
    """Unit tests for BrickResult model."""

    def test_create_success_result(self) -> None:
        """BrickResult should represent successful execution."""
        result = BrickResult(
            status=BrickStatus.SUCCESS,
            brick_name="CommitBrick",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            outputs={"commit_sha": "abc123"},
        )

        assert result.status == BrickStatus.SUCCESS
        assert result.brick_name == "CommitBrick"
        assert result.outputs["commit_sha"] == "abc123"
        assert result.error is None

    def test_create_failed_result(self) -> None:
        """BrickResult should capture failure information."""
        result = BrickResult(
            status=BrickStatus.FAILED,
            brick_name="CommitBrick",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            outputs={},
            error="API rate limit exceeded",
        )

        assert result.status == BrickStatus.FAILED
        assert result.error == "API rate limit exceeded"

    def test_create_skipped_result(self) -> None:
        """BrickResult should support skipped status."""
        result = BrickResult(
            status=BrickStatus.SKIPPED,
            brick_name="MergeBrick",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            outputs={},
            error="PR not approved yet",
        )

        assert result.status == BrickStatus.SKIPPED

    def test_result_duration_calculation(self) -> None:
        """BrickResult should calculate execution duration."""
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)

        result = BrickResult(
            status=BrickStatus.SUCCESS,
            brick_name="CIPipelineBrick",
            started_at=start,
            ended_at=end,
            outputs={},
        )

        assert result.duration_seconds == 30


class TestBrickStatus:
    """Unit tests for BrickStatus enum."""

    def test_status_values(self) -> None:
        """BrickStatus should have expected values."""
        assert BrickStatus.SUCCESS.value == "success"
        assert BrickStatus.FAILED.value == "failed"
        assert BrickStatus.SKIPPED.value == "skipped"
        assert BrickStatus.PENDING.value == "pending"


# =============================================================================
# UNIT TESTS: CommitBrick (60%)
# =============================================================================


class TestCommitBrick:
    """Unit tests for CommitBrick."""

    @pytest.mark.asyncio
    async def test_validate_with_valid_context(self, brick_context: BrickContext) -> None:
        """CommitBrick should validate successfully with valid context."""
        brick = CommitBrick(
            message="feat: Add new feature",
            files=["src/feature.py"],
            author_name="Alice Developer",
            author_email="alice@example.com",
        )

        is_valid = await brick.validate(brick_context)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_fails_without_files(self, brick_context: BrickContext) -> None:
        """CommitBrick should fail validation without files."""
        brick = CommitBrick(
            message="feat: Empty commit",
            files=[],
            author_name="Alice Developer",
            author_email="alice@example.com",
        )

        with pytest.raises(BrickValidationError, match="No files specified"):
            await brick.validate(brick_context)

    @pytest.mark.asyncio
    async def test_validate_fails_without_message(self, brick_context: BrickContext) -> None:
        """CommitBrick should fail validation without message."""
        brick = CommitBrick(
            message="",
            files=["src/feature.py"],
            author_name="Alice Developer",
            author_email="alice@example.com",
        )

        with pytest.raises(BrickValidationError, match="Commit message required"):
            await brick.validate(brick_context)

    @pytest.mark.asyncio
    async def test_execute_creates_commit(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """CommitBrick should create a commit via GitHub API."""
        brick = CommitBrick(
            message="feat: Add authentication",
            files=["src/auth.py", "tests/test_auth.py"],
            author_name="Alice Developer",
            author_email="alice@example.com",
        )

        result = await brick.execute(brick_context)

        assert result.status == BrickStatus.SUCCESS
        assert result.brick_name == "CommitBrick"
        assert "commit_sha" in result.outputs
        mock_github_client.create_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_dry_run_no_api_call(
        self,
        dry_run_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """CommitBrick should simulate without API calls in dry_run mode."""
        brick = CommitBrick(
            message="feat: Test feature",
            files=["src/feature.py"],
            author_name="Alice Developer",
            author_email="alice@example.com",
        )

        result = await brick.execute(dry_run_context)

        assert result.status == BrickStatus.SUCCESS
        assert "commit_sha" in result.outputs
        assert result.outputs["commit_sha"].startswith("dry_run_")
        mock_github_client.create_commit.assert_not_called()


# =============================================================================
# UNIT TESTS: PullRequestBrick (60%)
# =============================================================================


class TestPullRequestBrick:
    """Unit tests for PullRequestBrick."""

    @pytest.mark.asyncio
    async def test_validate_with_valid_context(self, brick_context: BrickContext) -> None:
        """PullRequestBrick should validate successfully with valid context."""
        brick = PullRequestBrick(
            title="feat: Add new feature",
            body="Implements the new feature",
            base_branch="main",
            head_branch="feat/new-feature",
        )

        is_valid = await brick.validate(brick_context)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_fails_without_title(self, brick_context: BrickContext) -> None:
        """PullRequestBrick should fail validation without title."""
        brick = PullRequestBrick(
            title="",
            body="Description",
            base_branch="main",
            head_branch="feat/test",
        )

        with pytest.raises(BrickValidationError, match="PR title required"):
            await brick.validate(brick_context)

    @pytest.mark.asyncio
    async def test_execute_creates_pr(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """PullRequestBrick should create a PR via GitHub API."""
        brick = PullRequestBrick(
            title="feat: Add authentication",
            body="Implements user authentication",
            base_branch="main",
            head_branch="feat/auth",
            labels=["enhancement"],
            reviewers=["bob"],
        )

        result = await brick.execute(brick_context)

        assert result.status == BrickStatus.SUCCESS
        assert result.brick_name == "PullRequestBrick"
        assert result.outputs["pr_number"] == 42
        assert "pr_url" in result.outputs
        mock_github_client.create_pull_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_stores_pr_number_in_metadata(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """PullRequestBrick should store PR number for downstream bricks."""
        brick = PullRequestBrick(
            title="feat: Test",
            body="Test PR",
            base_branch="main",
            head_branch="feat/test",
        )

        await brick.execute(brick_context)

        # The brick should update the context metadata
        assert brick_context.metadata.get("pr_number") == 42


# =============================================================================
# UNIT TESTS: CodeReviewBrick (60%)
# =============================================================================


class TestCodeReviewBrick:
    """Unit tests for CodeReviewBrick."""

    @pytest.mark.asyncio
    async def test_validate_with_pr_number(self, brick_context: BrickContext) -> None:
        """CodeReviewBrick should validate with explicit PR number."""
        brick = CodeReviewBrick(
            pr_number=42,
            reviewer="bob",
            action="approve",
        )

        is_valid = await brick.validate(brick_context)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_uses_metadata_pr_number(self, brick_context: BrickContext) -> None:
        """CodeReviewBrick should use PR number from context metadata."""
        brick_context.metadata["pr_number"] = 99
        brick = CodeReviewBrick(
            pr_number=None,  # Will use metadata
            reviewer="bob",
            action="approve",
        )

        is_valid = await brick.validate(brick_context)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_fails_without_pr_number(self, brick_context: BrickContext) -> None:
        """CodeReviewBrick should fail without PR number."""
        brick = CodeReviewBrick(
            pr_number=None,
            reviewer="bob",
            action="approve",
        )

        with pytest.raises(BrickValidationError, match="PR number required"):
            await brick.validate(brick_context)

    @pytest.mark.asyncio
    async def test_execute_approve_review(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """CodeReviewBrick should create an approval review."""
        brick = CodeReviewBrick(
            pr_number=42,
            reviewer="bob",
            action="approve",
            body="LGTM!",
        )

        result = await brick.execute(brick_context)

        assert result.status == BrickStatus.SUCCESS
        assert result.outputs["review_id"] == 123
        mock_github_client.create_review.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_request_changes_review(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """CodeReviewBrick should create a request-changes review."""
        brick = CodeReviewBrick(
            pr_number=42,
            reviewer="carol",
            action="request_changes",
            body="Please fix the tests",
            comments=[
                {"path": "src/auth.py", "line": 15, "body": "Use bcrypt here"},
            ],
        )

        result = await brick.execute(brick_context)

        assert result.status == BrickStatus.SUCCESS
        mock_github_client.create_review.assert_called_once()


# =============================================================================
# UNIT TESTS: CIPipelineBrick (60%)
# =============================================================================


class TestCIPipelineBrick:
    """Unit tests for CIPipelineBrick."""

    @pytest.mark.asyncio
    async def test_validate_with_workflow_name(self, brick_context: BrickContext) -> None:
        """CIPipelineBrick should validate with workflow name."""
        brick = CIPipelineBrick(
            workflow_name="ci.yml",
            trigger_ref="refs/heads/feat/test",
        )

        is_valid = await brick.validate(brick_context)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_fails_without_workflow(self, brick_context: BrickContext) -> None:
        """CIPipelineBrick should fail without workflow name."""
        brick = CIPipelineBrick(
            workflow_name="",
            trigger_ref="refs/heads/main",
        )

        with pytest.raises(BrickValidationError, match="Workflow name required"):
            await brick.validate(brick_context)

    @pytest.mark.asyncio
    async def test_execute_triggers_workflow(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """CIPipelineBrick should trigger a workflow run."""
        brick = CIPipelineBrick(
            workflow_name="ci.yml",
            trigger_ref="refs/heads/feat/auth",
            inputs={"run_integration": "true"},
        )

        result = await brick.execute(brick_context)

        assert result.status == BrickStatus.SUCCESS
        assert result.outputs["run_id"] == 456
        mock_github_client.trigger_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_simulates_with_expected_status(
        self,
        dry_run_context: BrickContext,
    ) -> None:
        """CIPipelineBrick should simulate with expected status in dry_run."""
        brick = CIPipelineBrick(
            workflow_name="ci.yml",
            trigger_ref="refs/heads/main",
            expected_status="failure",  # Simulate failure
            duration_seconds=60,
        )

        result = await brick.execute(dry_run_context)

        assert result.status == BrickStatus.SUCCESS  # Brick succeeded
        assert result.outputs["workflow_status"] == "failure"  # But simulated failure


# =============================================================================
# UNIT TESTS: MergeBrick (60%)
# =============================================================================


class TestMergeBrick:
    """Unit tests for MergeBrick."""

    @pytest.mark.asyncio
    async def test_validate_with_pr_number(self, brick_context: BrickContext) -> None:
        """MergeBrick should validate with PR number."""
        brick = MergeBrick(
            pr_number=42,
            merge_method="squash",
        )

        is_valid = await brick.validate(brick_context)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_uses_metadata_pr_number(self, brick_context: BrickContext) -> None:
        """MergeBrick should use PR number from context metadata."""
        brick_context.metadata["pr_number"] = 99
        brick = MergeBrick(
            pr_number=None,
            merge_method="merge",
        )

        is_valid = await brick.validate(brick_context)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_execute_merges_pr(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """MergeBrick should merge the PR."""
        brick = MergeBrick(
            pr_number=42,
            merge_method="squash",
            delete_branch=False,
        )

        result = await brick.execute(brick_context)

        assert result.status == BrickStatus.SUCCESS
        assert result.outputs["merge_sha"] == "merged123"
        mock_github_client.merge_pull_request.assert_called_once()
        mock_github_client.delete_branch.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_merges_and_deletes_branch(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """MergeBrick should optionally delete the branch after merge."""
        brick = MergeBrick(
            pr_number=42,
            merge_method="squash",
            delete_branch=True,
        )

        result = await brick.execute(brick_context)

        assert result.status == BrickStatus.SUCCESS
        mock_github_client.merge_pull_request.assert_called_once()
        mock_github_client.delete_branch.assert_called_once()


# =============================================================================
# INTEGRATION TESTS: Workflow Composition (30%)
# =============================================================================


class TestWorkflowComposition:
    """Integration tests for Workflow composition."""

    @pytest.mark.asyncio
    async def test_simple_workflow_execution(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """Workflow should execute multiple bricks in sequence."""
        workflow = Workflow(
            name="simple-feature",
            steps=[
                CommitBrick(
                    message="feat: Initial",
                    files=["src/feature.py"],
                    author_name="Alice",
                    author_email="alice@example.com",
                ),
                PullRequestBrick(
                    title="feat: New feature",
                    body="Description",
                    base_branch="main",
                    head_branch="feat/test",
                ),
            ],
        )

        results = await workflow.execute(brick_context)

        assert len(results) == 2
        assert all(r.status == BrickStatus.SUCCESS for r in results)

    @pytest.mark.asyncio
    async def test_workflow_passes_context_between_bricks(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """Workflow should pass metadata between bricks."""
        workflow = Workflow(
            name="feature-with-review",
            steps=[
                PullRequestBrick(
                    title="feat: Feature",
                    body="Desc",
                    base_branch="main",
                    head_branch="feat/test",
                ),
                CodeReviewBrick(
                    pr_number=None,  # Will use metadata from PR brick
                    reviewer="bob",
                    action="approve",
                ),
            ],
        )

        results = await workflow.execute(brick_context)

        assert len(results) == 2
        assert results[1].status == BrickStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_workflow_stops_on_failure(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """Workflow should stop execution when a brick fails."""
        mock_github_client.create_commit.side_effect = Exception("API Error")

        workflow = Workflow(
            name="failing-workflow",
            steps=[
                CommitBrick(
                    message="feat: Fail",
                    files=["src/fail.py"],
                    author_name="Alice",
                    author_email="alice@example.com",
                ),
                PullRequestBrick(
                    title="Never reached",
                    body="This should not execute",
                    base_branch="main",
                    head_branch="feat/fail",
                ),
            ],
        )

        results = await workflow.execute(brick_context)

        assert len(results) == 1
        assert results[0].status == BrickStatus.FAILED

    @pytest.mark.asyncio
    async def test_full_feature_workflow(
        self,
        brick_context: BrickContext,
        mock_github_client: MagicMock,
    ) -> None:
        """Integration test for complete feature development workflow."""
        workflow = Workflow(
            name="complete-feature",
            steps=[
                CommitBrick(
                    message="feat: Add user authentication",
                    files=["src/auth.py", "tests/test_auth.py"],
                    author_name="Alice Developer",
                    author_email="alice@example.com",
                ),
                PullRequestBrick(
                    title="feat: Add user authentication",
                    body="Implements login and registration",
                    base_branch="main",
                    head_branch="feat/auth",
                    labels=["enhancement"],
                    reviewers=["bob"],
                ),
                CodeReviewBrick(
                    pr_number=None,
                    reviewer="bob",
                    action="approve",
                    body="LGTM!",
                ),
                CIPipelineBrick(
                    workflow_name="ci.yml",
                    trigger_ref="refs/heads/feat/auth",
                ),
                MergeBrick(
                    pr_number=None,
                    merge_method="squash",
                    delete_branch=True,
                ),
            ],
        )

        results = await workflow.execute(brick_context)

        assert len(results) == 5
        assert all(r.status == BrickStatus.SUCCESS for r in results)
        # Verify all API calls were made
        mock_github_client.create_commit.assert_called_once()
        mock_github_client.create_pull_request.assert_called_once()
        mock_github_client.create_review.assert_called_once()
        mock_github_client.trigger_workflow.assert_called_once()
        mock_github_client.merge_pull_request.assert_called_once()
        mock_github_client.delete_branch.assert_called_once()


# =============================================================================
# E2E TESTS: GitHubClient (10%)
# =============================================================================


class TestGitHubClient:
    """Unit tests for GitHubClient."""

    def test_client_initialization(self) -> None:
        """GitHubClient should initialize with token."""
        client = GitHubClient(token="ghp_test_token")
        assert client.token == "ghp_test_token"

    def test_client_repo_url_construction(self) -> None:
        """GitHubClient should construct correct API URLs."""
        client = GitHubClient(token="ghp_test_token")
        url = client.get_repo_url("owner", "repo")
        assert url == "https://api.github.com/repos/owner/repo"

    @pytest.mark.asyncio
    async def test_client_handles_rate_limit(self) -> None:
        """GitHubClient should handle rate limiting gracefully."""
        client = GitHubClient(token="ghp_test_token")
        # This test would use real HTTP mocking in implementation
        # For now, just verify the method exists
        assert hasattr(client, "handle_rate_limit")
