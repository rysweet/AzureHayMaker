"""CodeReviewBrick - Submits code reviews.

Simulates a reviewer providing feedback on a pull request,
generating appropriate telemetry.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from azure_haymaker.workflow_bricks.base import BrickBase
from azure_haymaker.workflow_bricks.clients.github_client import GitHubClient
from azure_haymaker.workflow_bricks.exceptions import BrickValidationError
from azure_haymaker.workflow_bricks.models import BrickContext, BrickResult

logger = logging.getLogger(__name__)

# Type alias for review actions
ReviewAction = Literal["approve", "request_changes", "comment"]


class CodeReviewBrick(BrickBase):
    """Brick that submits a code review.

    Creates a review on a pull request with an optional
    body and inline comments.

    Attributes:
        pr_number: PR number to review (or None to use metadata)
        reviewer: Username of the reviewer
        action: Review action (approve, request_changes, comment)
        body: Review body text
        comments: Optional list of inline comments

    Example:
        >>> brick = CodeReviewBrick(
        ...     pr_number=42,
        ...     reviewer="bob",
        ...     action="approve",
        ...     body="LGTM! Great work.",
        ...     comments=[
        ...         {"path": "src/auth.py", "line": 15, "body": "Consider bcrypt"},
        ...     ],
        ... )
        >>> result = await brick.execute(context)
        >>> print(result.outputs["review_id"])
    """

    def __init__(
        self,
        pr_number: int | None,
        reviewer: str,
        action: ReviewAction,
        body: str = "",
        comments: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize CodeReviewBrick.

        Args:
            pr_number: PR number (or None to use context metadata)
            reviewer: Reviewer username
            action: Review action (approve, request_changes, comment)
            body: Review body text
            comments: Optional inline comments
        """
        super().__init__()
        self.pr_number = pr_number
        self.reviewer = reviewer
        self.action = action
        self.body = body
        self.comments = comments or []

    async def validate(self, context: BrickContext) -> bool:
        """Validate review preconditions.

        Checks that:
        - PR number is available (explicit or from metadata)
        - Reviewer is specified

        Args:
            context: Execution context

        Returns:
            True if validation passes

        Raises:
            BrickValidationError: If validation fails
        """
        # Try to get PR number from explicit param or metadata
        effective_pr = self._get_pr_number(context)
        if effective_pr is None:
            raise BrickValidationError(
                "PR number required. Provide pr_number or ensure context.metadata['pr_number'] is set."
            )

        if not self.reviewer:
            raise BrickValidationError("Reviewer username required")

        if self.action not in ("approve", "request_changes", "comment"):
            raise BrickValidationError(
                f"Invalid action '{self.action}'. Must be approve, request_changes, or comment."
            )

        if not context.github_token:
            raise BrickValidationError("GitHub token required")

        return True

    def _get_pr_number(self, context: BrickContext) -> int | None:
        """Get PR number from explicit param or context metadata.

        Args:
            context: Execution context

        Returns:
            PR number or None
        """
        if self.pr_number is not None:
            return self.pr_number
        return context.metadata.get("pr_number")

    async def execute(self, context: BrickContext) -> BrickResult:
        """Execute the review submission.

        In real mode, creates review via GitHub API.
        In dry_run mode, simulates the review without API calls.

        Args:
            context: Execution context

        Returns:
            BrickResult with review_id in outputs
        """
        result = self._create_result()

        try:
            effective_pr = self._get_pr_number(context)
            if effective_pr is None:
                result.mark_failed("No PR number available")
                return result

            if context.dry_run:
                review_data = await self._execute_dry_run(context, effective_pr)
            else:
                review_data = await self._execute_real(context, effective_pr)

            result.outputs["review_id"] = review_data["id"]
            result.outputs["pr_number"] = effective_pr
            result.outputs["reviewer"] = self.reviewer
            result.outputs["action"] = self.action

            # Log telemetry
            self._log_telemetry(
                result=result,
                event_type="submitted",
                context=context,
                target=f"{context.full_repo_name}#{effective_pr}",
                details={
                    "review_id": review_data["id"],
                    "action": self.action,
                    "reviewer": self.reviewer,
                    "comments_count": len(self.comments),
                },
            )

            result.mark_success()

        except Exception as e:
            logger.exception(f"Review submission failed: {e}")
            result.mark_failed(str(e))

        return result

    async def _execute_dry_run(
        self,
        context: BrickContext,
        pr_number: int,
    ) -> dict[str, Any]:
        """Execute in dry run mode (no API calls).

        Args:
            context: Execution context
            pr_number: PR number

        Returns:
            Simulated review data
        """
        # Generate fake but realistic review ID
        fake_id = (
            abs(hash(f"{context.full_repo_name}-{pr_number}-{self.reviewer}-{uuid.uuid4().hex}"))
            % 1000000
        )

        action_desc = {
            "approve": "APPROVED",
            "request_changes": "REQUESTED CHANGES",
            "comment": "COMMENTED",
        }

        logger.info(f"[DRY RUN] Would submit review on {context.full_repo_name}#{pr_number}")
        logger.info(f"[DRY RUN] Reviewer: {self.reviewer}")
        logger.info(f"[DRY RUN] Action: {action_desc.get(self.action, self.action)}")
        if self.body:
            logger.info(f"[DRY RUN] Body: {self.body[:100]}...")
        if self.comments:
            logger.info(f"[DRY RUN] Comments: {len(self.comments)} inline comments")

        return {"id": fake_id}

    async def _execute_real(
        self,
        context: BrickContext,
        pr_number: int,
    ) -> dict[str, Any]:
        """Execute real review submission via GitHub API.

        Args:
            context: Execution context
            pr_number: PR number

        Returns:
            Created review data
        """
        client = self._get_client(context)

        # Map action to GitHub event
        event_map = {
            "approve": "APPROVE",
            "request_changes": "REQUEST_CHANGES",
            "comment": "COMMENT",
        }
        event = event_map[self.action]

        # Format comments for API (if any)
        api_comments = None
        if self.comments:
            api_comments = [
                {
                    "path": c["path"],
                    "line": c.get("line", 1),
                    "body": c["body"],
                }
                for c in self.comments
            ]

        # Create the review
        review = await client.create_review(
            context.repo_owner,
            context.repo_name,
            pr_number,
            self.body,
            event,
            api_comments,
        )

        logger.info(
            f"Submitted {self.action} review on {context.full_repo_name}#{pr_number} "
            f"by {self.reviewer}"
        )

        return review

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


__all__ = ["CodeReviewBrick"]
