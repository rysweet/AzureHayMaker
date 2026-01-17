"""MergeBrick - Merges pull requests.

Simulates merging a pull request after approval,
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

# Type alias for merge methods
MergeMethod = Literal["merge", "squash", "rebase"]


class MergeBrick(BrickBase):
    """Brick that merges a pull request.

    Merges a PR using the specified method and optionally
    deletes the source branch.

    Attributes:
        pr_number: PR number to merge (or None to use metadata)
        merge_method: How to merge (merge, squash, rebase)
        delete_branch: Whether to delete branch after merge
        commit_title: Optional custom merge commit title
        commit_message: Optional custom merge commit message

    Example:
        >>> brick = MergeBrick(
        ...     pr_number=42,
        ...     merge_method="squash",
        ...     delete_branch=True,
        ... )
        >>> result = await brick.execute(context)
        >>> print(result.outputs["merge_sha"])
    """

    def __init__(
        self,
        pr_number: int | None,
        merge_method: MergeMethod = "merge",
        delete_branch: bool = False,
        commit_title: str | None = None,
        commit_message: str | None = None,
    ) -> None:
        """Initialize MergeBrick.

        Args:
            pr_number: PR number (or None to use context metadata)
            merge_method: Merge method (merge, squash, rebase)
            delete_branch: Delete branch after merge
            commit_title: Custom merge commit title
            commit_message: Custom merge commit message
        """
        super().__init__()
        self.pr_number = pr_number
        self.merge_method = merge_method
        self.delete_branch = delete_branch
        self.commit_title = commit_title
        self.commit_message = commit_message

    async def validate(self, context: BrickContext) -> bool:
        """Validate merge preconditions.

        Checks that:
        - PR number is available (explicit or from metadata)
        - Merge method is valid

        Args:
            context: Execution context

        Returns:
            True if validation passes

        Raises:
            BrickValidationError: If validation fails
        """
        effective_pr = self._get_pr_number(context)
        if effective_pr is None:
            raise BrickValidationError(
                "PR number required. Provide pr_number or ensure context.metadata['pr_number'] is set."
            )

        if self.merge_method not in ("merge", "squash", "rebase"):
            raise BrickValidationError(
                f"Invalid merge method '{self.merge_method}'. Must be merge, squash, or rebase."
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
        """Execute the PR merge.

        In real mode, merges PR via GitHub API.
        In dry_run mode, simulates the merge without API calls.

        Args:
            context: Execution context

        Returns:
            BrickResult with merge_sha in outputs
        """
        result = self._create_result()

        try:
            effective_pr = self._get_pr_number(context)
            if effective_pr is None:
                result.mark_failed("No PR number available")
                return result

            if context.dry_run:
                merge_data = await self._execute_dry_run(context, effective_pr)
            else:
                merge_data = await self._execute_real(context, effective_pr)

            result.outputs["merge_sha"] = merge_data["sha"]
            result.outputs["pr_number"] = effective_pr
            result.outputs["merge_method"] = self.merge_method
            result.outputs["branch_deleted"] = merge_data.get("branch_deleted", False)

            # Update context metadata
            context.metadata["merge_sha"] = merge_data["sha"]

            # Log telemetry
            self._log_telemetry(
                result=result,
                event_type="merged",
                context=context,
                target=f"{context.full_repo_name}#{effective_pr}",
                details={
                    "merge_sha": merge_data["sha"],
                    "merge_method": self.merge_method,
                    "branch_deleted": merge_data.get("branch_deleted", False),
                },
            )

            result.mark_success()

        except Exception as e:
            logger.exception(f"Merge failed: {e}")
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
            Simulated merge data
        """
        # Generate fake but realistic merge SHA
        fake_sha = f"dry_run_merge_{uuid.uuid4().hex[:12]}"

        logger.info(f"[DRY RUN] Would merge PR #{pr_number} on {context.full_repo_name}")
        logger.info(f"[DRY RUN] Method: {self.merge_method}")
        if self.delete_branch:
            logger.info(f"[DRY RUN] Would delete branch: {context.branch_name}")

        return {
            "sha": fake_sha,
            "merged": True,
            "branch_deleted": self.delete_branch,
        }

    async def _execute_real(
        self,
        context: BrickContext,
        pr_number: int,
    ) -> dict[str, Any]:
        """Execute real PR merge via GitHub API.

        Args:
            context: Execution context
            pr_number: PR number

        Returns:
            Merge result data
        """
        client = self._get_client(context)

        # Merge the PR
        merge_result = await client.merge_pull_request(
            context.repo_owner,
            context.repo_name,
            pr_number,
            self.merge_method,
            self.commit_title,
            self.commit_message,
        )

        merge_sha = merge_result.get("sha", "")
        branch_deleted = False

        logger.info(
            f"Merged PR #{pr_number} on {context.full_repo_name} (method: {self.merge_method})"
        )

        # Delete branch if requested
        if self.delete_branch:
            # Get the PR to find the head branch
            pr = await client.get_pull_request(
                context.repo_owner,
                context.repo_name,
                pr_number,
            )

            head_ref = pr.get("head", {}).get("ref")
            if head_ref:
                branch_deleted = await client.delete_branch(
                    context.repo_owner,
                    context.repo_name,
                    head_ref,
                )
                if branch_deleted:
                    logger.info(f"Deleted branch {head_ref}")
                else:
                    logger.warning(f"Could not delete branch {head_ref}")

        return {
            "sha": merge_sha,
            "merged": True,
            "branch_deleted": branch_deleted,
        }

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


__all__ = ["MergeBrick"]
