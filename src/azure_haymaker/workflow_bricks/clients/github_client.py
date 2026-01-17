"""GitHub API client for workflow bricks.

Provides async methods for GitHub operations including commits,
pull requests, reviews, workflows, and branch management.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async client for GitHub API operations.

    Provides methods for creating commits, pull requests, reviews,
    triggering workflows, and managing branches.

    Attributes:
        token: GitHub authentication token
        base_url: GitHub API base URL

    Example:
        >>> client = GitHubClient(token="ghp_...")
        >>> commit = await client.create_commit(
        ...     owner="my-org",
        ...     repo="my-repo",
        ...     message="feat: Add feature",
        ...     tree_sha="abc123",
        ...     parent_sha="def456",
        ... )
    """

    def __init__(
        self,
        token: str,
        base_url: str = "https://api.github.com",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the GitHub client.

        Args:
            token: GitHub authentication token (PAT or GitHub App token)
            base_url: GitHub API base URL (default: api.github.com)
            timeout: Request timeout in seconds
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._rate_limit_remaining: int | None = None
        self._rate_limit_reset: int | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_repo_url(self, owner: str, repo: str) -> str:
        """Get the API URL for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Full API URL for the repository
        """
        return f"{self.base_url}/repos/{owner}/{repo}"

    async def handle_rate_limit(self, response: httpx.Response) -> None:
        """Handle rate limit headers from response.

        Updates internal rate limit tracking and waits if necessary.

        Args:
            response: HTTP response from GitHub API
        """
        self._rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 5000))
        self._rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

        if self._rate_limit_remaining == 0:
            import time

            wait_time = max(0, self._rate_limit_reset - int(time.time()))
            logger.warning(f"Rate limited. Waiting {wait_time} seconds.")
            await asyncio.sleep(wait_time + 1)

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to GitHub API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint (relative to base_url)
            json: Optional JSON body

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=json,
            )

            await self.handle_rate_limit(response)
            response.raise_for_status()

            if response.status_code == 204:  # No content
                return {}

            return response.json()

    async def create_commit(
        self,
        owner: str,
        repo: str,
        message: str,
        tree_sha: str,
        parent_sha: str,
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> dict[str, Any]:
        """Create a new commit.

        Creates a commit object. Note: This creates the commit but doesn't
        update any ref to point to it. Use update_ref() to move a branch.

        Args:
            owner: Repository owner
            repo: Repository name
            message: Commit message
            tree_sha: SHA of the tree object this commit points to
            parent_sha: SHA of the parent commit
            author_name: Optional author name
            author_email: Optional author email

        Returns:
            Created commit object with 'sha' and other fields
        """
        body: dict[str, Any] = {
            "message": message,
            "tree": tree_sha,
            "parents": [parent_sha],
        }

        if author_name and author_email:
            body["author"] = {
                "name": author_name,
                "email": author_email,
            }

        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            json=body,
        )

    async def get_ref(self, owner: str, repo: str, ref: str) -> dict[str, Any]:
        """Get a git reference (branch or tag).

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Reference name (e.g., "heads/main", "tags/v1.0")

        Returns:
            Reference object with 'ref' and 'object.sha'
        """
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/ref/{ref}",
        )

    async def update_ref(
        self,
        owner: str,
        repo: str,
        ref: str,
        sha: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Update a git reference to point to a new commit.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Reference name (e.g., "heads/main")
            sha: SHA to point the ref to
            force: Force update even if not fast-forward

        Returns:
            Updated reference object
        """
        return await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/git/refs/{ref}",
            json={"sha": sha, "force": force},
        )

    async def create_tree(
        self,
        owner: str,
        repo: str,
        base_tree: str,
        tree: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a new tree object.

        Args:
            owner: Repository owner
            repo: Repository name
            base_tree: SHA of the base tree
            tree: List of tree entries to add/modify

        Returns:
            Created tree object with 'sha'
        """
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            json={"base_tree": base_tree, "tree": tree},
        )

    async def get_blob(
        self,
        owner: str,
        repo: str,
        file_sha: str,
    ) -> dict[str, Any]:
        """Get a blob (file) by SHA.

        Args:
            owner: Repository owner
            repo: Repository name
            file_sha: SHA of the blob

        Returns:
            Blob object with 'content' (base64 encoded)
        """
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/blobs/{file_sha}",
        )

    async def create_blob(
        self,
        owner: str,
        repo: str,
        content: str,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Create a blob (file) in the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            content: File content
            encoding: Content encoding (utf-8 or base64)

        Returns:
            Created blob with 'sha'
        """
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/blobs",
            json={"content": content, "encoding": encoding},
        )

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
    ) -> dict[str, Any]:
        """Create a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            body: PR description
            head: Branch with changes
            base: Target branch
            draft: Create as draft PR

        Returns:
            Created PR with 'number', 'html_url', etc.
        """
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft,
            },
        )

    async def add_labels(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: list[str],
    ) -> list[dict[str, Any]]:
        """Add labels to an issue or PR.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue/PR number
            labels: List of label names

        Returns:
            List of label objects
        """
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/labels",
            json={"labels": labels},
        )

    async def request_reviewers(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        reviewers: list[str],
    ) -> dict[str, Any]:
        """Request reviewers for a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: PR number
            reviewers: List of reviewer usernames

        Returns:
            Updated PR object
        """
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers",
            json={"reviewers": reviewers},
        )

    async def create_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        body: str,
        event: str,
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a pull request review.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: PR number
            body: Review body text
            event: Review event (APPROVE, REQUEST_CHANGES, COMMENT)
            comments: Optional list of review comments

        Returns:
            Created review with 'id'
        """
        request_body: dict[str, Any] = {
            "body": body,
            "event": event,
        }

        if comments:
            request_body["comments"] = comments

        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
            json=request_body,
        )

    async def trigger_workflow(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str,
        inputs: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Trigger a workflow dispatch event.

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Workflow file name (e.g., "ci.yml") or ID
            ref: Git reference to run workflow on
            inputs: Optional workflow inputs

        Returns:
            Empty dict (workflow triggered successfully)
        """
        body: dict[str, Any] = {"ref": ref}
        if inputs:
            body["inputs"] = inputs

        await self._request(
            "POST",
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
            json=body,
        )

        # Workflow dispatch returns 204, so return a synthetic response
        return {"status": "queued", "workflow_id": workflow_id, "ref": ref}

    async def get_workflow_runs(
        self,
        owner: str,
        repo: str,
        workflow_id: str | None = None,
        branch: str | None = None,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """Get workflow runs for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Optional workflow file name to filter by
            branch: Optional branch to filter by
            per_page: Number of results per page

        Returns:
            Workflow runs response with 'workflow_runs' list
        """
        endpoint = f"/repos/{owner}/{repo}/actions/runs"
        if workflow_id:
            endpoint = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"

        params = [f"per_page={per_page}"]
        if branch:
            params.append(f"branch={branch}")

        if params:
            endpoint += "?" + "&".join(params)

        return await self._request("GET", endpoint)

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        merge_method: str = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Merge a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: PR number
            merge_method: Merge method (merge, squash, rebase)
            commit_title: Optional custom commit title
            commit_message: Optional custom commit message

        Returns:
            Merge result with 'sha' and 'merged' status
        """
        body: dict[str, Any] = {"merge_method": merge_method}

        if commit_title:
            body["commit_title"] = commit_title
        if commit_message:
            body["commit_message"] = commit_message

        return await self._request(
            "PUT",
            f"/repos/{owner}/{repo}/pulls/{pull_number}/merge",
            json=body,
        )

    async def delete_branch(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> bool:
        """Delete a branch.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name to delete

        Returns:
            True if deleted successfully
        """
        try:
            await self._request(
                "DELETE",
                f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
            )
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                # Branch already deleted or protected
                logger.warning(f"Could not delete branch {branch}: {e}")
                return False
            raise

    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> dict[str, Any]:
        """Get a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: PR number

        Returns:
            Pull request object
        """
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pull_number}",
        )


__all__ = ["GitHubClient"]
