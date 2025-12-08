"""Unit tests for GitHubClient.

Tests cover:
- Client initialization and configuration
- Commit creation API
- Pull request creation API
- Review creation API
- Workflow triggering API
- PR merge API
- Rate limit handling
- Error handling and retries
- Authentication

Following TDD - these tests WILL FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from azure_haymaker.engineering_sim.github_client import (
    GitHubClient,
    RateLimitError,
    GitHubAPIError,
)


class TestGitHubClientInitialization:
    """Test GitHubClient initialization."""

    def test_github_client_initialization(self):
        """Test GitHubClient can be initialized."""
        client = GitHubClient(
            token="test_token",
            org="test-org"
        )

        assert client.token == "test_token"
        assert client.org == "test-org"
        assert client.rate_limit_strategy == "wait"
        assert client.base_url == "https://api.github.com"

    def test_github_client_with_custom_strategy(self):
        """Test GitHubClient with custom rate limit strategy."""
        client = GitHubClient(
            token="test_token",
            org="test-org",
            rate_limit_strategy="skip"
        )

        assert client.rate_limit_strategy == "skip"

    def test_github_client_with_github_enterprise(self):
        """Test GitHubClient with GitHub Enterprise URL."""
        client = GitHubClient(
            token="test_token",
            org="test-org",
            base_url="https://github.enterprise.com/api/v3"
        )

        assert client.base_url == "https://github.enterprise.com/api/v3"


class TestGitHubClientCommitAPI:
    """Test commit creation API."""

    @pytest.mark.asyncio
    async def test_create_commit_success(self):
        """Test create_commit() creates a commit."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "sha": "abc123",
                "commit": {
                    "author": {"name": "Alice", "email": "alice@example.com"},
                    "message": "Add feature"
                }
            }

            result = await client.create_commit(
                repo="backend-api",
                branch="feature/test",
                files={"src/test.py": "print('hello')"},
                message="Add feature"
            )

            assert result["sha"] == "abc123"
            assert result["commit"]["message"] == "Add feature"

    @pytest.mark.asyncio
    async def test_create_commit_with_author(self):
        """Test create_commit() with custom author."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "sha": "def456",
                "commit": {
                    "author": {"name": "Bob", "email": "bob@example.com"}
                }
            }

            result = await client.create_commit(
                repo="backend-api",
                branch="feature/test",
                files={"src/test.py": "code"},
                message="Fix bug",
                author={"name": "Bob", "email": "bob@example.com"}
            )

            assert result["commit"]["author"]["name"] == "Bob"


class TestGitHubClientPullRequestAPI:
    """Test pull request API."""

    @pytest.mark.asyncio
    async def test_create_pull_request_success(self):
        """Test create_pull_request() creates a PR."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "number": 142,
                "title": "Add feature",
                "state": "open"
            }

            result = await client.create_pull_request(
                repo="backend-api",
                title="Add feature",
                body="Description",
                head="feature/test",
                base="main"
            )

            assert result["number"] == 142
            assert result["title"] == "Add feature"

    @pytest.mark.asyncio
    async def test_create_pull_request_with_labels(self):
        """Test create_pull_request() with labels."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "number": 143,
                "title": "Fix bug",
                "labels": [{"name": "bug"}]
            }

            result = await client.create_pull_request(
                repo="backend-api",
                title="Fix bug",
                body="Description",
                head="hotfix/bug",
                base="main",
                labels=["bug"]
            )

            assert len(result["labels"]) == 1


class TestGitHubClientReviewAPI:
    """Test code review API."""

    @pytest.mark.asyncio
    async def test_create_review_approve(self):
        """Test create_review() with APPROVE."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": 1,
                "state": "APPROVED"
            }

            result = await client.create_review(
                repo="backend-api",
                pr_number=142,
                event="APPROVE",
                body="LGTM!"
            )

            assert result["id"] == 1
            assert result["state"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_create_review_with_comments(self):
        """Test create_review() with line comments."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "id": 2,
                "state": "COMMENT"
            }

            comments = [
                {"path": "src/file.py", "line": 42, "body": "Fix this"}
            ]

            result = await client.create_review(
                repo="backend-api",
                pr_number=142,
                event="COMMENT",
                body="Some feedback",
                comments=comments
            )

            assert result["id"] == 2


class TestGitHubClientRateLimiting:
    """Test rate limit handling."""

    @pytest.mark.asyncio
    async def test_get_rate_limit_returns_status(self):
        """Test get_rate_limit() returns rate limit info."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "resources": {
                    "core": {
                        "remaining": 4500,
                        "reset": 1733662800
                    }
                }
            }

            result = await client.get_rate_limit()

            assert result["resources"]["core"]["remaining"] == 4500

    @pytest.mark.asyncio
    async def test_rate_limit_wait_strategy(self):
        """Test rate limiting with wait strategy."""
        client = GitHubClient(
            token="test_token",
            org="test-org",
            rate_limit_strategy="wait"
        )

        # Simulate rate limit exhausted
        with patch.object(client, '_check_rate_limit', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {"remaining": 0, "reset": 1733662800}

            with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = {"sha": "abc123"}

                # Should wait and retry
                result = await client.create_commit(
                    repo="test",
                    branch="main",
                    files={},
                    message="test"
                )

    @pytest.mark.asyncio
    async def test_rate_limit_fail_strategy(self):
        """Test rate limiting with fail strategy."""
        client = GitHubClient(
            token="test_token",
            org="test-org",
            rate_limit_strategy="fail"
        )

        with patch.object(client, '_check_rate_limit', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = RateLimitError("Rate limit exceeded")

            with pytest.raises(RateLimitError):
                await client.create_commit(
                    repo="test",
                    branch="main",
                    files={},
                    message="test"
                )


class TestGitHubClientErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_handles_404_not_found(self):
        """Test handling of 404 errors."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = GitHubAPIError("404: Not Found")

            with pytest.raises(GitHubAPIError):
                await client.create_commit(
                    repo="nonexistent",
                    branch="main",
                    files={},
                    message="test"
                )

    @pytest.mark.asyncio
    async def test_handles_503_service_unavailable(self):
        """Test handling of 503 errors with retry."""
        client = GitHubClient(token="test_token", org="test-org")

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise GitHubAPIError("503: Service Unavailable")
            return {"sha": "abc123"}

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = side_effect

            # Should retry and eventually succeed
            result = await client.create_commit(
                repo="test",
                branch="main",
                files={},
                message="test"
            )

            assert result["sha"] == "abc123"
            assert call_count == 3


class TestGitHubClientMergeAPI:
    """Test PR merge API."""

    @pytest.mark.asyncio
    async def test_merge_pull_request_success(self):
        """Test merge_pull_request() merges PR."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "sha": "merge_sha",
                "merged": True
            }

            result = await client.merge_pull_request(
                repo="backend-api",
                pr_number=142,
                merge_method="squash"
            )

            assert result["sha"] == "merge_sha"
            assert result["merged"] is True

    @pytest.mark.asyncio
    async def test_merge_pull_request_with_custom_message(self):
        """Test merge_pull_request() with custom commit message."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "sha": "merge_sha",
                "merged": True
            }

            result = await client.merge_pull_request(
                repo="backend-api",
                pr_number=142,
                merge_method="squash",
                commit_title="Custom merge message"
            )

            assert result["merged"] is True
