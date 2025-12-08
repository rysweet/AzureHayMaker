"""Engineering simulation test fixtures and configuration.

Provides shared fixtures for:
- Mock GitHub clients
- Mock bricks
- Test contexts
- Sample configurations
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime


@pytest.fixture
def mock_github_client():
    """Fixture providing a mock GitHub API client.

    Returns:
        Mock GitHubClient with common methods mocked
    """
    client = Mock()
    client.token = "mock_token"
    client.org = "test-org"
    client.rate_limit_strategy = "wait"

    # Mock async methods
    client.create_commit = AsyncMock(return_value={
        "sha": "mock_commit_sha",
        "commit": {
            "author": {"name": "Test Author", "email": "test@example.com"},
            "message": "Test commit"
        },
        "files": ["test_file.py"],
        "stats": {"additions": 10, "deletions": 5}
    })

    client.create_pull_request = AsyncMock(return_value={
        "number": 1,
        "title": "Test PR",
        "body": "Test description",
        "state": "open",
        "head": {"ref": "feature/test"},
        "base": {"ref": "main"},
        "created_at": "2025-12-08T10:00:00Z"
    })

    client.create_review = AsyncMock(return_value={
        "id": 1,
        "user": {"login": "reviewer"},
        "state": "APPROVED",
        "submitted_at": "2025-12-08T11:00:00Z"
    })

    client.trigger_workflow = AsyncMock(return_value={
        "id": 1,
        "status": "queued",
        "workflow_name": "ci.yml"
    })

    client.merge_pull_request = AsyncMock(return_value={
        "sha": "merge_commit_sha",
        "merged": True,
        "merged_at": "2025-12-08T12:00:00Z"
    })

    client.get_rate_limit = AsyncMock(return_value={
        "resources": {
            "core": {
                "remaining": 5000,
                "reset": 1733662800
            }
        }
    })

    return client


@pytest.fixture
def sample_brick_context():
    """Fixture providing a sample BrickContext.

    Returns:
        BrickContext with common test values
    """
    from azure_haymaker.engineering_sim.bricks.base import BrickContext

    return BrickContext(
        team_id="team_alpha",
        sprint_id="sprint_42",
        repo_name="backend-api",
        branch_name="feature/test",
        base_branch="main",
        metadata={}
    )


@pytest.fixture
def sample_brick_context_with_commit(sample_brick_context):
    """Fixture providing a BrickContext with commit_sha.

    Returns:
        BrickContext with commit_sha set
    """
    return sample_brick_context.update(commit_sha="abc123def456")


@pytest.fixture
def sample_brick_context_with_pr(sample_brick_context_with_commit):
    """Fixture providing a BrickContext with PR number.

    Returns:
        BrickContext with pr_number set
    """
    return sample_brick_context_with_commit.update(pr_number=142)


@pytest.fixture
def sample_team_config():
    """Fixture providing a sample TeamConfig.

    Returns:
        Dict with team configuration
    """
    return {
        "team_id": "team_alpha",
        "team_size": 6,
        "focus": "backend",
        "repo": "backend-api",
        "sprint_duration_days": 10,
        "velocity_points": 40,
        "workflows": [
            {"type": "feature_development", "count": 9},
            {"type": "hotfix", "count": 2}
        ],
        "github_org": "test-org",
        "github_base_branch": "main"
    }


@pytest.fixture
def mock_workflow():
    """Fixture providing a mock Workflow.

    Returns:
        Mock Workflow with common methods
    """
    from azure_haymaker.engineering_sim.workflow import Workflow

    workflow = Mock(spec=Workflow)
    workflow.name = "test_workflow"
    workflow.bricks = []
    workflow.add_brick = Mock(return_value=workflow)
    workflow.execute = AsyncMock()
    workflow.validate_all = Mock(return_value=[])
    workflow.estimate_duration = Mock(return_value=300.0)

    return workflow


@pytest.fixture
def mock_brick():
    """Fixture providing a mock WorkflowBrick.

    Returns:
        Mock WorkflowBrick with common methods
    """
    from azure_haymaker.engineering_sim.bricks.base import WorkflowBrick

    brick = Mock(spec=WorkflowBrick)
    brick.name = "TestBrick"
    brick.validate = Mock(return_value=True)
    brick.execute = AsyncMock()

    return brick


@pytest.fixture
def github_api_response_commit():
    """Fixture providing a sample GitHub commit API response."""
    return {
        "sha": "a1b2c3d4e5f6",
        "node_id": "C_kwDOExample",
        "commit": {
            "author": {
                "name": "Alice Developer",
                "email": "alice@example.com",
                "date": "2025-12-08T10:00:00Z"
            },
            "committer": {
                "name": "Alice Developer",
                "email": "alice@example.com",
                "date": "2025-12-08T10:00:00Z"
            },
            "message": "Add OAuth2 authentication support",
            "tree": {"sha": "tree_sha", "url": "https://api.github.com/..."}
        },
        "url": "https://api.github.com/repos/test-org/backend-api/git/commits/a1b2c3d4e5f6",
        "html_url": "https://github.com/test-org/backend-api/commit/a1b2c3d4e5f6",
        "parents": [{"sha": "parent_sha", "url": "https://api.github.com/..."}],
        "stats": {
            "total": 150,
            "additions": 120,
            "deletions": 30
        },
        "files": [
            {
                "sha": "file_sha",
                "filename": "src/auth.py",
                "status": "modified",
                "additions": 80,
                "deletions": 10,
                "changes": 90
            },
            {
                "sha": "file_sha2",
                "filename": "tests/test_auth.py",
                "status": "added",
                "additions": 40,
                "deletions": 20,
                "changes": 60
            }
        ]
    }


@pytest.fixture
def github_api_response_pull_request():
    """Fixture providing a sample GitHub PR API response."""
    return {
        "id": 123456789,
        "node_id": "PR_kwDOExample",
        "number": 142,
        "state": "open",
        "locked": False,
        "title": "Add OAuth2 authentication support",
        "user": {"login": "alice-dev", "id": 1, "type": "User"},
        "body": "Implements OAuth2 authentication flow with token refresh support.",
        "created_at": "2025-12-08T10:00:00Z",
        "updated_at": "2025-12-08T10:00:00Z",
        "closed_at": None,
        "merged_at": None,
        "merge_commit_sha": None,
        "assignees": [{"login": "bob-dev", "id": 2}],
        "requested_reviewers": [{"login": "tech-lead", "id": 3}],
        "labels": [
            {"id": 1, "name": "enhancement", "color": "84b6eb"},
            {"id": 2, "name": "security", "color": "ee0701"}
        ],
        "head": {
            "label": "alice-dev:feature/oauth2",
            "ref": "feature/oauth2",
            "sha": "a1b2c3d4e5f6"
        },
        "base": {
            "label": "test-org:main",
            "ref": "main",
            "sha": "base_sha"
        },
        "draft": False,
        "url": "https://api.github.com/repos/test-org/backend-api/pulls/142",
        "html_url": "https://github.com/test-org/backend-api/pull/142"
    }


@pytest.fixture
def github_api_response_review():
    """Fixture providing a sample GitHub review API response."""
    return {
        "id": 987654321,
        "node_id": "PRR_kwDOExample",
        "user": {"login": "tech-lead", "id": 3},
        "body": "Great implementation! Just a few minor suggestions.",
        "state": "APPROVED",
        "html_url": "https://github.com/test-org/backend-api/pull/142#pullrequestreview-987654321",
        "submitted_at": "2025-12-08T11:30:00Z",
        "commit_id": "a1b2c3d4e5f6"
    }


@pytest.fixture
def mock_datetime(monkeypatch):
    """Fixture providing a mocked datetime for consistent testing.

    Returns:
        Fixed datetime: 2025-12-08 10:00:00
    """
    from datetime import datetime

    class MockDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 12, 8, 10, 0, 0)

        @classmethod
        def utcnow(cls):
            return datetime(2025, 12, 8, 10, 0, 0)

    monkeypatch.setattr("datetime.datetime", MockDateTime)
    return MockDateTime


@pytest.fixture
def sample_workflow_config():
    """Fixture providing a sample workflow configuration."""
    return {
        "name": "feature_development",
        "bricks": [
            {"type": "commit", "params": {"file_paths": ["src/feature.py"]}},
            {"type": "commit", "params": {"file_paths": ["tests/test_feature.py"]}},
            {"type": "pull_request", "params": {"title": "Add feature X"}},
            {"type": "ci_pipeline", "params": {"test_suite": "full"}},
            {"type": "review", "params": {"review_type": "APPROVE"}},
            {"type": "merge", "params": {"merge_strategy": "squash"}}
        ]
    }


# Marker for tests that require GitHub API access
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "requires_github_api: mark test as requiring real GitHub API access"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
