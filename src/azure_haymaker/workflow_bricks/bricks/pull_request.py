"""PullRequestBrick - Creates pull requests.

Simulates a developer opening a pull request for code review,
generating appropriate telemetry.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from azure_haymaker.workflow_bricks.base import BrickBase
from azure_haymaker.workflow_bricks.clients.github_client import GitHubClient
from azure_haymaker.workflow_bricks.exceptions import BrickValidationError
from azure_haymaker.workflow_bricks.models import BrickContext, BrickResult

logger = logging.getLogger(__name__)


class PullRequestBrick(BrickBase):
    """Brick that creates a pull request.

    Creates a PR with specified title, description, and optional
    labels and reviewers.

    Attributes:
        title: PR title
        body: PR description
        base_branch: Target branch for the PR
        head_branch: Source branch with changes
        labels: Optional list of label names
        reviewers: Optional list of reviewer usernames
        draft: Whether to create as draft PR

    Example:
        >>> brick = PullRequestBrick(
        ...     title="feat: Add user authentication",
        ...     body="Implements login and registration",
        ...     base_branch="main",
        ...     head_branch="feat/auth",
        ...     labels=["enhancement"],
        ...     reviewers=["bob", "carol"],
        ... )
        >>> result = await brick.execute(context)
        >>> print(result.outputs["pr_number"])
    """

    def __init__(
        self,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
        labels: list[str] | None = None,
        reviewers: list[str] | None = None,
        draft: bool = False,
    ) -> None:
        """Initialize PullRequestBrick.

        Args:
            title: PR title
            body: PR description
            base_branch: Target branch
            head_branch: Source branch
            labels: Optional label names
            reviewers: Optional reviewer usernames
            draft: Create as draft PR
        """
        super().__init__()
        self.title = title
        self.body = body
        self.base_branch = base_branch
        self.head_branch = head_branch
        self.labels = labels or []
        self.reviewers = reviewers or []
        self.draft = draft

    async def validate(self, context: BrickContext) -> bool:
        """Validate PR preconditions.

        Checks that:
        - PR title is provided
        - Base and head branches are specified

        Args:
            context: Execution context

        Returns:
            True if validation passes

        Raises:
            BrickValidationError: If validation fails
        """
        if not self.title or not self.title.strip():
            raise BrickValidationError("PR title required")

        if not self.base_branch:
            raise BrickValidationError("Base branch required")

        if not self.head_branch:
            raise BrickValidationError("Head branch required")

        if not context.github_token:
            raise BrickValidationError("GitHub token required")

        return True

    async def execute(self, context: BrickContext) -> BrickResult:
        """Execute PR creation.

        In real mode, creates PR via GitHub API.
        In dry_run mode, simulates the PR without API calls.

        Args:
            context: Execution context

        Returns:
            BrickResult with pr_number and pr_url in outputs
        """
        result = self._create_result()

        try:
            if context.dry_run:
                pr_data = await self._execute_dry_run(context)
            else:
                pr_data = await self._execute_real(context)

            result.outputs["pr_number"] = pr_data["number"]
            result.outputs["pr_url"] = pr_data["html_url"]
            result.outputs["title"] = self.title
            result.outputs["base_branch"] = self.base_branch
            result.outputs["head_branch"] = self.head_branch

            # Update context metadata for downstream bricks
            context.metadata["pr_number"] = pr_data["number"]
            context.metadata["pr_url"] = pr_data["html_url"]

            # Log telemetry
            self._log_telemetry(
                result=result,
                event_type="opened",
                context=context,
                target=f"{context.full_repo_name}#{pr_data['number']}",
                details={
                    "pr_number": pr_data["number"],
                    "title": self.title,
                    "base": self.base_branch,
                    "head": self.head_branch,
                    "draft": self.draft,
                },
            )

            result.mark_success()

        except Exception as e:
            logger.exception(f"PR creation failed: {e}")
            result.mark_failed(str(e))

        return result

    async def _execute_dry_run(self, context: BrickContext) -> dict[str, Any]:
        """Execute in dry run mode (no API calls).

        Args:
            context: Execution context

        Returns:
            Simulated PR data
        """
        # Generate fake but realistic PR number
        fake_number = abs(hash(f"{context.full_repo_name}-{self.title}-{uuid.uuid4().hex}")) % 10000

        logger.info(f"[DRY RUN] Would create PR on {context.full_repo_name}")
        logger.info(f"[DRY RUN] Title: {self.title}")
        logger.info(f"[DRY RUN] {self.head_branch} -> {self.base_branch}")
        if self.labels:
            logger.info(f"[DRY RUN] Labels: {', '.join(self.labels)}")
        if self.reviewers:
            logger.info(f"[DRY RUN] Reviewers: {', '.join(self.reviewers)}")

        return {
            "number": fake_number,
            "html_url": f"https://github.com/{context.full_repo_name}/pull/{fake_number}",
        }

    async def _execute_real(self, context: BrickContext) -> dict[str, Any]:
        """Execute real PR creation via GitHub API.

        Args:
            context: Execution context

        Returns:
            Created PR data
        """
        client = self._get_client(context)

        # Create the PR
        pr = await client.create_pull_request(
            context.repo_owner,
            context.repo_name,
            self.title,
            self.body,
            self.head_branch,
            self.base_branch,
            self.draft,
        )

        pr_number = pr["number"]

        # Add labels if specified
        if self.labels:
            try:
                await client.add_labels(
                    context.repo_owner,
                    context.repo_name,
                    pr_number,
                    self.labels,
                )
                logger.info(f"Added labels {self.labels} to PR #{pr_number}")
            except Exception as e:
                logger.warning(f"Failed to add labels to PR #{pr_number}: {e}")

        # Request reviewers if specified
        if self.reviewers:
            try:
                await client.request_reviewers(
                    context.repo_owner,
                    context.repo_name,
                    pr_number,
                    self.reviewers,
                )
                logger.info(f"Requested reviewers {self.reviewers} for PR #{pr_number}")
            except Exception as e:
                logger.warning(f"Failed to request reviewers for PR #{pr_number}: {e}")

        logger.info(f"Created PR #{pr_number} on {context.full_repo_name}")

        return pr

    def _get_client(self, context: BrickContext) -> GitHubClient:
        """Get or create GitHub client from context.

        Args:
            context: Execution context

        Returns:
            GitHubClient instance
        """
        if context.github_client is not None:
            return context.github_client

        return GitHubClient(token=context.github_token)


__all__ = ["PullRequestBrick"]
