"""Tests for github_client module.

Comprehensive unit tests for GitHub API client operations including:
- Client initialization
- Repository operations
- Commit and tree management
- Pull request creation and management
- Review operations
- Workflow dispatch
- Rate limit handling
- Error handling
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from azure_haymaker.workflow_bricks.clients.github_client import GitHubClient

if TYPE_CHECKING:
    pass


# =============================================================================
# UNIT TESTS - Client Initialization
# =============================================================================


class TestGitHubClientInit:
    """Tests for GitHubClient initialization."""

    def test_init_defaults(self) -> None:
        """Test client initialization with default values."""
        client = GitHubClient(token="ghp_testtoken")

        assert client.token == "ghp_testtoken"
        assert client.base_url == "https://api.github.com"
        assert client.timeout == 30.0
        assert client._rate_limit_remaining is None
        assert client._rate_limit_reset is None

    def test_init_custom_values(self) -> None:
        """Test client initialization with custom values."""
        client = GitHubClient(
            token="ghp_testtoken",
            base_url="https://github.example.com/api/v3/",
            timeout=60.0,
        )

        assert client.token == "ghp_testtoken"
        assert client.base_url == "https://github.example.com/api/v3"  # trailing slash stripped
        assert client.timeout == 60.0

    def test_get_headers(self) -> None:
        """Test authentication headers generation."""
        client = GitHubClient(token="ghp_testtoken")
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer ghp_testtoken"
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    def test_get_repo_url(self) -> None:
        """Test repository URL generation."""
        client = GitHubClient(token="ghp_test")
        url = client.get_repo_url("octocat", "hello-world")

        assert url == "https://api.github.com/repos/octocat/hello-world"


# =============================================================================
# UNIT TESTS - Rate Limit Handling
# =============================================================================


class TestRateLimitHandling:
    """Tests for rate limit handling."""

    @pytest.mark.asyncio
    async def test_handle_rate_limit_normal(self) -> None:
        """Test rate limit handling with remaining requests."""
        client = GitHubClient(token="ghp_test")
        response = MagicMock()
        response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1234567890",
        }

        await client.handle_rate_limit(response)

        assert client._rate_limit_remaining == 4999
        assert client._rate_limit_reset == 1234567890

    @pytest.mark.asyncio
    async def test_handle_rate_limit_exhausted(self) -> None:
        """Test rate limit handling when limit is exhausted."""
        client = GitHubClient(token="ghp_test")

        # Set reset time to be in the past to avoid actual sleep
        import time

        past_reset = int(time.time()) - 10

        response = MagicMock()
        response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(past_reset),
        }

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client.handle_rate_limit(response)
            # Sleep should be called with 1 second (max(0, past-now) + 1)
            mock_sleep.assert_called_once()


# =============================================================================
# UNIT TESTS - HTTP Request
# =============================================================================


class TestHttpRequest:
    """Tests for internal HTTP request handling."""

    @pytest.fixture
    def mock_httpx_client(self) -> MagicMock:
        """Create mock httpx client."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1234567890",
        }
        mock_response.json.return_value = {"sha": "abc123"}
        mock_response.raise_for_status = MagicMock()
        return mock_response

    @pytest.mark.asyncio
    async def test_request_success(self, mock_httpx_client: MagicMock) -> None:
        """Test successful HTTP request."""
        client = GitHubClient(token="ghp_test")

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.request.return_value = mock_httpx_client
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance

            result = await client._request("GET", "/repos/test/repo")

            assert result == {"sha": "abc123"}
            mock_client_instance.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_no_content(self) -> None:
        """Test request returns empty dict for 204 response."""
        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1234567890",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.request.return_value = mock_response
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance

            result = await client._request("DELETE", "/repos/test/repo/ref")

            assert result == {}

    @pytest.mark.asyncio
    async def test_request_http_error(self) -> None:
        """Test HTTP errors are propagated."""
        client = GitHubClient(token="ghp_test")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1234567890",
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.request.return_value = mock_response
            mock_async_client.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(httpx.HTTPStatusError):
                await client._request("GET", "/repos/nonexistent/repo")


# =============================================================================
# UNIT TESTS - Commit Operations
# =============================================================================


class TestCommitOperations:
    """Tests for commit-related operations."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create client for testing."""
        return GitHubClient(token="ghp_test")

    @pytest.mark.asyncio
    async def test_create_commit_basic(self, client: GitHubClient) -> None:
        """Test basic commit creation."""
        expected_response = {
            "sha": "commit123",
            "message": "Test commit",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.create_commit(
                owner="octocat",
                repo="hello-world",
                message="Test commit",
                tree_sha="tree123",
                parent_sha="parent123",
            )

            assert result["sha"] == "commit123"
            mock_request.assert_called_once_with(
                "POST",
                "/repos/octocat/hello-world/git/commits",
                json={
                    "message": "Test commit",
                    "tree": "tree123",
                    "parents": ["parent123"],
                },
            )

    @pytest.mark.asyncio
    async def test_create_commit_with_author(self, client: GitHubClient) -> None:
        """Test commit creation with author info."""
        expected_response = {"sha": "commit123"}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            await client.create_commit(
                owner="octocat",
                repo="hello-world",
                message="Test commit",
                tree_sha="tree123",
                parent_sha="parent123",
                author_name="Test User",
                author_email="test@example.com",
            )

            call_args = mock_request.call_args
            assert call_args[1]["json"]["author"]["name"] == "Test User"
            assert call_args[1]["json"]["author"]["email"] == "test@example.com"


# =============================================================================
# UNIT TESTS - Reference Operations
# =============================================================================


class TestReferenceOperations:
    """Tests for git reference operations."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create client for testing."""
        return GitHubClient(token="ghp_test")

    @pytest.mark.asyncio
    async def test_get_ref(self, client: GitHubClient) -> None:
        """Test getting a git reference."""
        expected_response = {
            "ref": "refs/heads/main",
            "object": {"sha": "abc123"},
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.get_ref("octocat", "hello-world", "heads/main")

            assert result["object"]["sha"] == "abc123"
            mock_request.assert_called_once_with(
                "GET",
                "/repos/octocat/hello-world/git/ref/heads/main",
            )

    @pytest.mark.asyncio
    async def test_update_ref(self, client: GitHubClient) -> None:
        """Test updating a git reference."""
        expected_response = {"ref": "refs/heads/main", "object": {"sha": "new123"}}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.update_ref(
                owner="octocat",
                repo="hello-world",
                ref="heads/main",
                sha="new123",
                force=True,
            )

            assert result["object"]["sha"] == "new123"
            mock_request.assert_called_once_with(
                "PATCH",
                "/repos/octocat/hello-world/git/refs/heads/main",
                json={"sha": "new123", "force": True},
            )


# =============================================================================
# UNIT TESTS - Tree and Blob Operations
# =============================================================================


class TestTreeBlobOperations:
    """Tests for tree and blob operations."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create client for testing."""
        return GitHubClient(token="ghp_test")

    @pytest.mark.asyncio
    async def test_create_tree(self, client: GitHubClient) -> None:
        """Test creating a git tree."""
        tree_entries = [
            {
                "path": "README.md",
                "mode": "100644",
                "type": "blob",
                "sha": "blob123",
            }
        ]
        expected_response = {"sha": "tree123"}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.create_tree(
                owner="octocat",
                repo="hello-world",
                base_tree="base123",
                tree=tree_entries,
            )

            assert result["sha"] == "tree123"

    @pytest.mark.asyncio
    async def test_get_blob(self, client: GitHubClient) -> None:
        """Test getting a blob."""
        expected_response = {
            "sha": "blob123",
            "content": "SGVsbG8gV29ybGQh",  # base64 encoded
            "encoding": "base64",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.get_blob(
                owner="octocat",
                repo="hello-world",
                file_sha="blob123",
            )

            assert result["sha"] == "blob123"
            assert result["content"] == "SGVsbG8gV29ybGQh"

    @pytest.mark.asyncio
    async def test_create_blob(self, client: GitHubClient) -> None:
        """Test creating a blob."""
        expected_response = {"sha": "newblob123"}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.create_blob(
                owner="octocat",
                repo="hello-world",
                content="Hello World!",
                encoding="utf-8",
            )

            assert result["sha"] == "newblob123"
            mock_request.assert_called_once_with(
                "POST",
                "/repos/octocat/hello-world/git/blobs",
                json={"content": "Hello World!", "encoding": "utf-8"},
            )


# =============================================================================
# UNIT TESTS - Pull Request Operations
# =============================================================================


class TestPullRequestOperations:
    """Tests for pull request operations."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create client for testing."""
        return GitHubClient(token="ghp_test")

    @pytest.mark.asyncio
    async def test_create_pull_request(self, client: GitHubClient) -> None:
        """Test creating a pull request."""
        expected_response = {
            "number": 42,
            "html_url": "https://github.com/octocat/hello-world/pull/42",
            "state": "open",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.create_pull_request(
                owner="octocat",
                repo="hello-world",
                title="Add feature",
                body="This PR adds a new feature.",
                head="feature-branch",
                base="main",
                draft=False,
            )

            assert result["number"] == 42
            mock_request.assert_called_once_with(
                "POST",
                "/repos/octocat/hello-world/pulls",
                json={
                    "title": "Add feature",
                    "body": "This PR adds a new feature.",
                    "head": "feature-branch",
                    "base": "main",
                    "draft": False,
                },
            )

    @pytest.mark.asyncio
    async def test_create_pull_request_draft(self, client: GitHubClient) -> None:
        """Test creating a draft pull request."""
        expected_response = {"number": 43, "draft": True}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.create_pull_request(
                owner="octocat",
                repo="hello-world",
                title="WIP: Feature",
                body="Work in progress",
                head="wip-branch",
                base="main",
                draft=True,
            )

            assert result["draft"] is True

    @pytest.mark.asyncio
    async def test_get_pull_request(self, client: GitHubClient) -> None:
        """Test getting a pull request."""
        expected_response = {
            "number": 42,
            "title": "Add feature",
            "state": "open",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.get_pull_request(
                owner="octocat",
                repo="hello-world",
                pull_number=42,
            )

            assert result["number"] == 42
            mock_request.assert_called_once_with(
                "GET",
                "/repos/octocat/hello-world/pulls/42",
            )

    @pytest.mark.asyncio
    async def test_merge_pull_request(self, client: GitHubClient) -> None:
        """Test merging a pull request."""
        expected_response = {
            "sha": "merge123",
            "merged": True,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.merge_pull_request(
                owner="octocat",
                repo="hello-world",
                pull_number=42,
                merge_method="squash",
                commit_title="feat: Add feature (#42)",
                commit_message="Detailed description",
            )

            assert result["merged"] is True
            mock_request.assert_called_once_with(
                "PUT",
                "/repos/octocat/hello-world/pulls/42/merge",
                json={
                    "merge_method": "squash",
                    "commit_title": "feat: Add feature (#42)",
                    "commit_message": "Detailed description",
                },
            )


# =============================================================================
# UNIT TESTS - Label Operations
# =============================================================================


class TestLabelOperations:
    """Tests for label operations."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create client for testing."""
        return GitHubClient(token="ghp_test")

    @pytest.mark.asyncio
    async def test_add_labels(self, client: GitHubClient) -> None:
        """Test adding labels to an issue/PR."""
        expected_response = [
            {"name": "bug", "color": "d73a4a"},
            {"name": "enhancement", "color": "a2eeef"},
        ]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.add_labels(
                owner="octocat",
                repo="hello-world",
                issue_number=42,
                labels=["bug", "enhancement"],
            )

            assert len(result) == 2
            mock_request.assert_called_once_with(
                "POST",
                "/repos/octocat/hello-world/issues/42/labels",
                json={"labels": ["bug", "enhancement"]},
            )


# =============================================================================
# UNIT TESTS - Review Operations
# =============================================================================


class TestReviewOperations:
    """Tests for pull request review operations."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create client for testing."""
        return GitHubClient(token="ghp_test")

    @pytest.mark.asyncio
    async def test_request_reviewers(self, client: GitHubClient) -> None:
        """Test requesting reviewers."""
        expected_response = {
            "requested_reviewers": [{"login": "reviewer1"}, {"login": "reviewer2"}]
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.request_reviewers(
                owner="octocat",
                repo="hello-world",
                pull_number=42,
                reviewers=["reviewer1", "reviewer2"],
            )

            assert len(result["requested_reviewers"]) == 2

    @pytest.mark.asyncio
    async def test_create_review_approve(self, client: GitHubClient) -> None:
        """Test creating an approval review."""
        expected_response = {"id": 12345, "state": "APPROVED"}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.create_review(
                owner="octocat",
                repo="hello-world",
                pull_number=42,
                body="LGTM!",
                event="APPROVE",
            )

            assert result["state"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_create_review_with_comments(self, client: GitHubClient) -> None:
        """Test creating a review with line comments."""
        comments = [
            {
                "path": "src/main.py",
                "position": 10,
                "body": "Consider using a constant here.",
            }
        ]
        expected_response = {"id": 12346, "state": "COMMENTED"}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            await client.create_review(
                owner="octocat",
                repo="hello-world",
                pull_number=42,
                body="Some suggestions",
                event="COMMENT",
                comments=comments,
            )

            call_args = mock_request.call_args[1]["json"]
            assert call_args["comments"] == comments


# =============================================================================
# UNIT TESTS - Workflow Operations
# =============================================================================


class TestWorkflowOperations:
    """Tests for GitHub Actions workflow operations."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create client for testing."""
        return GitHubClient(token="ghp_test")

    @pytest.mark.asyncio
    async def test_trigger_workflow(self, client: GitHubClient) -> None:
        """Test triggering a workflow dispatch."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}  # 204 response

            result = await client.trigger_workflow(
                owner="octocat",
                repo="hello-world",
                workflow_id="ci.yml",
                ref="main",
                inputs={"environment": "production"},
            )

            assert result["status"] == "queued"
            assert result["workflow_id"] == "ci.yml"
            mock_request.assert_called_once_with(
                "POST",
                "/repos/octocat/hello-world/actions/workflows/ci.yml/dispatches",
                json={"ref": "main", "inputs": {"environment": "production"}},
            )

    @pytest.mark.asyncio
    async def test_trigger_workflow_no_inputs(self, client: GitHubClient) -> None:
        """Test triggering workflow without inputs."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}

            await client.trigger_workflow(
                owner="octocat",
                repo="hello-world",
                workflow_id="ci.yml",
                ref="main",
            )

            call_args = mock_request.call_args[1]["json"]
            assert "inputs" not in call_args

    @pytest.mark.asyncio
    async def test_get_workflow_runs(self, client: GitHubClient) -> None:
        """Test getting workflow runs."""
        expected_response = {
            "total_count": 2,
            "workflow_runs": [
                {"id": 1, "status": "completed"},
                {"id": 2, "status": "in_progress"},
            ],
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            result = await client.get_workflow_runs(
                owner="octocat",
                repo="hello-world",
                workflow_id="ci.yml",
                branch="main",
                per_page=10,
            )

            assert len(result["workflow_runs"]) == 2

    @pytest.mark.asyncio
    async def test_get_workflow_runs_no_filter(self, client: GitHubClient) -> None:
        """Test getting all workflow runs without filters."""
        expected_response = {"workflow_runs": []}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = expected_response

            await client.get_workflow_runs(
                owner="octocat",
                repo="hello-world",
            )

            # Should use /actions/runs endpoint
            call_args = mock_request.call_args[0]
            assert "/actions/runs" in call_args[1]


# =============================================================================
# UNIT TESTS - Branch Operations
# =============================================================================


class TestBranchOperations:
    """Tests for branch operations."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        """Create client for testing."""
        return GitHubClient(token="ghp_test")

    @pytest.mark.asyncio
    async def test_delete_branch_success(self, client: GitHubClient) -> None:
        """Test successful branch deletion."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}

            result = await client.delete_branch(
                owner="octocat",
                repo="hello-world",
                branch="feature-branch",
            )

            assert result is True
            mock_request.assert_called_once_with(
                "DELETE",
                "/repos/octocat/hello-world/git/refs/heads/feature-branch",
            )

    @pytest.mark.asyncio
    async def test_delete_branch_protected(self, client: GitHubClient) -> None:
        """Test deleting a protected branch returns False."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 422
            mock_request.side_effect = httpx.HTTPStatusError(
                message="Protected branch",
                request=MagicMock(),
                response=mock_response,
            )

            result = await client.delete_branch(
                owner="octocat",
                repo="hello-world",
                branch="main",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_branch_other_error(self, client: GitHubClient) -> None:
        """Test other errors are propagated."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_request.side_effect = httpx.HTTPStatusError(
                message="Server error",
                request=MagicMock(),
                response=mock_response,
            )

            with pytest.raises(httpx.HTTPStatusError):
                await client.delete_branch(
                    owner="octocat",
                    repo="hello-world",
                    branch="feature-branch",
                )


# =============================================================================
# INTEGRATION TESTS - Full Workflows
# =============================================================================


class TestGitHubClientIntegration:
    """Integration tests for GitHub client workflows."""

    @pytest.mark.asyncio
    async def test_create_commit_and_update_ref_flow(self) -> None:
        """Test complete flow of creating a commit and updating a ref."""
        client = GitHubClient(token="ghp_test")

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            # Setup mock responses for each call
            mock_request.side_effect = [
                {"sha": "tree123"},  # create_tree
                {"sha": "commit123"},  # create_commit
                {"ref": "refs/heads/main", "object": {"sha": "commit123"}},  # update_ref
            ]

            # Create tree
            tree_result = await client.create_tree(
                owner="octocat",
                repo="hello-world",
                base_tree="base123",
                tree=[{"path": "README.md", "mode": "100644", "type": "blob", "sha": "blob123"}],
            )

            # Create commit
            commit_result = await client.create_commit(
                owner="octocat",
                repo="hello-world",
                message="Update README",
                tree_sha=tree_result["sha"],
                parent_sha="parent123",
            )

            # Update ref
            ref_result = await client.update_ref(
                owner="octocat",
                repo="hello-world",
                ref="heads/main",
                sha=commit_result["sha"],
            )

            assert ref_result["object"]["sha"] == "commit123"
            assert mock_request.call_count == 3
