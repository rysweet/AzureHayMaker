"""CommitBrick - Creates GitHub commits with file changes.

This brick handles:
- Creating commits with specified file changes
- Generating realistic file content if needed
- Auto-generating commit messages
- Tracking commit telemetry (SHA, author, stats, etc.)
- Error handling for branch/repo issues
"""

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


class CommitBrick(WorkflowBrick):
    """Creates a commit with file changes.

    This brick creates commits on GitHub with either:
    - Explicit file contents (via file_contents parameter)
    - Generated file contents (via file_paths parameter with generate_realistic_changes=True)

    Args:
        github_client: GitHubClient for API operations
        file_paths: List of file paths to create/modify (optional)
        file_contents: Dict mapping file paths to content (optional)
        commit_message: Commit message (auto-generated if None)
        author_name: Commit author name (optional)
        author_email: Commit author email (optional)
        generate_realistic_changes: Whether to generate realistic diffs (default: True)

    Example:
        >>> client = GitHubClient(token="...", org="myorg")
        >>> brick = CommitBrick(
        ...     github_client=client,
        ...     file_paths=["src/auth.py", "tests/test_auth.py"],
        ...     commit_message="Add OAuth2 authentication"
        ... )
        >>> context = BrickContext(
        ...     team_id="alpha",
        ...     sprint_id="s42",
        ...     repo_name="backend-api",
        ...     branch_name="feature/oauth2"
        ... )
        >>> result = await brick.execute(context)
        >>> assert result.success
        >>> assert result.context.commit_sha is not None
    """

    def __init__(
        self,
        github_client: GitHubClient,
        file_paths: list[str] | None = None,
        file_contents: dict[str, str] | None = None,
        commit_message: str | None = None,
        author_name: str | None = None,
        author_email: str | None = None,
        generate_realistic_changes: bool = True
    ):
        self.github_client = github_client
        self.file_paths = file_paths or []
        self.file_contents = file_contents or {}
        self.commit_message = commit_message
        self.author_name = author_name
        self.author_email = author_email
        self.generate_realistic_changes = generate_realistic_changes

    def validate(self, context: BrickContext) -> bool:
        """Validate that context has required branch_name.

        Args:
            context: Current workflow context

        Returns:
            True if branch_name is set and non-empty, False otherwise
        """
        return context.branch_name is not None and context.branch_name != ""

    async def execute(self, context: BrickContext) -> BrickResult:
        """Create a commit on the specified branch.

        Args:
            context: Current workflow context

        Returns:
            BrickResult with updated commit_sha and telemetry

        Raises:
            BrickExecutionError: If commit creation fails
        """
        start_time = time.time()

        try:
            # Validate preconditions
            if not self.validate(context):
                raise BrickExecutionError(
                    "CommitBrick requires branch_name in context"
                )

            # Prepare file changes
            files_to_commit = self._prepare_files()

            # Generate commit message if not provided
            message = self._generate_commit_message(files_to_commit)

            # Prepare author info if provided
            author = None
            if self.author_name and self.author_email:
                author = {
                    "name": self.author_name,
                    "email": self.author_email
                }

            # Create commit via GitHub API
            logger.info(
                f"Creating commit on {context.repo_name}/{context.branch_name} "
                f"with {len(files_to_commit)} file(s)"
            )

            try:
                commit_response = await self.github_client.create_commit(
                    repo=context.repo_name,
                    branch=context.branch_name,
                    files=files_to_commit,
                    message=message,
                    author=author
                )
            except GitHubAPIError as e:
                raise BrickExecutionError(
                    f"Failed to create commit: {str(e)}"
                ) from e

            # Extract commit details
            commit_sha = commit_response["sha"]
            commit_info = commit_response.get("commit", {})
            commit_author = commit_info.get("author", {})
            stats = commit_response.get("stats", {})
            files_changed = commit_response.get("files", [])

            # Build telemetry
            duration = time.time() - start_time
            telemetry = {
                "brick_type": "commit",
                "commit_sha": commit_sha,
                "branch": context.branch_name,
                "author": commit_author.get("name", self.author_name or "Unknown"),
                "message": message,
                "files_changed": files_changed if isinstance(files_changed, list) else list(files_to_commit.keys()),
                "lines_added": stats.get("additions", 0),
                "lines_deleted": stats.get("deletions", 0),
                "timestamp": datetime.now().isoformat(),
            }

            # Update context with commit SHA
            updated_context = context.update(commit_sha=commit_sha)

            logger.info(
                f"Successfully created commit {commit_sha[:8]} "
                f"(+{telemetry['lines_added']} -{telemetry['lines_deleted']})"
            )

            return BrickResult(
                success=True,
                context=updated_context,
                telemetry=telemetry,
                duration_seconds=duration
            )

        except BrickExecutionError:
            # Re-raise brick execution errors
            raise

        except Exception as e:
            # Wrap unexpected errors
            duration = time.time() - start_time
            raise BrickExecutionError(
                f"Unexpected error in CommitBrick: {str(e)}"
            ) from e

    def _prepare_files(self) -> dict[str, str]:
        """Prepare file contents for commit.

        Returns:
            Dict mapping file paths to content

        Uses explicit file_contents if provided, otherwise generates
        content for files in file_paths list.
        """
        if self.file_contents:
            return self.file_contents

        # Generate content for specified file paths
        files = {}
        for file_path in self.file_paths:
            if self.generate_realistic_changes:
                files[file_path] = self._generate_realistic_content(file_path)
            else:
                files[file_path] = f"# Auto-generated content for {file_path}\n"

        return files

    def _generate_realistic_content(self, file_path: str) -> str:
        """Generate realistic file content based on file type.

        Args:
            file_path: Path to file

        Returns:
            Generated content string
        """
        # Determine file type from extension
        if file_path.endswith(".py"):
            return self._generate_python_content(file_path)
        elif file_path.endswith(".js") or file_path.endswith(".ts"):
            return self._generate_javascript_content(file_path)
        elif file_path.endswith(".md"):
            return self._generate_markdown_content(file_path)
        elif file_path.endswith(".json"):
            return '{\n  "version": "1.0.0",\n  "updated": "true"\n}\n'
        else:
            return f"# Content for {file_path}\n# Generated automatically\n"

    def _generate_python_content(self, file_path: str) -> str:
        """Generate realistic Python code content."""
        is_test = "test_" in file_path or file_path.startswith("tests/")

        if is_test:
            return '''"""Test module."""

import pytest


def test_feature_works():
    """Test that feature works correctly."""
    result = process_data({"key": "value"})
    assert result is not None
    assert "status" in result


def test_error_handling():
    """Test error handling."""
    with pytest.raises(ValueError):
        process_data(None)
'''
        else:
            return '''"""Implementation module."""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def process_data(data: Dict[str, str]) -> Optional[Dict]:
    """Process input data.

    Args:
        data: Input data dictionary

    Returns:
        Processed result or None
    """
    if data is None:
        raise ValueError("Data cannot be None")

    logger.info(f"Processing data: {data}")
    return {"status": "success", "data": data}
'''

    def _generate_javascript_content(self, file_path: str) -> str:
        """Generate realistic JavaScript/TypeScript content."""
        return '''/**
 * Feature implementation
 */

export function processData(input) {
  if (!input) {
    throw new Error('Input is required');
  }

  return {
    status: 'success',
    data: input
  };
}
'''

    def _generate_markdown_content(self, file_path: str) -> str:
        """Generate realistic Markdown content."""
        return '''# Feature Documentation

## Overview

This feature provides improved functionality.

## Usage

```python
result = process_data({"key": "value"})
```

## Notes

- Implementation complete
- Tests passing
'''

    def _generate_commit_message(self, files: dict[str, str]) -> str:
        """Generate commit message based on files changed.

        Args:
            files: Dict of files being committed

        Returns:
            Generated commit message
        """
        if self.commit_message:
            return self.commit_message

        # Auto-generate message based on files
        if not files:
            return "Update repository"

        # Extract file info
        file_count = len(files)
        file_paths = list(files.keys())

        # Determine action verb
        has_tests = any("test" in f for f in file_paths)
        has_docs = any(f.endswith(".md") for f in file_paths)

        if has_tests and has_docs:
            action = "Add feature with tests and documentation"
        elif has_tests:
            action = "Add feature with tests"
        elif has_docs:
            action = "Update documentation"
        else:
            action = "Update feature implementation"

        # Add file count context
        if file_count == 1:
            return f"{action} ({file_paths[0]})"
        elif file_count <= 3:
            return f"{action} ({file_count} files)"
        else:
            return f"{action} ({file_count} files)"
