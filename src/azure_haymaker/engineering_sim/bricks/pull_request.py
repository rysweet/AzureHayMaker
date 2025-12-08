"""PullRequestBrick - Creates GitHub pull requests.

This brick handles:
- Creating pull requests from commits
- Auto-generating titles and descriptions
- Adding labels, assignees, and reviewers
- Draft PR support
- Tracking PR telemetry
"""

import logging
import time
from typing import List, Optional
from datetime import datetime

from azure_haymaker.engineering_sim.bricks.base import (
    WorkflowBrick,
    BrickContext,
    BrickResult,
    BrickExecutionError,
)
from azure_haymaker.engineering_sim.github_client import GitHubClient, GitHubAPIError

logger = logging.getLogger(__name__)


class PullRequestBrick(WorkflowBrick):
    """Creates a GitHub pull request.

    Args:
        github_client: GitHubClient for API operations
        title: PR title (auto-generated if None)
        body: PR description (auto-generated if None)
        head_branch: Source branch (uses context.branch_name if None)
        base_branch: Target branch (default: "main")
        labels: List of label names to add (default: [])
        assignees: List of assignee usernames (default: [])
        reviewers: List of reviewer usernames (default: [])
        draft: Whether to create as draft PR (default: False)
    """

    def __init__(
        self,
        github_client: GitHubClient,
        title: Optional[str] = None,
        body: Optional[str] = None,
        head_branch: Optional[str] = None,
        base_branch: str = "main",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        reviewers: Optional[List[str]] = None,
        draft: bool = False
    ):
        self.github_client = github_client
        self.title = title
        self.body = body
        self.head_branch = head_branch
        self.base_branch = base_branch
        self.labels = labels or []
        self.assignees = assignees or []
        self.reviewers = reviewers or []
        self.draft = draft

    def validate(self, context: BrickContext) -> bool:
        """Validate that context has branch_name and commit_sha.

        Args:
            context: Current workflow context

        Returns:
            True if both branch_name and commit_sha are set
        """
        return (
            context.branch_name is not None
            and context.branch_name != ""
            and context.commit_sha is not None
            and context.commit_sha != ""
        )

    async def execute(self, context: BrickContext) -> BrickResult:
        """Create a pull request.

        Args:
            context: Current workflow context

        Returns:
            BrickResult with updated pr_number and telemetry

        Raises:
            BrickExecutionError: If PR creation fails
        """
        start_time = time.time()

        try:
            # Validate preconditions
            if not self.validate(context):
                raise BrickExecutionError(
                    "PullRequestBrick requires branch_name and commit_sha in context"
                )

            # Determine head and base branches
            head = self.head_branch or context.branch_name
            # Use explicit base_branch from constructor first, then context, then default
            base = self.base_branch if self.base_branch != "main" else (context.base_branch or self.base_branch)

            # Generate title and body if not provided
            title = self.title or self._generate_title(head)
            body = self.body or self._generate_body(head, context)

            # Create PR via GitHub API
            logger.info(
                f"Creating PR on {context.repo_name}: {head} -> {base}"
            )

            try:
                pr_response = await self.github_client.create_pull_request(
                    repo=context.repo_name,
                    title=title,
                    body=body,
                    head=head,
                    base=base,
                    labels=self.labels if self.labels else None,
                    draft=self.draft
                )
            except GitHubAPIError as e:
                raise BrickExecutionError(
                    f"Failed to create pull request: {str(e)}"
                )

            # Extract PR details
            pr_number = pr_response["number"]
            pr_state = pr_response.get("state", "open")
            pr_draft = pr_response.get("draft", False)
            pr_created_at = pr_response.get("created_at", datetime.now().isoformat())

            # Build telemetry
            duration = time.time() - start_time
            telemetry = {
                "brick_type": "pull_request",
                "pr_number": pr_number,
                "title": title,
                "state": pr_state,
                "draft": pr_draft,
                "head_branch": head,
                "base_branch": base,
                "labels": self.labels,
                "assignees": self.assignees,
                "reviewers": self.reviewers,
                "created_at": pr_created_at,
                "timestamp": datetime.now().isoformat(),
            }

            # Update context with PR number
            updated_context = context.update(pr_number=pr_number)

            logger.info(
                f"Successfully created PR #{pr_number}: {title}"
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
                f"Unexpected error in PullRequestBrick: {str(e)}"
            )

    def _generate_title(self, branch_name: str) -> str:
        """Generate PR title from branch name.

        Args:
            branch_name: Git branch name

        Returns:
            Generated PR title
        """
        # Extract feature name from branch
        # Examples: feature/oauth2 -> Add OAuth2, hotfix/bug-123 -> Fix Bug 123
        parts = branch_name.split("/")

        if len(parts) >= 2:
            branch_type = parts[0].lower()
            feature = parts[1].replace("-", " ").replace("_", " ").title()

            if branch_type == "feature":
                return f"Add {feature}"
            elif branch_type == "hotfix" or branch_type == "bugfix":
                return f"Fix {feature}"
            elif branch_type == "refactor":
                return f"Refactor {feature}"
            else:
                return f"Update {feature}"

        # Fallback for simple branch names
        return f"Update {branch_name.replace('-', ' ').replace('_', ' ').title()}"

    def _generate_body(self, branch_name: str, context: BrickContext) -> str:
        """Generate PR description.

        Args:
            branch_name: Git branch name
            context: Current context

        Returns:
            Generated PR body
        """
        return f"""## Summary

Changes from branch `{branch_name}`.

## Details

- Team: {context.team_id}
- Sprint: {context.sprint_id}
- Commit: {context.commit_sha[:8] if context.commit_sha else 'N/A'}

## Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing complete
"""
