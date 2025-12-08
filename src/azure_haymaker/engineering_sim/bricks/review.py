"""ReviewBrick - Submits code reviews on pull requests."""

import logging
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from azure_haymaker.engineering_sim.bricks.base import (
    WorkflowBrick,
    BrickContext,
    BrickResult,
    BrickExecutionError,
)
from azure_haymaker.engineering_sim.github_client import GitHubClient, GitHubAPIError

logger = logging.getLogger(__name__)


class ReviewBrick(WorkflowBrick):
    """Creates a code review on a pull request.

    Args:
        github_client: GitHubClient for API operations
        reviewer_name: Name of reviewer (default: auto-generated)
        review_type: Type of review ("APPROVE", "REQUEST_CHANGES", "COMMENT")
        review_body: Review comment text (default: auto-generated)
        line_comments: List of line-specific comments (default: [])
    """

    def __init__(
        self,
        github_client: GitHubClient = None,
        reviewer_name: Optional[str] = None,
        review_type: str = "APPROVE",
        review_body: Optional[str] = None,
        body: Optional[str] = None,  # Alias for review_body
        line_comments: Optional[List[Dict[str, Any]]] = None,
        comments: Optional[List[Dict[str, Any]]] = None  # Alias for line_comments
    ):
        self.github_client = github_client
        self.reviewer_name = reviewer_name
        self.review_type = review_type
        # Support both review_body and body parameter names
        self.review_body = body or review_body
        # Support both line_comments and comments parameter names
        self.line_comments = comments or line_comments or []

    def validate(self, context: BrickContext) -> bool:
        """Validate that context has pr_number."""
        return context.pr_number is not None

    async def execute(self, context: BrickContext) -> BrickResult:
        """Submit a code review.

        Args:
            context: Current workflow context

        Returns:
            BrickResult with review telemetry

        Raises:
            BrickExecutionError: If review submission fails
        """
        start_time = time.time()

        try:
            if not self.validate(context):
                raise BrickExecutionError(
                    "ReviewBrick requires pr_number in context"
                )

            # Generate review body if not provided
            body = self.review_body or self._generate_review_body(self.review_type)

            # Submit review via GitHub API
            logger.info(
                f"Submitting {self.review_type} review on PR #{context.pr_number}"
            )

            try:
                review_response = await self.github_client.create_review(
                    repo=context.repo_name,
                    pr_number=context.pr_number,
                    event=self.review_type,
                    body=body,
                    comments=self.line_comments if self.line_comments else None
                )
            except GitHubAPIError as e:
                raise BrickExecutionError(
                    f"Failed to create review: {str(e)}"
                )

            # Extract review details
            review_id = review_response["id"]
            review_state = review_response.get("state", self.review_type)
            submitted_at = review_response.get("submitted_at", datetime.now().isoformat())
            reviewer = review_response.get("user", {}).get("login", self.reviewer_name or "unknown")

            # Build telemetry
            duration = time.time() - start_time
            telemetry = {
                "brick_type": "review",
                "review_id": review_id,
                "reviewer": reviewer,
                "state": review_state,
                "body": body,
                "line_comments_count": len(self.line_comments),
                "submitted_at": submitted_at,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"Successfully submitted {review_state} review #{review_id}"
            )

            return BrickResult(
                success=True,
                context=context,  # Review doesn't update context
                telemetry=telemetry,
                duration_seconds=duration
            )

        except BrickExecutionError:
            raise

        except Exception as e:
            duration = time.time() - start_time
            raise BrickExecutionError(
                f"Unexpected error in ReviewBrick: {str(e)}"
            )

    def _generate_review_body(self, review_type: str) -> str:
        """Generate review comment based on type."""
        if review_type == "APPROVE":
            messages = [
                "LGTM! Great work.",
                "Looks good to me! Approved.",
                "Nice implementation. Approved.",
                "All checks passed. Approved.",
            ]
        elif review_type == "REQUEST_CHANGES":
            messages = [
                "Please address the comments before merging.",
                "A few changes needed before this can be merged.",
                "Some improvements required.",
            ]
        else:  # COMMENT
            messages = [
                "Few minor suggestions.",
                "Looks mostly good, some comments inline.",
                "Overall good, left some feedback.",
            ]

        return random.choice(messages)
