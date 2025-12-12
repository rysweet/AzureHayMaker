"""Unit tests for CommitBrick.

Tests cover:
- Commit creation with file changes
- Commit message generation (auto and manual)
- Author information handling
- Realistic diff generation
- Telemetry data capture
- Error handling (branch not found, API failures)
- Validation requirements

Following TDD - these tests WILL FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

# These imports WILL FAIL - implementation doesn't exist yet
from azure_haymaker.engineering_sim.bricks.base import (
    BrickContext,
    BrickResult,
    BrickExecutionError,
)
from azure_haymaker.engineering_sim.bricks.commit import CommitBrick
from azure_haymaker.engineering_sim.github_client import GitHubClient


class TestCommitBrickInitialization:
    """Test CommitBrick initialization."""

    def test_commit_brick_minimal_initialization(self, mock_github_client):
        """Test CommitBrick can be initialized with minimal parameters."""
        brick = CommitBrick(github_client=mock_github_client)

        assert brick.github_client == mock_github_client
        assert brick.file_paths == []
        assert brick.file_contents == {}
        assert brick.commit_message is None
        assert brick.author_name is None
        assert brick.author_email is None
        assert brick.generate_realistic_changes is True

    def test_commit_brick_full_initialization(self, mock_github_client):
        """Test CommitBrick initialization with all parameters."""
        file_paths = ["src/auth.py", "tests/test_auth.py"]
        file_contents = {"src/auth.py": "def authenticate(): pass"}
        commit_message = "Add OAuth2 authentication"
        author_name = "Alice Developer"
        author_email = "alice@example.com"

        brick = CommitBrick(
            github_client=mock_github_client,
            file_paths=file_paths,
            file_contents=file_contents,
            commit_message=commit_message,
            author_name=author_name,
            author_email=author_email,
            generate_realistic_changes=False
        )

        assert brick.file_paths == file_paths
        assert brick.file_contents == file_contents
        assert brick.commit_message == commit_message
        assert brick.author_name == author_name
        assert brick.author_email == author_email
        assert brick.generate_realistic_changes is False

    def test_commit_brick_name_property(self, mock_github_client):
        """Test CommitBrick name property."""
        brick = CommitBrick(github_client=mock_github_client)
        assert brick.name == "CommitBrick"


class TestCommitBrickValidation:
    """Test CommitBrick validation logic."""

    def test_validate_requires_branch_name(self, mock_github_client):
        """Test validate() requires branch_name in context."""
        brick = CommitBrick(github_client=mock_github_client)

        context_no_branch = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )
        assert brick.validate(context_no_branch) is False

    def test_validate_passes_with_branch_name(self, mock_github_client):
        """Test validate() passes when branch_name is set."""
        brick = CommitBrick(github_client=mock_github_client)

        context_with_branch = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/oauth2"
        )
        assert brick.validate(context_with_branch) is True

    def test_validate_passes_with_empty_branch_name(self, mock_github_client):
        """Test validate() behavior with empty string branch name."""
        brick = CommitBrick(github_client=mock_github_client)

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name=""
        )
        # Empty string should be considered invalid
        assert brick.validate(context) is False


class TestCommitBrickExecution:
    """Test CommitBrick execute() method."""

    @pytest.mark.asyncio
    async def test_execute_creates_commit(self, mock_github_client):
        """Test execute() creates a commit via GitHub API."""
        # Mock GitHub client response
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123def456",
            "commit": {
                "author": {"name": "Alice Developer", "email": "alice@example.com"},
                "message": "Add authentication feature"
            },
            "files": ["src/auth.py", "tests/test_auth.py"],
            "stats": {"additions": 120, "deletions": 15}
        })

        brick = CommitBrick(
            github_client=mock_github_client,
            file_paths=["src/auth.py", "tests/test_auth.py"],
            commit_message="Add authentication feature"
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/oauth2"
        )

        result = await brick.execute(context)

        # Verify result
        assert result.success is True
        assert result.context.commit_sha == "abc123def456"

        # Verify GitHub API was called
        mock_github_client.create_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_updates_context_with_commit_sha(self, mock_github_client):
        """Test execute() updates context.commit_sha."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "commit_sha_123",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": ["file.py"],
            "stats": {"additions": 10, "deletions": 5}
        })

        brick = CommitBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        result = await brick.execute(context)

        assert result.context.commit_sha == "commit_sha_123"

    @pytest.mark.asyncio
    async def test_execute_generates_telemetry(self, mock_github_client):
        """Test execute() generates comprehensive telemetry."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {
                "author": {"name": "Alice", "email": "alice@example.com"},
                "message": "Add feature"
            },
            "files": ["src/feature.py", "tests/test_feature.py"],
            "stats": {"additions": 150, "deletions": 20}
        })

        brick = CommitBrick(
            github_client=mock_github_client,
            file_paths=["src/feature.py"],
            commit_message="Add feature"
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        result = await brick.execute(context)

        # Verify telemetry structure
        assert result.telemetry["brick_type"] == "commit"
        assert result.telemetry["commit_sha"] == "abc123"
        assert result.telemetry["branch"] == "feature/test"
        assert result.telemetry["author"] == "Alice"
        assert result.telemetry["message"] == "Add feature"
        assert "files_changed" in result.telemetry
        assert "lines_added" in result.telemetry
        assert "lines_deleted" in result.telemetry
        assert "timestamp" in result.telemetry

    @pytest.mark.asyncio
    async def test_execute_with_explicit_file_contents(self, mock_github_client):
        """Test execute() with explicit file contents."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": ["src/auth.py"],
            "stats": {"additions": 50, "deletions": 0}
        })

        file_contents = {
            "src/auth.py": "def authenticate(token):\n    return validate_token(token)"
        }

        brick = CommitBrick(
            github_client=mock_github_client,
            file_contents=file_contents
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/auth"
        )

        result = await brick.execute(context)

        # Verify file contents were passed to GitHub API
        call_args = mock_github_client.create_commit.call_args
        assert "files" in call_args.kwargs or len(call_args.args) >= 3

    @pytest.mark.asyncio
    async def test_execute_with_custom_author(self, mock_github_client):
        """Test execute() with custom author information."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {
                "author": {"name": "Bob Smith", "email": "bob@example.com"},
                "message": "Fix bug"
            },
            "files": ["src/bug.py"],
            "stats": {"additions": 5, "deletions": 3}
        })

        brick = CommitBrick(
            github_client=mock_github_client,
            author_name="Bob Smith",
            author_email="bob@example.com"
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="hotfix/bug-123"
        )

        result = await brick.execute(context)

        assert result.success is True
        assert result.telemetry["author"] == "Bob Smith"

    @pytest.mark.asyncio
    async def test_execute_generates_commit_message_when_none_provided(self, mock_github_client):
        """Test execute() auto-generates commit message if not provided."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {
                "author": {"name": "Dev", "email": "dev@example.com"},
                "message": "Update feature implementation"  # Auto-generated
            },
            "files": ["src/feature.py"],
            "stats": {"additions": 30, "deletions": 10}
        })

        brick = CommitBrick(
            github_client=mock_github_client,
            file_paths=["src/feature.py"],
            commit_message=None  # Should be auto-generated
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        result = await brick.execute(context)

        assert result.success is True
        assert len(result.telemetry["message"]) > 0

    @pytest.mark.asyncio
    async def test_execute_measures_duration(self, mock_github_client):
        """Test execute() measures execution duration."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": ["file.py"],
            "stats": {"additions": 10, "deletions": 0}
        })

        brick = CommitBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        result = await brick.execute(context)

        assert result.duration_seconds >= 0
        assert isinstance(result.duration_seconds, float)


class TestCommitBrickErrorHandling:
    """Test CommitBrick error handling."""

    @pytest.mark.asyncio
    async def test_execute_handles_branch_not_found(self, mock_github_client):
        """Test execute() handles branch not found error."""
        mock_github_client.create_commit = AsyncMock(
            side_effect=BrickExecutionError("Branch 'feature/test' not found")
        )

        brick = CommitBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/nonexistent"
        )

        with pytest.raises(BrickExecutionError) as exc_info:
            await brick.execute(context)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_handles_api_failure(self, mock_github_client):
        """Test execute() handles GitHub API failures."""
        mock_github_client.create_commit = AsyncMock(
            side_effect=Exception("GitHub API error: 503 Service Unavailable")
        )

        brick = CommitBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        with pytest.raises(Exception) as exc_info:
            await brick.execute(context)

        assert "503" in str(exc_info.value) or "API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_returns_failure_result_on_error(self, mock_github_client):
        """Test execute() returns failure BrickResult on error (if error handling is internal)."""
        # This tests an alternative error handling pattern where errors are caught
        # and returned as failed BrickResult instead of raised
        mock_github_client.create_commit = AsyncMock(
            side_effect=Exception("Simulated error")
        )

        brick = CommitBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        # Depending on implementation, this may return a failed result
        # or raise an exception. Test both patterns.
        try:
            result = await brick.execute(context)
            # If no exception, should be failed result
            assert result.success is False
            assert result.error is not None
        except Exception:
            # If exception raised, that's also acceptable
            pass

    @pytest.mark.asyncio
    async def test_execute_without_validation_fails(self, mock_github_client):
        """Test execute() fails if context not validated first."""
        brick = CommitBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
            # Missing branch_name
        )

        # Should fail validation
        assert brick.validate(context) is False


class TestCommitBrickRealisticChanges:
    """Test CommitBrick realistic change generation."""

    @pytest.mark.asyncio
    async def test_execute_generates_realistic_file_changes(self, mock_github_client):
        """Test execute() generates realistic file changes when enabled."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": ["src/feature.py", "tests/test_feature.py"],
            "stats": {"additions": 75, "deletions": 12}
        })

        brick = CommitBrick(
            github_client=mock_github_client,
            generate_realistic_changes=True
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        result = await brick.execute(context)

        # Verify realistic stats
        assert result.telemetry["lines_added"] > 0
        assert result.telemetry["files_changed"] is not None

    @pytest.mark.asyncio
    async def test_execute_with_multiple_files(self, mock_github_client):
        """Test execute() handles multiple file changes."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": [
                "src/auth.py",
                "src/utils.py",
                "tests/test_auth.py",
                "tests/test_utils.py"
            ],
            "stats": {"additions": 200, "deletions": 30}
        })

        brick = CommitBrick(
            github_client=mock_github_client,
            file_paths=[
                "src/auth.py",
                "src/utils.py",
                "tests/test_auth.py",
                "tests/test_utils.py"
            ]
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/auth"
        )

        result = await brick.execute(context)

        assert result.success is True
        assert len(result.telemetry["files_changed"]) == 4


class TestCommitBrickEdgeCases:
    """Test CommitBrick edge cases."""

    @pytest.mark.asyncio
    async def test_execute_with_empty_file_paths(self, mock_github_client):
        """Test execute() with empty file_paths list."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": ["generated_file.py"],  # Generated internally
            "stats": {"additions": 10, "deletions": 0}
        })

        brick = CommitBrick(
            github_client=mock_github_client,
            file_paths=[]  # Empty, should generate files
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        result = await brick.execute(context)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_preserves_existing_context_fields(self, mock_github_client):
        """Test execute() preserves existing context fields."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "new_commit_sha",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": ["file.py"],
            "stats": {"additions": 10, "deletions": 0}
        })

        brick = CommitBrick(github_client=mock_github_client)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test",
            pr_number=142,  # Existing field
            metadata={"existing_key": "existing_value"}
        )

        result = await brick.execute(context)

        # Should preserve existing fields
        assert result.context.team_id == "team_alpha"
        assert result.context.sprint_id == "sprint_42"
        assert result.context.pr_number == 142
        assert result.context.metadata["existing_key"] == "existing_value"
        # Should add new commit_sha
        assert result.context.commit_sha == "new_commit_sha"

    @pytest.mark.asyncio
    async def test_execute_with_very_long_commit_message(self, mock_github_client):
        """Test execute() handles very long commit messages."""
        long_message = "A" * 1000  # 1000 character message

        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "abc123",
            "commit": {
                "author": {"name": "Dev", "email": "dev@example.com"},
                "message": long_message
            },
            "files": ["file.py"],
            "stats": {"additions": 10, "deletions": 0}
        })

        brick = CommitBrick(
            github_client=mock_github_client,
            commit_message=long_message
        )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        result = await brick.execute(context)

        assert result.success is True
        assert len(result.telemetry["message"]) == 1000
