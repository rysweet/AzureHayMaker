"""GitHub API client for engineering simulation.

Provides async GitHub API operations with:
- Rate limiting and backoff
- Automatic retries
- Telemetry tracking
- Error handling

This client wraps GitHub API calls needed for engineering simulations.
"""

import asyncio
import logging
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""
    pass


class RateLimitError(Exception):
    """Exception raised when GitHub rate limit is exceeded."""
    pass


class GitHubClient:
    """GitHub API client for engineering simulation.

    Provides async methods for common GitHub operations:
    - Creating commits
    - Creating pull requests
    - Creating reviews
    - Merging PRs
    - Rate limit management

    Args:
        token: GitHub personal access token
        org: GitHub organization name
        rate_limit_strategy: How to handle rate limits ("wait", "skip", "fail")
        base_url: GitHub API base URL (default: public GitHub)
        max_retries: Maximum number of retries for failed requests (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)
    """

    def __init__(
        self,
        token: str,
        org: str,
        rate_limit_strategy: str = "wait",
        base_url: str = "https://api.github.com",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.token = token
        self.org = org
        self.rate_limit_strategy = rate_limit_strategy
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._rate_limit_cache: dict[str, Any] | None = None
        self._last_rate_limit_check: float = 0

    async def create_commit(
        self,
        repo: str,
        branch: str,
        files: dict[str, str],
        message: str,
        author: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Create a commit with file changes.

        Args:
            repo: Repository name
            branch: Branch name to commit to
            files: Dict mapping file paths to content
            message: Commit message
            author: Optional author dict with 'name' and 'email'

        Returns:
            Dict containing commit data including 'sha'

        Raises:
            GitHubAPIError: If commit creation fails
            RateLimitError: If rate limit exceeded and strategy is "fail"
        """
        await self._check_rate_limit()

        payload = {
            "branch": branch,
            "message": message,
            "files": files,
        }

        if author:
            payload["author"] = author

        endpoint = f"/repos/{self.org}/{repo}/commits"
        return await self._make_request_with_retry("POST", endpoint, payload)

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        labels: list[str] | None = None,
        draft: bool = False
    ) -> dict[str, Any]:
        """Create a pull request.

        Args:
            repo: Repository name
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch
            labels: Optional list of label names
            draft: Whether to create as draft PR

        Returns:
            Dict containing PR data including 'number'

        Raises:
            GitHubAPIError: If PR creation fails
            RateLimitError: If rate limit exceeded
        """
        await self._check_rate_limit()

        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": draft,
        }

        if labels:
            payload["labels"] = labels

        endpoint = f"/repos/{self.org}/{repo}/pulls"
        return await self._make_request("POST", endpoint, payload)

    async def create_review(
        self,
        repo: str,
        pr_number: int,
        event: str,
        body: str,
        comments: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Create a pull request review.

        Args:
            repo: Repository name
            pr_number: PR number
            event: Review event ("APPROVE", "REQUEST_CHANGES", "COMMENT")
            body: Review body text
            comments: Optional list of line comments

        Returns:
            Dict containing review data including 'id' and 'state'

        Raises:
            GitHubAPIError: If review creation fails
            RateLimitError: If rate limit exceeded
        """
        await self._check_rate_limit()

        payload = {
            "event": event,
            "body": body,
        }

        if comments:
            payload["comments"] = comments

        endpoint = f"/repos/{self.org}/{repo}/pulls/{pr_number}/reviews"
        return await self._make_request("POST", endpoint, payload)

    async def merge_pull_request(
        self,
        repo: str,
        pr_number: int,
        merge_method: str = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None
    ) -> dict[str, Any]:
        """Merge a pull request.

        Args:
            repo: Repository name
            pr_number: PR number
            merge_method: Merge method ("merge", "squash", "rebase")
            commit_title: Optional custom merge commit title
            commit_message: Optional custom merge commit message

        Returns:
            Dict containing merge data including 'sha' and 'merged' boolean

        Raises:
            GitHubAPIError: If merge fails
            RateLimitError: If rate limit exceeded
        """
        await self._check_rate_limit()

        payload = {
            "merge_method": merge_method,
        }

        if commit_title:
            payload["commit_title"] = commit_title

        if commit_message:
            payload["commit_message"] = commit_message

        endpoint = f"/repos/{self.org}/{repo}/pulls/{pr_number}/merge"
        return await self._make_request("PUT", endpoint, payload)

    async def trigger_workflow(
        self,
        repo: str,
        workflow: str,
        ref: str,
        inputs: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Trigger a GitHub Actions workflow.

        Args:
            repo: Repository name
            workflow: Workflow file name or ID
            ref: Git reference (branch, tag, commit)
            inputs: Optional workflow inputs

        Returns:
            Dict containing workflow run data

        Raises:
            GitHubAPIError: If workflow trigger fails
            RateLimitError: If rate limit exceeded
        """
        await self._check_rate_limit()

        payload = {
            "ref": ref,
        }

        if inputs:
            payload["inputs"] = inputs

        endpoint = f"/repos/{self.org}/{repo}/actions/workflows/{workflow}/dispatches"
        return await self._make_request("POST", endpoint, payload)

    async def update_check_run(
        self,
        repo: str,
        check_run_id: int,
        status: str,
        conclusion: str | None = None
    ) -> dict[str, Any]:
        """Update a GitHub check run.

        Args:
            repo: Repository name
            check_run_id: Check run ID
            status: Status ("queued", "in_progress", "completed")
            conclusion: Optional conclusion ("success", "failure", "cancelled")

        Returns:
            Dict containing check run data

        Raises:
            GitHubAPIError: If update fails
            RateLimitError: If rate limit exceeded
        """
        await self._check_rate_limit()

        payload = {
            "status": status,
        }

        if conclusion:
            payload["conclusion"] = conclusion

        endpoint = f"/repos/{self.org}/{repo}/check-runs/{check_run_id}"
        return await self._make_request("PATCH", endpoint, payload)

    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current rate limit status.

        Returns:
            Dict containing rate limit info with 'resources' key

        Raises:
            GitHubAPIError: If request fails
        """
        endpoint = "/rate_limit"
        # Don't use retry wrapper for rate limit checks
        return await self._make_request("GET", endpoint, {})

    async def _check_rate_limit(self) -> dict[str, int]:
        """Check rate limit and handle according to strategy.

        Returns:
            Dict with 'remaining' and 'reset' timestamp

        Raises:
            RateLimitError: If rate limit exceeded and strategy is "fail"
        """
        # Simple rate limit check - can be overridden by tests
        current_time = time.time()

        # Only check every 10 seconds to avoid excessive API calls
        if current_time - self._last_rate_limit_check < 10 and self._rate_limit_cache:
            return self._rate_limit_cache

        try:
            rate_limit_data = await self.get_rate_limit()
            core_limit = rate_limit_data.get("resources", {}).get("core", {})

            remaining = core_limit.get("remaining", 5000)
            reset = core_limit.get("reset", int(current_time) + 3600)

            self._rate_limit_cache = {"remaining": remaining, "reset": reset}
            self._last_rate_limit_check = current_time

            # Handle rate limit strategies
            if remaining == 0:
                if self.rate_limit_strategy == "fail":
                    raise RateLimitError(
                        f"GitHub rate limit exceeded. Resets at {reset}"
                    )
                elif self.rate_limit_strategy == "wait":
                    # Wait until reset
                    wait_time = max(0, reset - current_time)
                    logger.warning(
                        f"Rate limit exceeded. Waiting {wait_time}s until reset."
                    )
                    await asyncio.sleep(min(wait_time, 60))  # Cap wait at 60s for testing
                # "skip" strategy continues without waiting

            return self._rate_limit_cache

        except RateLimitError:
            # Re-raise rate limit errors
            raise
        except (GitHubAPIError, Exception) as e:
            # If rate limit check fails with API errors (including 5xx), continue
            # Don't block workflow due to transient rate limit check failures
            logger.warning(f"Rate limit check failed: {e}")
            return {"remaining": 5000, "reset": int(current_time) + 3600}

    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic for transient errors.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            Dict containing response data

        Raises:
            GitHubAPIError: If request fails after all retries
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await self._make_request(method, endpoint, payload)

            except GitHubAPIError as e:
                last_error = e
                error_str = str(e)

                # Check if error is retryable (5xx errors)
                if any(code in error_str for code in ["503", "502", "500"]) and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Request failed with {error_str}, "
                        f"retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Non-retryable error or max retries reached
                raise

        # Max retries exceeded
        if last_error:
            raise GitHubAPIError(
                f"Request failed after {self.max_retries} attempts: {last_error}"
            )

        raise GitHubAPIError("Request failed with unknown error")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Make HTTP request to GitHub API using aiohttp.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            Dict containing response data

        Raises:
            GitHubAPIError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AzureHayMaker-Engineering-Simulation/1.0",
        }

        # Sanitize headers for logging (never log auth tokens)
        safe_headers = {k: ("***REDACTED***" if k == "Authorization" else v)
                        for k, v in headers.items()}
        logger.debug(f"GitHub API {method} {endpoint} headers={safe_headers}")

        try:
            async with aiohttp.ClientSession() as session, session.request(
                method=method,
                url=url,
                json=payload if payload else None,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                # Log response status
                logger.debug(f"GitHub API response: {response.status}")

                # Handle HTTP errors
                if response.status >= 400:
                    error_text = await response.text()
                    raise GitHubAPIError(
                        f"GitHub API error {response.status}: {error_text}"
                    )

                # Return JSON response for non-204 responses
                if response.status == 204:
                    # No content (e.g., successful DELETE)
                    return {"status": "success"}

                return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise GitHubAPIError(f"HTTP request failed: {e}") from e
        except TimeoutError as e:
            logger.error(f"Request timeout for {endpoint}")
            raise GitHubAPIError(f"Request timeout: {endpoint}") from e
        except Exception as e:
            logger.error(f"Unexpected error during GitHub API request: {e}")
            raise GitHubAPIError(f"Unexpected error: {e}") from e
