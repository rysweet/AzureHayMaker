"""MergeBrick - Merges pull requests."""

import logging
import time
from datetime import datetime

from azure_haymaker.engineering_sim.bricks.base import (
    BrickContext,
    BrickExecutionError,
    BrickResult,
    WorkflowBrick,
)
from azure_haymaker.engineering_sim.github_client import GitHubAPIError, GitHubClient

logger = logging.getLogger(__name__)


class MergeBrick(WorkflowBrick):
    """Merges a pull request.

    Args:
        github_client: GitHubClient for API operations
        merge_method: Merge method ("merge", "squash", "rebase") - default: "squash"
        commit_title: Optional custom merge commit title
        commit_message: Optional custom merge commit message
    """

    def __init__(
        self,
        github_client: GitHubClient = None,
        merge_method: str = "squash",
        merge_strategy: str | None = None,  # Alias for merge_method
        commit_title: str | None = None,
        commit_message: str | None = None
    ):
        self.github_client = github_client
        # Support both merge_method and merge_strategy parameter names
        self.merge_method = merge_strategy or merge_method
        self.commit_title = commit_title
        self.commit_message = commit_message

    def validate(self, context: BrickContext) -> bool:
        """Validate that context has pr_number and CI passed.

        Checks metadata for ci_passed flag.
        """
        if context.pr_number is None:
            return False

        # Check if CI has passed (stored in metadata as ci_status="success" or ci_passed=True)
        ci_status = context.metadata.get("ci_status", "")
        ci_passed = context.metadata.get("ci_passed", False)
        return ci_status == "success" or ci_passed is True

    async def execute(self, context: BrickContext) -> BrickResult:
        """Merge a pull request.

        Args:
            context: Current workflow context

        Returns:
            BrickResult with merge telemetry

        Raises:
            BrickExecutionError: If merge fails
        """
        start_time = time.time()

        try:
            if not self.validate(context):
                raise BrickExecutionError(
                    "MergeBrick requires pr_number in context"
                )

            # Merge PR via GitHub API
            logger.info(
                f"Merging PR #{context.pr_number} with method: {self.merge_method}"
            )

            try:
                merge_response = await self.github_client.merge_pull_request(
                    repo=context.repo_name,
                    pr_number=context.pr_number,
                    merge_method=self.merge_method,
                    commit_title=self.commit_title,
                    commit_message=self.commit_message
                )
            except GitHubAPIError as e:
                raise BrickExecutionError(
                    f"Failed to merge pull request: {str(e)}"
                ) from e

            # Extract merge details
            merge_sha = merge_response.get("sha", "unknown")
            merged = merge_response.get("merged", True)
            merged_at = merge_response.get("merged_at", datetime.now().isoformat())

            # Build telemetry
            duration = time.time() - start_time
            telemetry = {
                "brick_type": "merge",
                "pr_number": context.pr_number,
                "merge_sha": merge_sha,
                "merge_method": self.merge_method,
                "merged": merged,
                "merged_at": merged_at,
                "timestamp": datetime.now().isoformat(),
            }

            # Update context with merge SHA and metadata
            updated_metadata = {**context.metadata, "merged": merged, "merge_sha": merge_sha}
            updated_context = context.update(commit_sha=merge_sha, metadata=updated_metadata)

            logger.info(
                f"Successfully merged PR #{context.pr_number} -> {merge_sha[:8]}"
            )

            return BrickResult(
                success=True,
                context=updated_context,
                telemetry=telemetry,
                duration_seconds=duration
            )

        except BrickExecutionError:
            raise

        except Exception as e:
            duration = time.time() - start_time
            raise BrickExecutionError(
                f"Unexpected error in MergeBrick: {str(e)}"
            ) from e
