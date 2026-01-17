"""CommitBrick - Creates git commits.

Simulates a developer making a commit to a repository,
generating appropriate telemetry.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from azure_haymaker.workflow_bricks.base import BrickBase
from azure_haymaker.workflow_bricks.clients.github_client import GitHubClient
from azure_haymaker.workflow_bricks.exceptions import BrickValidationError
from azure_haymaker.workflow_bricks.models import BrickContext, BrickResult

logger = logging.getLogger(__name__)


class CommitBrick(BrickBase):
    """Brick that creates a git commit.

    Creates a commit with specified files and message, simulating
    a developer's code contribution.

    Attributes:
        message: Commit message
        files: List of file paths to include in the commit
        author_name: Commit author's name
        author_email: Commit author's email

    Example:
        >>> brick = CommitBrick(
        ...     message="feat: Add user authentication",
        ...     files=["src/auth.py", "tests/test_auth.py"],
        ...     author_name="Alice Developer",
        ...     author_email="alice@example.com",
        ... )
        >>> result = await brick.execute(context)
        >>> print(result.outputs["commit_sha"])
    """

    def __init__(
        self,
        message: str,
        files: list[str],
        author_name: str,
        author_email: str,
        file_contents: dict[str, str] | None = None,
    ) -> None:
        """Initialize CommitBrick.

        Args:
            message: Commit message
            files: List of file paths to include
            author_name: Commit author's name
            author_email: Commit author's email
            file_contents: Optional dict mapping file paths to contents
                          (for dry run simulation or test content)
        """
        super().__init__()
        self.message = message
        self.files = files
        self.author_name = author_name
        self.author_email = author_email
        self.file_contents = file_contents or {}

    async def validate(self, context: BrickContext) -> bool:
        """Validate commit preconditions.

        Checks that:
        - Commit message is provided
        - At least one file is specified
        - GitHub token is available

        Args:
            context: Execution context

        Returns:
            True if validation passes

        Raises:
            BrickValidationError: If validation fails
        """
        if not self.message or not self.message.strip():
            raise BrickValidationError("Commit message required")

        if not self.files:
            raise BrickValidationError("No files specified for commit")

        if not context.github_token:
            raise BrickValidationError("GitHub token required")

        return True

    async def execute(self, context: BrickContext) -> BrickResult:
        """Execute the commit.

        In real mode, creates a commit via GitHub API.
        In dry_run mode, simulates the commit without API calls.

        Args:
            context: Execution context

        Returns:
            BrickResult with commit_sha in outputs
        """
        result = self._create_result()

        try:
            if context.dry_run:
                commit_sha = await self._execute_dry_run(context)
            else:
                commit_sha = await self._execute_real(context)

            result.outputs["commit_sha"] = commit_sha
            result.outputs["message"] = self.message
            result.outputs["files"] = self.files
            result.outputs["author"] = f"{self.author_name} <{self.author_email}>"

            # Update context metadata for downstream bricks
            context.metadata["last_commit_sha"] = commit_sha

            # Log telemetry
            self._log_telemetry(
                result=result,
                event_type="created",
                context=context,
                target=f"{context.full_repo_name}@{context.branch_name}",
                details={
                    "commit_sha": commit_sha,
                    "message": self.message,
                    "files_count": len(self.files),
                },
            )

            result.mark_success()

        except Exception as e:
            logger.exception(f"Commit failed: {e}")
            result.mark_failed(str(e))

        return result

    async def _execute_dry_run(self, context: BrickContext) -> str:
        """Execute in dry run mode (no API calls).

        Args:
            context: Execution context

        Returns:
            Simulated commit SHA
        """
        # Generate a fake but realistic-looking SHA
        fake_sha = f"dry_run_{uuid.uuid4().hex[:12]}"

        logger.info(
            f"[DRY RUN] Would create commit on {context.full_repo_name}:{context.branch_name}"
        )
        logger.info(f"[DRY RUN] Message: {self.message}")
        logger.info(f"[DRY RUN] Files: {', '.join(self.files)}")
        logger.info(f"[DRY RUN] Author: {self.author_name} <{self.author_email}>")

        return fake_sha

    async def _execute_real(self, context: BrickContext) -> str:
        """Execute real commit via GitHub API.

        This creates a commit using the GitHub Git Data API:
        1. Get current branch ref
        2. Create blobs for changed files
        3. Create a new tree
        4. Create the commit
        5. Update the branch ref

        Args:
            context: Execution context

        Returns:
            Commit SHA
        """
        client = self._get_client(context)

        # 1. Get current branch ref to find parent commit
        ref = await client.get_ref(
            context.repo_owner,
            context.repo_name,
            f"heads/{context.branch_name}",
        )
        parent_sha = ref["object"]["sha"]

        # 2. Create blobs for files (using provided or placeholder content)
        tree_entries = []
        for file_path in self.files:
            content = self.file_contents.get(
                file_path, self._generate_placeholder_content(file_path)
            )

            blob = await client.create_blob(
                context.repo_owner,
                context.repo_name,
                content,
            )

            tree_entries.append(
                {
                    "path": file_path,
                    "mode": "100644",  # Regular file
                    "type": "blob",
                    "sha": blob["sha"],
                }
            )

        # 3. Create new tree based on parent
        # First get parent tree
        parent_commit = await client._request(
            "GET",
            f"/repos/{context.repo_owner}/{context.repo_name}/git/commits/{parent_sha}",
        )
        base_tree = parent_commit["tree"]["sha"]

        new_tree = await client.create_tree(
            context.repo_owner,
            context.repo_name,
            base_tree,
            tree_entries,
        )

        # 4. Create the commit
        commit = await client.create_commit(
            context.repo_owner,
            context.repo_name,
            self.message,
            new_tree["sha"],
            parent_sha,
            self.author_name,
            self.author_email,
        )

        # 5. Update branch ref to point to new commit
        await client.update_ref(
            context.repo_owner,
            context.repo_name,
            f"heads/{context.branch_name}",
            commit["sha"],
        )

        logger.info(
            f"Created commit {commit['sha']} on {context.full_repo_name}:{context.branch_name}"
        )

        return commit["sha"]

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

    def _generate_placeholder_content(self, file_path: str) -> str:
        """Generate placeholder content for a file.

        Used when file_contents is not provided.

        Args:
            file_path: Path to the file

        Returns:
            Placeholder content string
        """
        timestamp = datetime.now(UTC).isoformat()
        return f"""# Auto-generated content for simulation
# File: {file_path}
# Generated: {timestamp}
# Author: {self.author_name}

# This file was created as part of a software engineering team simulation.
"""


__all__ = ["CommitBrick"]
