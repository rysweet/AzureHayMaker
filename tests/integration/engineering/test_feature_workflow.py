"""Integration tests for feature development workflow.

Tests complete workflow execution from commit to merge.
Uses mocked GitHub API to test workflow integration.

NOTE: These tests require shared conftest fixtures. Skipped until fixture
sharing is properly configured between unit and integration test directories.
"""

import pytest

# Skip until conftest fixture sharing is configured
pytestmark = pytest.mark.skip(reason="Requires shared conftest fixtures - see follow-up issue")

from unittest.mock import AsyncMock, Mock

from azure_haymaker.engineering_sim.bricks.base import BrickContext
from azure_haymaker.engineering_sim.bricks.commit import CommitBrick
from azure_haymaker.engineering_sim.bricks.pull_request import PullRequestBrick
from azure_haymaker.engineering_sim.bricks.review import ReviewBrick
from azure_haymaker.engineering_sim.bricks.ci_pipeline import CIPipelineBrick
from azure_haymaker.engineering_sim.bricks.merge import MergeBrick
from azure_haymaker.engineering_sim.workflow import Workflow


@pytest.mark.integration
class TestFeatureWorkflowIntegration:
    """Integration tests for complete feature workflow."""

    @pytest.mark.asyncio
    async def test_complete_feature_workflow(self, mock_github_client):
        """Test complete feature development workflow end-to-end."""
        # Setup mock responses
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "commit_sha_123",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": ["src/feature.py"],
            "stats": {"additions": 100, "deletions": 10}
        })

        mock_github_client.create_pull_request = AsyncMock(return_value={
            "number": 142,
            "title": "Add feature X",
            "state": "open",
            "created_at": "2025-12-08T10:00:00Z"
        })

        mock_github_client.trigger_workflow = AsyncMock(return_value={
            "id": "run_1",
            "status": "completed",
            "conclusion": "success"
        })

        mock_github_client.create_review = AsyncMock(return_value={
            "id": 1,
            "state": "APPROVED",
            "submitted_at": "2025-12-08T11:00:00Z"
        })

        mock_github_client.merge_pull_request = AsyncMock(return_value={
            "sha": "merge_sha_456",
            "merged": True
        })

        # Build workflow
        workflow = (Workflow("feature_development")
                    .add_brick(CommitBrick(
                        github_client=mock_github_client,
                        file_paths=["src/feature.py"],
                        commit_message="Implement feature X"
                    ))
                    .add_brick(PullRequestBrick(
                        github_client=mock_github_client,
                        title="Add feature X"
                    ))
                    .add_brick(CIPipelineBrick(
                        github_client=mock_github_client,
                        failure_probability=0.0  # Always succeed for test
                    ))
                    .add_brick(ReviewBrick(
                        github_client=mock_github_client,
                        review_type="APPROVE"
                    ))
                    .add_brick(MergeBrick(
                        github_client=mock_github_client,
                        merge_strategy="squash"
                    )))

        # Execute workflow
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/x"
        )

        result = await workflow.execute(context)

        # Verify workflow succeeded
        assert result.success is True
        assert result.context.commit_sha == "commit_sha_123"
        assert result.context.pr_number == 142
        assert result.context.metadata["merged"] is True

        # Verify all API calls were made
        mock_github_client.create_commit.assert_called_once()
        mock_github_client.create_pull_request.assert_called_once()
        mock_github_client.trigger_workflow.assert_called_once()
        mock_github_client.create_review.assert_called_once()
        mock_github_client.merge_pull_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_with_ci_failure_and_retry(self, mock_github_client):
        """Test workflow handles CI failure gracefully."""
        mock_github_client.create_commit = AsyncMock(return_value={
            "sha": "commit_sha",
            "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
            "files": ["src/file.py"],
            "stats": {"additions": 10, "deletions": 0}
        })

        mock_github_client.create_pull_request = AsyncMock(return_value={
            "number": 143,
            "title": "Add feature",
            "state": "open"
        })

        # First CI run fails
        ci_call_count = 0

        async def ci_side_effect(*args, **kwargs):
            nonlocal ci_call_count
            ci_call_count += 1
            if ci_call_count == 1:
                return {"id": "run_1", "status": "completed", "conclusion": "failure"}
            else:
                return {"id": "run_2", "status": "completed", "conclusion": "success"}

        mock_github_client.trigger_workflow = AsyncMock(side_effect=ci_side_effect)

        # Build workflow with retry
        workflow = (Workflow("feature_with_retry")
                    .add_brick(CommitBrick(github_client=mock_github_client))
                    .add_brick(PullRequestBrick(github_client=mock_github_client))
                    .add_brick(CIPipelineBrick(
                        github_client=mock_github_client,
                        retry_on_failure=True
                    )))

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        result = await workflow.execute(context)

        # Should eventually succeed after retry
        assert result.success is True
        assert ci_call_count == 2

    @pytest.mark.asyncio
    async def test_workflow_stops_on_failed_validation(self, mock_github_client):
        """Test workflow stops if brick validation fails."""
        # Create workflow that requires PR number but doesn't create one
        workflow = (Workflow("invalid_workflow")
                    .add_brick(ReviewBrick(
                        github_client=mock_github_client
                    )))  # ReviewBrick requires pr_number

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
            # Missing pr_number
        )

        result = await workflow.execute(context)

        assert result.success is False
        assert "Validation failed" in result.error


@pytest.mark.integration
class TestMultipleWorkflowsIntegration:
    """Test running multiple workflows in sequence."""

    @pytest.mark.asyncio
    async def test_sequential_feature_workflows(self, mock_github_client):
        """Test multiple feature workflows run sequentially."""
        # Mock responses
        commit_counter = 0

        async def create_commit_side_effect(*args, **kwargs):
            nonlocal commit_counter
            commit_counter += 1
            return {
                "sha": f"commit_sha_{commit_counter}",
                "commit": {"author": {"name": "Dev", "email": "dev@example.com"}},
                "files": ["file.py"],
                "stats": {"additions": 10, "deletions": 0}
            }

        mock_github_client.create_commit = AsyncMock(side_effect=create_commit_side_effect)

        pr_counter = 0

        async def create_pr_side_effect(*args, **kwargs):
            nonlocal pr_counter
            pr_counter += 1
            return {
                "number": 140 + pr_counter,
                "title": f"Feature {pr_counter}",
                "state": "open"
            }

        mock_github_client.create_pull_request = AsyncMock(side_effect=create_pr_side_effect)

        # Create two feature workflows
        workflow1 = (Workflow("feature_1")
                     .add_brick(CommitBrick(github_client=mock_github_client))
                     .add_brick(PullRequestBrick(github_client=mock_github_client)))

        workflow2 = (Workflow("feature_2")
                     .add_brick(CommitBrick(github_client=mock_github_client))
                     .add_brick(PullRequestBrick(github_client=mock_github_client)))

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/test"
        )

        # Execute both workflows
        result1 = await workflow1.execute(context)
        result2 = await workflow2.execute(context)

        # Both should succeed with unique commit SHAs and PR numbers
        assert result1.success is True
        assert result2.success is True
        assert result1.context.commit_sha == "commit_sha_1"
        assert result2.context.commit_sha == "commit_sha_2"
        assert result1.context.pr_number == 141
        assert result2.context.pr_number == 142


@pytest.mark.integration
@pytest.mark.requires_github_api
class TestRealGitHubAPIIntegration:
    """Integration tests against real GitHub API (gated behind env var)."""

    @pytest.fixture
    def real_github_client(self):
        """Fixture for real GitHub client (requires env vars)."""
        import os
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_TEST_ORG"):
            pytest.skip("Real GitHub API tests require GITHUB_TOKEN and GITHUB_TEST_ORG")

        from azure_haymaker.engineering_sim.github_client import GitHubClient
        return GitHubClient(
            token=os.getenv("GITHUB_TOKEN"),
            org=os.getenv("GITHUB_TEST_ORG")
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_api_feature_workflow(self, real_github_client):
        """Test workflow against real GitHub API (slow, requires credentials)."""
        # This test creates real GitHub resources
        # Only run in CI or with explicit opt-in
        pytest.skip("Skipping real API test by default")

        workflow = (Workflow("real_api_test")
                    .add_brick(CommitBrick(
                        github_client=real_github_client,
                        file_paths=["test_file.txt"],
                        commit_message="Test commit from integration test"
                    ))
                    .add_brick(PullRequestBrick(
                        github_client=real_github_client,
                        title="Test PR - Safe to close",
                        body="This PR was created by automated integration tests"
                    )))

        context = BrickContext(
            team_id="test_team",
            sprint_id="test_sprint",
            repo_name=os.getenv("GITHUB_TEST_REPO", "test-repo"),
            branch_name="test/integration-test"
        )

        result = await workflow.execute(context)

        # Verify real GitHub resources were created
        assert result.success is True
        assert result.context.commit_sha is not None
        assert result.context.pr_number is not None

        # TODO: Cleanup - close PR and delete branch
